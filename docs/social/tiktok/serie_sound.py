"""Musik + Effekte für serie.html (ausverkauft, paket, schrank, warenkorb), selbst erzeugt.

Aufruf: python3 serie_sound.py <ordner>  -> serie-<name>.wav
"""

import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sound import SR, hat, hz, kick, lowpass, noise, placer, pop, sine, square  # noqa: E402
from story_sound import bonk, ding, musicbox, sparkle, womp  # noqa: E402

BEAT = 0.42
HAPPY = [("C", ["C", "E", "G"]), ("A", ["A", "C", "E"]), ("F", ["F", "A", "C"]), ("G", ["G", "B", "D"])]
MELODY = [("E", 6), ("G", 6), ("C", 7), ("G", 6), ("A", 6), ("G", 6), ("E", 6), ("D", 6),
          ("C", 6), ("E", 6), ("D", 6), ("G", 5), ("A", 5), ("C", 6), ("D", 6), ("E", 6)]


def happy_loop(put, start, end, beat=BEAT, drums=True, vol=1.0):
    """Fröhliche Spieluhr mit leichtem Beat zwischen start und end."""
    b = 0
    while start + b * beat < end - 0.05:
        at = start + b * beat
        root, tones = HAPPY[(b // 4) % 4]
        if b % 4 == 0:
            put(sine(hz(root, 3), beat * 4, decay=1.2, attack=0.03, vol=0.11 * vol), at)
        n_, o = MELODY[b % len(MELODY)]
        put(musicbox(hz(n_, o), dur=0.8, vol=0.11 * vol), at)
        put(musicbox(hz(tones[b % 3], 5), dur=0.4, vol=0.05 * vol), at + beat / 2)
        if drums:
            put(kick(0.2, low=60, high=150, k=30), at, 0.4 * vol)
            put(hat(0.03), at + beat / 2, 0.14 * vol)
        b += 1


def sleepy(put, start, end):
    for k, f in enumerate([hz("A", 5), hz("F", 5), hz("C", 5), hz("D", 5), hz("C", 5)]):
        if start + k * 0.6 < end:
            put(musicbox(f, dur=1.4, vol=0.08), start + k * 0.6)


def slide(f1, f2, dur, vol=0.35):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = f1 * (f2 / f1) ** (t / dur)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.minimum(1, (dur - t) * 8) * vol


def whoosh(dur=0.25):
    x = lowpass(noise(dur), 0.12)
    return x * np.sin(np.linspace(0, np.pi, len(x))) ** 2 * 1.3


def thud():
    return kick(0.35, low=40, high=110, k=16) * 1.1


def sting():                                         # Schock-Akkord (schief)
    return sum(square(f, 0.7, duty=0.5, decay=4, vol=0.08) for f in (hz("C", 4), hz("F#", 4), hz("B", 4)))


def scratch():
    n = int(0.3 * SR)
    t = np.arange(n) / SR
    f = 900 * np.exp(-t * 8) + 120
    return lowpass(np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * np.exp(-t * 6), 0.2) * 0.4 + noise(0.3) * np.exp(-t * 12) * 0.2


def write(out, length, path):
    out = out[: int(length * SR)]
    fade = int(0.5 * SR)
    out[-fade:] *= np.linspace(1, 0, fade)
    out = np.tanh(lowpass(out, 0.45) * 1.4)
    out = out / np.max(np.abs(out)) * 0.9
    pcm = (out * 32767).astype(np.int16)
    with wave.open(path, "wb") as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes(np.repeat(pcm[:, None], 2, axis=1).tobytes())


def ausverkauft(path, length=10.5):
    out = np.zeros(int((length + 1) * SR))
    put = placer(out)
    happy_loop(put, 0, 4.6)
    put(sparkle(), 0.3)
    put(pop(), 2.2)
    put(square(1320, 0.06, duty=0.25, decay=40, vol=0.2), 2.25)
    for k, at in enumerate((3.0, 3.6, 4.2, 4.8)):
        put(bonk(), at)
        put(square(880 / 2 ** (k / 4), 0.08, duty=0.25, decay=30, vol=0.15), at)
    put(thud(), 5.6)
    put(sting(), 5.6)
    for k, (n_, o, d) in enumerate([("A", 3, 0.28), ("G#", 3, 0.28), ("G", 3, 0.28), ("F#", 3, 0.7)]):
        put(womp(hz(n_, o), d, wobble=k == 3), 6.6 + k * 0.28)
    put(slide(700, 180, 1.0), 7.6)                   # rutscht unter die Decke
    sleepy(put, 8.6, length)
    write(out, length, path)


def paket(path, length=11.0):
    out = np.zeros(int((length + 1) * SR))
    put = placer(out)
    happy_loop(put, 0, 6.2)
    put(pop(), 1.6)
    put(ding(2093.0), 1.65, 0.6)
    put(whoosh(0.4), 2.8)
    put(thud(), 3.3)
    put(slide(400, 1600, 0.5, 0.25), 5.0)            # Deckel auf
    put(sparkle(), 5.3)
    put(scratch(), 6.2)                              # Musik stoppt: Plattenkratzer
    put(bonk(), 6.6)
    for k, (n_, o, d) in enumerate([("G", 3, 0.3), ("F#", 3, 0.6)]):
        put(womp(hz(n_, o), d, wobble=k == 1), 9.0 + k * 0.3)
    put(whoosh(0.5), 9.4)
    sleepy(put, 9.8, length)
    write(out, length, path)


def schrank(path, length=10.0):
    out = np.zeros(int((length + 1) * SR))
    put = placer(out)
    happy_loop(put, 0, 2.4, drums=False)
    put(slide(220, 330, 0.5, 0.15), 0.3)             # Türen gehen auf
    happy_loop(put, 2.4, 5.6, beat=0.25)             # hektisch
    for k in range(12):
        put(whoosh(0.22), 2.6 + k * 0.25, 0.8)
    put(slide(600, 150, 0.9), 5.6)                   # Luft raus
    sleepy(put, 6.2, 7.6)
    put(ding(1568.0), 7.6)
    put(sparkle(), 7.65)
    happy_loop(put, 8.0, length, drums=False, vol=0.8)
    write(out, length, path)


def warenkorb(path, length=10.5):
    out = np.zeros(int((length + 1) * SR))
    put = placer(out)
    happy_loop(put, 0, 3.6)
    for k, at in enumerate((0.5, 1.1, 1.7, 2.3, 2.9)):
        put(pop(), at)
        put(square(1046.5 * 2 ** (k / 6), 0.07, duty=0.25, decay=30, vol=0.18), at + 0.03)
    put(thud(), 3.6)
    put(sting(), 3.6)
    for k, at in enumerate((5.6, 6.0, 6.4, 6.8, 7.2)):
        put(whoosh(0.22), at)
        put(square(1046.5 / 2 ** (k / 6), 0.07, duty=0.25, decay=30, vol=0.15), at + 0.05)
    sleepy(put, 5.4, 8.0)
    put(ding(1568.0), 8.3)
    put(sparkle(), 8.6)
    happy_loop(put, 8.6, length, drums=False, vol=0.9)
    write(out, length, path)


if __name__ == "__main__":
    folder = sys.argv[1]
    for name, fn in (("ausverkauft", ausverkauft), ("paket", paket), ("schrank", schrank), ("warenkorb", warenkorb)):
        fn(f"{folder}/serie-{name}.wav")
    print("ok")
