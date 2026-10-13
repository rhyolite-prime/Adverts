# RhyolitePrime PVC Gas Hose Advert — Finishing Touches Implementation Plan

This document outlines the end-to-end engineering and creative upgrades applied to make the 45-second Blender advert (`advert/`) broadcast-ready.

---

## 1. Critical Visual & Staging Fixes (`blender/scene_builder.py`)

| Issue | Root Cause | Implementation Fix |
|---|---|---|
| **Outro cuts to a blank card on frame 1080** | `Builder.overlay()` scaled every stage's title and spec text down to `(0.01, 0.01, 0.01)` between `f1 - 10` and `f1`. | Added `hold_end` handling (enabled automatically on the final `outro` stage) so the three commitments and the WhatsApp / phone / email call-to-action remain at full `1.0` scale through the final frame (`1080`). |
| **Global `Sun` light washes out dark studio & indoor stages** | A single root-level `Sun` (`energy = 2.6`) stayed active across all 9 stages, shining into the dark steel studio (Stages 1 & 9) and indoor workshop/kitchen sets. | Keyframed `Sun.energy` per stage (`0.0` in dark studio stages, softer fill in indoor sets, full golden-hour/dawn energy in Outdoor & Agriculture stages). |
| **Static characters & props during work phase (`f0` to `f1 - 36`)** | Characters were only keyframed at `f0` and `f1 - 36`, causing the oxyacetylene torch to stay frozen while `WeldBead` grew across the pipe, and causing moving conveyor crates in Stage 8 to clip through the worker's hands and floating `AirTool`. | Added multi-keyframe working actions (`work_motion`) for every stage, animated torches/utensils/tools along with the hands, moved the manufacturing worker slightly back (`y = 1.02`) so crates clear the hands, and hid/lowered handheld tools when the character transitions into the thumbs-up. |
| **Intro hose floats in mid-air** | `HoseIntro` middle control points were at `z = 1.02 m` with no support. | Reshaped the intro hose spline so it uncoils across the studio floor (`z = 0.04 m`) and sweeps into a crisp foreground underline curve beneath the rising 3D wordmark. |
| **Intro product photo desaturation under `AgX`** | `all-products.jpg` used raw emission `1.0` under `AgX`, dulling the red, blue, and yellow/orange hoses. | Added contrast/saturation-compensated emission (`sRGB` curve boost + dark backing plaque behind the primary `#80004d` frame) so the product photo pops cleanly. |

---

## 2. Product Hero Realism (`blender/scene_builder.py`, `blender/geometry.py`)

To match the physical hoses shown in `advert/images/all-products.jpg`:

1. **Three-Layer Reinforced Hose Cross-Section (`hose_end_cap`):**
   - Built a dedicated multi-material end-cap assembly placed at visible hose tips (Intro & Outro hero hoses):
     - **Outer layer:** Colored PVC jacket (`hose_orange`, `hose_red`, or `hose_blue`).
     - **Middle ring:** White braided high-tensile fiber reinforcement (`band_white`).
     - **Inner core:** Dark black rubber/PVC bore (`black`) with a recessed hollow interior.
2. **Ribbed & Braided PVC Hose Shader:**
   - Upgraded `hose_orange`, `hose_red`, and `hose_blue` in `MATERIAL_DEFS` with procedural fine ribbing/braid bump (`bump = 0.08`, `tex_scale = 140`), lower specular roughness (`rough = 0.26`), and glossy PVC clearcoat (`coat = 0.65`) so every hose catches rim highlights.
3. **Brass Hex Fittings & Crimped Ferrules (`hose` helper):**
   - Added automatic brass hex connectors and crimped sleeves at hose connection points (cylinder valves, stove/range inlets, and torch/tool couplings).

---

## 3. Character Performance & Celebration Polish (`blender/rig_characters.py`, `blender/scene_builder.py`)

1. **Active Working Motions (`f0` to `f1 - 40`):**
   - **Stage 2 (Welding & Cutting):** Welder sweeps the cutting torch steadily across the steel plate while an animated glowing kerf line (`CutKerf`) advances with the torch tip and spark emitter.
   - **Stage 3 (Oxyacetylene Welding):** Welder's hand, `OxyTorch`, `OxyFlame`, `FlameGlow`, and spark origin track along the pipe seam (`x = -0.35` to `x = +0.25`) in sync with the growing `WeldBead`.
   - **Stage 4 (Domestic Kitchen):** Home cook stirs the pot on the front burner before stepping into the thumbs-up pose.
   - **Stage 5 (Commercial Kitchen):** Chef works a spatula across the sizzling griddle before giving the thumbs-up.
   - **Stage 6 (Outdoor & Camping):** Campers tend the sausages on the portable grill with tongs before both celebrating.
   - **Stage 7 (Agriculture & Farms):** Farmer gestures to inspect the hanging gas brooder and chicks before giving the thumbs-up.
   - **Stage 8 (Manufacturing):** Factory worker actuates the pneumatic tool downward on passing crates, then lowers the tool as the left hand gives a thumbs-up.
