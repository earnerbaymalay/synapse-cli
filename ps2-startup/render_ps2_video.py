#!/usr/bin/env python3
"""
PS2-Inspired XFCE Startup Video Engine (parallel Cairo renderer -> FFmpeg)

Three-act structure modelled on the PlayStation 2 BIOS boot:
  Act I   (0.0 - 4.4s)  Black void; light motes spiral inward, collapse into a
                        horizontal flare and an ENDEAVOUROS wordmark, then fade.
  Act II  (4.1 - 9.6s)  Translucent glass towers on a reflective floor, revealed
                        as the mist clears, slow continuous camera orbit, drifting
                        orbs; camera rises into a pale blue whiteout.
  Act III (9.5 - 12.0s) Whiteout dissolves into the XFCE 4.20 logo. Everything is
                        static from T_STATIC onwards so the final frame can be
                        handed off pixel-for-pixel to the SDDM login theme.

All timing is driven by smooth (C1/C2) easing curves; there are no hard cuts.
"""

import math
import multiprocessing
import os
import subprocess
import sys
import time

try:
    import cairo
except ImportError:
    cairo = None

WIDTH = 1920
HEIGHT = 1080
BG_WIDTH = 3840
BG_HEIGHT = 2160
FPS = 60
DURATION = 9.6
TOTAL_FRAMES = int(DURATION * FPS)  # 576 frames

# Timeline (seconds)
T_INTRO_FADE = (3.7, 4.35)
T_TOWER_START = 4.1
T_TOWER_FADE_IN = (4.1, 5.0)
T_WHITEOUT = (7.4, 8.4)
T_LOGO_DISSOLVE = (7.4, 8.1)
T_LOGO_IN = (7.45, 8.15)
T_SHEEN = (8.0, 8.35)
T_STATIC = 8.4

FOV = 1250.0

# Logo / greeter layout (shared with the SDDM theme via theme.conf; 1080p ref coords, 744.0 in 4K)
LOGO_CY = 372.0          # baseline of the wordmark (744.0 in 3840x2160 4K)
PANEL_TOP = 572          # where the greeter's login panel begins

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

ORIG_SOURCE_MP4 = os.path.join(SCRIPT_DIR, "original_ps2_source.mp4")
AUDIO_WAV = os.path.join(SCRIPT_DIR, "ps2_startup.wav")
FINAL_MP4 = os.path.join(SCRIPT_DIR, "ps2_xfce_startup.mp4")
THEME_DIR = os.path.join(SCRIPT_DIR, "sddm-theme")
GREETER_BG = os.path.join(THEME_DIR, "background.png")

MONO_FONT = "JetBrainsMono Nerd Font"
SANS_FONT = "Inter"
LOGO_FONT = "DejaVu Sans"


# -----------------------------------------------------------------------------
# Easing helpers
# -----------------------------------------------------------------------------
def clamp(x, lo=0.0, hi=1.0):
    return lo if x < lo else hi if x > hi else x


def smoothstep(e0, e1, x):
    x = clamp((x - e0) / (e1 - e0))
    return x * x * (3.0 - 2.0 * x)


def smootherstep(e0, e1, x):
    x = clamp((x - e0) / (e1 - e0))
    return x * x * x * (x * (x * 6.0 - 15.0) + 10.0)


def lerp(a, b, k):
    return a + (b - a) * k


def mix3(c1, c2, k):
    return (lerp(c1[0], c2[0], k), lerp(c1[1], c2[1], k), lerp(c1[2], c2[2], k))


# -----------------------------------------------------------------------------
# Procedural scene data (deterministic, shared by all workers)
# -----------------------------------------------------------------------------
GRID = 11
SPACING = 14.0


def init_scene_data():
    seed = 1337

    def rnd():
        nonlocal seed
        seed = (seed * 1664525 + 1013904223) % 4294967296
        return seed / 4294967296.0

    # Tower field: a regular grid with gaps, mostly short towers and a few tall
    # ones -- the PS2 "memory card" skyline.
    towers = []
    half = (GRID - 1) / 2.0
    for gx in range(GRID):
        for gz in range(GRID):
            if rnd() < 0.2:
                continue
            h = 4.0 + (rnd() ** 2.4) * 52.0
            towers.append({
                'x': (gx - half) * SPACING, 'y': 0.0, 'z': (gz - half) * SPACING,
                'w': 7.6, 'h': h, 'd': 7.6,
                'phase': rnd() * math.pi * 2.0,
            })

    orbs = []
    for _ in range(46):
        orbs.append({
            'x': (rnd() - 0.5) * 170.0,
            'y': 4.0 + rnd() * 70.0,
            'z': (rnd() - 0.5) * 170.0,
            'radius': 0.35 + rnd() * 0.6,
            'rise': 1.2 + rnd() * 2.6,
            'sway': rnd() * math.pi * 2.0,
        })
    return towers, orbs


def init_intro_particles():
    seed = 4242

    def rnd():
        nonlocal seed
        seed = (seed * 1664525 + 1013904223) % 4294967296
        return seed / 4294967296.0

    parts = []
    for _ in range(280):
        parts.append({
            'a0': rnd() * math.pi * 2.0,
            'r0': 380.0 + rnd() * 1050.0,
            'spin': 1.4 + rnd() * 2.2,
            'delay': rnd() * 0.75,
            'size': 0.8 + rnd() * 1.9,
            'tint': rnd(),
        })
    return parts


SCENE_TOWERS, SCENE_ORBS = init_scene_data()
INTRO_PARTICLES = init_intro_particles()


