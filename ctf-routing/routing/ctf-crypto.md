# CTF Crypto — Cryptography and Mathematics

Scope: encryption, hashing, signatures, randomness, key exchange, zero-knowledge proofs, lattices and number theory — including attacks on classical hand ciphers and modern protocols, plus "non-standard" challenges where a mathematical structure is used as a cipher.

Out of scope: the algorithm is embedded in a custom VM/obfuscated binary and the difficulty lies in understanding the program (pivot to `ctf-reverse`); crypto is only one part of a Web challenge (pivot to `ctf-web`); encrypted C2 traffic (pivot to `ctf-malware`).

> This file is the **local decision layer**: it references only **filenames** under the `ctf-crypto` skill and does not duplicate their contents.
> Usage: **fingerprint the algorithm first** (constants, S-box, state update form), then follow the decision tree to read only the one corresponding file.

## File Index

| File | Contents | When to read |
|---|---|---|
| `classic-ciphers.md` | Classical ciphers: Vigenère (including Kasiski), Atbash, substitution wheels, XOR variants (multi-byte frequency analysis), deterministic OTP, cascaded XOR, book ciphers, OTP key reuse/many-time pad, homophonic substitution, grid permutation, image Caesar, XOR key recovery from file headers | Hand ciphers, substitution/shift, XOR reuse |
| `modern-ciphers.md` | Modern ciphers: AES (CFB-8, ECB leakage), CBC-MAC/OFB-MAC, padding oracle, S-box collisions, GF(2) elimination, partial LCG output, composite-modulus affine, AES-GCM derived keys and **nonce reuse (forbidden attack)**, Ascon-like reduced-round differential, custom linear MAC forgery, Bleichenbacher PKCS#1 v1.5 (ROBOT), birthday/meet-in-the-middle, CRC32 collision forgery, byte-by-byte zeroing oracle to recover an AES key | Modern block ciphers, MACs, oracle-class attacks |
| `modern-ciphers-2.md` | Modern ciphers part 2: Blum-Goldwasser bit-extension oracle, hash length extension, compression oracle (CRIME-style), hash time reversal (cycle detection), OFB reverse decryption, weak KDF (public-key hash XOR), HMAC-CRC linearity, DES weak keys under OFB, SRP bypass, AES brute force with a modified S-box, reduced-round AES square attack, **AES-ECB byte-by-byte chosen plaintext**, ECB cut-and-paste, CBC IV bit-flip auth bypass, Rabin parity oracle, PBKDF2 pre-hash bypass, MD5 multicollisions | Block mode misuse, hash/MAC construction problems |
| `modern-ciphers-3.md` | Modern ciphers part 3: custom hash state inversion, small-payload CRC32 brute force, noisy RSA LSB oracle error correction, sponge hash MITM collision, CBC IV forgery + block truncation, padding oracle to CBC bit-flip RCE, SPN S-box intersection attack, AES-CFB IV recovery with timestamp-seeded PRNG, three-round XOR protocol key cancellation, AES-CBC UnicodeDecodeError side channel, SHA-256-based attack to bypass XOR aggregate hash, custom MAC forgery via XOR block cancellation, HMAC key recovery via XOR+addition | Variants not covered by the above files, search by symptom |
| `stream-ciphers.md` | Stream ciphers: LFSR (Berlekamp-Massey, correlation attack, known plaintext, Galois vs Fibonacci, autocorrelation tap recovery), RC4 second-byte bias, XOR adjacent-byte correlation | Stream ciphers, LFSR, RC4 |
| `dh-attacks.md` | Classic finite-field Diffie-Hellman: triage order, trivial generators (`g = 0/1/p-1`, peer values `A = 0/1/p-1/p`), Pohlig-Hellman when `p-1` is smooth (hand-rolled BSGS per prime-power + CRT), small-subgroup confinement / Lim-Lee static-key recovery via CRT, oracle shapes, static vs ephemeral, Logjam / export-grade downgrade triage | Parameters are a prime `p`, a generator `g`, and public values — a key exchange rather than RSA/ECC |
| `rsa-attacks.md` | RSA: small e (cube root), common modulus, Wiener, Pollard p−1, Håstad broadcast, linear-padding Håstad (Coppersmith), Franklin-Reiter related messages, Coppersmith linearly related primes, Fermat/adjacent primes, multi-prime, constrained digits, structured primes, Manger oracle, polynomial hashing | Abnormal RSA parameters or an oracle present |
| `rsa-attacks-2.md` | RSA special topics: p=q validation bypass, CRT cube root when `gcd(e,phi)>1`, factoring from a multiple of phi, multiplicative homomorphic signature forgery, weak key generation via base representation, exponent reduction, batch GCD shared primes, partial key recovery from dp/dq/qinv, **RSA-CRT fault attack**, homomorphic decryption oracle bypass, CRT factoring with small primes, Montgomery timing, Bleichenbacher low-exponent signature forgery, signature bypass with e=1 and a crafted modulus | RSA variants not covered above |
| `ecc-attacks.md` | ECC: small subgroups, invalid curves, Smart attack (anomalous curves, with Sage code), fault injection, clock group DLP, Pohlig-Hellman, **ECDSA nonce reuse**, Ed25519 torsion side channel, DSA nonce reuse, DSA key recovery when k generation uses an MD5 collision | Elliptic curves/DSA/ECDSA |
| `zkp-and-advanced.md` | ZKP and graph 3-coloring, Z3 solving guide, garbled circuits, Shamir secret sharing, two-letter constraint solving, races, broken Groth16 setup, DV-SNARG forgery, KZG pairing oracle permutation recovery, Shamir reused polynomial coefficients | Zero-knowledge proofs, secret sharing, constraint solving |
| `prng.md` | Randomness basics: MT19937, MT floats recovered via GF(2) magic matrix to predict tokens, LCG, GF(2) matrix PRNG, V8 XorShift128+ state recovery via Z3, middle-square, hill climbing, random-mode oracle, time seed, C `srand/rand` synced through ctypes, password cracking, logistic chaotic PRNG | Output sequence looks random and can be sampled in quantity |
| `prng-attacks.md` | Randomness CTF in practice: MT subset-sum seed recovery, MT19937 constraint propagation, Rule 86 cellular automaton inversion via Z3, Java LCG meet-in-the-middle, LCG modular inverse rollback, LFSR bit-folding ASCII parity, Z3 solving-time oracle, randcrack predicting DSA k, format-string offset seed, NTP poisoning UUID XOR | PRNG variants not covered above |
| `historical.md` | Historical ciphers (Lorenz SZ40/42, book cipher implementation) | WWII/mechanical cipher challenges |
| `advanced-math.md` | Mathematical attacks: isogenies, Pohlig-Hellman, BSGS for generic DLP, LLL, Merkle-Hellman knapsack via LLL, Coppersmith, quaternion RSA, GF(2)[x] CRT, S-box collision code, LWE lattice CVP, non-prime modulus affine, GF(2) linear algebra introspective CRC | Number theory/lattice tooling needed but unsure where to start |
| `lattice-and-lwe.md` | Lattice attack triage and workflow: LLL/BKZ/Babai, HNP with partial or biased nonces, truncated LCG state recovery, LWE embedding and CVP, Ring-LWE/Module-LWE identification, orthogonal lattices, subset sum/knapsack, common failure modes | You have decided a lattice is needed, but are unsure which construction |
| `exotic-crypto.md` | Non-standard algebraic structures: braid group DH/Alexander polynomial, monotone function inversion, tropical semiring residuals, Paillier, Hamming-code spiral interleaving, ElGamal generic re-encryption, FPE Feistel brute force, icosahedral symmetry group cipher, Goldwasser-Micali duplication oracle | The cipher is built on an unfamiliar algebraic structure |
| `exotic-crypto-2.md` | Non-standard structures part 2: BB-84 QKD MITM, ElGamal trivial DLP (B=p−1), Paillier LSB oracle (homomorphic doubling), differential privacy noise cancellation, homomorphic encryption bit extraction, matrix ElGamal via Jordan normal form, OSS signature forgery via Pollard, Cayley-Purser keyless decryption, BIP39 partial mnemonic checksum brute force, Asmuth-Bloom CRT threshold recovery, polynomial-prime Rabin, LCG period detection, Vandermonde coefficient recovery, **FHE recognition (BFV/BGV/CKKS/TFHE/FHEW)** | Same as above, search by structural features; **scheme names BFV/BGV/CKKS/TFHE/FHEW/SEAL/OpenFHE, a parameter file with N/t/q/sigma, huge ciphertexts, or a homomorphic op interface (`add`/`mul`/`scalar_mult`)** |
| `modern-ciphers-4.md` | Modern ciphers part 4: ChaCha20-Poly1305 nonce reuse (forbidden attack over 2^130−5, RFC 8439), partitioning-oracle / key-committing AEAD and ciphertext splitting via lattice, sponge-construction generality (SHA-3 / Keccak / Ascon / Gimli / Sparkle) with rate/capacity/rounds/pad table and endianness workflow, eSTREAM Trivium (1152-round warmup) and Grain cube-attack outline | AEAD nonce reuse, sponge/hash-construction generality, or a lightweight stream cipher (Trivium/Grain) |
| `post-quantum.md` | Post-quantum recognition **and attacks**: Module-LWE / ML-KEM (Kyber) identification, flattening Module-LWE to plain LWE, **ML-DSA (Dilithium) parameter table (q=8380417, gamma1/gamma2, c-tau, FIPS 204 sizes) with nonce-bias/HNP, message-flooding, verifier-bug forgery and fault-attack notes**, **SPHINCS+/SLH-DSA (FIPS 205) parameter/size table with one-time-key reuse and state-reset attack surface**, estimator usage | Parameters look like a PQC scheme — **a PQC signature challenge (ML-DSA / SPHINCS+) rather than a KEM**, or an ML-KEM/Module-LWE instance |
| `ai-assisted-crypto.md` | AI/LLM-camouflaged crypto **recognition** (2025-2026): ML model as the cipher (weights are the "ciphertext" → pivot `ctf-ai-ml/model-attacks.md`), LLM-assisted encrypt/sign protocols (prompt injection for keys → `ctf-ai-ml/llm-attacks.md` + `ctf-web/ai-agentic-web.md`), ML side channels (power/timing traces → `ctf-forensics/signals-and-hardware.md`), clickbait "AI crypto" (classic underneath → stay here) | Challenge title or payload mentions AI/ML/LLM/neural crypto and you must decide: pivot to `ctf-ai-ml` vs solve classic crypto underneath |

