# AI CLI WORK - Claude Code Configuration

This workspace is the primary environment for AI agent orchestration, development, and network analysis.

## Core Guidelines
- **Project Structure**: Keep projects modularized into subdirectories within `~/Desktop/AI CLI WORK/`.
- **Python Tooling**: Use `uv` (`uv venv`, `uv pip`, `uv run`) for rapid, isolated environments.
- **Model Context Protocol (MCP)**:
  - `fetch`: Web content fetching via `uvx mcp-server-fetch`.
  - `memory`: Persistent entity/relation knowledge graph via `@modelcontextprotocol/server-memory` backed by `~/.local/share/mcp-memory/memory.json` (shared with Gemini).
  - `sequential-thinking`: Step-by-step hypothesis testing and complex reasoning via `@modelcontextprotocol/server-sequential-thinking`.
- **Local LLMs (Ollama)**:
  - Endpoint: `http://localhost:11434` (systemd daemon with `OLLAMA_KEEP_ALIVE=24h`, `OLLAMA_NUM_PARALLEL=1`).
  - Active models: `qwen2.5-coder:latest`, `llama3.2:latest`, `dolphin-mistral:latest`, `nous-hermes2:latest`, `qwen-abliterated:latest`.
  - Shell helpers (supports stdin piping): `ask-qwen`, `ask-llama`, `ask-dolphin`, `ask-hermes`, `ask-ab`, `ask-ollama`.
  - State monitoring: `ollama ps` checks resident RAM usage.
- **Trilium Notes Integration**:
  - ETAPI bridge available at `trilium-ai/trilium_bridge.py` and `trilium-ai/ai_to_trilium.sh` on `http://localhost:8080`.
- **Networking & Pentesting**:
  - `wlan0` is unmanaged and dedicated for RF monitoring/packet capture (`bettercap`, `wavescope`, `tshark`).
  - Ethernet (`enp0s31f6`) is the primary network link with Quad9 DNS.
  - Do not alter network interfaces without explicit instructions.
- **Shell & Tools**:
  - Modern CLI utilities: `bat` (cat), `eza` (ls), `ripgrep` (`rg`), `fd`, `jq`, and `lazygit` (`lg`).
  - Clipboard: `clip` (`xclip -selection clipboard`) and `clippaste`.
