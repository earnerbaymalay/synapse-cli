# TriliumNext ↔ AI CLI Bridge

A small, dependency-light bridge that lets local AI tools (`ollama`, the
`claude` CLI, scripts) read and write notes in **TriliumNext Notes** through its
REST API (**ETAPI**).

- **Bridge client:** `trilium_bridge.py` (Python 3 stdlib only — no pip installs)
- **AI wrapper:** `ai_to_trilium.sh` (Ollama → Trilium note, and note → Ollama context)
- **Config template:** `.trilium-env.template`

Everything talks to Trilium at `http://localhost:8080` (the port the launcher
`~/Desktop/AI CLI WORK/start-ai-session.sh` expects). TriliumNext is a desktop
(Electron) app; the launcher starts it and it serves ETAPI on that port.

---

## 1. One-time setup — generate an ETAPI token (MANUAL, required)

ETAPI needs an auth token. Tokens **cannot** be created non-interactively
without your Trilium password, so create one in the UI:

1. Start Trilium (the launcher does this, or run `TRILIUM_PORT=8080 triliumnext &`).
2. In TriliumNext open **Options** (menu / gear icon, top-left) → **ETAPI** tab.
   - If ETAPI calls are rejected even with a token, also check
     **Options → Advanced** / **Settings → Security** and ensure the API is on.
3. Click **Create new ETAPI token**, name it (e.g. `ai-cli`), and copy the
   token string (shown only once).

Then wire it into the bridge:

```bash
cd ~/Desktop/AI\ CLI\ WORK
cp trilium-ai/.trilium-env.template .trilium-env
# edit .trilium-env and paste the token after TRILIUM_ETAPI_TOKEN=
chmod 600 .trilium-env
```

The bridge looks for the token in this order:

1. `$TRILIUM_ETAPI_TOKEN` environment variable
2. `~/Desktop/AI CLI WORK/.trilium-env` (or the path in `$TRILIUM_ENV_FILE`)

The base URL comes from `$TRILIUM_URL` or `.trilium-env`, defaulting to
`http://localhost:8080`.

> Keep `.trilium-env` out of version control. Only the `.template` is safe to share.

---

## 2. `trilium_bridge.py` — commands

```bash
cd ~/Desktop/AI\ CLI\ WORK/trilium-ai

# connectivity / auth test
./trilium_bridge.py info

# search notes -> prints "<noteId>\t<title>"
./trilium_bridge.py search "project ideas"

# print a note's content
./trilium_bridge.py get <noteId>

# create a note (content from --content or stdin)
echo "hello from the CLI" | ./trilium_bridge.py create "My note"
./trilium_bridge.py create "My note" --content "hello" --parent root --type text

# append to an existing note (content from --content or stdin)
echo "another line" | ./trilium_bridge.py append <noteId>
```

If no token is configured, every command exits with a clear message pointing you
to **Options → ETAPI → Create new token**.

---

## 3. `ai_to_trilium.sh` — Ollama ↔ Trilium

```bash
cd ~/Desktop/AI\ CLI\ WORK/trilium-ai

# Ask a local model and save its answer as a timestamped Trilium note
./ai_to_trilium.sh ask "Explain the observer pattern in one paragraph"

# Choose a model (default: qwen2.5-coder) and/or a parent note
./ai_to_trilium.sh ask -m llama3.2 "Give me three blog title ideas"
./ai_to_trilium.sh ask -m dolphin-mistral -p <parentNoteId> "Draft a README intro"

# Use an existing note as context for the model, then save the answer
./ai_to_trilium.sh context <noteId> "Summarize this note as five bullets"
./ai_to_trilium.sh context <noteId> -m qwen2.5-coder "Turn these notes into a checklist"
```

Each run creates a note titled `[YYYY-MM-DD HH:MM] <prompt>`, with the model
name, the prompt, and the answer stored in `<pre>` blocks. The answer is also
echoed to your terminal.

Available Ollama models on this machine: `nous-hermes2`, `dolphin-mistral`,
`qwen2.5-coder` (default), `llama3.2`.

---

## 4. Smoke test (after you add the token)

```bash
cd ~/Desktop/AI\ CLI\ WORK/trilium-ai

# 1. confirm auth works
./trilium_bridge.py info

# 2. create a test note and capture its id
echo "created by the AI bridge" | ./trilium_bridge.py create "AI Bridge Test"

# 3. find it and read it back
./trilium_bridge.py search "AI Bridge Test"
./trilium_bridge.py get <noteId-from-search>

# 4. end-to-end AI round-trip
./ai_to_trilium.sh ask "Say hello and confirm the bridge works"
```

---

## 5. How it maps to ETAPI

| Bridge command | ETAPI call |
| --- | --- |
| `search`  | `GET /etapi/notes?search=...` |
| `get`     | `GET /etapi/notes/{id}/content` |
| `create`  | `POST /etapi/create-note` |
| `append`  | `GET` then `PUT /etapi/notes/{id}/content` |
| `info`    | `GET /etapi/app-info` |

Auth is sent as the `Authorization: <token>` request header.

---

## 6. Data location (for reference / backups)

- Trilium data dir: `~/.local/share/trilium-data`
- SQLite database: `~/.local/share/trilium-data/document.db`
- Config: `~/.local/share/trilium-data/config.ini`

The bridge never touches the database directly — it only uses ETAPI over HTTP,
so Trilium must be running for it to work.

---

## 7. Troubleshooting

- **`cannot reach Trilium ...`** — Trilium isn't running, or not on port 8080.
  Start it with `TRILIUM_PORT=8080 triliumnext &` or via the launcher.
- **`HTTP 401`** — token missing/invalid; regenerate it in Options → ETAPI.
- **`HTTP 400` on create** — the `--parent` noteId doesn't exist; use `root` or a
  real note id from `search`.
