"""Test live market data API endpoint to verify real connectivity and rate limits."""
import urllib.request
import json
import time
from datetime import datetime, timezone

url = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070?api-key=579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b&format=json&offset=0&limit=2"
ts = datetime.now(timezone.utc).isoformat()
print(f"Timestamp: {ts}")
print(f"Source: Government of India Open Government Data (data.gov.in)")
print(f"Endpoint: {url}")

req = urllib.request.Request(url, headers={"User-Agent": "AgriNegotiator-Verification/1.0"})
start_time = time.time()
try:
    with urllib.request.urlopen(req, timeout=10) as response:
        duration = time.time() - start_time
        status = response.status
        raw = response.read().decode('utf-8')
        print(f"Response Status: {status} (in {duration:.2f}s)")
        print("Raw Response Payload (first 300 chars):")
        print(raw[:300])
except urllib.error.HTTPError as e:
    duration = time.time() - start_time
    status = e.code
    raw = e.read().decode('utf-8')
    print(f"HTTP Error: {status} ({e.reason}) (in {duration:.2f}s)")
    print("Response Payload:")
    print(raw[:300])
except Exception as e:
    duration = time.time() - start_time
    print(f"Connection Exception: {e} (in {duration:.2f}s)")
