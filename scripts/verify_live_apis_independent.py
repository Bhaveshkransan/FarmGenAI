import os
import time
import requests
import json
from dotenv import load_dotenv

load_dotenv()

print("=== ALL THREE APIS VERIFICATION ===")

# 1. Data.gov.in
print("\n1. DATA.GOV.IN MANDI API:")
dg_key = os.getenv("DATA_GOV_API_KEY", "")
if not dg_key:
    print("  Status: BLOCKED - Credential unavailable")
else:
    t0 = time.time()
    try:
        url = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
        params = {
            "api-key": dg_key,
            "format": "json",
            "limit": 5,
            "filters[state.keyword]": "Maharashtra",
            "filters[commodity]": "Soybean",
        }
        res = requests.get(url, params=params, timeout=15)
        dt = time.time() - t0
        if res.status_code == 200:
            recs = res.json().get("records", [])
            print(f"  Result: PASS (Status 200, Latency: {dt:.2f}s, Records fetched: {len(recs)})")
            if recs:
                print(f"  Sample: APMC {recs[0].get('market')}, Modal Price: Rs {recs[0].get('modal_price')}/quintal")
        else:
            print(f"  Result: FAIL (Status {res.status_code}, Latency: {dt:.2f}s)")
    except Exception as e:
        print(f"  Result: BLOCKED / NETWORK TIMEOUT ({type(e).__name__})")

# 2. Groq
print("\n2. GROQ LLM API:")
groq_key = os.getenv("GROQ_API_KEY", "")
if not groq_key:
    print("  Status: BLOCKED - Credential unavailable")
else:
    t0 = time.time()
    try:
        headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
        payload = {
            "model": "qwen/qwen3.8-27b",
            "messages": [{"role": "user", "content": "Respond with single word: OK"}],
            "max_tokens": 10,
        }
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=10)
        dt = time.time() - t0
        if res.status_code == 200:
            ans = res.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            print(f"  Result: PASS (Model: qwen/qwen3.8-27b, Latency: {dt:.2f}s, Response: {ans})")
        else:
            print(f"  Result: FAIL (Status {res.status_code}, Response: {res.text[:100]})")
    except Exception as e:
        print(f"  Result: FAIL ({e})")

# 3. Gemini
print("\n3. GEMINI LLM API:")
gem_key = os.getenv("GEMINI_API_KEY", "")
if not gem_key:
    print("  Status: BLOCKED - Credential unavailable")
else:
    t0 = time.time()
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gem_key}"
        payload = {"contents": [{"parts": [{"text": "Respond with single word: OK"}]}]}
        res = requests.post(url, json=payload, timeout=10)
        dt = time.time() - t0
        if res.status_code == 200:
            data = res.json()
            ans = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
            print(f"  Result: PASS (Model: gemini-1.5-flash, Latency: {dt:.2f}s, Response: {ans})")
        elif res.status_code == 429:
            print(f"  Result: RATE LIMITED / BLOCKED (Status 429 - Free Quota Exceeded, Latency: {dt:.2f}s)")
        else:
            print(f"  Result: FAIL (Status {res.status_code}, Response: {res.text[:120]})")
    except Exception as e:
        print(f"  Result: FAIL ({e})")
