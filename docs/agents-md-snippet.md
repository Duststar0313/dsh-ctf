# AGENTS.md snippet (optional)

`ctf` preset 的人格已经包含下面的核心规则。把这段追加到 `~/.dsh/AGENTS.md`，可以让你在**非 ctf preset**
的普通会话里也遵守同样的 CTF 工作流；不装这一节也不影响插件工作。

路径说明：技能由插件自带的 provider 提供，不需要你写死任何目录。若你另外把技能同步到了
`~/.dsh/skills`，那份会以 rank 400 优先于包内副本（rank 600）。

```markdown
## CTF work: always start at `ctf-routing`

`ctf-routing` 是任何 CTF 任务的**唯一入口**：新题目、新二进制、流量包、URL、压缩包都算。
加载它之后按它的流程走：

1. 加载 `ctf-routing`（同时会拿到该技能的基础目录）。
2. 判断方向；不确定时先读 `routing/triage.md`。
3. 读 `routing/<direction>.md` —— 该方向的决策层（范围、File Index、决策树）。
4. 只打开索引点名的那**一个**内容文件；用 grep 定位章节，不要整篇读入。

不要直接打开 ctf-web / ctf-pwn / ctf-reverse / ctf-crypto / ctf-forensics / ctf-misc /
ctf-malware / ctf-osint / ctf-ai-ml 的内容文件：它们是由路由层选择的内容库。

`ctf-writeup` 与 `ctf-match-ops` 不是内容库，各自只有一个 `SKILL.md`，可以直接加载。
`ctf-writeup` 是终点技能：解题完成后再交给它。`solve-challenge` 在装了 `ctf-routing` 时是冗余的。

## Live CTF events: add `ctf-match-ops`

涉及**正在进行的比赛**（有记分板、有时间限制、同时多题、需要提交 flag）时，在 `ctf-routing` 之外
再加载 `ctf-match-ops`：它掌管看板 triage、按期望值排序、单题时间盒、并行分工与 flag 格式/提交纪律。

- 一题一个 owner；每题独立目录 `challenges/<name>/`。
- 长跑任务（爆破、破解、fuzz、socket 等待、大文件下载）放后台任务。
- 侦察阶段就确认准确的 flag 格式；提交前 trim 空白 —— 提交次数有限。
- 持续维护解题日志。
- 安装任何东西前先查工具链现状，并给安装本身设时间盒。

单题、离线、没有时钟：不用 `ctf-match-ops`。
```

## 工具链提示

安装器在包内：`bash scripts/install_ctf_tools.sh --verify`。

Python 包请一律用 `python3 -m pip install --break-system-packages X`。有些镜像把 Python 2.7 的 `pip`
排在 `PATH` 前面，裸 `pip install` 会装进一个没有 CTF 脚本会用的解释器。

`angr` 单独放一个 venv，因为它的 `z3-solver` 会遮蔽系统 `z3`：

```bash
python3 -m venv ~/.dsh/venvs/angr
~/.dsh/venvs/angr/bin/python -m pip install angr
```
