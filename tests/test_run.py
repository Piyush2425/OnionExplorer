"""
Quick Test Script for onion_explorer Library
Run this script to test both one-shot scraping and continuous background monitoring.
"""

import time
from onion_explorer import ThreatLocationClient

def main():
    print("=" * 60)
    print("1. TESTING ONE-SHOT SCRAPING")
    print("=" * 60)
    
    # Initialize client with RansomFeed & RansomLook monitors
    client = ThreatLocationClient(monitors=["ransomfeed", "ransomlook"])
    
    print("[*] Fetching location links...")
    locations = client.fetch_all_locations()
    print(f"[+] Total locations fetched: {len(locations)}")
    
    if locations:
        print(f"    Sample Location: [{locations[0].group_name}] -> {locations[0].location_url} ({locations[0].status})")

    print("\n" + "=" * 60)
    print("2. TESTING CONTINUOUS MONITORING (Running for 10 seconds)")
    print("=" * 60)

    # Callback when a new threat actor location is discovered
    def on_new_location(loc):
        print(f"  🚨 [NEW LOCATION ALERT] [{loc.source_feed}] {loc.group_name} -> {loc.location_url}")

    # Create continuous monitor with in-memory deduplication polling every 5 seconds
    monitor = client.create_continuous_monitor(
        interval_seconds=5,
        on_new_location=on_new_location
    )

    print("[*] Starting background continuous monitor thread...")
    monitor.start()
    
    # Let it run for 10 seconds to observe deduplication
    time.sleep(10)
    
    print("[*] Stopping continuous monitor...")
    monitor.stop()
    print("[+] Test completed successfully!")

if __name__ == "__main__":
    main()
