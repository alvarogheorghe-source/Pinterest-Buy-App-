"""Musik für story.html (Mali nachts auf Pinterest), 14,5 s, selbst erzeugt.

0–5.6 s    nachts im Bett: leise Spieluhr, Wisch-Geräusche, "wow"-Funkeln beim Influencer-Hasen,
           verträumtes Glockenspiel bei der Traumwolke
5.6 s      Lampe "klick"
6.0–7.5 s  überfordert: Browserfenster poppen auf (Benachrichtigungs-Blips, Spannung steigt)
7.6–9.5 s  sucht: Uhr tickt, Preisschilder "bonk"
9.6 s      "womp womp" (alles zu teuer)
11.0 s     Idee: "ding!", Funkeln, kurzer fröhlicher Ausklang
Aufruf: python3 story_sound.py <ordner>  -> story-sound.wav
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sound import SR, env, hat, hz, kick, lowpass, noise, placer, pop, sine, square  # noqa: E402

LEN = 14.5
BEAT = 0.6                    # 100 BPM, gemütlich


def musicbox(freq, dur=1.2, vol=0.16):
    """Spieluhr: Sinus mit hellen Obertönen, schnell abklingend."""
    return sine(freq, dur, decay=4.5, attack=0.002, vol=vol, harmonics=(1.0, 0.0, 0.35, 0.0, 0.12))


def boing(at_freq=300):
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    f = at_freq * (1 + 1.2 * np.sin(t * 18) * np.exp(-t * 6))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7) * 0.5


def tick():
    x = noise(0.012) * env(int(0.012 * SR), attack=0.0005, decay=300)
    return (x - lowpass(x, 0.3)) * 0.6


def bonk():
    n = int(0.18 * SR)
    t = np.arange(n) / SR
    f = 260 * np.exp(-t * 10) + 120
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 18) * 0.7


def womp(start_hz, dur, wobble=False):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = start_hz * (1 - 0.03 * t / dur)
    if wobble:
        f = f * (1 + 0.025 * np.sin(2 * np.pi * 6 * t))
    w = np.where((np.cumsum(f) / SR) % 1 < 0.5, 1.0, -1.0)
    return lowpass(w * env(n, attack=0.02) * np.minimum(1, (dur - t) * 10), 0.12) * 0.55


def ding(f=1568.0):
    return sine(f, 1.0, decay=4, vol=0.4, harmonics=(1.0, 0.5, 0.25))


def sparkle():
    out = np.zeros(int(0.5 * SR))
    put = placer(out)
    for k, f in enumerate((2093.0, 2637.0, 3136.0, 4186.0)):
        put(sine(f, 0.3, decay=12, vol=0.12), k * 0.05)
    return out


def typing():
    x = noise(0.02) * env(int(0.02 * SR), attack=0.0005, decay=200)
    return (x - lowpass(x, 0.25)) * 0.35


def render(path):
    out = np.zeros(int((LEN + 1) * SR))
    put = placer(out)
    rng = np.random.default_rng(3)

    # --- nachts im Bett (0–5.6 s): leise, verschlafene Spieluhr ---
    chords = [("F", ["F", "A", "C"]), ("D", ["D", "F", "A"]), ("A#", ["A#", "D", "F"]), ("C", ["C", "E", "G"])]
    melody = [("A", 5), ("C", 6), ("F", 6), ("E", 6), ("D", 6), ("C", 6), ("A#", 5), ("A", 5), ("G", 5)]
    for k, (n_, o) in enumerate(melody):
        put(musicbox(hz(n_, o), vol=0.08), 0.15 + k * BEAT)
    for bar in range(3):
        root, tones = chords[bar % 4]
        for k in range(8):
            put(musicbox(hz(tones[k % 3], 4), vol=0.05), bar * 2.0 + k * 0.25)
        put(sine(hz(root, 3), 2.0, decay=1.2, attack=0.05, vol=0.1), bar * 2.0)
    swipe_len = int(0.16 * SR)
    for at in (0.2, 0.5, 0.75, 0.97, 1.17, 1.37, 1.6, 1.88, 2.25, 2.75):   # Wischen: schnell, dann langsamer
        put(lowpass(noise(0.16), 0.2) * np.sin(np.linspace(0, np.pi, swipe_len)) ** 2, at, 0.5)
    put(sparkle(), 3.0)                                   # der Influencer-Hase
    put(ding(2093.0), 3.05, 0.5)
    for k, f in enumerate((1046.5, 1318.5, 1568.0, 2093.0, 2637.0)):   # Traumwolke: Glockenspiel hoch
        put(musicbox(f, dur=1.2, vol=0.12), 4.3 + k * 0.09)

    # --- Lampe an, überfordert (5.6–7.5 s) ---
    click = noise(0.015) * env(int(0.015 * SR), attack=0.0005, decay=250)
    put(click, 5.6, 0.9)
    put(click, 5.635, 0.5)
    for k in range(12):                                   # Fenster poppen, immer höher
        put(square(880 * 2 ** (k / 12), 0.06, duty=0.25, decay=40, vol=0.22), 6.0 + k * 0.1)
        put(pop(), 6.0 + k * 0.1, 0.35)
    n = int(1.5 * SR)
    tt = np.arange(n) / SR
    put(np.sin(2 * np.pi * np.cumsum(180 + 420 * (tt / 1.5) ** 2) / SR) * (tt / 1.5) * 0.18, 6.0)   # Spannung
    put(sine(hz("D", 3), 1.8, decay=0.8, attack=0.1, vol=0.12, harmonics=(1.0, 0.4)), 5.8)

    # --- suchen (7.6–9.5 s) ---
    for k in range(19):
        put(tick(), 7.6 + k * 0.1)
    put(sine(hz("D", 3), 2.0, decay=0.6, attack=0.2, vol=0.12, harmonics=(1.0, 0.3)), 7.6)
    for at in (8.0, 8.4, 8.8, 9.2):
        put(bonk(), at)
    for k, (n_, o, d) in enumerate([("A", 3, 0.3), ("G#", 3, 0.3), ("G", 3, 0.3), ("F#", 3, 0.75)]):
        put(womp(hz(n_, o), d, wobble=k == 3), 9.6 + k * 0.3)

    # --- Idee (11.0 s) ---
    put(ding(1568.0), 11.0)
    put(sparkle(), 11.05)
    happy = [("C", 6), ("E", 6), ("G", 6), ("C", 7), ("G", 6), ("E", 6), ("F", 6), ("A", 6), ("G", 6)]
    for k, (n_, o) in enumerate(happy):
        put(musicbox(hz(n_, o), vol=0.14), 11.4 + k * BEAT / 2)
    for k, (root, tones) in enumerate([("C", ["C", "E", "G"]), ("F", ["F", "A", "C"]), ("C", ["C", "E", "G"])]):
        put(sine(hz(root, 3), 1.2, decay=1.5, attack=0.05, vol=0.12), 11.4 + k * 1.2)
        for m, note in enumerate(tones):
            put(musicbox(hz(note, 5), dur=0.9, vol=0.06), 11.4 + k * 1.2 + m * 0.1)
    put(sparkle(), 13.4)

    out = out[: int(LEN * SR)]
    fade = int(0.7 * SR)
    out[-fade:] *= np.linspace(1, 0, fade)
    out = np.tanh(lowpass(out, 0.45) * 1.4)
    out = out / np.max(np.abs(out)) * 0.9
    pcm = (out * 32767).astype(np.int16)
    import wave
    with wave.open(path, "wb") as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes(np.repeat(pcm[:, None], 2, axis=1).tobytes())


if __name__ == "__main__":
    render(f"{sys.argv[1]}/story-sound.wav")
    print("ok")
