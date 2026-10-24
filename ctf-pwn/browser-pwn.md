# CTF Pwn - Browser Pwn / V8 Engine Exploitation

## Table of Contents
- [识别与适用范围](#识别与适用范围)
- [V8 对象模型](#v8-对象模型)
- [经典漏洞类别](#经典漏洞类别)
- [利用原语演化](#利用原语演化)
- [题目识别与工作流](#题目识别与工作流)
- [浏览器管线：从 renderer OOB 到读 flag](#浏览器管线从-renderer-oob-到读-flag)
- [相关交叉引用](#相关交叉引用)

---

## 识别与适用范围

Chromium/V8 引擎利用（2025-2026 高级 CTF 类别）。适用信号：

- 题目给一个 `d8`（V8 独立 shell）、`node`、或 patch 过的 Chromium/Node 构建，并附带 `exp.js`/`exp.py` 起点或一个 CVE 的 diff
- 目标是一个**解释器/JIT 引擎的运行时 bug**（类型混淆、OOB、check 消除），而不是传统二进制漏洞（栈/堆）——先走 `ctf-routing` 确认不是 `ctf-pwn` 的其他常规方向
- flag 通常在目标机文件系统或远程服务中，`d8` 题的标准结局是 shellcode / `execve`，Chromium 题则是 renderer 进程内 RCE

本节只有识别价值；具体技术见以下各节。所有 CVE 编号与引擎版本均以**赛题实际给出的构建与 patch 为准**——V8 迭代极快，diff 定位永远优先于背 CVE 号。

## V8 对象模型

**HeapObject 与 Map（布局基础）**

V8 中每个 JS 对象是一个 `HeapObject`：头部是 8 字节（压缩指针下 4 字节）的 **Map** 指针，Map 描述对象的内存布局（字段数、属性种类、elements kind、in-object properties 等）。对象图的引用在启用 pointer compression 后是 32 位压缩指针（4GB cage 内偏移），因此对象之间**可以互相改写**，这是所有 exploitation 的地基：

```js
// %DebugPrint 看对象内部布局（--allow-natives-syntax）
%DebugPrint(obj);
// 输出示例: map -> 0x1234... , properties -> , elements -> FixedDoubleArray
```

**Fast vs Dictionary properties**

- **Fast properties**：named properties 存在对象 in-object 槽或独立的 `PropertyArray`/`PropertyArray` backing store，读写走固定偏移，速度快
- **Dictionary mode**（NameDictionary）：属性过多或被大量删除后对象退化为哈希表；退化点（map transition）是 type confusion 的高发区——把 fast 对象当 dictionary 对象操作（或反过来）就能制造 OOB / 越权读写

**Elements Kind（元素种类）**

elements backing store 决定数组元素是 tagged 指针还是原始 double/SMI。主要 kinds（按可容纳性递增）：

```
PACKED_SMI_ELEMENTS → PACKED_DOUBLE_ELEMENTS → PACKED_ELEMENTS
HOLEY_SMI_ELEMENTS → HOLEY_DOUBLE_ELEMENTS → HOLEY_ELEMENTS → DICTIONARY_ELEMENTS
```

- 数组越界写/写 undefined 会把 kind 升级（PACKED→HOLEY，甚至→DICTIONARY），**升级时刻的元素迁移**是历史漏洞的温床（迁移循环用错长度/索引）
- double 数组槽位存 64 位原始位模式，tagged 数组槽位存对象指针——**两种 kinds 之间的"阵营混淆"就是 addrof/fakeobj 的直接来源**（见利用原语演化）

**Sandbox 隔离背景（2024+，Chrome 默认开启）**

- 指针压缩 cage（4GB 对齐空间）内，对象互引仍可被 OOB 原语任意改写
- **V8 sandbox** 在此基础上把所有"指向 cage 外"的原始指针（ArrayBuffer backing store 的 external pointer、代码指针 code pointer 等）替换成 sandbox 内的 32 位**表索引**（External Pointer Table / Code Pointer Table，表本体在 sandbox 外且只读）
- 后果：即使拿到 OOB 数组，也不能像老版本那样直接把"目标地址"写进 backing_store 字段拿到任意读写；但 **elements backing store 的索引越界（OOB 数组 / typed array OOB）仍然可控**，可读写 cage 内任意对象、或沿 backing store 相邻区域扫外部内存
- 一句话模型：**sandbox 挡"指针"，不挡"索引"**——攻击面从改指针变成改索引/表条目/制造类型混淆

## 经典漏洞类别

**1. array.shift / array index OOB**

- `Array.prototype.shift`/`splice`/`copyWithin` 等内置在迁移元素时用错索引或长度（历史如 CVE-2020-16040 等），导致越界读/写 backing store
- 直接数组索引 OOB：`obj[i]` 的索引检查被绕过（负索引、极大索引、species 构造的数组长度不一致），常见触发面是 `%ArraySpeciesCreate`、`Object.defineProperty` 之后 length 未同步

```js
// 示意：species 数组长度比期望小 → 循环写越界
const fake = [];
Array.prototype[Symbol.species] = function(){ fake.length = 0; return fake; }; // 控制返回数组大小
// 触发内建（如 Array.prototype.sort / concat）后 fake 被越界填
```

**2. 阵营混淆（elements kind confusion）**

- 数组 kind 与代码预期不一致：代码按 SMI 数组处理实际是 DOUBLE 数组（或反过来），指针位模式被当数值、数值被当指针
- 触发方式：`Object.defineProperty` 改 `length`、`Array.prototype.concat` 的 species 路径、元素迁移时的过渡 kind
- 收益：**一步拿到 addrof / fakeobj**（见利用原语演化），是 d8 题最常考的类型混淆形态

**3. JIT 误编译（TurboFan / Maglev）**

- **Check elimination / 类型推断错误**：优化器认为某值恒为 `double` 或 `tagged`，省略运行时检查，实际输入违反该假设 → 数值/指针混淆（历史上如 CVE-2024-0517，Maglev 的 type confusion，被在野利用）
- **Register allocation bug**：寄存器分配冲突导致值被覆盖，或 32/64 位截断
- **简化 lowering（SimplifiedLowering）的 truncation 错误**：浮点→整型转换的截断/符号处理错误造成 OOB 索引
- 调试：`--trace-turbo` / `--trace-maglev` / `--print-opt-code` 看优化后代码，对比 `%NeverOptimizeFunction` 的行为

```js
// 示意：逃逸分析/check elimination 被打破 → 0 长度数组仍被索引
function f(a) { /* 优化器认为 a.length === 0 恒真 */ return a[%DebugRandomInt()]; }
for (let i=0;i<1e5;i++) f(new Array(0));  // 喂类型反馈
f(oob_array);  // 实际传入非空/可 OOB 的数组
```

**4. JSON.parse OOB**

- JSON 解析器（含惰性 parse 路径）历史上多次出现 OOB 读/越界写（元素迁移与 length 计算不一致的变体）
- 现实题目多为"给 patch diff，自己构造 JSON 触发"：注意 parser 的 fast path（无 whitespace、紧凑数组）与 slow path 行为差异

**5. string / buffer 长度篡改**

- 用相邻对象的 OOB 写把 `String` 对象的 length 字段改大 → `str[idx]` 越界读（泄露相邻 heap）
- 把 `ArrayBuffer` 的 `byte_length` / `backing_store` 相关字段篡改 → typed array 越界读写；或把 `DataView` 偏移改到负数/超大
- 篡改后 `ArrayBuffer.prototype.slice` / `TextDecoder` 可把越界数据拷到正常对象里外带

## 利用原语演化

**阶段 1：OOB 数组 → addrof / fakeobj（无 sandbox 或 cage 内）**

双数组布局（double 数组与 tagged 数组相邻），用一个数组的 OOB 槽读另一个数组的槽：

```js
// 示意（需按实际布局调偏移）
function addrof(obj) {
  victim[0] = obj;      // tagged 数组槽位写入对象指针
  return oob[0];        // double 数组越界读出该槽的位模式（压缩指针）
}
function fakeobj(addr) { /* 反向：把数值当 tagged 指针放回槽位 */ }
```

**阶段 2：任意读写（fake ArrayBuffer / DataView）**

用 fakeobj 在 heap 里伪造一个 `ArrayBuffer`/`DataView`，把 `backing_store` 设为目标地址（**老版本/`--no-sandbox` 直接写原始指针**），再经 DataView 读写任意地址。必要时用 `%DebugPrint` 与读已知对象（如自身）校准对象布局偏移。

**阶段 3（经典结局，无 sandbox）：WASM instance 的 RWX 内存 → shellcode**

- 实例化一个 WASM module，`WasmInstanceObject` 内指向 `jump_table_start` / 代码区（历史上 RWX 或可改权限），把 shellcode 写进去，调用 WASM 导出函数触发
- 这条链依赖"能拿到并写入 raw 指针"，**在启用 sandbox 的构建中不可直接复用**

```js
// 示意
const wasm_code = new Uint8Array([0,97,115,109,/*...*/]);
const instance = new WebAssembly.Instance(new WebAssembly.Module(wasm_code));
// 用任意写把 shellcode 覆盖到 wasm 代码区，再 instance.exports.main();
```

**阶段 4（V8 sandbox 时代，2024+）：不再直接改指针**

- 没有可写的 external pointer：backing_store 只能"索引"不能"赋值"
- 常见替代攻击面（点到即止，该领域进展快，**以赛题为准**）：
  - **cage 内对象操作**：OOB 改 Map/长度制造类型混淆，把 OOB 扩大成跨 backing store 的原始读写（typed array 的 guard region 之外扫外部内存）
  - **External/Code Pointer Table 相关**：表索引越界读写、或利用 backing store OOB 泄漏 sandbox 外指针再做二次利用
  - **Sparkplug（基线编译器）与 pointer-compression scheme 边界**：简单编译器的检查遗漏、压缩指针符号扩展边界 bug，是 2025-2026 的高频考点
- 实战建议：先确认目标构建是否开 sandbox（`d8 --version`、patch diff 是否含 `sandbox/` 目录、`%DebugPrint` 输出是否显示 32 位指针），**未开 sandbox 的题目直接用阶段 1-3 老链**

## 题目识别与工作流

**patch diff 定位（Chromium 补丁对比）**

- 题目给 `chromium` 源码 + 一个 commit 或 diff：先看改动文件在哪个子系统
  - `src/builtins/*.tq`（Torque 内建）→ 数组/字符串内建 OOB
  - `src/compiler/*`（TurboFan/Maglev lowering、simplified lowering）→ JIT 误编译
  - `src/objects/*`、`src/heap/*` → 对象布局/GC/迁移
  - `src/json/*`、`src/parsing/*` → JSON.parse 类
- 技巧：`git log`/`git show <commit>` 看修复提交，反推触发路径；diff 里**删掉的检查**就是漏洞条件

**d8 环境搭建**

```bash
# V8 自带 d8 构建或从官方源码 build；CTF 常直接给编译好的 d8
./d8 --allow-natives-syntax --shell exp.js
# 常用 flag
./d8 --allow-natives-syntax --trace-turbo --trace-maglev --print-opt-code --shell exp.js
./d8 --allow-natives-syntax --jit-fuzzing --shell exp.js   # 需要时禁用 JIT
```

**%DebugPrint 与常用 helper**

- `%DebugPrint(obj)` 打印对象 Map/elements/length/指针；`%SystemBreak()` 中断进 gdb；`%NeverOptimizeFunction(f)`、`%OptimizeFunctionOnNextCall(f)`
- 标准 helper 集：`addrof / fakeobj / arb_read8 / arb_write8 / bigint_to_bits / bits_to_bigint`（BigInt 与指针位模式互转，读写地址以 BigInt 传参最省事）
- 布局调校：`gc()` 稳定堆布局；`%ArraySpeciesCreate`、`Array.of` 等做堆喷；先在同一块连续分配里放 victim 与 oob

**node.js 作为攻击面**

- `node` 内部也是 V8，且默认暴露 `Buffer`/typed array：`Buffer` 的池分配与 `arrayBuffer` 语义可当现成的"外部内存"原语
- node 特有 host 对象（`process.binding`、`fs`、`child_process`）让 renderer 内 RCE 之后直接读 flag，无需 shellcode 的完整链
- 注意 node 与 d8 的 builtin 版本差异，`%DebugPrint` 需 `node --allow-natives-syntax`（部分版本可用）

## 浏览器管线：从 renderer OOB 到读 flag

**完整链（浏览器题，很少见）**

1. renderer 内 V8 OOB/类型混淆 → cage 内任意读写（或 backing store OOB）
2. renderer 进程被 OS sandbox 隔离：shellcode 只能进程内执行，无法直接读 `file://` 外文件/触碰 browser 进程
3. **sandbox escape**：滥用 Blink/Mojo 接口——通过被控的 renderer 拿 `Mojo` JS API、请求 browser 进程的 privileged interface（如 `FileSystemManager`、`DownloadManager`），或利用 `file://` 路径、`--no-sandbox` 以外的进程模型缺陷
4. 经典历史链（Chrome 0day 组合）本质都是"V8 bug 拿 renderer 任意读写 → Mojo 接口滥用跨进程"；CTF 中这种完整双段链极其罕见，通常只考前半段

**CTF 的简化点（95% 的题）**

- 题目给 **d8**（无浏览器进程、无 OS sandbox）：OOB → 任意读写 → WASM RWX/shellcode → `execve("/readflag")` 或直接读文件，完
- 题目给 chromium 时多带 `--no-sandbox` 或 flag 在 renderer 可读路径（如 `file:///flag` 或挂载卷），renderer RCE 即等于拿到 flag
- 结论：**先确认交付形态（d8 vs chromium vs node）再决定要不要碰浏览器进程链**；看到 `chrome://` / Mojo 相关题再进跨进程部分，否则按 d8 套路打

---

## 相关交叉引用

- 引擎 bug 已定位但需要"从 bug 到 shell"的通用二进制原语 → `ctf-pwn/advanced-exploits.md`（含早期 type confusion 案例）、`ctf-pwn/sandbox-escape.md`
- 自定义解释器/VM（非 V8）的逃逸 → `ctf-pwn/sandbox-escape.md`、`ctf-pwn/advanced-exploits-*.md`
- 纯 web 面（XSS 起手、service worker、DOM 混淆）→ `ctf-web`
- 只想读懂 JS/WASM 逻辑而非打引擎 → `ctf-reverse`
