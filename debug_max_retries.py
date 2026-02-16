import sys
import os
from openai import OpenAI
from groq import Groq
try:
    print("Testing OpenAI client with max_retries=0...")
    client = OpenAI(api_key="test", max_retries=0)
    print("OpenAI client initialized successfully.")
except Exception as e:
    print(f"OpenAI client failed: {e}")

try:
    print("Testing Groq client with max_retries=0...")
    groq = Groq(api_key="test", max_retries=0)
    print("Groq client initialized successfully.")
except Exception as e:
    print(f"Groq client failed: {e}")
