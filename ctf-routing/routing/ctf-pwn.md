# CTF Pwn — Binary Exploitation

Scope: binaries/services where you already hold an **executable primitive** — stack and global buffer overflows, format strings, heap allocator exploitation, ROP/SROP, shellcode, kernel module exploitation, sandbox and custom VM escapes, and non-x86 targets such as Windows/ARM.

Out of scope: you have not yet figured out what the binary does (pivot to `ctf-reverse` first); pure web-facing vulnerabilities (`ctf-web`); disk/traffic forensics (`ctf-forensics`); challenges that require breaking a cryptographic primitive first (`ctf-crypto`).

> This file is the **local decision layer**: it references only **filenames** under the `ctf-pwn` skill and does not duplicate their contents.
> Usage: first use `checksec` + `file` to determine protections and architecture, then read only **one** file per the decision tree below; do not open several large files at once.

## File Index

| File | Contents | When to read |
|---|---|---|
| `overflow-basics.md` | Stack/global buffer overflow, ret2win, canary bypass, byte-by-byte canary brute force on forking services, struct pointer overwrite, signed integer bypass, hidden gadgets, stride-style OOB leak, parser stack overflow (unchecked memcpy length + callee-saved register restore) | A stack overflow via `gets`/`scanf("%s")`/`strcpy`; in a menu challenge, adjacent struct pointers are overwritable |
| `rop-and-shellcode.md` | Core ROP: ret2libc, syscall ROP, rdx control, ret2csu, bad-character XOR bypass, obscure gadgets (BEXTR/XLAT/STOSB/PEXT), `xchg rax,esp` stack pivot, sprintf gadget chain, canary XOR epilogue as an RDX zeroing gadget, `stub_execveat` instead of execve | NX is enabled so ROP is needed; `pop rdx`/`pop rax` are unavailable; bad-character filtering is present |
| `rop-advanced.md` | Advanced ROP: double stack pivot to BSS (`leave;ret`), SROP (including UTF-8 constraints), seccomp bypass, RETF to switch x64→x32, input-reversal shellcode, `.fini_array` hijack, ret2vdso, x32 ABI syscall aliases, time-blind exfiltration shellcode | seccomp is in the way; stack space is insufficient and a pivot is needed; the standard chain does not work |
| `format-string.md` | Format string: leaks, GOT overwrite, blind exploitation, filter bypass, canary leak, `__free_hook`, `.rela.plt` rewrite, saved EBP overwrite to pivot to `.bss`, argv[0] overwrite, `.fini_array` loop, `__printf_chk` bypass, single-call leak + GOT overwrite, exploitation when input is ROT13-transformed | `printf(user_input)` is present; there is a leak but the offset is unknown |
| `advanced.md` | Advanced seccomp, UAF, JIT, obscure GOT, heap overlap via base conversion, tree-structure stack underflow allocation, ret2dlresolve, kernel basics | Conventional techniques are blocked; there is no libc leak and ret2dlresolve is needed |
| `heap-techniques.md` | House of Apple 2 (including the setcontext SUID variant), Einherjar, Orange/Spirit/Lore/Force, heap layout shaping, custom allocators (nginx/talloc), classic unlink, musl libc heap (meta pointer + atexit hijack), tcache stashing unlink, unsafe unlink + top chunk consolidation | Heap challenge involving tcache/unsorted bin and House of X techniques |
| `heap-glibc-24x.md` | glibc 2.40-2.43 heap/FSOP status check & corrections: `_IO_wfile_jumps` is **not** removed in 2.41 (measured on Debian trixie 2.41-12, still exported through 2.44-experimental); 2.42 adds large-block tcache via `glibc.malloc.tcache_max` tunable; 2.43 deprecates the whole internal-stdio symbol batch (incl. `_IO_wfile_jumps`/`_IO_file_jumps`/`_IO_list_all`) with a future-removal warning; per-symbol export table (2.41/2.43/2.44); version identification commands; House-of-X vs FSOP decision flow | Heap challenge running on glibc ≥ 2.40 (Ubuntu 24.10/25.04, Debian 13/sid, Fedora 42+), House of Apple 2 appears broken (`nm -D` cannot find `_IO_wfile_jumps`), or a version-dependent FSOP path decision is needed |
| `heap-techniques-2.md` | writeup-style heap variants: UAF vtable pointer encoding for argument passing, uninitialized chunk residual pointer leak, tcache strcpy null-byte overflow + backward consolidation, adjacent struct function pointer overflow, hidden menu tcache poisoning, double-free + forged `_IO_FILE` vtable to hijack stdout, tcache→fastbin cross-bin attack, 6-bit index OOB, IS_MMAPED bit flip to leak from a calloc chunk, fastbin LSB overwrite under a restricted filename regex, custom allocator unsafe unlink against GOT | Heap challenge where the usual House techniques do not apply and a pattern must be found among the writeup-style variants |
| `heap-fsop.md` | `_IO_FILE` exploitation: two-stage fastbin stdout vtable hijack (PIE + Full RELRO), `_IO_buf_base` null-byte hijack of stdin, glibc 2.24+ vtable check bypass, unsorted bin attack on stdin `_IO_buf_end`, `mp_` struct corruption, UAF using `realloc(ptr,0)` as free, single-byte refcount wrap-around UAF | FSOP is needed; stdin/stdout FILE structs are usable; Full RELRO leaves no writable GOT |
| `advanced-exploits.md` | Advanced exploitation part 1: VM signed comparison, BF JIT shellcode, type confusion, off-by-one index corruption, DNS overflow, ASAN shadow memory, encoding-constrained format string, custom canary preservation, canary-aware partial overwrite, CSV injection, MD5 preimage gadget, VM GC UAF, path traversal sanitization bypass, FSOP + seccomp bypass | The target is a custom VM/interpreter/JIT, or an unusual primitive is needed |
| `advanced-exploits-2.md` | part 2: bytecode verifier self-modification bypass, io_uring UAF + SQE injection, int32→int16 truncation, GC null-reference cascading corruption, multi-fgets libc leak without a leak primitive, signed/unsigned char underflow heap overflow, XOR keystream brute-force write primitive, tcache pointer decryption leak, forged chunk size to promote into unsorted bin, FSOP stdout TLS leak, TLS destructor hijack, custom shadow stack pointer overflow, negative OOB heap write, XSS→binary bridge | search by symptom when a specific primitive is needed |
| `advanced-exploits-3.md` | part 3: stack variable overlap/carry corruption causing OOB, 8-bit loop counter causing a 1-byte overflow, game AI mean OOB read, arbitrary read/write against GOT, `__environ`+memcpy stack leak, JIT sandbox uint16 jump truncation escape, DNS compression pointer stack overflow, ELF code-signing bypass, game level signed/unsigned coordinate mismatch, missing fd inheritance of O_CLOEXEC, sign-extension underflow, building ROP from a read-only primitive, 4-byte shellcode + timing side channel, CRC oracle as arbitrary read, UTF-8 case-conversion overflow | same as above; search by symptom |
| `advanced-exploits-4.md` | part 4: Windows SEH overwrite + pushad VirtualAlloc ROP, IAT relative resolution, detached-process shell stability, SeDebugPrivilege escalation, ARM overflow + Thumb shellcode, RISC-V (rv64) exploitation notes, hardware/firmware pwn recognition, Forth interpreter system word, GF(2) Gaussian elimination multi-round tcache poisoning, single-bit flip primitive (mprotect + iterative code patching), Game of Life shellcode evolution, strdup/free ordering UAF, Windows CFG bypass using `system()`, neural network output as function pointer index OOB, unique-byte-count limit defeated through counter overflow | Windows / ARM / RISC-V / hardware-firmware / language-interpreter style pwn |
| `advanced-exploits-5.md` | part 5: data-interpretation exploitation — Chip-8 emulator OOB to ret2libc, double-precision floating-point quicksort canary relocation, Bloom filter `abs(INT_MIN)` negative-index OOB write | emulator, algorithm/data-structure challenges |
| `sandbox-escape.md` | Custom VM exploitation, FUSE/CUSE devices, busybox/restricted shell, shell tricks, `process_vm_readv` sandbox bypass, named pipe file-size bypass, Python eval injection via a CPU emulator's print opcode (cross-reference `ctf-misc/pyjails.md`) | escaping a sandbox/restricted shell/custom VM |
| `browser-pwn.md` | Chromium/V8 engine exploitation: V8 object model (Map/properties/elements kind, pointer compression, V8 sandbox), classic bug classes (array OOB, elements kind confusion, TurboFan/Maglev miscompilation, JSON.parse OOB, string/buffer length tampering), primitive evolution (OOB → addrof/fakeobj → WASM RWX → shellcode; sandbox-era alternatives), d8 workflow (`%DebugPrint`, patch-diff triage, node.js attack surface), renderer→sandbox-escape chain | Chromium/d8/node/V8 engine challenge: given a patched d8, an `exp.js` start, or an engine bug diff — engine/runtime bug exploitation, not classic binary pwn |
| `wasm-pwn.md` | WebAssembly **runtime** exploitation (vs misc game-cheat / reverse wasm2c): linear memory/memory.grow/table & bounds-check failure modes, integer overflow & OOB indexing, table type confusion, runtime-layer bugs (wasmtime/wasm3/wamr, version-specific), WASI capability escape, exploit routes (OOB → function-table/export-pointer control, host import argument injection), identification workflow; cross-references `ctf-misc/games-and-vms*.md` and `ctf-reverse/tools.md` | WASM **runtime vulnerability** rather than a puzzle: `.wasm` + host program (Rust/C) with a runtime version clue, wasm triggers host crash/OOB/type confusion — not "solve the wasm algorithm" (that is reverse) nor game-state cheating (that is misc) |
| `kernel.md` | Kernel exploitation basics: environment setup, QEMU debugging, heap spray structures (tty_struct, poll_list, user_key_payload, seq_operations), kernel stack overflow, canary leak, privilege escalation (ret2usr, kROP), modprobe_path/core_pattern overwrite, kmalloc size mismatch heap overflow + struct file f_op corruption | a kernel module, `/dev/xxx`, or a QEMU launch script is present |
| `kernel-techniques.md` | Advanced kernel: tty_struct kROP (forged vtable + stack pivot), ioctl register control for AAW, userfaultfd race stabilization, SLUB freelist hardening/obfuscation, kernel panic leak, MADV_DONTNEED race window, cross-cache CPU-split, PTE overlap file write, addr_limit failure-path bypass | a kernel challenge is stuck on the basic techniques |
| `kernel-bypass.md` | Kernel protection bypass: KASLR/FGKASLR (`__ksymtab`), KPTI (swapgs trampoline, signal handling, modprobe_path/core_pattern ROP), SMEP/SMAP bypass, kernel module GDB debugging, initramfs/virtio-9p workflow, exploit templates and delivery | a kernel challenge requires bypassing protections first |
| `field-notes.md` | Long-term accumulation: heap exploitation cheat sheet, supplementary exploitation notes, common commands | confirmed to be pwn and a broad cheat sheet is needed (**read last; the largest file**) |

