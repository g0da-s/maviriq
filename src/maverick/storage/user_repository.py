from uuid import uuid4

from maverick.storage.database import db_connection


class UserRepository:
    async def create(self, email: str, password_hash: str) -> dict:
        user_id = f"usr_{uuid4().hex[:12]}"
        async with db_connection() as db:
            await db.execute(
                "INSERT INTO users (id, email, password_hash) VALUES (?, ?, ?)",
                (user_id, email, password_hash),
            )
            await db.commit()
            cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = await cursor.fetchone()
            return dict(row)

    async def get_by_email(self, email: str) -> dict | None:
        async with db_connection() as db:
            cursor = await db.execute("SELECT * FROM users WHERE email = ?", (email,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_by_id(self, user_id: str) -> dict | None:
        async with db_connection() as db:
            cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def deduct_credit(self, user_id: str) -> bool:
        """Atomically deduct 1 credit. Returns False if insufficient."""
        async with db_connection() as db:
            cursor = await db.execute(
                "UPDATE users SET credits = credits - 1 WHERE id = ? AND credits > 0",
                (user_id,),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def add_credits(self, user_id: str, amount: int) -> None:
        async with db_connection() as db:
            await db.execute(
                "UPDATE users SET credits = credits + ? WHERE id = ?",
                (amount, user_id),
            )
            await db.commit()
