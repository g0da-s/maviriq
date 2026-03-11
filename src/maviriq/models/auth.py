from typing import Literal

from pydantic import BaseModel


class UserResponse(BaseModel):
    id: str
    email: str
    credits: int
    created_at: str


class CheckoutRequest(BaseModel):
    pack: Literal[5, 20, 50]
