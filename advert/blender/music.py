"""Procedural background music, diegetic sound effects, and voiceover mixer for the RhyolitePrime advert.

Pure Python standard library (no numpy needed), so it runs inside Blender's
bundled Python as well as a normal python3. Output is a 16-bit stereo WAV.

Musical & Audio layout (matches shots.py):
  * 96 BPM, 4/4. One stage = 5 seconds = two bars, so every stage starts on a
    bar line and the chord changes line up with the cuts.
  * Each stage has its own two-chord progression.
  * Kick on every beat, clap on beats 2 and 4, eighth-note hats, a bass line
    on the chord roots, a soft pad, and a plucked arpeggio lead.
  * At every stage start there is a bell stinger and a short rising sweep,
    which is where the on-screen key selling point appears.
  * Stage-specific diegetic SFX (welding spark crackle & torch hiss, oxyacetylene
    flame roar, kitchen piezo igniter & sizzle, outdoor grill sizzle, farm
    brooder hum & chick peeps, factory pneumatic air wrench bursts, and a
    confirmation chime when the green check badge pops in).
  * Spoken voiceover clips from `advert/audio/vo_01_intro.wav` .. `vo_09_outro.wav`
    are aligned to each stage (`stage_t + 0.30s`), exported as a dedicated 45s
    `voiceover_track.wav` stem, and mixed into `background_music.wav` with
    smooth automatic sidechain ducking of the instrumental bed.
"""

import array
import math
import os
import random
import wave

import shots as S

SAMPLE_RATE = 44100
BPM = 96
BEAT = 60.0 / BPM          # 0.625 s
BAR = 4 * BEAT             # 2.5 s
STAGE = 2 * BAR            # 5.0 s
VO_OFFSET = 0.30           # seconds into each stage where the voiceover begins

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
AUDIO_DIR = os.path.abspath(os.path.join(HERE, "..", "audio"))

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
        start = max(0, int(t0 * SAMPLE_RATE))
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


# ---------------------------------------------------------------------------
# Procedural Diegetic Sound Effects (SFX)
# ---------------------------------------------------------------------------

def sfx_check_chime():
    """Bright two-note confirmation chime when the green check badge pops in."""
    n1 = bell(79, 0.35)   # G5
    n2 = bell(84, 0.65)   # C6
    gap = int(0.08 * SAMPLE_RATE)
    out = [0.0] * (gap + len(n2))
    for i, v in enumerate(n1):
        if i < len(out):
            out[i] += 0.45 * v
    for i, v in enumerate(n2):
        out[gap + i] += 0.55 * v
    return out


def sfx_torch_pop_and_hiss(rng, seconds=3.3, crackle_rate=18):
    """Torch ignition pop followed by pressurized gas hiss and welding spark crackles."""
    length = int(seconds * SAMPLE_RATE)
    out = [0.0] * length
    # Ignition pop in first 80ms
    pop_len = min(length, int(0.08 * SAMPLE_RATE))
    for i in range(pop_len):
        t = i / SAMPLE_RATE
        f = 160.0 * math.exp(-t * 35.0) + 55.0
        out[i] += 0.55 * math.sin(2 * math.pi * f * t) * math.exp(-t * 45.0)
    # Continuous band-filtered gas hiss + crackle impulses
    lp = 0.0
    hp_prev = 0.0
    for i in range(length):
        t = i / SAMPLE_RATE
        env = min(1.0, t / 0.12) * min(1.0, (seconds - t) / 0.35)
        x = rng.uniform(-1.0, 1.0)
        lp += (x - lp) * 0.18
        hp = x - hp_prev
        hp_prev = x
        out[i] += 0.09 * (0.6 * hp + 0.4 * lp) * env
    # Spark crackle bursts
    n_crackles = int(seconds * crackle_rate)
    for _ in range(n_crackles):
        c0 = rng.randint(int(0.15 * SAMPLE_RATE), max(int(0.16 * SAMPLE_RATE), length - int(0.15 * SAMPLE_RATE)))
        clen = rng.randint(int(0.004 * SAMPLE_RATE), int(0.015 * SAMPLE_RATE))
        amp = rng.uniform(0.12, 0.28)
        for k in range(min(clen, length - c0)):
            out[c0 + k] += amp * rng.uniform(-1.0, 1.0) * math.exp(-k / (0.004 * SAMPLE_RATE))
    return out


