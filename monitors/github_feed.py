#!/usr/bin/env python3
"""
GitHub Custom Threat Intelligence Feed Parser
--------------------------------------------
Flexible crawler that pulls from configured public GitHub files,
extracts v3 onion URLs, v2 onion URLs, and Telegram group/channel links via regex,
and normalizes them into sectors.
"""

import os
import re
import json
import requests
import logging

logger = logging.getLogger("github_feed")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")
GITHUB_DATA_PATH = os.path.join(DATA_DIR, "github_feed_extracted.json")
GITHUB_TELEGRAM_JSON = os.path.join(DATA_DIR, "github_telegram_links.json")
GITHUB_FORUMS_JSON = os.path.join(DATA_DIR, "github_forums_groups.json")
GITHUB_MARKETS_JSON = os.path.join(DATA_DIR, "github_markets.json")

ONION_V3_RE = re.compile(r'\b[a-z2-7]{56}\.onion\b', re.IGNORECASE)
ONION_V2_RE = re.compile(r'\b[a-z2-7]{16}\.onion\b', re.IGNORECASE)
TELEGRAM_RE = re.compile(r'\b(?:https?://)?(?:t\.me|telegram\.me)/(?:\+|joinchat/)?[a-z0-9_]{5,32}\b', re.IGNORECASE)

DEFAULT_CONFIG = {
    "github_feeds": [
        "https://raw.githubusercontent.com/fastfire/deepdarkCTI/main/forum.md",
        "https://raw.githubusercontent.com/fastfire/deepdarkCTI/main/markets.md",
        "https://raw.githubusercontent.com/fastfire/deepdarkCTI/main/telegram_threat_actors.md",
        "https://raw.githubusercontent.com/fastfire/deepdarkCTI/main/telegram_infostealer.md",
        "https://raw.githubusercontent.com/fastfire/deepdarkCTI/main/ransomware_gang.md"
    ]
}

def load_config():
    """Load config.json or create a default one."""
    if not os.path.exists(CONFIG_PATH):
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return DEFAULT_CONFIG

FEEDS_BACKUP_DIR = os.path.join(DATA_DIR, "feeds")

def get_raw_url(url: str) -> str:
    """Convert github.com HTML URL to raw.githubusercontent.com URL if needed."""
    url = url.strip()
    if "github.com" in url and "raw.githubusercontent.com" not in url:
        # Convert blob URLs: github.com/user/repo/blob/main/path -> raw.githubusercontent.com/user/repo/main/path
        url = url.replace("github.com", "raw.githubusercontent.com")
        url = url.replace("/blob/", "/")
    return url

