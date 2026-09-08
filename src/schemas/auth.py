from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class RecruiterSignup(BaseModel):
    """
    Pydantic schema representing recruiter sign-up payload.
    """
    email: EmailStr
    password: str = Field(..., min_length=8, description="Must include numeric & special chars")
    full_name: str
    role: Optional[str] = Field(default="interviewer", description="admin, interviewer, or candidate")


class Token(BaseModel):
    """
    Pydantic schema for returning access tokens to the client.
    """
    access_token: str
    token_type: str
    role: str
    email: str
    full_name: str


class TokenData(BaseModel):
    """
    Pydantic schema containing token payload claims.
    """
    email: Optional[str] = None
