import subprocess
import shutil
import re
import wcwidth
import pytest

ANSI_RE = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')

def vis_len(s: str) -> int:
    clean = ANSI_RE.sub('', s)
    return wcwidth.wcswidth(clean)

def test_agy_widget_banner_alignment():
    """Verify that every line in agy-widget --banner has identical visual width."""
    res = subprocess.run(
        ["python3", "/home/ebaymlay/Desktop/AI CLI WORK/Scripts/agy-widget", "-b"],
        capture_output=True,
        text=True,
        check=True
    )
    lines = [l for l in res.stdout.splitlines() if l.strip()]
    assert len(lines) >= 6
    widths = [vis_len(l) for l in lines]
    first_width = widths[0]
    for idx, w in enumerate(widths):
        assert w == first_width, f"Line {idx+1} width {w} != first line width {first_width}"

def test_screensaver_rotation():
    """Verify screensaver alternates between #4 and #5."""
    res = subprocess.run(
        ["/home/ebaymlay/Desktop/AI CLI WORK/Scripts/screensaver", "--status"],
        capture_output=True,
        text=True,
        check=True
    )
    clean_out = ANSI_RE.sub('', res.stdout)
    assert "Swap Mode:            ACTIVE" in clean_out or "Startup Rotation:   ACTIVE" in clean_out
    assert "#4" in clean_out or "#5" in clean_out

def test_ps2_system_boot_status():
    """Verify PS2 system boot status reports active."""
    res = subprocess.run(
        ["/home/ebaymlay/Desktop/AI CLI WORK/ps2-startup/xfce-ps2-startup", "--status"],
        capture_output=True,
        text=True,
        check=True
    )
    clean_out = ANSI_RE.sub('', res.stdout)
    assert "System Boot Splash: ACTIVE" in clean_out
    assert "Master Video:       READY" in clean_out