def fetch_feed_data(url: str) -> str:
    """Fetch file content from GitHub raw URL, back up to local disk, and fallback if offline."""
    raw_url = get_raw_url(url)
    
    # Extract filename from URL
    filename = raw_url.split("/")[-1]
    if not filename.endswith(".md"):
        filename = f"{filename}.md"
        
    os.makedirs(FEEDS_BACKUP_DIR, exist_ok=True)
    local_path = os.path.join(FEEDS_BACKUP_DIR, filename)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        logger.info(f"Attempting to download feed from {raw_url}...")
        resp = requests.get(raw_url, headers=headers, timeout=20)
        resp.raise_for_status()
        
        # Save backup to local file
        with open(local_path, "w", encoding="utf-8") as f:
            f.write(resp.text)
        logger.info(f"Successfully downloaded and saved: {local_path}")
        return resp.text
    except Exception as e:
        logger.error(f"Failed to download GitHub feed from {url}: {e}")
        
        # Fallback to local cache
        if os.path.exists(local_path):
            logger.info(f"Using locally cached copy of the feed: {local_path}")
            try:
                with open(local_path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as read_err:
                logger.error(f"Failed to read locally cached feed {local_path}: {read_err}")
                
        return ""

def parse_extracted_links(text: str, source_url: str):
    """Scan content for onion links and Telegram links, returns sector dictionary."""
    results = {
        "forums_groups": {},
        "markets": {},
        "telegram_links": {}
    }

    # Extract clean filename as source tag (e.g. github:forum.md)
    filename = source_url.split("/")[-1]
    if not filename.endswith(".md"):
        filename = f"{filename}.md"
    src_tag = f"github:{filename}"

    source_url_lower = source_url.lower()
    lines = text.splitlines()

    # ── Option A: Telegram markdown table parser ──
    if "telegram_threat_actors" in source_url_lower or "telegram_infostealer" in source_url_lower:
        for line in lines:
            line = line.strip()
            if not line.startswith("|") or line.count("|") < 3:
                continue
            # Skip header indicator line (e.g. |---|)
            if "---" in line:
                continue
            
            parts = [p.strip() for p in line.split("|")]
            # Format: |Telegram Link|Status|Name|Type...
            if len(parts) < 4:
                continue
                
            tg_url = parts[1]
            status = parts[2]
            name = parts[3] if len(parts) > 3 else ""
            
            # Clean name
            name = re.sub(r'[*_`#|[\]()]', '', name).strip()
            
            # Check if valid Telegram link
            if not ("t.me/" in tg_url or "telegram.me/" in tg_url):
                continue
                
            tg_lower = tg_url.lower()
            if not tg_lower.startswith("http"):
                tg_lower = f"https://{tg_lower}"
                
            # If name is empty, extract from URL
            if not name:
                name = tg_url.split("/")[-1].replace("+", "Invite ")
                
            key = name.lower().strip()
            if not key:
                key = tg_url.split("/")[-1]
                
            # Determine initial availability based on status column in markdown
            available = (status.lower() in ["valid", "online", "active"])
            
            if key not in results["telegram_links"]:
                results["telegram_links"][key] = {
                    "name": name,
                    "locations": []
                }
                
            results["telegram_links"][key]["locations"].append({
                "fqdn": "",
                "url": tg_lower,
                "available": available,
                "last_visit": "",
                "server_info": "",
                "url_type": "telegram",
                "status": "Online" if available else "Offline",
                "source": src_tag
            })

    # ── Option B: Forum / Ransomware Gang / Market markdown table parser ──
    elif "forum.md" in source_url_lower or "ransomware_gang" in source_url_lower or "markets.md" in source_url_lower:
        for line in lines:
            line = line.strip()
            if not line.startswith("|") or line.count("|") < 3:
                continue
            if "---" in line:
                continue
                
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 3:
                continue
                
            col_name_url = parts[1]
            status = parts[2]
            
            # Extract [Name](URL) from first column
            match = re.search(r'\[([^\]]+)\]\(([^)]+)\)', col_name_url)
            if match:
                name = match.group(1).strip()
                url = match.group(2).strip()
            else:
                # Fallback: maybe just text name or raw URL
                name = col_name_url
                # Try to find a URL in parts
                url = ""
                for part in parts:
                    if "http" in part or ".onion" in part:
                        url = part.strip()
                        break
            
            if not url:
                continue
                
            # Clean name
            name = re.sub(r'[*_`#|[\]()]', '', name).strip()
            if not name:
                name = "GitHub Extracted Site"
                
            # Check if it is onion
            url_lower = url.lower()
            onion_match = ONION_V3_RE.search(url_lower) or ONION_V2_RE.search(url_lower)
            if not onion_match:
                if not url_lower.startswith("http"):
                    continue
                fqdn = url_lower.replace("https://", "").replace("http://", "").split("/")[0]
            else:
                fqdn = onion_match.group(0)
                if not url_lower.startswith("http"):
                    url = f"http://{url}"

            # Categorize: if market or shop in name/url, put in markets, else forums_groups
            category = "forums_groups"
            if any(term in name.lower() or term in url_lower for term in ["market", "shop", "marketplace"]) or "markets.md" in source_url_lower:
                category = "markets"
                
            key = name.lower().strip()
            available = (status.lower() in ["valid", "online", "active"])
            
            if key not in results[category]:
                results[category][key] = {
                    "name": name,
                    "locations": []
                }
                
            results[category][key]["locations"].append({
                "fqdn": fqdn,
                "url": url,
                "available": available,
                "last_visit": "",
                "server_info": "",
                "url_type": "market" if category == "markets" else "leak_site",
                "status": "Online" if available else "Offline",
                "source": src_tag
            })

    # ── Option C: General Regex Fallback ──
    else:
        # Fallback to general regex parsing
        onions_v3 = ONION_V3_RE.findall(text)
        for onion in set(onions_v3):
            onion_lower = onion.lower()
            name = "GitHub Extracted Site"
            for line in lines:
                if onion in line:
                    clean_line = re.sub(r'[*_`#\-|[\]()]', ' ', line)
                    clean_line = clean_line.replace(onion, '').strip()
                    words = [w for w in clean_line.split() if len(w) > 2][:3]
                    if words: name = " ".join(words)
                    break
            
            key = name.lower().strip()
            if not key: key = onion_lower[:16]
            category = "forums_groups"
            if any(term in onion_lower or term in name.lower() for term in ["market", "shop", "marketplace"]):
                category = "markets"
                
            if key not in results[category]:
                results[category][key] = {"name": name, "locations": []}
            results[category][key]["locations"].append({
                "fqdn": onion_lower,
                "url": f"http://{onion_lower}",
                "available": False,
                "last_visit": "",
                "server_info": "",
                "url_type": "market" if category == "markets" else "leak_site",
                "status": "Not scanned yet",
                "source": src_tag
            })

        telegrams = TELEGRAM_RE.findall(text)
        for tg_url in set(telegrams):
            tg_lower = tg_url.lower()
            if not tg_lower.startswith("http"):
                tg_lower = f"https://{tg_lower}"
            name = "GitHub Telegram Group"
            for line in lines:
                if tg_url in line:
                    clean_line = re.sub(r'[*_`#\-|[\]()]', ' ', line)
                    clean_line = clean_line.replace(tg_url, '').strip()
                    words = [w for w in clean_line.split() if len(w) > 2][:3]
                    if words: name = " ".join(words)
                    break
            key = name.lower().strip()
            if not key: key = tg_url.split("/")[-1]
            if key not in results["telegram_links"]:
                results["telegram_links"][key] = {"name": name, "locations": []}
            results["telegram_links"][key]["locations"].append({
                "fqdn": "",
                "url": tg_lower,
                "available": False,
                "last_visit": "",
                "server_info": "",
                "url_type": "telegram",
                "status": "Not scanned yet",
                "source": src_tag
            })

    return results

def scrape_and_save_github_feeds():
    """Scrape all configured GitHub feeds, extract urls, and save output JSON."""
    config = load_config()
    feeds = config.get("github_feeds", [])
    
    combined = {
        "forums_groups": {},
        "markets": {},
        "telegram_links": {}
    }

    for feed_url in feeds:
        logger.info(f"Scraping GitHub feed: {feed_url}")
        content = fetch_feed_data(feed_url)
        if not content:
            continue
        
        parsed = parse_extracted_links(content, feed_url)
        # Merge results
        for sector in ["forums_groups", "markets", "telegram_links"]:
            for key, val in parsed[sector].items():
                if key not in combined[sector]:
                    combined[sector][key] = val
                else:
                    # Append unique locations
                    existing_urls = [l["url"] for l in combined[sector][key]["locations"]]
                    for loc in val["locations"]:
                        if loc["url"] not in existing_urls:
                            combined[sector][key]["locations"].append(loc)

    with open(GITHUB_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)
    with open(GITHUB_TELEGRAM_JSON, "w", encoding="utf-8") as f:
        json.dump(combined["telegram_links"], f, indent=2, ensure_ascii=False)
    with open(GITHUB_FORUMS_JSON, "w", encoding="utf-8") as f:
        json.dump(combined["forums_groups"], f, indent=2, ensure_ascii=False)
    with open(GITHUB_MARKETS_JSON, "w", encoding="utf-8") as f:
        json.dump(combined["markets"], f, indent=2, ensure_ascii=False)
    
    # Count stats
    tg_count = sum(len(v["locations"]) for v in combined["telegram_links"].values())
    onion_count = sum(len(v["locations"]) for v in combined["forums_groups"].values())
    market_count = sum(len(v["locations"]) for v in combined["markets"].values())
    
    logger.info(f"GitHub feed extraction complete. Saved to {GITHUB_DATA_PATH}.")
    logger.info(f"  Extracted: {onion_count} onion links, {market_count} market links, {tg_count} Telegram links")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scrape_and_save_github_feeds()
