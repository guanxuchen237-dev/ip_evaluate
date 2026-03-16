import requests
import json

url = "http://127.0.0.1:5000/api/ai/report"
payload = {
    "title": "Debug Novel",
    "abstract": "This is a debug abstract to test the SWOT generation capabilities of the AI service."
}

try:
    print(f"Testing {url}...")
    response = requests.post(url, json=payload, timeout=60)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
except Exception as e:
    print(f"Error: {e}")
