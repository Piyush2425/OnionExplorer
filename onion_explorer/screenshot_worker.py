import os
import re
import time
import socket
import logging
import hashlib
import threading
from queue import Queue, Empty
from typing import Dict, Any

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

from onion_explorer.database import get_database

logger = logging.getLogger("OnionExplorer.ScreenshotWorker")

# Directory setup
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")
SCREENSHOTS_DIR = os.path.join(STATIC_DIR, "screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

# SOCKS5 Tor default ports
TOR_HOST = "127.0.0.1"
TOR_PORT = 9050

# Worker queue & task tracking
task_queue = Queue()
active_tasks = set()
tasks_lock = threading.Lock()
worker_thread = None
running = True

def is_tor_active() -> bool:
    """Test if SOCKS5 Tor proxy is listening on localhost."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1.5)
        s.connect((TOR_HOST, TOR_PORT))
        s.close()
        return True
    except Exception:
        return False

def get_url_md5(url: str) -> str:
    """Compute MD5 hex hash of a URL."""
    return hashlib.md5(url.encode("utf-8")).hexdigest()

def make_screenshot_driver(use_tor: bool = True) -> webdriver.Chrome:
    """Instantiate a headless Chrome web driver with optional SOCKS5 proxy configuration."""
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1200,750")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    )

    if use_tor:
        logger.info(f"Routing browser automation traffic via Tor SOCKS5 proxy ({TOR_HOST}:{TOR_PORT})...")
        opts.add_argument(f"--proxy-server=socks5://{TOR_HOST}:{TOR_PORT}")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    driver.set_page_load_timeout(45) # Long timeout for slow darkweb onions
    return driver

def capture_screenshot_task(entity_key: str, url: str) -> bool:
    """Loads a URL via Chrome driver, takes screenshot, and updates DB status."""
    use_tor = is_tor_active()
    if not use_tor:
        logger.warning(f"Tor SOCKS5 proxy not detected on {TOR_HOST}:{TOR_PORT}. Verification will fallback to direct connection.")

    md5_hash = get_url_md5(url)
    filename = f"{md5_hash}.png"
    save_path = os.path.join(SCREENSHOTS_DIR, filename)

    driver = None
    success = False
    status_val = "Offline"

    try:
        driver = make_screenshot_driver(use_tor=use_tor)
        logger.info(f"🚀 [Screenshot] Launching browser for: {url}")
        driver.get(url)
        
        # Give dynamic contents a few seconds to settle
        time.sleep(4)
        
        # Save screenshot
        driver.save_screenshot(save_path)
        logger.info(f"📸 [Screenshot] Successfully captured: {url} -> {save_path}")
        success = True
        status_val = "Online"
    except WebDriverException as wde:
        logger.error(f"❌ [Screenshot] Browser connection error for {url}: {wde}")
        # Delete stale screenshot on load failure
        if os.path.exists(save_path):
            try:
                os.remove(save_path)
            except Exception:
                pass
    except Exception as e:
        logger.error(f"❌ [Screenshot] Error capturing {url}: {e}")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    # Save to database
    try:
        db = get_database()
        db.update_location_screenshot(entity_key, url, filename if success else None, status_val)
        logger.info(f"💾 [Screenshot] Updated database for {url}: status={status_val}, screenshot={filename if success else None}")
    except Exception as dbe:
        logger.error(f"Failed to update database for location: {dbe}")

    return success

def queue_url_for_screenshot(entity_key: str, url: str, force: bool = False):
    """Adds a location URL to the verification and screenshot task queue."""
    if not url or not url.startswith("http"):
        return

    with tasks_lock:
        task_id = f"{entity_key}:{url}"
        if task_id in active_tasks and not force:
            logger.debug(f"Task already in queue or processing: {task_id}")
            return
        active_tasks.add(task_id)
        task_queue.put({"entity_key": entity_key, "url": url})
        logger.info(f"📥 [Screenshot Queue] Added task: {url}")

def worker_loop():
    """Background execution loop processing tasks sequentially."""
    global running
    logger.info("📟 Screenshot verification worker thread started.")
    
    while running:
        try:
            task = task_queue.get(timeout=2)
            entity_key = task["entity_key"]
            url = task["url"]
            
            try:
                capture_screenshot_task(entity_key, url)
            except Exception as loop_err:
                logger.error(f"Error executing screenshot task: {loop_err}")
            finally:
                with tasks_lock:
                    task_id = f"{entity_key}:{url}"
                    active_tasks.discard(task_id)
                task_queue.task_done()
        except Empty:
            continue
        except Exception as e:
            logger.error(f"Screenshot worker loop error: {e}")
            time.sleep(2)

def start_screenshot_worker():
    """Initializes and runs the screenshot queue worker thread."""
    global worker_thread, running
    running = True
    if worker_thread is None or not worker_thread.is_alive():
        worker_thread = threading.Thread(target=worker_loop, daemon=True, name="ScreenshotWorker")
        worker_thread.start()
        logger.info("✨ Screenshot worker thread launched.")

def stop_screenshot_worker():
    """Stops the screenshot queue worker thread gracefully."""
    global running, worker_thread
    running = False
    if worker_thread:
        worker_thread.join(timeout=5)
        worker_thread = None
        logger.info("🛑 Screenshot worker thread stopped.")
