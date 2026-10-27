#!/usr/bin/env python3
"""
PS2-Inspired Startup Sound Generator (numpy only, 48 kHz stereo)

Cue sheet, locked to render_ps2_video.py's timeline:
  0.3 - 2.4s  Reverse swell: low sine + rising air noise, cut at the flare.
  2.4s        Flare hit: deep sub "whum" + inharmonic glass bell cluster.
  2.4 - 4.3s  High shimmer tail, decaying into the dark.
  4.1 - 9.4s  Tower drone: beating low D, breathing air, sparse distant plinks.
  8.2 - 9.5s  Rising whoosh into the whiteout.
  9.6 - 12s   Logo chord: D major add9 pad + soft bell, fading out by 12.0s.
Everything runs through a long synthetic-IR convolution reverb (stereo
decorrelated, high frequencies decaying faster) for the cavernous PS2 space.
"""

import wave

import numpy as np

SAMPLE_RATE = 48000
DURATION = 12.0
TOTAL_SAMPLES = int(SAMPLE_RATE * DURATION)


def _env(t, start, attack, decay):
    """Exponential-attack / exponential-decay envelope beginning at `start`."""
    x = np.maximum(0.0, t - start)
    return (1.0 - np.exp(-x / attack)) * np.exp(-x / decay) * (t >= start)


def _band_noise(rng, n, lo, hi):
    """Stationary band-limited noise via FFT masking with soft edges."""
    spec = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, 1.0 / SAMPLE_RATE)
    mask = 1.0 / (1.0 + (lo / np.maximum(f, 1e-3)) ** 4) / (1.0 + (f / hi) ** 4)
    out = np.fft.irfft(spec * mask, n)
    return out / (np.max(np.abs(out)) + 1e-9)


def _bell(t, start, f0, amp, decay):
    """Inharmonic bell/glass partials (modal ratios of a struck bar)."""
    x = np.maximum(0.0, t - start)
    on = t >= start
    out = np.zeros_like(t)
    for ratio, rel, dmul in ((1.0, 1.0, 1.0), (2.76, 0.5, 0.6), (5.40, 0.25, 0.4), (8.93, 0.12, 0.25)):
        out += rel * np.sin(2 * np.pi * f0 * ratio * x) * np.exp(-x / (decay * dmul))
    return amp * out * (1.0 - np.exp(-x / 0.004)) * on


def _fm_plink(t, start, f0, amp, decay):
    x = np.maximum(0.0, t - start)
    on = t >= start
    index = 2.2 * np.exp(-x / 0.25)
    sig = np.sin(2 * np.pi * f0 * x + index * np.sin(2 * np.pi * f0 * 1.4 * x))
    return amp * sig * np.exp(-x / decay) * (1.0 - np.exp(-x / 0.003)) * on


def _reverb_ir(rng, seconds, rt60, hf_rt60):
    n = int(seconds * SAMPLE_RATE)
    tt = np.arange(n) / SAMPLE_RATE
    irs = []
    for _ in range(2):
        lo = _band_noise(rng, n, 20.0, 2500.0) * np.exp(-6.9 * tt / rt60)
        hi = _band_noise(rng, n, 2500.0, 16000.0) * np.exp(-6.9 * tt / hf_rt60)
        ir = lo + 0.5 * hi
        ir[: int(0.022 * SAMPLE_RATE)] = 0.0  # pre-delay
        irs.append(ir / np.sqrt(np.sum(ir ** 2)))
    return irs


def _convolve(x, ir):
    n = len(x) + len(ir) - 1
    nfft = 1 << (n - 1).bit_length()
    y = np.fft.irfft(np.fft.rfft(x, nfft) * np.fft.rfft(ir, nfft), nfft)
    return y[: len(x)]


