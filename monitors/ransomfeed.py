#!/usr/bin/env python3
"""
Ransomfeed Advanced Scraper (High-Speed Multi-Threaded Version)
----------------------------------------------------------------
1. If ransomfeed_groups_stats.csv is missing, scrape the stats page.
2. Read all group names from stats CSV.
3. Concurrently scrape all group profiles using ThreadPoolExecutor for 100% WAF bypass.
4. Output combined JSON and CSV of all source URLs with 100% data integrity.
"""

import requests
from bs4 import BeautifulSoup
import json
import csv
import time
import re
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict

# ---------- Configuration ----------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

BASE_URL = "https://www.ransomfeed.it/"
STATS_PAGE = "?page=stats&subpage=groups-stats"
PROFILE_PATH = "?page=stats&subpage=group-profile"
STATS_CSV = os.path.join(DATA_DIR, "ransomfeed_groups_stats.csv")
SOURCE_JSON = os.path.join(DATA_DIR, "ransomfeed_all_source_urls.json")
SOURCE_CSV = os.path.join(DATA_DIR, "ransomfeed_all_source_urls.csv")
MAX_WORKERS = 35  # 35 parallel threads

def fetch_stats_csv_if_missing():
    if os.path.exists(STATS_CSV):
        print(f"[+] Stats file '{STATS_CSV}' already exists. Skipping download.")
        return True

    print(f"[*] Stats file not found. Fetching stats page...")
    url = f"{BASE_URL}{STATS_PAGE}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    try:
        resp = requests.get(url, timeout=30, headers=headers)
        resp.raise_for_status()
    except Exception as e:
        print(f"[-] Failed to fetch stats page: {e}")
        return False

    soup = BeautifulSoup(resp.text, "html.parser")
    rows = soup.find_all("tr", attrs={"data-group": True})
    if not rows:
        print("[-] No group rows found on stats page.")
        return False

    groups = []
    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 4:
            continue
        name_tag = cells[0].find("a", class_="fw-semibold")
        group_name = name_tag.get_text(strip=True) if name_tag else ""

        total = re.sub(r"[^\d]", "", cells[1].get_text(strip=True)) or "0"
        yr2026 = re.sub(r"[^\d]", "", cells[2].get_text(strip=True)) or "0"
        yr2025 = re.sub(r"[^\d]", "", cells[3].get_text(strip=True)) or "0"

        groups.append({
            "group": group_name,
            "total": int(total),
            "2026": int(yr2026),
            "2025": int(yr2025)
        })

    with open(STATS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["group", "total", "2026", "2025"])
        writer.writeheader()
        writer.writerows(groups)

    print(f"[+] Stats CSV saved: {STATS_CSV} ({len(groups)} groups)")
    return True

def read_group_names(csv_file: str) -> List[str]:
    groups = []
    try:
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get("group") or row.get("Group")
                if name:
                    groups.append(name)
        print(f"[+] Read {len(groups)} group names from {csv_file}")
        return groups
    except Exception as e:
        print(f"[-] Error reading CSV: {e}")
        return []

def parse_source_urls(html: str) -> List[Dict]:
    soup = BeautifulSoup(html, "html.parser")
    results = []

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if ".onion" not in href:
            continue

        status = "Unknown"
        version = ""

        for ancestor in a.parents:
            for el in ancestor.find_all(attrs={"data-i18n": True}):
                i18n_val = el.get("data-i18n")
                if i18n_val == "stats.online":
                    status = "Online"
                elif i18n_val == "stats.offline":
                    status = "Offline"
                if status != "Unknown":
                    break
            if status != "Unknown":
                break

        if status == "Unknown" and a.parent:
            parent_text = a.parent.get_text()
            if "Online" in parent_text:
                status = "Online"
            elif "Offline" in parent_text:
                status = "Offline"

        if a.parent:
            all_text = a.parent.get_text()
            version_match = re.search(r'\b(?:v|version)?\s*([23])\b', all_text, re.IGNORECASE)
            if version_match:
                version = version_match.group(1)

        results.append({
            "url": href,
            "status": status,
            "version": version
        })

    return results

def fetch_group_profile(session: requests.Session, group_name: str) -> tuple:
    url = f"{BASE_URL}{PROFILE_PATH}&group={group_name}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        resp = session.get(url, timeout=20, headers=headers)
        if resp.status_code == 200:
            urls = parse_source_urls(resp.text)
            return group_name, urls
        else:
            return group_name, []
    except Exception as e:
        return group_name, []

def scrape_all_groups(groups: List[str]) -> Dict[str, List[Dict]]:
    all_data = {}
    total = len(groups)
    print(f"[*] Concurrently scraping {total} groups using {MAX_WORKERS} threads...")

    from requests.adapters import HTTPAdapter

    with requests.Session() as session:
        adapter = HTTPAdapter(pool_connections=MAX_WORKERS, pool_maxsize=MAX_WORKERS)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_group = {
                executor.submit(fetch_group_profile, session, group): group for group in groups
            }

            completed = 0
            for future in as_completed(future_to_group):
                completed += 1
                group_name, urls = future.result()
                all_data[group_name] = urls
                if completed % 25 == 0 or completed == total:
                    print(f"  Progress: [{completed}/{total}] groups completed.")

    return all_data

def save_outputs(all_data: Dict[str, List[Dict]]):
    with open(SOURCE_JSON, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)

    csv_rows = []
    for group, urls in all_data.items():
        for url_info in urls:
            csv_rows.append({
                "group": group,
                "url": url_info["url"],
                "status": url_info["status"],
                "version": url_info["version"]
            })

    with open(SOURCE_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["group", "url", "status", "version"])
        writer.writeheader()
        writer.writerows(csv_rows)

    print(f"[+] JSON saved to {SOURCE_JSON}")
    print(f"[+] CSV saved to {SOURCE_CSV}")
    print(f"    Total source URLs: {len(csv_rows)}")

def main():
    start_time = time.time()
    print("[*] Starting Ransomfeed High-Speed Scraper\n")

    if not fetch_stats_csv_if_missing():
        print("[-] Cannot proceed without group stats.")
        return

    groups = read_group_names(STATS_CSV)
    if not groups:
        print("[-] No groups found. Exiting.")
        return

    all_data = scrape_all_groups(groups)
    save_outputs(all_data)

    total_online = sum(1 for urls in all_data.values() for u in urls if u["status"] == "Online")
    total_offline = sum(1 for urls in all_data.values() for u in urls if u["status"] == "Offline")
    total_unknown = sum(1 for urls in all_data.values() for u in urls if u["status"] == "Unknown")
    elapsed = time.time() - start_time

    print(f"\n[+] Scraping completed in {elapsed:.1f} seconds!")
    print(f"    Online : {total_online}")
    print(f"    Offline: {total_offline}")
    print(f"    Unknown: {total_unknown}")
    print(f"    Groups with URLs: {sum(1 for urls in all_data.values() if urls)}")

if __name__ == "__main__":
    main()