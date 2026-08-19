Rust -> WASM transform

This folder contains a sample Rust crate that can be compiled to a WebAssembly module for use by the Python wasmtime pipeline.

Build instructions (on a machine with Rust toolchain):

1. Install the wasm target:
   rustup target add wasm32-unknown-unknown

2. Build release wasm:
   cargo build --release --target wasm32-unknown-unknown -p transform

3. The compiled wasm will be in:
   target/wasm32-unknown-unknown/release/transform.wasm

Copy the resulting transform.wasm to python-prototype/transforms/transform.wasm to have the Python pipeline use it.

Notes:
- The sample crate exposes three C-style exports: alloc(size) -> ptr, dealloc(ptr, size), and transform(ptr, len) -> (out_ptr, out_len).
- The transform function prepends an injected shim and copies the input bytes; it is intentionally small and safe for demonstration.
- For production use, consider compiling with memory/size limits and testing thoroughly.
