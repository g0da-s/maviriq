import logging
from uuid import uuid4

from maviriq.storage import DatabaseError
from maviriq.supabase_client import get_supabase

logger = logging.getLogger(__name__)


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
        try:
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
        except Exception as e:
            logger.exception("Failed to record credit transaction for user")
            raise DatabaseError(str(e)) from e

    async def deduct_credit_with_txn(self, user_id: str, txn_type: str) -> bool:
        """Atomically deduct 1 credit and record the transaction.

        Returns True if the credit was deducted, False if insufficient credits.
        """
        sb = await get_supabase()
        try:
            result = await sb.rpc(
                "deduct_credit_with_txn",
                {"p_user_id": user_id, "p_txn_type": txn_type},
            ).execute()
        except Exception as e:
            logger.exception("Failed to deduct credit for user")
            raise DatabaseError(str(e)) from e
        return result.data is True

    async def fulfill_stripe_payment(
        self,
        user_id: str,
        amount: int,
        stripe_session_id: str,
    ) -> bool:
        """Atomically add credits + record transaction, idempotent on stripe_session_id.

        Returns True if credits were added, False if already processed.
        """
        sb = await get_supabase()
        try:
            result = await sb.rpc(
                "fulfill_stripe_payment",
                {
                    "p_user_id": user_id,
                    "p_amount": amount,
                    "p_stripe_session_id": stripe_session_id,
                },
            ).execute()
        except Exception as e:
            logger.exception(
                "Failed to fulfill Stripe payment for session %s", stripe_session_id
            )
            raise DatabaseError(str(e)) from e
        return result.data is True