# -----------------------------------------------------------------------------
# Camera (single continuous path -- no piecewise velocity jumps)
# -----------------------------------------------------------------------------
def get_camera(t):
    # Not clamped below 0: the camera is already gliding before the fade-in.
    u = min(1.0, (t - T_TOWER_START) / (9.5 - T_TOWER_START))
    # Mostly linear glide with eased ends: never stops, never jerks.
    s = 0.45 * u + 0.55 * smootherstep(0.0, 1.0, u)
    theta = -0.62 + 1.10 * s
    radius = 225.0 - 50.0 * s
    rise = smoothstep(8.2, 9.6, t) ** 2

    cx = math.sin(theta) * radius
    cz = math.cos(theta) * radius
    cy = 88.0 - 22.0 * s + rise * 70.0
    tx, ty, tz = 0.0, rise * 190.0, 0.0
    roll = 0.035 * math.sin(theta * 1.7)

    fx, fy, fz = tx - cx, ty - cy, tz - cz
    f_len = math.sqrt(fx * fx + fy * fy + fz * fz) or 1.0
    fx /= f_len; fy /= f_len; fz /= f_len

    rx, ry, rz = -fz, 0.0, fx
    r_len = math.hypot(rx, rz) or 1.0
    rx /= r_len; rz /= r_len

    ux = ry * fz - rz * fy
    uy = rz * fx - rx * fz
    uz = rx * fy - ry * fx

    cr, sr = math.cos(roll), math.sin(roll)
    rx, ry, rz, ux, uy, uz = (rx * cr + ux * sr, ry * cr + uy * sr, rz * cr + uz * sr,
                              -rx * sr + ux * cr, -ry * sr + uy * cr, -rz * sr + uz * cr)
    return (cx, cy, cz, fx, fy, fz, rx, ry, rz, ux, uy, uz)


def project_pt(x, y, z, cam):
    cx, cy, cz, fx, fy, fz, rx, ry, rz, ux, uy, uz = cam
    dx, dy, dz = x - cx, y - cy, z - cz
    cam_z = dx * fx + dy * fy + dz * fz
    if cam_z <= 1.0:
        return None
    cam_x = dx * rx + dy * ry + dz * rz
    cam_y = dx * ux + dy * uy + dz * uz
    return (WIDTH / 2.0 + (cam_x / cam_z) * FOV,
            HEIGHT / 2.0 - (cam_y / cam_z) * FOV,
            cam_z, FOV / cam_z)


# -----------------------------------------------------------------------------
# Cheap bloom: draw into a low-res surface, upscale bilinear, add.
# -----------------------------------------------------------------------------
def make_glow_layer(factor):
    w, h = WIDTH // factor, HEIGHT // factor
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    gctx = cairo.Context(surf)
    gctx.scale(1.0 / factor, 1.0 / factor)
    return surf, gctx


def composite_glow(ctx, surf, factor, alpha=1.0):
    ctx.save()
    ctx.scale(factor, factor)
    ctx.set_source_surface(surf, 0, 0)
    ctx.get_source().set_filter(cairo.FILTER_BILINEAR)
    ctx.set_operator(cairo.OPERATOR_ADD)
    ctx.paint_with_alpha(alpha)
    ctx.restore()


def spaced_text(ctx, text, x, y, tracking):
    """Draw text with letter-spacing; returns total advance."""
    cx = x
    for ch in text:
        ctx.move_to(cx, y)
        ctx.text_path(ch)
        cx += ctx.text_extents(ch).x_advance + tracking
    return cx - x - tracking


def spaced_width(ctx, text, tracking):
    return sum(ctx.text_extents(ch).x_advance for ch in text) + tracking * (len(text) - 1)


# -----------------------------------------------------------------------------
# Act I -- light vortex & wordmark
# -----------------------------------------------------------------------------
INTRO_CX, INTRO_CY = WIDTH / 2.0, HEIGHT / 2.0 - 10.0


