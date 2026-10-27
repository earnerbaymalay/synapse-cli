#!/usr/bin/env python3
"""
PS2-Inspired Startup Sound Generator
Generates an authentic, studio-grade 48kHz stereo WAV recreating the iconic
PlayStation 2 boot ambiance:
1. Deep sub-bass ocean rumble
2. Atmospheric suspended organ/synth pad cluster with lush chorus
3. Resonant swept-filter swoosh (flying through crystal monoliths)
4. Shimmering celestial bell/crystal chimes (logo reveal)
5. Cavernous spatial reverb
"""

import math
import wave
import numpy as np

SAMPLE_RATE = 48000
DURATION = 12.0  # seconds
TOTAL_SAMPLES = int(SAMPLE_RATE * DURATION)

def generate_ps2_soundtrack(output_path):
    t = np.linspace(0, DURATION, TOTAL_SAMPLES, endpoint=False)
    
    left = np.zeros(TOTAL_SAMPLES, dtype=np.float64)
    right = np.zeros(TOTAL_SAMPLES, dtype=np.float64)

    # -------------------------------------------------------------
    # 1. Gentle Deep Sub-Bass Oceanic Resonance (0s - 11.5s)
    # Warm, deep 38Hz ocean floor breathing resonance
    # -------------------------------------------------------------
    sub_freq = 38.0
    sub_env = np.clip(t / 3.0, 0.0, 1.0) * np.exp(-np.maximum(0.0, t - 6.2) / 4.2)
    # Gentle low-frequency oceanic breathing modulation
    sub_lfo = 0.88 + 0.12 * np.sin(2 * np.pi * 0.22 * t)
    sub_wave = np.sin(2 * np.pi * sub_freq * t) + 0.18 * np.sin(2 * np.pi * (sub_freq * 2) * t)
    left += 0.38 * sub_wave * sub_env * sub_lfo
    right += 0.38 * sub_wave * sub_env * sub_lfo

    # -------------------------------------------------------------
    # 2. Warm Diffused Ethereal Pad Chord (0.4s - 11.8s)
    # Suspended D-minor 9th ethereal cluster: D2, A2, D3, F3, A3, C4, D4
    # Warm rounded sine waveforms with gentle stereo chorus
    # -------------------------------------------------------------
    pad_notes = [
        (73.42, 0.32),   # D2 - deep foundation
        (110.00, 0.28),  # A2 - fifth warmth
        (146.83, 0.24),  # D3 - octave core
        (174.61, 0.18),  # F3 - minor third emotional texture
        (220.00, 0.14),  # A3 - celestial tenth
        (261.63, 0.10),  # C4 - suspended seventh
        (293.66, 0.07),  # D4 - gentle high shimmer
    ]
    
    pad_env = np.clip((t - 0.3) / 2.6, 0.0, 1.0) * np.exp(-np.maximum(0.0, t - 6.8) / 4.0)
    
    for freq, amp in pad_notes:
        detune = 0.42
        # Soft harmonics (pure warm tones with gentle second harmonic)
        w_l = np.sin(2 * np.pi * (freq - detune) * t) + 0.08 * np.sin(2 * np.pi * (freq * 2 - detune) * t)
        w_r = np.sin(2 * np.pi * (freq + detune) * t) + 0.08 * np.sin(2 * np.pi * (freq * 2 + detune) * t)
        left += amp * w_l * pad_env
        right += amp * w_r * pad_env

    # -------------------------------------------------------------
    # 3. Dynamic Flying Swoosh (3.2s - 7.6s)
    # Authentic analog 2-pole resonant bandpass sweep over warm brown noise
    # -------------------------------------------------------------
    np.random.seed(1337)
    white = np.random.normal(0, 0.06, TOTAL_SAMPLES)
    brown = np.zeros(TOTAL_SAMPLES, dtype=np.float64)
    b = 0.0
    for i in range(TOTAL_SAMPLES):
        b = 0.95 * b + white[i]
        brown[i] = b

    swoosh_env = np.exp(-((t - 5.6) ** 2) / 1.6)
    sweep_p = np.clip((t - 3.2) / 3.2, 0.0, 1.0)
    f_sweep = 200.0 + 680.0 * (sweep_p ** 1.5)

    y_swoosh = np.zeros(TOTAL_SAMPLES, dtype=np.float64)
    y1, y2 = 0.0, 0.0
    r_res = 0.86
    cos_thetas = np.cos(2 * np.pi * f_sweep / SAMPLE_RATE)
    for i in range(TOTAL_SAMPLES):
        out = (1.0 - r_res) * brown[i] + 2.0 * r_res * cos_thetas[i] * y1 - (r_res * r_res) * y2
        y2, y1 = y1, out
        y_swoosh[i] = out

    swoosh_sig = y_swoosh * swoosh_env * 0.45
    pan = np.clip((t - 3.8) / 3.0, 0.0, 1.0)
    left += swoosh_sig * (1.1 - 0.3 * pan)
    right += swoosh_sig * (0.8 + 0.3 * pan)

    # -------------------------------------------------------------
    # 4. Soft Celestial Bells / Crystal Chimes (6.8s - 12.0s)
    # Iconic PlayStation 2 logo reveal chimes: harmonious D-major celestial series
    # (D5, A5, D6, F#6, A6, D7) with soft exponential attack and natural acoustic decay
    # -------------------------------------------------------------
    chime_start = 6.8
    chime_mask = t >= chime_start
    t_chime = np.maximum(0.0, t - chime_start)
    # Soft exponential attack (eliminates harsh transient clicks)
    chime_attack = (1.0 - np.exp(-t_chime / 0.045)) * chime_mask

    bell_freqs = [
        (587.33, 0.22, 0.50, 2.5),  # D5 - warm resonant body
        (880.00, 0.18, 0.40, 2.3),  # A5 - pure fifth warmth
        (1174.66, 0.15, 0.65, 2.1), # D6 - crystal octave
        (1479.98, 0.10, 0.30, 1.9), # F#6 - sweet major third shimmer
        (1760.00, 0.06, 0.70, 1.6), # A6 - soft starlight shimmer
        (2349.32, 0.025, 0.50, 1.3),# D7 - delicate celestial air (softly attenuated)
    ]

    for f, b_amp, b_pan, b_decay in bell_freqs:
        # Subtle organic pitch vibrato shimmer
        vibrato = 1.0 + 0.002 * np.sin(2 * np.pi * 4.8 * t_chime)
        bell_decay_env = np.exp(-t_chime / b_decay)
        bell_wave = np.sin(2 * np.pi * f * vibrato * t_chime) * chime_attack * bell_decay_env
        left += b_amp * (1.0 - b_pan * 0.4) * bell_wave
        right += b_amp * (0.6 + b_pan * 0.4) * bell_wave

    # -------------------------------------------------------------
    # 5. Warm Golden Confirmation Swell (7.0s - 12.0s)
    # -------------------------------------------------------------
    swell_t = np.maximum(0.0, t - 7.0)
    swell_env = (1.0 - np.exp(-swell_t / 0.9)) * np.exp(-swell_t / 3.8) * (t >= 7.0)
    warm_tone = np.sin(2 * np.pi * 146.83 * t) + 0.35 * np.sin(2 * np.pi * 220.0 * t)
    left += 0.18 * warm_tone * swell_env
    right += 0.18 * warm_tone * swell_env

    # -------------------------------------------------------------
    # 6. Warm Cavernous Multi-Tap Reverb with High-Damping
    # -------------------------------------------------------------
    delays_ms = [53, 97, 149, 211, 281, 383, 509, 673, 911]
    decays =    [0.68, 0.60, 0.52, 0.44, 0.36, 0.28, 0.20, 0.14, 0.08]

    rev_l = np.zeros(TOTAL_SAMPLES, dtype=np.float64)
    rev_r = np.zeros(TOTAL_SAMPLES, dtype=np.float64)

    for d_ms, dec in zip(delays_ms, decays):
        d_samples = int((d_ms / 1000.0) * SAMPLE_RATE)
        if d_samples < TOTAL_SAMPLES:
            rev_l[d_samples:] += left[:-d_samples] * dec * 0.18
            rev_r[d_samples:] += right[:-d_samples] * dec * 0.18

    # Damped reverb mix (gentle low-pass feel, cathedral warmth)
    left = 0.76 * left + 0.32 * rev_l
    right = 0.76 * right + 0.32 * rev_r

    # Soft, warm tape saturation
    left = np.tanh(left * 0.90)
    right = np.tanh(right * 0.90)

    # Master gain normalization: reduced peak target for soft, relaxed master (-3.1 dBFS)
    max_val = max(np.max(np.abs(left)), np.max(np.abs(right)), 1e-6)
    target_peak = 0.70  # -3.1 dBFS (softer, non-fatiguing, cinema-grade dynamic headroom)
    gain = target_peak / max_val
    left = left * gain
    right = right * gain

    # Master smooth fade out at end
    fade_len = int(0.6 * SAMPLE_RATE)
    fade_out = np.linspace(1.0, 0.0, fade_len)
    left[-fade_len:] *= fade_out
    right[-fade_len:] *= fade_out

    # Convert to 16-bit PCM
    stereo = np.column_stack((left, right))
    pcm_data = (stereo * 32767.0).astype(np.int16)
    with wave.open(output_path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm_data.tobytes())
    print(f"[+] Successfully generated refined PS2 soundtrack: {output_path} ({DURATION}s, {SAMPLE_RATE}Hz stereo, peak={target_peak:.2f})")

if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "ps2_startup.wav"
    generate_ps2_soundtrack(out)
