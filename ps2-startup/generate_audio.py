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
    # 1. Deep Sub-Bass Ocean Rumble (0s - 11s)
    # -------------------------------------------------------------
    sub_freq = 48.0
    sub_env = np.clip(t / 2.5, 0.0, 1.0) * np.exp(-np.maximum(0.0, t - 6.0) / 4.0)
    # Modulation for oceanic breathing feel
    sub_lfo = 0.85 + 0.15 * np.sin(2 * np.pi * 0.3 * t)
    sub_wave = np.sin(2 * np.pi * sub_freq * t) + 0.35 * np.sin(2 * np.pi * (sub_freq * 2) * t)
    left += 0.45 * sub_wave * sub_env * sub_lfo
    right += 0.45 * sub_wave * sub_env * sub_lfo

    # -------------------------------------------------------------
    # 2. Atmospheric Organ / Synth Pad Cluster (0.5s - 11.5s)
    # Suspended D-minor / ethereal cluster: D2, A2, D3, F3, A3, D4
    # -------------------------------------------------------------
    pad_notes = [
        (73.42, 0.35),   # D2
        (110.00, 0.30),  # A2
        (146.83, 0.28),  # D3
        (174.61, 0.22),  # F3
        (220.00, 0.18),  # A3
        (293.66, 0.14),  # D4
    ]
    
    pad_env = np.clip((t - 0.4) / 2.2, 0.0, 1.0) * np.exp(-np.maximum(0.0, t - 6.5) / 3.8)
    
    for freq, amp in pad_notes:
        # Slight stereo detune (chorus effect)
        detune = 0.55
        # Soft harmonics (triangle/warm sine mix)
        w_l = np.sin(2 * np.pi * (freq - detune) * t) + 0.18 * np.sin(2 * np.pi * (freq * 2 - detune) * t)
        w_r = np.sin(2 * np.pi * (freq + detune) * t) + 0.18 * np.sin(2 * np.pi * (freq * 2 + detune) * t)
        left += amp * w_l * pad_env
        right += amp * w_r * pad_env

    # -------------------------------------------------------------
    # 3. Dynamic Flying Swoosh (3.2s - 8.0s)
    # Bandpass swept noise simulating flying through crystal monoliths
    # -------------------------------------------------------------
    noise = np.random.normal(0, 0.15, TOTAL_SAMPLES)
    swoosh_env = np.exp(-((t - 6.2) ** 2) / 1.5)
    # Sweeping resonant band
    sweep_phase = np.clip((t - 3.2) / 3.5, 0.0, 1.0)
    cutoff = 200.0 + 1600.0 * (sweep_phase ** 2)
    # Simple swept resonator
    carrier = np.sin(2 * np.pi * cutoff * t)
    swoosh_sig = noise * carrier * swoosh_env * 1.8
    # Dynamic panning from left to center/right
    pan = np.clip((t - 4.0) / 3.0, 0.0, 1.0)
    left += swoosh_sig * (1.2 - 0.4 * pan)
    right += swoosh_sig * (0.8 + 0.4 * pan)

    # -------------------------------------------------------------
    # 4. Celestial Crystal Chimes / Bell Harmonics (6.8s - 12.0s)
    # The iconic PS2 high-frequency crystalline shimmer when logo appears
    # -------------------------------------------------------------
    chime_start = 6.8
    chime_mask = t >= chime_start
    t_chime = np.maximum(0.0, t - chime_start)
    chime_env = np.exp(-t_chime / 2.2) * chime_mask
    
    # Bell frequencies (high shimmering harmonics)
    bell_freqs = [
        (1318.5, 0.28, 0.7),  # E6
        (1975.5, 0.22, 0.3),  # B6
        (2637.0, 0.18, 0.8),  # E7
        (3322.4, 0.12, 0.2),  # G#7
        (3951.0, 0.09, 0.5),  # B7
    ]
    
    for f, b_amp, b_pan in bell_freqs:
        # Subtle vibrato shimmer
        vibrato = 1.0 + 0.003 * np.sin(2 * np.pi * 5.2 * t_chime)
        bell_wave = np.sin(2 * np.pi * f * vibrato * t_chime) * np.exp(-t_chime / 1.8)
        left += b_amp * (1.0 - b_pan * 0.5) * bell_wave * chime_env
        right += b_amp * (0.5 + b_pan * 0.5) * bell_wave * chime_env

    # -------------------------------------------------------------
    # 5. Warm Golden Confirmation Swell (7.0s - 12.0s)
    # -------------------------------------------------------------
    swell_t = np.maximum(0.0, t - 7.0)
    swell_env = (1.0 - np.exp(-swell_t / 0.8)) * np.exp(-swell_t / 3.5) * (t >= 7.0)
    warm_tone = np.sin(2 * np.pi * 146.83 * t) + 0.4 * np.sin(2 * np.pi * 220.0 * t)
    left += 0.22 * warm_tone * swell_env
    right += 0.22 * warm_tone * swell_env

    # -------------------------------------------------------------
    # 6. Cavernous Cathedral Reverb (Multi-tap Delay Network)
    # -------------------------------------------------------------
    delays_ms = [47, 83, 137, 191, 257, 349, 463, 617, 853]
    decays =    [0.72, 0.65, 0.58, 0.50, 0.43, 0.36, 0.28, 0.20, 0.14]
    
    rev_l = np.zeros(TOTAL_SAMPLES, dtype=np.float64)
    rev_r = np.zeros(TOTAL_SAMPLES, dtype=np.float64)
    
    for d_ms, dec in zip(delays_ms, decays):
        d_samples = int((d_ms / 1000.0) * SAMPLE_RATE)
        if d_samples < TOTAL_SAMPLES:
            rev_l[d_samples:] += left[:-d_samples] * dec * 0.22
            rev_r[d_samples:] += right[:-d_samples] * dec * 0.22

    # Mix dry + wet
    left = 0.78 * left + 0.38 * rev_l
    right = 0.78 * right + 0.38 * rev_r

    # Soft tape saturation / limiter using tanh
    left = np.tanh(left * 1.15)
    right = np.tanh(right * 1.15)

    # Master gain normalization to -1.5 dBFS
    max_val = max(np.max(np.abs(left)), np.max(np.abs(right)), 1e-6)
    target_peak = 0.88  # -1.1 dBFS
    gain = target_peak / max_val
    left = left * gain
    right = right * gain

    # Master fade out at the very end to prevent pop
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
    print(f"[+] Successfully generated PS2 soundtrack: {output_path} ({DURATION}s, {SAMPLE_RATE}Hz stereo)")

if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "ps2_startup.wav"
    generate_ps2_soundtrack(out)
