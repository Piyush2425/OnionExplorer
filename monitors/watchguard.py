"""
WatchGuard Ransomware Tracker Scraper
======================================
Scrapes all ransomware groups from:
  https://www.watchguard.com/wgrd-security-hub/ransomware-tracker

Extracts per group:
  - Group Name, Profile URL
  - Status (Active / Inactive)
  - Ransomware Type
  - First Seen date
  - Last Seen date
  - Onion links (.onion URLs from the detail page)
  - Email addresses
  - Telegram links

Output: data/watchguard_ransomware.json  AND  data/watchguard_ransomware.csv
"""

import os
import re
import json
import csv
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# ─── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("WatchGuard")

# ─── Constants ────────────────────────────────────────────────────────────────
BASE_URL = "https://www.watchguard.com"
TRACKER_URL = f"{BASE_URL}/wgrd-security-hub/ransomware-tracker"

# Store data in project's /data directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "data")
os.makedirs(DATA_DIR, exist_ok=True)

OUTPUT_JSON = os.path.join(DATA_DIR, "watchguard_ransomware.json")
OUTPUT_CSV  = os.path.join(DATA_DIR, "watchguard_ransomware.csv")

ONION_PATTERN   = re.compile(r'[a-z2-7]{16,56}\.onion(?:/[^\s"\'<>]*)?', re.IGNORECASE)
EMAIL_PATTERN   = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')
TELEGRAM_PATTERN = re.compile(r'(?:https?://)?(?:t\.me|telegram\.me)/[a-zA-Z0-9_@+]{3,}')


# ─── Driver Factory ──────────────────────────────────────────────────────────
def make_driver() -> webdriver.Chrome:
    """Create a headless Chrome driver."""
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    )
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=opts)


# ─── Phase 1: Scrape listing table (all pages) ───────────────────────────────
def scrape_listing_table(driver: webdriver.Chrome) -> list[dict]:
    """
    Scrape the main tracker table across ALL pages.
    Returns a list of dicts with: group_name, group_url, status, ransomware_type,
    first_seen, last_seen.
    """
    groups = []
    page = 0

    while True:
        url = f"{TRACKER_URL}?page={page}"
        log.info(f"📄 Scraping listing page {page}: {url}")
        driver.get(url)

        # Wait for the table body to appear
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr"))
            )
        except TimeoutException:
            log.warning(f"  Table not found on page {page} — stopping pagination.")
            break

        soup = BeautifulSoup(driver.page_source, "html.parser")
        rows = soup.select("table tbody tr")

        if not rows:
            log.info("  No rows found — end of listing.")
            break

        page_count = 0
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 4:
                continue

            # Status cell: contains <span class="siren-on"> when active
            status_cell = cells[0]
            is_active = bool(status_cell.find("span", class_="siren-on"))
            status = "Active" if is_active else "Inactive"

            # Name + URL cell
            name_cell = cells[1]
            link_tag = name_cell.find("a")
            if not link_tag:
                continue
            group_name = link_tag.get_text(strip=True)
            group_path = link_tag.get("href", "")
            group_url = BASE_URL + group_path if group_path.startswith("/") else group_path

            # Ransomware type cell
            ransomware_type = cells[2].get_text(strip=True)

            # First Seen (datetime attribute gives ISO format)
            first_seen_tag = cells[3].find("time")
            first_seen = first_seen_tag.get("datetime", "") if first_seen_tag else ""
            first_seen_display = first_seen_tag.get_text(strip=True) if first_seen_tag else ""

            # Last Seen
            last_seen_tag = cells[4].find("time") if len(cells) > 4 else None
            last_seen = last_seen_tag.get("datetime", "") if last_seen_tag else ""
            last_seen_display = last_seen_tag.get_text(strip=True) if last_seen_tag else ""

            groups.append({
                "group_name": group_name,
                "group_url": group_url,
                "status": status,
                "ransomware_type": ransomware_type,
                "first_seen": first_seen,
                "first_seen_display": first_seen_display,
                "last_seen": last_seen,
                "last_seen_display": last_seen_display,
                "onion_links": [],
                "emails": [],
                "telegram_links": [],
            })
            page_count += 1

        log.info(f"  → Found {page_count} groups on page {page}")

        # Check if there's a "next page" link
        next_link = soup.select_one("li.pager__item--next a")
        if not next_link:
            log.info("  🏁 Reached last page.")
            break

        page += 1
        time.sleep(1.5)

    log.info(f"✅ Total groups scraped from listing: {len(groups)}")
    return groups


