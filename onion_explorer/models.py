"""
OnionExplorer Models
--------------------
Standardized dataclasses representing scraped threat actor locations.
"""

from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Dict, Any, Optional

@dataclass
class ThreatActorLocation:
    group_name: str
    location_url: str
    source_feed: str
    fqdn: str = ""
    url_type: str = "leak_site"        # leak_site, negotiation_portal, telegram, mirror
    status: str = "Unknown"             # Online, Offline, Unknown
    version: str = ""                  # v2, v3
    discovered_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    raw_metadata: Dict[str, Any] = field(default_factory=dict)
    sector: str = ""                   # forums_groups, markets, telegram_links

    def __post_init__(self):
        if not self.sector:
            if self.url_type == "telegram" or "t.me" in self.location_url.lower():
                self.sector = "telegram_links"
            elif self.url_type == "market":
                self.sector = "markets"
            else:
                self.sector = "forums_groups"

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ThreatActorLocation":
        """Create model instance from dictionary."""
        loc_url = data.get("location_url", data.get("url", ""))
        url_type = data.get("url_type", "leak_site")
        sector = data.get("sector", "")
        
        # Auto-detect sector
        if not sector:
            if url_type == "telegram" or "t.me" in loc_url.lower():
                sector = "telegram_links"
            elif data.get("type") == "market" or url_type == "market":
                sector = "markets"
            else:
                sector = "forums_groups"

        return cls(
            group_name=data.get("group_name", data.get("group", "")),
            location_url=loc_url,
            source_feed=data.get("source_feed", "unknown"),
            fqdn=data.get("fqdn", ""),
            url_type=url_type,
            status=data.get("status", "Unknown"),
            version=str(data.get("version", "")),
            discovered_at=data.get("discovered_at", datetime.utcnow().isoformat()),
            raw_metadata=data.get("raw_metadata", {}),
            sector=sector
        )

    @property
    def unique_key(self) -> str:
        """Unique key representation for deduplication."""
        clean_url = self.location_url.strip().rstrip("/").lower()
        clean_group = self.group_name.strip().lower()
        return f"{clean_group}::{clean_url}"
