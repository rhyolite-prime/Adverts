# RhyolitePrime PVC Gas Hose Advert (Blender)

A 45-second animated advert for RhyolitePrime Industrial PVC Gas Hoses, built in Blender. The sets and hoses are procedural; the characters come from the Rigify file in `rigs/`.

- `IMPLEMENTATION_PLAN.md`: detailed plan and summary of all production finishing touches applied to the advert.
- `SCRIPT.md`: the advert script (including stage-by-stage voiceover lines). It is generated from `blender/shots.py`, so edit the shot data there and regenerate with `python3 blender/shots.py --markdown > SCRIPT.md`.
- `blender/build_ad.py`: entry point. Builds the scene, generates the mastered soundtrack (music + diegetic SFX + ducked voiceover), renders frames, saves the `.blend`, and muxes the MP4.
- `blender/shots.py`: shot list, on-screen text, voiceover script lines, timings (9 stages x 5 s, 24 fps).
- `blender/scene_builder.py`: the Blender scene: characters, working animations, three-layer reinforced hoses with brass fittings, flames, sparks, cameras with Depth of Field, compositor Fog Glow, and the on-screen broadcast overlay.
- `blender/rig_characters.py`: the characters. Each one is appended fresh from `rigs/Body Mechanics Rigs.blend` (Jack or Jill), posed with the FK controls by a fast analytical matrix solver, and given per-part clothing and skin materials.
- `blender/geometry.py`: mesh generators (`box`, `cylinder`, `ring`, `cone`, `sphere`, `torus`, `plane`, `merge`, `translate`).
- `audio/vo_01_intro.wav` .. `audio/vo_09_outro.wav`: spoken voiceover clips for each of the nine 5-second stages.
- `images/all-products.jpg`: the product photo shown above the wordmark in the intro. It is packed into the `.blend`.
- `rigs/Body Mechanics Rigs.blend`: the supplied Rigify file with the Jack and Jill models and rigs.
- `blender/music.py`: procedural background music (96 BPM, 45 s), stage-specific diegetic sound effects, and automatic voiceover sidechain ducking, stdlib only.

Each application gets its own 5-second stage. An intro and an outro bookend the seven application stages. Each stage shows its key selling point in the lower third, with the product spec line, a top-right brand corner badge, and a progress bar. The music changes chord at every cut, layers stage-specific sound effects and spoken voiceover, and plays a bell stinger on each selling point.

## Look and feel

- Colours follow the RhyolitePrime palette: primary `#80004d` for the intro title, the wordmark and the brand; accent `#cc6699` for stage labels; light `#f8f9fa` for body text; dark `#212529` for the lower-third band; success `#4bb543` for the progress bar and check badge. The hoses keep their product colours (3/8 inch orange, 5/16 inch red and blue) with a glossy PVC clearcoat, fine braided bump, brass hex fittings, and three-layer reinforced cross-sections (black inner core, white braided fiber middle layer, coloured outer PVC jacket).
- The intro shows the product photo (`images/all-products.jpg`) in a beveled primary-coloured frame above the RhyolitePrime wordmark and the three-layer reinforced orange hose.
- All characters are African, with dark skin tones from the palette-led skin set (`skin_warm`, `skin_mid`, `skin_deep`), 3D facial features (almond sclera, large dark iris/pupil with catchlight glint, upper eyelid and lash line, animated eyebrows, and a sculpted nose with bridge, tip, wings, and nostrils), and a natural mid-stage blink. They perform active working motions during the stage before facing the camera to celebrate.
- Every application stage ends with the character giving a thumbs-up. Welding visors flip up onto the helmet brow, and a bright smile and circular green check badge (success `#4bb543` on a dark-and-white disc) pop in on the chest.
- The welder and oxy welder wear visor helmets, leather jackets, aprons and gloves. The home cook wears an apron and stirs the pot, and the chef wears a white jacket, toque and apron while working the griddle. The farmer wears a straw hat, overalls and gloves. The factory worker wears a hard hat and a hi-vis vest while operating a pneumatic tool.

## Requirements

- Blender 5.x (tested with Blender 5.0.1 / 5.1.2 Python API, including `sequence_editor.strips` and `compositing_node_group`).
- Optional, for the MP4: `ffmpeg` on your PATH. You can also `pip install imageio-ffmpeg` with any Python 3.

## Build and render

Run from `advert/`:

```bash
# 1. Quick check: 640x360, 8 samples, all frames
blender -b --python blender/build_ad.py -- --preview

# 2. Full quality: 1920x1080, 32 samples, then ffmpeg mux to MP4
blender -b --python blender/build_ad.py

# Options
blender -b --python blender/build_ad.py -- --samples 16          # faster, a bit noisier
blender -b --python blender/build_ad.py -- --device GPU          # use a GPU if Cycles can see one
blender -b --python blender/build_ad.py -- --stage 3             # render only stage 3 (oxyacetylene)
blender -b --python blender/build_ad.py -- --build-only          # just build and save the .blend

# If you rendered without ffmpeg, mux the frames later with plain Python:
python3 blender/build_ad.py --mux-only
```

You can also open `blender/build_ad.py` in Blender's Text Editor and press Run Script. In that case the defaults apply (1920x1080, 32 samples).

Outputs go to `advert/output/` (git-ignored):

- `RhyolitePrime_Advert.blend`: the editable scene, with the mastered soundtrack strip and voiceover stem strip on the timeline. Camera markers switch the camera at each stage.
- `background_music.wav`: mastered stereo audio (music + stage SFX + auto-ducked voiceover).
- `voiceover_track.wav`: aligned 45-second voiceover stem.
- `frames/frame_NNNN.png`
- `RhyolitePrime_Advert.mp4`

## Editing the advert

- Change the copy, voiceover lines, timings, or hose colours in `blender/shots.py`. Then regenerate `SCRIPT.md` with `python3 blender/shots.py --markdown > SCRIPT.md`.
- Change the stage content in `blender/scene_builder.py`. Each `stage_*` function builds one stage. Every object is automatically shown only during its stage.
- Change the music, stage SFX, or voiceover ducking in `blender/music.py` (`PROGRESSIONS`, `BPM`, `add_stage_sfx`).
