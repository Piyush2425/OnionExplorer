"""
JSON Exporter Utility
"""

import json
from typing import List
from ..models import ThreatActorLocation

def export_to_json(locations: List[ThreatActorLocation], filepath: str, indent: int = 2):
    data = [loc.to_dict() for loc in locations]
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)
