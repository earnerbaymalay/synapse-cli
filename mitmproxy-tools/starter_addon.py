"""
Starter mitmproxy addon — lab template for mitmproxy 12.x.

Run it:
    mitmweb   -s ~/Desktop/AI\\ CLI\\ WORK/mitmproxy-tools/starter_addon.py   # browser UI
    mitmdump  -s ~/Desktop/AI\\ CLI\\ WORK/mitmproxy-tools/starter_addon.py   # headless/logging
    mitmproxy -s ~/Desktop/AI\\ CLI\\ WORK/mitmproxy-tools/starter_addon.py   # TUI

What it does out of the box:
  - logs every request (method + URL) and response (status + size)
  - prints POST/PUT/PATCH request bodies (truncated)
  - saves flows whose host matches HOSTS_OF_INTEREST to a .mitm file you can reload

Optional tweaks (commented below): inject/rewrite a header, block a host,
rewrite response text. Uncomment what you need.

Authorized testing only — your own devices, accounts, and lab.
"""

import logging
import os
from datetime import datetime

from mitmproxy import http, ctx

# ---- config knobs -----------------------------------------------------------
# Only bodies/flows for these hosts get extra attention. Empty list = all hosts.
HOSTS_OF_INTEREST: list[str] = []          # e.g. ["api.example.com", "login.site.com"]
MAX_BODY = 2000                             # chars of body to log
SAVE_DIR = os.path.expanduser("~/captures/mitm")
# -----------------------------------------------------------------------------


def _interesting(host: str) -> bool:
    return not HOSTS_OF_INTEREST or any(h in host for h in HOSTS_OF_INTEREST)


class LabAddon:
    def __init__(self) -> None:
        os.makedirs(SAVE_DIR, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.save_path = os.path.join(SAVE_DIR, f"flows_{stamp}.mitm")

    def load(self, loader) -> None:
        logging.info(f"[lab] addon loaded — saving flows of interest to {self.save_path}")

    def request(self, flow: http.HTTPFlow) -> None:
        req = flow.request
        logging.info(f"→ {req.method} {req.pretty_url}")

        if req.method in ("POST", "PUT", "PATCH") and req.content and _interesting(req.pretty_host):
            body = req.get_text(strict=False) or ""
            logging.info(f"   body[{len(body)}]: {body[:MAX_BODY]}")

        # --- OPTIONAL: inject a header into every outgoing request ---
        # req.headers["X-Lab"] = "mitmproxy"

        # --- OPTIONAL: block a host (return a canned 403) ---
        # if "ads.example.com" in req.pretty_host:
        #     flow.response = http.Response.make(403, b"blocked by lab addon")

    def response(self, flow: http.HTTPFlow) -> None:
        resp = flow.response
        if resp is None:
            return
        size = len(resp.content) if resp.content else 0
        logging.info(f"← {flow.request.method} {flow.request.pretty_url} "
                     f"[{resp.status_code}] {size}B")

        # --- OPTIONAL: rewrite response text (e.g. swap a string) ---
        # if "text" in resp.headers.get("content-type", ""):
        #     txt = resp.get_text(strict=False) or ""
        #     resp.set_text(txt.replace("foo", "bar"))

        # save flows we care about for later replay/analysis
        if _interesting(flow.request.pretty_host):
            with open(self.save_path, "ab") as fh:
                from mitmproxy.io import FlowWriter
                FlowWriter(fh).add(flow)


addons = [LabAddon()]
