import uuid
from pydantic import BaseModel, Field, EmailStr


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class User(UserBase):
    id: uuid.UUID
    is_active: bool = True

    class Config:
        from_attributes = True


# Minimal representation of the user stored in the token
class UserInToken(BaseModel):
    id: uuid.UUID
    email: EmailStr


# Essential fields from Supabase user object needed after auth operations
class SupabaseUser(BaseModel):
    id: uuid.UUID
    aud: str
    role: str
    email: EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    # Represents potential data decoded from a JWT (not used directly with Supabase validation)
    sub: str | None = None
    id: uuid.UUID | None = None
    email: EmailStr | None = None


class PasswordResetRequest(BaseModel):
    email: EmailStr


# Model removed as password confirmation is now handled client-side via Supabase JS
# class PasswordResetConfirm(BaseModel):
#     token: str
#     new_password: str = Field(..., min_length=8)

# Model removed as verification is now handled client-side via Supabase JS
# class VerifyRecoveryPayload(BaseModel):
#     token: str
#     type: str
#     email: EmailStr
