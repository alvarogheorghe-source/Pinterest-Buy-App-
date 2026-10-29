"""Sound für herbst.html (15,5 s), filmisch und ruhig: Lo-Fi mit weichen Akkorden und Vinyl,
Wind mit Böen, raschelndes Laub, sanfte Blasen-Töne, Grillen, "hatschi", traurige Spieluhr.

Aufruf: python3 herbst_sound.py <ordner>  -> herbst.wav
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gatekeeping_sound import crickets  # noqa: E402
from serie_sound import whoosh, write  # noqa: E402
from sound import SR, env, hz, lowpass, music_lofi, noise, placer, sine  # noqa: E402
from story_sound import musicbox  # noqa: E402

LEN = 20.2
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


def blip(freq, vol=0.22):
    """Sanfter Blasen-Ton (Nachricht steigt auf)."""
    return sine(freq, 0.35, decay=9, attack=0.004, vol=vol, harmonics=(1.0, 0.25))


def sparkle_soft():
    out = np.zeros(int(0.6 * SR))
    put = placer(out)
    for k, f in enumerate((1568.0, 2093.0, 2637.0, 3136.0)):
        put(sine(f, 0.4, decay=10, vol=0.08), k * 0.06)
    return out


def render(path):
    out = np.zeros(int((LEN + 1) * SR))
    put = placer(out)

    put(lowpass(music_lofi(LEN, 1.8, 14.6, 99), 0.18), 0, 0.55)     # ruhiger Lo-Fi, ab der ersten Nachricht
    put(wind(LEN), 0)
    for at, s in GUSTS:
        put(rustle(0.8), at + 0.1, 0.8 * s)
        put(whoosh(0.6), at + 0.05, 0.5 * s)
    put(chatter(1.0), 0.4)                                          # Zähneklappern, leise

    for at in (1.9, 4.4, 6.8, 9.4, 9.8, 10.2, 10.6):                # eigene Nachrichten
        put(blip(988.0), at)
    for at in (2.9, 5.2, 7.5, 12.0):                                # Antworten
        put(blip(659.3, 0.18), at)
        put(blip(523.3, 0.14), at + 0.1)
    put(sine(880.0, 0.25, decay=10, vol=0.1), 11.0)                 # gesehen
    put(crickets(0.9), 11.0, 0.7)
    put(sneeze(), 12.45, 0.8)
    put(whoosh(0.6), 14.35, 0.8)                                    # weißer Übergang
    put(sparkle_soft(), 14.6)
    put(blip(1318.5, 0.2), 16.0)                                    # Ping! endlich eine Antwort
    put(blip(1760.0, 0.2), 16.12)
    put(blip(659.3, 0.16), 16.1)
    put(blip(523.3, 0.16), 16.9)
    for k, (n_, o) in enumerate([("E", 5), ("D", 5), ("C", 5), ("B", 4)]):   # traurige Spieluhr
        put(musicbox(hz(n_, o), dur=1.4, vol=0.12), 17.0 + k * 0.28)
    put(lowpass(noise(0.4), 0.05) * np.exp(-np.arange(int(0.4 * SR)) / SR * 9) * 3, 18.0)   # Schnee rutscht ab
    put(blip(988.0), 18.6)                                          # und morgen wieder …
    write(out, LEN, path)


if __name__ == "__main__":
    render(f"{sys.argv[1]}/herbst.wav")
    print("ok")
