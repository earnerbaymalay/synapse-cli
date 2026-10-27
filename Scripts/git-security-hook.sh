#!/usr/bin/env bash
# ==============================================================================
# Offline Git Security Pre-Commit Hook
# Multi-Tier Local Security & Secret Leak Scanner
# Tier 1: Instant Regex Pattern & Entropy Scanning
# Tier 2: Local AI Security Audit via Resident Ollama (qwen2.5-coder:latest)
# ==============================================================================

set -eo pipefail

RED="\033[1;31m"
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
BLUE="\033[1;34m"
BOLD="\033[1m"
RESET="\033[0m"

log_info() {
    printf "${BLUE}[SEC-HOOK]${RESET} %b\n" "$1"
}

log_pass() {
    printf "${GREEN}[SEC-PASS]${RESET} %b\n" "$1"
}

log_warn() {
    printf "${YELLOW}[SEC-WARN]${RESET} %b\n" "$1"
}

log_fail() {
    printf "${RED}[SEC-FAIL]${RESET} %b\n" "$1"
}

# 1. Check if there are staged changes
STAGED_DIFF=$(git diff --cached --no-color -U0)
if [ -z "${STAGED_DIFF}" ]; then
    exit 0
fi

log_info "Analyzing staged changes for secrets, credentials, and vulnerabilities..."

# Extract only added lines (lines starting with + but not +++)
ADDED_LINES=$(echo "${STAGED_DIFF}" | grep '^+[^+]' || true)

if [ -z "${ADDED_LINES}" ]; then
    log_pass "No new code additions to scan. Commit proceeding."
    exit 0
fi

VIOLATIONS=()

# ------------------------------------------------------------------------------
# TIER 1: Regex Pattern & Secret Signatures
# ------------------------------------------------------------------------------
check_pattern() {
    local name="$1"
    local regex="$2"
    local case_flag="${3:-}"
    local matches
    if [ "$case_flag" = "-i" ]; then
        matches=$(echo "${ADDED_LINES}" | grep -E -i -n -e "${regex}" || true)
    else
        matches=$(echo "${ADDED_LINES}" | grep -E -n -e "${regex}" || true)
    fi
    if [ -n "${matches}" ]; then
        VIOLATIONS+=("${name}:")
        while IFS= read -r line; do
            VIOLATIONS+=("    ${line:0:100}")
        done <<< "${matches}"
    fi
}

check_pattern "AWS Access Key ID" 'AKIA[0-9A-Z]{16}'
check_pattern "GitHub Personal Access Token" '(ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{82})'
check_pattern "Private Cryptographic Key" '-----BEGIN (RSA |EC |DSA |OPENSSH |ENCRYPTED |)PRIVATE KEY-----'
check_pattern "OpenAI / Anthropic API Key" '(sk-[a-zA-Z0-9]{32,}|sk-ant-[a-zA-Z0-9]{32,})'
check_pattern "Slack Token" 'xox[baprs]-[0-9a-zA-Z]{10,48}'
check_pattern "Generic High-Entropy Secret/Password" '(api[_-]?key|secret[_-]?key|client[_-]?secret|auth[_-]?token|passwd|password)[[:space:]]*[:=][[:space:]]*(("[^"]{8,}")|('\''[^'\'']{8,}'\'')|([a-zA-Z0-9_\-]{16,}))' -i

