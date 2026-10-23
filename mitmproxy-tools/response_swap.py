"""
response_swap.py — rewrite content in responses from a target site.

For responses from TARGET_HOSTS, applies literal string swaps (SWAPS) and/or
regex swaps (REGEX_SWAPS) to text/html/js/json bodies. mitmproxy transparently
handles gzip/br decompression via get_text()/set_text(), so you edit plain text.

Logs how many substitutions were made per flow. Great for lab demos:
defacement, feature-flag flipping, swapping API values, injecting a banner, etc.

Run:
    mitmweb  -s ~/Desktop/AI\\ CLI\\ WORK/mitmproxy-tools/response_swap.py
    mitmdump -s ~/Desktop/AI\\ CLI\\ WORK/mitmproxy-tools/response_swap.py

Authorized testing only — your own devices and sites.
"""

import logging
import re

from mitmproxy import http

# ---- config -----------------------------------------------------------------
# Only rewrite responses from these hosts. Empty list = every host (careful!).
TARGET_HOSTS: list[str] = ["example.com"]        # e.g. ["app.target.local"]

# Literal find -> replace (applied first, in order).
SWAPS: dict[str, str] = {
    "Example Domain": "Owned by the Lab 🧪",
}

# Regex find -> replace (Python re; applied after literal swaps).
# Values may use backrefs like \1.
REGEX_SWAPS: dict[str, str] = {
    # r'("balance"\s*:\s*)\d+': r'\g<1>999999',
    # r'<title>.*?</title>': r'<title>MITM</title>',
}

# Optional: inject a visible banner at the top of HTML bodies (set to None to skip).
HTML_BANNER: str | None = '<div style="background:#c0392b;color:#fff;padding:6px;' \
                          'font:14px sans-serif;text-align:center;">⚠ MITM lab — content modified</div>'
# -----------------------------------------------------------------------------

_COMPILED = [(re.compile(p, re.S), r) for p, r in REGEX_SWAPS.items()]


def _match(host: str) -> bool:
    return not TARGET_HOSTS or any(h in host for h in TARGET_HOSTS)


class ResponseSwap:
    def load(self, loader) -> None:
        logging.info(f"[swap] active for hosts={TARGET_HOSTS or ['ALL']} "
                     f"({len(SWAPS)} literal, {len(_COMPILED)} regex)")

    def response(self, flow: http.HTTPFlow) -> None:
        resp = flow.response
        if resp is None or not resp.content:
            return
        if not _match(flow.request.pretty_host):
            return
        ctype = resp.headers.get("content-type", "")
        if not any(t in ctype for t in ("text", "html", "json", "javascript", "xml")):
            return

        text = resp.get_text(strict=False)
        if text is None:
            return
        original = text
        n = 0

        for find, repl in SWAPS.items():
            if find in text:
                n += text.count(find)
                text = text.replace(find, repl)

        for rx, repl in _COMPILED:
            text, c = rx.subn(repl, text)
            n += c

        if HTML_BANNER and "html" in ctype and "<body" in text.lower():
            text = re.sub(r"(<body[^>]*>)", r"\1" + HTML_BANNER, text,
                          count=1, flags=re.I)
            n += 1

        if text != original:
            resp.set_text(text)
            logging.info(f"[swap] {flow.request.pretty_url} — {n} change(s)")


addons = [ResponseSwap()]
