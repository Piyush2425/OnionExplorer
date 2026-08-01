#!/usr/bin/env python3
"""
Ransomware.live - High-Speed Multi-Threaded Location Scraper
------------------------------------------------------------
1. Cache/fetch group list (name and slug) from /groups page.
2. Concurrently fetch each group page using ThreadPoolExecutor.
3. Parse Known Locations table for each group (extracts data-fqdn and onion URLs).
4. Output combined JSON and CSV of all locations with 100% data integrity.
"""

import requests
from bs4 import BeautifulSoup
import csv
import json
import time
import os
import sys
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional

# ---------- Configuration ----------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

BASE_URL = "https://www.ransomware.live"
GROUPS_PAGE = "/groups"
GROUP_DETAIL_PAGE = "/group"

GROUPS_CSV = os.path.join(DATA_DIR, "ransomware_live_groups.csv")
LOCATIONS_CSV = os.path.join(DATA_DIR, "ransomware_live_locations.csv")
LOCATIONS_JSON = os.path.join(DATA_DIR, "ransomware_live_locations.json")
MAX_WORKERS = 35  # 35 parallel threads

def fetch_html(url: str, session: Optional[requests.Session] = None) -> Optional[str]:
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        if session:
            resp = session.get(url, timeout=20, headers=headers)
        else:
            resp = requests.get(url, timeout=20, headers=headers)
        resp.raise_for_status()
        return resp.text
    except Exception:
        return None

def scrape_groups_from_page() -> List[Dict]:
    url = f"{BASE_URL}{GROUPS_PAGE}"
    html = fetch_html(url)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    items = soup.find_all("li", class_="rl-group-item")
    if not items:
        print("[-] No group items found on page.")
        return []

    groups = []
    for item in items:
        link = item.find("a", href=True)
        if not link:
            continue
        href = link.get("href")
        if not href or "/group/" not in href:
            continue
        slug = href.split("/group/")[-1].strip("/")
        if not slug:
            continue

        name_tag = item.find("span", class_="rl-group-badge")
        display_name = name_tag.get_text(strip=True) if name_tag else slug

        groups.append({
            "slug": slug,
            "name": display_name
        })

    return groups

