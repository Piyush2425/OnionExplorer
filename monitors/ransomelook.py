#!/usr/bin/env python3
"""
RansomLook.io - Async scraper with JSON + CSV output
Stores up/down status for every link of every group and market.
SSL verification is disabled to bypass expired certificate.
"""

import aiohttp
import asyncio
import json
import csv
import time
import os
from typing import List, Dict, Any, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

BASE_URL = "https://www.ransomlook.io/api"
CONCURRENT_LIMIT = 25
GROUPS_JSON = os.path.join(DATA_DIR, "ransomlook_groups.json")
MARKETS_JSON = os.path.join(DATA_DIR, "ransomlook_markets.json")
LINKS_CSV = os.path.join(DATA_DIR, "ransomlook_links.csv")

def extract_locations(data: Any) -> List[Dict[str, Any]]:
    """Extract location data (including availability) from API response."""
    locations = []
    if not data or not isinstance(data, list) or len(data) == 0:
        return locations
    entry = data[0]
    if isinstance(entry, dict) and "locations" in entry:
        for loc in entry["locations"]:
            locations.append({
                "url": loc.get("slug", ""),
                "fqdn": loc.get("fqdn", ""),
                "available": loc.get("available", False),
                "version": loc.get("version", 0),
                "lastscrape": loc.get("lastscrape", "")
            })
    return locations

async def fetch_json(session: aiohttp.ClientSession, endpoint: str) -> Any:
    url = f"{BASE_URL}/{endpoint}"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                print(f"  [!] HTTP {resp.status} for {endpoint}")
                return None
    except Exception as e:
        print(f"  [-] Error {endpoint}: {e}")
        return None

async def scrape_entities(
    session: aiohttp.ClientSession,
    names: List[str],
    entity_type: str,
    semaphore: asyncio.Semaphore
) -> Dict[str, Any]:
    """Scrape details for many entities concurrently."""
    async def fetch_one(name: str):
        async with semaphore:
            print(f"  Fetching {entity_type}/{name}")
            data = await fetch_json(session, f"{entity_type}/{name}")
            locations = extract_locations(data)
            return name, {
                "locations": locations,
                "link_count": len(locations)
            }

    tasks = [fetch_one(name) for name in names]
    results = await asyncio.gather(*tasks)
    return dict(results)

def write_csv(links_data: List[Tuple[str, str, Dict[str, Any]]], filename: str):
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["entity_name", "entity_type", "url", "fqdn", "available", "version", "lastscrape"])
        for name, etype, loc in links_data:
            writer.writerow([
                name,
                etype,
                loc.get("url", ""),
                loc.get("fqdn", ""),
                loc.get("available", False),
                loc.get("version", 0),
                loc.get("lastscrape", "")
            ])

async def main():
    print("[*] Starting RansomLook scraper (JSON + CSV with up/down status)")
    start_time = time.time()

    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        print("[*] Fetching group list...")
        group_names = await fetch_json(session, "groups")
        if not group_names or not isinstance(group_names, list):
            print("[-] Failed to fetch groups.")
            return
        print(f"[+] Found {len(group_names)} groups.")

        print("[*] Fetching market list...")
        market_names = await fetch_json(session, "markets")
        if not market_names or not isinstance(market_names, list):
            print("[-] Failed to fetch markets.")
            return
        print(f"[+] Found {len(market_names)} markets.")

        semaphore = asyncio.Semaphore(CONCURRENT_LIMIT)

        print("\n[*] Scraping group details...")
        groups_data = await scrape_entities(session, group_names, "group", semaphore)

        print("\n[*] Scraping market details...")
        markets_data = await scrape_entities(session, market_names, "market", semaphore)

    groups_output = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "total_groups": len(groups_data),
        "groups": groups_data
    }
    markets_output = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "total_markets": len(markets_data),
        "markets": markets_data
    }

    with open(GROUPS_JSON, "w", encoding="utf-8") as f:
        json.dump(groups_output, f, indent=2, ensure_ascii=False)
    with open(MARKETS_JSON, "w", encoding="utf-8") as f:
        json.dump(markets_output, f, indent=2, ensure_ascii=False)

    csv_rows = []
    for name, data in groups_data.items():
        for loc in data["locations"]:
            csv_rows.append((name, "group", loc))
    for name, data in markets_data.items():
        for loc in data["locations"]:
            csv_rows.append((name, "market", loc))

    write_csv(csv_rows, LINKS_CSV)

    total_links = len(csv_rows)
    up_links = sum(1 for _, _, loc in csv_rows if loc.get("available", False))
    down_links = total_links - up_links

    total_group_links = sum(g["link_count"] for g in groups_data.values())
    total_market_links = sum(m["link_count"] for m in markets_data.values())

    elapsed = time.time() - start_time
    print("\n" + "="*55)
    print(f"[+] Scraping complete in {elapsed:.1f} seconds!")
    print(f"    JSON files:")
    print(f"      - {GROUPS_JSON} – {len(groups_data)} groups, {total_group_links} links")
    print(f"      - {MARKETS_JSON} – {len(markets_data)} markets, {total_market_links} links")
    print(f"    CSV file:")
    print(f"      - {LINKS_CSV} – {total_links} total links")
    print(f"\n[*] Link status summary:")
    print(f"      Up   : {up_links} links")
    print(f"      Down : {down_links} links")
    print("="*55)

if __name__ == "__main__":
    asyncio.run(main())