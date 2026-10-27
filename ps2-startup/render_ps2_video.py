#!/usr/bin/env python3
"""
PS2-Inspired XFCE Startup Video Engine (High-Performance Parallel Renderer)
Synthesizes the iconic PlayStation 2 boot sequence:
- Oceanic atmospheric void & looming crystal monolith pillars
- Floating luminous energy orbs & high-speed camera bank
- Celestial supernova flash
- Iconic PlayStation 2 style XFCE 4.20 typography & metallic light sheen
- 100% deterministic 60.00 FPS (720 frames) across 8 CPU threads via Cairo & FFmpeg
"""

import math
import multiprocessing
import os
import subprocess
import sys
import time

try:
    import cairo
    import numpy as np
except ImportError:
    print("[!] Error: pycairo and numpy required. Run with uv run --with pycairo,numpy")
    sys.exit(1)

WIDTH = 1920
HEIGHT = 1080
FPS = 60
DURATION = 12.0
TOTAL_FRAMES = int(DURATION * FPS)  # 720 frames

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

AUDIO_WAV = os.path.join(SCRIPT_DIR, "ps2_startup.wav")
FINAL_MP4 = os.path.join(SCRIPT_DIR, "ps2_xfce_startup.mp4")

# -----------------------------------------------------------------------------
# Procedural Scene Data (Pre-computed & shared across workers)
# -----------------------------------------------------------------------------
def init_scene_data():
    # Deterministic pseudo-random sequence
    seed = 1337
    def rnd():
        nonlocal seed
        seed = (seed * 1664525 + 1013904223) % 4294967296
        return seed / 4294967296.0

    towers = []
    TOWER_COUNT = 115
    for i in range(TOWER_COUNT):
        side = 1.0 if rnd() > 0.5 else -1.0
        x = (18.0 + rnd() * 120.0) * side
        z = -rnd() * 640.0 + 40.0
        h = 25.0 + rnd() * 145.0
        w = 9.0 + rnd() * 12.0
        d = 9.0 + rnd() * 12.0
        phase = rnd() * math.pi * 2.0
        towers.append({
            'x': x, 'y': 0.0, 'z': z,
            'w': w, 'h': h, 'd': d,
            'phase': phase,
            'verts': [
                (-w/2, 0.0, -d/2), (w/2, 0.0, -d/2), (w/2, 0.0, d/2), (-w/2, 0.0, d/2),
                (-w/2, h, -d/2), (w/2, h, -d/2), (w/2, h, d/2), (-w/2, h, d/2)
            ]
        })

    orbs = []
    ORB_COUNT = 360
    palette = [
        (0.22, 0.74, 0.97),  # Sky Cyan (#38bdf8)
        (0.01, 0.52, 0.78),  # Ocean Blue (#0284c7)
        (0.75, 0.52, 0.99),  # Soft Mauve (#c084fc)
        (0.98, 0.98, 1.00),  # Starlight White (#f8fafc)
        (0.20, 0.83, 0.60),  # Emerald (#34d399)
    ]
    for i in range(ORB_COUNT):
        orbs.append({
            'x': (rnd() - 0.5) * 260.0,
            'y': rnd() * 120.0 - 10.0,
            'z': -rnd() * 600.0 + 40.0,
            'radius': 2.0 + rnd() * 3.5,
            'orbitSpeed': 0.6 + rnd() * 1.2,
            'orbitRadius': 8.0 + rnd() * 25.0,
            'orbitPhase': rnd() * math.pi * 2.0,
            'color': palette[int(rnd() * len(palette))]
        })

    return towers, orbs

SCENE_TOWERS, SCENE_ORBS = init_scene_data()

