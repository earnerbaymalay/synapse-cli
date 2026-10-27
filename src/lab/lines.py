"""Vibe-coded vs hand-coded line counter over a rolling window (default 24h).

Vibe (AI) lines come from agent transcripts, which record every file edit exactly:
  - Claude Code: ~/.claude/projects/**/*.jsonl  (structuredPatch / bashEditDiff "+" lines,
    full content for newly created files)
  - Antigravity / agy: ~/.gemini/antigravity*/conversations/*.db  (protobuf tool calls:
    write_to_file, write_file, replace_file_content, multi_replace_file_content, edit_file)

Hand lines are inferred from git: lines added per file in commits inside the window plus
uncommitted working-tree changes, minus the AI lines that landed in that same file
(floored at 0). Git trailers aren't used because agent commits here carry none.
"""

from __future__ import annotations

import difflib
import json
import os
import sqlite3
import subprocess
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

HOME = Path.home()
CLAUDE_DIR = HOME / ".claude/projects"
AGY_GLOB = ".gemini/antigravity*/conversations/*.db"
AGY_DONE = 3  # step status for a completed tool call
DEFAULT_ROOTS = [HOME / "Desktop", HOME / "Projects", HOME / "jailbox", HOME / "Downloads"]
SKIP_SUFFIXES = (".lock", ".min.js", ".min.css", ".map", ".svg", ".csv", ".log", ".pcap")
SKIP_NAMES = {"package-lock.json", "pnpm-lock.yaml", "yarn.lock", "uv.lock", "Cargo.lock"}


@dataclass
class Tally:
    by_source: Counter = field(default_factory=Counter)
    by_file: Counter = field(default_factory=Counter)

    def add(self, source: str, path: str, n: int) -> None:
        if n <= 0 or not path or not counted(path):
            return
        self.by_source[source] += n
        self.by_file[os.path.realpath(path)] += n

    @property
    def total(self) -> int:
        return sum(self.by_source.values())


def counted(path: str) -> bool:
    name = os.path.basename(path)
    return not (name in SKIP_NAMES or name.endswith(SKIP_SUFFIXES))


def added_lines(old: str, new: str) -> int:
    """Lines present in `new` but not `old` — same notion as '+' lines in a unified diff."""
    sm = difflib.SequenceMatcher(None, old.splitlines(), new.splitlines(), autojunk=False)
    return sum(j2 - j1 for tag, _, _, j1, j2 in sm.get_opcodes() if tag in ("replace", "insert"))


def count_plus(hunks: list[dict]) -> int:
    return sum(1 for h in hunks for ln in h.get("lines", []) if ln.startswith("+"))


# --- Claude Code ---------------------------------------------------------------

def parse_iso(ts: str) -> float:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()


def claude_entry_lines(entry: dict) -> list[tuple[str, int]]:
    """(file, added_lines) for one transcript entry carrying a tool result."""
    res = entry.get("toolUseResult")
    if not isinstance(res, dict):
        return []
    out = []
    if "filePath" in res:
        if res.get("type") == "create":
            out.append((res["filePath"], len(res.get("content", "").splitlines())))
        else:
            out.append((res["filePath"], count_plus(res.get("structuredPatch") or [])))
    for f in (res.get("bashEditDiff") or {}).get("files", []):
        out.append((f["filePath"], count_plus(f.get("hunks", []))))
    return out


