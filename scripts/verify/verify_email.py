import asyncio
import os
from dotenv import load_dotenv
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType

# Explicitly load from backend/.env
load_dotenv("backend/.env")

# Re-create config to ensure we pulled latest env vars
conf = ConnectionConfig(
    MAIL_USERNAME = os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD"),
    MAIL_FROM = os.getenv("MAIL_FROM"),
    MAIL_PORT = 465, # Try SSL port
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com"),
    MAIL_STARTTLS = False,
    MAIL_SSL_TLS = True,
    USE_CREDENTIALS = True,
    VALIDATE_CERTS = False # Bypass for local dev SSL issues
)

async def test_email():
    print(f"Testing email connection...")
    print(f"User: {conf.MAIL_USERNAME}")
    print(f"Server: {conf.MAIL_SERVER}")
    
    message = MessageSchema(
        subject="Test Email from VinSight",
        recipients=[conf.MAIL_USERNAME], # Send to self
        body="<p>This is a test email to verify credentials.</p>",
        subtype=MessageType.html
    )

    fm = FastMail(conf)
    try:
        await fm.send_message(message)
        print("SUCCESS: Email sent successfully.")
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(test_email())
