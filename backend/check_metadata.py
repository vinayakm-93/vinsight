import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("API_NINJAS_KEY")
ticker = "AAPL"
api_url = f'https://api.api-ninjas.com/v1/earningstranscript?ticker={ticker}'

response = requests.get(api_url, headers={'X-Api-Key': API_KEY})
if response.status_code == 200:
    data = response.json()
    if isinstance(data, list) and len(data) > 0:
        print(f"Keys available: {data[0].keys()}")
        print(f"Quarter: {data[0].get('quarter')}")
        print(f"Year: {data[0].get('year')}")
    elif isinstance(data, dict):
        print(f"Keys available: {data.keys()}")
else:
    print(f"Error: {response.status_code}")
