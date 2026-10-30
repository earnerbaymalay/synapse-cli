#!/bin/bash
# Install the dns-lock NetworkManager dispatcher hook and lock all existing
# Wi-Fi / wired profiles to Quad9 DoT (no DHCP- or RA-supplied DNS).
# Run from a normal terminal: sudo ./install-dns-lock.sh
set -euo pipefail

if [ "$EUID" -ne 0 ]; then
    echo "Run with sudo." >&2
    exit 1
fi

here="$(cd "$(dirname "$0")" && pwd)"
install -o root -g root -m 755 "$here/10-dns-lock" /etc/NetworkManager/dispatcher.d/10-dns-lock
systemctl enable --now NetworkManager-dispatcher.service >/dev/null

while IFS=: read -r uuid type; do
    case "$type" in 802-11-wireless|802-3-ethernet) ;; *) continue ;; esac
    nmcli connection modify "$uuid" \
        ipv4.ignore-auto-dns yes ipv6.ignore-auto-dns yes connection.dns-over-tls yes
    echo "locked: $(nmcli -g connection.id connection show "$uuid")"
done < <(nmcli -t -f UUID,TYPE connection show)

# Apply to whatever is connected right now
while IFS=: read -r dev type state; do
    case "$type" in wifi|ethernet) ;; *) continue ;; esac
    [ "$state" = connected ] && nmcli device reapply "$dev" && echo "reapplied: $dev"
done < <(nmcli -t -f DEVICE,TYPE,STATE device)

echo
resolvectl status | grep -E '^(Global|Link)|DNS Servers|DNSOverTLS'