def draw_intro(ctx, t):
    ctx.set_source_rgb(0.0, 0.0, 0.0)
    ctx.paint()

    glow, gctx = make_glow_layer(6)

    # Inward spiralling motes
    for p in INTRO_PARTICLES:
        q = clamp((t - 0.35 - p['delay']) / (2.05 - p['delay']))
        if q <= 0.0 or q >= 1.0:
            continue
        r = p['r0'] * (1.0 - q) ** 1.7
        ang = p['a0'] + p['spin'] * q * 2.4
        x = INTRO_CX + math.cos(ang) * r
        y = INTRO_CY + math.sin(ang) * r * 0.62
        a = smoothstep(0.0, 0.25, q) * (1.0 - smoothstep(0.85, 1.0, q))
        col = mix3((0.55, 0.78, 1.0), (1.0, 1.0, 1.0), p['tint'])
        ctx.set_source_rgba(col[0], col[1], col[2], 0.9 * a)
        ctx.arc(x, y, p['size'], 0, math.pi * 2)
        ctx.fill()
        gctx.set_source_rgba(col[0], col[1], col[2], 0.8 * a)
        gctx.arc(x, y, p['size'] * 5.0, 0, math.pi * 2)
        gctx.fill()

    # Central gathering glow
    gather = smoothstep(0.6, 2.35, t) * (1.0 - smoothstep(2.4, 3.6, t) * 0.75)
    if gather > 0.0:
        rad = cairo.RadialGradient(INTRO_CX, INTRO_CY, 0, INTRO_CX, INTRO_CY, 60 + 220 * gather)
        rad.add_color_stop_rgba(0.0, 0.85, 0.93, 1.0, 0.55 * gather)
        rad.add_color_stop_rgba(0.4, 0.30, 0.55, 0.95, 0.22 * gather)
        rad.add_color_stop_rgba(1.0, 0.0, 0.1, 0.3, 0.0)
        ctx.set_source(rad)
        ctx.paint()

    # Horizontal flare at the moment of collapse
    flare = smoothstep(2.25, 2.42, t) * (1.0 - smoothstep(2.42, 3.4, t))
    if flare > 0.0:
        ctx.save()
        ctx.translate(INTRO_CX, INTRO_CY)
        ctx.scale(1.0, 0.018 + 0.03 * (1.0 - flare))
        span = 300.0 + 900.0 * smoothstep(2.25, 2.9, t)
        rad = cairo.RadialGradient(0, 0, 0, 0, 0, span)
        rad.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, flare)
        rad.add_color_stop_rgba(0.35, 0.65, 0.85, 1.0, 0.6 * flare)
        rad.add_color_stop_rgba(1.0, 0.2, 0.4, 1.0, 0.0)
        ctx.set_source(rad)
        ctx.arc(0, 0, span, 0, math.pi * 2)
        ctx.fill()
        ctx.restore()

    # Wordmark
    word_a = smoothstep(2.32, 2.85, t)
    if word_a > 0.0:
        ctx.select_font_face(SANS_FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        ctx.set_font_size(58.0)
        word = "ENDEAVOUROS"
        tracking = 22.0
        ww = spaced_width(ctx, word, tracking)
        wx = INTRO_CX - ww / 2.0
        wy = INTRO_CY + 20.0
        breathe = 0.92 + 0.08 * math.sin((t - 2.3) * 2.2)

        gctx.select_font_face(SANS_FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        gctx.set_font_size(58.0)
        spaced_text(gctx, word, wx, wy, tracking)
        gctx.set_source_rgba(0.55, 0.8, 1.0, 0.9 * word_a * breathe)
        gctx.set_line_width(10.0)
        gctx.stroke()

        spaced_text(ctx, word, wx, wy, tracking)
        ctx.set_source_rgba(0.96, 0.98, 1.0, word_a)
        ctx.fill()

        sub_a = smoothstep(2.75, 3.25, t)
        ctx.set_font_size(15.0)
        sub = "DELL LATITUDE 7490   ·   ARCH LINUX"
        sw = spaced_width(ctx, sub, 5.0)
        spaced_text(ctx, sub, INTRO_CX - sw / 2.0, wy + 58.0, 5.0)
        ctx.set_source_rgba(0.62, 0.72, 0.86, 0.85 * sub_a)
        ctx.fill()

    composite_glow(ctx, glow, 6, 1.0)


# -----------------------------------------------------------------------------
# Act II -- tower field
# -----------------------------------------------------------------------------
FOG_DEEP = (0.035, 0.075, 0.17)
FOG_WHITE = (0.80, 0.89, 1.0)
FACE_TOP = (0.74, 0.87, 1.0)
FACE_SIDE = (0.30, 0.48, 0.78)

# (normal, vertex indices) for the 5 drawable faces of a box
BOX_FACES = (
    ((0, 0, -1), (0, 1, 5, 4)),
    ((1, 0, 0), (1, 2, 6, 5)),
    ((0, 0, 1), (2, 3, 7, 6)),
    ((-1, 0, 0), (3, 0, 4, 7)),
)


def tower_fog_params(t):
    reveal = smoothstep(4.1, 6.2, t)
    white = smoothstep(*T_WHITEOUT, t)
    fog_d = lerp(50.0, 300.0, reveal) * lerp(1.0, 0.22, white)
    fog_col = mix3(FOG_DEEP, FOG_WHITE, white)
    return fog_d, fog_col, white


def draw_towers(ctx, t):
    cam = get_camera(t)
    cx, cy, cz = cam[0], cam[1], cam[2]
    fog_d, fog_col, white = tower_fog_params(t)

    # Sky / floor gradient around the horizon
    far = project_pt(cx + cam[3] * 4000.0, 0.0, cz + cam[5] * 4000.0, cam)
    horizon = far[1] if far else HEIGHT * 0.45
    hn = clamp(horizon / HEIGHT, 0.05, 0.95)
    bg = cairo.LinearGradient(0, 0, 0, HEIGHT)
    bg.add_color_stop_rgb(0.0, *mix3((0.0, 0.008, 0.03), fog_col, white))
    bg.add_color_stop_rgb(hn, *mix3((0.02, 0.05, 0.12), fog_col, 0.5 + 0.5 * white))
    bg.add_color_stop_rgb(min(1.0, hn + 0.35), *mix3((0.008, 0.025, 0.07), fog_col, white))
    bg.add_color_stop_rgb(1.0, *mix3((0.0, 0.01, 0.035), fog_col, white))
    ctx.set_source(bg)
    ctx.paint()

    visible = []
    for tow in SCENE_TOWERS:
        dist = math.sqrt((tow['x'] - cx) ** 2 + (tow['h'] * 0.5 - cy) ** 2 + (tow['z'] - cz) ** 2)
        fog = 1.0 - math.exp(-(dist / fog_d) ** 2)
        if fog < 0.995:
            visible.append((dist, fog, tow))
    visible.sort(key=lambda v: v[0], reverse=True)

    glow, gctx = make_glow_layer(8)

    def box_points(tow, mirror):
        hw, hd = tow['w'] / 2.0, tow['d'] / 2.0
        h = -tow['h'] if mirror else tow['h']
        pts = []
        for vx, vy, vz in ((-hw, 0, -hd), (hw, 0, -hd), (hw, 0, hd), (-hw, 0, hd),
                           (-hw, h, -hd), (hw, h, -hd), (hw, h, hd), (-hw, h, hd)):
            p = project_pt(tow['x'] + vx, vy, tow['z'] + vz, cam)
            if p is None:
                return None
            pts.append(p)
        return pts

    def poly(c, pts, idx):
        c.move_to(pts[idx[0]][0], pts[idx[0]][1])
        for i in idx[1:]:
            c.line_to(pts[i][0], pts[i][1])
        c.close_path()

    def side_faces(tow):
        out = []
        for n, idx in BOX_FACES:
            fcx = tow['x'] + n[0] * tow['w'] / 2.0
            fcz = tow['z'] + n[2] * tow['d'] / 2.0
            if n[0] * (cx - fcx) + n[2] * (cz - fcz) > 0.0:
                out.append((n, idx))
        return out

    # Floor reflections (mirrored, faint, fading with depth)
    for dist, fog, tow in visible:
        pts = box_points(tow, True)
        if pts is None:
            continue
        a = 0.20 * (1.0 - fog)
        if a < 0.004:
            continue
        for n, idx in side_faces(tow):
            poly(ctx, pts, idx)
            grad = cairo.LinearGradient(0, pts[idx[0]][1], 0, pts[idx[2]][1])
            col = mix3(FACE_SIDE, fog_col, fog)
            grad.add_color_stop_rgba(0.0, col[0], col[1], col[2], a)
            grad.add_color_stop_rgba(1.0, col[0], col[1], col[2], 0.0)
            ctx.set_source(grad)
            ctx.fill()

    # Glossy floor veil between reflections and towers
    if horizon < HEIGHT:
        veil = cairo.LinearGradient(0, horizon, 0, HEIGHT)
        vc = mix3((0.01, 0.03, 0.08), fog_col, 0.25 + 0.75 * white)
        veil.add_color_stop_rgba(0.0, vc[0], vc[1], vc[2], 0.55)
        veil.add_color_stop_rgba(1.0, vc[0], vc[1], vc[2], 0.25)
        ctx.set_source(veil)
        ctx.rectangle(0, max(0.0, horizon), WIDTH, HEIGHT)
        ctx.fill()

    # Towers
    for dist, fog, tow in visible:
        pts = box_points(tow, False)
        if pts is None:
            continue
        vis = 1.0 - fog
        shimmer = 0.9 + 0.1 * math.sin(t * 1.3 + tow['phase'])
        for n, idx in side_faces(tow):
            shade = 0.82 if n[0] != 0 else 1.0
            top_col = mix3(mix3(FACE_SIDE, FACE_TOP, 0.45), fog_col, fog)
            base_col = mix3((FACE_SIDE[0] * 0.35, FACE_SIDE[1] * 0.35, FACE_SIDE[2] * 0.4), fog_col, fog)
            poly(ctx, pts, idx)
            grad = cairo.LinearGradient(0, pts[idx[2]][1], 0, pts[idx[0]][1])
            grad.add_color_stop_rgba(0.0, top_col[0] * shade, top_col[1] * shade, top_col[2] * shade, 0.70 * vis + 0.1)
            grad.add_color_stop_rgba(1.0, base_col[0], base_col[1], base_col[2], 0.55 * vis + 0.1)
            ctx.set_source(grad)
            ctx.fill()

        # Lit cap
        cap = mix3(FACE_TOP, fog_col, fog)
        poly(ctx, pts, (4, 5, 6, 7))
        ctx.set_source_rgba(cap[0], cap[1], cap[2], (0.85 * vis + 0.1) * shimmer)
        ctx.fill_preserve()
        ctx.set_source_rgba(1.0, 1.0, 1.0, 0.55 * vis)
        ctx.set_line_width(max(0.6, min(2.0, 220.0 / dist)))
        ctx.stroke()

        # Vertical edges
        ctx.set_source_rgba(0.80, 0.92, 1.0, 0.32 * vis)
        for i in range(4):
            ctx.move_to(pts[i][0], pts[i][1])
            ctx.line_to(pts[i + 4][0], pts[i + 4][1])
        ctx.stroke()

        poly(gctx, pts, (4, 5, 6, 7))
        gctx.set_source_rgba(0.55, 0.78, 1.0, 0.75 * vis * shimmer)
        gctx.fill()

    # Drifting translucent orbs
    for orb in SCENE_ORBS:
        oy = orb['y'] + orb['rise'] * (t - T_TOWER_START)
        ox = orb['x'] + math.sin(t * 0.6 + orb['sway']) * 3.0
        oz = orb['z'] + math.cos(t * 0.5 + orb['sway']) * 3.0
        p = project_pt(ox, oy, oz, cam)
        if p is None:
            continue
        fog = 1.0 - math.exp(-(p[2] / fog_d) ** 2)
        vis = 1.0 - fog
        if vis < 0.01:
            continue
        r = max(1.0, orb['radius'] * p[3])
        g = cairo.RadialGradient(p[0] - r * 0.3, p[1] - r * 0.3, 0, p[0], p[1], r)
        g.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.75 * vis)
        g.add_color_stop_rgba(0.6, 0.6, 0.82, 1.0, 0.25 * vis)
        g.add_color_stop_rgba(1.0, 0.5, 0.75, 1.0, 0.05 * vis)
        ctx.set_source(g)
        ctx.arc(p[0], p[1], r, 0, math.pi * 2)
        ctx.fill()
        gctx.set_source_rgba(0.6, 0.85, 1.0, 0.6 * vis)
        gctx.arc(p[0], p[1], r * 2.5, 0, math.pi * 2)
        gctx.fill()

    composite_glow(ctx, glow, 8, 0.9)

    if white > 0.0:
        ctx.set_source_rgba(FOG_WHITE[0], FOG_WHITE[1], FOG_WHITE[2], white ** 1.5)
        ctx.paint()


# -----------------------------------------------------------------------------
# Act III -- PlayStation 2 logo (final frame == greeter background)
# -----------------------------------------------------------------------------
def logo_layout(ctx):
    """Measure the PlayStation 2 logo group so it is centred exactly on the screen."""
    ctx.select_font_face(LOGO_FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(88.0)
    ps_ext = ctx.text_extents("PlayStation")
    ctx.set_font_size(108.0)
    two_ext = ctx.text_extents("2")
    emblem_r = 44.0
    gap = 32.0
    gap_two = 16.0
    total = emblem_r * 2.0 + gap + ps_ext.x_advance + gap_two + two_ext.x_advance
    left = WIDTH / 2.0 - total / 2.0
    return {
        'emblem_x': left + emblem_r,
        'emblem_y': LOGO_CY - ps_ext.height / 2.0 + 2.0,
        'emblem_r': emblem_r,
        'text_x': left + emblem_r * 2.0 + gap - ps_ext.x_bearing,
        'text_w': ps_ext.width,
        'text_h': ps_ext.height,
        'badge_x': left + emblem_r * 2.0 + gap + ps_ext.x_advance + gap_two,
        'badge_w': two_ext.width,
        'badge_h': two_ext.height,
    }


def draw_logo_background(ctx):
    # 1. Deep PS2 cyber-blue void + subtle indigo nebula core
    rad = cairo.RadialGradient(WIDTH / 2.0, 400.0, 40.0, WIDTH / 2.0, 470.0, 1180.0)
    rad.add_color_stop_rgb(0.0, 0.055, 0.16, 0.36)
    rad.add_color_stop_rgb(0.42, 0.016, 0.058, 0.16)
    rad.add_color_stop_rgb(1.0, 0.002, 0.010, 0.035)
    ctx.set_source(rad)
    ctx.paint()

    # 2. Subtle perspective crystal monolith silhouettes & glowing glass edges
    cam = get_camera(6.6)
    cx, cy, cz = cam[0], cam[1], cam[2]
    fog_d = 265.0
    fog_col = (0.015, 0.05, 0.14)

    visible = []
    for tow in SCENE_TOWERS:
        dist = math.sqrt((tow['x'] - cx) ** 2 + (tow['h'] * 0.5 - cy) ** 2 + (tow['z'] - cz) ** 2)
        fog = 1.0 - math.exp(-(dist / fog_d) ** 2)
        if fog < 0.995:
            visible.append((dist, fog, tow))
    visible.sort(key=lambda v: v[0], reverse=True)

    def box_pts(tow):
        hw, hd = tow['w'] / 2.0, tow['d'] / 2.0
        h = tow['h']
        pts = []
        for vx, vy, vz in ((-hw, 0, -hd), (hw, 0, -hd), (hw, 0, hd), (-hw, 0, hd),
                           (-hw, h, -hd), (hw, h, -hd), (hw, h, hd), (-hw, h, hd)):
            p = project_pt(tow['x'] + vx, vy, tow['z'] + vz, cam)
            if p is None:
                return None
            pts.append(p)
        return pts

    def poly(c, pts, idx):
        c.move_to(pts[idx[0]][0], pts[idx[0]][1])
        for i in idx[1:]:
            c.line_to(pts[i][0], pts[i][1])
        c.close_path()

    for dist, fog, tow in visible:
        pts = box_pts(tow)
        if pts is None:
            continue
        vis = (1.0 - fog) * 0.34
        for n, idx in BOX_FACES:
            fcx = tow['x'] + n[0] * tow['w'] / 2.0
            fcz = tow['z'] + n[2] * tow['d'] / 2.0
            if n[0] * (cx - fcx) + n[2] * (cz - fcz) <= 0.0:
                continue
            shade = 0.82 if n[0] != 0 else 1.0
            top_col = mix3(mix3(FACE_SIDE, FACE_TOP, 0.45), fog_col, fog)
            base_col = mix3((FACE_SIDE[0] * 0.3, FACE_SIDE[1] * 0.3, FACE_SIDE[2] * 0.38), fog_col, fog)
            poly(ctx, pts, idx)
            grad = cairo.LinearGradient(0, pts[idx[2]][1], 0, pts[idx[0]][1])
            grad.add_color_stop_rgba(0.0, top_col[0] * shade, top_col[1] * shade, top_col[2] * shade, 0.65 * vis)
            grad.add_color_stop_rgba(1.0, base_col[0], base_col[1], base_col[2], 0.35 * vis)
            ctx.set_source(grad)
            ctx.fill()

        # Crystal top cap & luminous edges
        cap = mix3(FACE_TOP, fog_col, fog)
        poly(ctx, pts, (4, 5, 6, 7))
        ctx.set_source_rgba(cap[0], cap[1], cap[2], 0.72 * vis)
        ctx.fill_preserve()
        ctx.set_source_rgba(0.75, 0.92, 1.0, 0.48 * vis)
        ctx.set_line_width(max(0.5, min(1.5, 180.0 / dist)))
        ctx.stroke()

        ctx.set_source_rgba(0.60, 0.85, 1.0, 0.26 * vis)
        for i in range(4):
            ctx.move_to(pts[i][0], pts[i][1])
            ctx.line_to(pts[i + 4][0], pts[i + 4][1])
        ctx.stroke()

    # 3. Central clear-zone vignette so the PS2 // XFCE 4.20 emblem & SDDM login card have high contrast
    veil = cairo.RadialGradient(WIDTH / 2.0, 500.0, 110.0, WIDTH / 2.0, 520.0, 760.0)
    veil.add_color_stop_rgba(0.0, 0.025, 0.09, 0.22, 0.86)
    veil.add_color_stop_rgba(0.55, 0.012, 0.045, 0.13, 0.55)
    veil.add_color_stop_rgba(1.0, 0.0, 0.01, 0.035, 0.0)
    ctx.set_source(veil)
    ctx.paint()


def draw_logo(ctx, a, scale, sheen_p):
    L = logo_layout(ctx)
    ctx.save()
    ctx.translate(WIDTH / 2.0, LOGO_CY)
    ctx.scale(scale, scale)
    ctx.translate(-WIDTH / 2.0, -LOGO_CY)

    # Soft ambient halo behind the logo
    glow, gctx = make_glow_layer(8)
    gctx.select_font_face(LOGO_FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    gctx.set_font_size(88.0)
    gctx.move_to(L['text_x'], LOGO_CY)
    gctx.text_path("PlayStation")
    gctx.set_source_rgba(0.2, 0.55, 1.0, 0.75)
    gctx.set_line_width(12.0)
    gctx.stroke()
    gctx.set_font_size(108.0)
    gctx.move_to(L['badge_x'], LOGO_CY)
    gctx.text_path("2")
    gctx.set_source_rgba(0.0, 0.8, 1.0, 0.85)
    gctx.set_line_width(14.0)
    gctx.stroke()
    gctx.arc(L['emblem_x'], L['emblem_y'], L['emblem_r'] * 1.2, 0, math.pi * 2)
    gctx.set_source_rgba(0.2, 0.6, 1.0, 0.45)
    gctx.fill()
    composite_glow(ctx, glow, 8, 0.55 * a)

    # Authentic PlayStation PS Emblem
    ex, ey, er = L['emblem_x'], L['emblem_y'], L['emblem_r']
    ctx.save()
    # Upright P (coral/red gradient)
    pg = cairo.LinearGradient(ex - 22, ey - 36, ex + 18, ey + 24)
    pg.add_color_stop_rgba(0.0, 0.96, 0.22, 0.12, 0.98 * a)
    pg.add_color_stop_rgba(1.0, 0.72, 0.08, 0.04, 0.98 * a)
    ctx.set_source(pg)
    # P vertical stem
    ctx.rectangle(ex - 22, ey - 34, 12, 58)
    ctx.fill()
    # P loop
    ctx.arc(ex - 10, ey - 18, 16, -math.pi / 2.0, math.pi / 2.0)
    ctx.line_to(ex - 10, ey - 2)
    ctx.arc_negative(ex - 10, ey - 18, 6, math.pi / 2.0, -math.pi / 2.0)
    ctx.close_path()
    ctx.fill()

    # Perspective S bands (Yellow, Green, Cyan)
    # Band 1: Yellow
    ctx.set_source_rgba(1.0, 0.76, 0.05, 0.95 * a)
    ctx.move_to(ex - 26, ey + 18)
    ctx.curve_to(ex - 5, ey + 14, ex + 15, ey + 22, ex + 32, ey + 18)
    ctx.line_to(ex + 30, ey + 23)
    ctx.curve_to(ex + 15, ey + 27, ex - 5, ey + 19, ex - 26, ey + 23)
    ctx.close_path()
    ctx.fill()

    # Band 2: Green
    ctx.set_source_rgba(0.0, 0.68, 0.42, 0.95 * a)
    ctx.move_to(ex - 26, ey + 24)
    ctx.curve_to(ex - 5, ey + 20, ex + 15, ey + 28, ex + 30, ey + 24)
    ctx.line_to(ex + 28, ey + 29)
    ctx.curve_to(ex + 15, ey + 33, ex - 5, ey + 25, ex - 26, ey + 29)
    ctx.close_path()
    ctx.fill()

    # Band 3: Cyan
    ctx.set_source_rgba(0.0, 0.62, 0.92, 0.95 * a)
    ctx.move_to(ex - 26, ey + 30)
    ctx.curve_to(ex - 5, ey + 26, ex + 15, ey + 34, ex + 28, ey + 30)
    ctx.line_to(ex + 26, ey + 35)
    ctx.curve_to(ex + 15, ey + 39, ex - 5, ey + 31, ex - 26, ey + 35)
    ctx.close_path()
    ctx.fill()
    ctx.restore()

    # "PlayStation" -- Chrome gradient lettering
    ctx.select_font_face(LOGO_FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(88.0)
    top = LOGO_CY - L['text_h']
    tg = cairo.LinearGradient(0, top, 0, LOGO_CY)
    tg.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, a)
    tg.add_color_stop_rgba(0.45, 0.82, 0.90, 1.0, a)
    tg.add_color_stop_rgba(0.55, 0.32, 0.44, 0.65, a)
    tg.add_color_stop_rgba(1.0, 0.12, 0.20, 0.38, a)
    ctx.move_to(L['text_x'], LOGO_CY)
    ctx.text_path("PlayStation")
    ctx.set_source(tg)
    ctx.fill_preserve()
    ctx.set_line_width(1.4)
    ctx.set_source_rgba(0.85, 0.94, 1.0, 0.55 * a)
    ctx.stroke()

    # Sheen sweep across "PlayStation"
    if 0.0 < sheen_p < 1.0:
        ctx.save()
        ctx.move_to(L['text_x'], LOGO_CY)
        ctx.text_path("PlayStation")
        ctx.clip()
        sx = L['text_x'] - 120.0 + sheen_p * (L['text_w'] + 240.0)
        sg = cairo.LinearGradient(sx - 60.0, 0, sx + 60.0, 0)
        sg.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.0)
        sg.add_color_stop_rgba(0.5, 1.0, 1.0, 1.0, 0.85 * a * math.sin(sheen_p * math.pi))
        sg.add_color_stop_rgba(1.0, 1.0, 1.0, 1.0, 0.0)
        ctx.set_source(sg)
        ctx.paint()
        ctx.restore()

    # "2" -- Authentic PS2 Electric Blue gradient lettering
    ctx.select_font_face(LOGO_FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(108.0)
    top2 = LOGO_CY - L['badge_h']
    bg = cairo.LinearGradient(0, top2, 0, LOGO_CY)
    bg.add_color_stop_rgba(0.0, 0.25, 0.95, 1.0, a)
    bg.add_color_stop_rgba(0.35, 0.05, 0.68, 1.0, a)
    bg.add_color_stop_rgba(0.70, 0.05, 0.38, 0.95, a)
    bg.add_color_stop_rgba(1.0, 0.02, 0.12, 0.55, a)
    ctx.move_to(L['badge_x'], LOGO_CY)
    ctx.text_path("2")
    ctx.set_source(bg)
    ctx.fill_preserve()
    ctx.set_line_width(2.0)
    ctx.set_source_rgba(0.45, 0.88, 1.0, 0.90 * a)
    ctx.stroke()
    ctx.restore()

    # Subtitle, divider and system line (not scaled -- they settle by fading)
    ctx.select_font_face(SANS_FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(19.0)
    sub = "XFCE 4.20 DESKTOP ENVIRONMENT"
    sw = spaced_width(ctx, sub, 8.0)
    spaced_text(ctx, sub, WIDTH / 2.0 - sw / 2.0, LOGO_CY + 68.0, 8.0)
    ctx.set_source_rgba(0.66, 0.76, 0.90, 0.92 * a)
    ctx.fill()

    dg = cairo.LinearGradient(WIDTH / 2.0 - 320.0, 0, WIDTH / 2.0 + 320.0, 0)
    dg.add_color_stop_rgba(0.0, 0.35, 0.7, 1.0, 0.0)
    dg.add_color_stop_rgba(0.5, 0.45, 0.78, 1.0, 0.85 * a)
    dg.add_color_stop_rgba(1.0, 0.35, 0.7, 1.0, 0.0)
    ctx.set_source(dg)
    ctx.rectangle(WIDTH / 2.0 - 320.0, LOGO_CY + 96.0, 640.0, 1.5)
    ctx.fill()

    ctx.select_font_face(MONO_FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(13.0)
    os_text = "ENDEAVOUROS LINUX • DELL LATITUDE 7490"
    ext = ctx.text_extents(os_text)
    ctx.move_to(WIDTH / 2.0 - ext.x_advance / 2.0, LOGO_CY + 128.0)
    ctx.set_source_rgba(0.72, 0.80, 0.90, 0.85 * a)
    ctx.show_text(os_text)

    # Corner HUD
    ctx.set_font_size(11.0)
    ctx.set_source_rgba(0.55, 0.63, 0.74, 0.55 * a)
    for text, x_right, y in (("BIOS 2.20 // KABY LAKE-R", False, 48),
                             ("SYSTEM MEMORY: 24 GB DUAL-CH", True, 48),
                             ("ENDEAVOUROS // ARCH LINUX", False, HEIGHT - 40),
                             ("DISPLAY: eDP-1 1080p 60Hz", True, HEIGHT - 40)):
        w = ctx.text_extents(text).x_advance
        ctx.move_to(WIDTH - 48 - w if x_right else 48, y)
        ctx.show_text(text)
    return L


def draw_logo_scene(ctx, t):
    draw_logo_background(ctx)
    a = smootherstep(*T_LOGO_IN, t)
    scale = lerp(1.05, 1.0, smootherstep(T_LOGO_IN[0], T_LOGO_IN[1] + 0.4, t))
    sheen = clamp((t - T_SHEEN[0]) / (T_SHEEN[1] - T_SHEEN[0]))
    if a > 0.0:
        draw_logo(ctx, a, scale, sheen if t < T_SHEEN[1] else 1.0)
    haze = 1.0 - smoothstep(*T_LOGO_DISSOLVE, t)
    if haze > 0.0:
        ctx.set_source_rgba(FOG_WHITE[0], FOG_WHITE[1], FOG_WHITE[2], haze)
        ctx.paint()


# -----------------------------------------------------------------------------
# Frame compositor
# -----------------------------------------------------------------------------
def render_frame_surface(frame_idx, scale=1):
    if cairo is None:
        raise RuntimeError("pycairo is required to render video frames.")
    # Everything is settled by T_STATIC; freezing t keeps the tail pixel-identical.
    t = min(frame_idx / float(FPS), T_STATIC)

    surface = cairo.ImageSurface(cairo.FORMAT_RGB24, int(WIDTH * scale), int(HEIGHT * scale))
    ctx = cairo.Context(surface)
    if scale != 1:
        ctx.scale(scale, scale)
    ctx.set_source_rgb(0, 0, 0)
    ctx.paint()

    if t < T_INTRO_FADE[1]:
        a = 1.0 - smoothstep(*T_INTRO_FADE, t)
        ctx.push_group()
        draw_intro(ctx, t)
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(a)

    if T_TOWER_START <= t < T_LOGO_DISSOLVE[0]:
        a = smoothstep(*T_TOWER_FADE_IN, t)
        ctx.push_group()
        draw_towers(ctx, t)
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(a)

    if t >= T_LOGO_DISSOLVE[0]:
        draw_logo_scene(ctx, t)

    surface.flush()
    return surface


def render_single_frame(frame_idx):
    return bytes(render_frame_surface(frame_idx, scale=1).get_data())


def export_greeter_assets():
    """Write the 4K (3840x2160) final frame as the SDDM & XFCE background plus the matching layout."""
    os.makedirs(THEME_DIR, exist_ok=True)
    scale_4k = BG_WIDTH / float(WIDTH)  # 2.0 -> 3840x2160
    surf = render_frame_surface(TOTAL_FRAMES - 1, scale=scale_4k)
    surf.write_to_png(GREETER_BG)
    L = logo_layout(cairo.Context(cairo.ImageSurface(cairo.FORMAT_RGB24, 8, 8)))
    with open(os.path.join(THEME_DIR, "theme.conf"), "w") as f:
        f.write("[General]\n")
        f.write("background=background.png\n")
        f.write("user=ebaymlay\n")
        f.write(f"emblemX={L['emblem_x']:.1f}\n")
        f.write(f"emblemY={L['emblem_y']:.1f}\n")
        f.write(f"panelTop={PANEL_TOP}\n")
    print(f"[✓] 4K Greeter & Desktop background ({BG_WIDTH}x{BG_HEIGHT}): {GREETER_BG}")


def build_authentic_ps2_audio():
    """Extract and master the genuine PS2 BIOS audio (intro + crystal towers + PS2 chime) into AUDIO_WAV."""
    import wave
    import numpy as np

    if not os.path.exists(ORIG_SOURCE_MP4):
        from generate_audio import generate_ps2_soundtrack
        generate_ps2_soundtrack(AUDIO_WAV)
        return

    sr = 48000
    raw = subprocess.check_output([
        "ffmpeg", "-v", "error", "-i", ORIG_SOURCE_MP4,
        "-f", "f32le", "-ac", "2", "-ar", str(sr), "-"
    ])
    stereo = np.frombuffer(raw, dtype=np.float32).reshape(-1, 2)

    target_samples = int(DURATION * sr)
    out = np.zeros((target_samples, 2), dtype=np.float32)

    # Part 1: 0.35s .. 8.85s (8.50s) from original PS2 startup (Sony Computer Entertainment + Crystal Towers dive)
    s0 = int(0.35 * sr)
    dur1 = int(8.50 * sr)
    seg1 = stereo[s0:s0 + dur1].copy()
    # Smooth fade-in (50ms) and fade-out over the last 1.1s (7.4s .. 8.5s)
    fi = int(0.05 * sr)
    seg1[:fi] *= np.linspace(0.0, 1.0, fi, dtype=np.float32)[:, None]
    fo = int(1.10 * sr)
    seg1[-fo:] *= np.linspace(1.0, 0.0, fo, dtype=np.float32)[:, None]
    out[:len(seg1)] += seg1

    # Part 2: 14.05s .. 16.45s (2.40s) authentic PlayStation 2 logo chime layered at t = 7.15s
    c0 = int(14.05 * sr)
    cdur = int(2.40 * sr)
    chime = stereo[c0:c0 + cdur].copy()
    cfi = int(0.08 * sr)
    chime[:cfi] *= np.linspace(0.0, 1.0, cfi, dtype=np.float32)[:, None]
    cfo = int(0.45 * sr)
    chime[-cfo:] *= np.linspace(1.0, 0.0, cfo, dtype=np.float32)[:, None]

    start_chime = int(7.15 * sr)
    end_chime = min(target_samples, start_chime + len(chime))
    out[start_chime:end_chime] += chime[:end_chime - start_chime] * 0.95

    # Soft master to peak = 0.70 (matches test_audio_soundtrack_valid 0.65..0.75)
    peak = float(np.max(np.abs(out))) or 1.0
    out = out * (0.70 / peak)
    pcm16 = np.clip(out * 32767.0, -32768, 32767).astype(np.int16)

    with wave.open(AUDIO_WAV, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm16.tobytes())
    print(f"[✓] Authentic PS2 soundtrack mastered: {AUDIO_WAV} ({DURATION}s, peak=0.70)")


# -----------------------------------------------------------------------------
# Main orchestration: combine original PS2 video + 4K XFCE background via FFmpeg
# -----------------------------------------------------------------------------
def main():
    print("=" * 68)
    print("  PS2 XFCE 4.20 STARTUP VIDEO GENERATOR (ORIGINAL PS2 + 4K XFCE BG)")
    print("=" * 68)
    print(f"[*] Target: {WIDTH}x{HEIGHT} @ {FPS} FPS ({TOTAL_FRAMES} frames, {DURATION}s)")
    t_start = time.time()

    export_greeter_assets()
    build_authentic_ps2_audio()

    if not os.path.exists(ORIG_SOURCE_MP4):
        sys.exit(f"[!] Missing original PS2 source video: {ORIG_SOURCE_MP4}")

    # Cross-fade from original PS2 video (0.35s..8.75s = 8.40s) into the 4K background.png
    # over 1.0s (7.40s..8.40s), holding the static final frame from 8.40s..9.60s (1.20s).
    filter_complex = (
        f"[0:v]trim=start=0.35:duration=8.40,setpts=PTS-STARTPTS,"
        f"fps={FPS},crop=1340:980:50:50,"
        f"scale={WIDTH}:{HEIGHT}:flags=lanczos,setsar=1,format=yuv420p[ps2];"
        f"[1:v]scale={WIDTH}:{HEIGHT}:flags=lanczos,loop=loop=135:size=1:start=0,"
        f"fps={FPS},setsar=1,format=yuv420p[bg];"
        f"[ps2][bg]xfade=transition=fade:duration=1.00:offset=7.40,"
        f"scale=out_color_matrix=bt709:out_range=tv,format=yuv420p[v]"
    )

    ffmpeg_cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", ORIG_SOURCE_MP4,
        "-i", GREETER_BG,
        "-i", AUDIO_WAV,
        "-filter_complex", filter_complex,
        "-map", "[v]", "-map", "2:a",
        "-frames:v", str(TOTAL_FRAMES),
        "-c:v", "libx264", "-preset", "slow", "-crf", "15", "-tune", "film",
        "-g", "60", "-profile:v", "high",
        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
        "-color_range", "tv",
        "-c:a", "aac", "-b:a", "256k", "-ar", "48000",
        "-shortest", "-movflags", "+faststart",
        FINAL_MP4,
    ]
    print("[*] Encoding master startup video with Lanczos scaling & smooth xfade...")
    subprocess.run(ffmpeg_cmd, check=True)

    size_mb = os.path.getsize(FINAL_MP4) / (1024.0 * 1024.0)
    print(f"[✓] {FINAL_MP4} ({size_mb:.2f} MB, {time.time() - t_start:.1f}s)")


if __name__ == "__main__":
    main()
