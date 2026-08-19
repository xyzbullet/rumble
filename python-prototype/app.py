"""Minimal FastAPI-based proxy prototype.

- /static serves the SPA
- /proxy?url=... forwards the request to the target and streams the response back
- CORS middleware is enabled (configurable)

This is a simple starting point — HTML rewriting and WebSocket/WebRTC tunnels are TODOs in the code.
"""
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import StreamingResponse, FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import asyncio
from urllib.parse import urlparse

app = FastAPI(title="rumble-proxy-prototype")

# Allow all origins for prototype; tighten in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple static SPA route
from pathlib import Path

@app.get("/")
async def index():
    # Resolve static index relative to this file so it works regardless of CWD
    static_index = Path(__file__).parent / "static" / "index.html"
    return FileResponse(str(static_index))

async def stream_response(resp: httpx.Response):
    async for chunk in resp.aiter_bytes():
        yield chunk


# HTML rewrite using BeautifulSoup and optional WASM transform
from bs4 import BeautifulSoup
try:
    import wasmtime
    WASMTIME_AVAILABLE = True
except Exception:
    WASMTIME_AVAILABLE = False

def python_html_rewrite(html_bytes: bytes, base_url: str) -> bytes:
    """Rewrite links and inject a small shim so subsequent requests route through /proxy."""
    try:
        soup = BeautifulSoup(html_bytes, "lxml")
    except Exception:
        soup = BeautifulSoup(html_bytes, "html.parser")

    # Rewrite href/src/action/srcset to proxy endpoint
    def rewrite_attr(tag, attr):
        val = tag.get(attr)
        if not val:
            return
        # ignore data: and javascript: links
        if val.startswith("data:") or val.startswith("javascript:"):
            return
        # build absolute URL using the browser behavior is complex — keep relative URLs as-is but use base when possible
        from urllib.parse import urljoin, quote_plus
        new = urljoin(base_url, val)
        tag[attr] = f"/proxy?url={quote_plus(new)}"

    from urllib.parse import urljoin, quote_plus
    for tag in soup.find_all(True):
        for attr_name in ("href", "src", "action"):
            rewrite_attr(tag, attr_name)
        # srcset handling (basic)
        if tag.has_attr("srcset"):
            parts = []
            for part in tag["srcset"].split(','):
                piece = part.strip().split(' ')[0]
                new = urljoin(base_url, piece)
                parts.append(f"/proxy?url={quote_plus(new)}")
            tag["srcset"] = ','.join(parts)

    # Inject a small shim to rewrite fetch/XHR/fetch calls to go through proxy origin if needed
    shim = soup.new_tag("script")
    shim.string = "(function(){window.__rumble_proxy=true; /* shim placeholder */})();"
    if soup.body:
        soup.body.insert(0, shim)
    else:
        soup.insert(0, shim)

    return str(soup).encode("utf-8")


def run_wasm_transform(html_bytes: bytes, base_url: str) -> bytes:
    """Run a WASM transform if a module is present at transforms/transform.wasm using WASI stdin/stdout.
    Falls back to returning original bytes on failure.
    """
    try:
        if not WASMTIME_AVAILABLE:
            return html_bytes
        module_path = "python-prototype/transforms/transform.wasm"
        import os
        if not os.path.exists(module_path):
            return html_bytes

        # Use wasmtime with WASI to run _start which reads stdin and writes stdout
        store = wasmtime.Store()
        wasi_config = wasmtime.WasiConfig()
        # set stdin to our html_bytes, run module, capture stdout by connecting to pipes is not directly available
        # Instead, use wasmtime's API to instantiate the module and call an exported 'transform' function if present
        module = wasmtime.Module(store.engine, module_path)
        instance = wasmtime.Instance(store, module, [])
        # Expect an exported function 'transform' that accepts i32 ptr/len and returns pointer/len in memory
        try:
            transform = instance.exports(store)["transform"]
        except Exception:
            return html_bytes
        memory = instance.exports(store)["memory"]
        # allocate input in memory by creating a simple allocator at the end — assume module exposes 'alloc' and 'dealloc'
        try:
            alloc = instance.exports(store)["alloc"]
            dealloc = instance.exports(store)["dealloc"]
        except Exception:
            return html_bytes
        # allocate
        inp_len = len(html_bytes)
        inp_ptr = alloc(store, inp_len)
        # write into memory
        buf = memory.data_ptr(store)
        # buf is a pointer to memory; write via ctypes
        import ctypes
        ctypes.memmove(ctypes.c_void_p(buf + inp_ptr), html_bytes, inp_len)
        # call transform(ptr, len) -> out_ptr (i64: high=ptr, low=len) or returns ptr and uses out_len export
        res = transform(store, inp_ptr, inp_len)
        # handle different return shapes
        if isinstance(res, int):
            out_ptr = res
            out_len = instance.exports(store)["out_len"](store)
        elif isinstance(res, tuple) or isinstance(res, list):
            out_ptr, out_len = res
        else:
            return html_bytes
        # read output
        out_buf_ptr = buf + out_ptr
        out_bytes = ctypes.string_at(out_buf_ptr, out_len)
        # free
        try:
            dealloc(store, out_ptr, out_len)
        except Exception:
            pass
        return out_bytes
    except Exception:
        return html_bytes


