# PlayStation 2 // XFCE 4.20 Startup Animation Suite

Custom engineered PlayStation 2 BIOS inspired animated boot sequence tailored specifically for **XFCE 4.20** on **EndeavourOS Arch Linux** (Dell Latitude 7490).

---

## 🎮 Features

- **Iconic PS2 BIOS Visuals**:
  - Deep oceanic misty twilight void with atmospheric depth fog.
  - 110 crystalline monolithic save towers rising from the void with glowing cyan wireframe edge bevels and illuminated tops.
  - 360 luminous energy orbs and stardust motes floating, orbiting, and streaking in 3D.
  - Cinematic camera choreography: slow low-angle atmospheric glide transitioning into a dramatic banking curve through the monolith canyon.
  - Blinding celestial supernova whiteout flash.
- **PS2-Style XFCE 4.20 Typography**:
  - Central 3D crystal hexagon monolith prism with glowing cyan core.
  - Iconic "XFCE" bold metallic gradient typography (White -> Sky Blue -> Royal Blue) with crisp bevel outline and superscript "4.20" badge.
  - Diagonal light sheen traversing across the letters.
  - Classic Sony PS2 spaced subtitle: `D E S K T O P   E N V I R O N M E N T`.
  - Telemetry HUD: `BIOS 2.20 // KABY LAKE-R`, `SYSTEM MEMORY: 24 GB DUAL-CH`, `ENDEAVOUROS // ARCH LINUX`, `DISPLAY: eDP-1 1080p 60Hz`.
  - Hardware status pill: `[ ● SYSTEM READY | VA-API ACCELERATED | PIPEWIRE 1.6 ]`.
- **Iconic Audio Recreation**:
  - Synthesized 48kHz 24-bit stereo soundtrack recreated via Python (`numpy` / `scipy`):
    - 48 Hz oceanic sub-bass foundation
    - D-minor ethereal suspended organ / synth pad cluster with stereo chorus
    - Swept-filter resonant wind swoosh during monolith canyon flight
    - High-frequency celestial crystal bell chimes (E6, B6, E7, G#7, B7)
    - Cavernous cathedral reverberation network
- **Hardware VA-API Acceleration**:
  - Plays fullscreen instantly via `mpv` with Intel UHD Graphics 620 VA-API hardware decoding (`vaapi[nv12]`) and PipeWire audio.
  - Zero dropped frames, exact 60.00 FPS (720 frames at 1920x1080).
- **Interactive Desktop Skipping**:
  - Press `ESC`, `Q`, `Space`, `Enter`, or click anywhere with the mouse to immediately dismiss the video and reveal the loaded XFCE desktop.
  - Custom `input.conf` bindings ensure instant skip behavior in mpv without getting trapped in windowed mode.

---

## 🚀 Usage

The launcher `ps2-startup` is available in your PATH:

```bash
# Play fullscreen startup sequence (default)
ps2-startup

# Windowed preview mode (1280x720)
ps2-startup --window

# Interactive real-time WebGL/Canvas kiosk mode in Chromium
ps2-startup --web

# Check autostart status & video metrics
ps2-startup --status

# Install as XFCE session login autostart
ps2-startup --install-autostart

# Disable XFCE session login autostart
ps2-startup --remove-autostart

# Rebuild / re-render video from source across 8 CPU threads
ps2-startup --rebuild
```

---

## 📂 Architecture & Files

| File | Description |
| :--- | :--- |
| `ps2_xfce_startup.mp4` | Master 1080p60 H.264/AAC video (12.0s, 720 frames, 8 MB). |
| `xfce-ps2-startup` | Main CLI orchestrator with single-instance flock lock and mpv wrapper. |
| `input.conf` | Dedicated mpv keybindings (instant skip via ESC, ENTER, Q, or click). |
| `render_ps2_video.py` | Multi-core parallel renderer (utilizes 8 CPU threads via PyCairo & FFmpeg). |
| `generate_audio.py` | Procedural PS2 boot sound synthesizer (sub-bass, chord, swoosh, chimes, reverb). |
| `ps2_engine.js` | Pure mathematical 3D perspective projection engine on 2D HTML5 canvas. |
| `index.html` | Real-time interactive browser/kiosk edition with keyboard controls. |
| `~/.config/autostart/ps2-xfce-startup.desktop` | XFCE autostart service entry. |
