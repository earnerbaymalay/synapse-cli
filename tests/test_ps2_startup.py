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
    assert int(nb_frames) == 720

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

def test_monolith_top_visual_alignment():
    import sys
    if PS2_DIR not in sys.path:
        sys.path.insert(0, PS2_DIR)
    from render_ps2_video import init_scene_data, get_camera, project_pt
    towers, _ = init_scene_data()
    # Check that during rise and flight, multiple monolith tops cleanly reach and align near top of screen (0 <= sy <= 55)
    for t in [2.0, 3.0, 4.0, 5.0]:
        cam = get_camera(t)
        aligned = [
            tow for tow in towers
            if (p := project_pt(tow['x'], tow['h'] * (1.0 - (1.0 - max(0.0, min(1.0, (t - tow['delay']) / 2.6))) ** 3), tow['z'], cam))
            and 0 <= p[0] <= 1920 and 0 <= p[1] <= 55
        ]
        assert len(aligned) >= 3, f"Expected multiple towers aligning near top of screen at t={t}, got {len(aligned)}"

    # Also verify zero collisions along camera flight corridor
    for step in range(0, 720, 15):
        t = step / 60.0
        cam = get_camera(t)
        cx, cy, cz = cam[0], cam[1], cam[2]
        for tow in towers:
            assert not (abs(tow['x'] - cx) < (tow['w'] / 2 + 1.0) and abs(tow['z'] - cz) < (tow['d'] / 2 + 1.0)), \
                f"Camera collision detected at t={t:.2f} with tower at ({tow['x']:.1f}, {tow['z']:.1f})"

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

