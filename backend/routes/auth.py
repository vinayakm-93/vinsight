from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from datetime import timedelta
import secrets
import logging

from ..database import get_db
from ..models import User, Watchlist, PasswordReset
from ..services import auth, mail
from datetime import datetime
from ..rate_limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# MVP In-Memory Verification Storage
# In production, use Redis or a DB table with expiration
verification_codes = {}

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    investing_goals: str | None = None
    feature_requests: str | None = None
    verification_code: str # Now required

class UserVerifyRequest(BaseModel):
    email: EmailStr

class UserCodeVerify(BaseModel):
    email: EmailStr
    code: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    
    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/request-verify")
@limiter.limit("3/minute")  # Prevent email bombing
async def request_verification(request: Request, user_request: UserVerifyRequest, db: Session = Depends(get_db)):
    # Check if user exists
    existing = db.query(User).filter(User.email == user_request.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Generate Code (cryptographically secure)
    code = f"{secrets.randbelow(900000) + 100000}"
    verification_codes[user_request.email] = code
    
    # Send Email
    await mail.send_verification_email(user_request.email, code)
    
    return {"status": "success", "message": "Verification code sent"}

@router.post("/verify-code")
def verify_code(request: UserCodeVerify):
    stored_code = verification_codes.get(request.email)
    if not stored_code or stored_code != request.code:
        raise HTTPException(status_code=400, detail="Invalid verification code")
    return {"status": "success", "message": "Code verified"}

# DEBUG ENDPOINT REMOVED FOR SECURITY
# Verification codes should never be exposed via API

@router.post("/register", response_model=UserOut)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    logger.info(f"Registration attempt for: {user_in.email}")
    try:
        # Verify Code
        stored_code = verification_codes.get(user_in.email)
        
        if not stored_code or stored_code != user_in.verification_code:
            raise HTTPException(status_code=400, detail="Invalid or expired verification code")

        # Check if user exists (Double check)
        existing = db.query(User).filter(User.email == user_in.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        hashed_pw = auth.get_password_hash(user_in.password)
        new_user = User(
            email=user_in.email, 
            hashed_password=hashed_pw,
            investing_goals=user_in.investing_goals,
            feature_requests=user_in.feature_requests
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Create Default Watchlist
        default_watchlist = Watchlist(
            name="My First List",
            user_id=new_user.id,
            stocks="AAPL,NVDA,GOOGL,MSFT,TSLA"
        )
        db.add(default_watchlist)
        db.commit()
        
        # Cleanup code
        if user_in.email in verification_codes:
            del verification_codes[user_in.email]
            
        return new_user
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.exception("Registration failed")
        raise HTTPException(status_code=500, detail="Registration failed. Please try again.")

@router.post("/login")
@limiter.limit("5/minute")  # Prevent brute force
def login(request: Request, login_req: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login_req.email).first()
    if not user or not auth.verify_password(login_req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    # Create Token
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.email, "id": user.id}, expires_delta=access_token_expires
    )
    
    # Set HttpOnly Cookie
    import os
    is_production = os.getenv("ENV", "development") == "production"
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        secure=is_production,  # True in production (HTTPS)
        samesite="lax" if not is_production else "strict",
        max_age=auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    
    return {"status": "success", "user": {"id": user.id, "email": user.email}}

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(key="access_token")
    return {"status": "success"}

@router.get("/me", response_model=UserOut)
def read_users_me(request: Request, db: Session = Depends(get_db)):
    # Custom cookie extraction
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if token.startswith("Bearer "):
        token = token.split(" ")[1]
        
    payload = auth.decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    user_id = payload.get("id")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
        
    return user

# Password Reset Models
class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class VerifyResetCodeRequest(BaseModel):
    email: EmailStr
    code: str

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str
    new_password: str

# Password Reset Endpoints
@router.post("/forgot-password")
@limiter.limit("3/minute")  # Prevent email bombing
async def forgot_password(request: Request, password_request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Request a password reset code"""
    # Check if user exists
    user = db.query(User).filter(User.email == password_request.email).first()
    if not user:
        # Don't reveal if email exists or not (security best practice)
        return {"status": "success", "message": "If this email exists, a reset code has been sent"}
    
    # Generate 6-digit code (cryptographically secure)
    code = f"{secrets.randbelow(900000) + 100000}"
    
    # Invalidate any existing reset codes for this user
    db.query(PasswordReset).filter(
        PasswordReset.user_id == user.id,
        PasswordReset.is_used == False
    ).update({"is_used": True})
    
    # Create new reset code
    reset_record = PasswordReset(
        user_id=user.id,
        reset_code=code
    )
    db.add(reset_record)
    db.commit()
    
    # Send email
    await mail.send_password_reset_email(password_request.email, code)
    
    return {"status": "success", "message": "If this email exists, a reset code has been sent"}

@router.post("/verify-reset-code")
def verify_reset_code(request: VerifyResetCodeRequest, db: Session = Depends(get_db)):
    """Verify the reset code without changing password"""
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid code or email")
    
    # Find valid reset code
    reset_record = db.query(PasswordReset).filter(
        PasswordReset.user_id == user.id,
        PasswordReset.reset_code == request.code,
        PasswordReset.is_used == False
    ).first()
    
    if not reset_record:
        raise HTTPException(status_code=400, detail="Invalid or expired code")
    
    # Check if code is expired (15 minutes)
    time_diff = datetime.utcnow() - reset_record.created_at
    if time_diff.total_seconds() > 900:  # 15 minutes
        raise HTTPException(status_code=400, detail="Code has expired")
    
    return {"status": "success", "message": "Code verified"}

@router.post("/reset-password")
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset password with valid code"""
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid code or email")
    
    # Find valid reset code
    reset_record = db.query(PasswordReset).filter(
        PasswordReset.user_id == user.id,
        PasswordReset.reset_code == request.code,
        PasswordReset.is_used == False
    ).first()
    
    if not reset_record:
        raise HTTPException(status_code=400, detail="Invalid or expired code")
    
    # Check if code is expired (15 minutes)
    time_diff = datetime.utcnow() - reset_record.created_at
    if time_diff.total_seconds() > 900:  # 15 minutes
        raise HTTPException(status_code=400, detail="Code has expired")
    
    # Update password
    user.hashed_password = auth.get_password_hash(request.new_password)
    
    # Mark code as used
    reset_record.is_used = True
    
    db.commit()
    
    return {"status": "success", "message": "Password reset successfully"}
