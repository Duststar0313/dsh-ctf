# CTF Reverse — Reverse Engineering

Scope: **figure out how the target works first**, before exploiting it — native binaries, obfuscated/packed/virtualized targets, APK/WASM/firmware/bytecode, custom VMs, game clients, anti-debug and anti-analysis logic, scripts and esolangs.

Out of scope: the vulnerability is already clear and what remains is getting a shell (pivot to `ctf-pwn`); disk/traffic/log forensics (`ctf-forensics`); the web application itself (`ctf-web`); model attacks (`ctf-ai-ml`); C2/evasion for real malware samples (`ctf-malware`).

> This file is the **local decision layer**: it references only **filenames** under the `ctf-reverse` skill and does not duplicate their contents.
> Usage: **first try the "zero-cost three steps" below**, then decide which file to read; do not open a decompiler and go file by file right away.

## File Index

| File | Contents | When to read |
|---|---|---|
| `tools.md` | Static analysis tools: GDB, Ghidra, radare2, IDA, Binary Ninja, dogbolt.org decompiler comparison, RISC-V+Capstone, Unicorn emulation, Python bytecode, WASM (incl. WASI/Component Model), Android APK, .NET, packed binaries | Need to choose/use static tools; target is WASM/WASI/APK/.NET/packed |
| `tools-dynamic.md` | Dynamic tools: Frida (hooks, anti-debug bypass, memory scanning, Android/iOS), angr symbolic execution (path exploration, constraints, CFG), lldb, x64dbg | Want to get the flag **without reversing** (hook `strcmp`/`memcmp`); the decision logic suits symbolic execution |
| `tools-emulation.md` | Emulation and side channels: Qiling (cross-platform OS-level emulation), Triton (DSE), Intel Pin instruction counting + genetic-algorithm side channel, opcode-trace-only reconstruction, LD_PRELOAD frozen time + `memcmp` side-channel byte-by-byte brute force | Foreign-architecture binaries; very heavy anti-debugging; need a byte-by-byte side channel |
| `unicorn-emulation.md` | Unicorn Engine deep-dive: when Unicorn beats GDB/angr/Qiling, setup scaffold, hook cookbook, ARM/MIPS/Thumb, mixed-mode 64→32 via `retf`, firmware MMIO, snapshot & fork brute-force oracles, coverage and timeout tuning, threading and self-modifying code, GDB stub integration, performance, Keystone+Unicorn trace inversion, shellcode unpacking, custom VM emulation, Qiling-vs-Unicorn decision tree, emulator comparison table, pitfalls, worked examples | You are emulating raw shellcode / a bare-metal or firmware blob / a custom VM, or you need a fast fork-based brute-force oracle rather than full symbolic execution |
| `tools-advanced.md` | Advanced tools part 1: VMProtect/Themida analysis, binary diffing (BinDiff/Diaphora), deobfuscation frameworks (D-810, GOOMBA, Miasm), Qiling, Triton DSE, Manticore, Rizin/Cutter, RetDec, custom VM bytecode lifting to LLVM IR, MLIR and modern LLVM pass deobfuscation | Need to fight obfuscation/packing; need VM bytecode lifting; `.mlir` artifacts or LLVM `opt -passes=` deobfuscation |
| `tools-advanced-2.md` | Advanced tools part 2: advanced GDB (Python scripting, brute force, conditional breakpoints, watchpoints, rr reverse debugging, pwndbg/GEF), advanced Ghidra scripting, patching (Binary Ninja API, LIEF), GDB constraint extraction + ILP solving, positional-encoding input zero-flag monitoring, LD_PRELOAD dumping execute-only binaries, PEDA grabbing the flag bit by bit | Need scripted GDB, automated constraint extraction, or patching |
| `anti-analysis.md` | Anti-analysis overview: Linux anti-debugging (ptrace, /proc, timing, signals, direct syscalls), Windows anti-debugging (PEB, NtQueryInformationProcess, heap flags, TLS callbacks, breakpoint detection, exceptions, thread hiding), anti-VM/sandbox (CPUID, MAC, timing, traces), anti-DBI (Frida detection and bypass), self-checksumming, anti-disassembly (opaque predicates, junk bytes), MBA identification and simplification | Program detects debuggers/sandboxes, refuses to run, or behaves abnormally |
| `anti-analysis-ctf.md` | CTF-practical anti-analysis: SIGILL handler switching execution mode, SIGFPE side channel (strace counting), Keystone+Unicorn instruction-trace inversion, stack-frame manipulation to implement a call-free chain, parent process patching a child binary dump | The anti-analysis trick is very specific but you cannot name it |
| `patterns.md` | Basic patterns: custom VM, anti-debugging, nanomite, self-modifying code, XOR ciphers, mixed-mode stager, LLVM obfuscation, S-box/keystream, SECCOMP/BPF, exception handlers, memory dump, byte-by-byte transforms, x86-64 pitfalls, custom mangle, position-dependent transforms, hex-encoded string comparison, signal-based exploration | There is a VM/obfuscation/self-modification but you do not know the specific trick |
| `patterns-runtime.md` | Runtime patching and oracles: malware anti-analysis bypass, multi-stage shellcode loader, timing side channel, multithreaded anti-debugging (decoy + signal MBA), INT3 patching + coredump brute-force oracle, signal chain + LD_PRELOAD oracle, printf format-string VM decompilation to Z3, quadtree recursive image format parsing | Need to rely on oracles/brute force/runtime patching rather than static analysis |
| `patterns-ctf.md` | Competition patterns part 1: hidden emulator opcodes, LD_PRELOAD key extraction, SPN static extraction, image XOR smoothness, byte-by-byte cipher, mathematical convergence bitmap, PE XOR bitmap OCR, two-stage RC4+VM loader, GBA ROM meet-in-the-middle, Sprague-Grundy game, kernel module maze, multithreaded VM channel, backdoor shared-library string diff, custom binfmt kernel module + RC4 flat binary, hash-resolved imports/no-import ransomware, ELF section header corruption | grep this file family by symptom |
| `patterns-ctf-2.md` | part 2: multi-layer self-decryption brute force, embedded ZIP+XOR license, stack string deobfuscation, prefix hash brute force, integer validation via CVP/LLL lattice, decision-tree function obfuscation, GF(2^8) Gaussian elimination, ROP chain obfuscation (ROPfuscation) analysis | same as above, search by symptom |
| `patterns-ctf-3.md` | part 3: Z3 one-line Python circuit, sliding-window popcount, keyboard LED Morse code (ioctl), C++ destructor hidden check, syscall side-effect memory corruption, MFC dialog event handling, VM sequential keychain brute force, BWT inverse transform, OpenType font ligature exploitation, GLSL shader VM self-modification, instruction count as cryptographic state, objdump batch crackme automation, fork+pipe+dead-branch anti-analysis, TensorFlow DNN sigmoid layer inversion, BPF analyzed by way of kernel JIT to x64 | same as above, search by symptom |
| `languages.md` | Language-specific: Python bytecode and opcode remapping, Python version differences, Pyarmor static unpacking, DOS stub, Unity IL2CPP, HarmonyOS HAP/ABC, Brainfuck/esolang (character-by-character static analysis, read-count side-channel oracle, comparison idiom detection), UEFI, transpiling to C, coverage side channel, OPAL functional reversing, non-bijective substitution, FRACTRAN program inversion | Target is bytecode/script/esolang |
| `languages-platforms.md` | Platforms and frameworks: Roblox place files, Godot resource extraction, Rust serde_json schema recovery, Android JNI RegisterNatives obfuscation, DEX runtime bytecode patching (`/proc/self/maps`), native .so loading bypass, Frida bypassing Firebase Cloud Functions, Verilog/hardware RE, prefix hash inversion, Ruby/Perl polyglot constraint solving, Electron ASAR extraction, Node.js npm runtime introspection, React Native / Hermes (.hbc) | Target is a game/mobile/frontend framework artifact; RN/Hermes `.bundle`/`.hbc` |
| `languages-compiled.md` | Compiled languages: Go (GoReSym, goroutines, memory layout, channels, embed.FS, UUID patching), Rust (demangle, Option/Result, Vec, panic strings), Swift (demangle, protocol witness table), Kotlin/JVM coroutine state machines, Haskell GHC CMM, C++ (vtable reconstruction, RTTI, STL patterns) | Target is a compiled language such as Go/Rust/Swift/C++ |
| `platforms.md` | Platforms: macOS/iOS (Mach-O, code signing, ObjC runtime, Swift, dyld, jailbreak bypass), embedded/IoT firmware (binwalk, UART/JTAG/SPI, ARM/MIPS, RTOS), kernel drivers (Linux `.ko`, eBPF, Windows `.sys`), game engines (Unreal, Unity, anti-cheat, Lua), automotive CAN bus | Target is firmware/driver/mobile/game engine |
| `platforms-hardware.md` | Hardware and architectures: HD44780 LCD controller GPIO reconstruction, advanced RISC-V (custom extensions, privileged mode, debugging), ARM64/AArch64 reversing and exploitation (calling conventions, ROP gadgets, qemu-aarch64-static) | There is a hardware, RISC-V, or ARM64 target |
| `field-notes.md` | Quick reference: binary types, anti-debug bypass, specialized patterns, CTF case notes, AI/LLM-assisted RE workflow | After the target type is confirmed, when you need a broad quick reference (**read last**); AI/LLM-assisted RE for large/obfuscated binaries |