## Decision Tree

- **Check protections first**: No PIE + Partial RELRO → direct GOT overwrite; Full RELRO → target hooks instead (glibc < 2.34)/vtable/return address → `heap-fsop.md` or `format-string.md`
- Stack overflow + no canary → `overflow-basics.md`; a chain is needed → `rop-and-shellcode.md`
- Canary present: leakable → leak first, then ROP; forking service → byte-by-byte brute force → both in `overflow-basics.md`
- NX enabled → ROP (`rop-and-shellcode.md`); chain does not fit → stack pivot (`xchg rax,esp` in `rop-and-shellcode.md` / double pivot in `rop-advanced.md`)
- seccomp present → `rop-advanced.md`; x32/RETF/ret2vdso needed → same file
- No libc leak and no libc file → ret2dlresolve → `advanced.md`
- `printf(user_input)` present → `format-string.md`
- Menu challenge + malloc/free → tcache/unsorted bin → `heap-techniques.md`; FILE structs → `heap-fsop.md`; House of X → `heap-techniques.md`; all conventional techniques fail → `heap-techniques-2.md`
- **glibc ≥ 2.40 的 heap/FSOP 先核对版本**（Ubuntu 24.10/25.04、Debian 13/sid、Fedora 42+）：`ldd --version` + `nm -D libc.so.6 | grep -E 'wfile_jumps|str_jumps|file_jumps|printf_function_table'` 实测符号再选链 —— 2.41 并未移除 `_IO_wfile_jumps`（House of Apple 2 仍可用），2.43 起整批内建 stdio 符号弃用（未来移除预告）；版本依赖的路径决策见 `heap-glibc-24x.md`
- Target is a custom VM/interpreter/JIT/emulator → `sandbox-escape.md` first, then `advanced-exploits.md`, `advanced-exploits-5.md`
- Target is **Chromium/d8/node/V8** (a patched engine build, an engine-bug diff, or an `exp.js` start) → `browser-pwn.md`
- Target is a **WASM runtime vulnerability** (`.wasm` + host program in Rust/C, runtime-version clue, wasm input triggers host crash/OOB/type confusion) → `wasm-pwn.md` — not a wasm puzzle: game-state cheating is `ctf-misc` (`games-and-vms*.md`), solving the wasm algorithm is `ctf-reverse` (`tools.md` wasm2c)
- Kernel module or `/dev/` present → `kernel.md` → stuck → `kernel-techniques.md` → protections not bypassed → `kernel-bypass.md`
- Windows / ARM / RISC-V binary → `advanced-exploits-4.md` (RISC-V details: "RISC-V (rv64) Exploitation Notes" section)
- Firmware/hardware pwn (TPM / secure boot / SMM / glitching / firmware extraction) → read the "Hardware/Firmware Pwn Recognition" section in `advanced-exploits-4.md` first: pure firmware reversing → `ctf-reverse`, code execution inside firmware → this skill
- Unusual primitives such as io_uring / GC / TLS / floating point / races appear → grep by keyword across `advanced-exploits-2.md` through `advanced-exploits-5.md`
- Completely lost → `field-notes.md`

