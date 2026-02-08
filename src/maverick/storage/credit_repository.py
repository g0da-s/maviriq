from uuid import uuid4

from maverick.storage.database import db_connection


class CreditTransactionRepository:
    async def record(
        self,
        user_id: str,
        amount: int,
        txn_type: str,
        stripe_session_id: str | None = None,
    ) -> None:
        txn_id = f"txn_{uuid4().hex[:12]}"
        async with db_connection() as db:
            await db.execute(
                """INSERT INTO credit_transactions (id, user_id, amount, type, stripe_session_id)
                   VALUES (?, ?, ?, ?, ?)""",
                (txn_id, user_id, amount, txn_type, stripe_session_id),
            )
            await db.commit()
