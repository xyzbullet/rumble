#!/usr/bin/env python3
"""
Simple HTTP fuzzer (fuzzer2) — performs GET requests with random paths against a list of targets.
Writes results to log2.csv, server errors to server_errors2.log, and a summary to summary2.txt.

Usage: python3 fuzzer2.py --iterations 200 --workers 3
"""
import argparse
import csv
import random
import string
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx


def random_path(max_segments=4, max_len=12):
    segments = []
    for _ in range(random.randint(1, max_segments)):
        seg_len = random.randint(1, max_len)
        seg = ''.join(random.choices(string.ascii_letters + string.digits + "-_~.", k=seg_len))
        segments.append(seg)
    path = '/' + '/'.join(segments)
    # maybe add query
    if random.random() < 0.4:
        qk = ''.join(random.choices(string.ascii_lowercase, k=4))
        qv = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
        path += f'?{qk}={qv}'
    return path


class Fuzzer2:
    def __init__(self, targets, iterations, workers, seed, out_dir='python-prototype/fuzz'):
        self.targets = targets
        self.iterations = iterations
        self.workers = workers
        self.seed = seed
        self.out_dir = out_dir
        random.seed(seed)
        self.lock = threading.Lock()
        self.results = []
        self.server_errors = []
        self.start_time = None

    def _worker_task(self, iteration, client):
        target = random.choice(self.targets)
        path = random_path()
        url = target.rstrip('/') + path
        t0 = time.time()
        try:
            resp = client.get(url, timeout=15.0)
            elapsed = (time.time() - t0) * 1000.0
            status = resp.status_code
            error = ''
            if status >= 500:
                # capture server side error body (truncate to reasonable size)
                body = resp.text
                with self.lock:
                    self.server_errors.append((iteration, url, status, body))
        except Exception as e:
            elapsed = (time.time() - t0) * 1000.0
            status = ''
            error = ''.join(traceback.format_exception_only(type(e), e)).strip()
            with self.lock:
                # record exceptions also as server_errors for visibility
                self.server_errors.append((iteration, url, 'EXCEPTION', error + '\n' + traceback.format_exc()))
        with self.lock:
            self.results.append({
                'iteration': iteration,
                'url': url,
                'status': status,
                'elapsed_ms': int(elapsed),
                'error': error,
            })

    def run(self):
        self.start_time = time.time()
        # Prepare client
        with httpx.Client(follow_redirects=True, headers={"User-Agent": "fuzzer2/1.0"}) as client:
            # Use ThreadPoolExecutor to run tasks
            with ThreadPoolExecutor(max_workers=self.workers) as executor:
                futures = []
                for i in range(1, self.iterations + 1):
                    futures.append(executor.submit(self._worker_task, i, client))

                # wait for completion
                for fut in as_completed(futures):
                    # exceptions handled inside _worker_task; just ensure any unexpected exceptions bubble
                    try:
                        fut.result()
                    except Exception:
                        with self.lock:
                            self.server_errors.append(('internal_exception', '', '', traceback.format_exc()))

        duration = time.time() - self.start_time
        # Write logs
        csv_path = f"{self.out_dir}/log2.csv"
        errors_path = f"{self.out_dir}/server_errors2.log"
        summary_path = f"{self.out_dir}/summary2.txt"

        # write CSV
        with open(csv_path, 'w', newline='', encoding='utf-8') as fh:
            writer = csv.DictWriter(fh, fieldnames=['iteration', 'url', 'status', 'elapsed_ms', 'error'])
            writer.writeheader()
            for r in sorted(self.results, key=lambda x: x['iteration']):
                writer.writerow(r)

        # write server errors
        with open(errors_path, 'w', encoding='utf-8') as fh:
            for err in self.server_errors:
                iteration, url, status, body = err
                fh.write(f"---- ITER {iteration} | STATUS {status} | URL: {url}\n")
                if isinstance(body, str):
                    fh.write(body)
                else:
                    fh.write(repr(body))
                fh.write('\n\n')

        # compute summary
        total = len(self.results)
        successes = sum(1 for r in self.results if isinstance(r['status'], int) and 200 <= r['status'] < 300)
        redirects = sum(1 for r in self.results if isinstance(r['status'], int) and 300 <= r['status'] < 400)
        client_err = sum(1 for r in self.results if isinstance(r['status'], int) and 400 <= r['status'] < 500)
        server_err = sum(1 for r in self.results if isinstance(r['status'], int) and r['status'] >= 500)
        exceptions = sum(1 for r in self.results if r['status'] == '' or r['error'])
        avg_ms = int(sum(r['elapsed_ms'] for r in self.results) / total) if total else 0

        with open(summary_path, 'w', encoding='utf-8') as fh:
            fh.write(f"Fuzzer2 run summary\n")
            fh.write(f"Seed: {self.seed}\n")
            fh.write(f"Targets: {', '.join(self.targets)}\n")
            fh.write(f"Iterations: {self.iterations}\n")
            fh.write(f"Workers: {self.workers}\n")
            fh.write(f"Duration_s: {duration:.2f}\n")
            fh.write(f"Total: {total}\n")
            fh.write(f"Success (2xx): {successes}\n")
            fh.write(f"Redirects (3xx): {redirects}\n")
            fh.write(f"Client errors (4xx): {client_err}\n")
            fh.write(f"Server errors (5xx): {server_err}\n")
            fh.write(f"Exceptions: {exceptions}\n")
            fh.write(f"Avg_elapsed_ms: {avg_ms}\n")
            fh.write('\nTop status codes:\n')
            from collections import Counter
            codes = Counter(r['status'] for r in self.results)
            for code, cnt in codes.most_common():
                fh.write(f"{code}: {cnt}\n")

        return {
            'csv': csv_path,
            'errors': errors_path,
            'summary': summary_path,
            'duration_s': duration,
            'total': total,
        }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run fuzzer2')
    parser.add_argument('--iterations', type=int, default=200)
    parser.add_argument('--workers', type=int, default=3)
    parser.add_argument('--seed', type=int, default=424242)
    args = parser.parse_args()

    targets = [
        'https://example.com',
        'https://httpbin.org',
        'https://iana.org',
        'https://www.rfc-editor.org',
    ]

    f = Fuzzer2(targets=targets, iterations=args.iterations, workers=args.workers, seed=args.seed)
    print(f"Starting fuzzer2: iterations={args.iterations} workers={args.workers} seed={args.seed}")
    res = f.run()
    print(f"Completed: wrote {res['csv']}, {res['errors']}, {res['summary']}")
