import os
import json
import sys
from urllib.parse import quote_plus, urlparse
import httpx

TEST_URLS = [
    "https://example.com",
    "https://httpbin.org/get",
    "https://www.google.com",
]

PROXY_BASE = "http://127.0.0.1:8080/proxy?url="

OUT_DIR = os.path.join(os.path.dirname(__file__), "output")
RESULTS_PATH = os.path.join(os.path.dirname(__file__), "results.json")

os.makedirs(OUT_DIR, exist_ok=True)

results = {}

client = httpx.Client(timeout=30.0)

for url in TEST_URLS:
    host = urlparse(url).hostname or url.replace("https://", "").replace("http://", "").replace("/", "_")
    out_path = os.path.join(OUT_DIR, f"{host}.html")
    entry = {"url": url, "host": host}
    try:
        proxy_url = PROXY_BASE + quote_plus(url)
        resp = client.get(proxy_url)
        entry["status_code"] = resp.status_code
        if resp.status_code != 200:
            entry["ok"] = False
            entry["reason"] = f"Status {resp.status_code}"
        else:
            content = resp.content
            # write output
            with open(out_path, "wb") as f:
                f.write(content)
            entry["saved_path"] = out_path
            # check for HTML
            ct = resp.headers.get("content-type", "")
            if "text/html" in ct.lower() or b"<html" in content.lower():
                entry["ok"] = True
            else:
                entry["ok"] = False
                entry["reason"] = "Not an HTML response"
    except Exception as e:
        entry["ok"] = False
        entry["exception"] = repr(e)
    results[host] = entry

# write results.json
with open(RESULTS_PATH, "w") as f:
    json.dump(results, f, indent=2)

# summary print
passed = sum(1 for v in results.values() if v.get("ok"))
failed = len(results) - passed
print(f"Passed: {passed}, Failed: {failed}")
for k, v in results.items():
    status = "PASS" if v.get("ok") else "FAIL"
    print(f"{k}: {status} - {v.get('reason','')}")

if failed > 0:
    sys.exit(2)
else:
    sys.exit(0)
