import requests
import os
from dotenv import load_dotenv

# load API key from .env safely
try:
    dotenv_file = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(dotenv_file):
        load_dotenv(dotenv_file)
except Exception:
    pass

API_KEY = os.getenv("OPENROUTER_API_KEY")

url = "https://openrouter.ai/api/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

data = {
    "model": "deepseek/deepseek-chat",
    "messages": [
        {
            "role": "user",
            "content": "You are a farmer negotiating crop price. Buyer offered ₹16 but minimum price is ₹18. What should the farmer do?"
        }
    ]
}

response = requests.post(url, headers=headers, json=data)

print(response.json())