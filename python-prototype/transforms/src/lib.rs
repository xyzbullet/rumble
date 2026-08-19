// Minimal Rust WASM transform crate
// Exposes: alloc(size) -> ptr, dealloc(ptr, size), transform(ptr, len) -> (out_ptr, out_len)
// The transform will prepend a small shim string and copy input bytes into a newly allocated buffer.

#![no_std]
#![feature(lang_items)]

extern crate alloc;
use core::panic::PanicInfo;
use core::ptr;
use core::slice;
use alloc::vec::Vec;

#[panic_handler]
fn panic(_info: &PanicInfo) -> ! {
    loop {}
}

#[no_mangle]
pub extern "C" fn alloc(size: usize) -> *mut u8 {
    let mut v = Vec::with_capacity(size);
    let ptr = v.as_mut_ptr();
    // prevent free
    core::mem::forget(v);
    ptr
}

#[no_mangle]
pub extern "C" fn dealloc(ptr: *mut u8, _size: usize) {
    // In a production crate, implement a proper allocator or use the global allocator.
    // This minimal example does not attempt to free memory safely.
}

#[no_mangle]
pub extern "C" fn transform(ptr: *const u8, len: usize, out_ptr_ptr: *mut u32, out_len_ptr: *mut u32) {
    // Unsafe: copy input bytes and prepend shim
    let shim = b"<script>/*RUMBLE_INJECTED*/</script>";
    unsafe {
        let input = slice::from_raw_parts(ptr, len);
        let total = shim.len() + input.len();
        // allocate output using alloc
        let out_ptr = alloc(total) as *mut u8;
        // copy shim
        ptr::copy_nonoverlapping(shim.as_ptr(), out_ptr, shim.len());
        // copy input
        ptr::copy_nonoverlapping(input.as_ptr(), out_ptr.add(shim.len()), input.len());
        // write back out ptr/len as u32
        *out_ptr_ptr = out_ptr as u32;
        *out_len_ptr = total as u32;
    }
}

// Required stubs for no_std
#[lang = "eh_personality"] extern fn eh_personality() {}
