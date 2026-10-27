import math
import os
import subprocess
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PS2_DIR = os.path.join(BASE_DIR, "ps2-startup")
VIDEO_PATH = os.path.join(PS2_DIR, "ps2_xfce_startup.mp4")
AUDIO_PATH = os.path.join(PS2_DIR, "ps2_startup.wav")
SCRIPT_PATH = os.path.join(PS2_DIR, "xfce-ps2-startup")

def test_video_exists_and_valid():
    assert os.path.exists(VIDEO_PATH), "Video file ps2_xfce_startup.mp4 must exist"
    assert os.path.getsize(VIDEO_PATH) > 1024 * 1024, "Video file size must be > 1MB"

    # Inspect with ffprobe
    res = subprocess.run([
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate,nb_frames,codec_name",
        "-of", "csv=p=0",
        VIDEO_PATH
    ], capture_output=True, text=True, check=True)
    
    parts = res.stdout.strip().split(",")
    codec, width, height, r_frame_rate, nb_frames = parts
    assert codec == "h264"
    assert int(width) == 1920
    assert int(height) == 1080
    assert r_frame_rate == "60/1"
    assert int(nb_frames) in (720, 804)

def test_audio_soundtrack_valid():
    assert os.path.exists(AUDIO_PATH), "Audio file ps2_startup.wav must exist"
    res = subprocess.run([
        "ffprobe", "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=sample_rate,channels,codec_name",
        "-of", "csv=p=0",
        AUDIO_PATH
    ], capture_output=True, text=True, check=True)
    parts = res.stdout.strip().split(",")
    codec, sample_rate, channels = parts
    assert int(sample_rate) == 48000
    assert int(channels) == 2

    import wave
    import numpy as np
    with wave.open(AUDIO_PATH, "rb") as wf:
        n = wf.getnframes()
        data = wf.readframes(n)
        samples = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32767.0
        peak = np.max(np.abs(samples))
        assert 0.65 <= peak <= 0.75, f"Audio peak {peak:.3f} should be softly mastered around 0.70"

def _renderer():
    import sys
    if PS2_DIR not in sys.path:
        sys.path.insert(0, PS2_DIR)
    import render_ps2_video
    return render_ps2_video


def test_tower_field_in_view_and_camera_clear():
    r = _renderer()
    towers, _ = r.init_scene_data()
    assert len(towers) > 60
    # Most of the tower field is on screen through the orbit
    for t in (5.5, 7.0, 8.5):
        cam = r.get_camera(t)
        on_screen = [tw for tw in towers
                     if (p := r.project_pt(tw['x'], tw['h'], tw['z'], cam))
                     and 0 <= p[0] <= r.WIDTH and 0 <= p[1] <= r.HEIGHT]
        assert len(on_screen) > len(towers) * 0.6, f"t={t}: only {len(on_screen)} towers visible"
    # Camera never enters the grid
    for step in range(0, r.TOTAL_FRAMES, 10):
        cam = r.get_camera(step / r.FPS)
        assert math.hypot(cam[0], cam[2]) > (r.GRID / 2) * r.SPACING * 1.42


def test_camera_motion_is_smooth():
    r = _renderer()
    prev_v = None
    # Visible tower window (black before, whiteout after)
    for step in range(int(r.T_TOWER_START * r.FPS), int(r.T_WHITEOUT[1] * r.FPS)):
        a, b = r.get_camera((step - 1) / r.FPS), r.get_camera(step / r.FPS)
        v = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
        if prev_v is not None:
            jerk = math.dist(v, prev_v)
            assert jerk < 0.1, f"camera velocity jump {jerk:.3f} at frame {step}"
        prev_v = v


def test_final_frames_static_and_match_greeter():
    r = _renderer()
    last = r.render_single_frame(r.TOTAL_FRAMES - 1)
    settled = r.render_single_frame(int(r.T_STATIC * r.FPS) + 1)
    assert last == settled, "frames after T_STATIC must be identical for the SDDM hand-off"
    assert os.path.exists(os.path.join(PS2_DIR, "sddm-theme", "background.png"))