@app.get("/proxy")
async def proxy_get(url: str):
    # Basic validation
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Only http/https URLs are supported")

    async with httpx.AsyncClient(http2=True, timeout=60.0, limits=httpx.Limits(max_connections=100)) as client:
        try:
            # First attempt a simple GET to obtain headers and decide mode
            try:
                quick = await client.get(url, headers={"User-Agent": "rumble-prototype/0.1"}, timeout=30.0)
                status_code = quick.status_code
                headers = dict(quick.headers)
                content_type = headers.get("content-type", "application/octet-stream")
            except Exception:
                # Fall back to streaming headless mode to avoid blocking
                status_code = 200
                headers = {}
                content_type = "application/octet-stream"

            # Remove or adjust headers that will block embedding
            headers.pop("x-frame-options", None)
            headers.pop("content-security-policy", None)

            # If HTML, buffer, transform (WASM or Python), then respond
            if "text/html" in content_type.lower():
                # Read body with retries/backoff to handle incomplete/chunked upstream closes
                async def fetch_body_with_retries(attempts=3, backoff=0.5):
                    last_exc = None
                    for i in range(attempts):
                        try:
                            async with client.stream("GET", url, headers={"User-Agent": "rumble-prototype/0.1"}, timeout=60.0) as r2:
                                try:
                                    body = await r2.aread()
                                except Exception:
                                    # fallback: collect chunks manually
                                    chunks = []
                                    try:
                                        async for ch in r2.aiter_bytes():
                                            chunks.append(ch)
                                    except Exception as e_inner:
                                        # record inner exception but return whatever collected so far
                                        last_exc = e_inner
                                        if chunks:
                                            return b"".join(chunks), dict(r2.headers), r2.status_code
                                        raise
                                    return b"".join(chunks), dict(r2.headers), r2.status_code
                                return body, dict(r2.headers), r2.status_code
                        except Exception as e:
                            last_exc = e
                            await asyncio.sleep(backoff * (2 ** i))
                    raise last_exc

                try:
                    body, origin_headers, origin_status = await fetch_body_with_retries(attempts=3)
                except Exception as e:
                    raise HTTPException(status_code=502, detail=f"Upstream read failed: {e}")

                # try WASM transform first, then python fallback
                transformed = run_wasm_transform(body, url)
                if transformed == body:
                    # run synchronous python transform in threadpool
                    transformed = await asyncio.get_event_loop().run_in_executor(None, lambda: python_html_rewrite(body, url))

                # Remove content-encoding because we've processed/decompressed the body for transformation
                headers.pop("content-encoding", None)
                # Update content-length to match transformed body
                headers["content-length"] = str(len(transformed))

                return Response(content=transformed, media_type=content_type, headers=headers)

            # For others, buffer the content (safer for prototype) then return
            try:
                async with client.stream("GET", url, headers={"User-Agent": "rumble-prototype/0.1"}, timeout=60.0) as origin_resp:
                    chunks = []
                    async for chunk in origin_resp.aiter_bytes():
                        chunks.append(chunk)
                    content = b"".join(chunks)
                    headers.pop("content-encoding", None)
                    headers["content-length"] = str(len(content))
                    return Response(content=content, status_code=origin_resp.status_code, media_type=content_type, headers=headers)
            except Exception as e:
                raise HTTPException(status_code=502, detail=f"Upstream streaming failed: {e}")

        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=str(e))

# TODO: implement WebSocket-based TCP tunnel endpoint

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8080, reload=True)
