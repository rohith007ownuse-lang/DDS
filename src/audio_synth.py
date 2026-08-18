"""
audio_synth.py
Generates alert tone .wav files procedurally - pure Python stdlib
(wave + math), no external audio assets or extra dependencies needed.
"""

import os
import wave
import math
import struct


def generate_tone_wav(path, pattern, sample_rate=44100, volume=0.6):
    samples = []
    fade_samples = max(1, int(sample_rate * 0.005))

    for freq, duration_ms in pattern:
        n = int(sample_rate * duration_ms / 1000)
        for i in range(n):
            if freq <= 0:
                samples.append(0.0)
                continue
            t = i / sample_rate
            s = math.sin(2 * math.pi * freq * t)
            if i < fade_samples:
                s *= i / fade_samples
            elif i > n - fade_samples:
                s *= (n - i) / fade_samples
            samples.append(s * volume)

    out_dir = os.path.dirname(path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        packed = b"".join(
            struct.pack("<h", int(max(-1.0, min(1.0, s)) * 32767))
            for s in samples
        )
        wf.writeframes(packed)

    return path
