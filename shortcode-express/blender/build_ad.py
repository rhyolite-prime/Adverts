"""End-to-end builder and renderer for the ShortCode Express ("Be Fluent") advert.

Can be run either inside Blender or directly with a Python that has the `bpy`
module installed (`pip install bpy imageio-ffmpeg`):

    blender -b -P shortcode-express/blender/build_ad.py -- [options]
    python3 shortcode-express/blender/build_ad.py [options]

Options:
    --out-dir DIR       Output folder (default: shortcode-express/output)
    --width W           Render width (default: 1920)
    --height H          Render height (default: 1080)
    --samples N         Render samples per pixel (default: 64)
    --engine NAME       CYCLES or BLENDER_EEVEE (default: CYCLES)
    --device MODE       AUTO, GPU, or CPU (default: AUTO)
    --preview           Render 1 keyframe per scene (7 frames total) for fast verification
    --stage N           Render only scene N (1-7)
    --frame-step K      Render every K-th frame and hold in between (default: 1)
    --start-frame F     Override start frame
    --end-frame F       Override end frame
    --build-only        Save the .blend and audio WAVs without rendering frames
    --mux-only          Skip rendering; mux existing PNGs + WAV into the final MP4
"""

import argparse
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import music  # noqa: E402
import scene_builder  # noqa: E402
import shots as S  # noqa: E402


def parse_args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = argv[1:]

    default_out = os.path.abspath(os.path.join(HERE, "..", "output"))
    ap = argparse.ArgumentParser(description="Build & render the ShortCode Express 40s advert.")
    ap.add_argument("--out-dir", default=default_out)
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--samples", type=int, default=32)
    ap.add_argument("--engine", default="CYCLES", choices=["CYCLES", "BLENDER_EEVEE"])
    ap.add_argument("--device", default="CPU", choices=["AUTO", "GPU", "CPU"])
    ap.add_argument("--preview", action="store_true",
                    help="Render one representative frame per scene (7 frames total)")
    ap.add_argument("--stage", type=int, default=0,
                    help="Render only scene N (1-7)")
    ap.add_argument("--frame-step", type=int, default=1,
                    help="Render every K-th frame and duplicate onto intermediate frames")
    ap.add_argument("--start-frame", type=int, default=1)
    ap.add_argument("--end-frame", type=int, default=S.total_frames())
    ap.add_argument("--build-only", action="store_true")
    ap.add_argument("--mux-only", action="store_true")
    return ap.parse_args(argv)


def find_ffmpeg():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def attach_audio_to_scene(scene, wav_path, vo_stem_path=None):
    seq = scene.sequence_editor_create()
    strips = getattr(seq, "strips", None) or getattr(seq, "sequences", None)
    if strips is not None and os.path.exists(wav_path):
        for s in list(strips):
            strips.remove(s)
        strips.new_sound("MasterTrack", wav_path, channel=1, frame_start=1)
        if vo_stem_path and os.path.exists(vo_stem_path):
            vo_strip = strips.new_sound("VoiceoverStem", vo_stem_path, channel=2, frame_start=1)
            vo_strip.mute = True


def render_frames(scene, frames_dir, frame_list, step=1):
    import bpy

    os.makedirs(frames_dir, exist_ok=True)
    total = len(frame_list)
    t_start = time.time()

    for i, f in enumerate(frame_list):
        t0 = time.time()
        scene.frame_set(f)
        out_path = os.path.join(frames_dir, f"frame_{f:04d}.png")
        scene.render.filepath = out_path
        bpy.ops.render.render(write_still=True)

        if step > 1:
            for dup in range(f + 1, min(f + step, S.total_frames() + 1)):
                dup_path = os.path.join(frames_dir, f"frame_{dup:04d}.png")
                shutil.copyfile(out_path, dup_path)

        dt = time.time() - t0
        elapsed = time.time() - t_start
        eta = (elapsed / (i + 1)) * (total - i - 1)
        print(f"[shortcode-express] rendered frame {f:04d} ({i + 1}/{total}) in {dt:.1f}s — ETA {eta / 60:.1f} min",
              flush=True)


