"""
RansomLook.io Monitor Implementation
"""

import requests
from typing import List, Dict, Optional
import logging

from ..base import BaseMonitor
from ..models import ThreatActorLocation

logger = logging.getLogger("onion_explorer.monitors.ransomlook")

BASE_URL = "https://www.ransomlook.io/api"

class RansomLookMonitor(BaseMonitor):
    def __init__(self, proxy: Optional[str] = None, timeout: int = 20):
        super().__init__(proxy=proxy, timeout=timeout)

    @property
    def feed_name(self) -> str:
        return "RansomLook"

    def fetch_entity_locations(self, session: requests.Session, entity_name: str, entity_type: str = "group") -> List[ThreatActorLocation]:
        endpoint = "group" if entity_type == "group" else "market"
        url = f"{BASE_URL}/{endpoint}/{entity_name}"
        try:
            resp = session.get(url, timeout=self.timeout, verify=False)
            if resp.status_code != 200:
                return []
            data = resp.json()
            if not isinstance(data, list) or not data:
                return []
            
            entry = data[0]
            if not isinstance(entry, dict) or "locations" not in entry:
                return []

            results = []
            for loc in entry["locations"]:
                slug_url = loc.get("slug", "")
                fqdn = loc.get("fqdn", "")
                target_url = slug_url if slug_url else f"http://{fqdn}"
                if not target_url:
                    continue

                available = loc.get("available", False)
                status = "Online" if available else "Offline"
                version_val = loc.get("version", "")
                version = f"v{version_val}" if version_val else ""

                results.append(ThreatActorLocation(
                    group_name=entity_name,
                    location_url=target_url,
                    source_feed=self.feed_name,
                    fqdn=fqdn,
                    url_type="market" if entity_type == "market" else "leak_site",
                    status=status,
                    version=version,
                    raw_metadata={"lastscrape": loc.get("lastscrape", "")}
                ))

            return results
        except Exception as e:
            logger.debug(f"Error fetching RansomLook entity {entity_name}: {e}")
            return []

    def fetch_locations(self) -> List[ThreatActorLocation]:
        logger.info("[*] Scraping RansomLook.io API...")
        session = self.get_session()
        
        all_locations = []
        try:
            # Disable SSL warnings for RansomLook expired certs
            requests.packages.urllib3.disable_warnings() # type: ignore

            # Fetch group list
            groups_resp = session.get(f"{BASE_URL}/groups", timeout=self.timeout, verify=False)
            if groups_resp.status_code == 200:
                groups = groups_resp.json()
                if isinstance(groups, list):
                    for g in groups:
                        all_locations.extend(self.fetch_entity_locations(session, g, entity_type="group"))

            # Fetch market list
            markets_resp = session.get(f"{BASE_URL}/markets", timeout=self.timeout, verify=False)
            if markets_resp.status_code == 200:
                markets = markets_resp.json()
                if isinstance(markets, list):
                    for m in markets:
                        all_locations.extend(self.fetch_entity_locations(session, m, entity_type="market"))

        except Exception as e:
            logger.error(f"Error scraping RansomLook: {e}")

        logger.info(f"[+] RansomLook.io scraped {len(all_locations)} location links.")
        return all_locations