# -----------------------------------------------------------------------------
# 3D Camera Projection Math
# -----------------------------------------------------------------------------
def get_camera(t):
    if t < 4.5:
        p = t / 4.5
        cx = math.sin(t * 0.5) * 8.0
        cy = 14.0 + math.sin(t * 0.35) * 4.0
        cz = 50.0 - p * 110.0
        tx = cx * 0.5
        ty = 22.0
        tz = cz - 120.0
        roll = math.sin(t * 0.4) * 0.03
    elif t < 7.2:
        p = (t - 4.5) / 2.7
        ease = p * p * (3.0 - 2.0 * p)
        bank_s = math.sin(ease * math.pi)
        cx = math.sin(4.5 * 0.5) * 8.0 + bank_s * 32.0
        cy = 18.0 + ease * 18.0
        cz = -60.0 - ease * 420.0
        tx = bank_s * 20.0
        ty = 26.0 + ease * 12.0
        tz = cz - 140.0
        roll = -bank_s * 0.28
    else:
        cx, cy, cz = 0.0, 0.0, 100.0
        tx, ty, tz = 0.0, 0.0, 0.0
        roll = 0.0

    fx = tx - cx; fy = ty - cy; fz = tz - cz
    f_len = math.hypot(fx, fy, fz) or 1.0
    fx /= f_len; fy /= f_len; fz /= f_len

    rx = fz; ry = 0.0; rz = -fx
    r_len = math.hypot(rx, rz) or 1.0
    rx /= r_len; rz /= r_len

    ux = ry * fz - rz * fy
    uy = rz * fx - rx * fz
    uz = rx * fy - ry * fx

    if roll != 0.0:
        cr = math.cos(roll); sr = math.sin(roll)
        nrx = rx * cr + ux * sr; nry = ry * cr + uy * sr; nrz = rz * cr + uz * sr
        nux = -rx * sr + ux * cr; nuy = -ry * sr + uy * cr; nuz = -rz * sr + uz * cr
        rx, ry, rz = nrx, nry, nrz
        ux, uy, uz = nux, nuy, nuz

    return (cx, cy, cz, fx, fy, fz, rx, ry, rz, ux, uy, uz)

def project_pt(x, y, z, cam):
    cx, cy, cz, fx, fy, fz, rx, ry, rz, ux, uy, uz = cam
    dx = x - cx; dy = y - cy; dz = z - cz
    cam_x = dx * rx + dy * ry + dz * rz
    cam_y = dx * ux + dy * uy + dz * uz
    cam_z = dx * fx + dy * fy + dz * fz
    if cam_z <= 1.0:
        return None
    fov = 1050.0
    sx = 960.0 + (cam_x / cam_z) * fov
    sy = 540.0 - (cam_y / cam_z) * fov
    return (sx, sy, cam_z, fov / cam_z)

