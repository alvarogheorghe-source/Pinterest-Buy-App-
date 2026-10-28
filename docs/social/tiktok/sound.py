"""Eigener Chiptune-Sound für die Malipin-TikToks (150 BPM, 1 Schlag = 0,4 s) + Effekte.

Alles selbst erzeugt (Sinus, Rechteck, Rauschen) -> keine fremden Rechte.
Aufruf: python3 sound.py <ordner>  -> sound-1.wav, sound-2.wav, sound-3.wav
"""

import sys
import wave

import numpy as np

SR = 44100
BEAT = 0.4
BAR = BEAT * 4
rng = np.random.default_rng(7)

NOTE = {n: 440 * 2 ** ((i - 9) / 12) for i, n in enumerate(
    ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"])}


def hz(name, octave):
    return NOTE[name] * 2 ** (octave - 4)


# Akkorde pro Takt: C – G – Am – F (fröhlich, eingängig)
CHORDS = [("C", ["C", "E", "G"]), ("G", ["G", "B", "D"]), ("A", ["A", "C", "E"]), ("F", ["F", "A", "C"])]


def env(n, attack=0.004, decay=None):
    t = np.arange(n) / SR
    e = np.minimum(1, t / attack) if attack else np.ones(n)
    if decay:
        e = e * np.exp(-t * decay)
    return e


def square(freq, dur, duty=0.5, decay=6.0, vol=1.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    w = np.where((t * freq) % 1 < duty, 1.0, -1.0)
    return w * env(n, decay=decay) * vol


def lowpass(x, alpha):
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):            # einfacher Tiefpass (Einpol)
        acc += alpha * (v - acc)
        y[i] = acc
    return y


def noise(dur):
    return rng.uniform(-1, 1, int(dur * SR))


def kick(dur=0.28, low=48, high=160, k=28):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = low + (high - low) * np.exp(-t * k)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 11)


def snare():
    n = int(0.2 * SR)
    t = np.arange(n) / SR
    return (noise(0.2) * 0.7 + np.sin(2 * np.pi * 190 * t) * 0.5) * np.exp(-t * 22)


def hat(dur=0.05):
    x = noise(dur)
    x = x - lowpass(x, 0.35)             # nur die Höhen
    return x * env(len(x), attack=0.001, decay=70)


# ---------- Effekte ----------
def boom():
    x = kick(0.9, low=35, high=120, k=9) * 1.2
    x[: int(0.25 * SR)] += lowpass(noise(0.25), 0.08) * np.exp(-np.arange(int(0.25 * SR)) / SR * 14) * 0.8
    return x


def pop():
    n = int(0.09 * SR)
    t = np.arange(n) / SR
    f = 500 + 900 * (t / t[-1])
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 35) * 0.7


def whoosh(dur=0.3):
    x = lowpass(noise(dur), 0.12)
    n = len(x)
    return x * np.sin(np.linspace(0, np.pi, n)) ** 2 * 1.4


