import csv
import random
import string
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

PROXY_URL = "http://127.0.0.1:8080/proxy"
TARGETS = [
    "https://example.com",
    "https://httpbin.org",
    "https://iana.org",
    "https://www.rfc-editor.org",
]

ITERATIONS = 200
WORKERS = 3
LOG_CSV = "python-prototype/fuzz/log.csv"
SERVER_ERRORS_LOG = "python-prototype/fuzz/server_errors.log"
SUMMARY = "python-prototype/fuzz/summary.txt"

lock = threading.Lock()


def random_path():
    # generate a short random path like /a1b2
    length = random.randint(1, 6)
    return "/" + "".join(random.choices(string.ascii_letters + string.digits, k=length))


def make_request(session, target):
    url = target + random_path()
    data = {"url": url}
    try:
        # send via proxy endpoint as POST with target url in body
        resp = session.post(PROXY_URL, json=data, timeout=10)
        status = resp.status_code
        length = len(resp.content)
        exc = ""
    except Exception as e:
        status = None
        length = 0
        exc = str(e)
    return url, status, length, exc


def main():
    # prepare CSV with header
    with open(LOG_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["url", "status", "response_length", "exception"])

    successes = 0
    failures = 0
    server_errors = []

    session = requests.Session()

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futures = [ex.submit(make_request, session, random.choice(TARGETS)) for _ in range(ITERATIONS)]
        for fut in as_completed(futures):
            url, status, length, exc = fut.result()
            with lock:
                with open(LOG_CSV, "a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow([url, status, length, exc])

            if exc:
                failures += 1
            elif status is None:
                failures += 1
            elif 500 <= int(status) <= 599:
                failures += 1
                server_errors.append((url, status))
            else:
                successes += 1

    # if server_errors or failures > 0, gather /tmp/copilot-detached-*.log
    if server_errors or failures > 0:
        import glob

        logs = glob.glob('/tmp/copilot-detached-*.log')
        if logs:
            with open(SERVER_ERRORS_LOG, 'w', encoding='utf-8') as out:
                for p in logs:
                    out.write(f"=== {p} ===\n")
                    try:
                        with open(p, 'r', encoding='utf-8', errors='replace') as inp:
                            out.write(inp.read())
                    except Exception as e:
                        out.write(f"Error reading {p}: {e}\n")
                    out.write('\n')

    # write summary
    with open(SUMMARY, 'w', encoding='utf-8') as s:
        s.write(f"total_iterations,{ITERATIONS}\n")
        s.write(f"workers,{WORKERS}\n")
        s.write(f"successes,{successes}\n")
        s.write(f"failures,{failures}\n")
        s.write(f"server_errors_count,{len(server_errors)}\n")
        if server_errors:
            for url, status in server_errors:
                s.write(f"server_error,{url},{status}\n")


if __name__ == '__main__':
    main()
