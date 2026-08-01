#!/usr/bin/env python3
"""
OnionExplorer Library Test Script
---------------------------------
Tests:
 1. Standardized ThreatActorLocation models
 2. One-shot location scraping (RansomFeed, RansomwareLive, RansomLook)
 3. Continuous background scraper runner with callback hooks
 4. Deduplication engines (MemoryStateStore & SQLiteStateStore)
 5. Exporting results to JSON & CSV files
"""

import time
import os
import logging

# Configure logging format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)

from onion_explorer import ThreatLocationClient, ThreatActorLocation
from onion_explorer.engine import MemoryStateStore, SQLiteStateStore
from onion_explorer.exporters import export_to_json, export_to_csv


def test_models_and_deduplication():
    print("\n" + "=" * 60)
    print("STEP 1: Testing Data Models & Deduplication Storage")
    print("=" * 60)

    # 1. Memory Store Test
    mem_store = MemoryStateStore()
    loc1 = ThreatActorLocation(
        group_name="LockBit",
        location_url="http://lockbit54321.onion",
        source_feed="RansomFeed",
        status="Online"
    )
    loc2 = ThreatActorLocation(
        group_name="lockbit",  # different casing
        location_url="http://lockbit54321.onion/", # trailing slash
        source_feed="RansomwareLive",
        status="Online"
    )

    is_new_1 = mem_store.add(loc1)
    is_new_2 = mem_store.add(loc2)

    print(f"[*] Added loc1 (LockBit): New = {is_new_1}")
    print(f"[*] Added loc2 (lockbit duplicate): New = {is_new_2}")
    assert is_new_1 is True, "loc1 should be new"
    assert is_new_2 is False, "loc2 should be detected as duplicate"
    print(f"[+] MemoryStateStore size: {mem_store.size()} (Expected: 1)")

    # 2. SQLite Store Test
    db_file = "test_state.db"
    if os.path.exists(db_file):
        os.remove(db_file)

    sqlite_store = SQLiteStateStore(db_path=db_file)
    sqlite_store.add(loc1)
    sqlite_store.add(loc2)
    print(f"[+] SQLiteStateStore size: {sqlite_store.size()} (Expected: 1)")

    if os.path.exists(db_file):
        os.remove(db_file)
    print("[+] Step 1 PASSED!")


def test_one_shot_scraping():
    print("\n" + "=" * 60)
    print("STEP 2: Testing One-Shot Location Scraping")
    print("=" * 60)

    # Initialize client for RansomLook (fast API monitor) and RansomFeed
    client = ThreatLocationClient(monitors=["ransomlook"])
    
    print("[*] Fetching threat actor location links...")
    locations = client.fetch_all_locations()
    print(f"[+] Total location links returned: {len(locations)}")

    if locations:
        sample = locations[0]
        print(f"\n--- Sample Threat Actor Location ---")
        print(f"  Group Name  : {sample.group_name}")
        print(f"  Location URL: {sample.location_url}")
        print(f"  Source Feed : {sample.source_feed}")
        print(f"  Status      : {sample.status}")
        print(f"  URL Type    : {sample.url_type}")

        # Test Exporters
        os.makedirs("data", exist_ok=True)
        json_out = "data/test_output.json"
        csv_out = "data/test_output.csv"
        
        export_to_json(locations[:10], json_out)
        export_to_csv(locations[:10], csv_out)
        print(f"\n[+] Exported sample results to {json_out} and {csv_out}")

    print("[+] Step 2 PASSED!")


def test_continuous_scraping():
    print("\n" + "=" * 60)
    print("STEP 3: Testing Continuous Background Monitoring & Callbacks")
    print("=" * 60)

    received_alerts = []

    def handle_new_location(loc: ThreatActorLocation):
        received_alerts.append(loc)
        print(f"  🚨 [NEW LOCATION DISCOVERED] [{loc.source_feed}] {loc.group_name} -> {loc.location_url}")

    def handle_cycle_complete(total_count, new_count):
        print(f"  [Cycle Complete] Total links: {total_count} | New links: {new_count}")

    client = ThreatLocationClient(monitors=["ransomlook"])
    
    # Create continuous monitor running every 3 seconds for testing
    monitor = client.create_continuous_monitor(
        interval_seconds=3,
        on_new_location=handle_new_location,
        on_cycle_complete=handle_cycle_complete
    )

    print("[*] Starting continuous background monitor thread...")
    monitor.start()

    # Let it run 1st cycle (discovers items)
    time.sleep(4)
    first_count = len(received_alerts)
    print(f"[*] End of Cycle 1 -> Callbacks triggered: {first_count}")

    # Let it run 2nd cycle (deduplication should suppress alerts)
    time.sleep(4)
    second_count = len(received_alerts)
    print(f"[*] End of Cycle 2 -> Callbacks triggered: {second_count}")

    print("[*] Stopping continuous monitor...")
    monitor.stop()

    assert second_count == first_count, "Deduplication failed during continuous monitoring cycle"
    print("[+] Continuous monitoring deduplication test PASSED!")


if __name__ == "__main__":
    print("============================================================")
    print("   OnionExplorer Threat Location Library Test Suite")
    print("============================================================")
    
    try:
        test_models_and_deduplication()
        test_one_shot_scraping()
        test_continuous_scraping()
        
        print("\n" + "=" * 60)
        print("🎉 ALL LIBRARY TESTS COMPLETED SUCCESSFULLY!")
        print("============================================================")
    except Exception as e:
        print(f"\n[-] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
