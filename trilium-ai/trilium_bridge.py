#!/usr/bin/env python3
"""
trilium_bridge.py - a small, dependency-light client for TriliumNext's ETAPI.

Uses only the Python 3 standard library (urllib + json). Talks to the ETAPI
REST API exposed by TriliumNext at <TRILIUM_URL>/etapi.

Configuration (in order of precedence):
  1. Environment variables TRILIUM_ETAPI_TOKEN and TRILIUM_URL
  2. The file ../.trilium-env relative to this script, or the path in
     $TRILIUM_ENV_FILE (simple KEY=VALUE lines)

Subcommands:
  search  <query>              Search notes, print "<noteId>  <title>"
  get     <noteId>             Print a note's content to stdout
  create  <title>              Create a note (content via --content or stdin)
  append  <noteId>             Append text to a note (content via --content or stdin)
  info                         Print ETAPI app-info (handy connectivity test)

Examples:
  export TRILIUM_ETAPI_TOKEN=... ; ./trilium_bridge.py search "project ideas"
  ./trilium_bridge.py get abc123
  echo "hello" | ./trilium_bridge.py create "My note"
  ./trilium_bridge.py create "My note" --content "hello" --parent root
  echo "more text" | ./trilium_bridge.py append abc123
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_URL = "http://localhost:8080"


def _load_env_file(path):
    """Parse a simple KEY=VALUE file into a dict. Missing file -> {}."""
    values = {}
    if not path or not os.path.isfile(path):
        return values
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key:
                    values[key] = val
    except OSError:
        pass
    return values


def _config():
    """Resolve (base_url, token). Exit with guidance if no token."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    env_file = os.environ.get(
        "TRILIUM_ENV_FILE", os.path.join(script_dir, os.pardir, ".trilium-env")
    )
    file_vals = _load_env_file(env_file)

    token = os.environ.get("TRILIUM_ETAPI_TOKEN") or file_vals.get(
        "TRILIUM_ETAPI_TOKEN", ""
    )
    base_url = (
        os.environ.get("TRILIUM_URL")
        or file_vals.get("TRILIUM_URL")
        or DEFAULT_URL
    ).rstrip("/")

    if not token:
        sys.stderr.write(
            "ERROR: No ETAPI token found.\n"
            "  Set TRILIUM_ETAPI_TOKEN in the environment, or put it in\n"
            "  %s\n\n"
            "  Generate a token in TriliumNext:\n"
            "    Options (menu / gear) -> ETAPI -> Create new ETAPI token\n"
            "  Then copy .trilium-env.template to .trilium-env, paste the token,\n"
            "  and run: chmod 600 .trilium-env\n" % os.path.abspath(env_file)
        )
        sys.exit(2)
    return base_url, token


def _request(method, path, token, data=None, content_type="application/json"):
    """Perform an ETAPI HTTP request; return (status, body_bytes)."""
    base_url, _ = (None, None)
    url = path if path.startswith("http") else _request.base_url + path
    headers = {"Authorization": token}
    body = None
    if data is not None:
        if content_type == "application/json":
            body = json.dumps(data).encode("utf-8")
        else:
            body = data if isinstance(data, bytes) else str(data).encode("utf-8")
        headers["Content-Type"] = content_type
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.getcode(), resp.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        sys.stderr.write(
            "ERROR: %s %s -> HTTP %s\n%s\n" % (method, url, exc.code, detail)
        )
        sys.exit(1)
    except urllib.error.URLError as exc:
        sys.stderr.write(
            "ERROR: cannot reach Trilium at %s (%s)\n"
            "  Is TriliumNext running and is ETAPI enabled?\n" % (url, exc.reason)
        )
        sys.exit(1)


def cmd_info(args, base_url, token):
    _request.base_url = base_url + "/etapi"
    status, body = _request("GET", "/app-info", token)
    print(body.decode("utf-8", "replace"))


def cmd_search(args, base_url, token):
    _request.base_url = base_url + "/etapi"
    query = urllib.parse.urlencode({"search": args.query})
    status, body = _request("GET", "/notes?" + query, token)
    payload = json.loads(body.decode("utf-8", "replace"))
    results = payload.get("results", [])
    if not results:
        print("(no matching notes)")
        return
    for note in results:
        print("%s\t%s" % (note.get("noteId", "?"), note.get("title", "")))


def cmd_get(args, base_url, token):
    _request.base_url = base_url + "/etapi"
    status, body = _request("GET", "/notes/%s/content" % args.note_id, token)
    sys.stdout.write(body.decode("utf-8", "replace"))
    if not body.endswith(b"\n"):
        sys.stdout.write("\n")


def _read_content(args):
    if args.content is not None:
        return args.content
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return ""


def cmd_create(args, base_url, token):
    _request.base_url = base_url + "/etapi"
    content = _read_content(args)
    payload = {
        "parentNoteId": args.parent,
        "title": args.title,
        "type": args.type,
        "content": content,
    }
    status, body = _request("POST", "/create-note", token, data=payload)
    result = json.loads(body.decode("utf-8", "replace"))
    note = result.get("note", {})
    note_id = note.get("noteId", "?")
    print("Created note %s: %s" % (note_id, note.get("title", args.title)))


def cmd_append(args, base_url, token):
    _request.base_url = base_url + "/etapi"
    addition = _read_content(args)
    # Fetch existing content, concatenate, then PUT it back.
    status, body = _request("GET", "/notes/%s/content" % args.note_id, token)
    existing = body.decode("utf-8", "replace")
    sep = "" if existing.endswith("\n") or not existing else "\n"
    new_content = existing + sep + addition
    _request(
        "PUT",
        "/notes/%s/content" % args.note_id,
        token,
        data=new_content,
        content_type="text/html",
    )
    print("Appended %d chars to note %s" % (len(addition), args.note_id))


def build_parser():
    parser = argparse.ArgumentParser(description="TriliumNext ETAPI bridge")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("search", help="search notes")
    p.add_argument("query")
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("get", help="print a note's content")
    p.add_argument("note_id")
    p.set_defaults(func=cmd_get)

    p = sub.add_parser("create", help="create a note")
    p.add_argument("title")
    p.add_argument("--content", default=None, help="content (else read stdin)")
    p.add_argument("--parent", default="root", help="parent noteId (default root)")
    p.add_argument("--type", default="text", help="note type (default text)")
    p.set_defaults(func=cmd_create)

    p = sub.add_parser("append", help="append to a note")
    p.add_argument("note_id")
    p.add_argument("--content", default=None, help="content (else read stdin)")
    p.set_defaults(func=cmd_append)

    p = sub.add_parser("info", help="print ETAPI app-info")
    p.set_defaults(func=cmd_info)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    base_url, token = _config()
    args.func(args, base_url, token)


if __name__ == "__main__":
    main()