def test_sddm_theme_files():
    theme = os.path.join(PS2_DIR, "sddm-theme")
    meta = open(os.path.join(theme, "metadata.desktop")).read()
    assert "MainScript=Main.qml" in meta and "QtVersion=6" in meta
    conf = open(os.path.join(theme, "theme.conf")).read()
    assert "user=ebaymlay" in conf and "background=background.png" in conf
    qml = open(os.path.join(theme, "Main.qml")).read()
    assert "sddm.login(" in qml and "onLoginFailed" in qml


def test_boot_handoff_hardened():
    boot = open(os.path.join(PS2_DIR, "system", "ps2-system-boot")).read()
    for flag in ("--no-config", "--load-scripts=no", "--load-console=no",
                 "--no-input-default-bindings", "--keep-open=always"):
        assert flag in boot
    binds = open(os.path.join(PS2_DIR, "system", "boot-input.conf")).read()
    assert "run" not in binds.split("#")[0]
    assert "ESC    seek 100 absolute-percent+exact" in binds


def test_launcher_cli_status():
    assert os.path.exists(SCRIPT_PATH), "Launcher script must exist"
    assert os.access(SCRIPT_PATH, os.X_OK), "Launcher script must be executable"
    res = subprocess.run([SCRIPT_PATH, "--status"], capture_output=True, text=True, check=True)
    assert "PS2 XFCE 4.20 Startup Status Report" in res.stdout
    assert "READY" in res.stdout
    assert "1920x1080" in res.stdout

def test_launcher_cli_help():
    res = subprocess.run([SCRIPT_PATH, "--help"], capture_output=True, text=True, check=True)
    assert "PlayStation 2 // XFCE 4.20 Startup Sequence Suite" in res.stdout
    assert "--play" in res.stdout
    assert "--window" in res.stdout
    assert "--install-autostart" in res.stdout

def test_input_conf_valid():
    input_conf = os.path.join(PS2_DIR, "input.conf")
    assert os.path.exists(input_conf), "input.conf must exist"
    with open(input_conf, "r") as f:
        content = f.read()
    assert "ESC" in content and "quit" in content, "ESC must be bound to quit"
    assert "q" in content and "quit" in content, "q must be bound to quit"
    assert "SPACE" in content and "pause" in content, "SPACE must cycle pause"

def test_generate_audio_functional(tmp_path):
    test_wav = str(tmp_path / "functional_ps2_audio.wav")
    import sys
    if PS2_DIR not in sys.path:
        sys.path.insert(0, PS2_DIR)
    from generate_audio import generate_ps2_soundtrack
    generate_ps2_soundtrack(test_wav)
    assert os.path.exists(test_wav)
    assert os.path.getsize(test_wav) > 100_000

    # Also test CLI execution with system python3
    cli_wav = str(tmp_path / "cli_ps2_audio.wav")
    subprocess.run([sys.executable, os.path.join(PS2_DIR, "generate_audio.py"), cli_wav], check=True)
    assert os.path.exists(cli_wav)
    assert os.path.getsize(cli_wav) > 100_000

    res = subprocess.run([
        "ffprobe", "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=sample_rate,channels,codec_name",
        "-of", "csv=p=0",
        test_wav
    ], capture_output=True, text=True, check=True)
    codec, sample_rate, channels = res.stdout.strip().split(",")
    assert int(sample_rate) == 48000
    assert int(channels) == 2

def test_symlinks_resolution():
    symlinks = [
        os.path.expanduser("~/.local/bin/ps2-startup"),
        os.path.expanduser("~/omega-desktop/bin/ps2-startup"),
        os.path.join(BASE_DIR, "Scripts/ps2-startup"),
    ]
    for symlink in symlinks:
        if os.path.exists(symlink):
            res = subprocess.run([symlink, "--status"], capture_output=True, text=True, check=True)
            assert "PS2 XFCE 4.20 Startup Status Report" in res.stdout

