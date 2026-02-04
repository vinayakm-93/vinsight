
import os
from dotenv import load_dotenv
import google.generativeai as genai

# Debug Env Loading
env_path = os.path.join(os.getcwd(), "backend", ".env")
print(f"Loading .env from: {env_path}")

if os.path.exists(env_path):
    print("File exists.")
    with open(env_path, 'r') as f:
        content = f.read()
        if "GEMINI_API_KEY" in content:
            print("GEMINI_API_KEY found in file content.")
        else:
            print("GEMINI_API_KEY NOT found in file content.")
else:
    print("File DOES NOT exist.")

load_dotenv(env_path, override=True) # Force reload

api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    print(f"API Key loaded (len={len(api_key)}): {api_key[:4]}...{api_key[-4:]}")
    genai.configure(api_key=api_key)
    
    print("Listing models...")
    try:
        found_flash = False
        for m in genai.list_models():
            print(f"- {m.name}")
            if 'flash' in m.name:
                found_flash = True
        
        if found_flash:
            print("\nSUCCESS: Found flash model!")
        else:
            print("\nWARNING: Flash model not found in list.")

    except Exception as e:
        print(f"Error listing models: {e}")

else:
    print("ERROR: API Key is None or Empty after loading.")
