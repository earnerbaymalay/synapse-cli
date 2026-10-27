#!/bin/bash
# AI CLI Session Launcher
# Ensures backend daemons are warm and drops directly into the unified AI shell

# 1. Background Ollama pre-warm
curl -s -X POST http://localhost:11434/api/generate -d '{"model": "qwen2.5-coder:latest"}' > /dev/null 2>&1 &

# 2. Enter AI CLI Work directory and launch unified interactive shell
cd "$HOME/Desktop/AI CLI WORK" || exit 1
exec bash