def riser(dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 220 + 1100 * (t / dur) ** 2
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.25
    hiss = (noise(dur) - lowpass(noise(dur), 0.2)) * 0.35
    return (tone + hiss) * (t / dur) ** 1.5


def ding(f1=1318.5, f2=1975.5, dur=0.7):
    n = int(dur * SR)
    t = np.arange(n) / SR
    return (np.sin(2 * np.pi * f1 * t) + 0.6 * np.sin(2 * np.pi * f2 * t)) * np.exp(-t * 6) * 0.45


def shutter():
    x = np.zeros(int(0.16 * SR))
    for start in (0, 0.07):
        c = noise(0.025) * env(int(0.025 * SR), attack=0.0005, decay=160)
        i = int(start * SR)
        x[i:i + len(c)] += c
    return x * 1.1


def kaching():
    x = np.zeros(int(0.9 * SR))
    for start, f in ((0, 2093.0), (0.09, 2637.0)):
        d = ding(f, f * 1.5, 0.8)
        i = int(start * SR)
        x[i:i + len(d)] += d[: len(x) - i]
    return x


def blip(freq=1760):
    return square(freq, 0.05, duty=0.25, decay=40, vol=0.25)


# ---------- Musik ----------
def music(length, drums_from, drums_to, light_after):
    out = np.zeros(int(length * SR) + SR)

    def put(sig, at, vol=1.0):
        i = int(at * SR)
        j = min(len(out), i + len(sig))
        out[i:j] += sig[: j - i] * vol

    beats = int(length / BEAT)
    for b in range(beats):
        at = b * BEAT
        bar = int(at // BAR)
        root, tones = CHORDS[bar % 4]
        full = drums_from <= at < drums_to
        light = at >= light_after
        # Bass: Achtel auf dem Grundton
        for half in (0, 1):
            put(square(hz(root, 2), BEAT / 2 * 0.9, duty=0.5, decay=5, vol=0.28), at + half * BEAT / 2)
        # Arpeggio: Sechzehntel aus den Akkordtönen
        for s in range(4):
            note = tones[(b * 4 + s) % 3]
            put(square(hz(note, 5), BEAT / 4 * 0.8, duty=0.25, decay=14, vol=0.09), at + s * BEAT / 4)
        # Schlagzeug
        put(hat(), at + BEAT / 2, 0.35)
        if full or light:
            put(kick(), at, 0.95 if full else 0.6)
            if b % 2 == 1:
                put(snare(), at, 0.45 if full else 0.3)
            if full:
                put(hat(0.03), at + BEAT / 4, 0.2)
                put(hat(0.03), at + 3 * BEAT / 4, 0.2)
    # Melodie in der Endkarte (Mali-Thema)
    melody = [("E", 5), ("G", 5), ("C", 6), ("G", 5), ("A", 5), ("G", 5), ("E", 5), ("D", 5)]
    for k, (n_, o) in enumerate(melody):
        put(square(hz(n_, o), BEAT * 0.45, duty=0.5, decay=5, vol=0.14), light_after + k * BEAT / 2)
    return out


def render(length, events, drums_from, drums_to, light_after, path):
    # Musik weicher (Tiefpass ~3 kHz), damit die Rechteckwellen am Handy nicht kratzen
    out = lowpass(music(length, drums_from, drums_to, light_after), 0.33) * 0.75

    def put(sig, at, vol=1.0):
        i = int(at * SR)
        j = min(len(out), i + len(sig))
        out[i:j] += sig[: j - i] * vol

    for at, kind, *args in events:
        put(kind(*args) if args else kind(), at, 0.8)
    out = out[: int(length * SR)]
    fade = int(0.35 * SR)
    out[-fade:] *= np.linspace(1, 0, fade)
    out = np.tanh(out * 1.3)                      # sanft begrenzen, macht es "lauter"
    out = out / np.max(np.abs(out)) * 0.92
    pcm = (out * 32767).astype(np.int16)
    stereo = np.repeat(pcm[:, None], 2, axis=1)
    with wave.open(path, "wb") as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes(stereo.tobytes())


if __name__ == "__main__":
    folder = sys.argv[1]
    # Video 1: Hook, Riser, 8 Vibes im Takt, Endkarte
    v1 = [(0, boom), (0.8, riser, 0.8), (1.6, boom)]
    v1 += [(1.6 + i * 0.8 - 0.12, whoosh, 0.22) for i in range(1, 8)]
    v1 += [(1.6 + i * 0.8, pop) for i in range(8)]
    v1 += [(8.0, boom), (8.0, ding), (8.4, ding, 1568.0, 2349.0)]
    render(12, v1, 1.6, 8.0, 8.0, f"{folder}/sound-1.wav")
    # Video 2: Hook, Mali hüpft rein, Scan, Drop mit Preisen, Endkarte
    v2 = [(0, boom), (1.8, whoosh, 0.35), (2.2, pop), (2.4, riser, 2.4)]
    v2 += [(2.4 + i * 0.2, blip, 1320 + (i % 3) * 220) for i in range(11)]
    v2 += [(4.8, boom)] + [(4.8 + i * 0.16, pop) for i in range(6)]
    v2 += [(8.4, boom), (8.4, ding), (8.8, ding, 1568.0, 2349.0)]
    render(12, v2, 0.0, 8.4, 8.4, f"{folder}/sound-2.wav")
    # Video 3: Hook, Preis-Sticker, Auslöser, Scan, Treffer, Ka-ching, Endkarte
    v3 = [(0, boom), (0.6, pop), (1.6, shutter), (1.9, whoosh, 0.3), (2.4, riser, 1.2)]
    v3 += [(2.4 + i * 0.2, blip, 1320 + (i % 3) * 220) for i in range(6)]
    v3 += [(3.6, boom), (3.6, pop), (4.0, pop), (4.4, pop), (5.2, kaching)]
    v3 += [(8.0, boom), (8.0, ding), (8.4, ding, 1568.0, 2349.0)]
    render(12, v3, 1.6, 8.0, 8.0, f"{folder}/sound-3.wav")
    print("ok")
