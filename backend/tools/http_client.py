"""
Shared HTTP client configuration for all crawling tools.
Uses a realistic browser User-Agent and proper SSL/timeout settings.
"""

import aiohttp
import ssl
import certifi

# Realistic browser User-Agent — prevents bot-blocking by servers
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
}


def create_session(timeout: int = 20, max_connections: int = 10) -> tuple:
    """Return (connector, timeout_config, headers) for aiohttp.ClientSession."""
    ssl_ctx = ssl.create_default_context(cafile=certifi.where())
    connector = aiohttp.TCPConnector(limit=max_connections, ssl=ssl_ctx)
    timeout_config = aiohttp.ClientTimeout(total=timeout)
    return connector, timeout_config, DEFAULT_HEADERS