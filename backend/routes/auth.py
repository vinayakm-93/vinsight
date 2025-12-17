from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from datetime import timedelta, datetime
import secrets
import logging
# Import updated models
from database import get_db
from models import User, Watchlist, PasswordReset, VerificationCode
from services import auth, mail
from rate_limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.get("/health-db")
def health_db(db: Session = Depends(get_db)):
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        return {"status": "ok", "message": "Database connection healthy"}
    except Exception as e:
        logger.exception("Database health check failed")
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")

# Constants
VERIFICATION_CODE_EXPIRE_MINUTES = 15

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    investing_goals: str | None = None
    feature_requests: str | None = None
    verification_code: str

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
@limiter.limit("3/minute")
async def request_verification(request: Request, user_request: UserVerifyRequest, db: Session = Depends(get_db)):
    # Check if user exists
    existing = db.query(User).filter(User.email == user_request.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Generate Code
    code = f"{secrets.randbelow(900000) + 100000}"
    
    # Save to DB (Delete old codes first)
    db.query(VerificationCode).filter(VerificationCode.email == user_request.email).delete()
    
    new_code = VerificationCode(
        email=user_request.email,
        code=code,
        expires_at=datetime.utcnow() + timedelta(minutes=VERIFICATION_CODE_EXPIRE_MINUTES)
    )
    db.add(new_code)
    db.commit()
    
    # Send Email
    await mail.send_verification_email(user_request.email, code)
    
    return {"status": "success", "message": "Verification code sent"}

@router.post("/verify-code")
def verify_code(request: UserCodeVerify, db: Session = Depends(get_db)):
    # Verify from DB
    record = db.query(VerificationCode).filter(VerificationCode.email == request.email).first()
    
    if not record or record.code != request.code:
        raise HTTPException(status_code=400, detail="Invalid verification code")
        
    if datetime.utcnow() > record.expires_at:
        raise HTTPException(status_code=400, detail="Verification code expired")
        
    return {"status": "success", "message": "Code verified"}

@router.post("/register", response_model=UserOut)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    logger.info(f"Registration attempt for: {user_in.email}")
    try:
        # Verify Code from DB
        record = db.query(VerificationCode).filter(VerificationCode.email == user_in.email).first()
        
        if not record or record.code != user_in.verification_code:
            raise HTTPException(status_code=400, detail="Invalid verification code")
            
        if datetime.utcnow() > record.expires_at:
            raise HTTPException(status_code=400, detail="Verification code expired")

        # Check if user exists
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
        
        # Cleanup code
        db.delete(record)
        db.commit()
        
        return new_user
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.exception("Registration failed")
        raise HTTPException(status_code=500, detail="Registration failed. Please try again.")

@router.post("/login")
@limiter.limit("5/minute")
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
    # Set HttpOnly Cookie
    # Since we are now using Next.js Proxy (First-Party), we should use SameSite=Lax
    # This is more compatible and secure for first-party contexts than None
    import os
    is_production = os.getenv("ENV", "development") == "production"
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        secure=is_production, # Still keep Secure=True in prod (HTTPS)
        samesite="lax",      # Changed from 'none' to 'lax' for proxy compatibility
        max_age=auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    
    return {"status": "success", "user": {"id": user.id, "email": user.email}}

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(key="access_token")
    return {"status": "success"}

@router.get("/me", response_model=UserOut)
def read_users_me(request: Request, db: Session = Depends(get_db)):
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

@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(request: Request, password_request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == password_request.email).first()
    if not user:
        return {"status": "success", "message": "If this email exists, a reset code has been sent"}
    
    code = f"{secrets.randbelow(900000) + 100000}"
    
    db.query(PasswordReset).filter(
        PasswordReset.user_id == user.id,
        PasswordReset.is_used == False
    ).update({"is_used": True})
    
    reset_record = PasswordReset(
        user_id=user.id,
        reset_code=code
    )
    db.add(reset_record)
    db.commit()
    
    await mail.send_password_reset_email(password_request.email, code)
    
    return {"status": "success", "message": "If this email exists, a reset code has been sent"}

@router.post("/verify-reset-code")
def verify_reset_code(request: VerifyResetCodeRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid code or email")
    
    reset_record = db.query(PasswordReset).filter(
        PasswordReset.user_id == user.id,
        PasswordReset.reset_code == request.code,
        PasswordReset.is_used == False
    ).first()
    
    if not reset_record:
        raise HTTPException(status_code=400, detail="Invalid or expired code")
    
    time_diff = datetime.utcnow() - reset_record.created_at
    if time_diff.total_seconds() > 900:
        raise HTTPException(status_code=400, detail="Code has expired")
    
    return {"status": "success", "message": "Code verified"}

@router.post("/reset-password")
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid code or email")
    
    reset_record = db.query(PasswordReset).filter(
        PasswordReset.user_id == user.id,
        PasswordReset.reset_code == request.code,
        PasswordReset.is_used == False
    ).first()
    
    if not reset_record:
        raise HTTPException(status_code=400, detail="Invalid or expired code")
    
    time_diff = datetime.utcnow() - reset_record.created_at
    if time_diff.total_seconds() > 900:
        raise HTTPException(status_code=400, detail="Code has expired")
    
    user.hashed_password = auth.get_password_hash(request.new_password)
    reset_record.is_used = True
    db.commit()
    
    return {"status": "success", "message": "Password reset successfully"}
