# AI CLI WORK - Claude Code Configuration

This workspace is the primary environment for AI agent orchestration, development, and network analysis.

## Core Guidelines
- **Project Structure**: Keep projects modularized into subdirectories within `~/Desktop/AI CLI WORK/`.
- **Python Tooling**: Use `uv` (`uv venv`, `uv pip`, `uv run`) for rapid, isolated environments.
- **Model Context Protocol (MCP)**:
  - `fetch`: Web content fetching via `uvx mcp-server-fetch`.
  - `memory`: Persistent entity/relation knowledge graph via `@modelcontextprotocol/server-memory` backed by `~/.local/share/mcp-memory/memory.json` (shared with Gemini).
  - `sequential-thinking`: Step-by-step hypothesis testing and complex reasoning via `@modelcontextprotocol/server-sequential-thinking`.
  - `filesystem`: Scoped, structured filesystem operations via `@modelcontextprotocol/server-filesystem` for `~/Desktop/AI CLI WORK`.
- **Local LLMs (Ollama)**:
  - Endpoint: `http://localhost:11434` (systemd daemon with `OLLAMA_KEEP_ALIVE=24h`, `OLLAMA_NUM_PARALLEL=1`).
  - Active models: `qwen2.5-coder:latest`, `llama3.2:latest`, `dolphin-mistral:latest`, `nous-hermes2:latest`, `qwen-abliterated:latest`.
  - Shell helpers (supports stdin piping & options): `ask-qwen`, `ask-llama`, `ask-dolphin`, `ask-hermes`, `ask-ab`, `ask-ollama [-m model] [prompt]`.
  - State monitoring & management: `ollama ps` checks resident RAM usage; `ollama-stop [model]` or `ollama-flush` unloads models to free RAM; `ollama-warm` pre-loads the code model.
- **Central AI Knowledge Base (Obsidian)**:
  - Markdown repository at `~/Obsidian/AI-Knowledge-Base` (`OBSIDIAN_AI_VAULT`).
  - High-signal retention policy: conversational filler is discarded; only distilled decisions, verified solutions, workflows, and insights are archived.
  - Shell commands: `ai-log [note]`, `ai-kb add --category [decisions|insights|solutions|workflows|daily]`, `ai-kb distill [text/pipe]`, `ai-kb ask [prompt]`, `ai-kb search [query]`, and `ai-kb open`.
- **Networking & Pentesting**:
  - `wlan0` is unmanaged and dedicated for RF monitoring/packet capture (`bettercap`, `wavescope`, `tshark`).
  - Ethernet (`enp0s31f6`) is the primary network link with Quad9 DNS.
  - Do not alter network interfaces without explicit instructions.
- **Shell & Tools**:
  - Modern CLI utilities: `bat` (cat), `eza` (ls), `ripgrep` (`rg`), `fd`, `jq`, and `lazygit` (`lg`).
  - Python: `venv` function auto-activates existing `.venv` (with `ollama` SDK installed) or creates a new one via `uv`.
  - Clipboard: `clip` (`xclip -selection clipboard`) and `clippaste`.
