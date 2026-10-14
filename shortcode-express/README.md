# ShortCode Express — “Build Beyond the Smartphone” (40s Blender Advert)

A procedural **Blender 5.x** 3D animation pipeline for the **40-second (960 frames at 24 fps) ShortCode Express ("Be Fluent") advert**, built directly from [`shortcode_express_ad.md`](shortcode_express_ad.md) and the three real product screenshots (`onboarding-acquiring-porting-buy_code.png`, `flow-builder.png`, and `dashboard.png`).

---

## 1. Campaign & 7-Scene Timeline (40.0 Seconds)

| Scene | Time | Frames | On-Screen Headline | Voiceover (`audio/vo_*.wav`) | Visual & 3D Action |
|---|---|---|---|---|---|
| **1. A dial connects a customer** | `0:00–0:04` (`4s`) | `1–96` | **A simple dial. A vital connection.** | *"Africa moves money with a dial."* | Warm neighborhood shop. Customer dials `*714*14#` on a 3D feature phone (`Welcome / 1. Pay merchant / 2. Check balance`) while merchant nods across the counter. Outgoing signal pulse rings expand from the phone. |
| **2. The engineering bottleneck** | `0:04–0:09` (`5s`) | `97–216` | **More branches. More complexity.** | *"But while apps got frameworks, USSD got endless if-else."* | Dark engineering workstation. Nested `if / else if / else` blocks extend out of the monitor as a tangled 3D web of red/amber tubes with `New menu`, `API error`, and `Another change` alerts. Engineer rubs forehead in restrained frustration. |
| **3. The reveal** | `0:09–0:13` (`4s`) | `217–312` | **Visual USSD development.** | *"Meet ShortCode Express. Powered by Sapo DSL Engine."* | Workstation opens into bright lighting with `flow-builder.png`, 3D `ShortCode Express / Powered by Sapo DSL Engine` monument, and untangled 3D flow nodes (`MENU`, `CONDITION`, `HTTP API`). |
| **4. From short code to working flow** | `0:13–0:21` (`8s`) | `313–504` | **Design the journey. Not the boilerplate.** | *"Get a short code—or bring yours. Drag. Drop. Connect. Build USSD flows without writing code."* | Shows `onboarding-acquiring-porting-buy_code.png` (`Get a short code *714*14#` / `Bring an existing code`) and `flow-builder.png` with 3D nodes animating on **Drag**, **Drop**, and **Connect**, updating a live 3D phone simulator. |
| **5. Connect the services behind the menu** | `0:21–0:29` (`8s`) | `505–696` | **Connect existing services. Extend with your own.** | *"Connect mobile money, banking, SMS, and KYC through the plugin marketplace. Need something unique? Build your own plugin."* | Lead engineer and teammate collaborate as 3D `Mobile Money`, `Core Banking`, `SMS / OTP`, `KYC`, and `Your Plugin` cards snap into the payment route above `OTP · Vouchers · Commerce · Logistics`. |
| **6. Engineering control, not just a canvas** | `0:29–0:35` (`6s`) | `697–840` | **Test clearly. Release deliberately. Stay in control.** | *"Simulate. Validate. Deploy. Track sessions. Roll back with confidence."* | 5-beat operational sequence (`Simulate`, `Validate`, `Deploy`, `Track sessions` on `dashboard.png` with `90.3%` completion rate, and `Roll back with confidence`). |
| **7. The customer outcome and brand close** | `0:35–0:40` (`5s`) | `841–960` | **ShortCode Express — Be fluent. / Build your first USSD flow.** | *"Build beyond the smartphone. ShortCode Express. Be fluent."* | Return to the shop as the customer's phone shows `Payment successful ✓`. Both customer and merchant smile and give a thumbs-up beside the 3D `ShortCode Express` end card (`rhyoliteprime.com`). |

---

## 2. Directory Layout

```text
shortcode-express/
├── shortcode_express_ad.md                        # Campaign brief & implementation plan
├── SCRIPT.md                                      # Generated shot-by-shot script table
├── README.md                                      # Build & render instructions
├── dashboard.png                                  # Operations dashboard UI texture
├── flow-builder.png                               # Visual Flow Builder UI texture
├── onboarding-acquiring-porting-buy_code.png      # Short-code provisioning UI texture
├── audio/
│   ├── vo_01_dial.wav                             # Scene 1 voiceover (0:00–0:04)
│   ├── vo_02_bottleneck.wav                       # Scene 2 voiceover (0:04–0:09)
│   ├── vo_03_reveal.wav                           # Scene 3 voiceover (0:09–0:13)
│   ├── vo_04_flow_builder.wav                     # Scene 4 voiceover (0:13–0:21)
│   ├── vo_05_plugins.wav                          # Scene 5 voiceover (0:21–0:29)
│   ├── vo_06_control.wav                          # Scene 6 voiceover (0:29–0:35)
│   └── vo_07_outro.wav                            # Scene 7 voiceover (0:35–0:40)
└── blender/
    ├── build_ad.py                                # CLI entry point (.blend, audio, frames, MP4)
    ├── scene_builder.py                           # 7 3D stages, UI screens, cameras, lights, compositor
    ├── rig_characters.py                          # Rigged Jack & Jill with 3D eyes, eyelids, brows & nose
    ├── geometry.py                                # Procedural 3D mesh primitives
    ├── music.py                                   # 40s soundtrack + DTMF/typing/UI SFX + auto-ducked VO
    └── shots.py                                   # Single source of truth for shot timings & copy
```

---

## 3. Building & Rendering

### Build `.blend` + Mastered Audio Only

```bash
python3 shortcode-express/blender/build_ad.py --build-only
```

Produces:
- `shortcode-express/output/ShortCodeExpress_Advert.blend` (with packed UI screenshots and VSE audio tracks)
- `shortcode-express/output/background_music.wav` (mastered 40s stereo soundtrack + SFX + auto-ducked voiceover)
- `shortcode-express/output/voiceover_track.wav` (isolated 40s voiceover stem)

### Fast 7-Scene Preview Render + MP4

```bash
python3 shortcode-express/blender/build_ad.py --preview --width 960 --height 540 --samples 24
```

### Full 40-Second (960-Frame) 1080p Master Render

```bash
python3 shortcode-express/blender/build_ad.py --width 1920 --height 1080 --samples 64
```
