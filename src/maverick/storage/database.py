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

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    credits INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS credit_transactions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    amount INTEGER NOT NULL,
    type TEXT NOT NULL,
    stripe_session_id TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
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
        # Migration: add user_id to validation_runs if not present
        try:
            await db.execute(
                "ALTER TABLE validation_runs ADD COLUMN user_id TEXT REFERENCES users(id)"
            )
            await db.commit()
        except Exception:
            pass  # Column already exists
