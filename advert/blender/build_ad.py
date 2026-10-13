"""Build and render the RhyolitePrime PVC gas hose advert (Blender 5.x).

Run from a terminal (Blender 5.1.2 on your PATH, or the full path to the binary):

    blender -b --python build_ad.py -- --preview            # quick check, 640x360
    blender -b --python build_ad.py                         # full 1920x1080 render
    blender -b --python build_ad.py -- --stage 3            # only stage 3 (domestic)
    blender -b --python build_ad.py -- --build-only         # just build and save the .blend

Or open build_ad.py in Blender's Text Editor and press Run Script (defaults apply).

After the frames are rendered, the MP4 with the background music, sound effects,
and voiceover is made by ffmpeg. This step does not need Blender:

    python3 build_ad.py --mux-only

Outputs (in advert/output/, which is git-ignored):
    RhyolitePrime_Advert.blend   the editable Blender scene (soundtrack & VO strips on timeline)
    background_music.wav         mastered soundtrack (music + diegetic SFX + ducked voiceover)
    voiceover_track.wav          aligned 45s spoken voiceover stem
    frames/frame_NNNN.png        the rendered frames
    RhyolitePrime_Advert.mp4     final video with soundtrack (needs ffmpeg)
"""

import argparse
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import music  # noqa: E402  (stdlib only)
import shots as S  # noqa: E402

OUT_DIR = os.path.abspath(os.path.join(HERE, "..", "output"))
FRAMES_DIR = os.path.join(OUT_DIR, "frames")
BLEND_PATH = os.path.join(OUT_DIR, "RhyolitePrime_Advert.blend")
MUSIC_PATH = os.path.join(OUT_DIR, "background_music.wav")
VO_STEM_PATH = os.path.join(OUT_DIR, "voiceover_track.wav")
MP4_PATH = os.path.join(OUT_DIR, "RhyolitePrime_Advert.mp4")
TOTAL_FRAMES = int(round(S.SHOT_SECONDS * S.FPS)) * len(S.SHOTS)


def parse_args(argv):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--preview", action="store_true", help="640x360, 8 samples (fast check)")
    p.add_argument("--width", type=int, default=1920)
    p.add_argument("--height", type=int, default=1080)
    p.add_argument("--samples", type=int, default=32, help="Cycles render samples")
    p.add_argument("--engine", choices=["CYCLES", "EEVEE"], default="CYCLES")
    p.add_argument("--device", choices=["CPU", "GPU"], default="CPU",
                   help="Cycles device. GPU uses the first available accelerator.")
    p.add_argument("--stage", type=int, help="render only this stage number (1-based)")
    p.add_argument("--start", type=int, help="first frame to render")
    p.add_argument("--end", type=int, help="last frame to render")
    p.add_argument("--build-only", action="store_true", help="build and save the .blend, do not render")
    p.add_argument("--no-mux", action="store_true", help="skip the ffmpeg step")
    p.add_argument("--mux-only", action="store_true", help="only mux existing frames with the music (no Blender)")
    p.add_argument("--out", default=OUT_DIR, help="output folder")
    return p.parse_args(argv)


def frame_range(args):
    if args.stage:
        if not 1 <= args.stage <= len(S.SHOTS):
            raise SystemExit(f"--stage must be 1..{len(S.SHOTS)}")
        first = 1 + (args.stage - 1) * int(S.SHOT_SECONDS * S.FPS)
        return first, first + int(S.SHOT_SECONDS * S.FPS) - 1
    start = args.start or 1
    end = args.end or TOTAL_FRAMES
    return start, end


