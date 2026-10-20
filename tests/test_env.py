from dotenv import load_dotenv
import os

try:
    dotenv_file = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(dotenv_file):
        load_dotenv(dotenv_file)
except Exception:
    pass

print(os.getenv("FEATHERLESS_API_KEY"))