# ─── Phase 2: Scrape detail page for a single group ──────────────────────────
def scrape_group_detail(driver: webdriver.Chrome, group: dict) -> dict:
    """
    Visit a group's detail page and extract onion links, emails, and Telegram links.
    Updates the group dict in-place.
    """
    try:
        driver.get(group["group_url"])
        WebDriverWait(driver, 12).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(2)

        body_text = driver.find_element(By.TAG_NAME, "body").text
        page_source = driver.page_source

        # Extract onion links (from both visible text and source)
        onion_matches = set(ONION_PATTERN.findall(body_text)) | set(ONION_PATTERN.findall(page_source))
        # Filter out obviously non-onion false positives
        onions = [o for o in onion_matches if len(o.split(".onion")[0]) >= 16]

        # Extract emails (filter out watchguard.com domains)
        emails = [
            e for e in set(EMAIL_PATTERN.findall(body_text))
            if "watchguard" not in e.lower() and "example" not in e.lower()
        ]

        # Extract Telegram links
        telegrams = list(set(TELEGRAM_PATTERN.findall(body_text)))

        group["onion_links"] = onions
        group["emails"] = emails
        group["telegram_links"] = telegrams

        log.info(
            f"  ✔ {group['group_name']}: "
            f"{len(onions)} onion(s), {len(emails)} email(s), {len(telegrams)} telegram(s)"
        )

    except Exception as e:
        log.error(f"  ✗ Failed to scrape detail for {group['group_name']}: {e}")

    return group


# ─── Phase 3: Save outputs ───────────────────────────────────────────────────
def save_outputs(groups: list[dict]):
    """Save results to JSON and CSV."""
    # JSON output
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(groups, f, indent=2, ensure_ascii=False)
    log.info(f"💾 JSON saved → {OUTPUT_JSON}")

    # CSV output
    fieldnames = [
        "group_name", "group_url", "status", "ransomware_type",
        "first_seen", "first_seen_display", "last_seen", "last_seen_display",
        "onion_links", "emails", "telegram_links"
    ]
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for g in groups:
            row = dict(g)
            row["onion_links"]    = " | ".join(g["onion_links"])
            row["emails"]         = " | ".join(g["emails"])
            row["telegram_links"] = " | ".join(g["telegram_links"])
            writer.writerow(row)
    log.info(f"💾 CSV saved  → {OUTPUT_CSV}")


# ─── Main ────────────────────────────────────────────────────────────────────
def main():
    log.info("🚀 WatchGuard Ransomware Tracker Scraper starting...")
    driver = make_driver()

    try:
        # Phase 1: Get all group metadata from listing pages
        groups = scrape_listing_table(driver)

        if not groups:
            log.warning("No groups found. Exiting.")
            return

        # Phase 2: Visit each detail page to extract onion links
        log.info(f"\n🔍 Scraping detail pages for {len(groups)} groups...")
        for idx, group in enumerate(groups, 1):
            log.info(f"  [{idx}/{len(groups)}] {group['group_name']}")
            scrape_group_detail(driver, group)

        # Phase 3: Save both JSON and CSV
        save_outputs(groups)

        # Summary
        active   = sum(1 for g in groups if g["status"] == "Active")
        inactive = len(groups) - active
        with_onion = sum(1 for g in groups if g["onion_links"])

        log.info("\n" + "=" * 50)
        log.info("📊 SCRAPING SUMMARY")
        log.info(f"  Total Groups     : {len(groups)}")
        log.info(f"  Active           : {active}")
        log.info(f"  Inactive         : {inactive}")
        log.info(f"  Groups with Onion: {with_onion}")
        log.info("=" * 50)
        log.info("✨ Done.")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()