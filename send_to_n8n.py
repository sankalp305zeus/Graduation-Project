import json
import sys
import requests

payload_file = sys.argv[1] if len(sys.argv) > 1 else "test-payload.json"
url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:5678/webhook-test/theme-extraction-demo"

with open(payload_file, encoding="utf-8") as f:
    payload = json.load(f)

print(f"Sending {payload_file} to {url} ...")
resp = requests.post(url, json=payload, timeout=7200)
print("Status:", resp.status_code)
print(resp.text[:2000])