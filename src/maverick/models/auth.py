from pydantic import BaseModel


class UserResponse(BaseModel):
    id: str
    email: str
    credits: int
    created_at: str


class CheckoutRequest(BaseModel):
    pack: int  # 5, 20, or 50
