# AI CLI WORK - Claude Code Configuration

This workspace is the primary environment for AI agent orchestration, development, and network analysis.

## Core Guidelines
- **Project Structure**: Keep projects modularized into subdirectories within `~/Desktop/AI CLI WORK/`.
- **Python Tooling**: Use `uv` (`uv venv`, `uv pip`, `uv run`) for rapid, isolated environments.
- **Local LLMs**: Ollama is active on `http://localhost:11434`. Available models include `qwen2.5-coder:latest`, `dolphin-mistral:latest`, `nous-hermes2:latest`, and `llama3.2:latest`.
- **Networking & Pentesting**:
  - `wlan0` is unmanaged and dedicated for RF monitoring/packet capture (`bettercap`, `wavescope`, `tshark`).
  - Ethernet (`enp0s31f6`) is the primary network link with Quad9 DNS.
  - Do not alter network interfaces without explicit instructions.
- **Shell & Tools**:
  - Prefer modern CLI tools: `bat` for viewing, `eza` for directory listings, `ripgrep` (`rg`) for search, `fd` for file discovery, and `jq` for JSON manipulation.
  - Use `xclip -selection clipboard` for clipboard interactions.