## Common Entry Points

- ret2win (No PIE + no canary) → `overflow-basics.md`
- Two-stage ret2libc (`puts` leak → `system`) → `rop-and-shellcode.md`
- ret2csu (no libc gadgets) → `rop-and-shellcode.md`
- SROP → `rop-advanced.md`; ret2dlresolve → `advanced.md`
- Format string GOT overwrite → `format-string.md`
- tcache poisoning / double free → `heap-techniques.md`, `heap-techniques-2.md`
- House of Apple 2 → `heap-techniques.md`（glibc ≥ 2.40 先核对 `heap-glibc-24x.md` 的符号实测表与 2.43+ 弃用提示）
- `_IO_FILE` vtable hijack → `heap-fsop.md`
- Stack pivot (`xchg rax,esp` / `leave;ret`) → `rop-and-shellcode.md`, `rop-advanced.md`
- modprobe_path / core_pattern overwrite → `kernel.md`, `kernel-bypass.md`
- KASLR / SMEP / SMAP bypass → `kernel-bypass.md`

## Related Directions

- Still unclear what the binary does → `ctf-reverse` (`advanced-exploits-*` involves a lot of VM/bytecode work, but first confirm whether you should pivot to reverse)
- The real difficulty is encodings, restricted shells, or miscellaneous sandboxes → `ctf-misc`
- The exploit chain depends on web endpoints/sessions/uploads → `ctf-web`
- A cryptographic primitive must be broken first → `ctf-crypto` (when routing does not cover it, use the `skill` tool to load `ctf-crypto`)

## Maintenance

- It is linked to the `ctf-pwn` skill through the identically named directory; when files are added or removed upstream, the `## File Index` table in this file must be updated in sync.
- **Important**: `advanced-exploits.md` and `advanced-exploits-2.md` through `advanced-exploits-5.md` are **sharded by date of inclusion**, not classified by topic. When looking for a specific primitive, use `grep` to scan these 6 files by symptom keyword; do not guess contents from the numbering.
