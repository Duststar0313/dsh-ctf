# CTF Pwn - glibc 2.40-2.43 Heap & FSOP：现状核查、勘误与后继路径

> 适用环境：2025-2026 现代 CTF 宿主（Ubuntu 24.10/25.04 → glibc 2.40/2.41；Debian 13 trixie → 2.41；Debian sid → 2.42/2.43；Fedora 42+ → 2.42）。回答一个高频问题：「House of Apple / 各种 FSOP 在新版 glibc 还灵不灵？」。结论先行：**glibc 2.41 没有移除 `_IO_wfile_jumps`，House of Apple 2 在 2.41/2.42/2.43（实测至 2.44-experimental）仍然可用**；真正的新变化是 2.42 的 tcache 大块缓存与 2.43 起对整批内建 stdio 符号的弃用预告。

## Table of Contents

- [TL;DR Version Timeline and Corrections](#tldr-version-timeline-and-corrections)
- [glibc 2.40 (2024-08)](#glibc-240-2024-08)
- [glibc 2.41 (2025-02): _IO_wfile_jumps NOT Removed](#glibc-241-2025-02-io_wfile_jumps-not-removed)
- [glibc 2.42 (2025-08): tcache_max](#glibc-242-2025-08-tcache_max)
- [glibc 2.43 (2026-02): Internal stdio Deprecated](#glibc-243-2026-02-internal-stdio-deprecated)
- [FSOP Symbol Status 2.41-2.44 measured](#fsop-symbol-status-241-244-measured)
- [FSOP Paths Alive vs Dead on 2.41+](#fsop-paths-alive-vs-dead-on-241)
- [Modern tcache / fastbin Hardening](#modern-tcache--fastbin-hardening)
- [Version Identification](#version-identification)
- [Decision Workflow](#decision-workflow)
- [Evidence and Sources](#evidence-and-sources)

---

## TL;DR Version Timeline and Corrections

| glibc | 发布 | 堆 / FSOP 相关真实变化 | 对 CTF 的影响 |
|---|---|---|---|
| 2.40 | 2024-08 | 无 malloc/libio 结构变更，bugfix 为主 | 按 2.39 打法（tcache key 形态不变） |
| 2.41 | 2025-02 | **未移除 `_IO_wfile_jumps`**；修复 wchar IO 越界写（bug 20632）；`dlopen` 不再隐式启用可执行栈 | House of Apple 2 仍可用；注意 dlopen/栈可执行行为收紧 |
| 2.42 | 2025-08 | tcache 支持大块缓存（tunable `glibc.malloc.tcache_max`，上限 4 MB） | 默认环境行为同 2.41；远端若开大 tcache_max 则大块可进 tcache |
| 2.43 | 2026-02 | **弃用整批内建 stdio 符号**（`_IO_file_jumps`/`_IO_wfile_jumps`/`_IO_list_all`/`_IO_str_overflow` 等，"may stop working with a future version"，且**不提供 compat 符号**）；`malloc_set_state()` 恒失败 | 符号仍在（实测可 `nm -D` 到），链仍可用；但未来版本随时移除 |
| 2.44 | 2026 (Debian experimental) | 实测符号仍在，弃用未落地 | 继续按符号实测为准 |

> ⚠️ **勘误**：网上/部分 writeup 流传「glibc 2.41（Ubuntu 25.04/Debian 13）已移除 `_IO_wfile_jumps`，House of Apple 2 失效」。**这与官方变更记录不符**：glibc 2.41 官方 NEWS 无任何相关移除条目；Debian trixie 的 2.41-12+deb13u4 实测 `_IO_wfile_jumps@@GLIBC_2.2.5` 仍在导出（见下节实测命令）。流言的来源大概率是把 glibc 2.43 的弃用预告（"may stop working with a future version"）或 2026 年 "libio: validate and mangle the wide vtable" 加固讨论误传成了"已移除"。**实操准则：永远以目标 libc 的 `nm -D` 实测为准，不要按版本号一刀切。**

## glibc 2.40 (2024-08)

**真实变化（官方 NEWS）**：无 malloc/tcache/libio 结构性变更。主要条目：`<stdbit.h>` 内置宏、`_ISOC23_SOURCE`、C23 数学函数、`glibc.rtld.enable_secure` 测试 tunable、fortify/clang 增强、utmp/utmpx 2038 字段改无符号。属于「bugfix 版」。

**与堆利用相关的修复**（体现 2.40 为维护版）：
- `fclose` 对大量 FILE* 的线性搜索耗时问题（bug 27777）
- `fdopen` seek 失败时的内存泄漏（bug 31840）
- `__gcov_exit` 中 `_IO_link_in` 崩溃（bug 31963）

**要点**：`tcache key`（2.39 引入）在 2.40 保持原样：释放进 tcache 时在 chunk 用户区首 8 字节写入进程随机的 `tcache_key`；`tcache_get` 前若该字段等于 key 则遍历桶检测 double-free → abort。绕过仍靠 UAF 覆写 key 字段 / tcache stashing 覆写 / 取走后再造链。

**快速验证 tcache key（在 2.40/2.41 目标上）**：

```bash
# gdb 挂上目标：free(p) 后查看
#   x/4gx p            -> [0] = PROTECT_PTR(next)^(p>>12), [1] = tcache_key(每进程随机)
# 两次运行对比 [1] 不同 == key 机制生效；把 [1] 覆盖成任意值即可绕过 double-free 检测
```

**版本子号**：存在 2.40.1 补丁版（NEWS 顶部独立条目），为 bugfix 累积，无堆语义变化；遇到 `2.40.x` 按 2.40 处理。

**检测命令**（区分 2.40 与旧版）：见 [Version Identification](#version-identification)；关键差异只是版本号，符号面 2.40 ≈ 2.39。

## glibc 2.41 (2025-02): _IO_wfile_jumps NOT Removed

**勘误核心**：2.41 官方 NEWS（"Deprecated and removed features" 一节）**没有任何 `_IO_wfile_jumps` 条目**。与 libio 相关的只有一条 bugfix：`[20632] stdio: Buffer overflow in wchar IO (_IO_wfile_overflow)`——这是**修 bug，不是删符号**，且不影响 wide-char FSOP 链的可达性。

**实测（Debian trixie，libc6 2.41-12+deb13u4）**：

```bash
LC_ALL=C nm -D libc.so.6 | grep -E 'wfile_jumps|wfile_overflow'
# 00000000001d18c0 D _IO_wfile_jumps@@GLIBC_2.2.5        <- 仍在，Apple 2 可用
# 0000000000084360 T _IO_wfile_overflow@@GLIBC_2.2.5
```

**结论**：House of Apple 2（依赖 `_IO_wfile_jumps` vtable 的 wide-char 路径：伪造 FILE → `_wide_data` → `_wide_vtable` 的 `__doallocate` → `system`/`setcontext`）在 Ubuntu 25.04 / Debian 13 的 glibc 2.41 上**照常可用**。详见 [heap-techniques.md](heap-techniques.md) 的 House of Apple 2 节。

**2.41 真正影响 CTF 的变化**：
1. `dlopen`/`dlmopen` 不再为了需要可执行栈的 SO 而自动把进程栈置为可执行（缺 GNU_STACK 的库加载会直接失败）。影响 ret2dlresolve / 栈上 shellcode 类题目：确认目标 ELF 的 GNU_STACK 后再决定 shellcode 放置位置。
2. `abort(3)` 改为 async-signal-safe；从 SIGABRT handler 里 `longjmp` 会被强制终止（要用 `sigsetjmp`）。个别用 abort 触发 FILE flush 的 FSOP 链需复核 handler 语义。
3. 新增 `glibc.rtld.execstack` tunable（默认允许）。

**检测要点**：先 `ldd --version`/直跑 `libc.so.6` 定版本，再 `nm -D` 检查目标符号，符号在 → 对应链可用。

## glibc 2.42 (2025-08): tcache_max

**真实变化（官方 NEWS，Major new features 第一条）**：

> The thread-local cache in malloc (tcache) now supports caching of large blocks. This feature can be enabled by setting the tunable `glibc.malloc.tcache_max` to a larger value (max 4194304). Tcache is also significantly faster for small sizes.

即：**tcache 首次支持缓存大块**，上限 `glibc.malloc.tcache_max` 可从默认的 1032 字节（0x408 含头）调到 4194304（4 MB）。默认值不变，所以默认环境行为与 2.41 一致（tcache 仍只收 ≤ 0x400 request）。

**exploit 影响**：
- 默认容器/比赛环境通常不开 tunable → 打法不变；
- 若题目以 `GLIBC_TUNABLES=glibc.malloc.tcache_max=...` 或 `initramfs` 配置显式开了大值：tcache poisoning / 桶重排 / stashing 可以作用到大 chunk（unsorted 层面的大块也能进 tcache），`count ≤ 7` 与 key 检测机制同样作用于大块；
- 检测：`strings libc.so.6 | grep tcache_max` 确认 tunable 存在；运行 `GLIBC_TUNABLES=glibc.malloc.tcache_max=0x100000 ./test` 实测大块释放是否进 tcache。

2.42 其余变化：`<termio.h>` 移除、pthread 锁 elision 弃用（2.43 删除）、GCC 12.1+/Binutils 2.39+ 构建要求、GLIBC-SA-2025 修复若干。符号面与 2.41 一致（无 libio 导出改动，2.42 NEWS 无弃用条目）。

## glibc 2.43 (2026-02): Internal stdio Deprecated

**真实变化（官方 NEWS，"Deprecated and removed features"）**：整批**内建 stdio 数据/函数符号**被标记弃用，列表包含

`_IO_file_jumps`、`_IO_file_overflow`、`_IO_file_write`、`_IO_file_xsputn`、`_IO_list_all`、`_IO_str_overflow`、`_IO_str_underflow`、`_IO_wfile_jumps`、`_IO_wfile_overflow`、`_IO_wfile_underflow`、`_IO_wfile_xsputn` 等几十个；原文：

> … may stop working with a future version of glibc. Unlike other symbol removals, these old applications will not be supported using compatibility symbols.

**要点**：
1. 这是**预告，不是移除**：2.43 实测 `_IO_wfile_jumps@@GLIBC_2.2.5`、`_IO_file_jumps@@GLIBC_2.2.5`、`_IO_list_all@@GLIBC_2.2.5` 全部仍在（本文件作者在 Debian sid 2.43-4 上验证）。2.44-experimental 同样在。
2. **无 compat 符号兜底**：一旦未来版本移除（2.44/2.45），依赖这些符号的 FSOP 链（House of Apple 全家、经典 `_IO_list_all` flush）会直接断，且旧的动态链接程序也不会被兼容——这与以往符号移除策略不同，说明 libio 内建接口在官方眼里"不该被外部使用"。
3. 其他 2.43 变化：`malloc_set_state()` 恒返回 -1（dumped-heap 支持移除；堆快照恢复类技巧失效）；TX lock elision 删除；AArch64 malloc 默认 2MB hugetlb；新增 `mseal(2)`。

**对策**：CTF 目标以**实测符号**为准；同一题目若给了 libc 文件，直接 `nm -D` 后按 [FSOP Symbol Status](#fsop-symbol-status-241-244-measured) 决策。长远看 FSOP 的稳定入口将只剩"合法 vtable 段内偏移 + 动态数据符号（`_IO_2_1_stdout_` 等）"，但 `_IO_2_1_stdout_`/`setcontext` 亦可能受未来调整，写 exploit 前保持核对习惯。

## FSOP Symbol Status 2.41-2.44 measured

以下为**实测**（2.41 = Debian trixie `libc6_2.41-12+deb13u4`；2.43 = Debian sid 宿主；2.44 = Debian experimental `libc6_2.44-3`；均 amd64，`LC_ALL=C nm -D libc.so.6`）。✓ = 动态导出存在。

| 符号 | 用途 | 2.41 | 2.43 | 2.44 | 备注 |
|---|---|---|---|---|---|
| `_IO_wfile_jumps` | House of Apple 2 宽字符 vtable 本体 | ✓ | ✓ | ✓ | 2.43+ 弃用预告 |
| `_IO_wfile_overflow/underflow/xsputn` | 宽字符函数（doallocate 触发点） | ✓ | ✓ | ✓ | — |
| `_IO_file_jumps` | 窄字符 vtable（`_IO_file_overflow` 路径） | ✓ | ✓ | ✓ | 2.43+ 弃用预告 |
| `_IO_file_overflow` / `_IO_file_write` / `_IO_file_xsputn` | 窄字符写原语 | ✓ | ✓ | ✓ | — |
| `_IO_list_all` | exit/abort 时 `_IO_flush_all_lockp` 遍历头 | ✓ | ✓ | ✓ | 2.43+ 弃用预告 |
| `_IO_str_jumps` / `_IO_wstr_jumps` | House of Apple 3 vtable 数据符号 | ✗ | ✗ | ✗ | **2.41 已不导出**（更早已 hidden/局部化）；Apple 3 需先实测 |
| `_IO_str_overflow` / `_IO_str_underflow` | str 路径函数（可作 vtable 内目标） | ✓ | ✓ | ✓ | — |
| `__printf_function_table` / `__printf_arginfo_table` | House of Apple 1 数据符号 | ✗ | ✗ | ✗ | **2.41 已不导出**；Apple 1 在 2.41+ 失效 |
| `global_max_fast` | House of Orange 老变体（改 fastbin 上限） | ✗ | ✗ | ✗ | 2.41 已不导出；Orange 改用 `_IO_list_all` 版 |
| `__free_hook` / `__malloc_hook` | 传统 hook | ✓(weak) | ✓(weak) | ✓(weak) | 2.34+ 已不再被调用，勿用 |
| `_IO_2_1_stdout_` / `_IO_2_1_stderr_` / `setcontext` | FILE 数据、栈迁移 gadget | ✓ | ✓ | ✓ | — |

**读表结论**：2.40-2.44 的 FSOP 攻击面变化不是"wfile 被删"，而是**数据侧符号的消失**（`_IO_str_jumps`、printf 两张表、`global_max_fast`）+ **2.43 起所有 vtable/`_IO_list_all` 的弃用预告**。宽字符（Apple 2）与窄字符（`_IO_file_*`）两条主路径全程存活。

## FSOP Paths Alive vs Dead on 2.41+

- ✅ **`_IO_wfile_jumps` 宽字符路径（House of Apple 2）**：含 `__doallocate` 洞，可直达 `system(fp)` 或 `setcontext` 栈迁移；2.41-2.44 实测可用 → **首选**（链细节见 [heap-techniques.md](heap-techniques.md)）。触发点：`exit()`/`abort()` 的 `_IO_flush_all_lockp` 或 `fflush`/`fclose` 路径走到 `_IO_wfile_overflow` → `_IO_wdoallocbuf` → `_IO_WDOALLOCATE(fp)`。
- ✅ **窄字符 `_IO_file_jumps` 路径**：伪造 FILE 让 `_IO_file_overflow` 按 `_IO_write_base/_IO_write_ptr` 差写穿，或 `_IO_file_write` 把任意内存写到 fd（泄露/写 GOT 区）；依赖 `_IO_file_jumps`/`_IO_file_overflow`，2.41-2.44 全部导出。经典落点：覆写 `_IO_2_1_stdout_` 的 `_IO_write_base/_ptr` → 下一次 `puts`/`exit` 把 `[base,ptr)` 的堆内残留写穿到 fd，实现泄 libc；细节见 [heap-fsop.md](heap-fsop.md)。
- ✅ **`_IO_list_all` + exit flush**：`exit()` → `__run_exit_handlers` → `_IO_cleanup` → `_IO_flush_all_lockp` 遍历链表，2.24+ 一直可用；2.41-2.43 符号在。**vtable 校验提醒**：2.24+ `_IO_vtable_check` 要求 `fp->vtable` 落在 `__libc_IO_vtables` 段内，所以伪造 FILE 的 vtable 字段只能填段内合法符号地址（如 `_IO_wfile_jumps`/`_IO_file_jumps`），不能直接填 `system`。
- ✅ **`_IO_str_overflow` 函数路径（Apple 3 变体的函数侧）**：函数仍导出；但 `_IO_str_jumps` 数据符号 2.41 起缺失，若 exploit 依赖 `libc.sym['_IO_str_jumps']` 需改为"实测 libc 的 vtables 段内偏移"或换 Apple 2。
- ❌ **House of Apple 1**（`__printf_function_table`/`__printf_arginfo_table` 触发 `%c` 打表）：2.41 实测两符号缺失 → 失效。
- ❌ **House of Orange 改 `global_max_fast` 变体**：符号缺失；2.26+ 的 Orange 本来就以 `_IO_list_all` 为目标，走那条。
- ⚠️ `__free_hook`/`__malloc_hook`：符号还在但 2.34+ 无效果，别浪费时间。

**路径选择口诀**：wfile 在 → Apple 2；wfile 不在但 file/list 在 → 窄字符/`_IO_list_all`；全缺 → 极新 libc，回 [heap-fsop.md](heap-fsop.md) 的非 vtable 变体。

## Modern tcache / fastbin Hardening

（2.39-2.43 均成立，为既定事实，无需在 2.40+ 重复验证）

- **safe-linking（2.32+）**：tcache 与 fastbin 的 `fd` 存 `P ^ (chunk_addr >> 12)`。tcache poisoning 写目标时 `mangled = target ^ (cur >> 12)`；泄露 `fd` 可按同一公式解出堆基址。
- **tcache key（2.39+）**：`tcache_put` 在 chunk 用户区首 8 字节写进程随机密钥 `tcache_key`；`tcache_get` 前若 `e->key == tcache_key` 就遍历整桶查重，命中即 abort（"double free detected"）。绕过：UAF 先把 key 字段写成别的值，或经 tcache stashing 用 `bk` 写入覆盖 key。
- **每桶上限 7**，`tcache_count` 置 0 则禁用 tcache；tcache 默认上限 chunk size 1032（0x408 含头，即 request ≤ 0x400）；**2.42+ 可用 `glibc.malloc.tcache_max` 扩到 4 MB**（大块同样受 key/count 约束）。
- **calloc 不从 tcache 取块**（保证清零语义；种进 tcache 的伪造块不会被 calloc 拿出来），但 free 仍可能进 tcache。
- **fastbin**：`global_max_fast` 默认 0x80（0x60 数据区）；2.38 起 fastbin attack（`malloc` 返回 fastbin 中块时）同样要先过 tcache key 关卡；fastbin 也需要 safe-linking。

**快速观察/绕过清单**（写 exploit 前跑一遍，确认目标形态）：
- free 后 `x/8gx chunk`：`[1]` 为随机 key → key 生效；`[0]` 为 mangled fd → safe-linking 生效。
- double-free 想走 tcache：先 UAF 把 `[1]` 写成别的值，或向该桶再放 6 块凑满 7 让后续 double free 进 fastbin/unsorted。
- `malloc(0x410)`（request 0x400+1B 跨桶）观察是否进 tcache：默认不进（超 1032），2.42+ 开 `tcache_max` 后进。
- tcache stashing unlink（`bk` 覆写）在 2.39+ 仍是 tcache key 之外最常用的"无 key 覆盖"写原语。

## Version Identification

```bash
# 1. 版本号（三选一）
ldd --version | head -1                        # "ldd (Ubuntu GLIBC 2.41-…) 2.41" / "Debian GLIBC 2.43-4"
/lib/x86_64-linux-gnu/libc.so.6               # 直接执行打印版本（usrmerge 后 /lib -> /usr/lib 符号链接）
strings libc.so.6 | grep -m1 'GNU C Library'  # 离线 libc 文件

# 2. 容器内
docker run --rm ubuntu:25.04 /lib/x86_64-linux-gnu/libc.so.6
# （发行版映射参考：Ubuntu 24.04=2.39, 24.10=2.40, 25.04=2.41；Debian 12=2.36, 13=2.41, sid=2.42/2.43；Fedora 42+=2.42；final 以 ldd 为准）

# 3. FSOP 符号核查（2.41+ 关键命令）
LC_ALL=C nm -D /path/to/libc.so.6 | grep -E 'wfile_jumps|str_jumps|file_jumps|printf_function_table|global_max_fast'
# 期望：wfile_jumps/file_jumps 在；str_jumps/printf_function_table/global_max_fast 不在（2.41+ 正常现象）

# 4. pwntools 视角
python3 -c "from pwn import *; l=ELF('libc.so.6'); print(l.sym.get('_IO_wfile_jumps'))"
# 输出 None == 符号缺失；有地址 == House of Apple 2 可用
```

## Decision Workflow

拿到堆题（尤其 House of X / FSOP 方向）按此顺序：

1. **定 glibc 版本**：`ldd --version`、容器直跑 `libc.so.6`，或对附件 libc 用 `strings`/pwntools identify。
2. **≤ 2.39**：走 [heap-techniques.md](heap-techniques.md) / [heap-fsop.md](heap-fsop.md) 的既有打法（含 tcache key 绕过）。
3. **2.40-2.44**：`nm -D` 实测符号表再选链（不要按版本号猜）：
   - `_IO_wfile_jumps` 在 → House of Apple 2（首选，`system(fp)` 或 SUID 时 `setcontext` 变体）；
   - 缺 `_IO_wfile_jumps` → 窄字符 `_IO_file_jumps`（`_IO_file_overflow` 写穿 / `_IO_file_write` 泄露）或 `_IO_list_all` + exit flush；
   - 确认 `_IO_str_jumps`/`__printf_function_table` 是否导出：2.41+ 通常已无，Apple 3 / Apple 1 默认不可用；
   - `global_max_fast` 通常已无：House of Orange 走 `_IO_list_all` 版。
4. **2.43+**：记住弃用预告——链还能跑，但未来 libc 随时移除且无 compat 符号；拿题先看它给不给 libc 附件，给了就按附件实测。
5. 全部 FSOP 符号都缺（极新版本）→ 回退 [heap-fsop.md](heap-fsop.md) 的非 vtable 变体（`_IO_buf_base` 空字节劫持、unsorted 覆盖 stdin 字段），或改走 heap overlap 简化目标。

## Evidence and Sources

- glibc 2.40/2.41/2.42/2.43 官方 `NEWS`（via [sources.debian.org glibc](https://sources.debian.org/src/glibc/) 镜像，`Version 2.4x` 条目）：
  - 2.41 无 `_IO_wfile_jumps` 移除条目；libio 仅 [20632] `_IO_wfile_overflow` 越界写修复
  - 2.42 新增 "tcache now supports caching of large blocks"（`glibc.malloc.tcache_max`, max 4194304）
  - 2.43 弃用整批 internal stdio 符号（含 `_IO_file_jumps`/`_IO_wfile_jumps`/`_IO_list_all`），"will not be supported using compatibility symbols"
- 实测符号表：Debian `libc6_2.41-12+deb13u4`（trixie）、宿主 sid `2.43-4`、`libc6_2.44-3`（experimental）的 amd64 `libc.so.6` `nm -D` 结果（见 [FSOP Symbol Status](#fsop-symbol-status-241-244-measured)）。
- 加固事实（safe-linking 2.32、tcache key 2.39、count 7、calloc 不取 tcache）为社区既有共识，可在目标 libc 上用分配/释放测试复核。
- 相关讨论：[libio: validate and mangle the wide vtable](https://patchwork.ozlabs.org/project/glibc/patch/20260824150600.150104-1-7991aleschino@gmail.com/)（2026-08，wide vtable 加固提案）。