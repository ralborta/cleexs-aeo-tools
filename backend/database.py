"""
MySQL database for storing analysis results.
Uses aiomysql for async access.
Auto-creates database and tables on startup.
"""

import json
from typing import Optional

import aiomysql
from datetime import datetime, timezone

from config import MYSQL_HOST, MYSQL_PORT, MYSQL_DATABASE, MYSQL_USER, MYSQL_PASSWORD

_pool: Optional[aiomysql.Pool] = None


async def _get_pool() -> aiomysql.Pool:
    global _pool
    if _pool is None:
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
    """Create database (if not exists) and tables."""
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
    """Save a full analysis result."""
    pool = await _get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            now = datetime.now(timezone.utc).isoformat()
            await cur.execute(
                "INSERT INTO analyses (url, domain, overall_score, results_json, created_at) VALUES (%s, %s, %s, %s, %s)",
                (url, domain, overall_score, json.dumps(results, default=str), now),
            )


async def get_history(limit: int = 50) -> list:
    """Get recent analysis history."""
    pool = await _get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT id, url, domain, overall_score, created_at FROM analyses ORDER BY created_at DESC LIMIT %s",
                (limit,),
            )
            rows = await cur.fetchall()
            return list(rows)


async def get_analysis(analysis_id: int) -> Optional[dict]:
    """Get a full analysis result by ID."""
    pool = await _get_pool()
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
    """Get analysis history for a specific domain."""
    pool = await _get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT id, url, domain, overall_score, created_at FROM analyses WHERE domain = %s ORDER BY created_at DESC LIMIT %s",
                (domain, limit),
            )
            rows = await cur.fetchall()
            return list(rows)