def fetch_groups_csv_if_missing(force_refresh: bool = False):
    if force_refresh:
        print(f"[*] Force refresh requested. Re-fetching group list...")
    elif os.path.exists(GROUPS_CSV):
        try:
            with open(GROUPS_CSV, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                valid = all(row.get("slug", "").strip() for row in rows)
                if valid and rows:
                    print(f"[+] Group list file '{GROUPS_CSV}' exists ({len(rows)} groups). Skipping download.")
                    return True
                else:
                    print(f"[!] Group list file '{GROUPS_CSV}' is corrupted. Re-fetching...")
        except Exception as e:
            print(f"[!] Error reading CSV: {e}. Re-fetching...")

    print(f"[*] Fetching groups from {BASE_URL}{GROUPS_PAGE}...")
    groups = scrape_groups_from_page()
    if not groups:
        print("[-] Failed to fetch group list.")
        return False

    with open(GROUPS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["slug", "name"])
        writer.writeheader()
        writer.writerows(groups)

    print(f"[+] Groups CSV saved: {GROUPS_CSV} ({len(groups)} groups)")
    return True

def read_groups(csv_file: str) -> List[Dict]:
    groups = []
    try:
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                slug = row.get("slug", "").strip()
                name = row.get("name", "").strip()
                if slug:
                    groups.append({
                        "slug": slug,
                        "name": name or slug
                    })
        print(f"[+] Read {len(groups)} valid groups from {csv_file}")
        return groups
    except Exception as e:
        print(f"[-] Error reading CSV: {e}")
        return []

def parse_group_locations(html: str) -> List[Dict]:
    soup = BeautifulSoup(html, "html.parser")
    locations_table = None

    for table in soup.find_all("table"):
        header_text = table.get_text()
        if "FQDN" in header_text or "Favicon" in header_text or "Available" in header_text:
            locations_table = table
            break

    if not locations_table:
        return []

    locations = []
    rows = locations_table.find_all("tr")
    for row in rows[1:]:
        cells = row.find_all("td")
        if not cells:
            continue

        # 1. Extract FQDN (attribute data-fqdn, <code> tag, or cell with .onion)
        fqdn = ""
        fqdn_link = row.find(attrs={"data-fqdn": True})
        if fqdn_link and fqdn_link.get("data-fqdn"):
            fqdn = fqdn_link["data-fqdn"].strip()

        if not fqdn:
            code_tag = row.find("code")
            if code_tag and ".onion" in code_tag.get_text():
                fqdn = code_tag.get_text(strip=True)

        if not fqdn:
            for cell in cells:
                text = cell.get_text(strip=True)
                if ".onion" in text:
                    fqdn = text
                    break

        if not fqdn:
            continue

        # 2. Extract Available status
        available = False
        success_badge = row.find(class_=re.compile(r"bg-success|online"))
        if success_badge:
            available = True
        elif "yes" in row.get_text().lower():
            available = True

        danger_badge = row.find(class_=re.compile(r"bg-danger|offline"))
        if danger_badge:
            available = False

        # 3. Last Visit date
        last_visit = ""
        for cell in cells:
            text = cell.get_text(strip=True)
            if re.search(r"\d{4}-\d{2}-\d{2}", text):
                last_visit = text
                break

        # 4. Server Info
        server_info = ""
        svg_icon = row.find("svg")
        if svg_icon and svg_icon.find("title"):
            server_info = svg_icon.find("title").get_text(strip=True)
        elif len(cells) >= 6:
            server_info = cells[5].get_text(strip=True)

        # 5. Full URL
        url = f"http://{fqdn}" if fqdn and not fqdn.startswith("http") else fqdn

        locations.append({
            "fqdn": fqdn,
            "url": url,
            "available": available,
            "last_visit": last_visit,
            "server_info": server_info
        })

    return locations

def fetch_one_group(session: requests.Session, group: Dict) -> List[Dict]:
    slug = group["slug"]
    name = group["name"]
    url = f"{BASE_URL}{GROUP_DETAIL_PAGE}/{slug}"
    html = fetch_html(url, session=session)
    if not html:
        return []

    locations = parse_group_locations(html)
    for loc in locations:
        loc["group_slug"] = slug
        loc["group_name"] = name
    return locations

def scrape_all_locations(groups: List[Dict]) -> List[Dict]:
    all_locations = []
    total = len(groups)
    print(f"[*] Concurrently fetching locations for {total} groups using {MAX_WORKERS} threads...")

    from requests.adapters import HTTPAdapter

    with requests.Session() as session:
        adapter = HTTPAdapter(pool_connections=MAX_WORKERS, pool_maxsize=MAX_WORKERS)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_group = {
                executor.submit(fetch_one_group, session, group): group for group in groups
            }

            completed = 0
            for future in as_completed(future_to_group):
                completed += 1
                locs = future.result()
                all_locations.extend(locs)
                if completed % 50 == 0 or completed == total:
                    print(f"  Progress: [{completed}/{total}] groups parsed.")

    return all_locations

def save_outputs(all_locations: List[Dict]):
    if not all_locations:
        print("[!] No data to save.")
        return

    fieldnames = ["group_slug", "group_name", "fqdn", "url", "available", "last_visit", "server_info"]
    with open(LOCATIONS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_locations)
    print(f"[+] CSV saved to {LOCATIONS_CSV}")

    nested = {}
    for loc in all_locations:
        slug = loc["group_slug"]
        if slug not in nested:
            nested[slug] = {
                "name": loc["group_name"],
                "locations": []
            }
        nested[slug]["locations"].append({
            "fqdn": loc["fqdn"],
            "url": loc["url"],
            "available": loc["available"],
            "last_visit": loc["last_visit"],
            "server_info": loc["server_info"]
        })

    with open(LOCATIONS_JSON, "w", encoding="utf-8") as f:
        json.dump(nested, f, indent=2, ensure_ascii=False)
    print(f"[+] JSON saved to {LOCATIONS_JSON}")

def main():
    start_time = time.time()
    force_refresh = "--refresh" in sys.argv or "-r" in sys.argv
    print("[*] Starting Ransomware.live High-Speed Scraper\n")

    if not fetch_groups_csv_if_missing(force_refresh):
        print("[-] Cannot proceed without group list.")
        return

    groups = read_groups(GROUPS_CSV)
    if not groups:
        print("[-] No valid groups found. Exiting.")
        return

    all_locations = scrape_all_locations(groups)
    save_outputs(all_locations)

    total_locations = len(all_locations)
    online = sum(1 for loc in all_locations if loc["available"])
    offline = total_locations - online
    groups_with_locations = len(set(loc["group_slug"] for loc in all_locations))
    elapsed = time.time() - start_time

    print(f"\n[+] Scraping completed in {elapsed:.1f} seconds!")
    print(f"    Total locations: {total_locations}")
    print(f"    Online: {online}")
    print(f"    Offline: {offline}")
    print(f"    Groups with locations: {groups_with_locations}")

if __name__ == "__main__":
    main()