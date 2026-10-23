"""
token_harvester.py — auto-save auth tokens & cookies seen by the proxy.

Captures, from every flow:
  - Request  Authorization headers (Bearer / Basic / anything)
  - Request  Cookie headers  + common API-key headers
  - Response Set-Cookie headers
  - Token-looking fields in JSON request/response bodies
    (access_token, id_token, refresh_token, token, jwt, session, api_key, ...)

Each hit is appended as one JSON line to:
    ~/captures/mitm/tokens_<timestamp>.jsonl
and a short line is logged. Duplicate (host, kind, name, value) hits are skipped
so the file doesn't fill with the same token on every request.

Run:
    mitmweb  -s ~/Desktop/AI\\ CLI\\ WORK/mitmproxy-tools/token_harvester.py
    mitmdump -s ~/Desktop/AI\\ CLI\\ WORK/mitmproxy-tools/token_harvester.py

Authorized testing only — your own devices, accounts, and lab.
"""

import json
import logging
import os
from datetime import datetime

from mitmproxy import http

# ---- config -----------------------------------------------------------------
# Only harvest from these hosts. Empty list = every host.
HOSTS: list[str] = []                       # e.g. ["api.target.com", "login.target.com"]
# Header names (lowercase) treated as credentials.
CRED_HEADERS = {"authorization", "cookie", "x-api-key", "x-auth-token",
                "x-access-token", "api-key", "x-csrf-token"}
# JSON keys (lowercase substring match) treated as tokens.
TOKEN_KEYS = ("access_token", "refresh_token", "id_token", "token", "jwt",
              "session", "sessionid", "sid", "auth", "api_key", "apikey",
              "secret", "password", "passwd")
SAVE_DIR = os.path.expanduser("~/captures/mitm")
# -----------------------------------------------------------------------------


def _match(host: str) -> bool:
    return not HOSTS or any(h in host for h in HOSTS)


def _walk_json(obj, out, path=""):
    """Recursively collect token-looking key/value pairs from parsed JSON."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            kp = f"{path}.{k}" if path else str(k)
            if isinstance(v, (dict, list)):
                _walk_json(v, out, kp)
            elif isinstance(v, (str, int)) and any(t in str(k).lower() for t in TOKEN_KEYS):
                sval = str(v)
                if sval and sval.lower() not in ("", "null", "false", "true"):
                    out.append((kp, sval))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _walk_json(v, out, f"{path}[{i}]")


class TokenHarvester:
    def __init__(self) -> None:
        os.makedirs(SAVE_DIR, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.path = os.path.join(SAVE_DIR, f"tokens_{stamp}.jsonl")
        self.seen: set[tuple] = set()
        self.count = 0

    def load(self, loader) -> None:
        logging.info(f"[tokens] harvesting to {self.path}")

    def _save(self, host: str, url: str, kind: str, name: str, value: str) -> None:
        key = (host, kind, name, value)
        if key in self.seen:
            return
        self.seen.add(key)
        rec = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "host": host, "url": url, "kind": kind, "name": name, "value": value,
        }
        with open(self.path, "a") as fh:
            fh.write(json.dumps(rec) + "\n")
        self.count += 1
        preview = value if len(value) <= 60 else value[:57] + "..."
        logging.info(f"[tokens] #{self.count} {host} {kind}:{name} = {preview}")

    def _scan_headers(self, headers, host, url, kind):
        for name, val in headers.items():
            if name.lower() in CRED_HEADERS and val:
                self._save(host, url, kind, name, val)

    def _scan_body(self, text, host, url, kind):
        if not text:
            return
        try:
            data = json.loads(text)
        except Exception:
            return
        hits: list[tuple] = []
        _walk_json(data, hits)
        for name, val in hits:
            self._save(host, url, f"{kind}-json", name, val)

    def request(self, flow: http.HTTPFlow) -> None:
        if not _match(flow.request.pretty_host):
            return
        host, url = flow.request.pretty_host, flow.request.pretty_url
        self._scan_headers(flow.request.headers, host, url, "req-header")
        if flow.request.content:
            self._scan_body(flow.request.get_text(strict=False), host, url, "req")

    def response(self, flow: http.HTTPFlow) -> None:
        if flow.response is None or not _match(flow.request.pretty_host):
            return
        host, url = flow.request.pretty_host, flow.request.pretty_url
        # Set-Cookie can appear multiple times
        for name, val in flow.response.headers.items():
            if name.lower() == "set-cookie" and val:
                self._save(host, url, "resp-set-cookie", "set-cookie", val)
        if flow.response.content:
            ctype = flow.response.headers.get("content-type", "")
            if "json" in ctype or "text" in ctype:
                self._scan_body(flow.response.get_text(strict=False), host, url, "resp")


addons = [TokenHarvester()]