# -----------------------------------------------------------------------------
# Worker Function: Render Single Frame to Raw Bytes
# -----------------------------------------------------------------------------
def render_single_frame(frame_idx):
    t = frame_idx / float(FPS)
    cam = get_camera(t)

    surface = cairo.ImageSurface(cairo.FORMAT_RGB24, WIDTH, HEIGHT)
    ctx = cairo.Context(surface)

    # 1. Background
    if t < 7.2:
        bg = cairo.LinearGradient(0, 0, 0, HEIGHT)
        bg.add_color_stop_rgb(0.0, 0.0, 0.01, 0.03)
        bg.add_color_stop_rgb(0.55, 0.01, 0.04, 0.12)
        bg.add_color_stop_rgb(1.0, 0.0, 0.01, 0.04)
        ctx.set_source(bg)
        ctx.paint()
    else:
        ctx.set_source_rgb(0.0, 0.01, 0.03)
        ctx.paint()

    # 2. Monolith Towers
    if t < 7.5:
        cx, cy, cz = cam[0], cam[1], cam[2]
        fx, fz = cam[3], cam[5]
        visible_towers = []
        for tow in SCENE_TOWERS:
            dist = math.hypot(tow['x'] - cx, (tow['h'] * 0.5) - cy, tow['z'] - cz)
            f_dist = (tow['x'] - cx) * fx + (tow['z'] - cz) * fz
            if f_dist > -20.0 and dist < 700.0:
                visible_towers.append((tow, dist))

        visible_towers.sort(key=lambda item: item[1], reverse=True)

        for tow, dist in visible_towers:
            pts = []
            valid = True
            for vx, vy, vz in tow['verts']:
                p = project_pt(tow['x'] + vx, tow['y'] + vy, tow['z'] + vz, cam)
                if not p:
                    valid = False; break
                pts.append(p)
            if not valid:
                continue

            fog = max(0.0, min(1.0, 1.0 - (dist / 520.0) ** 1.6))
            if fog <= 0.01:
                continue

            pulse = 0.75 + 0.25 * math.sin(t * 2.0 + tow['phase'])

            # Monolith body faces
            faces = [
                (3, 2, 6, 7),  # front
                (0, 3, 7, 4),  # left
                (1, 2, 6, 5),  # right
            ]
            for f in faces:
                ctx.move_to(pts[f[0]][0], pts[f[0]][1])
                ctx.line_to(pts[f[1]][0], pts[f[1]][1])
                ctx.line_to(pts[f[2]][0], pts[f[2]][1])
                ctx.line_to(pts[f[3]][0], pts[f[3]][1])
                ctx.close_path()

                grad = cairo.LinearGradient(0, pts[f[2]][1], 0, pts[f[0]][1])
                grad.add_color_stop_rgba(0.0, 0.01, 0.09, 0.22, 0.75 * fog)
                grad.add_color_stop_rgba(0.5, 0.00, 0.05, 0.14, 0.85 * fog)
                grad.add_color_stop_rgba(1.0, 0.00, 0.02, 0.05, 0.92 * fog)
                ctx.set_source(grad)
                ctx.fill()

            # Glowing top cap
            ctx.move_to(pts[4][0], pts[4][1])
            ctx.line_to(pts[5][0], pts[5][1])
            ctx.line_to(pts[6][0], pts[6][1])
            ctx.line_to(pts[7][0], pts[7][1])
            ctx.close_path()
            ctx.set_source_rgba(0.22, 0.74, 0.97, 0.45 * fog * pulse)
            ctx.fill()

            # Wireframe bevel edges (Iconic PS2 crystal monolith edge glow)
            lw = max(1.0, min(2.8, 350.0 / dist))
            ctx.set_line_width(lw)
            ctx.set_source_rgba(0.22, 0.74, 0.97, 0.85 * fog * pulse)

            ctx.move_to(pts[4][0], pts[4][1]); ctx.line_to(pts[5][0], pts[5][1])
            ctx.line_to(pts[6][0], pts[6][1]); ctx.line_to(pts[7][0], pts[7][1]); ctx.close_path()
            ctx.move_to(pts[0][0], pts[0][1]); ctx.line_to(pts[4][0], pts[4][1])
            ctx.move_to(pts[1][0], pts[1][1]); ctx.line_to(pts[5][0], pts[5][1])
            ctx.move_to(pts[2][0], pts[2][1]); ctx.line_to(pts[6][0], pts[6][1])
            ctx.move_to(pts[3][0], pts[3][1]); ctx.line_to(pts[7][0], pts[7][1])
            ctx.stroke()

    # 3. Energy Orbs & Sparks
    if t < 7.6:
        for orb in SCENE_ORBS:
            ox, oy, oz = orb['x'], orb['y'], orb['z']
            if t < 4.5:
                ox += math.sin(t * orb['orbitSpeed'] + orb['orbitPhase']) * orb['orbitRadius']
                oy += math.cos(t * orb['orbitSpeed'] + orb['orbitPhase']) * (orb['orbitRadius'] * 0.4)
            else:
                p = (t - 4.5) / 2.7
                spiral_s = 3.0 + p * 8.0
                ox = ox * (1.0 - p * 0.5) + math.sin(t * spiral_s + orb['orbitPhase']) * (18.0 * (1.0 - p * 0.7))
                oy = oy * (1.0 - p * 0.5) + math.cos(t * spiral_s + orb['orbitPhase']) * (14.0 * (1.0 - p * 0.7))

            proj = project_pt(ox, oy, oz, cam)
            if not proj:
                continue

            dist = proj[2]
            fog = max(0.0, min(1.0, 1.0 - (dist / 480.0) ** 1.5))
            if fog <= 0.02:
                continue

            r = max(1.2, min(12.0, orb['radius'] * proj[3] * 0.015))
            cr, cg, cb = orb['color']

            if t > 4.8 and t < 7.2:
                streak_len = min(60.0, (t - 4.5) * 24.0 * (proj[3] * 0.02))
                ctx.set_source_rgba(cr, cg, cb, 0.8 * fog)
                ctx.set_line_width(max(1.0, r * 0.6))
                ctx.move_to(proj[0], proj[1])
                ctx.line_to(proj[0] - (cam[0] - ox) * 0.04 * streak_len, proj[1] + (cam[1] - oy) * 0.04 * streak_len)
                ctx.stroke()
            else:
                ctx.set_source_rgba(cr, cg, cb, 0.9 * fog)
                ctx.arc(proj[0], proj[1], r, 0, math.pi * 2)
                ctx.fill()
                ctx.set_source_rgba(cr, cg, cb, 0.25 * fog)
                ctx.arc(proj[0], proj[1], r * 2.8, 0, math.pi * 2)
                ctx.fill()

    # 4. Supernova Flare / Flash (7.15s - 8.1s)
    if 7.15 <= t <= 8.1:
        f_alpha = (t - 7.15) / 0.30 if t < 7.45 else 1.0 - (t - 7.45) / 0.65
        a = max(0.0, min(1.0, f_alpha * 1.1))
        if a > 0.0:
            ctx.set_source_rgba(0.88, 0.96, 1.0, a)
            ctx.paint()

    # 5. Iconic PlayStation 2 // XFCE 4.20 Presentation (7.8s - 12.0s)
    if t >= 7.8:
        p = min(1.0, (t - 7.8) / 0.7)
        # Deep cosmic twilight radial vignette
        rad = cairo.RadialGradient(WIDTH / 2.0, HEIGHT / 2.0 - 20.0, 100.0, WIDTH / 2.0, HEIGHT / 2.0, 850.0)
        rad.add_color_stop_rgba(0.0, 0.015, 0.08, 0.20, 0.60 * p)
        rad.add_color_stop_rgba(0.6, 0.005, 0.03, 0.10, 0.90 * p)
        rad.add_color_stop_rgba(1.0, 0.0, 0.01, 0.03, 1.0 * p)
        ctx.set_source(rad)
        ctx.paint()

        # Floating stardust motes
        for i in range(45):
            sx = (math.sin(i * 12.3 + t * 0.25) * 0.5 + 0.5) * WIDTH
            sy = (math.cos(i * 8.7 + t * 0.20) * 0.5 + 0.5) * HEIGHT
            sa = (0.2 + 0.3 * math.sin(t * 1.5 + i)) * p
            ctx.set_source_rgba(0.73, 0.90, 0.99, sa)
            ctx.arc(sx, sy, 1.2 + (i % 3) * 0.6, 0, math.pi * 2)
            ctx.fill()

        # Corner HUD
        ctx.select_font_face("JetBrainsMono Nerd Font", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(11.0)
        ctx.set_source_rgba(0.58, 0.64, 0.72, 0.6 * p)

        ctx.move_to(48, 48); ctx.show_text("BIOS 2.20 // KABY LAKE-R")
        ctx.move_to(48, HEIGHT - 48); ctx.show_text("ENDEAVOUROS // ARCH LINUX")

        ext1 = ctx.text_extents("SYSTEM MEMORY: 24 GB DUAL-CH")
        ctx.move_to(WIDTH - 48 - ext1.width, 48); ctx.show_text("SYSTEM MEMORY: 24 GB DUAL-CH")

        ext2 = ctx.text_extents("DISPLAY: eDP-1 1080p 60Hz")
        ctx.move_to(WIDTH - 48 - ext2.width, HEIGHT - 48); ctx.show_text("DISPLAY: eDP-1 1080p 60Hz")

        cx = WIDTH / 2.0
        cy = HEIGHT / 2.0 - 22.0

        # Central 3D Hexagonal Prism Emblem
        sym_x = cx - 250.0
        sym_y = cy - 14.0
        s_rad = 48.0

        # Hexagon Fill & Stroke
        ctx.set_line_width(2.8)
        ctx.set_source_rgba(0.22, 0.74, 0.97, 0.95 * p)
        for k in range(6):
            ang = (math.pi / 3.0) * k - math.pi / 6.0
            px = sym_x + math.cos(ang) * s_rad
            py = sym_y + math.sin(ang) * s_rad
            if k == 0: ctx.move_to(px, py)
            else: ctx.line_to(px, py)
        ctx.close_path()
        ctx.set_source_rgba(0.01, 0.52, 0.78, 0.25 * p)
        ctx.fill_preserve()
        ctx.set_source_rgba(0.22, 0.74, 0.97, 0.95 * p)
        ctx.stroke()

        # Inner facets
        ctx.set_line_width(1.4)
        ctx.set_source_rgba(1.0, 1.0, 1.0, 0.7 * p)
        ctx.move_to(sym_x, sym_y - s_rad); ctx.line_to(sym_x, sym_y + s_rad)
        ctx.move_to(sym_x - math.cos(math.pi/6)*s_rad, sym_y - math.sin(math.pi/6)*s_rad)
        ctx.line_to(sym_x, sym_y)
        ctx.line_to(sym_x + math.cos(math.pi/6)*s_rad, sym_y - math.sin(math.pi/6)*s_rad)
        ctx.stroke()

        # Glowing core
        ctx.set_source_rgba(0.22, 0.74, 0.97, 1.0 * p)
        ctx.arc(sym_x, sym_y, 9.0, 0, math.pi * 2)
        ctx.fill()

        # Main "XFCE" PlayStation 2 Style Typography
        ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(108.0)
        text_x = cx - 170.0
        text_y = cy + 24.0

        # Gradient Text Fill (White -> Cyan -> Royal Blue)
        t_grad = cairo.LinearGradient(text_x, text_y - 80.0, text_x, text_y + 20.0)
        t_grad.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 1.0 * p)
        t_grad.add_color_stop_rgba(0.28, 0.49, 0.83, 0.99, 1.0 * p)
        t_grad.add_color_stop_rgba(0.68, 0.01, 0.52, 0.78, 1.0 * p)
        t_grad.add_color_stop_rgba(1.0, 0.01, 0.41, 0.63, 1.0 * p)

        ctx.move_to(text_x, text_y)
        ctx.text_path("XFCE")
        ctx.set_source(t_grad)
        ctx.fill_preserve()

        # Crisp Top Beveled Outline
        ctx.set_line_width(1.8)
        ctx.set_source_rgba(1.0, 1.0, 1.0, 0.7 * p)
        ctx.stroke()

        # "4.20" Super-Script Badge
        ctx.set_font_size(32.0)
        badge_x = text_x + 312.0
        badge_y = text_y - 50.0
        b_grad = cairo.LinearGradient(badge_x, badge_y - 25.0, badge_x, badge_y)
        b_grad.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 1.0 * p)
        b_grad.add_color_stop_rgba(1.0, 0.22, 0.74, 0.97, 1.0 * p)
        ctx.move_to(badge_x, badge_y)
        ctx.text_path("4.20")
        ctx.set_source(b_grad)
        ctx.fill()

        # Shimmer / Light Sheen across "XFCE" (t = 8.3s - 10.6s)
        sheen_p = (t - 8.3) / 2.3
        if 0.0 <= sheen_p <= 1.2:
            ctx.save()
            ctx.rectangle(text_x - 10.0, text_y - 95.0, 440.0, 120.0)
            ctx.clip()

            sheen_x = (text_x - 120.0) + sheen_p * 600.0
            s_grad = cairo.LinearGradient(sheen_x - 40.0, text_y - 60.0, sheen_x + 40.0, text_y + 20.0)
            s_grad.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.0)
            s_grad.add_color_stop_rgba(0.5, 1.0, 1.0, 1.0, 0.85 * p)
            s_grad.add_color_stop_rgba(1.0, 1.0, 1.0, 1.0, 0.0)

            # Angled light sweep polygon
            ctx.move_to(sheen_x - 30.0, text_y - 100.0)
            ctx.line_to(sheen_x + 30.0, text_y - 100.0)
            ctx.line_to(sheen_x + 70.0, text_y + 30.0)
            ctx.line_to(sheen_x + 10.0, text_y + 30.0)
            ctx.close_path()
            ctx.set_source(s_grad)
            ctx.fill()
            ctx.restore()

        # Subtitle: "DESKTOP ENVIRONMENT"
        ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(19.0)
        sub_text = "D E S K T O P   E N V I R O N M E N T"
        sub_ext = ctx.text_extents(sub_text)
        ctx.move_to(cx - sub_ext.width / 2.0 + 8.0, cy + 72.0)
        ctx.set_source_rgba(0.58, 0.64, 0.72, 0.9 * p)
        ctx.show_text(sub_text)

        # Glowing Divider Line
        d_grad = cairo.LinearGradient(cx - 300.0, 0, cx + 300.0, 0)
        d_grad.add_color_stop_rgba(0.0, 0.22, 0.74, 0.97, 0.0)
        d_grad.add_color_stop_rgba(0.5, 0.22, 0.74, 0.97, 0.9 * p)
        d_grad.add_color_stop_rgba(1.0, 0.22, 0.74, 0.97, 0.0)
        ctx.set_source(d_grad)
        ctx.rectangle(cx - 300.0, cy + 98.0, 600.0, 1.8)
        ctx.fill()

        # OS & Hardware Meta
        ctx.select_font_face("JetBrainsMono Nerd Font", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(13.0)
        os_text = "ENDEAVOUROS LINUX • DELL LATITUDE 7490"
        os_ext = ctx.text_extents(os_text)
        ctx.move_to(cx - os_ext.width / 2.0, cy + 128.0)
        ctx.set_source_rgba(0.79, 0.83, 0.88, 0.9 * p)
        ctx.show_text(os_text)

        # Status Pill Badge
        badge_y = cy + 174.0
        bw = 580.0
        bh = 38.0
        ctx.set_line_width(1.0)
        ctx.set_source_rgba(0.06, 0.09, 0.16, 0.76 * p)
        ctx.rectangle(cx - bw / 2.0, badge_y - bh / 2.0, bw, bh)
        ctx.fill_preserve()
        ctx.set_source_rgba(0.22, 0.74, 0.97, 0.32 * p)
        ctx.stroke()

        # Pulsing Green LED
        led_pulse = 0.65 + 0.35 * math.sin(t * 4.0)
        ctx.set_source_rgba(0.06, 0.72, 0.51, led_pulse * p)
        ctx.arc(cx - 245.0, badge_y, 4.5, 0, math.pi * 2)
        ctx.fill()

        # Badge labels
        ctx.set_font_size(11.0)
        ctx.set_source_rgba(0.39, 0.45, 0.55, 0.9 * p)
        ctx.move_to(cx - 232.0, badge_y + 4.0); ctx.show_text("SYSTEM READY")
        ctx.move_to(cx - 90.0, badge_y + 4.0); ctx.show_text("|")
        ctx.move_to(cx - 70.0, badge_y + 4.0); ctx.show_text("VA-API ACCELERATED")
        ctx.move_to(cx + 115.0, badge_y + 4.0); ctx.show_text("|")
        ctx.move_to(cx + 135.0, badge_y + 4.0); ctx.show_text("PIPEWIRE 1.6")

    # Final gentle fade to black (11.5s - 12.0s) for desktop reveal
    if t > 11.4:
        fade_a = min(1.0, (t - 11.4) / 0.6)
        ctx.set_source_rgba(0.0, 0.0, 0.0, fade_a)
        ctx.paint()

    # Flush surface and return raw buffer
    surface.flush()
    return bytes(surface.get_data())

# -----------------------------------------------------------------------------
# Main Orchestration: Stream 720 frames to ffmpeg
# -----------------------------------------------------------------------------
def main():
    print("=" * 68)
    print("  PS2 XFCE 4.20 HIGH-PERFORMANCE STARTUP VIDEO GENERATOR")
    print("=" * 68)
    print(f"[*] Target: 1080p @ 60.00 FPS ({TOTAL_FRAMES} frames, {DURATION}s)")
    print(f"[*] Dell Latitude 7490 Parallel Boost: 8 worker threads")

    # 1. Synthesize audio if needed
    if not os.path.exists(AUDIO_WAV):
        print("[*] Generating studio-grade PlayStation 2 boot audio...")
        try:
            from generate_audio import generate_ps2_soundtrack
            generate_ps2_soundtrack(AUDIO_WAV)
        except Exception:
            gen_script = os.path.join(SCRIPT_DIR, "generate_audio.py")
            subprocess.run([sys.executable, gen_script, AUDIO_WAV], check=True)
    else:
        print(f"[✓] Audio soundtrack ready: {AUDIO_WAV}")

    # 2. Launch FFmpeg process with stdin pipe for raw frames
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{WIDTH}x{HEIGHT}",
        "-pix_fmt", "bgra",
        "-r", str(FPS),
        "-i", "-",  # Video from stdin pipe
        "-i", AUDIO_WAV,  # Audio from WAV
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "320k",
        "-shortest",
        FINAL_MP4
    ]

    print("[*] Spawning FFmpeg encoder process...")
    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    t_start = time.time()
    rendered_count = 0

    # 3. Parallel frame generation with multiprocessing pool
    workers = min(8, multiprocessing.cpu_count())
    print(f"[*] Rendering & encoding {TOTAL_FRAMES} frames across {workers} parallel workers...")

    with multiprocessing.Pool(processes=workers) as pool:
        # imap preserves strict chronological frame order
        for frame_bytes in pool.imap(render_single_frame, range(TOTAL_FRAMES), chunksize=4):
            proc.stdin.write(frame_bytes)
            rendered_count += 1
            if rendered_count % 60 == 0 or rendered_count == TOTAL_FRAMES:
                pct = (rendered_count / TOTAL_FRAMES) * 100.0
                fps_rate = rendered_count / max(0.001, time.time() - t_start)
                print(f"    -> Progress: {rendered_count:3d}/{TOTAL_FRAMES} ({pct:5.1f}%) | {fps_rate:4.1f} FPS", end="\r", flush=True)

    print()
    proc.stdin.close()
    _, stderr = proc.communicate()

    if proc.returncode != 0:
        print(f"[!] FFmpeg error:\n{stderr.decode()}")
        sys.exit(1)

    elapsed = time.time() - t_start
    size_mb = os.path.getsize(FINAL_MP4) / (1024.0 * 1024.0)
    print("=" * 68)
    print(f"[🎉] COMPLETE: Successfully rendered & encoded {FINAL_MP4}")
    print(f"    Size: {size_mb:.2f} MB | Render Time: {elapsed:.2f}s | Avg Speed: {TOTAL_FRAMES/elapsed:.1f} FPS")
    print("=" * 68)

if __name__ == "__main__":
    main()
