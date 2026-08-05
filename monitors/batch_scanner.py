import os
import time
import json
import hashlib
import logging
from playwright.sync_api import sync_playwright

log = logging.getLogger("OnionExplorer.BatchScanner")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCREENSHOTS_DIR = os.path.join(BASE_DIR, "static", "screenshots")
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_FILE = os.path.join(DATA_DIR, "scan_results.json")

os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            log.error(f"Error loading DB: {e}")
    return {}

def save_db(db):
    try:
        with open(DB_FILE, "w") as f:
            json.dump(db, f, indent=4)
    except Exception as e:
        log.error(f"Error saving DB: {e}")

def run_batch_scan(urls):
    """
    Runs a batch scan over a list of URLs using Playwright Firefox and Tor.
    Updates the local JSON database with the results.
    """
    db = load_db()
    
    with sync_playwright() as p:
        # Launch Firefox with Tor Proxy
        browser = p.firefox.launch(
            headless=True,
            proxy={"server": "socks5://127.0.0.1:9050"}
        )
        context = browser.new_context(ignore_https_errors=True)
        
        for url in urls:
            if not url or not (".onion" in url):
                continue
                
            log.info(f"Scanning: {url}")
            url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
            filename = f"{url_hash}.png"
            filepath = os.path.join(SCREENSHOTS_DIR, filename)
            relative_path = f"/static/screenshots/{filename}"
            
            try:
                page = context.new_page()
                # Set timeout to 60 seconds because Tor is slow
                page.goto(url, timeout=60000, wait_until="domcontentloaded")
                # Wait an extra 5 seconds for rendering
                page.wait_for_timeout(5000)
                
                page.screenshot(path=filepath, full_page=True)
                log.info(f"Success: {url}")
                
                db[url] = {
                    "status": "Online",
                    "last_scan": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "screenshot": relative_path,
                    "error": None
                }
            except Exception as e:
                log.warning(f"Failed to scan {url}: {e}")
                db[url] = {
                    "status": "Offline",
                    "last_scan": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "screenshot": None,
                    "error": str(e)
                }
            finally:
                page.close()
                # Save after each URL in case of crash
                save_db(db)
                
        browser.close()
    
    log.info("Batch scan completed.")
    return db
