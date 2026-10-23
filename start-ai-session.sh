#!/bin/bash
echo "╔══════════════════════════════════════════════════════╗"
echo "║          🤖 AI CLI WORK - Unified Session            ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "📓 Checking Trilium Notes..."
if ! pgrep -x "triliumnext" > /dev/null; then
  echo "  → Starting Trilium..."
  triliumnext &>/dev/null &
  sleep 1
fi
echo "  → Trilium ready at http://localhost:8080"
echo ""
echo "🤖 Local Ollama Models (Active):"
echo "  ollama run nous-hermes2     → 6.1GB  conversational, low-refusal"
echo "  ollama run dolphin-mistral  → 4.1GB  uncensored, instruction-tuned"
echo "  ollama run qwen2.5-coder    → 4.7GB  code specialist (or: ask-ollama '<prompt>')"
echo "  ollama run llama3.2         → 2.0GB  fast, general purpose"
echo ""
echo "🛠️  AI Assistants & MCP:"
echo "  claude          → Claude Code (Project: CLAUDE.md | MCP: fetch)"
echo "  agy             → Antigravity CLI / Gemini (Project: GEMINI.md | MCP: fetch)"
echo "  huggingface-cli → HuggingFace Hub"
echo ""
echo "⚡ Modern Dev Shortcuts:"
echo "  lg              → lazygit (visual Git TUI)"
echo "  clip / clippaste→ clipboard copy/paste (xclip)"
echo "  venv / activate → instant uv-powered Python environment"
echo "  aiwork          → return to ~/Desktop/AI CLI WORK"
echo ""
cd "$HOME/Desktop/AI CLI WORK"
exec bash
