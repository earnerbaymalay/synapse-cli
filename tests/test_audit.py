from lab import audit
from lab.audit import FAIL, PASS, WARN
from lab.cli import build_parser


def test_nm_config_pass():
    text = "[x]\nwifi.scan-rand-mac-address=yes\nipv6.ip6-privacy=2\n[y]\nwifi.cloned-mac-address=random\n"
    assert audit.parse_nm_config(text).status == PASS


def test_nm_config_missing_cloned_mac():
    c = audit.parse_nm_config("wifi.scan-rand-mac-address=yes\nipv6.ip6-privacy=2\n")
    assert c.status == FAIL and "cloned-mac-address=unset" in c.detail


def test_hardware_mac_leak_case_insensitive():
    assert audit.parse_iface_macs({"wlan0": "B4:69:21:FA:71:D4"}).status == FAIL
    assert audit.parse_iface_macs({"wlan0": "3a:11:22:33:44:55"}).status == PASS


def test_resolved_flags_dhcp_dns_leak():
    text = "Protocols: +DNSOverTLS\nDNS Servers: 9.9.9.9#dns.quad9.net 192.168.1.1\n"
    c = audit.parse_resolved(text)
    assert c.status == FAIL and "192.168.1.1" in c.detail


def test_resolved_quad9_only():
    text = "Protocols: +DNSOverTLS\nCurrent DNS Server: 9.9.9.9#dns.quad9.net\nDNS Servers: 9.9.9.9 149.112.112.112\n"
    assert audit.parse_resolved(text).status == PASS


def test_resolved_non_quad9_fallback_is_warning():
    text = "Protocols: +DNSOverTLS\nDNS Servers: 9.9.9.9\nFallback DNS Servers: 1.1.1.1#cloudflare-dns.com\n"
    c = audit.parse_resolved(text)
    assert c.status == WARN and "1.1.1.1" in c.detail


def test_resolved_no_dot():
    assert audit.parse_resolved("Protocols: -DNSOverTLS\n").status == FAIL


def test_firewall():
    ok = audit.parse_firewall("public (active)\n  target: DROP\n", "stealth-egress gateway-lan-to-HOST")
    assert [c.status for c in ok] == [PASS, PASS]
    bad = audit.parse_firewall("public\n  target: default\n", "allow-host-ipv6")
    assert [c.status for c in bad] == [FAIL, FAIL]
    unreadable = audit.parse_firewall("", "")
    assert [c.status for c in unreadable] == [WARN]


def test_listeners_ignores_loopback():
    ss = (
        'tcp LISTEN 0 4096 127.0.0.1:8384 0.0.0.0:* users:(("syncthing",pid=1,fd=1))\n'
        "udp UNCONN 0 0 127.0.0.53%lo:53 0.0.0.0:*\n"
        "tcp LISTEN 0 4096 [::1]:631 [::]:*\n"
    )
    assert audit.parse_listeners(ss).status == PASS


def test_listeners_flags_public():
    ss = 'udp UNCONN 0 0 0.0.0.0:5353 0.0.0.0:* users:(("spotify",pid=2,fd=3))\n'
    c = audit.parse_listeners(ss)
    assert c.status == WARN and "spotify@0.0.0.0:5353" in c.detail


def test_syncthing():
    assert audit.parse_syncthing("<globalAnnounceEnabled>true</globalAnnounceEnabled>").status == FAIL
    off = "".join(f"<{t}>false</{t}>" for t in ("globalAnnounceEnabled", "localAnnounceEnabled", "relaysEnabled", "natEnabled"))
    assert audit.parse_syncthing(off).status == PASS


def test_icmp_and_avahi():
    assert audit.parse_icmp("1\n").status == PASS
    assert audit.parse_icmp("0").status == FAIL
    assert audit.parse_avahi("active\n").status == FAIL
    assert audit.parse_avahi("inactive\n").status == PASS


def test_genmon_escapes_and_reports_worst():
    out = audit.render_genmon([audit.Check("a<b", WARN, "x&y"), audit.Check("c", FAIL, "z")])
    assert "#f38ba8" in out and "a&lt;b" in out and "x&amp;y" in out


def test_cli_parses_wrapped_passthrough():
    ns, extra = build_parser().parse_known_args(["pcap", "file.pcap", "--model", "qwen"])
    assert ns.cmd == "pcap" and [*extra, *ns.args] == ["file.pcap", "--model", "qwen"]


def test_listeners_ignores_dhcp_clients():
    ss = "udp UNCONN 0 0 [fe80::1b2c:b90e:5fbb:13ff]%wlan0:546 [::]:*\nudp UNCONN 0 0 0.0.0.0%wlan0:68 0.0.0.0:*\n"
    assert audit.parse_listeners(ss).status == PASS
