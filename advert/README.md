# RhyolitePrime PVC Gas Hose Advert (Blender)

A 45-second animated advert for RhyolitePrime Industrial PVC Gas Hoses, built in Blender. The sets and hoses are procedural; the characters come from the Rigify file in `rigs/`.

- `SCRIPT.md`: the advert script. It is generated from `blender/shots.py`, so edit the shot data there and regenerate with `python3 blender/shots.py --markdown > SCRIPT.md`.
- `blender/build_ad.py`: entry point. Builds the scene, renders frames, saves the `.blend`, and muxes the MP4.
- `blender/shots.py`: shot list, on-screen text, timings (9 stages x 5 s, 24 fps).
- `blender/scene_builder.py`: the Blender scene: characters, props, hoses, flames, sparks, cameras, and the on-screen overlay.
- `blender/rig_characters.py`: the characters. Each one is appended fresh from `rigs/Body Mechanics Rigs.blend` (Jack or Jill), posed with the FK controls by a small solver, and given per-part clothing and skin materials.
- `blender/geometry.py`: small mesh generators (no Blender operators needed).
- `rigs/Body Mechanics Rigs.blend`: the supplied Rigify file with the Jack and Jill models and rigs.
- `blender/music.py`: procedural background music, 96 BPM, 45 s, stdlib only.

Each application gets its own 5-second stage. An intro and an outro bookend the seven application stages. Each stage shows its key selling point in the lower third, with the product spec line and a progress bar. The music changes chord at every cut and has a bell stinger on each selling point.

## Look and feel

- Colours follow the RhyolitePrime palette: primary `#80004d` for the intro title, the wordmark and the brand; accent `#cc6699` for stage labels; light `#f8f9fa` for body text; dark `#212529` for the lower-third band; success `#4bb543` for the progress bar. The hoses keep their product colours (3/8 inch orange, 5/16 inch red and blue).
- All characters are African, with dark skin tones from the palette-led skin set (`skin_warm`, `skin_mid`, `skin_deep`). They face the camera.
- Every application stage ends with the character giving a thumbs-up. Then a smile and a green check mark (success `#4bb543`) appear, to show satisfaction and trust. The check mark is a flat mesh on the chest, with no prop in the hand.
- The welder and oxy welder wear visor helmets, leather jackets, aprons and gloves. The home cook wears an apron, and the chef wears a white jacket, toque and apron. The farmer wears a straw hat, overalls and gloves. The factory worker wears a hard hat and a hi-vis vest.

## Requirements

- Blender 5.1.2 (the scripts use the Blender 5.x Python API, for example `sequence_editor.strips`).
- Optional, for the MP4: `ffmpeg` on your PATH. You can also `pip install imageio-ffmpeg` with any Python 3.

## Build and render

Run from this folder:

```bash
# 1. Quick check: 640x360, 8 samples, all frames (roughly 15 to 40 minutes for all 1,080 frames, depending on your CPU)
blender -b --python blender/build_ad.py -- --preview

# 2. Full quality: 1920x1080, 32 samples, then ffmpeg mux to MP4
blender -b --python blender/build_ad.py

# Options
blender -b --python blender/build_ad.py -- --samples 16          # faster, a bit noisier
blender -b --python blender/build_ad.py -- --device GPU          # use a GPU if Cycles can see one
blender -b --python blender/build_ad.py -- --stage 3             # render only stage 3 (domestic)
blender -b --python blender/build_ad.py -- --build-only          # just build and save the .blend

# If you rendered without ffmpeg, mux the frames later with plain Python:
python3 blender/build_ad.py --mux-only
```

You can also open `blender/build_ad.py` in Blender's Text Editor and press Run Script. In that case the defaults apply (1920x1080, 32 samples).

Outputs go to `advert/output/` (git-ignored):

- `RhyolitePrime_Advert.blend`: the editable scene, with the music strip on the timeline. Camera markers switch the camera at each stage.
- `background_music.wav`
- `frames/frame_NNNN.png`
- `RhyolitePrime_Advert.mp4`

## Timing

Full 1080p at 32 samples is slow on CPU. Expect hours on a typical CPU and much less with a GPU. Use `--preview`, `--samples 16`, or `--stage N` while you iterate.

## Editing the advert

- Change the copy, timings, or hose colours in `blender/shots.py`. Then regenerate `SCRIPT.md`.
- Change the stage content in `blender/scene_builder.py`. Each `stage_*` function builds one stage. Every object is automatically shown only during its stage.
- Change the music in `blender/music.py` (`PROGRESSIONS`, `BPM`).

## Notes and assumptions

- The brief does not say which hose goes with which application, so the colour per stage is a creative choice (see `shots.py`).
- Oxyacetylene uses red for fuel gas and blue for oxygen. That is the common convention. Confirm it against your local standard before publishing.
- The characters use the supplied rig's mesh (about 3,000 faces each), so they are less detailed than a sculpted character. Only the arms and fingers are posed: the rig's IK constraints did not reach their targets reliably, so the arms use FK and a solver. The face has no controls or shape keys, so the smile is a curved mesh placed on the mouth. The rig has no ring-finger control, so that finger is posed directly.
- The camera and text overlay are fixed to the lens, so the title stays on screen.
- The PNG frames are muxed with ffmpeg, not Blender's built-in FFmpeg writer. That keeps the audio path simple and works with any Blender build.
- Testing: the latest changes were checked by building the scene headless with the Blender 5.0.1 Python module (build only, no render; the build takes several minutes here). The arm solver was checked against the rig: the left-hand reach target is within about 15 mm, and the thumbs-up fist within about 1 mm. The right-hand cross-body target is out of reach and was not used. Earlier builds were rendered with the same module (the newest published on PyPI), not the 5.1.2 desktop binary. The Cycles path was exercised. EEVEE and the GPU path were not tested.