def scan_claude(since: float, tally: Tally, root: Path = CLAUDE_DIR) -> None:
    for path in root.rglob("*.jsonl"):
        try:
            if path.stat().st_mtime < since:
                continue
            fh = path.open(encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            for line in fh:
                if '"toolUseResult"' not in line:
                    continue
                try:
                    entry = json.loads(line)
                    if parse_iso(entry["timestamp"]) < since:
                        continue
                except (ValueError, KeyError):
                    continue
                for fp, n in claude_entry_lines(entry):
                    tally.add("claude", fp, n)


# --- Antigravity ---------------------------------------------------------------

def _varint(b: bytes, i: int) -> tuple[int, int]:
    v = s = 0
    while True:
        c = b[i]
        i += 1
        v |= (c & 0x7F) << s
        s += 7
        if c < 0x80:
            return v, i


def pb_fields(b: bytes):
    """Minimal protobuf wire-format reader: yields (field_number, value)."""
    i = 0
    while i < len(b):
        key, i = _varint(b, i)
        num, wire = key >> 3, key & 7
        if wire == 0:
            v, i = _varint(b, i)
        elif wire == 2:
            n, i = _varint(b, i)
            v, i = b[i:i + n], i + n
        elif wire == 1:
            v, i = b[i:i + 8], i + 8
        elif wire == 5:
            v, i = b[i:i + 4], i + 4
        else:
            raise ValueError(f"unsupported wire type {wire}")
        yield num, v


def pb_get(b, *path):
    for p in path:
        if not isinstance(b, bytes):
            return None
        b = next((v for f, v in pb_fields(b) if f == p), None)
        if b is None:
            return None
    return b


def agy_call_lines(name: str, a: dict) -> tuple[str, int] | None:
    if name == "write_to_file":
        return a.get("TargetFile", ""), len(a.get("CodeContent", "").splitlines())
    if name == "write_file":
        return a.get("Path", ""), len(a.get("Content", "").splitlines())
    if name == "replace_file_content":
        return a.get("TargetFile", ""), added_lines(a.get("TargetContent", ""), a.get("ReplacementContent", ""))
    if name == "multi_replace_file_content":
        chunks = a.get("ReplacementChunks") or []
        if isinstance(chunks, str):
            chunks = json.loads(chunks)
        n = sum(added_lines(c.get("TargetContent", ""), c.get("ReplacementContent", "")) for c in chunks)
        return a.get("TargetFile", ""), n
    if name == "edit_file":
        return a.get("Path", ""), added_lines(a.get("Target", ""), a.get("Replacement", ""))
    return None


def scan_agy(since: float, tally: Tally, home: Path = HOME) -> None:
    for db in home.glob(AGY_GLOB):
        try:
            if db.stat().st_mtime < since:
                continue
            con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            rows = con.execute(
                "select step_payload from steps where status = ? and step_payload is not null", (AGY_DONE,)
            ).fetchall()
            con.close()
        except sqlite3.Error:
            continue
        for (payload,) in rows:
            try:
                ts = pb_get(payload, 5, 1, 1)
                name = pb_get(payload, 5, 4, 2)
                if not isinstance(ts, int) or ts < since or not name:
                    continue
                hit = agy_call_lines(name.decode(), json.loads(pb_get(payload, 5, 4, 3) or b"{}"))
            except (ValueError, IndexError, UnicodeDecodeError):
                continue
            if hit:
                tally.add("antigravity", *hit)


# --- git (hand-coded) ------------------------------------------------------------

def git(repo: Path, *args: str) -> str:
    try:
        return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=20).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""


def parse_numstat(text: str, repo: Path) -> Counter:
    out = Counter()
    for line in text.splitlines():
        parts = line.split("\t")
        if len(parts) != 3 or not parts[0].isdigit():  # binary files show "-"
            continue
        path = parts[2]
        if " => " in path:  # rename: keep destination
            path = path.split(" => ")[-1].replace("}", "").replace("{", "")
        if counted(path):
            out[os.path.realpath(repo / path)] += int(parts[0])
    return out


def find_repos(roots: list[Path], max_depth: int = 4) -> list[Path]:
    repos = []
    for root in roots:
        if not root.is_dir():
            continue
        for dirpath, dirnames, _ in os.walk(root):
            depth = Path(dirpath).relative_to(root).parts
            if ".git" in dirnames:
                repos.append(Path(dirpath))
            dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in ("node_modules", ".venv", "venv")]
            if len(depth) >= max_depth:
                dirnames.clear()
    return repos


