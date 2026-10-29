"""Sound für herbst.html (15,5 s): Wind mit Böen, Zähneklappern, raschelndes Laub, leiser
Schleich-Beat, Tippen, Benachrichtigungen, Grillen, "hatschi", am Ende traurige Spieluhr.

Aufruf: python3 herbst_sound.py <ordner>  -> herbst.wav
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gatekeeping_sound import crickets, key_click, notif, sneaky  # noqa: E402
from serie_sound import scratch, slide, sting, thud, whoosh, write  # noqa: E402
from sound import SR, boom, env, hz, lowpass, noise, placer, pop, sine, square  # noqa: E402
from story_sound import bonk, musicbox, womp  # noqa: E402

LEN = 15.5
GUSTS = [(0.1, 1.0), (3.7, 0.5), (7.8, 1.2), (10.6, 0.6), (12.9, 0.9)]


def wind(length):
    """Windrauschen: tiefes Rauschen, das langsam auf- und abschwillt, plus Böen."""
    n = int(length * SR)
    t = np.arange(n) / SR
    base = lowpass(noise(length), 0.02) * 6
    howl = lowpass(noise(length), 0.06) * 2
    level = 0.25 + 0.1 * np.sin(t * 0.9) + sum(s * np.exp(-((t - at - 0.35) ** 2) / 0.12) for at, s in GUSTS)
    return (base + howl * level) * level * 0.5


def rustle(dur=0.6):
    x = noise(dur)
    x = x - lowpass(x, 0.25)
    crackle = (np.random.default_rng(2).random(len(x)) > 0.985) * np.random.default_rng(3).uniform(-1, 1, len(x))
    return (x * 0.25 + crackle * 0.6) * np.sin(np.linspace(0, np.pi, len(x))) * 0.6


def chatter(dur=1.3):
    """Zähneklappern: schnelle, kurze Klicks."""
    out = np.zeros(int(dur * SR))
    put = placer(out)
    k = 0.0
    while k < dur - 0.05:
        c = noise(0.01) * env(int(0.01 * SR), attack=0.0005, decay=400)
        put(lowpass(c, 0.5), k, 0.7)
        k += 0.055
    return out


def sneeze():
    """"Ha-…-tschi!": ansteigendes Einatmen, dann ein scharfer Stoß."""
    out = np.zeros(int(0.9 * SR))
    put = placer(out)
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    inhale = lowpass(noise(0.45), 0.08) * (t / t[-1]) ** 2 * 0.6
    put(inhale + np.sin(2 * np.pi * np.cumsum(300 + 500 * t / t[-1]) / SR) * (t / t[-1]) * 0.15, 0)
    burst = noise(0.25) * env(int(0.25 * SR), attack=0.003, decay=14)
    put((burst - lowpass(burst, 0.15)) * 1.2, 0.45)
    put(sine(520, 0.2, decay=12, vol=0.25), 0.45)
    return out


def render(path):
    out = np.zeros(int((LEN + 1) * SR))
    put = placer(out)
    rng = np.random.default_rng(5)

    put(wind(LEN), 0)
    for at, s in GUSTS:
        put(rustle(0.8), at + 0.1, 0.8 * s)
        put(whoosh(0.6), at + 0.05, 0.6 * s)
    put(boom(), 0, 0.7)
    put(chatter(1.3), 0.3)

    sneaky(put, 1.8, 11.0)                                          # leiser Schleich-Beat
    for frm, to in ((2.0, 2.8), (4.5, 4.9), (6.9, 7.2)):            # Tippen
        t = frm
        while t < to:
            put(key_click(), t)
            t += 0.05 + rng.uniform(0, 0.03)
    for at in (2.9, 5.0, 7.3):
        put(whoosh(0.18), at, 0.6)
        put(pop(), at + 0.05, 0.5)
    for at in (3.4, 5.4, 7.6):
        put(notif(), at)
    put(bonk(), 3.6)
    put(womp(hz("G", 3), 0.3), 3.65)
    put(womp(hz("F#", 3), 0.55, wobble=True), 3.95)
    put(pop(), 5.9, 0.8)                                            # Blatt klatscht ins Gesicht
    put(slide(700, 300, 0.3, 0.2), 5.9)
    put(scratch(), 5.6)
    put(boom(), 8.05)                                               # WELCHER LINK + Windstoß
    put(sting(), 8.1)
    for at in (9.5, 9.8, 10.1, 10.4, 10.7):                         # DMs
        put(square(1046.5, 0.05, duty=0.25, decay=40, vol=0.15), at)
        put(pop(), at, 0.4)
    put(sine(880.0, 0.25, decay=10, vol=0.15), 11.0)                # gesehen
    put(crickets(1.0), 11.0)
    put(slide(500, 900, 0.15, 0.12), 11.2)
    put(slide(900, 300, 0.25, 0.14), 11.7)
    put(thud(), 12.1)
    put(sneeze(), 12.45)                                            # hatschi bei 12.9
    put(chatter(0.8), 13.6)
    for k, (n_, o) in enumerate([("E", 5), ("D", 5), ("C", 5), ("B", 4), ("A", 4)]):   # traurige Spieluhr
        put(musicbox(hz(n_, o), dur=1.4, vol=0.14), 13.6 + k * 0.38)
    write(out, LEN, path)


if __name__ == "__main__":
    render(f"{sys.argv[1]}/herbst.wav")
    print("ok")
