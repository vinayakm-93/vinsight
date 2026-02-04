import asyncio
import os
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr
from pathlib import Path

# Setup Logging
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs', 'email.log')

# Ensure directory exists (redundant safety)
os.makedirs(os.path.dirname(log_file), exist_ok=True)

file_handler = RotatingFileHandler(log_file, maxBytes=1024*1024, backupCount=5)
file_handler.setFormatter(log_formatter)

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)

logger = logging.getLogger("email_service")
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Explicitly load from backend/.env
load_dotenv("backend/.env")

# Support both prefixes for better compatibility with .env templates
MAIL_USER = os.getenv("MAIL_USERNAME") or os.getenv("SMTP_USERNAME")
MAIL_PASS = os.getenv("MAIL_PASSWORD") or os.getenv("SMTP_PASSWORD")
MAIL_SERVER = os.getenv("MAIL_SERVER") or os.getenv("SMTP_SERVER", "smtp.gmail.com")
MAIL_PORT = int(os.getenv("MAIL_PORT") or os.getenv("SMTP_PORT", 587))
MAIL_SENDER = os.getenv("MAIL_FROM") or os.getenv("EMAIL_FROM") or MAIL_USER

# For development, we can print to console if no real creds or using placeholders
MOCK_MODE = (MAIL_USER is None) or ("your_email" in MAIL_USER)

# Only create real config if we have credentials
if not MOCK_MODE:
    conf = ConnectionConfig(
        MAIL_USERNAME = MAIL_USER,
        MAIL_PASSWORD = MAIL_PASS,
        MAIL_FROM = MAIL_SENDER,
        MAIL_PORT = MAIL_PORT,
        MAIL_SERVER = MAIL_SERVER,
        MAIL_STARTTLS = True,
        MAIL_SSL_TLS = False,
        USE_CREDENTIALS = True,
        VALIDATE_CERTS = False
    )
else:
    conf = None  # Will be handled by MOCK_MODE checks in methods


# --- Email Templates ---

def get_base_style():
    return """
    font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    color: #e2e8f0;
    max-width: 600px;
    margin: 0 auto;
    background-color: #0f172a;
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    """

def get_header(title):
    return f"""
    <div style="background-color: #1e293b; padding: 32px 24px; text-align: center; border-bottom: 1px solid #334155;">
        <h1 style="color: #60a5fa; margin: 0; font-size: 28px; font-weight: 800; letter-spacing: -1px;">VinSight</h1>
        <p style="color: #94a3b8; font-size: 14px; margin: 8px 0 0 0; text-transform: uppercase; letter-spacing: 2px;">{title}</p>
    </div>
    """

def get_footer():
    return """
    <div style="background-color: #0f172a; padding: 24px; text-align: center; border-top: 1px solid #1e293b;">
        <p style="color: #64748b; font-size: 12px; margin: 0;">&copy; 2025 VinSight Finance. All rights reserved.</p>
        <p style="color: #475569; font-size: 11px; margin-top: 8px;">Automated Alert System</p>
    </div>
    """

async def send_verification_email(email: EmailStr, code: str):
    logger.info(f"Preparing verification email for {email}")
    if MOCK_MODE:
        logger.info(f"[MOCK] Verification Code for {email}: {code}")
        print(f"[MOCK EMAIL] To: {email} | Code: {code}")
        return

    html = f"""
    <div style="{get_base_style()}">
        {get_header("Verify Your Account")}
        
        <div style="padding: 40px 24px; text-align: center;">
            <p style="font-size: 16px; color: #cbd5e1; margin-bottom: 24px; line-height: 1.6;">
                Welcome to VinSight! Please verify your email address to access your dashboard.
            </p>
            
            <div style="background-color: #1e293b; padding: 24px; border-radius: 12px; margin: 0 auto 24px auto; display: inline-block; border: 1px solid #334155;">
                <span style="font-size: 32px; font-family: 'Courier New', monospace; font-weight: bold; color: #f8fafc; letter-spacing: 8px;">{code}</span>
            </div>
            
            <p style="font-size: 14px; color: #64748b;">
                This code will expire in 10 minutes.<br>
                If you didn't request this, please ignore this email.
            </p>
        </div>
        
        {get_footer()}
    </div>
    """

    message = MessageSchema(
        subject="Verify your VinSight Account",
        recipients=[email],
        body=html,
        subtype=MessageType.html
    )

    fm = FastMail(conf)
    try:
        await fm.send_message(message)
        logger.info(f"Verification email sent successfully to {email}")
    except Exception as e:
        logger.error(f"Failed to send verification email to {email}: {str(e)}")
        print(f"MOCK FALLBACK CODE: {code}")

