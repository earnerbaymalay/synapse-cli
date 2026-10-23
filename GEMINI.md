# Workspace Configuration: AI CLI WORK

You are working in the primary AI CLI Work directory (`~/Desktop/AI CLI WORK`).

## Guidelines & Architecture
- **Organization**: Keep projects organized into clean, dedicated subdirectories.
- **Python Environment**: Prefer `uv` (`uv venv`, `uv pip`, `uv run`) for rapid, isolated environments.
- **Model Context Protocol (MCP)**:
  - `fetch`: Web content fetching via `uvx mcp-server-fetch`.
  - `memory`: Knowledge graph persistence via `@modelcontextprotocol/server-memory` backed by `~/.local/share/mcp-memory/memory.json` (shared with Claude Code).
  - `sequential-thinking`: Step-by-step reasoning via `@modelcontextprotocol/server-sequential-thinking`.
- **Local LLM Integration**:
  - Ollama runs locally on port `11434` with 24h keep-alive and single-threaded CPU concurrency protection.
  - Models: `qwen2.5-coder`, `llama3.2`, `nous-hermes2`, `dolphin-mistral`, `qwen-abliterated`.
  - Shell helpers: `ask-qwen`, `ask-llama`, `ask-dolphin`, `ask-hermes`, `ask-ab` (supporting stdin piping).
- **Trilium Notes Integration**:
  - ETAPI bridge available at `trilium-ai/trilium_bridge.py` on `http://localhost:8080`.
- **Network Posture**:
  - `wlan0` is dedicated for RF monitoring/packet capture (`wavescope`, `bettercap`, `tshark`).
  - Ethernet (`enp0s31f6`) is the primary uplink with Quad9 DNS.
  - Do not disrupt network interface states without explicit request.
- **Tooling**:
  - Use `jq` for JSON processing, `ripgrep` for searching, `fd` for discovery, `lazygit` (`lg`) for git, and `xclip` (`clip`/`clippaste`) for clipboard.
