import uuid
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime


# --- Authentication Models ---
class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class User(UserBase):
    id: uuid.UUID
    is_active: bool = True  # Assuming Supabase users are active by default

    class Config:
        from_attributes = True


# Minimal representation of the user stored in the token
class UserInToken(BaseModel):
    id: uuid.UUID
    email: EmailStr


# Supabase returns more info, but this is essential for our JWT validation/usage
class SupabaseUser(BaseModel):
    id: uuid.UUID
    aud: str
    role: str
    email: EmailStr
    # Supabase includes many other fields like confirmed_at, created_at etc.
    # We only map what we strictly need for our app's logic post-login.


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    # This will hold the payload decoded from our JWT if we were doing it manually
    # Using 'sub' (subject) standard claim for user identifier (email or id)
    sub: str | None = None  # Could be email or UUID string
    id: uuid.UUID | None = None  # Extracted user ID
    email: EmailStr | None = None  # Extracted user email


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str  # The token received via email (or temp password, depending on flow)
    new_password: str = Field(..., min_length=8)
