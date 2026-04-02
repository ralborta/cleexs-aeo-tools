"""
Shared HTTP client configuration for all crawling tools.
Uses a realistic browser User-Agent and proper SSL/timeout settings.
"""

import os
import socket
import ssl

import aiohttp
import certifi

# Realistic browser User-Agent — prevents bot-blocking by servers
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

# Sin "br": en muchos entornos (Railway/Docker) falta brotli y aiohttp falla al leer respuestas br.
# Si necesitas br, instala el paquete `brotli` y vuelve a añadir "br" aquí.
DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "es,en-US;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Referer": "https://www.google.com/",
    "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Upgrade-Insecure-Requests": "1",
}


def create_session(timeout: int = 20, max_connections: int = 10) -> tuple:
    """Return (connector, timeout_config, headers) for aiohttp.ClientSession."""
    ssl_ctx = ssl.create_default_context(cafile=certifi.where())
    # IPv6 roto en algunos hosts cloud → ClientConnectorError (errno 0, message '') .
    # Desactivar con HTTP_IPV4_ONLY=0 si necesitas IPv6 explícito.
    ipv4_only = os.getenv("HTTP_IPV4_ONLY", "1").strip().lower() in ("1", "true", "yes", "on")
    fam = socket.AF_INET if ipv4_only else 0
    connector = aiohttp.TCPConnector(limit=max_connections, ssl=ssl_ctx, family=fam)
    timeout_config = aiohttp.ClientTimeout(total=timeout)
    return connector, timeout_config, DEFAULT_HEADERS