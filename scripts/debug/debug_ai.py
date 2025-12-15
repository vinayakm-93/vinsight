from dotenv import load_dotenv
import os
import google.generativeai as genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
print(f"Key loaded: {api_key[:5]}..." if api_key else "Key Missing")

if not api_key:
    exit(1)

genai.configure(api_key=api_key)
try:
    model = genai.GenerativeModel('gemini-2.0-flash')
    response = model.generate_content("Say 'Hello AI' if you are working.")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
