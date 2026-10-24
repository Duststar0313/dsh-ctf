# CTF Pwn - WebAssembly Runtime Exploitation

## Table of Contents
- [识别与适用范围](#识别与适用范围)
- [WASM 内存模型与安全边界](#wasm-内存模型与安全边界)
- [经典漏洞类别](#经典漏洞类别)
- [利用：从越界到断沙箱](#利用从越界到断沙箱)
- [题目识别工作流](#题目识别工作流)
- [与 misc / reverse 的边界（交叉引用）](#与-misc--reverse-的边界交叉引用)

---

## 识别与适用范围

WASM 运行时漏洞利用——目标不是"解 WASM 里的算法"，而是**WASM 运行时/宿主进程本身有漏洞**，wasm 只是攻击载荷。适用信号：

- 题目给 `.wasm` + 宿主程序（Rust/C），宿主里能看出 runtime（`wasmtime`、`wasmer`、`wasm3`、`wamr`、`wasmi`、V8/Wasmtime embedding 等）与版本线索
- 题目描述带"CVE-xxxx"、`runtime version`、或者攻击面是 `call_indirect` / `memory.grow` / host import 参数
- 本地验证：wasm 输入能触发宿主崩溃/越界/类型混淆（`wasm-validate` 通过但运行时行为异常）

对比：如果题目只需要读懂 wasm 逻辑（flag 校验、算法、序列化格式）→ 走 `ctf-reverse`；如果只是 WASM 游戏改状态作弊 → 走 `ctf-misc`（见文末交叉引用）。所有 CVE 编号与 runtime 版本**以赛题实际给出的版本为准**——运行时迭代快，先确认版本再搜对应补丁。

## WASM 内存模型与安全边界

**Linear memory**

- 32 位地址空间（wasm32），页大小 64 KiB；`(i32.load/store)` 是唯一直接内存访问方式
- 越界访问按规范必须 **trap**——漏洞本质是让实现漏掉/绕过这个检查
- 实现有两条路线：**显式 bounds check**（wasmtime 默认，带 guard page 优化）与 **guard region + 隐含检查**（V8 的 WASM：大块 guard 内存，靠分段地址空间避免逐次检查）

```wat
;; 一个典型的越界读（合法 wasm，行为取决于 runtime 是否漏检）
(func (export "oob") (param i32) (result i32)
  local.get 0
  i32.load offset=0)   ;; 对 0xFFFFFFFC 等边界值做访问
```

**memory.grow**

- 返回**旧大小**（页数），失败返回 `-1`（即 `0xFFFFFFFF`）。不检查返回值直接做 offset 计算 → 下溢/溢出
- 记忆点：`grow` 成功时旧页数即新数据区的起点，失败返回 -1 必须显式处理

**Table 与 function references**

- `table`（funcref 数组）与 linear memory **分离**；`call_indirect (i32)` 用索引查表调用，并做**签名（类型）检查**
- 攻击目标：绕过类型检查（表条目被篡改成签名不同但地址可控的条目）、或把 table 存储 OOB 触及（取决于实现里 table 与线性内存是否在同一堆块）
- 新版本 type function references（`ref.func`、`table.set`）与 GC 提案改变了类型检查路径——**以目标 runtime 版本为准**

**bounds check 失败的两种形态**

1. **数值侧绕过**：`i32.add` 溢出（`0xFFFFFFFF + 1 = 0`）、负索引符号扩展错误、`u32` 截断——检查用的是溢出后的值
2. **实现侧绕过**：guard page 覆盖不足、迁移/拷贝路径（`memory.copy`/segment init）的 src/dst 长度计算错误——检查了首字节但没检查尾字节

## 经典漏洞类别

**1. 整数溢出 / 越界索引**

- `memory.grow` 返回值未检查 → 用 `-1` 算 offset（`(grow_result + 1)` 溢出成 0 之类）绕过后台检查
- `memory.copy`、`data.drop`/segment 初始化、`memcpy` 包装的 **src/dst/len 计算**溢出：`src+len`、`dst+len` 溢出后 `copy` 越界
- loop 计数类型错误（i32 负数当 usize、u64→u32 截断）

```c
// 宿主 C 侧典型坏代码（wasm 提供全部参数）
void host_memcpy(char* dst, char* src, size_t len) {
  memcpy(dst, src, len);  // dst/src 来自 wasm 计算的 i32，len 来自不可信 wasm 代码
}
```

**2. type confusion（表数组元素类型篡改）**

- 如果 runtime 把 table/globals/exports 元数据与线性内存分配在**同一块可 OOB 触及的堆区**（解释器实现常见），越界写可篡改 table 条目的地址/签名
- `call_indirect` 时用篡改后的条目 → 跳转到任意地址（宿主内），签名检查被绕过

```wat
;; 示意：先 OOB 改 table[0] 的目标地址，再：
(func (export "trigger") (result i32)
  i32.const 0
  call_indirect (type 0))  ;; 跳到被篡改的条目
```

**3. runtime 层 bug（以目标版本为准）**

- **wasmtime**（Rust）：历史上多次 bounds check / 类型检查 / 内存元数据漏洞；经典利用面是 `memory.grow` 与 table 操作的检查遗漏。注意 wasmtime 有详细的安全公告（SECURITY.md / GitHub advisories），**先对版本号搜 advisories**
- **wasm3**（C 解释器）：整数溢出、循环/栈处理 OOB 的公开报告很多（历史 CVE 密集），解释器把 wasm 栈/操作数放在宿主堆结构上，越界可打相邻元数据
- **WAMR / wasmi / wasmer**：解释器与 AOT 编译路径均有漏洞史；AOT 侧还有代码生成错误（JIT 类）
- 通用思路：先确认运行时如何**存储 wasm 状态**（操作数栈、locals、table、globals、export 描述符）在宿主进程内的布局，再判断 OOB 能打什么

**4. WASI sandbox escape（能力模型滥用）**

- WASI 是 **capability 模型**：进程只见显式 preopen 的 fd（如 `--dir .`），默认无文件系统/网络/进程能力
- escape 路径：
  - `path_open` 的路径处理 bug：`..` 逃逸、符号链接指向 preopen 外、`proc_self`/`/proc` 滥用（若 runtime 未过滤）
  - 宿主额外开放的 import（调试 syscall、`fd_readdir` 边界外）
  - 更本质的路线：先内存破坏（类别 1-3）拿到宿主进程内任意读写，再打宿主 libc（不再受 WASI 限制）

## 利用：从越界到断沙箱

**路线 A：越界读写 → 控制函数表 / 导出函数指针**

1. 构造触发越界的 wasm 输入（上文漏洞类别 1-2）
2. 用 OOB 泄露/定位 runtime 的 table、export 描述符或宿主可写数据（观察 `wasm-objdump -x` 的导出布局 + 宿主内存 dump 校准偏移）
3. 把导出函数指针/table 条目改写为可控目标（ROP gadget、shellcode 地址、或 host 已有函数）
4. `call_indirect` / 调用该导出 → 执行流跳转；配合宿主 NX/RELRO 决定 ROP 或 shellcode

**路线 B：host import（env 函数）参数注入**

- 题目 `imports` 常给 `malloc`/`memcpy`/`read` 等 host 函数；wasm 侧传参失控（长度、dst 偏移、fd）→ 宿主堆溢出 / 任意偏移读写
- 利用：用 host 函数本身做原语——例如 `memcpy(dst_越界, src, len)` 制造宿主堆越界写，再按堆技巧（house of X、`__free_hook` 等）推进；或 `read` 到越界地址做泄露

```js
// 浏览器/Node 侧加载示意（CTF 常给此类 loader）
const { instance } = await WebAssembly.instantiateStreaming(fetch('p.wasm'), {
  env: { malloc: (n) => host_malloc(n), memcpy: (d, s, n) => host_memcpy(d, s, n) }
});
```

**路线 C：WASI 沙箱逃逸（无内存破坏前提）**

- 先枚举 preopen 与可用 syscall：`ls -la /dev/fd`、`fd_readdir`、测试 `path_open` 对 `..` 与符号链接的行为
- 找宿主未过滤的能力（进程、网络、文件系统扩展）；无则回到路线 A/B 用内存破坏断沙箱

## 题目识别工作流

**判定信号**

- 交付物含 `.wasm` + `main.rs`/`main.c`（或 loader JS）：看宿主怎么加载——`wasmtime::Engine`/`Store`、`wasmer`、`wasm3`/`m3_`、`wamr`、还是 V8/QuickJS 内嵌
- 版本线索：`Cargo.lock`/`Cargo.toml`、`wasmtime --version`、`README`、dockerfile、或编译信息字符串；**先对版本搜已知漏洞公告**（wasmtime/wasmer 的 GitHub Security Advisories、NVD）
- 运行形态：`wasm-validate p.wasm` 通过、但特定输入使宿主 panic/segfault/越界 → pwn 方向；若只是输出错 flag 且宿主不崩 → 多半是 reverse 解算法

**工作流**

```bash
# 1. 摸清交付物
file p.wasm  &&  wasm-objdump -x p.wasm        # exports/imports/table/memory 布局
# 2. 版本与加载方式
strings host  | grep -i wasmtime   # 或看 Cargo.lock / 源码
# 3. 起本地复现：写 wasm 触发候选 bug（grow 返回、copy 边界、call_indirect 越界）
# 4. 崩溃后用 gdb/asan 看越界写入落在宿主哪里 → 决定路线 A/B/C
```

**常见陷阱**

- 别把"wasm 里算法有 bug"当 pwn：先确认宿主/runtime 是否有可打的检查漏洞，再花时间做 wasm 载荷
- 注意 wasm32 的 `i32` 在宿主 C/Rust 侧常被转成 `usize`：`(u32 as usize)` 语义差异本身就是 bug 源

## 与 misc / reverse 的边界（交叉引用）

- **不是本题**（game cheat / 状态篡改）：`ctf-misc/games-and-vms.md`（WASM patching：`wasm2wat` 改逻辑再 `wat2wasm`）、`ctf-misc/games-and-vms-2.md`（WASM linear memory manipulation：加载后改运行时状态变量作弊）——这些是"利用 wasm 做游戏作弊"，**不涉及 runtime 漏洞**；若题目只是游戏逻辑/状态 → `ctf-misc`
- **不是本题**（解算法）：`ctf-reverse/tools.md` 的 WASM Analysis 节（`wasm2c` 反编译 + `wasm_rt_trap` 处理）——wasm 是**被分析的代码**（读懂逻辑找 flag），不是攻击载荷；这类题 → `ctf-reverse`
- 本题（wasm-pwn）分界一句话：**wasm 是攻击输入，漏洞在 runtime/宿主**；misc/reverse 的 wasm 题，wasm 是被作弊或被分析的对象
- 拿到内存破坏后继续 → `ctf-pwn/heap-techniques*.md`、`ctf-pwn/rop-and-shellcode.md`（宿主内推进）
- WASM 在浏览器引擎内（V8 的 WASM 编译、`jump_table` 攻击面）→ `ctf-pwn/browser-pwn.md`（WASM 是 V8 利用链的一环）
