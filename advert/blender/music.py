"""Procedural background music for the RhyolitePrime advert.

Pure Python standard library (no numpy needed), so it runs inside Blender's
bundled Python as well as a normal python3. Output is a 16-bit stereo WAV.

Musical layout (matches shots.py):
  * 96 BPM, 4/4. One stage = 5 seconds = two bars, so every stage starts on a
    bar line and the chord changes line up with the cuts.
  * Each stage has its own two-chord progression.
  * Kick on every beat, clap on beats 2 and 4, eighth-note hats, a bass line
    on the chord roots, a soft pad, and a plucked arpeggio lead.
  * At every stage start there is a bell stinger and a short rising sweep,
    which is where the on-screen key selling point appears.
  * The last stage resolves to C major and rings out.
"""

import array
import math
import random
import wave

SAMPLE_RATE = 44100
BPM = 96
BEAT = 60.0 / BPM          # 0.625 s
BAR = 4 * BEAT             # 2.5 s
STAGE = 2 * BAR            # 5.0 s

# Two chords per stage (one per bar). Chords are (root MIDI note, quality).
# C4 = 60. Quality "M" = major triad, "m" = minor triad.
PROGRESSIONS = [
    [(48, "M"), (57, "m")],   # 0 intro: C - Am
    [(57, "m"), (53, "M")],   # 1 welding & cutting: Am - F
    [(53, "M"), (55, "M")],   # 2 oxyacetylene: F - G
    [(48, "M"), (55, "M")],   # 3 domestic: C - G
    [(50, "m"), (55, "M")],   # 4 commercial kitchen: Dm - G
    [(52, "m"), (48, "M")],   # 5 outdoor & camping: Em - C
    [(53, "M"), (50, "m")],   # 6 agriculture: F - Dm
    [(57, "m"), (52, "m")],   # 7 manufacturing: Am - Em
    [(53, "M"), (48, "M")],   # 8 outro: F - C (resolves)
]


def midi_hz(note):
    return 440.0 * 2.0 ** ((note - 69) / 12.0)


def chord_notes(root, quality):
    third = 4 if quality == "M" else 3
    return [root, root + third, root + 7]


class Mix:
    def __init__(self, seconds):
        self.n = int(seconds * SAMPLE_RATE) + SAMPLE_RATE
        self.left = array.array("d", bytes(8 * self.n))
        self.right = array.array("d", bytes(8 * self.n))

    def add(self, t0, samples, pan=0.0):
        """Add a mono list of samples starting at time t0 (seconds)."""
        start = int(t0 * SAMPLE_RATE)
        gl = math.cos((pan + 1) * math.pi / 4)
        gr = math.sin((pan + 1) * math.pi / 4)
        end = min(self.n, start + len(samples))
        left, right = self.left, self.right
        for i in range(start, end):
            s = samples[i - start]
            left[i] += s * gl
            right[i] += s * gr


def env_exp(length, decay):
    return [math.exp(-decay * i / SAMPLE_RATE) for i in range(length)]


def kick(length=int(0.35 * SAMPLE_RATE)):
    out = []
    phase = 0.0
    for i in range(length):
        t = i / SAMPLE_RATE
        f = 45.0 + 85.0 * math.exp(-t * 28.0)
        phase += 2 * math.pi * f / SAMPLE_RATE
        out.append(math.sin(phase) * math.exp(-t * 9.0))
    return out


def noise_burst(rng, seconds, decay, highpass=0.0):
    length = int(seconds * SAMPLE_RATE)
    out = []
    prev = 0.0
    for i in range(length):
        x = rng.uniform(-1, 1)
        if highpass:
            y = x - prev
            prev = x
            x = y
        out.append(x * math.exp(-decay * i / SAMPLE_RATE))
    return out


def bell(note, seconds=1.4):
    base = midi_hz(note)
    length = int(seconds * SAMPLE_RATE)
    out = []
    partials = [(1.0, 1.0, 1.4), (2.76, 0.45, 2.2), (5.40, 0.18, 3.5)]
    for i in range(length):
        t = i / SAMPLE_RATE
        s = 0.0
        for ratio, amp, decay in partials:
            s += amp * math.sin(2 * math.pi * base * ratio * t) * math.exp(-decay * t)
        out.append(s * (1.0 - math.exp(-t * 400.0)))
    return out


def pluck(note, seconds=0.45):
    f = midi_hz(note)
    length = int(seconds * SAMPLE_RATE)
    out = []
    for i in range(length):
        t = i / SAMPLE_RATE
        tri = 2.0 / math.pi * math.asin(math.sin(2 * math.pi * f * t))
        out.append(tri * math.exp(-t * 7.0))
    return out


def bass_note(note, seconds):
    f = midi_hz(note)
    length = int(seconds * SAMPLE_RATE)
    out = []
    for i in range(length):
        t = i / SAMPLE_RATE
        # soft saw from a few harmonics, gently decaying
        s = 0.0
        for h in range(1, 6):
            s += math.sin(2 * math.pi * f * h * t) / h
        a = min(1.0, t / 0.01) * math.exp(-t * 2.5)
        out.append(0.6 * s * a)
    return out


