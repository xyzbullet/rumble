Project architecture — Rumble (Python frontend + wisp dataplane)

Goal
----
Build a web-proxy platform (browser-like tab, games, apps) with a Python control plane and UI, and the high-performance Rust wisp-server-rust as the dataplane for extreme throughput. Provide fast fetch-and-rewrite proxying for typical web pages, plus tunnel/proxy support for games and apps.

High-level design
-----------------
- Control plane (Python, FastAPI)
  - Serves the single-page UI and control endpoints
  - Handles user sessions, auth, quotas, and configuration
  - Implements a first-pass HTTP proxy endpoint for fetch-and-rewrite behavior using async httpx
  - Provides WebSocket endpoints for tunneling TCP-style apps and signaling for WebRTC dataplane
  - Responsible for HTML parsing / rewriting orchestration and injecting client shim

- Dataplane (Rust, wisp-server-rust)
  - Modified wisp build to act as a high-performance fetcher, cache and streaming engine
  - Offloads heavy I/O (high throughput TLS termination, zero-copy forwarding, HTTP/2/3) from Python
  - Exposes a compact API/IPC (HTTP/gRPC/local socket) the Python control plane can call to request high-throughput operations

- Client (SPA)
  - Sleek, minimal UI with tabs (Browser, Games, Apps)
  - Communicates with control plane via HTTP and WebSocket
  - Injected client-side shim rewrites subsequent resource loads to go via the proxy endpoints

Key components and responsibilities
-----------------------------------
- HTML Rewriting
  - Use an HTML parser (server-side via Python using an HTML parser or WASM module) to rewrite resource URLs to the proxy origin
  - Rewrite CSP, meta refresh, forms, and set-cookie domain/path attributes as needed
  - Inject a small JS shim to route dynamic fetches through the proxy
  - For modern SPA pages with heavy client-side routing, fall back to a headless or remote rendering path via wisp if necessary

- Resource fetching and streaming
  - Prefer streaming byte-forwarding for non-HTML assets to avoid buffering large files in memory
  - Use efficient async clients (httpx) and connection pools; hand off long-lived, high-throughput flows to wisp

- Games & Apps routing
  - TCP-based apps: WebSocket tunnel proxy (server translates between WS and backend TCP sockets) OR a wisp-managed TCP tunnel
  - UDP/real-time: WebRTC data channels with the server as gateway (use control plane for signaling and wisp/rust for media forwarding)

- CORS and media support
  - Provide permissive, configurable CORS handling on proxy endpoints (with careful security defaults)
  - Support efficient video/image streaming with correct content-type and range requests (pass-through where possible)

Performance considerations
--------------------------
- Python control plane should be mostly lightweight orchestration; avoid heavy I/O and large-buffer streaming in Python for hot paths
- Rust wisp must be extended to support kernel-bypass / zero-copy techniques for target throughput (40 Gb/s target). Expect need for DPDK/AF_XDP, NIC tuning, TLS offload, and horizontal scaling across multiple nodes.

Security and legal
------------------
- Implement authentication, rate-limits, abuse detection
- Respect user privacy and provide clear policies for credential forwarding and cookies
- Implement optional content filtering and DMCA/legal handling workflows

Next steps
----------
1. Create Python prototype skeleton (FastAPI app, simple /proxy endpoint that forwards and streams resources).
2. Define RPC or HTTP API between Python and modified wisp for high-throughput operations.
3. Implement HTML rewrite pipeline and a minimal client-side shim.
4. Add WebSocket tunnel proof-of-concept for TCP apps.
5. Benchmark and iterate; profile hot paths and move them into Rust wisp when needed.

References and inspiration
--------------------------
- Scramjet project (interception-based proxy ideas, WASM-based transformations)
- Various "unblocker" projects on GitHub (fetch-and-rewrite approaches)

