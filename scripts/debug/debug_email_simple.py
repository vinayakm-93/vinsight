import asyncio
import os
import sys
from dotenv import load_dotenv

# Add DB path
sys.path.append(os.getcwd())

# Load Env
load_dotenv(dotenv_path="backend/.env")

from backend.services import mail

async def test_email():
    print("--- DEBUG EMAIL SENDING ---")
    print(f"MAIL_USERNAME: {os.getenv('MAIL_USERNAME')}")
    print(f"MAIL_PORT: {os.getenv('MAIL_PORT')}")
    print(f"MOCK_MODE: {mail.MOCK_MODE}")
    
    email = "vinayak_test@example.com"
    code = "123456"
    
    print(f"Attempting to send verification email to {email}...")
    try:
        await mail.send_verification_email(email, code)
        print("Function returned (Check if it printed MOCK or sent real email).")
    except Exception as e:
        print(f"Email Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_email())