def sfx_stove_ignite_and_sizzle(rng, seconds=3.4, piezo=True):
    """Piezo igniter ticks + soft blue-flame gas whoosh + gentle pan/pot sizzle."""
    length = int(seconds * SAMPLE_RATE)
    out = [0.0] * length
    if piezo:
        for click_t in (0.08, 0.20, 0.32):
            c0 = int(click_t * SAMPLE_RATE)
            for k in range(min(int(0.008 * SAMPLE_RATE), length - c0)):
                out[c0 + k] += 0.45 * math.sin(2 * math.pi * 2900.0 * (k / SAMPLE_RATE)) * math.exp(-k / 80.0)
    # Flame whoosh at 0.36s + steady sizzle
    lp = 0.0
    prev = 0.0
    for i in range(length):
        t = i / SAMPLE_RATE
        if t < 0.34 and piezo:
            continue
        dt = t - (0.34 if piezo else 0.0)
        whoosh = 0.18 * math.exp(-dt * 4.5) * math.sin(2 * math.pi * 95.0 * dt)
        env = min(1.0, dt / 0.15) * min(1.0, (seconds - t) / 0.35)
        x = rng.uniform(-1.0, 1.0)
        hp = x - prev
        prev = x
        lp += (hp - lp) * 0.35
        out[i] += whoosh + 0.075 * lp * env
    return out


def sfx_chick_peep(f0=2900.0, f1=3500.0, duration=0.11):
    """Soft high-frequency chirp for the poultry brooder stage."""
    length = int(duration * SAMPLE_RATE)
    out = []
    phase = 0.0
    for i in range(length):
        u = i / length
        f = f0 + (f1 - f0) * math.sin(math.pi * u)
        phase += 2 * math.pi * f / SAMPLE_RATE
        env = math.sin(math.pi * u) ** 1.5
        out.append(0.14 * math.sin(phase) * env)
    return out


def sfx_pneumatic_burst(rng, duration=0.22):
    """Compressed-air tool actuation + exhaust hiss ('psht')."""
    length = int(duration * SAMPLE_RATE)
    out = []
    prev = 0.0
    for i in range(length):
        t = i / SAMPLE_RATE
        x = rng.uniform(-1.0, 1.0)
        hp = x - prev
        prev = x
        whirr = 0.35 * math.sin(2 * math.pi * (420.0 + 180.0 * math.exp(-t * 14.0)) * t) * math.exp(-t * 16.0)
        hiss = 0.45 * hp * math.exp(-t * 11.0)
        out.append(whirr + hiss)
    return out


def add_stage_sfx(mix, stage, stage_t, rng):
    """Layer subtle stage-specific diegetic sound effects into `mix`."""
    chime = sfx_check_chime()
    if stage == 0:
        # Intro hose uncoil whoosh
        mix.add(stage_t + 0.25, [v * 0.22 for v in sweep(1.5)], pan=-0.15)
    elif stage == 1:
        # Welding & cutting: torch pop, cutting hiss, sparks + check chime
        mix.add(stage_t + 0.15, [v * 0.32 for v in sfx_torch_pop_and_hiss(rng, 3.3, crackle_rate=22)], pan=0.1)
        mix.add(stage_t + 3.92, [v * 0.32 for v in chime], pan=0.15)
    elif stage == 2:
        # Oxyacetylene welding: torch flame + bead crackle + check chime
        mix.add(stage_t + 0.18, [v * 0.30 for v in sfx_torch_pop_and_hiss(rng, 3.3, crackle_rate=14)], pan=-0.1)
        mix.add(stage_t + 3.92, [v * 0.32 for v in chime], pan=0.15)
    elif stage == 3:
        # Domestic kitchen: piezo clicks + burner ignition + pot simmer + check chime
        mix.add(stage_t + 0.10, [v * 0.32 for v in sfx_stove_ignite_and_sizzle(rng, 3.4, piezo=True)], pan=-0.1)
        mix.add(stage_t + 3.92, [v * 0.32 for v in chime], pan=0.15)
    elif stage == 4:
        # Commercial kitchen: busy griddle sizzle + range burner + check chime
        mix.add(stage_t + 0.12, [v * 0.32 for v in sfx_stove_ignite_and_sizzle(rng, 3.4, piezo=False)], pan=0.1)
        mix.add(stage_t + 3.92, [v * 0.32 for v in chime], pan=0.15)
    elif stage == 5:
        # Outdoor & camping: grill sizzle + check chime
        mix.add(stage_t + 0.15, [v * 0.28 for v in sfx_stove_ignite_and_sizzle(rng, 3.3, piezo=False)], pan=0.0)
        mix.add(stage_t + 3.92, [v * 0.34 for v in chime], pan=0.15)
    elif stage == 6:
        # Agriculture & farms: soft chick peeps + warm brooder hum + check chime
        for pt, f0, pan in ((0.45, 2850, -0.25), (0.62, 3100, -0.2), (1.55, 2950, 0.2),
                            (2.45, 3050, -0.15), (3.15, 2900, 0.25)):
            mix.add(stage_t + pt, sfx_chick_peep(f0, f0 + 550), pan=pan)
        mix.add(stage_t + 3.92, [v * 0.32 for v in chime], pan=0.15)
    elif stage == 7:
        # Manufacturing: rhythmic pneumatic tool bursts + check chime
        for bt in (0.45, 1.30, 2.15, 3.00):
            mix.add(stage_t + bt, [v * 0.30 for v in sfx_pneumatic_burst(rng)], pan=-0.1)
        mix.add(stage_t + 3.92, [v * 0.32 for v in chime], pan=0.15)
    elif stage == 8:
        # Outro loop swoosh
        mix.add(stage_t + 0.15, [v * 0.20 for v in sweep(1.3)], pan=0.0)


