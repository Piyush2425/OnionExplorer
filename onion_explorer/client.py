"""
Unified ThreatLocationClient Facade
"""

from typing import List, Generator, Optional, Callable, Union
import logging

from .models import ThreatActorLocation
from .base import BaseMonitor
from .monitors import RansomFeedMonitor, RansomwareLiveMonitor, RansomLookMonitor
from .engine import ContinuousMonitor, BaseStateStore, MemoryStateStore, SQLiteStateStore

logger = logging.getLogger("onion_explorer.client")

class ThreatLocationClient:
    """Primary entry point for the OnionExplorer threat location library."""

    MONITOR_MAP = {
        "ransomfeed": RansomFeedMonitor,
        "ransomware_live": RansomwareLiveMonitor,
        "ransomlook": RansomLookMonitor
    }

    def __init__(
        self,
        monitors: Optional[List[Union[str, BaseMonitor]]] = None,
        proxy: Optional[str] = None,
        timeout: int = 20
    ):
        self.proxy = proxy
        self.timeout = timeout
        self.active_monitors: List[BaseMonitor] = []

        if monitors is None:
            # Default to all monitors
            monitors = list(self.MONITOR_MAP.keys())

        for item in monitors:
            if isinstance(item, BaseMonitor):
                self.active_monitors.append(item)
            elif isinstance(item, str) and item.lower() in self.MONITOR_MAP:
                monitor_cls = self.MONITOR_MAP[item.lower()]
                self.active_monitors.append(monitor_cls(proxy=self.proxy, timeout=self.timeout))
            else:
                logger.warning(f"Unknown monitor specified: {item}")

    def fetch_all_locations(self) -> List[ThreatActorLocation]:
        """Scrape all locations across configured monitors once."""
        results = []
        for monitor in self.active_monitors:
            try:
                results.extend(monitor.fetch_locations())
            except Exception as e:
                logger.error(f"Error fetching from monitor {monitor.feed_name}: {e}")
        return results

    def export_online_locations_to_csv(self, filepath: str) -> List[ThreatActorLocation]:
        """Fetch all locations, filter for status == 'Online', and export them to a CSV file."""
        from .exporters.csv_exporter import export_to_csv
        locations = self.fetch_all_locations()
        online_locations = [loc for loc in locations if loc.status == "Online"]
        export_to_csv(online_locations, filepath)
        return online_locations

    def stream_locations(self) -> Generator[ThreatActorLocation, None, None]:
        """Stream locations as they are scraped across monitors."""
        for monitor in self.active_monitors:
            try:
                yield from monitor.stream_locations()
            except Exception as e:
                logger.error(f"Error streaming from monitor {monitor.feed_name}: {e}")

    def create_continuous_monitor(
        self,
        interval_seconds: int = 1800,
        store: Optional[BaseStateStore] = None,
        use_sqlite: bool = False,
        sqlite_path: str = "threat_locations_state.db",
        on_new_location: Optional[Callable[[ThreatActorLocation], None]] = None,
        on_status_change: Optional[Callable[[ThreatActorLocation, str, str], None]] = None,
        on_cycle_complete: Optional[Callable[[int, int], None]] = None,
        on_error: Optional[Callable[[Exception, str], None]] = None
    ) -> ContinuousMonitor:
        """Construct a continuous background monitor instance."""
        if store is None:
            if use_sqlite:
                store = SQLiteStateStore(db_path=sqlite_path)
            else:
                store = MemoryStateStore()

        return ContinuousMonitor(
            monitors=self.active_monitors,
            store=store,
            interval_seconds=interval_seconds,
            on_new_location=on_new_location,
            on_status_change=on_status_change,
            on_cycle_complete=on_cycle_complete,
            on_error=on_error
        )
