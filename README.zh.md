# dsh-ctf

把 [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) 变成 CTF 解题 agent —— 一个可安装的插件。

`dsh plugin --profile web add <本包>` 之后，profile 里会多出三样东西：

- **`ctf` agent preset（「CTF 解题」）**：人格、工具面、并行子 agent、长上下文压缩策略；
- **13 个技能**：`ctf-routing` 入口 + 9 个方向内容库 + `ctf-match-ops`（比赛运营）+ `ctf-writeup`，
  外加独立的 `solve-challenge` 调度器；
- **`scripts/install_ctf_tools.sh`**：各方向 `## Prerequisites` 汇总出的工具链一键安装器。

不改 dsh 源码：插件是一个补丁层 + 一个 `skills` provider，路径在运行时自行解析，因此放在任何 profile
目录、任何机器上都能用，配置里没有写死的绝对路径。

## 安装

```bash
# 从 git 安装（SSH；仓库为私有）
dsh plugin --profile web add "git+ssh://git@github.com/Duststar0313/dsh-ctf.git"

# 从本地目录安装
dsh plugin --profile web add /path/to/dsh-ctf
```

重启应用（`dsh web`），新建会话时 preset 列表里就会出现 **CTF 解题**。

可选 —— 把它设成新会话的默认 preset，写进该 profile 的 `cordis.patch.yml`：

```yaml
- id: agent-preset-registry
  name: '@deepseek-ai/dsh-agent-preset-registry'
  config:
    default: ctf
```

## 验证安装

```bash
node scripts/verify-plugin.mjs          # 插件与 provider 自检，不需要启动 dsh
python3 -m pytest -q                    # 技能库测试：链接、frontmatter、路由索引

dsh --profile web --dump-config | grep -n ctf      # 补丁层已合入
```

启动时若有坏行，会打印 `warning: 1 entry did not activate`；安装正常则没有该告警。

## 使用

打开 Web UI → 新建会话 → 选 **CTF 解题** → 把题目丢进去（URL、压缩包、二进制，或整场比赛加记分板）。
preset 的人格把 `ctf-routing` 定为强制第一步，9 个方向库只能经由路由层选择文件，避免一次性读爆上下文。

工具链，赛前或赛中：

```bash
bash scripts/install_ctf_tools.sh --verify   # 只报告有/缺，不安装
bash scripts/install_ctf_tools.sh all       # 装全平台适用的
bash scripts/install_ctf_tools.sh crypto    # 只装一个方向
```

## 仓库结构

| 路径 | 作用 |
|---|---|
| `cordis.patch.yml` | bundle 补丁层：插入 `ctf` preset（人格、工具、并行、压缩） |
| `lib/index.js` | 全部运行时：零依赖 Cordis 插件，注册 provider `ctf-bundle` |
| `ctf-routing/` | 唯一入口：`routing/<方向>.md` 决策层 + `routing/triage.md` |
| `ctf-web/` `ctf-pwn/` `ctf-reverse/` `ctf-crypto/` `ctf-forensics/` `ctf-misc/` `ctf-malware/` `ctf-osint/` `ctf-ai-ml/` | 方向内容库（技法笔记、脚本） |
| `ctf-match-ops/` `ctf-writeup/` | 比赛运营层；提交级 writeup |
| `solve-challenge/` | 上游独立调度器（留给其它 host 用） |
| `scripts/` | 工具链安装器、目录生成器、安全审计器、自检脚本 |
| `tests/` | 技能库测试：frontmatter、交叉引用、路由索引、代码片段、provider 契约 |
| `docs/` | [安装](docs/INSTALL.md)、[架构](docs/ARCHITECTURE.md)、[AGENTS.md 片段](docs/agents-md-snippet.md) |

## 设计要点

- **无写死路径。** provider 用 `import.meta.url` 推出包根目录，装在
  `~/.dsh/profiles/web/node_modules` 里和软链到本地仓库都成立。
- **零运行时依赖。** `lib/index.js` 只用 `node:` 内置模块；provider 契约只有 `list` + `get`，
  不要求宿主包在插件目录下可解析，因此不会因为宿主版本差异挂掉。
- **rank 600（`bundled`）。** 同一层里同名技能，用户自己的 `~/.dsh/skills`（rank 400）仍然优先。
  如果你之前手工同步过技能，删掉那份才能看到包里这份。
- **`resourceBase`。** 每个技能声明自己的目录，宿主会把它渲染成
  「Base directory for this skill: …」，`SKILL.md` 里的相对链接因此仍然可用。
- **只加不改。** 补丁层只用 `insert:` 增加一行，自带 `standard`/`ptc`/`minimal`/`cordis` 四个 preset 不动。

## 排障

| 现象 | 原因 |
|---|---|
| `warning: N entry did not activate` | 包在 profile 里不可解析 —— 用 `dsh plugin` 重装，检查 `node_modules/dsh-ctf` |
| `a skill provider named "ctf-bundle" is already registered` | 同一作用域挂了两份；留一份，或在 `ctf-skills` 行改 `providerName` |
| 技能内容偏旧 | `~/.dsh/skills` 里的旧副本（rank 400）赢了 —— 删掉 |
| `spawn pnpm ENOENT` | `dsh plugin` 依赖 `PATH` 里的 pnpm |
| `could not read Username for 'https://github.com'` | pnpm 会把 git 依赖按 HTTPS 解析，即使写的是 `git+ssh://` —— 加 `git config --global url."git@github.com:".insteadOf "https://github.com/"`，见[从 git 安装](docs/INSTALL.md#1-from-git-recommended) |
| preset 列表里没有「CTF 解题」 | bundle 没进 `dsh.profile.bundles`；装完要重启应用 |

## 来源与许可

- 插件代码、路由层、`ctf-match-ops`、`ctf-writeup`、`solve-challenge` 装配：本仓库，MIT。
- 技能内容派生自 [`ljagiello/ctf-skills`](https://github.com/ljagiello/ctf-skills)
  （MIT，Copyright (c) 2026 Lukasz Jagiello），并在本地扩写 —— 详见 [NOTICE.md](NOTICE.md)。

MIT，见 [LICENSE](LICENSE)。
