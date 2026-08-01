"""
RansomFeed.it Monitor Implementation
"""

import re
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional
import logging

from ..base import BaseMonitor
from ..models import ThreatActorLocation

logger = logging.getLogger("onion_explorer.monitors.ransomfeed")

BASE_URL = "https://www.ransomfeed.it/"
STATS_PAGE = "?page=stats&subpage=groups-stats"
PROFILE_PATH = "?page=stats&subpage=group-profile"

class RansomFeedMonitor(BaseMonitor):
    def __init__(self, proxy: Optional[str] = None, max_workers: int = 10, timeout: int = 20):
        super().__init__(proxy=proxy, timeout=timeout)
        self.max_workers = max_workers

    @property
    def feed_name(self) -> str:
        return "RansomFeed"

    def fetch_group_list(self, session: requests.Session) -> List[str]:
        """Fetch list of active threat actor groups from stats page."""
        url = f"{BASE_URL}{STATS_PAGE}"
        try:
            resp = session.get(url, timeout=self.timeout)
            resp.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to fetch RansomFeed stats page: {e}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        rows = soup.find_all("tr", attrs={"data-group": True})
        groups = []
        for row in rows:
            cells = row.find_all("td")
            if cells:
                name_tag = cells[0].find("a", class_="fw-semibold")
                group_name = name_tag.get_text(strip=True) if name_tag else ""
                if group_name:
                    groups.append(group_name)
        return groups

    def parse_profile_html(self, group_name: str, html: str) -> List[ThreatActorLocation]:
        """Parse source URLs and status from group profile page."""
        soup = BeautifulSoup(html, "html.parser")
        results = []
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if ".onion" not in href:
                continue

            status = "Unknown"
            version = ""

            # Detect status tags
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
                    version = f"v{version_match.group(1)}"

            # Extract FQDN
            fqdn_match = re.search(r'([a-z2-7]{16,56}\.onion)', href, re.IGNORECASE)
            fqdn = fqdn_match.group(1) if fqdn_match else ""

            results.append(ThreatActorLocation(
                group_name=group_name,
                location_url=href,
                source_feed=self.feed_name,
                fqdn=fqdn,
                url_type="leak_site",
                status=status,
                version=version
            ))

        return results

    def _fetch_one_profile(self, session: requests.Session, group_name: str) -> List[ThreatActorLocation]:
        url = f"{BASE_URL}{PROFILE_PATH}&group={group_name}"
        try:
            resp = session.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                return self.parse_profile_html(group_name, resp.text)
        except Exception as e:
            logger.warning(f"Error fetching profile for group {group_name}: {e}")
        return []

    def fetch_locations(self) -> List[ThreatActorLocation]:
        logger.info("[*] Scraping RansomFeed.it locations...")
        session = self.get_session()
        groups = self.fetch_group_list(session)
        if not groups:
            logger.warning("[-] No groups found on RansomFeed.it stats page.")
            return []

        all_locations = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_group = {
                executor.submit(self._fetch_one_profile, session, g): g for g in groups
            }
            for future in as_completed(future_to_group):
                try:
                    locations = future.result()
                    all_locations.extend(locations)
                except Exception as exc:
                    logger.debug(f"Failed fetching RansomFeed group profile: {exc}")

        logger.info(f"[+] RansomFeed.it scraped {len(all_locations)} location links across {len(groups)} groups.")
        return all_locations
