from datetime import datetime, timedelta, timezone
from typing import Any, Union
import jwt
from passlib.context import CryptContext
from app.core.config import settings
import uuid

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

BCRYPT_MAX_PASSWORD_BYTES = 72
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

def validate_password_length(password: str) -> str:
    if len(password.encode("utf-8")) > BCRYPT_MAX_PASSWORD_BYTES:
        raise ValueError(
            f"Password must be no more than {BCRYPT_MAX_PASSWORD_BYTES} bytes."
        )
    return password

def verify_password(plain_password: str, hashed_password: str) -> bool:
    validate_password_length(plain_password)
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    validate_password_length(password)
    return pwd_context.hash(password)

def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