def pad(notes, seconds):
    length = int(seconds * SAMPLE_RATE)
    out = [0.0] * length
    for note in notes:
        f = midi_hz(note)
        for i in range(length):
            t = i / SAMPLE_RATE
            env = min(1.0, t / 0.35) * min(1.0, (seconds - t) / 0.45)
            v = math.sin(2 * math.pi * f * t) + 0.35 * math.sin(2 * math.pi * f * 1.004 * t)
            out[i] += 0.5 * v * max(env, 0.0) / len(notes)
    return out


def sweep(seconds=1.2):
    rng = random.Random(7)
    length = int(seconds * SAMPLE_RATE)
    out = []
    lp = 0.0
    for i in range(length):
        t = i / length
        x = rng.uniform(-1, 1)
        lp += (x - lp) * (0.02 + 0.5 * t)  # brightening low-pass
        out.append(lp * t * (1 - t) * 4)
    return out


def build(path, total_seconds=None):
    n_stages = len(PROGRESSIONS)
    total = total_seconds or n_stages * STAGE
    mix = Mix(total)
    rng = random.Random(2026)

    kick_s = kick()
    clap_s = noise_burst(rng, 0.22, 26.0, highpass=True)
    hat_s = noise_burst(rng, 0.05, 90.0, highpass=True)
    sweep_s = sweep()

    for stage, prog in enumerate(PROGRESSIONS):
        stage_t = stage * STAGE
        is_outro = stage == n_stages - 1
        # Groove is quieter in the intro, builds in the middle, and resolves at the end.
        groove = 0.55 if stage == 0 else 1.0

        for bar, (root, quality) in enumerate(prog):
            bar_t = stage_t + bar * BAR
            notes = chord_notes(root, quality)
            # pad: sustain the chord across the bar (longer tail on the final bar)
            pad_len = BAR + (2.5 if is_outro and bar == 1 else 0.0)
            mix.add(bar_t, [v * 0.22 * groove for v in pad(notes, pad_len)])

            # kick on every beat, clap on 2 and 4, hats on eighths
            for beat in range(4):
                bt = bar_t + beat * BEAT
                mix.add(bt, [v * 0.85 * groove for v in kick_s])
                if beat in (1, 3):
                    mix.add(bt, [v * 0.22 * groove for v in clap_s], pan=0.15)
            for eighth in range(8):
                ht = bar_t + eighth * BEAT / 2
                mix.add(ht, [v * (0.10 if eighth % 2 else 0.06) * groove for v in hat_s], pan=-0.3 if eighth % 2 else 0.3)

            # bass: root, root, octave, root on eighths, one octave below the chord
            bass_pattern = [root - 12, root - 12, root, root - 12, root - 12, root - 12, root, root - 12]
            for eighth, bnote in enumerate(bass_pattern):
                bt = bar_t + eighth * BEAT / 2
                mix.add(bt, [v * 0.55 * groove for v in bass_note(bnote, BEAT / 2 * 0.95)])

            # arpeggio lead from the second stage onwards, panned and quieter in the intro
            if stage >= 2 or (stage == 1 and bar == 1):
                lead_notes = [notes[0] + 12, notes[1] + 12, notes[2] + 12, notes[1] + 12]
                for eighth in range(8):
                    lt = bar_t + eighth * BEAT / 2
                    mix.add(lt, [v * 0.16 for v in pluck(lead_notes[eighth % 4])], pan=0.45 if eighth % 2 else -0.45)

        # stinger on the stage's key selling point
        bell_notes = chord_notes(prog[0][0], prog[0][1])
        mix.add(stage_t, [v * 0.30 for v in bell(bell_notes[2] + 12)], pan=0.2)
        mix.add(stage_t + BEAT, [v * 0.18 for v in bell(bell_notes[0] + 24, 1.0)], pan=-0.2)
        if stage > 0:
            # rising sweep into the cut (the last half-second before the stage starts)
            mix.add(stage_t - 0.6 if stage_t >= 0.6 else 0.0, [v * 0.35 for v in sweep_s])

    # Final resolution: C major bell and a long tail.
    end_t = (n_stages - 1) * STAGE + STAGE - 0.8
    mix.add(end_t, [v * 0.25 for v in bell(72, 3.0)], pan=0.0)

    write_wav(path, mix, total)
    return path


def write_wav(path, mix, seconds):
    n = int(seconds * SAMPLE_RATE)
    l, r = mix.left, mix.right
    fade_in = int(0.4 * SAMPLE_RATE)
    fade_out = int(1.5 * SAMPLE_RATE)
    peak = max(max(abs(x) for x in l[:n]), max(abs(x) for x in r[:n]), 1e-9)
    gain = 0.8 / peak
    frames = array.array("h")
    for i in range(n):
        g = gain
        if i < fade_in:
            g *= i / fade_in
        if i > n - fade_out:
            g *= max(0.0, (n - i) / fade_out)
        frames.append(int(max(-1.0, min(1.0, math.tanh(l[i] * g * 1.1))) * 32767))
        frames.append(int(max(-1.0, min(1.0, math.tanh(r[i] * g * 1.1))) * 32767))
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(frames.tobytes())


if __name__ == "__main__":
    import os
    import sys
    import time

    here = os.path.dirname(os.path.abspath(__file__))
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "..", "output", "background_music.wav")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    t0 = time.time()
    build(out)
    print(f"wrote {os.path.abspath(out)} in {time.time() - t0:.1f}s")
