"""
CSV Exporter Utility
"""

import csv
from typing import List
from ..models import ThreatActorLocation

def export_to_csv(locations: List[ThreatActorLocation], filepath: str):
    fieldnames = [
        "group_name", "location_url", "source_feed", "fqdn", 
        "url_type", "status", "version", "discovered_at"
    ]
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for loc in locations:
            writer.writerow(loc.to_dict())
