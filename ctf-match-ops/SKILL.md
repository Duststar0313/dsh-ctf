---
name: ctf-match-ops
description: 'Competition operations for a live CTF: timeboxing, parallel triage across many challenges, flag capture/submission discipline, and solve-to-writeup handoff. Use when running a whole event, not one challenge.'
whenToUse: 'A live CTF event is running and you must manage many challenges, a scoreboard, or limited time — not for solving a single isolated challenge (use ctf-routing for that).'
license: MIT
---

# CTF Match Operations

This skill is the **operations layer** for a running competition. `ctf-routing` answers *"how do I solve this
one challenge"*; this skill answers *"how do I run the whole event without wasting time"*.

Load this **in addition to** `ctf-routing`, not instead of it. Every individual challenge still enters
through `ctf-routing`.

## When to use

- An event is live and there is a scoreboard and a clock.
- Several challenges are available at once and choosing *what* to attempt matters as much as solving it.
- You are working as one agent inside a team, and someone (or something) must own triage and dedup.

Do **not** use this for a single offline challenge with no time pressure — go straight to `ctf-routing`.

## Core loop

```
recon the board  ->  triage & rank  ->  assign  ->  solve (ctf-routing)  ->  capture flag
      ^                                                                          |
      |                                                                          v
      +------------------ re-rank on new intel <-- record --< submit & verify >--+
```

### 1. Recon the board (once, then on change)

Establish the playing field before touching any challenge:

- **Event facts**: name, start/end time, duration, scoring model (static vs dynamic/decay), whether
  hints cost points, number of attempts allowed per flag.
- **Flag format**: get it from the event rules, e.g. `flag{...}`, `CTF{...}`, `HTB{...}`. Write it down.
  A wrong-format guess silently wastes a submission.
- **Categories present and their point distribution** — tells you where the best value per unit time is.
- **Board state**: which challenges are already solved (by you or your team), which have the most
  solves (usually easiest), which have zero solves (often a trap, sometimes the jackpot).
- **Infra**: challenge hostnames/ports, any provided VPN/credentials, file downloads, container limits.

On CTFd, do all of this through the REST API, not a browser — see
[ctfd-navigation.md](../ctf-misc/ctfd-navigation.md) in `ctf-misc`. An API token must be created by the
user; ask for it.

### 2. Triage and rank

Score each unsolved challenge on **expected value per unit time**, not on how fun it looks:

| Signal | Interpretation |
|---|---|
| Many solves, low points | Warm-up; take it fast, it is usually a known technique |
| Few solves, high points | High value but budget a hard timebox and be willing to abandon |
| Zero solves, mid points | Frequently broken/unsolvable; do not burn the event on it |
| Category you have a library for | `ctf-routing` has content; cheap to attempt |
| Category with no tooling installed | Check the missing-tools list first; installing mid-event costs time |

Prefer **width over depth early**: attempt the cheapest correct solve across several categories before
committing to one hard target. Depth is for after the easy points are banked.

### 3. Assign and parallelize

- One owner per challenge. Two agents on the same challenge duplicate work and race on the same files.
- Give each challenge its **own working directory** (`challenges/<name>/`) so downloads, scripts, and
  dumps never collide.
- Use background jobs for anything long: brute force, hash cracking, fuzzing, large downloads, a pwn
  process waiting on a socket. Never block the main loop on a long-running command.
- Delegate genuinely independent challenges to subagents/teammates, and tell each one the flag format,
  the time budget, and the reporting format up front.
- Re-check the board between waves; a new hint or a released challenge changes the ranking.

### 4. Capture and verify the flag

- Extract the flag **exactly** — trailing whitespace, newlines, and copy-paste truncation are the most
  common causes of a "correct" flag being rejected.
- Verify against the official format before submitting.
- Record where it came from (file, response, memory offset) so the writeup is reproducible.
- **Submission attempts are often limited** — do not spray guesses.
- If a flag is rejected, do not immediately re-submit variants; re-read the challenge for a second
  stage or a decoy flag first.

### 5. Record and hand off

Maintain a running solve log as you go, not at the end. For each solved challenge capture:
name, category, points, flag, time-to-solve, tools used, one-paragraph approach, and the solve script path.

**Keep a process trace, not just the outcome.** While solving, save key steps to
`challenges/<name>/trace.md` — the significant commands, their key outputs, and what each
conclusion was based on. This is the asset for post-event review ("where did I get stuck"),
for a later attempt that resumes from zero, and for any future trajectory-based training.
Minimal format (append entries as you go):

```markdown
# trace — <challenge name>

## <HH:MM> <phase/idea>
- cmd: `<command>`
- got: <key output, one line>
- conclude: <what this rules in/out>
```

At the bottom keep a running `## untried` list of not-yet-attempted ideas — this is what a
resumed attempt reads first (Rule 4 in `ctf-routing`).

When a challenge is solved, hand off to `ctf-writeup` for the standardized writeup. Under time pressure,
record the raw log immediately and generate the polished writeup during a lull or after the event.

## Timeboxing discipline

- Set an explicit budget per challenge **before** starting (e.g. 20 min for a low-point challenge).
- When the budget expires, decide deliberately: extend once with a reason, park it, or abandon it.
  Parking requires writing down current state so a later attempt does not restart from zero.
- **Decide the "extend once" using failure attribution** (Rule 3 in `ctf-routing` § Operating
  Discipline): L1 tool error or L2 insufficient recon → worth one extension; L3 wrong strategy →
  extend only to switch the attack vector; L4 cognitive bias / repeated same failure → do **not**
  extend, park it — more time on the same path will not pay.
- Track total elapsed event time. Late in the event, favor challenges that are nearly solved over
  fresh attractive ones.
- A failed tool install or a broken environment is a time sink: cap debugging it, and note the missing
  tool for the post-event fix.

## Common failure modes

| Failure | Cost | Avoidance |
|---|---|---|
| Solving depth-first on one hard challenge | Loses all easy points | Rank by expected value; take width first |
| Two workers on one challenge | Duplicated effort, file races | Single owner per challenge, own directory |
| Blocking on a long-running command | Idle event time | Background jobs, check back later |
| Wrong flag format / stray whitespace | Wasted limited attempts | Confirm format at recon; trim before submit |
| Guessing the flag repeatedly | Burns attempts | Re-read the challenge; look for a second stage |
| No solve log | Unwritable writeup at the end | Log continuously, not retrospectively |

## Reporting format

When reporting status on a challenge, be terse and structured — the human is triaging several at once:

```
[challenge] category | points | status: solving|solved|parked|blocked
flag: <flag or ->
evidence: <one line: where the flag came from>
next: <concrete next step or "none">
```

## Related

- `ctf-routing` — the entry point for actually solving each challenge (load it first).
- `ctf-writeup` — standardized writeup once solved.
- `ctf-misc/ctfd-navigation.md` — CTFd REST API automation, including flag submission.
