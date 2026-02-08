import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request

from maverick.api.dependencies import get_current_user
from maverick.config import settings
from maverick.models.auth import CheckoutRequest
from maverick.storage.credit_repository import CreditTransactionRepository
from maverick.storage.user_repository import UserRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stripe")

PACK_TO_CREDITS = {5: 5, 20: 20, 50: 50}


def _get_price_id(pack: int) -> str:
    mapping = {
        5: settings.stripe_price_5,
        20: settings.stripe_price_20,
        50: settings.stripe_price_50,
    }
    price_id = mapping.get(pack)
    if not price_id:
        raise HTTPException(status_code=400, detail="Invalid pack size. Choose 5, 20, or 50.")
    return price_id


@router.post("/checkout")
async def create_checkout(
    req: CheckoutRequest,
    user: dict = Depends(get_current_user),
) -> dict:
    stripe.api_key = settings.stripe_secret_key
    price_id = _get_price_id(req.pack)

    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{settings.frontend_url}/credits?success=true",
        cancel_url=f"{settings.frontend_url}/credits?canceled=true",
        client_reference_id=user["id"],
        metadata={"user_id": user["id"], "credits": str(req.pack)},
    )
    return {"checkout_url": session.url}


@router.post("/webhook")
async def stripe_webhook(request: Request) -> dict:
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig, settings.stripe_webhook_secret
        )
    except (stripe.error.SignatureVerificationError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session.get("client_reference_id") or session["metadata"].get("user_id")
        credits = int(session["metadata"]["credits"])
        session_id = session["id"]

        user_repo = UserRepository()
        txn_repo = CreditTransactionRepository()
        await user_repo.add_credits(user_id, credits)
        await txn_repo.record(user_id, credits, "purchase", stripe_session_id=session_id)
        logger.info(f"Added {credits} credits to user {user_id} via Stripe session {session_id}")

    return {"status": "ok"}