async def send_password_reset_email(email: EmailStr, code: str):
    logger.info(f"Preparing password reset email for {email}")
    if MOCK_MODE:
        logger.info(f"[MOCK] Password Reset Code for {email}: {code}")
        print(f"[MOCK EMAIL] Password Reset - To: {email} | Code: {code}")
        return

    html = f"""
    <div style="{get_base_style()}">
        {get_header("Reset Your Password")}
        
        <div style="padding: 40px 24px; text-align: center;">
            <p style="font-size: 16px; color: #cbd5e1; margin-bottom: 24px; line-height: 1.6;">
                You requested to reset your VinSight password. Use the code below to continue.
            </p>
            
            <div style="background-color: #1e293b; padding: 24px; border-radius: 12px; margin: 0 auto 24px auto; display: inline-block; border: 1px solid #334155;">
                <span style="font-size: 32px; font-family: 'Courier New', monospace; font-weight: bold; color: #f8fafc; letter-spacing: 8px;">{code}</span>
            </div>
            
            <p style="font-size: 14px; color: #64748b;">
                This code will expire in 15 minutes.<br>
                If you didn't request this, please ignore this email and your password will remain unchanged.
            </p>
        </div>
        
        {get_footer()}
    </div>
    """

    message = MessageSchema(
        subject="Reset Your VinSight Password",
        recipients=[email],
        body=html,
        subtype=MessageType.html
    )

    fm = FastMail(conf)
    try:
        await fm.send_message(message)
        logger.info(f"Password reset email sent successfully to {email}")
    except Exception as e:
        logger.error(f"Failed to send password reset email to {email}: {str(e)}")
        print(f"MOCK FALLBACK CODE: {code}")

async def send_alert_email(email: EmailStr, symbol: str, price: float, condition: str, target: float):
    logger.info(f"Preparing alert email for {email} (Symbol: {symbol})")
    if MOCK_MODE:
        logger.info(f"[MOCK] Alert for {email}: {symbol} {condition} {target}")
        print(f"[MOCK ALERT] {symbol} {condition} {target}")
        return

    app_link = os.getenv("FRONTEND_URL", "http://localhost:3000")
    reset_link = f"{app_link}/dashboard?ticker={symbol}&action=reset_alert"
    
    color = "#10b981" if condition == 'above' else "#ef4444"
    arrow = "▲" if condition == 'above' else "▼"

    html = f"""
    <div style="{get_base_style()}">
        {get_header("Price Target Reached")}
        
        <div style="padding: 32px 24px; text-align: center;">
            <div style="margin-bottom: 24px;">
                <span style="font-size: 14px; font-weight: bold; background-color: #334155; color: #f8fafc; padding: 6px 12px; border-radius: 20px;">{symbol}</span>
            </div>
            
            <h2 style="font-size: 48px; margin: 0; font-weight: 800; color: {color};">
                {arrow} ${price}
            </h2>
            
            <p style="font-size: 18px; color: #cbd5e1; margin: 16px 0;">
                Has crossed <b style="color: #f8fafc;">{condition.upper()}</b> your target of <b>${target}</b>
            </p>
            
            <div style="margin-top: 32px;">
                <a href="{reset_link}" style="background-color: #3b82f6; color: #ffffff; padding: 14px 32px; border-radius: 8px; text-decoration: none; font-weight: bold; font-size: 16px; display: inline-block;">
                    Reset Alert
                </a>
            </div>
            
            <p style="margin-top: 24px;">
                <a href="{app_link}" style="color: #94a3b8; text-decoration: none; font-size: 14px; border-bottom: 1px dashed #475569;">
                    Open Dashboard
                </a>
            </p>
        </div>
        
        {get_footer()}
    </div>
    """

    message = MessageSchema(
        subject=f"🔔 Alert: {symbol} hit ${price}",
        recipients=[email],
        body=html,
        subtype=MessageType.html
    )

    fm = FastMail(conf)
    try:
        await fm.send_message(message)
        logger.info(f"Alert email sent successfully to {email} for {symbol}")
    except Exception as e:
        logger.error(f"Failed to send alert email to {email}: {str(e)}")
        print(f"MOCK FALLBACK ALERT: {symbol} ${price}")
