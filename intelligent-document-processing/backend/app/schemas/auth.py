from typing import Literal

from pydantic import BaseModel, Field, field_validator

Role = Literal["OPERATOR", "REVIEWER", "ADMIN", "COMPANY", "APPLICANT"]
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


def _clean_email(v: str) -> str:
    return v.strip().lower()


class LoginRequest(BaseModel):
    email: str = Field(pattern=EMAIL_PATTERN, max_length=255)
    password: str = Field(min_length=1, max_length=200)
    norm_email = field_validator("email")(_clean_email)


class RegisterRequest(BaseModel):
    """Public sign-up. Only the self-service roles are allowed; staff accounts are created by an administrator."""
    email: str = Field(pattern=EMAIL_PATTERN, max_length=255)
    full_name: str = Field(min_length=1, max_length=150)
    password: str = Field(min_length=8, max_length=200)
    role: Literal["COMPANY", "APPLICANT"]
    organization_name: str | None = Field(default=None, max_length=200)   # required for COMPANY
    registration_no: str | None = Field(default=None, max_length=60)
    country: str | None = Field(default=None, max_length=60)
    norm_email = field_validator("email")(_clean_email)


class UserCreate(BaseModel):
    email: str = Field(pattern=EMAIL_PATTERN, max_length=255)
    full_name: str = Field(min_length=1, max_length=150)
    password: str = Field(min_length=8, max_length=200)
    role: Role
    org_id: str | None = None
    norm_email = field_validator("email")(_clean_email)


class UserUpdate(BaseModel):
    role: Role | None = None
    is_active: bool | None = None


class UserOut(BaseModel):
    user_id: str
    email: str
    full_name: str
    role: Role
    org_id: str | None = None
    is_active: bool

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut
