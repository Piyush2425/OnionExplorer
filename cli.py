#!/usr/bin/env python3
"""
onion — CLI entry point for OnionExplorer
Usage:
    onion serve
"""
import sys
import os
import signal
import subprocess
import threading
import time
from main import app, start_background_scraper, sync_data_to_database
import logging

def serve():
    log = logging.getLogger("OnionExplorer")
    log.info("=" * 60)
    log.info("🧅 OnionExplorer — Threat Intelligence System")
    log.info("  Backend REST API : http://127.0.0.1:5000")
    log.info("  Frontend Console : http://localhost:5173")
    log.info("=" * 60)

    try:
        sync_data_to_database()
    except Exception as e:
        log.error(f"Initial database sync error: {e}")

    # Launch SvelteKit dev server in the background
    frontend_proc = None
    def start_frontend():
        nonlocal frontend_proc
        try:
            # Use shell=True to support both windows npm.cmd and linux npm
            frontend_proc = subprocess.Popen(
                "npm run dev",
                shell=True,
                cwd="frontend",
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=None if os.name == 'nt' else os.setsid
            )
            log.info("✨ SvelteKit Dev Server started on port 5173.")
        except Exception as err:
            log.error(f"❌ Failed to launch SvelteKit dev server: {err}")

    t = threading.Thread(target=start_frontend, daemon=True)
    t.start()

    start_background_scraper()
    
    try:
        app.run(debug=False, host="0.0.0.0", port=5000)
    finally:
        if frontend_proc:
            log.info("🛑 Stopping SvelteKit dev server...")
            try:
                if os.name == 'nt':
                    subprocess.run(f"taskkill /F /T /PID {frontend_proc.pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    os.killpg(os.getpgid(frontend_proc.pid), signal.SIGTERM)
            except Exception:
                try:
                    frontend_proc.terminate()
                except Exception:
                    pass

def main():
    if len(sys.argv) < 2 or sys.argv[1] != "serve":
        print("Usage: onion serve")
        sys.exit(1)
    serve()

if __name__ == "__main__":
    main()
