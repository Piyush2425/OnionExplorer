#!/usr/bin/env python3
"""
onion — CLI entry point for OnionExplorer
Usage:
    onion serve
"""
import sys
from main import app, start_background_scraper, sync_data_to_database
import logging

def serve():
    log = logging.getLogger("OnionExplorer")
    log.info("=" * 50)
    log.info("OnionExplorer Dashboard")
    log.info("  Server: http://localhost:5000")
    log.info("=" * 50)

    try:
        sync_data_to_database()
    except Exception as e:
        log.error(f"Initial database sync error: {e}")

    start_background_scraper()
    app.run(debug=False, host="0.0.0.0", port=5000)

def main():
    if len(sys.argv) < 2 or sys.argv[1] != "serve":
        print("Usage: onion serve")
        sys.exit(1)
    serve()

if __name__ == "__main__":
    main()
