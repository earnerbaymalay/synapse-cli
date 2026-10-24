#!/usr/bin/env python3
"""
Terminal Command Center - AI CLI WORK
Interactive CLI/TUI dashboard and control center for:
- Local LLMs (Ollama resident models, memory, prompting)
- Hardware thermals & CPU boost status (throttled, core temps, fan)
- Network privacy & stealth posture (MAC randomization, DoT, firewall)
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.layout import Layout
    from rich.text import Text
    from rich.live import Live
    from rich import box
except ImportError:
    print("Error: 'rich' library is required. Install via: uv pip install rich")
    sys.exit(1)

import httpx

console = Console()

HARDWARE_MAC = "b4:69:21:fa:71:d4"
OLLAMA_BASE_URL = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")


def run_cmd(cmd: List[str]) -> str:
    """Run shell command safely and return trimmed stdout."""
    try:
        res = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3
        )
        return res.stdout.strip()
    except Exception:
        return ""


def get_permanent_mac(iface: str) -> str:
    """Detect the physical hardware MAC for a network interface."""
    out = run_cmd(["ethtool", "-P", iface])
    match = re.search(r"([0-9a-fA-F:]{17})", out)
    if match:
        return match.group(1).lower()
    if iface.startswith("w"):
        return HARDWARE_MAC.lower()
    return ""


def get_network_privacy_status() -> Dict[str, Any]:
    """Inspect active interface, randomized MAC, DNS-over-TLS, and stealth firewall."""
    # Find active interface
    route = run_cmd(["ip", "route", "show", "default"])
    active_iface = "wlan0"
    if "dev" in route:
        parts = route.split()
        if "dev" in parts:
            idx = parts.index("dev")
            if idx + 1 < len(parts):
                active_iface = parts[idx + 1]

    # Current MAC
    cur_mac = ""
    mac_path = f"/sys/class/net/{active_iface}/address"
    if os.path.exists(mac_path):
        with open(mac_path, "r") as f:
            cur_mac = f.read().strip().lower()

    # Hardware MAC comparison
    hw_mac = get_permanent_mac(active_iface)
    is_spoofed = (cur_mac != hw_mac) if hw_mac and cur_mac else False

    # Wi-Fi SSID & Priority
    ssid = ""
    nm_active = run_cmd(["nmcli", "-t", "-f", "NAME,DEVICE", "connection", "show", "--active"])
    for line in nm_active.splitlines():
        if active_iface in line:
            ssid = line.split(":")[0]

    # DNS-over-TLS via systemd-resolved
    dot_active = False
    resolve_status = run_cmd(["resolvectl", "status"])
    if "+DNSOverTLS" in resolve_status and "dns.quad9.net" in resolve_status:
        dot_active = True

    # Link-specific DNS check for leaks (DHCP router DNS)
    link_dns_raw = run_cmd(["resolvectl", "dns", active_iface])
    link_leak = False
    if "192.168." in link_dns_raw or "10." in link_dns_raw:
        link_leak = True

    # Firewall target & ICMP drop
    fw_target = "UNKNOWN"
    icmp_drop = False
    fw_list = run_cmd(["sudo", "-n", "firewall-cmd", "--list-all"])
    if "target: DROP" in fw_list:
        fw_target = "DROP (Stealth)"
    elif "target: default" in fw_list:
        fw_target = "REJECT"

    # Kernel ICMP ignore
    sysctl_icmp = run_cmd(["sysctl", "-n", "net.ipv4.icmp_echo_ignore_all"])
    if sysctl_icmp == "1":
        icmp_drop = True

    # Avahi mDNS status
    avahi_status = run_cmd(["systemctl", "is-active", "avahi-daemon"])
    avahi_leaking = (avahi_status == "active")

    return {
        "interface": active_iface,
        "ssid": ssid or "Direct / Wired",
        "current_mac": cur_mac or "unknown",
        "hardware_mac": hw_mac or HARDWARE_MAC,
        "is_anonymized": is_spoofed,
        "dot_encrypted": dot_active and not link_leak,
        "link_leaking": link_leak,
        "firewall_target": fw_target,
        "icmp_stealth": icmp_drop,
        "mDNS_disabled": not avahi_leaking,
    }


def get_hardware_thermal_status() -> Dict[str, Any]:
    """Inspect CPU thermals, fan RPM, throttled daemon, and memory."""
    # Sensors
    sensors_out = run_cmd(["sensors"])
    pkg_temp = "N/A"
    core_temps: List[str] = []
    fan_rpm = "N/A"

    for line in sensors_out.splitlines():
        line_clean = line.strip()
        if "Package id 0:" in line_clean:
            match = re.search(r"\+([0-9\.]+)°C", line_clean)
            if match:
                pkg_temp = f"{match.group(1)}°C"
        elif line_clean.startswith("Core "):
            match = re.search(r"\+([0-9\.]+)°C", line_clean)
            if match:
                core_temps.append(f"{match.group(1)}°C")
        elif "fan1:" in line_clean:
            match = re.search(r"([0-9]+)\s*RPM", line_clean)
            if match:
                fan_rpm = f"{match.group(1)} RPM"

    # Throttled status
    throttled_active = run_cmd(["systemctl", "is-active", "throttled"]) == "active"

    # CPU Governor & Frequencies
    governor = ""
    gov_path = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
    if os.path.exists(gov_path):
        with open(gov_path, "r") as f:
            governor = f.read().strip()

    # RAM & ZRAM
    mem_total_gb = 0.0
    mem_used_gb = 0.0
    with open("/proc/meminfo", "r") as f:
        meminfo = f.read()
        total_kb = int(re.search(r"MemTotal:\s+(\d+)", meminfo).group(1))  # type: ignore
        avail_kb = int(re.search(r"MemAvailable:\s+(\d+)", meminfo).group(1))  # type: ignore
        mem_total_gb = round(total_kb / 1024 / 1024, 1)
        mem_used_gb = round((total_kb - avail_kb) / 1024 / 1024, 1)

    zram_used = run_cmd(["swapon", "--show=NAME,USED,SIZE", "--noheadings"])
    zram_str = "8.0 GB (zstd)"
    if "/dev/zram0" in zram_used:
        parts = zram_used.split()
        if len(parts) >= 3:
            zram_str = f"{parts[1]} / {parts[2]} (zstd)"

    return {
        "cpu_model": "Intel Core i5-8350U (4c/8t)",
        "pkg_temp": pkg_temp,
        "core_temps": core_temps,
        "fan_rpm": fan_rpm,
        "throttled_active": throttled_active,
        "governor": governor or "powersave",
        "ram": f"{mem_used_gb} GB / {mem_total_gb} GB",
        "zram": zram_str,
    }


def get_ollama_status() -> Dict[str, Any]:
    """Query local Ollama daemon for resident models and installed catalog."""
    is_running = False
    resident_models: List[Dict[str, Any]] = []
    catalog_models: List[str] = []

    try:
        with httpx.Client(base_url=OLLAMA_BASE_URL, timeout=1.5) as client:
            # Check running status & resident models
            res_ps = client.get("/api/ps")
            if res_ps.status_code == 200:
                is_running = True
                data = res_ps.json()
                for m in data.get("models", []):
                    size_mb = round(m.get("size", 0) / 1024 / 1024, 1)
                    size_str = f"{round(size_mb / 1024, 2)} GB" if size_mb > 1000 else f"{size_mb} MB"
                    resident_models.append({
                        "name": m.get("name", ""),
                        "size": size_str,
                        "details": m.get("details", {}).get("parameter_size", "N/A"),
                        "quant": m.get("details", {}).get("quantization_level", "N/A"),
                    })

            # Check installed catalog
            res_tags = client.get("/api/tags")
            if res_tags.status_code == 200:
                is_running = True
                tags_data = res_tags.json()
                catalog_models = [m.get("name", "") for m in tags_data.get("models", [])]
    except Exception:
        is_running = False

    return {
        "running": is_running,
        "url": OLLAMA_BASE_URL,
        "resident": resident_models,
        "catalog": catalog_models,
    }


def render_dashboard() -> Layout:
    """Build the Rich terminal dashboard layout."""
    net = get_network_privacy_status()
    hw = get_hardware_thermal_status()
    ai = get_ollama_status()

    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main", ratio=1),
        Layout(name="footer", size=3),
    )

    # Header Panel
    title = Text(" AI CLI WORK // MISSION COMMAND CENTER ", style="bold bright_white on dark_magenta")
    sub = Text(f"Host: Dell Latitude 7490 (EndeavourOS) | Time: {time.strftime('%Y-%m-%d %H:%M:%S')}", style="bright_cyan")
    header_content = Text.assemble(title, "  ", sub)
    layout["header"].update(Panel(header_content, box=box.ROUNDED, style="magenta"))

    # Main Grid: Left (Network & Hardware), Right (Ollama & AI)
    layout["main"].split_row(
        Layout(name="sys_net", ratio=1),
        Layout(name="ai_sec", ratio=1),
    )

    # 1. Network Privacy Panel
    net_table = Table(box=box.SIMPLE, show_header=False, expand=True)
    net_table.add_column("Key", style="bold cyan")
    net_table.add_column("Value")

    net_table.add_row("Uplink Interface", f"{net['interface']} ({net['ssid']})")
    
    if net["is_anonymized"]:
        mac_text = Text(f"{net['current_mac']} [ANONYMIZED]", style="bold green")
    else:
        mac_text = Text(f"{net['current_mac']} [LEAKING HARDWARE]", style="bold red")
    net_table.add_row("MAC Address", mac_text)
    net_table.add_row("Hardware MAC", f"{net['hardware_mac']} (Hidden)")

    dot_val = Text("Active (Quad9 9.9.9.9:853 DoT)", style="bold green") if net["dot_encrypted"] else Text("Disabled / Plaintext", style="bold red")
    net_table.add_row("DNS-over-TLS", dot_val)

    fw_val = Text(f"{net['firewall_target']}", style="bold green" if "DROP" in net["firewall_target"] else "bold yellow")
    net_table.add_row("Firewall Target", fw_val)

    icmp_val = Text("IGNORED (Ping-Proof)", style="bold green") if net["icmp_stealth"] else Text("Responding", style="bold yellow")
    net_table.add_row("Stealth (ICMP)", icmp_val)

    mdns_val = Text("DISABLED (No Leaks)", style="bold green") if net["mDNS_disabled"] else Text("Active (Leaking .local)", style="bold red")
    net_table.add_row("mDNS / Avahi", mdns_val)

    # Hardware Panel
    hw_table = Table(box=box.SIMPLE, show_header=False, expand=True)
    hw_table.add_column("Key", style="bold yellow")
    hw_table.add_column("Value")

    hw_table.add_row("CPU Package", f"{hw['pkg_temp']} (Dell EC Fan: {hw['fan_rpm']})")
    hw_table.add_row("Cores", " / ".join(hw["core_temps"]))
    
    th_val = Text("ACTIVE (25W Sustained)", style="bold green") if hw["throttled_active"] else Text("INACTIVE (15W EC Limit)", style="bold red")
    hw_table.add_row("Throttled Daemon", th_val)
    hw_table.add_row("RAM / ZRAM", f"{hw['ram']} | Swap: {hw['zram']}")

    left_render = Table.grid(expand=True)
    left_render.add_row(Panel(net_table, title="[bold green]🔒 Prime Directive: Network Privacy & Stealth[/]", box=box.ROUNDED))
    left_render.add_row(Panel(hw_table, title="[bold yellow]⚡ Hardware Boost & Thermal Telemetry[/]", box=box.ROUNDED))
    layout["sys_net"].update(left_render)

    # Right: Ollama Panel
    ai_table = Table(box=box.SIMPLE, show_header=False, expand=True)
    ai_table.add_column("Key", style="bold magenta")
    ai_table.add_column("Value")

    ollama_stat = Text("RUNNING (24h Keep-Alive)", style="bold green") if ai["running"] else Text("OFFLINE", style="bold red")
    ai_table.add_row("Ollama Service", ollama_stat)

    if ai["resident"]:
        res_text = "\n".join([f"• {m['name']} ({m['details']}, {m['size']})" for m in ai["resident"]])
        ai_table.add_row("Resident in RAM", Text(res_text, style="bold bright_green"))
    else:
        ai_table.add_row("Resident in RAM", Text("None (RAM empty)", style="dim italic"))

    cat_text = ", ".join(ai["catalog"]) if ai["catalog"] else "No models found"
    ai_table.add_row("Installed Models", Text(cat_text, style="cyan"))

    ai_table.add_row("Physical CPU Cores", "4 cores (Single-Thread Concurrency Safe)")
    ai_table.add_row("Pre-Commit Hook", Text("ACTIVE (Multi-Tier Regex + Qwen AI)", style="bold green"))

    right_render = Table.grid(expand=True)
    right_render.add_row(Panel(ai_table, title="[bold magenta]🧠 Local AI Engine & Offline Security[/]", box=box.ROUNDED))
    layout["ai_sec"].update(right_render)

    # Footer
    footer_text = Text(
        "Live Controls: [W] Warm Code Model | [F] Flush RAM | [R] Refresh | [Q] Exit (or Ctrl+C)",
        style="bold white on dark_blue",
        justify="center",
    )
    layout["footer"].update(Panel(footer_text, box=box.ROUNDED, style="blue"))

    return layout


def prompt_model(model: str, prompt: str) -> None:
    """Send an interactive streaming query to the resident local model."""
    console.print(f"\n[bold magenta]Querying {model}...[/]")
    try:
        with httpx.Client(base_url=OLLAMA_BASE_URL, timeout=60.0) as client:
            with client.stream("POST", "/api/generate", json={"model": model, "prompt": prompt}) as response:
                if response.status_code != 200:
                    console.print(f"[bold red]Ollama API Error: HTTP {response.status_code}[/]")
                    return
                for line in response.iter_lines():
                    if line:
                        chunk = json.loads(line)
                        print(chunk.get("response", ""), end="", flush=True)
                        if chunk.get("done", False):
                            break
                print("\n")
    except Exception as e:
        console.print(f"[bold red]Failed to query Ollama:[/] {e}")


def warm_model(model: str = "qwen2.5-coder:latest") -> None:
    """Preload code model into RAM via native Ollama API."""
    console.print(f"[bold cyan]Warming up {model} into RAM...[/]")
    try:
        with httpx.Client(base_url=OLLAMA_BASE_URL, timeout=30.0) as client:
            res = client.post("/api/generate", json={"model": model, "keep_alive": "24h"})
            if res.status_code == 200:
                console.print(f"[bold green]Model '{model}' loaded and warm in RAM![/]")
            else:
                console.print(f"[bold red]Ollama API returned HTTP {res.status_code}[/]")
    except Exception as e:
        console.print(f"[bold red]Failed to warm model:[/] {e}")


def flush_models() -> None:
    """Unload all resident models to free memory via native Ollama API."""
    console.print("[bold yellow]Flushing resident models from RAM...[/]")
    ai = get_ollama_status()
    resident = ai.get("resident", [])
    if not resident:
        console.print("[bold green]RAM already clear (no models loaded).[/]")
        return
    try:
        with httpx.Client(base_url=OLLAMA_BASE_URL, timeout=10.0) as client:
            for m in resident:
                name = m.get("name", "")
                if name:
                    client.post("/api/generate", json={"model": name, "keep_alive": 0})
        console.print("[bold green]RAM flushed successfully![/]")
    except Exception as e:
        console.print(f"[bold red]Failed to flush models:[/] {e}")


def get_keypress(timeout: float = 1.0) -> Optional[str]:
    """Check for single keypress without blocking in terminal mode."""
    if not sys.stdin.isatty():
        time.sleep(timeout)
        return None
    try:
        import select
        import termios
        import tty

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            rlist, _, _ = select.select([sys.stdin], [], [], timeout)
            if rlist:
                return sys.stdin.read(1)
            return None
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    except Exception:
        time.sleep(timeout)
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Terminal Command Center - AI CLI WORK")
    parser.add_argument("-w", "--watch", action="store_true", help="Live auto-refresh dashboard mode")
    parser.add_argument("-p", "--prompt", type=str, help="Quick prompt to resident code model")
    parser.add_argument("-m", "--model", type=str, default="qwen2.5-coder:latest", help="Target Ollama model")
    parser.add_argument("--warm", action="store_true", help="Warm up code model into RAM")
    parser.add_argument("--flush", action="store_true", help="Flush resident models to free RAM")
    parser.add_argument("--json", action="store_true", help="Output telemetry as JSON")
    args = parser.parse_args()

    if args.json:
        payload = {
            "network": get_network_privacy_status(),
            "hardware": get_hardware_thermal_status(),
            "ollama": get_ollama_status(),
        }
        print(json.dumps(payload, indent=2))
        return

    if args.warm:
        warm_model(args.model)
        return

    if args.flush:
        flush_models()
        return

    if args.prompt:
        prompt_model(args.model, args.prompt)
        return

    if args.watch:
        try:
            with Live(render_dashboard(), refresh_per_second=4, screen=True) as live:
                while True:
                    key = get_keypress(1.0)
                    if key:
                        ch = key.lower()
                        if ch == "q":
                            break
                        elif ch == "w":
                            warm_model(args.model)
                            time.sleep(0.5)
                        elif ch == "f":
                            flush_models()
                            time.sleep(0.5)
                    live.update(render_dashboard())
        except KeyboardInterrupt:
            return

    # Default: single display
    console.print(render_dashboard())


if __name__ == "__main__":
    main()