2. **Welder Visor Flip-Up & Emissive Smile (`Person.visor`, `Person.smile`):**
   - Animated welding visors in Stages 2 & 3 to flip up onto the helmet brow at `f1 - 38` just before the smile and thumbs-up, and upgraded the smile material (`smile_white`) with clean self-illumination so it reads clearly under every lighting setup.
3. **Circular Badge for the Green Check Mark (`Person.check`):**
   - Framed the `#4bb543` check mark inside a dark-and-white circular trust badge (`check_badge`) offset toward the non-raised side of the chest so the thumbs-up arm never blocks it.

---

## 4. Cinematography, Lighting & Blender 5.x Compositor (`blender/scene_builder.py`, `blender/build_ad.py`)

1. **Blender Compositor Glare / Bloom:**
   - Configured the scene's compositor node tree (supporting both Blender 4.x and 5.x compositor APIs) with a `ShaderNodeCompositorGlare` (`FOG_GLOW`) node so welding sparks, burner flames, and the 3D wordmark have a soft cinematic glow.
2. **Camera Depth of Field (DoF) & Smooth Easing:**
   - Enabled camera Depth of Field (`f/3.6` on application stages, `f/5.6` on studio cards) focused on an animated/placed focus target per stage.
   - Applied smooth `BEZIER` keyframe interpolation to camera moves and overlay animations.
3. **Procedural Sky/Ground Gradient World (`AdWorld`):**
   - Upgraded `AdWorld` from a flat solid RGB background to a vertical horizon-to-zenith gradient so stainless steel ranges, pipes, and brass valves reflect realistic studio/environment horizons.

---

## 5. Broadcast Graphics, Typography & Outro Layout (`blender/scene_builder.py`, `blender/shots.py`)

1. **Bold Broadcast Font (`DejaVuSans-Bold.ttf`):**
   - Automatically loads `/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf` (with cross-platform fallback paths and graceful fallback to Blender's built-in font) and adds subtle text extrusion/bevel for crisp legibility.
2. **Persistent Top-Right Brand Pill:**
   - Added a `RhyolitePrime` brand badge in the top-right header bar across application stages (`Stages 2–8`) to balance the top-left stage label.
3. **High-Impact Outro Card:**
   - Added subtle glowing accent bars and persisted all contact details (`WhatsApp 055-385-9517 | Call 053-276-0832 | sales@rhyoliteprime.com`) right to the end of the video.

---

## 6. Audio: Voiceover, Diegetic SFX & Auto-Ducked Master (`blender/music.py`, `blender/shots.py`, `advert/audio/`)

1. **Spoken Voiceover Clips (`advert/audio/vo_01_intro.wav` .. `vo_09_outro.wav`):**
   - Generated 9 stage-aligned voiceover clips using the selected advertising voice (`voice-00`) and recorded the spoken script lines in `blender/shots.py` (`"voiceover"` and `"vo_file"` fields) and `SCRIPT.md`.
2. **Procedural Stage Sound Effects (`blender/music.py`):**
   - Synthesized stage-specific diegetic SFX in pure Python stdlib:
     - *Stage 2:* Torch pop + cutting gas hiss + spark crackle bursts.
     - *Stage 3:* Dual-gas torch ignition + oxyacetylene weld hum & crackle.
     - *Stage 4:* Electronic piezo igniter clicks + soft burner whoosh + pot simmer.
     - *Stage 5:* Commercial range roar + griddle sizzle.
     - *Stage 6:* Charcoal/gas grill sizzle + gentle outdoor breeze.
     - *Stage 7:* Warm brooder burner hum + soft chick peeps.
     - *Stage 8:* Rhythmic pneumatic air-tool bursts (`psht-psht`) + conveyor whirr.
     - *Stages 2–8 at `t = +3.95s`:* Bright two-tone confirmation chime synced to the green check-mark pop-in.
3. **Automatic Music Ducking & Multi-Stem VSE Timeline:**
   - `music.py` automatically ducks the instrumental bed by ~5.5 dB whenever the voiceover is speaking, outputs a clean `voiceover_track.wav` stem alongside the full mastered `background_music.wav`, and `build_ad.py` places the audio on Blender's Video Sequence Editor timeline.
