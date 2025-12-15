from dotenv import load_dotenv
import os
from groq import Groq

load_dotenv()

key = os.getenv("GROQ_API_KEY")
print(f"Groq Key: {key[:5]}..." if key else "Missing Key")

client = Groq(api_key=key)

try:
    print("Testing Groq API connection...")
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "user", "content": "Say 'Groq is ready'"}
        ]
    )
    print(f"Response: {completion.choices[0].message.content}")
except Exception as e:
    print(f"Error: {e}")
