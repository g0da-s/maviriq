from uuid import uuid4

from maverick.supabase_client import get_supabase


class CreditTransactionRepository:
    async def record(
        self,
        user_id: str,
        amount: int,
        txn_type: str,
        stripe_session_id: str | None = None,
    ) -> None:
        txn_id = f"txn_{uuid4().hex[:12]}"
        sb = await get_supabase()
        await (
            sb.table("credit_transactions")
            .insert(
                {
                    "id": txn_id,
                    "user_id": user_id,
                    "amount": amount,
                    "type": txn_type,
                    "stripe_session_id": stripe_session_id,
                }
            )
            .execute()
        )
