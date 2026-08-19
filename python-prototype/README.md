Python prototype for Rumble

Run locally for development:

1. Create a virtualenv and install requirements:
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt

2. Run the server:
   uvicorn app:app --reload --port 8080

This prototype implements a fetch-and-stream /proxy endpoint and serves a Sentinel-inspired browser UI at the root route. The UI intentionally matches the browser shell added under sentinel-browser, but keeps the Python proxy as the actual execution layer.

Research notes from MercuryWorkshop projects
-------------------------------------------

Scramjet
- Shipped as an interception-based browser proxy that rewrites content at runtime to bypass CORS and browser restrictions.
- The core idea is not a raw HTTP reverse proxy; it instruments the web page and rewrites assets inside the browser sandbox.
- This is useful for the browser-facing layer of Rumble, especially when we want a single SPA that can safely fetch and re-write pages without exposing raw upstream origins.

Epoxy TLS / Wisp
- epoxy-tls is a browser-JS TLS / proxy project built on top of the Wisp protocol. It demonstrates that encrypted web traffic can be proxied through the browser by running TLS logic in WebAssembly and tunneling through Wisp.
- The key takeaway for Rumble is that a browser-first proxy can safely tunnel TCP streams through a controlled dataplane, while the Python control plane keeps orchestration logic and policy checks.
- In practice: use Python for route policy, HTML rewriting and session plumbing; use a Rust/Wisp server for high-throughput traffic, TLS termination and long-lived streaming.

WispMark
- WispMark benchmarks Wisp server and client implementations using echo tests and reports throughput in MiB/s.
- The results in MercuryWorkshop's benchmark repo are generally in the 1-3 GiB/s range on strong desktop hardware, with a multithreaded Rust/Wisp configuration reaching up to ~4.7 GiB/s in one test configuration.
- 10 Gb/s is roughly 1.25 GB/s (about 1,200 MiB/s) of sustained network throughput. That means Rumble's target is achievable on proper hardware, but it requires a tuned Rust dataplane and a correct network path rather than a pure Python implementation.
- In other words, the benchmark target is realistic: 10 Gb/s is not a far-off ceiling, but it is a system-level performance objective, not just a single-process benchmark number.

Recommended benchmark path
---------------------------

1. Stand up the Rust Wisp server and the client under test.
2. Use WispMark's echo-throughput methodology to establish a baseline.
3. Evaluate the server at 1, 10 and 5x10 parallel streams to measure where saturation begins.
4. Tune the server for kernel-bypass / zero-copy and TLS offload once the baseline is stable.
5. Compare the result to the 10 Gb/s target (about 1.25 GB/s). 

To evaluate the results locally after running WispMark:
  python scripts/wispmark_report.py /path/to/wispmark-results.md

This prints the best sustained throughput and compares it against the 10 Gb/s target.

