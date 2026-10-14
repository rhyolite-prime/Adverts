"""Procedural soundtrack, UI/diegetic sound effects, and voiceover mixer for ShortCode Express.

Pure Python standard library (no numpy needed). Output is a 16-bit stereo WAV at 44.1 kHz.

Musical & SFX layout (matches shortcode_express_ad.md and shots.py):
  * 40.0 seconds total across 7 variable-length scenes:
      1. 00:00-00:04 (4s): Low rhythmic pulse + tactile DTMF keypad tones (*714*14#) + signal sweep
      2. 00:04-00:09 (5s): Tense rising minor pulse + accelerating keyboard typing + clean cut at 8.8s
      3. 00:09-00:13 (4s): Crisp reveal hit + bright C-major / G-major groove + harmonic shimmer
      4. 00:13-00:21 (8s): Confident forward momentum + three UI snap tones on Drag, Drop, Connect
      5. 00:21-00:29 (8s): Full groove + stereo arpeggio lead + magnetic plugin connection clicks
      6. 00:29-00:35 (6s): Five precise confirmation tones for Simulate, Validate, Deploy, Track, Roll back
      7. 00:35-00:40 (5s): Payment-success chime resolving into a C-major sonic signature
  * Loads `shortcode-express/audio/vo_01_dial.wav` .. `vo_07_outro.wav`, exports `voiceover_track.wav`,
    and mixes into `background_music.wav` with smooth automatic sidechain ducking.
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
VO_OFFSET = 0.25           # seconds into each scene where the voiceover begins

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
AUDIO_DIR = os.path.abspath(os.path.join(HERE, "..", "audio"))

# Per-scene harmonic plan: list of (root_midi, quality) chords stretched across the scene's bars
SCENE_CHORDS = [
    [(45, "m"), (52, "m")],                         # Scene 1 (4s): Am - Em (grounded pulse)
    [(50, "m"), (52, "m")],                         # Scene 2 (5s): Dm - Em (rising tension)
    [(48, "M"), (55, "M")],                         # Scene 3 (4s): C - G   (bright reveal!)
    [(53, "M"), (48, "M"), (55, "M"), (57, "m")],   # Scene 4 (8s): F - C - G - Am (Drag. Drop. Connect.)
    [(53, "M"), (55, "M"), (48, "M"), (57, "m")],   # Scene 5 (8s): F - G - C - Am (Plugin marketplace)
    [(50, "m"), (53, "M"), (55, "M")],              # Scene 6 (6s): Dm - F - G (Operational control)
    [(53, "M"), (48, "M")],                         # Scene 7 (5s): F - C (resolves to C major)
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
        start = max(0, int(t0 * SAMPLE_RATE))
        gl = math.cos((pan + 1) * math.pi / 4)
        gr = math.sin((pan + 1) * math.pi / 4)
        end = min(self.n, start + len(samples))
        left, right = self.left, self.right
        for i in range(start, end):
            s = samples[i - start]
            left[i] += s * gl
            right[i] += s * gr


def kick(length=int(0.32 * SAMPLE_RATE)):
    out = []
    phase = 0.0
    for i in range(length):
        t = i / SAMPLE_RATE
        f = 46.0 + 90.0 * math.exp(-t * 28.0)
        phase += 2 * math.pi * f / SAMPLE_RATE
        out.append(math.sin(phase) * math.exp(-t * 9.5))
    return out


def noise_burst(rng, seconds, decay, highpass=False):
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


def pluck(note, seconds=0.42):
    f = midi_hz(note)
    length = int(seconds * SAMPLE_RATE)
    out = []
    for i in range(length):
        t = i / SAMPLE_RATE
        tri = 2.0 / math.pi * math.asin(math.sin(2 * math.pi * f * t))
        out.append(tri * math.exp(-t * 7.2))
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
            env = min(1.0, t / 0.30) * min(1.0, (seconds - t) / 0.35)
            v = math.sin(2 * math.pi * f * t) + 0.35 * math.sin(2 * math.pi * f * 1.004 * t)
            out[i] += 0.5 * v * max(env, 0.0) / len(notes)
    return out


def sweep(seconds=1.1):
    rng = random.Random(7)
    length = int(seconds * SAMPLE_RATE)
    out = []
    lp = 0.0
    for i in range(length):
        t = i / length
        x = rng.uniform(-1, 1)
        lp += (x - lp) * (0.02 + 0.5 * t)
        out.append(lp * t * (1 - t) * 4)
    return out


# ---------------------------------------------------------------------------
# Diegetic & UI Sound Effects for ShortCode Express
# ---------------------------------------------------------------------------

DTMF_FREQS = {
    "*": (941.0, 1209.0),
    "#": (941.0, 1477.0),
    "1": (697.0, 1209.0),
    "4": (770.0, 1209.0),
    "7": (852.0, 1209.0),
}


def sfx_dtmf_key(key_char, duration=0.085):
    """Tactile keypad click + dual-tone multi-frequency dial tone."""
    f1, f2 = DTMF_FREQS.get(key_char, (770.0, 1336.0))
    length = int(duration * SAMPLE_RATE)
    out = []
    for i in range(length):
        t = i / SAMPLE_RATE
        click = 0.45 * math.sin(2 * math.pi * 1800.0 * t) * math.exp(-t * 180.0)
        tone = 0.22 * (math.sin(2 * math.pi * f1 * t) + math.sin(2 * math.pi * f2 * t))
        env = min(1.0, t / 0.005) * min(1.0, (duration - t) / 0.012)
        out.append(click + tone * env)
    return out


def sfx_key_clack(rng):
    """Restrained mechanical keyboard keystroke click."""
    length = int(0.032 * SAMPLE_RATE)
    f = rng.uniform(1900.0, 2500.0)
    out = []
    for i in range(length):
        t = i / SAMPLE_RATE
        n = rng.uniform(-1.0, 1.0) * math.exp(-t * 160.0)
        body = math.sin(2 * math.pi * f * t) * math.exp(-t * 140.0)
        out.append(0.32 * (0.6 * n + 0.4 * body))
    return out


def sfx_ui_snap(note_midi=76, duration=0.14):
    """Clean UI snap/pop for Drag, Drop, Connect, and plugin tile snapping."""
    f = midi_hz(note_midi)
    length = int(duration * SAMPLE_RATE)
    out = []
    for i in range(length):
        t = i / SAMPLE_RATE
        pop = 0.45 * math.sin(2 * math.pi * (f * 1.5) * t) * math.exp(-t * 65.0)
        chime = 0.35 * math.sin(2 * math.pi * f * t) * math.exp(-t * 22.0)
        out.append(pop + chime)
    return out


def sfx_confirm_chime(n1_midi=79, n2_midi=84):
    """Two-note confirmation chime."""
    n1 = bell(n1_midi, 0.32)
    n2 = bell(n2_midi, 0.58)
    gap = int(0.075 * SAMPLE_RATE)
    out = [0.0] * (gap + len(n2))
    for i, v in enumerate(n1):
        if i < len(out):
            out[i] += 0.42 * v
    for i, v in enumerate(n2):
        out[gap + i] += 0.52 * v
    return out


def add_scene_sfx(mix, scene_idx, t0, dur, rng):
    """Add scene-specific diegetic and interface sound effects matching shortcode_express_ad.md."""
    if scene_idx == 0:
        # Scene 1: Customer dials *714*14# + Call click + outgoing USSD signal pulse
        seq = ["*", "7", "1", "4", "*", "1", "4", "#"]
        for k, ch in enumerate(seq):
            mix.add(t0 + 0.18 + k * 0.14, sfx_dtmf_key(ch), pan=-0.15)
        mix.add(t0 + 1.45, sfx_ui_snap(81, 0.18), pan=-0.1)
        mix.add(t0 + 2.55, [v * 0.28 for v in sweep(1.1)], pan=0.15)
    elif scene_idx == 1:
        # Scene 2: Accelerating keyboard typing during 'endless if-else' + tense riser that cuts cleanly
        t_cur = t0 + 0.25
        step = 0.16
        while t_cur < t0 + dur - 0.65:
            mix.add(t_cur, sfx_key_clack(rng), pan=rng.uniform(-0.25, 0.25))
            step = max(0.065, step * 0.94)
            t_cur += step
        mix.add(t0 + dur - 1.35, [v * 0.35 for v in sweep(1.1)], pan=0.0)
    elif scene_idx == 2:
        # Scene 3: Crisp reveal hit + untangling harmonic shimmer
        mix.add(t0 + 0.02, [v * 0.42 for v in bell(72, 1.6)], pan=-0.2)
        mix.add(t0 + 0.10, [v * 0.38 for v in bell(79, 1.8)], pan=0.2)
        for k, note in enumerate((60, 64, 67, 72, 76, 79)):
            mix.add(t0 + 0.85 + k * 0.16, [v * 0.24 for v in pluck(note, 0.35)], pan=-0.3 + 0.12 * k)
    elif scene_idx == 3:
        # Scene 4: Three restrained interface sounds synced with 'Drag. Drop. Connect.' + phone menu chime
        mix.add(t0 + 1.10, sfx_ui_snap(72, 0.15), pan=-0.2)   # select short code *714*14#
        mix.add(t0 + 2.85, sfx_ui_snap(74, 0.15), pan=-0.25)  # Drag
        mix.add(t0 + 3.60, sfx_ui_snap(76, 0.16), pan=0.0)    # Drop
        mix.add(t0 + 4.35, sfx_ui_snap(79, 0.18), pan=0.25)   # Connect
        mix.add(t0 + 5.80, [v * 0.30 for v in sfx_confirm_chime(76, 81)], pan=0.3)
    elif scene_idx == 4:
        # Scene 5: Plugin marketplace tiles snapping in + 'Your Plugin' node + data pulse
        for k, note in enumerate((72, 74, 76, 79)):
            mix.add(t0 + 0.85 + k * 0.65, sfx_ui_snap(note, 0.14), pan=-0.2 + 0.12 * k)
        mix.add(t0 + 4.85, [v * 0.34 for v in sfx_confirm_chime(79, 84)], pan=0.15)  # Your Plugin
    elif scene_idx == 5:
        # Scene 6: Five precise confirmation tones for Simulate, Validate, Deploy, Track, Roll back
        beats = [(0.45, 72), (1.40, 74), (2.35, 76), (3.35, 79), (4.45, 84)]
        for dt, note in beats:
            mix.add(t0 + dt, sfx_ui_snap(note, 0.18), pan=0.1)
    elif scene_idx == 6:
        # Scene 7: Payment successful chime in shop + final sonic signature on 'ShortCode Express. Be fluent.'
        mix.add(t0 + 0.45, [v * 0.38 for v in sfx_confirm_chime(79, 84)], pan=-0.15)
        mix.add(t0 + 3.25, [v * 0.35 for v in bell(72, 2.2)], pan=-0.2)
        mix.add(t0 + 3.35, [v * 0.35 for v in bell(76, 2.2)], pan=0.2)
        mix.add(t0 + 3.45, [v * 0.42 for v in bell(84, 2.4)], pan=0.0)


# ---------------------------------------------------------------------------
# Voiceover loading & automatic sidechain ducking
# ---------------------------------------------------------------------------

def _read_wav_mono_float(path):
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
    peak = max((abs(x) for x in mono), default=0.0)
    if peak > 1e-4:
        gain = 0.88 / peak
        mono = [x * gain for x in mono]
    return mono


def build_voiceover_mix(seconds, audio_dir=AUDIO_DIR):
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
        t0, t1 = S.stage_times(idx)
        max_len = int((t1 - t0 - VO_OFFSET - 0.12) * SAMPLE_RATE)
        if len(samples) > max_len:
            samples = samples[:max_len]
        vo_mix.add(t0 + VO_OFFSET, samples, pan=0.0)
        loaded += 1
    return vo_mix, loaded


def apply_ducking_and_mix_vo(bed_mix, vo_mix, seconds, duck_gain=0.36):
    n = int(seconds * SAMPLE_RATE)
    env = 1.0
    attack = math.exp(-1.0 / (0.018 * SAMPLE_RATE))
    release = math.exp(-1.0 / (0.220 * SAMPLE_RATE))
    win = int(0.015 * SAMPLE_RATE)
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
    total = total_seconds or S.total_seconds()
    mix = Mix(total)
    rng = random.Random(2026)

    kick_s = kick()
    clap_s = noise_burst(rng, 0.20, 28.0, highpass=True)
    hat_s = noise_burst(rng, 0.045, 95.0, highpass=True)

    for idx, (shot, chords) in enumerate(zip(S.SHOTS, SCENE_CHORDS)):
        t0, t1 = S.stage_times(idx)
        dur = t1 - t0
        # Scene 2 cuts cleanly 0.22s before the Scene 3 reveal hit, as specified in the brief
        active_dur = dur - 0.22 if idx == 1 else dur
        seg_len = active_dur / len(chords)

        # Energy profile: low pulse in Scene 1, tense in Scene 2, bright & confident from Scene 3 onward
        groove = 0.52 if idx == 0 else (0.68 if idx == 1 else 1.0)

        for c_idx, (root, quality) in enumerate(chords):
            seg_t = t0 + c_idx * seg_len
            notes = chord_notes(root, quality)
            pad_len = seg_len + (1.4 if idx == len(S.SHOTS) - 1 and c_idx == len(chords) - 1 else 0.0)
            mix.add(seg_t, [v * 0.22 * groove for v in pad(notes, pad_len)])

            n_beats = max(1, int(round(seg_len / BEAT)))
            for b in range(n_beats):
                bt = seg_t + b * BEAT
                if bt >= t0 + active_dur:
                    break
                mix.add(bt, [v * 0.82 * groove for v in kick_s])
                if idx >= 2 and b % 2 == 1:
                    mix.add(bt, [v * 0.22 * groove for v in clap_s], pan=0.15)

            n_eighths = max(1, int(round(seg_len / (BEAT / 2))))
            for e in range(n_eighths):
                et = seg_t + e * (BEAT / 2)
                if et >= t0 + active_dur:
                    break
                mix.add(et, [v * (0.09 if e % 2 else 0.05) * groove for v in hat_s],
                        pan=-0.3 if e % 2 else 0.3)
                bnote = root if (e % 4 == 2) else (root - 12)
                mix.add(et, [v * 0.52 * groove for v in bass_note(bnote, BEAT / 2 * 0.92)])
                if idx >= 2:
                    lead_notes = [notes[0] + 12, notes[1] + 12, notes[2] + 12, notes[1] + 12]
                    mix.add(et, [v * 0.16 for v in pluck(lead_notes[e % 4])],
                            pan=0.42 if e % 2 else -0.42)

        add_scene_sfx(mix, idx, t0, dur, rng)

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
            apply_ducking_and_mix_vo(mix, vo_mix, total, duck_gain=0.36)
            print(f"[shortcode-express] mixed {count} voiceover clips with auto-ducking")

    write_wav(path, mix, total)
    return path


def write_wav(path, mix, seconds, fade_in_s=0.20, fade_out_s=1.0):
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