## Decision Tree

**Zero-cost three steps (do these first; many challenges end here)**

1. `strings binary | grep -iE "flag|CTF\{"` (alternatively `rabin2 -z`, `xxd | grep`)
2. `ltrace ./binary` and `strace -f -s 500 ./binary` — dynamic analysis often exposes the flag directly
3. Run it once with arbitrary input and observe the output and comparison behavior

**Then branch by target characteristics**

- Want to bypass manual reversing → Frida hook `strcmp`/`memcmp`, or go straight to angr → `tools-dynamic.md`
- Foreign architecture (MIPS/ARM/RISC-V) or excessive anti-debugging → Qiling emulation → `tools-emulation.md`; ARM64 details → `platforms-hardware.md`
- Known file format → Python bytecode/WASM/APK/.NET/Roblox/Godot/Electron → `languages.md`, `languages-platforms.md`
- Traces of a compiled language (Go symbols, Rust panic strings, Swift demangle, C++ vtable/RTTI) → `languages-compiled.md`
- Custom VM, obfuscation, self-modifying code → `patterns.md`; opaque predicates/MBA simplification → `anti-analysis.md`
- Program detects debuggers, refuses to run, or behaves abnormally → `anti-analysis.md`; trick is bizarre but specific → `anti-analysis-ctf.md`
- The decision depends on "is it right" rather than "what does it equal" (needs an oracle/brute force/patching) → `patterns-runtime.md`
- The core of the decision is hashes/lattices/GF(2^8)/can be handed to Z3 → `patterns-ctf-2.md`, `patterns-ctf-3.md`
- Packing, VMProtect/Themida, need a deobfuscation framework → `tools-advanced.md`; need scripted GDB/automated constraint extraction/patching → `tools-advanced-2.md`
- Firmware/kernel driver/mobile/game engine → `platforms.md`
- None of the above is certain → `field-notes.md` (quick reference by binary type)
- Large stripped/obfuscated binary where *understanding* (not solving) is the bottleneck → `field-notes.md` (AI/LLM-assisted RE); `.mlir`/MLIR traces → `tools-advanced.md`; RN/Hermes `.hbc` → `languages-platforms.md`; WASI module → `tools.md`

