# PlayStation 2 // XFCE 4.20 Startup & Login

PlayStation 2 BIOS inspired boot sequence for **XFCE 4.20** on **EndeavourOS** (Dell Latitude 7490):
the animation plays before login and its final XFCE frame *becomes* the SDDM login screen.

## Boot flow

```
SDDM starts X -> Xsetup runs ps2-system-boot (once per boot)
  Act I   0.0-4.4s   light motes spiral in -> flare -> ENDEAVOUROS wordmark
  Act II  4.1-9.6s   translucent tower field, slow orbit, drifting orbs, rise into whiteout
  Act III 9.5-12s    whiteout dissolves into the XFCE 4.20 logo (static from 11.2s)
mpv holds the last frame (keep-open) -> Xsetup returns -> sddm-greeter starts on top
  ps2-xfce SDDM theme: same image + password box for ebaymlay -> XFCE session
```

- **Seamless hand-off**: `render_ps2_video.py` exports the final frame as `sddm-theme/background.png`
  (BT.709 encode, so the decoded frame matches within ~1 level). The login panel fades in over it.
- **Login cannot be bypassed**: it's the real SDDM greeter (PAM). The only ways past it are a correct
  password or the restart/shutdown buttons. The XFCE X11 session is pinned.
- **Skipping the animation**: ESC / Enter / Space / Q jump to the final frame. They don't quit, so the hand-off still happens.
- **Hardened**: mpv runs as root before login, so it starts with `--no-config`, no builtin or
  auto-loaded scripts (mpv's console can run commands), and no default key bindings.
- **Audio** (`generate_audio.py`, numpy only): reverse swell -> sub "whum" + glass bells at the flare
  -> low beating drone with distant FM plinks -> rising whoosh -> D-major add9 logo chord, all through
  a 4 s synthetic-IR convolution reverb.

## 🚀 Usage

The launcher `ps2-startup` is available in your PATH:

```bash
# Play fullscreen startup sequence (default)
ps2-startup

# Windowed preview mode (1280x720)
ps2-startup --window

# Interactive real-time WebGL/Canvas kiosk mode in Chromium
ps2-startup --web

# Check system boot & autostart status & video metrics
ps2-startup --status

# Install the full sequence: boot animation + PS2 XFCE SDDM login theme
ps2-startup --install-boot-sequence
ps2-startup --remove-boot-sequence

# Pieces individually
ps2-startup --install-greeter | --remove-greeter
ps2-startup --install-system-boot

# Remove system startup boot animation
ps2-startup --remove-system-boot

# Install as XFCE user session login autostart
ps2-startup --install-autostart

# Disable XFCE user session login autostart
ps2-startup --remove-autostart

# Rebuild / re-render video from source across 8 CPU threads
ps2-startup --rebuild
```

---

## 📂 Architecture & Files

| File | Description |
| :--- | :--- |
| `ps2_xfce_startup.mp4` | Master 1080p60 H.264/AAC video (12.0s, 720 frames, 8 MB). |
| `sddm-theme/` | Qt6 SDDM theme (`Main.qml`, generated `background.png` + `theme.conf`). Installed to `/usr/share/sddm/themes/ps2-xfce`. |
| `system/ps2-system-boot` | Xsetup hook: plays once per boot and holds the last frame for the greeter. |
| `system/eof-handoff.lua`, `system/boot-input.conf` | EOF signal and skip-to-end bindings for the boot mpv. |
| `xfce-ps2-startup` | Main CLI orchestrator with single-instance flock lock and mpv wrapper. |
| `input.conf` | Dedicated mpv keybindings (instant skip via ESC, ENTER, Q, or click). |
| `render_ps2_video.py` | Multi-core parallel renderer (utilizes 8 CPU threads via PyCairo & FFmpeg). |
| `generate_audio.py` | Procedural PS2 boot sound synthesizer (sub-bass, chord, swoosh, chimes, reverb). |
| `ps2_engine.js` | Pure mathematical 3D perspective projection engine on 2D HTML5 canvas. |
| `index.html` | Real-time interactive browser/kiosk edition with keyboard controls. |
| `~/.config/autostart/ps2-xfce-startup.desktop` | XFCE autostart service entry. |
