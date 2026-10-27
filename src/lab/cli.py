"""`lab` — single entry point for the AI CLI WORK toolkit."""

from __future__ import annotations

import argparse
import os
import sys

from . import WORKSPACE, audit, lines

# subcommand -> (interpreter, script path relative to workspace, help)
WRAPPED = {
    "status": ("python", "Scripts/command_center.py", "Command center dashboard (Ollama, thermals, privacy)"),
    "pcap": ("python", "pentest-scope/ai-pcap-analyze.py", "AI-assisted pcap analysis"),
    "scan": ("bash", "pentest-scope/rf-scan.sh", "RF survey on wlan0"),
    "capture": ("bash", "pentest-scope/scoped-capture.sh", "Scope-filtered packet capture"),
    "scope": ("bash", "pentest-scope/build-scope-filter.sh", "Rebuild scope.bpf from scope-targets.txt"),
    "backup": ("bash", "Scripts/backup-system-configs.sh", "Back up system configs"),
}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="lab", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("audit", help="Audit privacy/stealth posture against the Prime Directive")
    a.add_argument("--format", choices=("text", "json", "genmon"), default="text")
    ln = sub.add_parser("lines", help="Count vibe-coded vs hand-coded lines in a rolling window")
    ln.add_argument("--hours", type=float, default=24)
    ln.add_argument("--format", choices=("text", "json", "genmon"), default="text")
    for name, (_, _, help_) in WRAPPED.items():
        s = sub.add_parser(name, help=help_, add_help=False)
        s.add_argument("args", nargs=argparse.REMAINDER)
    return p


def main(argv: list[str] | None = None) -> int:
    ns, extra = build_parser().parse_known_args(argv)
    if ns.cmd == "audit":
        return audit.main(ns.format)
    if ns.cmd == "lines":
        return lines.main(ns.hours, ns.format)
    interp, rel, _ = WRAPPED[ns.cmd]
    exe = sys.executable if interp == "python" else "bash"
    script = str(WORKSPACE / rel)
    os.execvp(exe, [exe, script, *extra, *ns.args])


if __name__ == "__main__":
    sys.exit(main())
