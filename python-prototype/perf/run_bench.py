#!/usr/bin/env python3
"""
Lightweight async benchmark for proxy endpoint.
Sends concurrent GET requests to PROXY_BASE/proxy?url=<target_url> (default target https://example.com)
Writes per-request logs to raw.log and summary to results.json
"""
import asyncio
import json
import os
import time
from statistics import mean, median

try:
    import httpx
except Exception:
    httpx = None

PROXY_BASE = os.environ.get("PROXY_BASE", "http://localhost:8000")
PROXY_PATH = os.environ.get("PROXY_PATH", "/proxy")
TARGET = os.environ.get("TARGET_URL", "https://example.com")
CONCURRENCIES = [1, 5, 10, 20]
RUN_SECONDS = int(os.environ.get("RUN_SECONDS", "10"))
OUT_DIR = os.path.dirname(__file__)
RAW_LOG = os.path.join(OUT_DIR, "raw.log")
RESULTS_JSON = os.path.join(OUT_DIR, "results.json")

URL = f"{PROXY_BASE.rstrip('/')}{PROXY_PATH}?url={TARGET}"


async def worker(client: httpx.AsyncClient, sem: asyncio.Semaphore, results: list, stop_at: float, log_f):
    async with sem:
        while time.perf_counter() < stop_at:
            start = time.perf_counter()
            ts = time.time()
            try:
                resp = await client.get(URL, timeout=10.0)
                # read body to ensure full request
                await resp.aread()
                elapsed = time.perf_counter() - start
                entry = {
                    "t": ts,
                    "latency": elapsed,
                    "status_code": resp.status_code,
                    "len": len(resp.content) if resp.content is not None else None,
                }
            except Exception as e:
                elapsed = time.perf_counter() - start
                entry = {"t": ts, "latency": elapsed, "error": str(e)}
            results.append(entry)
            log_f.write(json.dumps(entry) + "\n")
            log_f.flush()


async def run_one(concurrency: int):
    if httpx is None:
        raise RuntimeError("httpx not installed; please `pip install httpx`")
    results = []
    sem = asyncio.Semaphore(concurrency)
    stop_at = time.perf_counter() + RUN_SECONDS
    async with httpx.AsyncClient() as client:
        # launch N concurrent looping tasks
        tasks = [asyncio.create_task(worker(client, sem, results, stop_at, open(RAW_LOG, "a"))) for _ in range(concurrency)]
        # wait until time elapses
        try:
            await asyncio.gather(*tasks)
        except Exception:
            # ensure cancellation
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
    # compute stats
    latencies = [r.get("latency") for r in results if r.get("latency") is not None and "error" not in r]
    total = len(results)
    duration = RUN_SECONDS
    reqs_per_sec = total / duration if duration > 0 else 0
    mean_latency = mean(latencies) if latencies else None
    median_latency = median(latencies) if latencies else None
    p90 = None
    if latencies:
        lat_sorted = sorted(latencies)
        idx = int(0.9 * len(lat_sorted)) - 1
        idx = max(0, min(idx, len(lat_sorted) - 1))
        p90 = lat_sorted[idx]
    return {
        "concurrency": concurrency,
        "requests": total,
        "reqs_per_sec": reqs_per_sec,
        "mean_latency": mean_latency,
        "median_latency": median_latency,
        "p90_latency": p90,
    }


async def main():
    # prepare logs
    os.makedirs(OUT_DIR, exist_ok=True)
    # truncate raw log
    open(RAW_LOG, "w").close()
    summary = {"url": URL, "run_seconds": RUN_SECONDS, "results": []}
    for c in CONCURRENCIES:
        print(f"Running concurrency={c} for {RUN_SECONDS}s against {URL}")
        try:
            res = await run_one(c)
        except Exception as e:
            print("Error during run:", e)
            res = {"concurrency": c, "error": str(e)}
        summary["results"].append(res)
        # small pause between runs
        await asyncio.sleep(1)
    # write JSON
    with open(RESULTS_JSON, "w") as f:
        json.dump(summary, f, indent=2)
    print("Benchmark complete. Results written to:", RESULTS_JSON)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print("Unhandled error:", exc)
        raise
