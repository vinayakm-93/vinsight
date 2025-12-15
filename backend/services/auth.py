from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User

import os
import logging

# Configuration
# SECURITY: Never hardcode secrets in production code
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ENV = os.getenv("ENV", "development")

if not SECRET_KEY:
    if ENV == "production":
        raise RuntimeError("FATAL: JWT_SECRET_KEY environment variable is required in production")
    else:
        logging.warning("WARNING: JWT_SECRET_KEY not set. Using insecure default for DEVELOPMENT ONLY.")
        SECRET_KEY = "dev_only_insecure_key_" + os.urandom(16).hex()

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 7 days for MVP convenience

# Using PBKDF2 to avoid bcrypt 72-byte limit issues in some environments
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

from fastapi import Request

# ... (previous imports)

# ... (previous functions)

def get_current_user_from_cookie(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        return None
    
    if token.startswith("Bearer "):
        token = token.split(" ")[1]
        
    payload = decode_token(token)
    if not payload:
        return None
        
    user_id = payload.get("id")
    user = db.query(User).filter(User.id == user_id).first()
    return user

def get_current_user(user: Optional[User] = Depends(get_current_user_from_cookie)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

def get_current_user_optional(user: Optional[User] = Depends(get_current_user_from_cookie)):
    return user
