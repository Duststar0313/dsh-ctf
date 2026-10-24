# CTF Crypto - AI / LLM Camouflaged Cryptography Recognition

2025-2026 trend: challenges where an AI/ML/LLM component participates in — or merely dresses up — what looks like cryptography. This is a **recognition page**: it decides when to pivot to `ctf-ai-ml` and when to strip the AI wrapper and solve classic crypto underneath. Attack details live in the referenced files, not here.

## Table of Contents
- [Form 1: ML Model as the Cipher (weights are the "ciphertext")](#form-1-ml-model-as-the-cipher-weights-are-the-ciphertext)
- [Form 2: LLM-Assisted Encryption and Signing Protocols](#form-2-llm-assisted-encryption-and-signing-protocols)
- [Form 3: ML Side Channels (DPA and Timing, Crypto Side)](#form-3-ml-side-channels-dpa-and-timing-crypto-side)
- [Form 4: Clickbait AI Crypto (Classic Underneath)](#form-4-clickbait-ai-crypto-classic-underneath)
- [Pivot Decision](#pivot-decision)

---

## Form 1: ML Model as the Cipher (weights are the "ciphertext")

**Recognition:** a neural network is trained to "encrypt" — the flag is the model's input (or its key), the model / its weights are the "ciphertext", or you must invert the model to recover a message. Signs: weight/bias or checkpoint files, PyTorch/JAX/ONNX artifacts, phrases like "NN-based cipher" or "encryption by neural network".

**Action:** this is an AI/ML problem, not crypto → pivot to [../ctf-ai-ml/model-attacks.md](../ctf-ai-ml/model-attacks.md) (model inversion / input extraction, weights-as-secret, logits or gradient leakage).

## Form 2: LLM-Assisted Encryption and Signing Protocols

**Recognition:** a chatbot "helps" you encrypt, sign, or derive keys — the key lives in the LLM's prompt, or the model generates ciphertexts/signatures on demand against a real crypto backend.

**Action:** the vulnerability is almost always **prompt injection**, not the crypto — extract the key via a direct ask, or inject instructions through the "message to encrypt" field → [../ctf-ai-ml/llm-attacks.md](../ctf-ai-ml/llm-attacks.md) and [../ctf-web/ai-agentic-web.md](../ctf-web/ai-agentic-web.md). If the LLM output is then processed by real crypto code, run the standard crypto analysis on that layer too.

## Form 3: ML Side Channels (DPA and Timing, Crypto Side)

**Recognition:** power traces / timing measurements of a standard cipher's implementation (AES/DES/ECC key recovery), possibly with ML-assisted trace classification.

**Action:** the crypto math is standard leakage analysis; the ML part only classifies traces → solve as a hardware side-channel problem ([../ctf-forensics/signals-and-hardware.md](../ctf-forensics/signals-and-hardware.md#side-channel-power-analysis-ehax-2026)), involving `ctf-ai-ml` only when the attack itself is an ML technique (e.g. a neural-net trace classifier).

## Form 4: Clickbait AI Crypto (Classic Underneath)

**Recognition:** the title says "AI crypto" / "neural cipher" / "LLM encryption" but the payload is base64, XOR, AES, RSA, or a classic puzzle behind a GPT-generated wrapper story.

**Action:** do **not** pivot on the title — run the standard crypto flow first (fingerprint the algorithm, check encodings, look for the flag format); treat "AI" as flavor text.

## Pivot Decision

- Model weights / gradients / input inversion → `../ctf-ai-ml/model-attacks.md`
- Chatbot / agentic LLM holds or generates keys → `../ctf-ai-ml/llm-attacks.md` + `../ctf-web/ai-agentic-web.md`
- Power/timing traces of a standard cipher, ML only assists classification → `../ctf-forensics/signals-and-hardware.md`
- "AI" only in the title, classic payload → stay in `ctf-crypto` (standard flow)

This mirrors the `When to Pivot` section of `ctf-crypto/SKILL.md`: pivot only when the **real blocker** is the ML component; otherwise treat AI as presentation noise.