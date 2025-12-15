from dotenv import load_dotenv
import os

# Load env before importing service to ensure keys are ready
load_dotenv()

from services import earnings

print("--- Starting Debug ---")
API_KEY = os.getenv("API_NINJAS_KEY")
print(f"Loaded API Key in debug script: {API_KEY[:5]}..." if API_KEY else "Key NOT loaded in debug script")

print("Testing with ticker: AAPL")
transcript = earnings.get_transcript("AAPL")
print(f"Result: {len(transcript) if transcript else 'None'}")