## Decision Tree

**Step 1: Identify the algorithm** (determines which line to follow afterwards)

- S-box `0x637c777b` → AES; `expand 32-byte k` → ChaCha20; `0x9E3779B9` → TEA/XTEA; sequential S-box initialization → RC4
- Seeing an `n`, `e`, `c` triple → RSA; seeing curve parameters/points → ECC; seeing `p`, `q`, `g`, `y` → DLP/ElGamal
- The output is "a string of numbers that looks random" and can be sampled repeatedly → PRNG

**Step 2: Triage by symptom**

- Hand-solvable substitution/shift/permutation, or OTP reuse → `classic-ciphers.md`; mechanical/historical ciphers → `historical.md`
- Block cipher mode misuse (repeated ECB blocks, CBC bit-flipping, predictable IV) → `modern-ciphers.md`; AES-ECB byte-by-byte chosen plaintext → `modern-ciphers-2.md`
- A decryption/padding error oracle exists → padding oracle / Bleichenbacher → `modern-ciphers.md`; noisy or side-channel-style oracle → `modern-ciphers-3.md`
- AEAD nonce reused (GCM) → forbidden attack → `modern-ciphers.md`
- Suspicious hash/MAC construction (concatenated key, CRC as MAC, length-extendable) → `modern-ciphers-2.md`, `modern-ciphers-3.md`
- Stream cipher/LFSR/RC4 → `stream-ciphers.md`
- Abnormal RSA parameters (small e, common modulus, adjacent primes, multi-prime, constrained digits) → `rsa-attacks.md`
- RSA has an oracle (LSB/Manger/homomorphic) or fault injection → `rsa-attacks.md`, `rsa-attacks-2.md`
- Recovery from partial private key parameters (dp/dq/qinv) → `rsa-attacks-2.md`
- Suspicious ECC curve (anomalous, singular, small subgroup, invalid curve) or ECDSA/DSA nonce reuse → `ecc-attacks.md`
- SMT solving needed (constraints explicit, small scale) → Z3 guide → `zkp-and-advanced.md`
- ZKP/circuits/secret sharing/commitments → `zkp-and-advanced.md`
- PRNG state recoverable (MT19937, LCG, XorShift128+, time seed) → `prng.md`; variants → `prng-attacks.md`
- You have decided "this needs a lattice" → `lattice-and-lwe.md`; a concrete tool such as LLL/BSGS/Coppersmith is needed → `advanced-math.md`
- PQC-looking constants (`q=3329`/`8380417`, small `k/l` ranks, `FORS`/`WOTS`/`SPHINCS+` strings, tiny pk + huge signature) → `post-quantum.md` — for **signatures** (ML-DSA nonce/verifier bugs, SPHINCS+ one-time-key reuse) just as much as for KEM (ML-KEM)
- The cipher is built on an unfamiliar algebraic structure (braid group, tropical semiring, matrix group, coding) → `exotic-crypto.md`, `exotic-crypto-2.md`
- FHE smell: scheme names (BFV/BGV/CKKS/TFHE/FHEW/SEAL/OpenFHE), parameter file with N/t/q/sigma, huge ciphertexts, homomorphic op interface (`add`/`mul`/`scalar_mult`) → `exotic-crypto-2.md` (FHE section: attack the **weakened parameters** or **interface abuse**, never "break" FHE itself; tiny q/N → lattice, see `lattice-and-lwe.md`)
- Title or payload mentions AI/LLM/neural crypto → read `ai-assisted-crypto.md` first: ML model as cipher / LLM holds the key → pivot `ctf-ai-ml`; power/timing traces → `ctf-forensics` side channel; "AI" only as flavor on a classic payload → stay here and run the standard flow
- None of the above → look it up again using the algorithm's features: `grep` the keywords across the files above

