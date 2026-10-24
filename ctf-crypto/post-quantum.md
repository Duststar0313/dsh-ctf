# CTF Crypto - Post-Quantum Recognition & Attacks (ML-KEM / ML-DSA / SPHINCS+)

> Split from `lattice-and-lwe.md` -- PQC tables live here when lattice file exceeds 950 lines.

## Table of Contents

- [Module-LWE / ML-KEM (Kyber) Recognition (G7)](#module-lwe--ml-kem-kyber-recognition-g7)
- [SPHINCS+ / SLH-DSA (Hash-Based Signatures) Recognition & Attacks](#sphincs--slh-dsa-hash-based-signatures-recognition--attacks)
- [ML-DSA (Dilithium) Attack Details](#ml-dsa-dilithium-attack-details)
- [Kannan / Arora-Ge / LWE Estimator Decision Tree (G10)](#kannan--arora-ge--lwe-estimator-decision-tree-g10)

## Module-LWE / ML-KEM (Kyber) Recognition (G7)

**Standardized:** ML-KEM (Kyber), ML-DSA (Dilithium) -- NIST PQC. CTF gives `q=3329`, `N=256`, rank `k=2/3/4`.

| Scheme | k | q | eta (secret) | du/dv (compression) | ring |
|--------|---|---|---------------|----------------------|------|
| ML-KEM-512 | 2 | 3329 | 3 | du=10, dv=4 | Z_q[x]/(x^256+1) |
| ML-KEM-768 | 3 | 3329 | 2 | du=10, dv=4 | Z_q[x]/(x^256+1) |
| ML-KEM-1024| 4 | 3329 | 2 | du=11, dv=5 | Z_q[x]/(x^256+1) |

**Flattening Ring-LWE to plain LWE:** `A in R_q^{k x k}` -> `A_flat in Z_q^{256k x 256k}` via negacyclic `rot` of each polynomial. Same for `b = A*s + e`. Then LWE is `b_flat = A_flat * s_flat + e_flat` with `s_flat,e_flat` small `eta` (centered binomial).

```python
# flatten Module-LWE to plain LWE for lattice attack (SandboxAQ style)
def flatten_mlkem(A_poly, s_poly=None, e_poly=None, q=3329):
    """A_poly: k x k list of polys length 256, s_poly: k polys.
    Returns A_flat (256k x 256k), s_flat (256k), e_flat (256k).
    Each poly -> 256x256 negacyclic matrix.
    """
    k = len(A_poly)
    N = 256
    dim = k * N
    A_flat = [[0] * dim for _ in range(dim)]
    for i in range(k):
        for j in range(k):
            poly = list(A_poly[i][j]) + [0] * (N - len(A_poly[i][j]))
            for r in range(N):
                for c in range(N):
                    if r >= c:
                        A_flat[i * N + r][j * N + c] = poly[r - c] % q
                    else:
                        A_flat[i * N + r][j * N + c] = (-poly[N + r - c]) % q
    s_flat = []
    if s_poly is not None:
        for s in s_poly:
            s_flat.extend(list(s) + [0] * (N - len(s)))
    e_flat = []
    if e_poly is not None:
        for e in e_poly:
            e_flat.extend(list(e) + [0] * (N - len(e)))
    return A_flat, s_flat, e_flat
```

**FO failure oracle:** ML-KEM uses Fujisaki-Okamoto transform -- decryption failure leaks `e` via `du/dv` compression (lossy). CTF may give failure oracle (yes/no) -> use via BDD.

**NTT misorder:** Kyber NTT is bit-reversed order; challenge may give `A_ntt` without `bitrev` -- reorder before `inv_ntt`.

---

## SPHINCS+ / SLH-DSA (Hash-Based Signatures) Recognition & Attacks

**Positioning (FIPS 205):** NIST PQC family 3: hash-based signatures (SLH-DSA, formerly SPHINCS+). CTF 中出现概率低于 lattice 系；一旦出现，几乎总是**一次性密钥/状态复用**题材：同一密钥签两次、随机化字节或索引被固定、ADRS/域分隔字节被硬编码、或参数被大幅调弱。标准参数且随机化正常的 SLH-DSA 没有捷径可走——先找弱点（随机化/状态/参数），不要对标准方案做密码分析。

**Parameter table (真实值，FIPS 205 Table 1-2；SHA2 与 SHAKE 变体长度相同，w=16 全系一致):**

| SLH-DSA set | n | h | d | 每层树高 h'=h/d | FORS: k(树数) x tau(树高) | pk | sk | sig (bytes) |
|---|---|---|---|---|---|---|---|---|
| SHA2-128s | 16 | 63 | 7 | 9 | 14 x 12 | 32 | 64 | 7856 |
| SHA2-128f | 16 | 66 | 22 | 3 | 33 x 6 | 32 | 64 | 17088 |
| SHA2-192s | 24 | 63 | 7 | 9 | 17 x 14 | 48 | 96 | 16224 |
| SHA2-192f | 24 | 66 | 22 | 3 | 33 x 8 | 48 | 96 | 35664 |
| SHA2-256s | 32 | 64 | 8 | 8 | 22 x 14 | 64 | 128 | 29792 |
| SHA2-256f | 32 | 68 | 17 | 4 | 35 x 9 | 64 | 128 | 49856 |

完整参数（消息摘要长度 m、Winternitz len、随机化字节数；例如 256f 行 m=49）以 FIPS 205 表格为准核对。

**签名结构（识别特征）：** σ = (R, idx, FORS 签名, d 层 WOTS 签名 + 认证路径, 顶层认证路径)。FORS 部分 = k x tau 个 **n 字节叶子秘密值** + 各树 Merkle 认证路径——整个 blob 就是几十上百个 n 字节哈希堆出的小 Merkle 树森林（对比 ML-DSA：无树结构）。典型判别：**pk 极小（32/48/64 B）而签名极大（7.8–49.9 KB）**，与 Dilithium 正相反（Dilithium pk 1312–2592 B、签名 2420–4627 B）。密文/签名数据与源码里 `FORS_HEIGHT`/`SPHINCS_HEIGHT`/`SPHINCS_D` 等宏直接对照上表。

**攻击面（CTF 主线 = 状态/一次性密钥）：**

1. **一次性密钥重用（one-time key / state reuse）——重中之重。** SLH-DSA 名义上**无状态**：每次签名先随机出 R（依赖 opt_rand），再由消息摘要派生树索引 idx 与 FORS 索引，选中的 FORS/WOTS 密钥是一次性的。只要随机化失效（opt_rand 固定、弱 RNG、把"版本/年份"类字节硬编码进 PRF_msg 输入或 ADRS、或退化成计数器当 idx），不同签名就**撞上同一组 FORS/WOTS 一次性密钥**：
   - **WOTS 重用：** 两条签名暴露同一条 hash 链的两个位置；链只能前向（hash 迭代不可逆），拿到较低位置的值即可前向推到更高位 → 伪造该链位（配合 checksum 通常足够伪造任意消息）——经典 "WOTS 一次性密钥重用 → 伪造"。
   - **FORS 重用：** 两条签名命中同一 k 棵 FORS 树 → 已暴露叶子秘密集合随签名数增长；一旦目标消息的 k 个索引全部落在已暴露集合内即伪造成功。这就是经典 SPHINCS one-time key reuse 攻击思路（botnet/海量样本场景：同 idx 碰撞的签名收得越多，覆盖率越高；索引可预测时针对性收集）。
2. **状态回溯（有状态变体/教学实现）：** 经典 SPHINCS（2015）/XMSS/LMS 是**有状态**的——计数器选叶子；计数器回退/重置/并发复用 → 同一一次性密钥再次使用 → 同上的恢复/伪造。不少 CTF 实现把 SPHINCS+ 的"随机选 idx"退化成计数器，效果等同。
3. **ADRS/域分隔字节硬编码（"版本/年份字节"一类）：** FIPS 205 每个 hash 调用都喂 22–32 B ADRS（tree/层/类型 0x00–0x05/节点索引）来域分离。若题目把 ADRS 或随机化输入写成常数，两个本应不同的调用塌缩为同一输入 → 认证路径可交叉复用、索引可预测 → 一次性密钥碰撞。在源码里找 ADRS 构造与 R 生成（PRF_msg / opt_rand）。
4. **参数弱化：** 自实现把 h/d/tau/k 调得远小于 FIPS 205 表 → 叶子总数太少 → birthday 碰撞变便宜。

**检测命令：**

```bash
strings challenge_file | grep -iE 'sphincs|slh[-_]dsa|fors|wots'
# 或用实现宏核对：grep SPHINCS_HEIGHT / SPHINCS_D / SPHINCS_FORS_TREES / SPHINCS_FORS_HEIGHT
# 尺寸本身（pk 32/48/64, sig 7856..49856）常能直接锁定参数集
```

**实现提示：** 抓到两条 (idx, R) 相同的签名 → 逐字节差分定位 FORS Reveal 段（k x tau 个值）与各 WOTS 链段 → 链前向扩展 / 合并已暴露叶子集合 → 伪造目标消息。同属 PQC 签名攻击簇的 MAYO fault / FROST threshold 见 `zkp-and-advanced.md`（那里是 fault/threshold 路线，这里是随机化/一次性密钥路线）。

**诚实标注（勿夸大出现概率）：** 哈希签名题在 CTF 中少见，且几乎全部是随机化/状态误用题材；标准 SLH-DSA 的密码分析不属于 CTF 求解路径。

---

## ML-DSA (Dilithium) Attack Details

**Positioning (FIPS 204)：** ML-DSA (Dilithium) 格签名。识别特征：q = 8380417 = 2^23 − 2^13 + 1、环 R_q = Z_q[x]/(x^256+1)、k/l 很小、签名 = (c, z, h)。

**Parameter table (真实值，FIPS 204 Table 1-2；尺寸单位为字节):**

| Param | ML-DSA-44 (Dilithium2) | ML-DSA-65 (Dilithium3) | ML-DSA-87 (Dilithium5) |
|---|---|---|---|
| q | 8380417 | 8380417 | 8380417 |
| k, l | 4, 4 | 6, 5 | 8, 7 |
| eta (secret s1/s2 系数界) | 2 | 4 | 2 |
| tau (c 中 ±1 系数个数) | 39 | 49 | 60 |
| gamma1 (mask y 界) | 131072 = 2^17 | 524288 = 2^19 | 524288 = 2^19 |
| gamma2 (低比特 w0 界) | 95232 = (q−1)/88 | 261888 = (q−1)/32 | 261888 = (q−1)/32 |
| beta = tau·eta | 78 | 196 | 120 |
| omega (hint 非零系数上限) | 80 | 55 | 75 |
| d (t 高/低位切分) | 13 | 13 | 13 |
| pk / sk / sig sizes | 1312 / 2560 / 2420 | 1952 / 4032 / 3309 | 2592 / 4896 / 4627 |

**签名方程（一切攻击的起点）：** σ = (c, z, h)；挑战 c = H(μ ‖ w1) 由 256-bit 哈希经 SampleInBall 变成**恰好 tau 个 ±1、其余全 0** 的多项式（c-tau）；z = y + c·s1 (mod q)，y ← ExpandMask(ρ′, κ) 在 ±gamma1 内近似均匀；h 为 hint 向量（非零位 ≤ omega）。签名端拒绝采样：仅当 ‖z‖∞ < gamma1 − beta **且** ‖w0‖∞ < gamma2 − beta 才输出。验证端：w′ = A·z − c·t1·2^d，重算 c′ = H(μ ‖ w1′)，核对 c′=c、‖z‖∞ 界与 hint 计数。

**攻击面：**

1. **nonce（ρ′）偏置/泄漏 → HNP / MLWE。** 签名随机性全部由 SHAKE 从 ρ′（及 ρ″）展开。泄漏 ρ′（ExpandMask 侧信道）、弱 RNG、nonce 复用 → y 已知或有偏：
   - y 已知：z − y = c·s1 (mod q) 是 s1（l·256 个未知系数）的线性方程组，直接求解；
   - y 未知但有界（‖y‖∞ ≤ gamma1）：每条签名写成 c_i·s1 ≡ z_i − y_i (mod q)，小误差 y_i → HNP 形状。组装 A′ = [c_1; …; c_m]（m×k 环矩阵）、b = [z_1; …; z_m] → 环上 MLWE 实例（错误界 gamma1）→ 用 `lattice-and-lwe.md` HNP 节（line 144）/embedding/BKZ；或按本文第一节把环 flatten 到 Z_q。签名越多、误差界越紧，格越容易。
2. **消息泛洪（与签名 malleability 相关）。** 同一消息的签名**高度 malleable**：拒绝采样每次重抽 y，同一消息存在海量合法 (c,z,h)。对签名 oracle 泛洪（Debris-Alazard–Ducas–van Woerden 路线）让 w1 的统计泄露 s1：数十到数百条签名即可恢复密钥（论文级结论；CTF 版通常只需"能无限次签名"）。极端情形下（相同消息 + 可控/重复挑战 c）噪声集中，方程可直接线性化求解，不需要大格。与 ECDSA nonce 复用同族：nonce 整体泄漏的场景走 HNP，泛洪走统计侧。
3. **验证器 bug（漏范数检查 → 通用伪造）。** 验证端若跳过 ‖z‖∞ < gamma1 − beta（及 hint 计数检查），存在**通用伪造**：任选消息与掩码 y′ → w1 = HighBits(A·y′, 2·gamma2) → c = H(μ ‖ w1) → 解 A·z ≡ c·t1·2^d + A·y′ (mod q) 得 z = A⁻¹·(c·t1·2^d) + y′（A 公开、环上通常可逆，奇点就换 y′ 重试），h = 0（UseHint(0, w′) = HighBits(w′, 2·gamma2) 精确成立）。验证端重算出同一个 c 即接受——典型"只比 c == H(...)、丢掉了各项界检查"的题。
4. **错误样本 / fault 降级。** 对签名端注入 fault（跳过拒绝采样、固定 ρ′、翻转 c/y 的位）→ 每次 fault 得到更有利的方程（y 已知化/界收紧）。同一套 fault 剧本见 `zkp-and-advanced.md` MAYO（那边是 GF(16) 线性化；这里是 mod q=8380417 的线性方程）。

**实现提示：**

```python
# 已解析 m 条签名：c_i（tau 个 ±1 的挑战多项式）, z_i（l 个 poly）, hint h_i
# 每条签名一个方程 (mod q)：c_i * s1 == z_i - y_i,  ||y_i||_inf <= gamma1
# 组装：A' = [c_1; c_2; ...]（m x k 环矩阵）, b = [z_1; ...; z_m]
#     -> MLWE 实例 A' * s1 = b - y：走 lattice-and-lwe.md 的 HNP/embedding(+BKZ)，
#        或按本文 ML-KEM 节的 negacyclic-flatten 落到 Z_q
# 先做三件事再上格：
#   1) 能对同一消息无限签名吗？→ 泛洪路线，噪声集中后直接线性化
#   2) ρ' 是否固定/复用？→ y 碰撞，两条签名相减得到关于 s1 的线性方程
#   3) c 是否极稀疏/非 SampleInBall？→ 方程更稀疏，HNP 更易解
```

**交叉引用（PQC 签名攻击簇）：** `zkp-and-advanced.md` —— MAYO fault injection、FROST threshold 与本文同属"把签名随机性/实现弱点转成线性方程"一族的另外两个实例；fault 窗口、区间求交、线性求解等模板可以直接迁移。通用 HNP 机制：`lattice-and-lwe.md` §HNP（line 144）。同文件第一节给出环→Z_q 的 flatten（ML-DSA 组装大格时同款手法）。

**诚实标注（勿夸大出现概率）：** 标准参数、随机化正常的 ML-DSA 密码分析对 CTF 维数过大（s1 有 l·256 系数），不可能裸拼格；题目必然带弱化——nonce 被写死/泄漏、签名 oracle 可泛洪、验证器丢界检查、或 fault 注入。先侦察再选攻击线。

---

## Kannan / Arora-Ge / LWE Estimator Decision Tree (G10)

**When to use what:**

- **Kannan embedding** (`lambda=1` vs Bai-Galbraith `BDGL16`): Kannan `[[B 0],[t 1]]` is generic CVP -> BDD. Bai-Galbraith tweaks `lambda` to balance `||e||` vs `||s||` when `q` moderate and `secret` small. Use `lambda = q / (2*bound)` heuristic; sweep `1, q/4, q/2`.

- **Arora-Ge:** linearization when error `B < q/4` small and many samples. Build polynomial system `f_i(s) = ( <a_i,s> - b_i )*(...)` over `Z_q`, solve via Gröbner / linearization. Works for `m >> n^d` (e.g. `n=64, B<8`). If `B >= q/4` prefer lattice.

- **Hybrid MITM for sparse secrets:** secret `s` sparse `h=20` in `n=512` -> split `s = s1 + s2`, meet-in-the-middle via `BKZ` on projected lattice.

- **LWE estimator:** use `https://github.com/malb/lattice-estimator` (Albrecht et al.) to choose strategy:

```python
# estimator decision sketch (run offline: python -m estimator ...)
# Input: n=512, q=3329, Xs=CBeta(eta=2), Xe=CBeta(eta=2), m=256k
# Output: cost of BKZ 40 vs Arora-Ge vs hybrid
# In CTF, estimate with: from estimator import LWE
# LWE.estimate(n, q, Xs, Xe, m)
```

**Decision tree:**

```
LWE instance (n,q,m,Xs,Xe)
 ├─ B < q/4 and m > 2n  --> Arora-Ge (linearize, Gröbner)
 ├─ secret sparse (h < 0.1n) --> hybrid MITM + BKZ
 ├─ dim < 80  --> Kannan embedding + LLL then CVP.closest_vector
 ├─ dim 80-150 --> Bai-Galbraith embedding + BKZ 20-30 + GSO.Mat.babai
 └─ dim >150  --> estimator + BKZ 40+ or flatter (dim>100)
```

**Estimator guidance:** `lambda=1` generic; `Bai-Galbraith` when `q` small (`3329`) and `eta` tiny (`2,3`); `estimator` chooses `block_size` vs `hybrid`.

**Cross-link:** For Coppersmith small roots see `advanced-math.md` `hg_matrix(f_coeffs,N,X,beta,m,t) -> IntegerMatrix -> LLL -> sympy Poly` (beta=0.5, monic check, flatter optional).



---

*Back-link: see `lattice-and-lwe.md` NTRU (G1), GGH (G2), Mersenne AJPS (G3) for lattice construction; Coppersmith `hg_matrix` lives in `advanced-math.md`. ML-DSA nonce-bias HNP construction: `lattice-and-lwe.md` §HNP (line 144). PQC signature attack cluster (MAYO fault / FROST threshold): `zkp-and-advanced.md`.*