if [ ${#VIOLATIONS[@]} -gt 0 ]; then
    echo ""
    log_fail "${BOLD}CRITICAL SECRET / CREDENTIAL LEAK DETECTED!${RESET}"
    echo "Staged changes contain detected secrets or private credentials:"
    for v in "${VIOLATIONS[@]}"; do
        printf "${RED}%s${RESET}\n" "$v"
    done
    echo ""
    log_fail "Commit aborted to protect against credential leakage."
    echo "To override this check intentionally, use: git commit --no-verify"
    exit 1
fi

log_pass "Tier 1: No secret patterns or credentials detected."

# ------------------------------------------------------------------------------
# TIER 1.5: Quality Gate (shellcheck on staged shell scripts, pytest on Python changes)
# ------------------------------------------------------------------------------
REPO_ROOT="$(git rev-parse --show-toplevel)"
mapfile -t STAGED_FILES < <(git diff --cached --name-only --diff-filter=ACMR)

SHELL_FILES=()
for f in "${STAGED_FILES[@]}"; do
    [ -f "$f" ] || continue
    if [[ "$f" == *.sh ]] || head -n1 "$f" | grep -qE '^#!.*\b(ba)?sh\b'; then
        SHELL_FILES+=("$f")
    fi
done

if [ ${#SHELL_FILES[@]} -gt 0 ]; then
    if command -v shellcheck >/dev/null 2>&1; then
        if ! shellcheck -S warning "${SHELL_FILES[@]}"; then
            log_fail "shellcheck found issues in staged shell scripts."
            exit 1
        fi
        log_pass "Tier 1.5: shellcheck clean (${#SHELL_FILES[@]} script(s))."
    else
        log_warn "shellcheck not installed; skipped shell lint."
    fi
fi

if printf '%s\n' "${STAGED_FILES[@]}" | grep -qE '\.py$|^pyproject\.toml$'; then
    PYTEST="${REPO_ROOT}/.venv/bin/pytest"
    if [ -x "${PYTEST}" ]; then
        if ! (cd "${REPO_ROOT}" && "${PYTEST}" -q >/dev/null 2>&1); then
            log_fail "pytest failed. Run: .venv/bin/pytest"
            exit 1
        fi
        log_pass "Tier 1.5: pytest passed."
    else
        log_warn "pytest not found in .venv; skipped tests."
    fi
fi

# ------------------------------------------------------------------------------
# TIER 2: Local AI Security Audit via Ollama (qwen2.5-coder:latest)
# ------------------------------------------------------------------------------
OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"
MODEL="qwen2.5-coder:latest"

# Check if Ollama is accessible within 1s
if curl -s --max-time 1 "${OLLAMA_HOST}/api/tags" >/dev/null 2>&1; then
    log_info "Tier 2: Performing AI security review using resident ${MODEL}..."
    
    # Cap staged diff to prevent overwhelming prompt
    DIFF_SNIPPET=$(awk 'NR<=120' <<< "${ADDED_LINES}")
    
    PROMPT=$(cat <<EOF
You are a strict security scanner. Analyze the following newly added code lines from a git diff for CRITICAL security vulnerabilities (e.g. secret exposure, command injection, path traversal, eval/exec abuse).
If and only if you find a severe, actionable security flaw or hardcoded secret, respond with:
FAIL: <one brief explanation>
Otherwise, respond with:
PASS

Code lines:
${DIFF_SNIPPET}
EOF
)

    # Call Ollama generate
    RESPONSE=$(curl -s --max-time 8 "${OLLAMA_HOST}/api/generate" \
        -d "$(jq -n --arg m "$MODEL" --arg p "$PROMPT" '{model: $m, prompt: $p, stream: false}')" 2>/dev/null | jq -r '.response' 2>/dev/null || true)

    if echo "${RESPONSE}" | grep -i -q -E "(^|[[:space:]]|\*)FAIL:"; then
        echo ""
        log_fail "${BOLD}Local AI Security Audit Flagged Vulnerability!${RESET}"
        printf "${RED}%s${RESET}\n" "${RESPONSE}"
        echo ""
        log_fail "Commit blocked by local AI security review."
        echo "Fix the issue or override with: git commit --no-verify"
        exit 1
    else
        log_pass "Tier 2: AI security review passed (${MODEL})."
    fi
else
    log_warn "Ollama offline or busy; skipped Tier 2 AI audit (Tier 1 pattern scan was clean)."
fi

exit 0