def find_ffmpeg():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:  # optional: pip install imageio-ffmpeg
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def mux(out_dir, start, end, fps=S.FPS):
    """Combine the rendered PNG frames with the mastered soundtrack into an MP4 (uses ffmpeg)."""
    ffmpeg = find_ffmpeg()
    frames_dir = os.path.join(out_dir, "frames")
    if not os.path.isdir(frames_dir):
        raise SystemExit(f"no frames found in {frames_dir}; render first")
    music_path = os.path.join(out_dir, "background_music.wav")
    if not os.path.exists(music_path):
        music.build(music_path)
    if ffmpeg is None:
        print("ffmpeg not found. Install it (e.g. `brew install ffmpeg`, `apt install ffmpeg`, or "
              "`pip install imageio-ffmpeg`) and re-run with --mux-only.")
        return None
    audio_offset = (start - 1) / fps
    mp4 = os.path.join(out_dir, "RhyolitePrime_Advert.mp4")
    cmd = [
        ffmpeg, "-y", "-loglevel", "error",
        "-framerate", str(fps), "-start_number", str(start),
        "-i", os.path.join(frames_dir, "frame_%04d.png"),
        "-ss", f"{audio_offset:.4f}", "-i", music_path,
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "medium",
        "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
        mp4,
    ]
    print("muxing:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    print("wrote", mp4)
    return mp4


def run_blender(args):
    import bpy  # only available inside Blender

    import scene_builder

    os.makedirs(args.out, exist_ok=True)
    os.makedirs(os.path.join(args.out, "frames"), exist_ok=True)

    # The Cycles add-on is needed when running in background mode.
    try:
        bpy.ops.preferences.addon_enable(module="cycles")
    except Exception as exc:  # pragma: no cover
        print("[advert] could not enable Cycles:", exc)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene

    music_path = os.path.join(args.out, "background_music.wav")
    vo_stem_path = os.path.join(args.out, "voiceover_track.wav")
    print("[advert] generating soundtrack (music + SFX + ducked voiceover) ...")
    music.build(music_path, vo_stem_out=vo_stem_path)

    print("[advert] building scenes ...")
    scene_builder.build_scene(scene)

    # Render settings
    width, height = (640, 360) if args.preview else (args.width, args.height)
    samples = 8 if args.preview else args.samples
    start, end = frame_range(args)
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.fps = S.FPS
    scene.render.fps_base = 1.0
    scene.frame_start = start
    scene.frame_end = end
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    scene.render.filepath = os.path.join(args.out, "frames", "frame_")

    if args.engine == "CYCLES":
        scene.render.engine = "CYCLES"
        scene.cycles.samples = samples
        scene.cycles.use_denoising = True
        scene.cycles.device = "CPU"
        if args.device == "GPU":
            _enable_gpu(bpy)
    else:
        scene.render.engine = "BLENDER_EEVEE"
    try:
        scene.view_settings.view_transform = "AgX"
    except TypeError:
        pass

    # Put the mastered soundtrack (and separate muted VO stem for reference) on the VSE timeline.
    se = scene.sequence_editor_create()
    strips = se.strips if hasattr(se, "strips") else se.sequences
    strips.new_sound("Background music", os.path.abspath(music_path), 1, 1)
    if os.path.isfile(vo_stem_path):
        vo_strip = strips.new_sound("Voiceover Stem", os.path.abspath(vo_stem_path), 2, 1)
        vo_strip.mute = True  # already mixed with auto-ducking into channel 1

    os.makedirs(args.out, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(args.out, "RhyolitePrime_Advert.blend"))
    print("[advert] saved", os.path.join(args.out, "RhyolitePrime_Advert.blend"))

    if args.build_only:
        return

    print(f"[advert] rendering frames {start}-{end} at {width}x{height}, {samples} samples ...")
    bpy.ops.render.render(animation=True)
    print("[advert] render finished")

    if not args.no_mux and (start, end) == (1, TOTAL_FRAMES):
        mux(args.out, start, end)
    elif not args.no_mux:
        print("[advert] partial render: skipping mux (run the full render, then --mux-only)")


def _enable_gpu(bpy):
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for dev_type in ("OPTIX", "CUDA", "HIP", "METAL", "ONEAPI"):
        try:
            prefs.compute_device_type = dev_type
            prefs.get_devices()
            devices = [d for d in prefs.devices if d.type != "CPU"]
            if devices:
                for d in prefs.devices:
                    d.use = True
                bpy.context.scene.cycles.device = "GPU"
                print(f"[advert] using {dev_type} GPU")
                return
        except Exception:
            continue
    print("[advert] no GPU found, falling back to CPU")


def _bpy_importable():
    try:
        import bpy  # noqa: F401
        return True
    except ImportError:
        return False


def main():
    # Blender passes script arguments after "--". Plain python3 passes them directly.
    if "--" in sys.argv:
        argv = sys.argv[sys.argv.index("--") + 1:]
    elif _bpy_importable():
        argv = []
    else:
        argv = sys.argv[1:]
    args = parse_args(argv)

    if args.mux_only:
        start, end = frame_range(args)
        if mux(args.out, start, end) is None:
            sys.exit(1)
        return

    if not _bpy_importable():
        raise SystemExit(
            "This script must run inside Blender 5.x (blender -b --python build_ad.py -- ...).\n"
            "To only mux existing frames, use: python3 build_ad.py --mux-only")
    run_blender(args)


if __name__ == "__main__":
    main()
