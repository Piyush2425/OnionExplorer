"""
Continuous Monitoring Engine
"""

import time
import threading
import logging
from typing import List, Callable, Optional
from ..base import BaseMonitor
from ..models import ThreatActorLocation
from .store import BaseStateStore, MemoryStateStore

logger = logging.getLogger("onion_explorer.runner")

class ContinuousMonitor:
    """Continuous background runner for threat location monitors."""

    def __init__(
        self,
        monitors: List[BaseMonitor],
        store: Optional[BaseStateStore] = None,
        interval_seconds: int = 1800,
        on_new_location: Optional[Callable[[ThreatActorLocation], None]] = None,
        on_status_change: Optional[Callable[[ThreatActorLocation, str, str], None]] = None,
        on_cycle_complete: Optional[Callable[[int, int], None]] = None,
        on_error: Optional[Callable[[Exception, str], None]] = None
    ):
        self.monitors = monitors
        self.store = store if store is not None else MemoryStateStore()
        self.interval_seconds = interval_seconds
        
        self.on_new_location = on_new_location
        self.on_status_change = on_status_change
        self.on_cycle_complete = on_cycle_complete
        self.on_error = on_error

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.is_running = False

    def run_once(self) -> List[ThreatActorLocation]:
        """Execute a single scrape cycle across all monitors."""
        all_discovered = []
        new_count = 0

        for monitor in self.monitors:
            if self._stop_event.is_set():
                break
            
            try:
                logger.info(f"[*] Executing scrape cycle for feed '{monitor.feed_name}'")
                locations = monitor.fetch_locations()
                all_discovered.extend(locations)

                for loc in locations:
                    old_status = self.store.get_status(loc)
                    is_new = self.store.add(loc)

                    if is_new:
                        new_count += 1
                        if self.on_new_location:
                            try:
                                self.on_new_location(loc)
                            except Exception as cb_err:
                                logger.error(f"Error in on_new_location callback: {cb_err}")

                    elif old_status and old_status != loc.status:
                        if self.on_status_change:
                            try:
                                self.on_status_change(loc, old_status, loc.status)
                            except Exception as cb_err:
                                logger.error(f"Error in on_status_change callback: {cb_err}")

            except Exception as e:
                logger.error(f"Error executing monitor {monitor.feed_name}: {e}")
                if self.on_error:
                    self.on_error(e, monitor.feed_name)

        if self.on_cycle_complete:
            try:
                self.on_cycle_complete(len(all_discovered), new_count)
            except Exception as cb_err:
                logger.error(f"Error in on_cycle_complete callback: {cb_err}")

        return all_discovered

    def _loop(self):
        logger.info(f"[+] Continuous monitor loop started (interval={self.interval_seconds}s)")
        self.is_running = True
        
        while not self._stop_event.is_set():
            self.run_once()
            
            # Wait for next interval in small slices so stop() is responsive
            slept = 0
            while slept < self.interval_seconds and not self._stop_event.is_set():
                time.sleep(1)
                slept += 1

        self.is_running = False
        logger.info("[+] Continuous monitor loop stopped.")

    def start(self, daemon: bool = True):
        """Start the continuous monitor in a background thread."""
        if self.is_running:
            logger.warning("[!] Continuous monitor is already running.")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=daemon)
        self._thread.start()

    def stop(self):
        """Stop the background continuous monitor thread."""
        logger.info("[*] Stopping continuous monitor...")
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)
