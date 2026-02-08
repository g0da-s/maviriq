from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    credits: int
    created_at: str


class AuthResponse(BaseModel):
    token: str
    user: UserResponse


class CheckoutRequest(BaseModel):
    pack: int  # 5, 20, or 50
