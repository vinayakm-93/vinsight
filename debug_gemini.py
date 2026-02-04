
import os
import google.generativeai as genai
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), "backend", ".env")
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
print(f"API Key loaded: {api_key[:5]}...{api_key[-5:] if api_key else 'None'}")

if not api_key:
    print("Error: GEMINI_API_KEY not found in env.")
    exit(1)

genai.configure(api_key=api_key)

print("--- Available Models ---")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
             print(f"- {m.name}")
except Exception as e:
    print(f"List models failed: {e}")

print("\n--- Test Generation ---")
models_to_try = ['gemini-1.5-flash', 'models/gemini-1.5-flash', 'gemini-pro']
for m_name in models_to_try:
    print(f"Testing {m_name}...")
    try:
        model = genai.GenerativeModel(m_name)
        response = model.generate_content("Hello")
        print(f"SUCCESS: {m_name}")
        break
    except Exception as e:
        print(f"FAILED {m_name}: {e}")
