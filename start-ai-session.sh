#!/bin/bash
echo "╔══════════════════════════════════════════════════════╗"
echo "║          🤖 AI CLI WORK - Unified Session            ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "📓 Checking Trilium Notes..."
if ! pgrep -x "triliumnext" > /dev/null; then
  echo "  → Starting Trilium on port 8080..."
  TRILIUM_PORT=8080 triliumnext &>/dev/null &
  sleep 2
fi
echo "  → Trilium ready at http://localhost:8080"
echo ""

echo "🦙 Pre-warming Ollama Code Engine..."
# Trigger async background warm-up of qwen2.5-coder into RAM
curl -s -X POST http://localhost:11434/api/generate -d '{"model": "qwen2.5-coder:latest"}' > /dev/null 2>&1 &
echo "  → Model 'qwen2.5-coder:latest' warming in RAM (24h keep-alive active)"
echo ""

echo "🤖 Local Ollama Shortcuts & Models:"
echo "  ask-qwen \"prompt\"      → Qwen 2.5 Coder (code specialist, accepts stdin piping)"
echo "  ask-llama \"prompt\"     → LLaMA 3.2 (fast general purpose)"
echo "  ask-dolphin \"prompt\"   → Dolphin Mistral (uncensored instruction-tuned)"
echo "  ask-hermes \"prompt\"    → Nous Hermes 2 (conversational, low refusal)"
echo "  ask-ab \"prompt\"        → Qwen Abliterated"
echo "  ollama ps              → View currently loaded models and RAM usage"
echo ""

echo "🛠️  AI CLI Assistants (Shared MCP Context):"
echo "  claude          → Claude Code (CLAUDE.md | MCP: fetch, memory, sequential-thinking)"
echo "  agy             → Antigravity / Gemini (GEMINI.md | MCP: fetch, memory, sequential-thinking)"
echo ""

echo "⚡ Modern Dev & Shell Shortcuts:"
echo "  lg              → lazygit (Git TUI)"
echo "  clip / clippaste→ clipboard copy/paste (xclip)"
echo "  venv / activate → instant uv-powered Python environment"
echo "  aiwork          → return to ~/Desktop/AI CLI WORK"
echo ""

cd "$HOME/Desktop/AI CLI WORK"
exec bash
