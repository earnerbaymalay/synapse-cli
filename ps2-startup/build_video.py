#!/usr/bin/env python3
"""
PS2-Inspired XFCE Startup Video Builder
Captures 1080p60 WebM from Chromium headless, synthesizes studio-grade audio,
and encodes final high-definition H.264/AAC MP4 video with ffmpeg.
"""

import http.server
import os
import socketserver
import subprocess
import sys
import threading
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
PORT = 9995
CAPTURED_WEBM = os.path.join(SCRIPT_DIR, "raw_capture.webm")
AUDIO_WAV = os.path.join(SCRIPT_DIR, "ps2_startup.wav")
FINAL_MP4 = os.path.join(SCRIPT_DIR, "ps2_xfce_startup.mp4")

upload_event = threading.Event()

class CaptureHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=SCRIPT_DIR, **kwargs)

    def do_POST(self):
        if self.path == "/upload_video":
            content_length = int(self.headers.get("Content-Length", 0))
            data = self.rfile.read(content_length)
            with open(CAPTURED_WEBM, "wb") as f:
                f.write(data)
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")
            print(f"[+] Received raw video capture: {len(data)} bytes ({len(data) / (1024*1024):.2f} MB)")
            upload_event.set()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

def build():
    print("=" * 65)
    print("  PS2 XFCE 4.20 STARTUP VIDEO GENERATOR")
    print("=" * 65)

    # 1. Synthesize audio soundtrack
    if not os.path.exists(AUDIO_WAV):
        print("[*] Generating PlayStation 2 boot audio soundtrack...")
        try:
            from generate_audio import generate_ps2_soundtrack
            generate_ps2_soundtrack(AUDIO_WAV)
        except Exception:
            gen_script = os.path.join(SCRIPT_DIR, "generate_audio.py")
            subprocess.run([sys.executable, gen_script, AUDIO_WAV], check=True)
    else:
        print(f"[✓] Audio track ready: {AUDIO_WAV}")

    # 2. Start local HTTP server
    print(f"[*] Starting local HTTP server on port {PORT}...")
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("127.0.0.1", PORT), CaptureHandler)
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()

    # 3. Launch Headless Chromium
    print("[*] Launching Chromium (Headless 1080p60 Canvas MediaRecorder)...")
    url = f"http://127.0.0.1:{PORT}/render_page.html?record=1"
    chrome_cmd = [
        "chromium",
        "--headless=new",
        "--window-size=1920,1080",
        "--autoplay-policy=no-user-gesture-required",
        url
    ]

    chrome_proc = subprocess.Popen(chrome_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 4. Wait for WebM capture upload
    print("[*] Capturing 12.0s @ 60 FPS animation...")
    success = upload_event.wait(timeout=60)
    
    # Cleanup browser & server
    chrome_proc.terminate()
    try:
        chrome_proc.wait(timeout=2)
    except Exception:
        chrome_proc.kill()
    httpd.shutdown()
    httpd.server_close()

    if not success or not os.path.exists(CAPTURED_WEBM) or os.path.getsize(CAPTURED_WEBM) == 0:
        print("[!] ERROR: Failed to capture video from Chromium.")
        sys.exit(1)

    print(f"[✓] Raw capture saved: {CAPTURED_WEBM}")

    # 5. Multiplex and transcode into final MP4 with ffmpeg
    print("[*] Encoding final MP4 with H.264 High Profile and 320k AAC audio...")
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-i", CAPTURED_WEBM,
        "-i", AUDIO_WAV,
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "17",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "320k",
        "-shortest",
        FINAL_MP4
    ]

    subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if os.path.exists(FINAL_MP4):
        size_mb = os.path.getsize(FINAL_MP4) / (1024 * 1024)
        print(f"[🎉] SUCCESS: Generated {FINAL_MP4} ({size_mb:.2f} MB)")
    else:
        print("[!] ERROR: ffmpeg failed to produce output MP4.")
        sys.exit(1)

if __name__ == "__main__":
    build()