def scan_git(since: float, repos: list[Path]) -> tuple[Counter, Counter]:
    """Return (working, committed) added-line counts.

    working  = uncommitted + untracked changes. The AI edits that produced these lines
               (if any) are still inside the same window, so subtracting AI lines gives a
               clean hand-coded estimate.
    committed = lines added by commits in the window. These may have been AI-written in an
               earlier session (outside the window), so they are reported separately and
               NOT counted as hand-coded, to avoid mislabelling old AI work as human.
    """
    working, committed = Counter(), Counter()
    for repo in repos:
        committed += parse_numstat(git(repo, "log", f"--since=@{int(since)}", "--format=", "--numstat", "--no-merges"), repo)
        working += parse_numstat(git(repo, "diff", "HEAD", "--numstat"), repo)
        for f in git(repo, "ls-files", "--others", "--exclude-standard").splitlines():
            p = repo / f
            try:
                if counted(f) and p.stat().st_mtime >= since and p.stat().st_size < 2_000_000:
                    working[os.path.realpath(p)] += len(p.read_bytes().splitlines())
            except OSError:
                pass
    return working, committed


# --- report ----------------------------------------------------------------------

def compute(hours: float = 24, roots: list[Path] | None = None) -> dict:
    since = time.time() - hours * 3600
    ai = Tally()
    scan_claude(since, ai)
    scan_agy(since, ai)
    env_roots = os.environ.get("LAB_CODE_ROOTS")
    roots = roots or ([Path(p).expanduser() for p in env_roots.split(":")] if env_roots else DEFAULT_ROOTS)
    working, committed = scan_git(since, find_repos(roots))
    hand = sum(max(0, n - ai.by_file.get(f, 0)) for f, n in working.items())
    total = ai.total + hand
    return {
        "hours": hours,
        "vibe": ai.total,
        "hand": hand,
        "committed": sum(committed.values()),
        "vibe_pct": round(100 * ai.total / total) if total else 0,
        "by_source": dict(ai.by_source),
        "top_vibe_files": ai.by_file.most_common(5),
    }


def render_text(r: dict) -> str:
    src = ", ".join(f"{k} {v}" for k, v in sorted(r["by_source"].items())) or "none"
    lines = [
        f"Last {r['hours']:g}h",
        f"  󰚩 vibe-coded  {r['vibe']:>7}   ({src})",
        f"  ✍ hand-coded  {r['hand']:>7}   (uncommitted + untracked, minus AI)",
        f"  vibe share    {r['vibe_pct']:>6}%",
        f"   committed    {r['committed']:>6}   (in-window commits; mixed authorship, uncounted)",
    ]
    if r["top_vibe_files"]:
        lines.append("  top AI-edited files:")
        lines += [f"    {n:>6}  {f.replace(str(HOME), '~')}" for f, n in r["top_vibe_files"]]
    return "\n".join(lines)


def render_genmon(r: dict) -> str:
    tip = render_text(r).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (
        f"<txt><span foreground='#cba6f7'>󰚩 {r['vibe']}</span>"
        f"<span foreground='#6c7086'> · </span>"
        f"<span foreground='#89b4fa'>✍ {r['hand']}</span></txt>\n"
        f"<tool>{tip}</tool>\n"
        "<txtclick>xfce4-terminal --hold -x lab lines</txtclick>"
    )


def main(hours: float = 24, fmt: str = "text") -> int:
    import shutil
    synapse_bin = shutil.which("synapse") or os.path.expanduser("~/.local/bin/synapse")
    if os.path.isfile(synapse_bin) and os.access(synapse_bin, os.X_OK):
        try:
            res = subprocess.run([synapse_bin, "vibe", "-h", str(hours), "-f", fmt], check=True)
            return res.returncode
        except Exception:
            pass
    r = compute(hours)
    print(json.dumps(r, indent=2) if fmt == "json" else render_genmon(r) if fmt == "genmon" else render_text(r))
    return 0