def generate_ps2_soundtrack(output_path):
    rng = np.random.default_rng(1337)
    t = np.arange(TOTAL_SAMPLES) / SAMPLE_RATE
    left = np.zeros(TOTAL_SAMPLES)
    right = np.zeros(TOTAL_SAMPLES)

    def add(sig, pan=0.0):
        left[:] += sig * np.sqrt(0.5 * (1.0 - pan))
        right[:] += sig * np.sqrt(0.5 * (1.0 + pan))

    # --- Act I: reverse swell into the flare ---------------------------------
    T_FLARE = 2.4
    swell = np.clip((t - 0.3) / (T_FLARE - 0.3), 0.0, 1.0) ** 3 * (t < T_FLARE)
    glide = 55.0 + 18.0 * np.clip((t - 0.3) / (T_FLARE - 0.3), 0.0, 1.0)
    phase = 2 * np.pi * np.cumsum(glide) / SAMPLE_RATE
    add(0.55 * swell * (np.sin(phase) + 0.3 * np.sin(2 * phase)))
    air_lo = _band_noise(rng, TOTAL_SAMPLES, 250.0, 1200.0)
    air_hi = _band_noise(rng, TOTAL_SAMPLES, 1500.0, 7000.0)
    add(0.22 * swell * air_lo, -0.3)
    add(0.12 * swell ** 2 * air_hi, 0.3)

    # Flare: sub "whum" with falling pitch + glass bell cluster
    x = np.maximum(0.0, t - T_FLARE)
    whum_f = 40.0 + 34.0 * np.exp(-x / 0.18)
    whum = np.sin(2 * np.pi * np.cumsum(whum_f) / SAMPLE_RATE) * _env(t, T_FLARE, 0.006, 1.1)
    add(0.75 * whum)
    add(_bell(t, T_FLARE, 587.33, 0.20, 2.6), -0.25)    # D5
    add(_bell(t, T_FLARE + 0.012, 880.0, 0.15, 2.2), 0.25)  # A5
    add(_bell(t, T_FLARE + 0.03, 1318.5, 0.08, 1.8), 0.0)   # E6

    # Shimmer tail: high cluster with slow tremolo
    shim_env = _env(t, T_FLARE, 0.15, 1.1) * (1.0 - np.clip((t - 3.8) / 0.6, 0.0, 1.0))
    for f, p in ((1760.0, -0.5), (2349.3, 0.5), (2637.0, 0.0)):
        trem = 0.7 + 0.3 * np.sin(2 * np.pi * 5.5 * t + f)
        add(0.03 * np.sin(2 * np.pi * f * t) * trem * shim_env, p)

    # --- Act II: tower drone ---------------------------------------------------
    drone_env = np.clip((t - 4.1) / 1.4, 0.0, 1.0) ** 2 * (1.0 - np.clip((t - 9.2) / 0.6, 0.0, 1.0))
    for f, a in ((36.71, 0.08), (73.42, 0.06), (110.0, 0.035), (146.83, 0.02)):
        add(a * drone_env * np.sin(2 * np.pi * (f - 0.07) * t), -0.35)
        add(a * drone_env * np.sin(2 * np.pi * (f + 0.07) * t), 0.35)
    breath = 0.6 + 0.4 * np.sin(2 * np.pi * 0.21 * t - 1.2)
    add(0.05 * drone_env * breath * _band_noise(rng, TOTAL_SAMPLES, 300.0, 1400.0), 0.15)

    # Distant metallic plinks (D minor pentatonic), alternating pan
    for i, (st, f) in enumerate(((5.05, 1174.66), (5.85, 1567.98), (6.55, 1396.91),
                                 (7.3, 1760.0), (7.95, 1174.66), (8.55, 2093.0))):
        add(_fm_plink(t, st, f, 0.04, 0.9), -0.6 if i % 2 == 0 else 0.6)

    # Rising whoosh into the whiteout (three crossfaded bands = moving filter)
    rise = np.clip((t - 8.2) / 1.3, 0.0, 1.0)
    whoosh_env = rise ** 2 * (1.0 - np.clip((t - 9.5) / 0.35, 0.0, 1.0))
    bands = (_band_noise(rng, TOTAL_SAMPLES, 200.0, 700.0),
             _band_noise(rng, TOTAL_SAMPLES, 700.0, 2200.0),
             _band_noise(rng, TOTAL_SAMPLES, 2200.0, 8000.0))
    w0 = np.clip(1.0 - rise * 2.0, 0.0, 1.0)
    w2 = np.clip(rise * 2.0 - 1.0, 0.0, 1.0)
    w1 = 1.0 - w0 - w2
    add(0.30 * whoosh_env * (w0 * bands[0] + w1 * bands[1] + 0.7 * w2 * bands[2]))

    # --- Act III: logo chord ---------------------------------------------------
    T_LOGO = 9.6
    pad_env = _env(t, T_LOGO, 0.30, 3.2)
    for f, a, p in ((146.83, 0.10, 0.0), (293.66, 0.10, -0.3), (369.99, 0.07, 0.3),
                    (440.0, 0.08, -0.2), (659.26, 0.05, 0.4), (880.0, 0.035, -0.4)):
        for det in (-0.6, 0.6):
            add(1.5 * a * pad_env * np.sin(2 * np.pi * (f + det) * t + det), p + det * 0.3)
    add(_bell(t, T_LOGO + 0.05, 1760.0, 0.06, 2.4), -0.2)
    add(_bell(t, T_LOGO + 0.25, 2637.0, 0.035, 2.0), 0.3)

    # --- Space: long convolution reverb ---------------------------------------
    ir_l, ir_r = _reverb_ir(rng, 4.0, rt60=3.6, hf_rt60=1.6)
    mono = 0.5 * (left + right)
    wet_l = _convolve(left * 0.7 + mono * 0.3, ir_l)
    wet_r = _convolve(right * 0.7 + mono * 0.3, ir_r)
    left = 0.72 * left + 0.55 * wet_l
    right = 0.72 * right + 0.55 * wet_r

    # Gentle saturation, normalise to -3.1 dBFS, fade to silence by 12.0s
    left = np.tanh(left * 1.1)
    right = np.tanh(right * 1.1)
    peak = max(np.max(np.abs(left)), np.max(np.abs(right)), 1e-6)
    target_peak = 0.70
    left *= target_peak / peak
    right *= target_peak / peak

    fade = np.clip((DURATION - t) / 1.0, 0.0, 1.0) ** 2
    fade_in = np.clip(t / 0.01, 0.0, 1.0)
    left *= fade * fade_in
    right *= fade * fade_in

    pcm = (np.column_stack((left, right)) * 32767.0).astype(np.int16)
    with wave.open(output_path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm.tobytes())
    print(f"[+] Generated PS2 soundtrack: {output_path} ({DURATION}s, {SAMPLE_RATE}Hz stereo, peak={target_peak:.2f})")


if __name__ == "__main__":
    import sys
    generate_ps2_soundtrack(sys.argv[1] if len(sys.argv) > 1 else "ps2_startup.wav")
