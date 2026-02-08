from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import aiosqlite

DB_PATH = "maverick.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS validation_runs (
    id TEXT PRIMARY KEY,
    idea TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    current_agent INTEGER DEFAULT 0,
    started_at TEXT,
    completed_at TEXT,
    error TEXT,
    pain_discovery_output TEXT,
    competitor_research_output TEXT,
    viability_output TEXT,
    synthesis_output TEXT,
    total_cost_cents INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS search_cache (
    query_hash TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    query TEXT NOT NULL,
    response TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at TEXT NOT NULL
);
"""


async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db


@asynccontextmanager
async def db_connection() -> AsyncGenerator[aiosqlite.Connection]:
    db = await get_db()
    try:
        yield db
    finally:
        await db.close()


async def init_db() -> None:
    async with db_connection() as db:
        await db.executescript(SCHEMA)
        await db.commit()
