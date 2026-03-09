"""
MySQL database for storing analysis results.
Uses aiomysql for async access when SKIP_DB is not set.
With SKIP_DB=1, aiomysql is not imported (evita fallos de dependencia en Railway).
"""

import json
from typing import Optional, Any

from datetime import datetime, timezone

from config import (
    MYSQL_HOST,
    MYSQL_PORT,
    MYSQL_DATABASE,
    MYSQL_USER,
    MYSQL_PASSWORD,
    SKIP_DB,
)

_pool: Optional[Any] = None


def _get_aiomysql():
    """Import aiomysql solo cuando se usa DB (evita fallo al arrancar con SKIP_DB=1)."""
    import aiomysql
    return aiomysql


async def _get_pool():
    global _pool
    if _pool is None:
        aiomysql = _get_aiomysql()
        _pool = await aiomysql.create_pool(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            db=MYSQL_DATABASE,
            charset="utf8mb4",
            autocommit=True,
            minsize=1,
            maxsize=10,
        )
    return _pool


async def init_db():
    """Create database (if not exists) and tables. No-op if SKIP_DB=1."""
    if SKIP_DB:
        return
    aiomysql = _get_aiomysql()
    # First connect without specifying a database to create it
    conn = await aiomysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        charset="utf8mb4",
    )
    try:
        async with conn.cursor() as cur:
            await cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DATABASE}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
    finally:
        conn.close()

    # Now connect to the database and create tables
    pool = await _get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS analyses (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    url VARCHAR(2048) NOT NULL,
                    domain VARCHAR(255) NOT NULL,
                    overall_score INT DEFAULT 0,
                    results_json LONGTEXT NOT NULL,
                    created_at VARCHAR(64) NOT NULL,
                    INDEX idx_analyses_domain (domain),
                    INDEX idx_analyses_created (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)


async def save_analysis(url: str, domain: str, overall_score: int, results: dict):
    """Save a full analysis result. No-op if SKIP_DB=1."""
    if SKIP_DB:
        return
    pool = await _get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            now = datetime.now(timezone.utc).isoformat()
            await cur.execute(
                "INSERT INTO analyses (url, domain, overall_score, results_json, created_at) VALUES (%s, %s, %s, %s, %s)",
                (url, domain, overall_score, json.dumps(results, default=str), now),
            )


async def get_history(limit: int = 50) -> list:
    """Get recent analysis history. Returns [] if SKIP_DB=1."""
    if SKIP_DB:
        return []
    pool = await _get_pool()
    async with pool.acquire() as conn:
        aiomysql = _get_aiomysql()
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT id, url, domain, overall_score, created_at FROM analyses ORDER BY created_at DESC LIMIT %s",
                (limit,),
            )
            rows = await cur.fetchall()
            return list(rows)


async def get_analysis(analysis_id: int) -> Optional[dict]:
    """Get a full analysis result by ID. Returns None if SKIP_DB=1."""
    if SKIP_DB:
        return None
    pool = await _get_pool()
    aiomysql = _get_aiomysql()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT * FROM analyses WHERE id = %s",
                (analysis_id,),
            )
            row = await cur.fetchone()
            if row:
                result = dict(row)
                result["results"] = json.loads(result["results_json"])
                del result["results_json"]
                return result
            return None


async def get_domain_history(domain: str, limit: int = 20) -> list:
    """Get analysis history for a specific domain. Returns [] if SKIP_DB=1."""
    if SKIP_DB:
        return []
    pool = await _get_pool()
    aiomysql = _get_aiomysql()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT id, url, domain, overall_score, created_at FROM analyses WHERE domain = %s ORDER BY created_at DESC LIMIT %s",
                (domain, limit),
            )
            rows = await cur.fetchall()
            return list(rows)