# ---------------------------------------------------------------------------
# Voiceover loading & automatic sidechain ducking
# ---------------------------------------------------------------------------

def _read_wav_mono_float(path):
    """Read a WAV file and return a list of normalized float samples [-1, 1] at SAMPLE_RATE."""
    with wave.open(path, "rb") as w:
        nch = w.getnchannels()
        sw = w.getsampwidth()
        rate = w.getframerate()
        raw_bytes = w.readframes(w.getnframes())
    if sw == 2:
        data = array.array("h", raw_bytes)
        scale = 1.0 / 32768.0
    elif sw == 1:
        data = [b - 128 for b in raw_bytes]
        scale = 1.0 / 128.0
    else:
        return []
    if nch > 1:
        mono = [data[i] * scale for i in range(0, len(data), nch)]
    else:
        mono = [x * scale for x in data]
    if rate != SAMPLE_RATE and mono:
        new_len = int(round(len(mono) * SAMPLE_RATE / rate))
        ratio = (len(mono) - 1) / max(1, new_len - 1)
        resampled = []
        for i in range(new_len):
            pos = i * ratio
            idx = int(pos)
            frac = pos - idx
            s0 = mono[idx]
            s1 = mono[min(len(mono) - 1, idx + 1)]
            resampled.append(s0 + frac * (s1 - s0))
        mono = resampled
    # Normalize peak of each voiceover clip for consistent broadcast loudness
    peak = max((abs(x) for x in mono), default=0.0)
    if peak > 1e-4:
        gain = 0.88 / peak
        mono = [x * gain for x in mono]
    return mono


def build_voiceover_mix(seconds, audio_dir=AUDIO_DIR):
    """Build a Mix containing all stage voiceover clips aligned to their stage windows."""
    vo_mix = Mix(seconds)
    loaded = 0
    for idx, shot in enumerate(S.SHOTS):
        vo_file = shot.get("vo_file")
        if not vo_file:
            continue
        vo_path = os.path.join(audio_dir, vo_file)
        if not os.path.isfile(vo_path):
            continue
        samples = _read_wav_mono_float(vo_path)
        if not samples:
            continue
        # Ensure clip never spills past the stage boundary
        max_len = int((STAGE - VO_OFFSET - 0.15) * SAMPLE_RATE)
        if len(samples) > max_len:
            samples = samples[:max_len]
        vo_mix.add(idx * STAGE + VO_OFFSET, samples, pan=0.0)
        loaded += 1
    return vo_mix, loaded


def apply_ducking_and_mix_vo(bed_mix, vo_mix, seconds, duck_gain=0.38):
    """Duck `bed_mix` smoothly wherever `vo_mix` has active speech, then sum `vo_mix` in."""
    n = int(seconds * SAMPLE_RATE)
    env = 1.0
    attack = math.exp(-1.0 / (0.018 * SAMPLE_RATE))   # 18ms attack
    release = math.exp(-1.0 / (0.220 * SAMPLE_RATE))  # 220ms release
    win = int(0.015 * SAMPLE_RATE)
    # Precompute short-term speech activity detector in 15ms blocks
    active_blocks = []
    vo_l = vo_mix.left
    for b0 in range(0, n, win):
        b1 = min(n, b0 + win)
        peak = 0.0
        for i in range(b0, b1, 4):
            v = abs(vo_l[i])
            if v > peak:
                peak = v
        active_blocks.append(peak > 0.025)

    bl, br = bed_mix.left, bed_mix.right
    vl, vr = vo_mix.left, vo_mix.right
    for b_idx, speaking in enumerate(active_blocks):
        target = duck_gain if speaking else 1.0
        coeff = attack if speaking else release
        b0 = b_idx * win
        b1 = min(n, b0 + win)
        for i in range(b0, b1):
            env = coeff * env + (1.0 - coeff) * target
            bl[i] = bl[i] * env + vl[i] * 1.15
            br[i] = br[i] * env + vr[i] * 1.15


