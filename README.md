# Synapse CLI

> **The Canonical AI Engineering CLI, Privacy Audit & Workstation Suite for EndeavourOS & SynapseOS.**  
> *Bridging Antigravity CLI (`agy`), Claude Code, Local Ollama, RF security auditing, and the Synapse AI Brain.*

```
   ███████ ██    ██ ███    ██  █████  ██████  ███████ ███████      ██████ ██      ██ 
   ██       ██  ██  ████   ██ ██   ██ ██   ██ ██      ██          ██      ██      ██ 
   ███████   ████   ██ ██  ██ ███████ ██████  ███████ █████       ██      ██      ██ 
        ██    ██    ██  ██ ██ ██   ██ ██           ██ ██          ██      ██      ██ 
   ███████    ██    ██   ████ ██   ██ ██      ███████ ███████      ██████ ███████ ██ 
```

Primary workspace for AI agent orchestration (Claude Code, Gemini/Antigravity `agy`, local Ollama), network analysis, and desktop tooling on EndeavourOS. Agent instructions live in `CLAUDE.md` / `GEMINI.md` / `AGENTS.md`.

## `lab` & `synapse` CLI Integrations

One entry point (`~/.local/bin/lab` → `.venv/bin/lab`, editable install of `src/lab`):

| Command | What it does |
|---|---|
| `lab audit [--format text\|json\|genmon]` | Checks live state against the Prime Directive (MAC randomization, DoT/Quad9, firewalld DROP + `stealth-egress` policy, ICMP, Avahi, public listeners, Syncthing discovery). Exit 1 on any failure. Also drives the 󰒃 shield in the top bar. |
| `lab lines [--hours N] [--format text\|json\|genmon]` | Counts **vibe-coded vs hand-coded** lines in a rolling window (default 24h). Vibe lines come from agent transcripts (Claude Code `*.jsonl`, Antigravity `*.db`); hand lines from uncommitted + untracked git changes minus matched AI lines. In-window commits are reported separately (mixed authorship). Drives the 󰚩·✍ counter in the top bar. Set `LAB_CODE_ROOTS=/a:/b` to override which trees are scanned for repos. |
| `lab status` | Command center dashboard (`Scripts/command_center.py`) |
| `lab pcap` / `lab scan` / `lab capture` / `lab scope` | `pentest-scope/` tools — see `PENTEST-LAB-GUIDE.md` and `pentest-scope/AUTHORIZATION.md` |
| `lab backup` | `Scripts/backup-system-configs.sh` |

```bash
uv pip install -p .venv -e . pytest   # (re)install
.venv/bin/pytest                      # run tests
```

## Layout

- `src/lab/` — Python package (`cli.py`, `audit.py`); tests in `tests/`
- `Scripts/` — command center, `agy-menu`/`agy-widget`, pre-commit hook, `.desktop` launchers
- `pentest-scope/` — scoped capture / RF survey / AI pcap analysis (authorized targets only)
- `mitmproxy-tools/` — mitmproxy addons for lab traffic
- `.agents/` — Antigravity rules and skills

## Pre-commit hook

`.git/hooks/pre-commit` → `Scripts/git-security-hook.sh`:
1. Regex/entropy secret scan
2. Quality gate: `shellcheck -S warning` on staged shell scripts, `pytest` when Python changes
3. Local AI review via resident `qwen2.5-coder` (skipped if Ollama is offline)
