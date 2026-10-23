# Workspace Configuration: AI CLI WORK

You are working in the primary AI CLI Work directory (`~/Desktop/AI CLI WORK`).

## Guidelines & Architecture
- **Organization**: Keep projects organized into clean, dedicated subdirectories.
- **Python Environment**: Prefer `uv` (`uv venv`, `uv pip`, `uv run`) for rapid, isolated environments.
- **Local LLM Integration**: Ollama runs locally on port `11434` with installed models (`qwen2.5-coder`, `nous-hermes2`, `dolphin-mistral`, `llama3.2`).
- **Network Posture**:
  - `wlan0` is dedicated for RF monitoring/packet capture (`wavescope`, `bettercap`, `tshark`).
  - Ethernet (`enp0s31f6`) is the primary uplink with Quad9 DNS.
  - Do not disrupt network interface states without explicit request.
- **Tooling**:
  - Use `jq` for JSON processing, `ripgrep` for searching, `fd` for discovery, and `xclip` for clipboard access.