def mux_mp4(frames_dir, wav_path, mp4_path, fps=S.FPS, preview=False):
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        print("[shortcode-express] WARNING: ffmpeg not found; skipping MP4 mux.")
        return False

    if preview:
        pattern = os.path.join(frames_dir, "stage_%02d.png")
        shot_durs = [s["seconds"] for s in S.SHOTS]
        avg_dur = sum(shot_durs) / len(shot_durs)
        cmd = [
            ffmpeg, "-y",
            "-framerate", f"1/{avg_dur:.4f}",
            "-i", pattern,
            "-i", wav_path,
            "-t", str(int(S.total_seconds())),
            "-vf", f"fps={fps},format=yuv420p",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            mp4_path,
        ]
    else:
        pattern = os.path.join(frames_dir, "frame_%04d.png")
        cmd = [
            ffmpeg, "-y",
            "-framerate", str(fps),
            "-i", pattern,
            "-i", wav_path,
            "-t", str(int(S.total_seconds())),
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            mp4_path,
        ]
    print("[shortcode-express] running:", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)
    return True


def main():
    import bpy

    args = parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    frames_dir = os.path.join(args.out_dir, "frames")
    wav_path = os.path.join(args.out_dir, "background_music.wav")
    vo_stem_path = os.path.join(args.out_dir, "voiceover_track.wav")
    blend_path = os.path.join(args.out_dir, "ShortCodeExpress_Advert.blend")
    mp4_path = os.path.join(
        args.out_dir,
        "ShortCodeExpress_Advert_preview.mp4" if args.preview else "ShortCodeExpress_Advert.mp4",
    )

    print("[shortcode-express] generating 40s mastered soundtrack + voiceover stem ->", wav_path, flush=True)
    music.build(wav_path, S.total_seconds(), include_vo=True, vo_stem_out=vo_stem_path)

    if args.mux_only:
        mux_mp4(frames_dir, wav_path, mp4_path, preview=args.preview)
        return

    print("[shortcode-express] building 3D scene (7 scenes, 960 frames) ...", flush=True)
    scene = scene_builder.build_full_scene(
        width=args.width,
        height=args.height,
        samples=args.samples,
        engine=args.engine,
        device=args.device,
    )
    attach_audio_to_scene(scene, wav_path, vo_stem_path=vo_stem_path)

    print("[shortcode-express] saving blend file ->", blend_path, flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)

    if args.build_only:
        print("[shortcode-express] --build-only set; exiting after saving .blend and audio.", flush=True)
        return

    if args.preview:
        os.makedirs(frames_dir, exist_ok=True)
        for idx in range(len(S.SHOTS)):
            f0, f1 = S.stage_frames(idx)
            f = int(f0 + (f1 - f0) * 0.65)
            scene.frame_set(f)
            out_path = os.path.join(frames_dir, f"stage_{idx + 1:02d}.png")
            scene.render.filepath = out_path
            t0 = time.time()
            bpy.ops.render.render(write_still=True)
            print(f"[shortcode-express] preview scene {idx + 1}/7 (frame {f}) -> {out_path} ({time.time() - t0:.1f}s)",
                  flush=True)
        mux_mp4(frames_dir, wav_path, mp4_path, preview=True)
    elif 1 <= args.stage <= len(S.SHOTS):
        f0, f1 = S.stage_frames(args.stage - 1)
        frames = list(range(f0, f1 + 1, max(1, args.frame_step)))
        render_frames(scene, frames_dir, frames, step=args.frame_step)
    else:
        f0 = max(1, args.start_frame)
        f1 = min(S.total_frames(), args.end_frame)
        frames = list(range(f0, f1 + 1, max(1, args.frame_step)))
        render_frames(scene, frames_dir, frames, step=args.frame_step)
        if f0 == 1 and f1 == S.total_frames():
            mux_mp4(frames_dir, wav_path, mp4_path, preview=False)

    print("[shortcode-express] DONE ->", mp4_path, flush=True)


if __name__ == "__main__":
    main()
