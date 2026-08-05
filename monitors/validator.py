import os
import time
import hashlib
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

log = logging.getLogger("OnionExplorer.Validator")

# Base directory for screenshots
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCREENSHOTS_DIR = os.path.join(BASE_DIR, "static", "screenshots")

os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

def scan_onion_url(url: str) -> dict:
    """
    Opens the given onion URL using a Tor proxy, takes a screenshot,
    and returns the relative path to the screenshot.
    """
    if not url:
        return {"error": "No URL provided"}

    # Generate a safe filename based on URL hash
    url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
    filename = f"{url_hash}.png"
    filepath = os.path.join(SCREENSHOTS_DIR, filename)
    relative_path = f"/static/screenshots/{filename}"

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # Tor proxy
    options.add_argument("--proxy-server=socks5://127.0.0.1:9050")
    # Ignore certificate errors for onions
    options.add_argument("--ignore-certificate-errors")
    
    # Set window size for a decent screenshot
    options.add_argument("--window-size=1280,1024")

    driver = None
    try:
        log.info(f"Starting Tor scan for URL: {url}")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        # Set page load timeout (Tor can be slow)
        driver.set_page_load_timeout(60)
        
        # Load the URL
        driver.get(url)
        
        # Wait a brief moment to ensure dynamic content might load (simple wait)
        time.sleep(5)
        
        # Take screenshot
        driver.save_screenshot(filepath)
        log.info(f"Successfully captured screenshot for {url} at {filepath}")
        
        return {
            "success": True,
            "screenshot_path": relative_path,
            "url": url
        }
    except Exception as e:
        log.error(f"Failed to scan {url}: {e}")
        return {
            "success": False,
            "error": str(e),
            "url": url
        }
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass
