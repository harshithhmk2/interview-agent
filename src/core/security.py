from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from jose import JWTError, jwt
import bcrypt
from src.config import settings
from src.core.exceptions import AuthException


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Compares a plain text password with a hashed version using BCrypt.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception as e:
        raise AuthException(
            message="Failed to verify password hash",
            details={"original_error": str(e)}
        )


def get_password_hash(password: str) -> str:
    """
    Generates a secure BCrypt hash of a plain text password.
    """
    try:
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")
    except Exception as e:
        raise AuthException(
            message="Failed to generate password hash",
            details={"original_error": str(e)}
        )


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Encodes data payload into a JWT access token with an expiration timestamp.
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
    to_encode.update({"exp": int(expire.timestamp())})
    
    try:
        encoded_jwt = jwt.encode(
            claims=to_encode,
            key=settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        return encoded_jwt
    except Exception as e:
        raise AuthException(
            message="Could not generate access token",
            details={"original_error": str(e)}
        )


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decodes and verifies a JWT access token. Returns claims dict if valid,
    raises AuthException if the token is expired or signature check fails.
    """
    try:
        payload = jwt.decode(
            token=token,
            key=settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError as e:
        raise AuthException(
            message="Could not validate authentication credentials",
            details={"reason": "Expired or invalid token payload", "original_error": str(e)}
        )
