import google.genai as genai
import os

# The API key is expected to be set in the environment

# Define a simple tool
def add(a: int, b: int):
    """Adds two numbers."""
    return a + b

# Create the model
model = genai.GenerativeModel('gemini-1.5-flash', tools=[add])

# Generate content
response = model.generate_content("What is 10 + 23?")

print(response)