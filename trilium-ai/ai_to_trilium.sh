#!/usr/bin/env bash
#
# ai_to_trilium.sh - bridge local Ollama models and TriliumNext notes.
#
# Subcommands:
#   ask [-m MODEL] "PROMPT"
#       Run the prompt through `ollama run MODEL` and save the answer as a new
#       Trilium note titled "[timestamp] PROMPT".
#
#   context NOTE_ID [-m MODEL] "PROMPT"
#       Fetch NOTE_ID's content from Trilium, feed it to the model as context
#       along with PROMPT, and save the answer as a new note.
#
# Options:
#   -m MODEL     Ollama model (default: qwen2.5-coder)
#   -p PARENT    Parent noteId for the new note (default: root)
#
# The model's answer is stored inside a <pre> block so formatting is preserved
# in Trilium's text notes.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRIDGE="$SCRIPT_DIR/trilium_bridge.py"
DEFAULT_MODEL="qwen2.5-coder"

usage() {
  sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
  exit "${1:-1}"
}

html_escape() {
  # Escape &, <, > for safe embedding in a Trilium text (HTML) note.
  sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g'
}

[ $# -ge 1 ] || usage 1
CMD="$1"; shift

MODEL="$DEFAULT_MODEL"
PARENT="root"
NOTE_ID=""

case "$CMD" in
  ask)      : ;;
  context)
    [ $# -ge 1 ] || { echo "context requires a NOTE_ID" >&2; usage 1; }
    NOTE_ID="$1"; shift ;;
  -h|--help|help) usage 0 ;;
  *) echo "Unknown subcommand: $CMD" >&2; usage 1 ;;
esac

# Parse options
while getopts ":m:p:" opt; do
  case "$opt" in
    m) MODEL="$OPTARG" ;;
    p) PARENT="$OPTARG" ;;
    *) usage 1 ;;
  esac
done
shift $((OPTIND - 1))

[ $# -ge 1 ] || { echo "A prompt is required." >&2; usage 1; }
PROMPT="$*"

# Build the full prompt (with note context if requested).
FULL_PROMPT="$PROMPT"
CONTEXT_TITLE=""
if [ "$CMD" = "context" ]; then
  echo ">> Fetching Trilium note $NOTE_ID for context..." >&2
  CONTEXT="$(python3 "$BRIDGE" get "$NOTE_ID")"
  FULL_PROMPT="Use the following note as context.

--- CONTEXT (note $NOTE_ID) ---
$CONTEXT
--- END CONTEXT ---

$PROMPT"
  CONTEXT_TITLE=" (ctx:$NOTE_ID)"
fi

echo ">> Running ollama model '$MODEL'..." >&2
ANSWER="$(printf '%s' "$FULL_PROMPT" | ollama run "$MODEL")"

TS="$(date '+%Y-%m-%d %H:%M')"
# Truncate prompt for the title.
SHORT_PROMPT="$(printf '%s' "$PROMPT" | tr '\n' ' ' | cut -c1-60)"
TITLE="[$TS]$CONTEXT_TITLE $SHORT_PROMPT"

# Compose an HTML body: the prompt, the model, and the answer in a <pre>.
BODY="$(
  printf '<p><b>Model:</b> %s</p>\n' "$MODEL"
  printf '<p><b>Prompt:</b></p>\n<pre>%s</pre>\n' "$(printf '%s' "$PROMPT" | html_escape)"
  printf '<p><b>Answer:</b></p>\n<pre>%s</pre>\n' "$(printf '%s' "$ANSWER" | html_escape)"
)"

echo ">> Saving answer to Trilium..." >&2
printf '%s' "$BODY" | python3 "$BRIDGE" create "$TITLE" --parent "$PARENT"

echo ">> Done." >&2
echo "----- model answer -----"
printf '%s\n' "$ANSWER"