## Common Entry Points

- Full-block padding oracle decryption → `modern-ciphers.md`
- Bleichenbacher / ROBOT → `modern-ciphers.md`
- AES-ECB byte-by-byte chosen plaintext → `modern-ciphers-2.md`
- AES-GCM nonce reuse (forbidden attack) → `modern-ciphers.md`
- Hash length extension → `modern-ciphers-2.md`
- Small-e cube root / Håstad broadcast → `rsa-attacks.md`
- Coppersmith (linear padding, structured primes) → `rsa-attacks.md`
- Wiener / Pollard p−1 / Fermat → `rsa-attacks.md`
- RSA-CRT fault attack → `rsa-attacks-2.md`
- ECDSA/DSA nonce reuse → `ecc-attacks.md`
- Smart attack (anomalous curves) → `ecc-attacks.md`
- MT19937 state recovery / LCG parameter recovery → `prng.md`
- HNP (biased nonces) → `lattice-and-lwe.md`
- LWE CVP embedding → `lattice-and-lwe.md`
- Shamir secret sharing reused coefficients → `zkp-and-advanced.md`

## Related Directions

- The algorithm is placed in a custom VM/obfuscated binary and the difficulty is understanding the program → `ctf-reverse`
- Crypto verification is only one part of a Web challenge → `ctf-web`
- What must be solved is encrypted C2/network traffic → `ctf-malware`
- The challenge involves ML/model components (gradients, weights, adversarial examples) → `ctf-ai-ml` — triage AI/LLM-camouflaged crypto first via `ai-assisted-crypto.md` (when the "AI" part is only flavor, stay in `ctf-crypto`)
- It is only encoding/base conversion rather than cryptography → `ctf-misc`

## Maintenance

- It is linked to the `ctf-crypto` skill by a same-named directory; when files are added or removed upstream, the `## File Index` table in this file must be updated in sync.
- **Important**: `modern-ciphers/-2/-3`, `rsa-attacks/-2`, `prng/-attacks`, `exotic-crypto/-2` are all **continuation-style shards** (by inclusion time), not categorized by topic. When looking for a specific technique, use `grep` to scan the whole file family by symptom keywords; do not guess by number.
- After changing the `SKILL.md` frontmatter, confirm the YAML is valid: invalid frontmatter makes dsh **silently ignore the entire skill**.
