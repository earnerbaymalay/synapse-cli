"""Privacy/stealth posture audit: checks the CLAUDE.md Prime Directive against live state.

Each check is split into a pure parser (unit-tested) and a collector that runs commands.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

HARDWARE_MAC = "b4:69:21:fa:71:d4"
QUAD9 = ("9.9.9.9", "149.112.112.112")
SYNCTHING_CONFIG = Path.home() / ".local/state/syncthing/config.xml"

PASS, WARN, FAIL = "pass", "warn", "fail"


@dataclass
class Check:
    name: str
    status: str
    detail: str


def run(cmd: list[str]) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""


# --- parsers -----------------------------------------------------------------

def parse_nm_config(text: str) -> Check:
    want = {
        "wifi.scan-rand-mac-address": "yes",
        "wifi.cloned-mac-address": "random",
        "ipv6.ip6-privacy": "2",
    }
    found = dict(re.findall(r"^([\w.-]+)=(\S+)", text, re.M))
    bad = [f"{k}={found.get(k, 'unset')}" for k, v in want.items() if found.get(k) != v]
    if bad:
        return Check("NM MAC/IPv6 randomization", FAIL, ", ".join(bad))
    return Check("NM MAC/IPv6 randomization", PASS, "scan+connection MAC random, ip6-privacy=2")


def parse_iface_macs(macs: dict[str, str]) -> Check:
    leaked = [i for i, m in macs.items() if m.lower() == HARDWARE_MAC]
    if leaked:
        return Check("Hardware MAC hidden", FAIL, f"hardware MAC exposed on {', '.join(leaked)}")
    return Check("Hardware MAC hidden", PASS, f"{len(macs)} wifi iface(s) not using hardware MAC")


def parse_resolved(text: str) -> Check:
    if "+DNSOverTLS" not in text:
        return Check("DNS-over-TLS (Quad9)", FAIL, "DNSOverTLS not enabled")
    def rogue(pattern: str) -> list[str]:
        flat = " ".join(re.findall(pattern, text, re.M))
        return sorted({ip for ip in re.findall(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", flat) if ip not in QUAD9})

    active = rogue(r"^\s*(?:Current )?DNS Servers?:\s*(.+)")
    if active:
        return Check("DNS-over-TLS (Quad9)", FAIL, f"non-Quad9 resolvers active: {', '.join(active)}")
    fallback = rogue(r"^\s*Fallback DNS Servers:\s*(.+)")
    if fallback:
        return Check("DNS-over-TLS (Quad9)", WARN, f"non-Quad9 fallback resolvers: {', '.join(fallback)}")
    return Check("DNS-over-TLS (Quad9)", PASS, "DoT on, Quad9 only")


def parse_firewall(zone_info: str, policies: str) -> list[Check]:
    checks = []
    if re.search(r"^\s*target:\s*DROP", zone_info, re.M):
        checks.append(Check("Firewall default DROP", PASS, "default zone target DROP"))
    elif zone_info:
        checks.append(Check("Firewall default DROP", FAIL, "default zone target is not DROP"))
    else:
        checks.append(Check("Firewall default DROP", WARN, "could not read firewalld (needs sudo -n)"))
    if "stealth-egress" in policies.split():
        checks.append(Check("Discovery multicast egress blocked", PASS, "stealth-egress policy active"))
    elif policies:
        checks.append(Check("Discovery multicast egress blocked", FAIL, "stealth-egress policy missing"))
    return checks


def parse_icmp(value: str) -> Check:
    if value.strip() == "1":
        return Check("ICMP echo ignored", PASS, "icmp_echo_ignore_all=1")
    return Check("ICMP echo ignored", FAIL, f"icmp_echo_ignore_all={value.strip() or 'unknown'}")


def parse_avahi(state: str) -> Check:
    if state.strip() == "active":
        return Check("Avahi mDNS disabled", FAIL, "avahi-daemon is active")
    return Check("Avahi mDNS disabled", PASS, f"avahi-daemon {state.strip() or 'absent'}")


def parse_listeners(ss_out: str) -> Check:
    """Flag sockets bound to non-loopback addresses (inbound is dropped, but it's still exposure)."""
    exposed = set()
    for line in ss_out.splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        local = parts[4]
        addr = local.rsplit(":", 1)[0].strip("[]")
        if addr.startswith(("127.", "::1")) or "%lo" in addr:
            continue
        if local.endswith((":68", ":546")):  # DHCP/DHCPv6 client sockets are required
            continue
        proc = re.search(r'\(\("([^"]+)"', line)
        exposed.add(f"{proc.group(1) if proc else '?'}@{local}")
    if exposed:
        return Check("No public listeners", WARN, "; ".join(sorted(exposed)))
    return Check("No public listeners", PASS, "all listeners loopback-only")


def parse_syncthing(xml: str) -> Check:
    if not xml:
        return Check("Syncthing discovery off", PASS, "syncthing not configured")
    on = [t for t in ("globalAnnounceEnabled", "localAnnounceEnabled", "relaysEnabled", "natEnabled")
          if re.search(rf"<{t}>true</{t}>", xml)]
    if on:
        return Check("Syncthing discovery off", FAIL, f"enabled: {', '.join(on)}")
    return Check("Syncthing discovery off", PASS, "announce/relay/NAT disabled")


# --- collector ---------------------------------------------------------------

def wifi_macs() -> dict[str, str]:
    macs = {}
    for dev in Path("/sys/class/net").glob("w*"):
        try:
            macs[dev.name] = (dev / "address").read_text().strip()
        except OSError:
            pass
    return macs


def collect() -> list[Check]:
    checks = [
        parse_nm_config(run(["NetworkManager", "--print-config"])),
        parse_iface_macs(wifi_macs()),
        parse_resolved(run(["resolvectl", "status"])),
        *parse_firewall(
            run(["sudo", "-n", "firewall-cmd", "--list-all"]),
            run(["sudo", "-n", "firewall-cmd", "--get-policies"]),
        ),
        parse_icmp(run(["sysctl", "-n", "net.ipv4.icmp_echo_ignore_all"])),
        parse_avahi(run(["systemctl", "is-active", "avahi-daemon"])),
        parse_listeners(run(["ss", "-H", "-tulnp"])),
    ]
    try:
        xml = SYNCTHING_CONFIG.read_text()
    except OSError:
        xml = ""
    checks.append(parse_syncthing(xml))
    return checks


# --- output ------------------------------------------------------------------

ICON = {PASS: "✔", WARN: "▲", FAIL: "✘"}
COLOR = {PASS: "#a6e3a1", WARN: "#f9e2af", FAIL: "#f38ba8"}  # Catppuccin Mocha


def render_text(checks: list[Check]) -> str:
    ansi = {PASS: "\033[32m", WARN: "\033[33m", FAIL: "\033[31m"}
    lines = [f"{ansi[c.status]}{ICON[c.status]}\033[0m {c.name:<36} {c.detail}" for c in checks]
    return "\n".join(lines)


def render_genmon(checks: list[Check]) -> str:
    fails = sum(c.status == FAIL for c in checks)
    warns = sum(c.status == WARN for c in checks)
    worst = FAIL if fails else WARN if warns else PASS
    label = f"󰒃 {fails}✘" if fails else f"󰒃 {warns}▲" if warns else "󰒃"
    tip = "\n".join(f"{ICON[c.status]} {c.name}: {c.detail}" for c in checks)
    tip = tip.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (
        f"<txt><span foreground='{COLOR[worst]}'>{label}</span></txt>\n"
        f"<tool>Privacy audit\n{tip}</tool>\n"
        "<txtclick>xfce4-terminal --hold -x lab audit</txtclick>"
    )


def main(fmt: str = "text") -> int:
    checks = collect()
    if fmt == "json":
        print(json.dumps([asdict(c) for c in checks], indent=2))
    elif fmt == "genmon":
        print(render_genmon(checks))
    else:
        print(render_text(checks))
    return 1 if any(c.status == FAIL for c in checks) else 0
