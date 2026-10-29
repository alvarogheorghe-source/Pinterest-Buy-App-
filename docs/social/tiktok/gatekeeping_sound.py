"""Sound für gatekeeping.html (15,5 s), selbst erzeugt: frecher "Sneaky"-Beat, Tippen,
Benachrichtigungen, Plattenkratzer, Grillenzirpen (keine Antwort), "dun dun duuun" am Ende.

Aufruf: python3 gatekeeping_sound.py <ordner>  -> gatekeeping.wav
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from serie_sound import scratch, slide, sting, thud, whoosh, write  # noqa: E402
from sound import SR, boom, env, hat, hz, kick, lowpass, noise, placer, pop, sine, square  # noqa: E402
from story_sound import bonk, womp  # noqa: E402

LEN = 15.5
BEAT = 0.4                                  # 150 BPM


def pizz(freq, vol=0.18):
    """Gezupfter Bass (wie Pizzicato): kurz, rund."""
    return sine(freq, 0.22, decay=16, attack=0.002, vol=vol, harmonics=(1.0, 0.5, 0.2))


def sneaky(put, start, end):
    """Frecher Schleich-Beat in Moll: Bass-Zupfer, Klatscher, Hi-Hats."""
    line = [("A", 2), (None, 0), ("C", 3), ("A", 2), ("E", 3), (None, 0), ("D#", 3), ("D", 3)]
    b = 0
    while start + b * BEAT / 2 < end - 0.05:
        at = start + b * BEAT / 2
        n_, o = line[b % len(line)]
        if n_:
            put(pizz(hz(n_, o)), at)
        if b % 2 == 0:
            put(hat(0.03), at, 0.14)
        if b % 4 == 2:
            put(lowpass(noise(0.08), 0.3) * np.exp(-np.arange(int(0.08 * SR)) / SR * 40), at, 0.45)
        if b % 4 == 0:
            put(kick(0.2, low=55, high=150, k=30), at, 0.5)
        b += 1


def key_click():
    x = noise(0.012) * env(int(0.012 * SR), attack=0.0005, decay=300)
    return (x - lowpass(x, 0.3)) * 0.4


def notif():
    """Benachrichtigungs-Ding-Ding (Hoffnung!)."""
    out = np.zeros(int(0.5 * SR))
    put = placer(out)
    put(sine(1318.5, 0.35, decay=9, vol=0.3, harmonics=(1.0, 0.3)), 0)
    put(sine(1760.0, 0.35, decay=9, vol=0.3, harmonics=(1.0, 0.3)), 0.11)
    return out


def crickets(dur):
    """Grillen: kurze, hohe Zirp-Pakete."""
    out = np.zeros(int(dur * SR))
    put = placer(out)
    t0 = 0.0
    while t0 < dur - 0.3:
        for k in range(3):
            n = int(0.035 * SR)
            tt = np.arange(n) / SR
            chirp = np.sin(2 * np.pi * 4400 * tt) * np.sin(np.pi * tt / tt[-1]) * 0.12
            put(chirp, t0 + k * 0.05)
        t0 += 0.45
    return out


def bubble():
    return square(1046.5, 0.05, duty=0.25, decay=40, vol=0.15) + 0


def dun(freq, dur):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    w = sum(np.sign(np.sin(2 * np.pi * freq * m * tt)) / m for m in (1, 2))
    return lowpass(w * env(n, attack=0.01, decay=1.5 if dur > 0.6 else 4) * 0.25, 0.15)


def render(path):
    out = np.zeros(int((LEN + 1) * SR))
    put = placer(out)
    rng = np.random.default_rng(5)

    put(boom(), 0)                                   # Hook
    put(sting(), 0.05)
    sneaky(put, 1.6, 10.6)
    sneaky(put, 11.6, 13.6)

    for frm, to in ((1.8, 2.6), (4.3, 4.9), (6.7, 7.1)):        # Tippen
        t = frm
        while t < to:
            put(key_click(), t)
            t += 0.05 + rng.uniform(0, 0.03)
    for at in (2.7, 5.0, 7.2):                                  # gesendet
        put(whoosh(0.18), at, 0.7)
        put(pop(), at + 0.05, 0.6)
    for at in (3.2, 5.4, 7.5):                                  # Antwort kommt!
        put(notif(), at)

    put(bonk(), 3.4)                                            # "danke…???"
    put(womp(hz("G", 3), 0.3), 3.45)
    put(womp(hz("F#", 3), 0.55, wobble=True), 3.75)
    put(scratch(), 5.55)                                        # "vintage"
    put(whoosh(0.3), 7.95)                                      # zur Bio
    put(boom(), 8.3)                                            # WELCHER LINK
    put(sting(), 8.3)

    for at in (9.1, 9.4, 9.7, 10.0, 10.3):                      # DMs
        put(bubble(), at)
        put(pop(), at, 0.4)
    put(sine(880.0, 0.25, decay=10, vol=0.15), 10.6)            # gesehen
    put(crickets(1.0), 10.6)                                    # keine Antwort
    put(slide(500, 900, 0.15, 0.12), 10.8)                      # tippt …
    put(slide(900, 300, 0.25, 0.14), 11.3)                      # … nicht mehr

    put(thud(), 12.0)                                           # "warum fragt ihr immer"
    put(sting(), 12.0)

    put(boom(), 13.6)                                           # dun dun duuun
    for k, (n_, d) in enumerate((("D", 0.28), ("C#", 0.28), ("C", 1.4))):
        put(dun(hz(n_, 3), d), 13.7 + k * 0.32)
    write(out, LEN, path)


if __name__ == "__main__":
    render(f"{sys.argv[1]}/gatekeeping.wav")
    print("ok")
