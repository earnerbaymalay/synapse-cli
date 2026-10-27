# mitmproxy lab tools

Shared config lives in `~/.mitmproxy/config.yaml`:
- **proxy port 8081** (devices connect here — 8080 reserved)
- **web UI 127.0.0.1:8082** (mitmweb), auto-opens a browser

CA cert: `~/.mitmproxy/mitmproxy-ca-cert.pem` (install on targets for HTTPS; or browse `http://mitm.it` from a device already using the proxy).

## Run

```bash
# Browser UI (recommended) — proxy on :8081, UI opens at http://127.0.0.1:8082
mitmweb

# Browser UI + the starter addon (logging, body dumps, flow saving)
mitmweb -s ~/Desktop/AI\ CLI\ WORK/mitmproxy-tools/starter_addon.py

# Headless (no UI) — pure logging to the terminal / scripting
mitmdump -s ~/Desktop/AI\ CLI\ WORK/mitmproxy-tools/starter_addon.py

# Terminal UI
mitmproxy -s ~/Desktop/AI\ CLI\ WORK/mitmproxy-tools/starter_addon.py
```

## Point a target
Device Wi-Fi → manual proxy `192.168.1.246:8081` → browse `http://mitm.it` → install cert.

## Self-test from this box
```bash
curl --proxy 127.0.0.1:8081 http://example.com
curl --proxy 127.0.0.1:8081 --cacert ~/.mitmproxy/mitmproxy-ca-cert.pem https://example.com
```

## Starter addon
`starter_addon.py` (mitmproxy 12 API). Out of the box: logs each request/response,
prints POST/PUT/PATCH bodies, and saves flows of interest to `~/captures/mitm/flows_<ts>.mitm`.
Edit the knobs at the top (`HOSTS_OF_INTEREST`, `MAX_BODY`) and uncomment the optional
blocks to inject headers, block a host, or rewrite response text.

Reload a saved capture:
```bash
mitmweb -r ~/captures/mitm/flows_<timestamp>.mitm      # view past flows in the UI
mitmdump -nr ~/captures/mitm/flows_<timestamp>.mitm    # print them headless
```

## token_harvester.py
Auto-saves auth material to `~/captures/mitm/tokens_<ts>.jsonl` (one JSON object per line):
Authorization/Cookie/API-key request headers, Set-Cookie response headers, and
token-looking fields in JSON bodies (`access_token`, `jwt`, `session`, `api_key`, …).
De-duplicates. Scope it to a site by editing `HOSTS` at the top (empty = all hosts).
```bash
mitmweb -s ~/Desktop/AI\ CLI\ WORK/mitmproxy-tools/token_harvester.py
# review:  jq . ~/captures/mitm/tokens_*.jsonl   (or cat)
```

## response_swap.py
Rewrites responses from `TARGET_HOSTS`: literal `SWAPS`, regex `REGEX_SWAPS`, and an
optional injected HTML banner. Handles gzip/br automatically. Defaults ship with a demo
(`example.com`: swaps the title + adds a banner) — edit `TARGET_HOSTS`/`SWAPS` for your site.
```bash
mitmweb -s ~/Desktop/AI\ CLI\ WORK/mitmproxy-tools/response_swap.py
```

Authorized testing only — your own devices, accounts, and lab.
