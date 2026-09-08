from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.core.database import get_db
from src.core.security import get_password_hash, verify_password, create_access_token, decode_access_token
from src.core.exceptions import AuthException, NotFoundException
from src.db.models import User
from src.schemas.auth import RecruiterSignup, Token

router = APIRouter(prefix="/auth", tags=["auth"])

from typing import Optional

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/token")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="api/v1/auth/token", auto_error=False)

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    try:
        payload = decode_access_token(token)
        email: str = payload.get("sub")
        if email is None:
            raise AuthException("Invalid token claims")
    except Exception as e:
        raise AuthException("Could not validate credentials")
        
    result = await db.execute(select(User).filter(User.email == email))
    user = result.scalars().first()
    if user is None:
        raise NotFoundException("User not found")
    return user

async def get_current_user_optional(token: Optional[str] = Depends(oauth2_scheme_optional), db: AsyncSession = Depends(get_db)) -> Optional[User]:
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        email: str = payload.get("sub")
        if email is None:
            return None
        result = await db.execute(select(User).filter(User.email == email))
        return result.scalars().first()
    except Exception:
        return None

@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(payload: RecruiterSignup, db: AsyncSession = Depends(get_db)):
    stmt = select(User).filter(User.email == payload.email)
    result = await db.execute(stmt)
    if result.scalars().first():
        raise AuthException("Email is already registered")
        
    hashed_pwd = get_password_hash(payload.password)
    user = User(
        email=payload.email,
        hashed_password=hashed_pwd,
        full_name=payload.full_name,
        role=payload.role or "candidate"
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {"message": "User registered successfully", "id": str(user.id)}

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    stmt = select(User).filter(User.email == form_data.username)
    result = await db.execute(stmt)
    user = result.scalars().first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise AuthException("Incorrect email or password")
        
    access_token = create_access_token(data={"sub": user.email})
    return Token(
        access_token=access_token,
        token_type="bearer",
        role=user.role,
        email=user.email,
        full_name=user.full_name
    )
