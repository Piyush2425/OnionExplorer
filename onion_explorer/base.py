"""
Base Monitor Abstract Class & Connection Utilities
"""

from abc import ABC, abstractmethod
from typing import List, Generator, Optional, Dict
import requests
import logging

from .models import ThreatActorLocation

logger = logging.getLogger("onion_explorer")

class BaseMonitor(ABC):
    """Abstract Base Class for all feed monitors."""

    def __init__(self, proxy: Optional[str] = None, timeout: int = 20):
        self.proxy = proxy
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def get_session(self) -> requests.Session:
        """Create configured requests.Session with headers and optional proxy."""
        session = requests.Session()
        session.headers.update(self.headers)
        if self.proxy:
            session.proxies = {
                "http": self.proxy,
                "https": self.proxy
            }
        return session

    @property
    @abstractmethod
    def feed_name(self) -> str:
        """Name of the threat intelligence feed."""
        pass

    @abstractmethod
    def fetch_locations(self) -> List[ThreatActorLocation]:
        """Fetch all threat actor location URLs synchronously."""
        pass

    def stream_locations(self) -> Generator[ThreatActorLocation, None, None]:
        """Stream location URLs one by one as they are parsed."""
        for item in self.fetch_locations():
            yield item
