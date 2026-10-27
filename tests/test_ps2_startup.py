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