## Common Entry Points

- **Comparison-direction determination (do first; decides the whole solution direction)**: `transform(flag) == stored` → you need the inverse transform; `transform(stored) == flag` → the flag is the transformed data, so apply the transform to stored directly
- **Memory dump strategy**: let the program compute the answer itself and then dump it — break at the **final comparison**, supply arbitrary input of the correct length, and read out the computed flag with `x/s $rsi`
- **Decoy flags**: when several consecutive comparison targets appear, break at the **last** comparison, not the fake ones before it
- **PIE debugging**: `start` first to let the base address resolve, then use a relative breakpoint `b *main+0xCA`
- Single-byte XOR → brute force all 256; known plaintext (`flag{`) → directly XOR to derive the key
- Position-dependent transforms (`^ i`, `^ (i & 0xff)`) combined with a repeating key → cancel the position term first, then handle the key
- Byte-by-byte comparison logic → LD_PRELOAD/side-channel byte-by-byte brute force (`tools-emulation.md`)
- Pure Python decision circuit → Z3 (`patterns-ctf-3.md`)
- Brainfuck/esolang → `languages.md` (including the read-count oracle)
- Android/APK anti-debugging → `tools-dynamic.md` + `languages-platforms.md`

## Related Directions

- You already understand the binary and need heap/ROP/kernel exploitation → `ctf-pwn`
- It is actually recovering deleted files, PCAPs, or disk traces → `ctf-forensics`
- It is just reversing a small client-side script inside a web application → `ctf-web`
- The binary implements an ML model and what is being tested is model attacks/adversarial inputs → `ctf-ai-ml`
- The core logic is a cryptographic algorithm or a math problem → `ctf-crypto`
- It is a real malware sample (C2, evasion, delivery) → `ctf-malware`
- It is just a toy VM, an encoding challenge, a pyjail → `ctf-misc`

## Maintenance

- Associated with the `ctf-reverse` skill through a directory of the same name; when files are added or removed upstream, the `## File Index` table in this file must be updated to match.
- **Important**: `patterns-ctf.md`, `patterns-ctf-2.md`, `patterns-ctf-3.md` and `tools-advanced.md` / `tools-advanced-2.md` are **sharded by inclusion time**, not classified by topic. When looking for a specific technique, use `grep` to scan the whole file family by symptom keywords; do not guess contents by number.
- `anti-analysis.md` is the overview and `anti-analysis-ctf.md` is the concrete writeup: first check the overview to determine the category, then go to the CTF one to find the same-named technique.