def build(path, total_seconds=None, include_vo=True, vo_stem_out=None):
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
        groove = 0.55 if stage == 0 else 1.0

        for bar, (root, quality) in enumerate(prog):
            bar_t = stage_t + bar * BAR
            notes = chord_notes(root, quality)
            pad_len = BAR + (2.5 if is_outro and bar == 1 else 0.0)
            mix.add(bar_t, [v * 0.22 * groove for v in pad(notes, pad_len)])

            for beat in range(4):
                bt = bar_t + beat * BEAT
                mix.add(bt, [v * 0.85 * groove for v in kick_s])
                if beat in (1, 3):
                    mix.add(bt, [v * 0.22 * groove for v in clap_s], pan=0.15)
            for eighth in range(8):
                ht = bar_t + eighth * BEAT / 2
                mix.add(ht, [v * (0.10 if eighth % 2 else 0.06) * groove for v in hat_s],
                        pan=-0.3 if eighth % 2 else 0.3)

            bass_pattern = [root - 12, root - 12, root, root - 12, root - 12, root - 12, root, root - 12]
            for eighth, bnote in enumerate(bass_pattern):
                bt = bar_t + eighth * BEAT / 2
                mix.add(bt, [v * 0.55 * groove for v in bass_note(bnote, BEAT / 2 * 0.95)])

            if stage >= 2 or (stage == 1 and bar == 1):
                lead_notes = [notes[0] + 12, notes[1] + 12, notes[2] + 12, notes[1] + 12]
                for eighth in range(8):
                    lt = bar_t + eighth * BEAT / 2
                    mix.add(lt, [v * 0.16 for v in pluck(lead_notes[eighth % 4])],
                            pan=0.45 if eighth % 2 else -0.45)

        # Bell stinger on the stage's key selling point
        bell_notes = chord_notes(prog[0][0], prog[0][1])
        mix.add(stage_t, [v * 0.30 for v in bell(bell_notes[2] + 12)], pan=0.2)
        mix.add(stage_t + BEAT, [v * 0.18 for v in bell(bell_notes[0] + 24, 1.0)], pan=-0.2)
        if stage > 0:
            mix.add(stage_t - 0.6 if stage_t >= 0.6 else 0.0, [v * 0.35 for v in sweep_s])

        # Diegetic stage SFX
        add_stage_sfx(mix, stage, stage_t, rng)

    # Final resolution: C major bell and a long tail.
    end_t = (n_stages - 1) * STAGE + STAGE - 0.8
    mix.add(end_t, [v * 0.25 for v in bell(72, 3.0)], pan=0.0)

    # Normalize the music+SFX bed before ducking and voiceover summing
    n = int(total * SAMPLE_RATE)
    bed_peak = max(max(abs(x) for x in mix.left[:n]), max(abs(x) for x in mix.right[:n]), 1e-9)
    bed_scale = 0.72 / bed_peak
    for i in range(n):
        mix.left[i] *= bed_scale
        mix.right[i] *= bed_scale

    if include_vo:
        vo_mix, count = build_voiceover_mix(total)
        if count > 0:
            if vo_stem_out is None:
                vo_stem_out = os.path.join(os.path.dirname(os.path.abspath(path)), "voiceover_track.wav")
            write_wav(vo_stem_out, vo_mix, total, fade_in_s=0.05, fade_out_s=0.15)
            apply_ducking_and_mix_vo(mix, vo_mix, total, duck_gain=0.38)
            print(f"[advert] mixed {count} voiceover clips with auto-ducking")

    write_wav(path, mix, total)
    return path


def write_wav(path, mix, seconds, fade_in_s=0.25, fade_out_s=1.2):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    n = int(seconds * SAMPLE_RATE)
    l, r = mix.left, mix.right
    fade_in = int(fade_in_s * SAMPLE_RATE)
    fade_out = int(fade_out_s * SAMPLE_RATE)
    peak = max(max(abs(x) for x in l[:n]), max(abs(x) for x in r[:n]), 1e-9)
    gain = min(1.0, 0.88 / peak)
    frames = array.array("h")
    for i in range(n):
        g = gain
        if fade_in > 0 and i < fade_in:
            g *= i / fade_in
        if fade_out > 0 and i > n - fade_out:
            g *= max(0.0, (n - i) / fade_out)
        frames.append(int(max(-1.0, min(1.0, math.tanh(l[i] * g * 1.05))) * 32767))
        frames.append(int(max(-1.0, min(1.0, math.tanh(r[i] * g * 1.05))) * 32767))
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(frames.tobytes())


if __name__ == "__main__":
    import sys
    import time

    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "output", "background_music.wav")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    t0 = time.time()
    build(out)
    print(f"wrote {os.path.abspath(out)} in {time.time() - t0:.1f}s")
