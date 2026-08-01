#!/usr/bin/env python3
"""
Telegram Link Status Checker
----------------------------
Utility to check if public Telegram invite links, channels, or groups are active
and check them in parallel for large-scale feeds.
"""

import os
import json
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import logging

logger = logging.getLogger("telegram_checker")

def check_telegram_link(url: str) -> bool:
    """
    Checks if a public Telegram channel, group, or invite link is active.
    Returns:
        True if active, False if taken down, nonexistent, or expired.
    """
    url = url.strip()
    if not url:
        return False
    if not url.startswith("http"):
        url = f"https://{url}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return False

        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Invite links
        is_invite = "/joinchat/" in url or "/+" in url

        if is_invite:
            page_text = soup.get_text().lower()
            if "expired" in page_text or "invalid" in page_text:
                return False
            if "invited" in page_text or "join group" in page_text or "join channel" in page_text or "view in telegram" in page_text:
                return True
            return False

        # Public usernames
        page_title = soup.find(class_="tgme_page_title")
        if not page_title:
            return False

        page_extra = soup.find(class_="tgme_page_extra")
        if page_extra:
            extra_text = page_extra.get_text().lower()
            if any(term in extra_text for term in ["member", "subscriber", "online"]):
                return True

        page_desc = soup.find(class_="tgme_page_description")
        if page_desc:
            desc_text = page_desc.get_text()
            if "If you have Telegram, you can contact" in desc_text and not page_extra:
                return False
            return True

        return False
    except Exception:
        return False

def check_all_telegram_links(json_path: str):
    """
    Reads the extracted JSON file, checks all telegram links in parallel,
    updates their status to Online/Offline, and writes it back.
    """
    if not os.path.exists(json_path):
        logger.warning(f"File not found: {json_path}")
        return

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Check if nested under "telegram_links" key or if it is the direct list
        if isinstance(data, dict) and "telegram_links" in data:
            telegram_links = data["telegram_links"]
        else:
            telegram_links = data

        if not telegram_links:
            logger.info("No Telegram links found to check.")
            return

        urls_to_check = []
        for key, entity in telegram_links.items():
            for loc in entity.get("locations", []):
                urls_to_check.append(loc)

        if not urls_to_check:
            return

        logger.info(f"Checking status for {len(urls_to_check)} Telegram links in parallel...")

        def worker(loc_dict):
            active = check_telegram_link(loc_dict["url"])
            loc_dict["available"] = active
            loc_dict["status"] = "Online" if active else "Offline"

        # Check up to 40 links concurrently
        with ThreadPoolExecutor(max_workers=40) as executor:
            executor.map(worker, urls_to_check)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info("[+] Telegram link status check finished.")
    except Exception as e:
        logger.error(f"Error checking Telegram links: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import sys
    if len(sys.argv) > 1:
        check_all_telegram_links(sys.argv[1])
    else:
        test_urls = [
            "https://t.me/telegram",
            "https://t.me/nonexistent_channel_1234567890"
        ]
        for u in test_urls:
            print(f"{u} -> {check_telegram_link(u)}")
