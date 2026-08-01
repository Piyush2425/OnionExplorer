"""
Ransomware.live Monitor Implementation
"""

import re
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional
import logging

from ..base import BaseMonitor
from ..models import ThreatActorLocation

logger = logging.getLogger("onion_explorer.monitors.ransomware_live")

BASE_URL = "https://www.ransomware.live"
GROUPS_PAGE = "/groups"

class RansomwareLiveMonitor(BaseMonitor):
    def __init__(self, proxy: Optional[str] = None, max_workers: int = 10, timeout: int = 20):
        super().__init__(proxy=proxy, timeout=timeout)
        self.max_workers = max_workers

    @property
    def feed_name(self) -> str:
        return "Ransomware.live"

    def fetch_group_list(self, session: requests.Session) -> List[Dict[str, str]]:
        url = f"{BASE_URL}{GROUPS_PAGE}"
        try:
            resp = session.get(url, timeout=self.timeout)
            resp.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to fetch Ransomware.live groups page: {e}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.find_all("li", class_="rl-group-item")
        groups = []
        for item in items:
            link = item.find("a", href=True)
            if not link:
                continue
            href = link.get("href", "")
            if "/group/" not in href:
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

    def parse_group_page(self, group_name: str, html: str) -> List[ThreatActorLocation]:
        soup = BeautifulSoup(html, "html.parser")
        results = []

        # Look for Known Locations table or links
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if ".onion" not in href and not href.startswith("http"):
                continue

            if ".onion" not in href and "telegram" not in href.lower():
                continue

            url_type = "telegram" if "telegram" in href.lower() or "t.me" in href.lower() else "leak_site"
            status = "Unknown"
            
            # Check row status if inside a table row
            tr = a.find_parent("tr")
            if tr:
                row_text = tr.get_text()
                if "online" in row_text.lower() or "active" in row_text.lower():
                    status = "Online"
                elif "offline" in row_text.lower():
                    status = "Offline"

            fqdn_match = re.search(r'([a-z2-7]{16,56}\.onion)', href, re.IGNORECASE)
            fqdn = fqdn_match.group(1) if fqdn_match else ""

            results.append(ThreatActorLocation(
                group_name=group_name,
                location_url=href,
                source_feed=self.feed_name,
                fqdn=fqdn,
                url_type=url_type,
                status=status
            ))

        return results

    def _fetch_one_group(self, session: requests.Session, group: Dict[str, str]) -> List[ThreatActorLocation]:
        url = f"{BASE_URL}/group/{group['slug']}"
        try:
            resp = session.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                return self.parse_group_page(group['name'], resp.text)
        except Exception as e:
            logger.warning(f"Error fetching Ransomware.live group profile {group['slug']}: {e}")
        return []

    def fetch_locations(self) -> List[ThreatActorLocation]:
        logger.info("[*] Scraping Ransomware.live locations...")
        session = self.get_session()
        groups = self.fetch_group_list(session)
        if not groups:
            logger.warning("[-] No groups found on Ransomware.live.")
            return []

        all_locations = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_group = {
                executor.submit(self._fetch_one_group, session, g): g for g in groups
            }
            for future in as_completed(future_to_group):
                try:
                    locations = future.result()
                    all_locations.extend(locations)
                except Exception as exc:
                    logger.debug(f"Failed fetching Ransomware.live profile: {exc}")

        logger.info(f"[+] Ransomware.live scraped {len(all_locations)} location links across {len(groups)} groups.")
        return all_locations
