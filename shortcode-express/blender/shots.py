"""Shot list and timing definitions for the ShortCode Express ("Be Fluent") advert.

This file is the single source of truth for the 40-second Blender advert:
`scene_builder.py` and `music.py` read it directly, and running
`python3 shots.py --markdown > ../SCRIPT.md` regenerates the script table.

Timing: 7 scenes totaling 40.0 seconds at 24 fps (960 frames):
  1. Scene 1 (0:00-0:04, 4s,  96f): A dial connects a customer
  2. Scene 2 (0:04-0:09, 5s, 120f): The engineering bottleneck
  3. Scene 3 (0:09-0:13, 4s,  96f): The reveal (ShortCode Express / Sapo DSL Engine)
  4. Scene 4 (0:13-0:21, 8s, 192f): From short code to working flow (Drag. Drop. Connect.)
  5. Scene 5 (0:21-0:29, 8s, 192f): Connect the services behind the menu (Plugin marketplace)
  6. Scene 6 (0:29-0:35, 6s, 144f): Engineering control, not just a canvas
  7. Scene 7 (0:35-0:40, 5s, 120f): The customer outcome and brand close
"""

FPS = 24
BPM = 96

SHOTS = [
    {
        "id": "dial_connects",
        "seconds": 4.0,
        "label": "THE VITAL CONNECTION",
        "title": "A simple dial. A vital connection.",
        "spec": "*714*14#   |   Welcome:  1. Pay merchant   2. Check balance",
        "voiceover": "Africa moves money with a dial.",
        "vo_file": "vo_01_dial.wav",
        "visual": (
            "Warm neighborhood shop. A customer dials *714*14# on a basic feature phone while a "
            "merchant waits across the counter. The USSD menu ('Welcome / 1. Pay merchant / "
            "2. Check balance') lights up on the keypad phone, and a glowing signal pulse travels "
            "outward toward the network."
        ),
        "characters": "African customer with a basic feature phone and shop merchant across the counter.",
        "music": "Tactile DTMF keypad clicks (*714*14#) over a low, grounded rhythmic pulse and signal sweep.",
    },
    {
        "id": "engineering_bottleneck",
        "seconds": 5.0,
        "label": "THE BOTTLENECK",
        "title": "More branches. More complexity.",
        "spec": "if (input == '1') { else if (state == 'ERR') ... }   |   New menu · API error · Another change",
        "voiceover": "But while apps got frameworks, USSD got endless if-else.",
        "vo_file": "vo_02_bottleneck.wav",
        "visual": (
            "Dimly lit engineering workstation. Deeply nested if-else blocks extend out of the "
            "monitor into a tangled 3D web of crossing red and amber branches surrounded by "
            "floating 'New menu', 'API error', and 'Another change' alerts. The engineer rubs "
            "their forehead in restrained frustration and pauses with both hands over the keyboard."
        ),
        "characters": "African software engineer at a dual-monitor workstation.",
        "music": "Accelerating mechanical keyboard clacks and tense rising minor pulse that cuts cleanly.",
    },
    {
        "id": "the_reveal",
        "seconds": 4.0,
        "label": "INTRODUCING SHORTCODE EXPRESS",
        "title": "Visual USSD development.",
        "spec": "ShortCode Express   |   Powered by Sapo DSL Engine",
        "voiceover": "Meet ShortCode Express. Powered by Sapo DSL Engine.",
        "vo_file": "vo_03_reveal.wav",
        "visual": (
            "The workstation opens up into bright, confident lighting. Tangled red branches "
            "straighten into sleek glowing connectors and structured 3D flow nodes in front of "
            "the ShortCode Express Flow Builder ('flow-builder.png'). The 3D ShortCode Express "
            "wordmark and 'Powered by Sapo DSL Engine' badge rise above the scene as the engineer "
            "moves purposefully to the mouse."
        ),
        "characters": "African software engineer straightening posture and guiding the visual flow.",
        "music": "Crisp transition hit resolving into a bright C-major / G-major groove with harmonic shimmer.",
    },
    {
        "id": "short_code_to_flow",
        "seconds": 8.0,
        "label": "VISUAL FLOW BUILDER",
        "title": "Design the journey. Not the boilerplate.",
        "spec": "Get a short code (*714*14#) or port yours   |   Drag · Drop · Connect",
        "voiceover": "Get a short code—or bring yours. Drag. Drop. Connect. Build USSD flows without writing code.",
        "vo_file": "vo_04_flow_builder.wav",
        "visual": (
            "Product showcase stage. Starts with the short-code provisioning screen "
            "('onboarding-acquiring-porting-buy_code.png') highlighting 'Get a short code (*714*14#)' "
            "and 'Port a code I own', then transitions to the visual Flow Builder ('flow-builder.png'). "
            "3D Menu, Prompt, and Condition nodes Drag onto the canvas, Drop with a snap, and Connect "
            "with glowing splines while a 3D phone simulator updates live."
        ),
        "characters": "African software engineer at the side console making a connecting gesture.",
        "music": "Driving groove with three synchronized UI snap tones on 'Drag', 'Drop', and 'Connect'.",
    },
    {
        "id": "plugin_marketplace",
        "seconds": 8.0,
        "label": "PLUGIN MARKETPLACE & EXTENSIBILITY",
        "title": "Connect existing services. Extend with your own.",
        "spec": "Mobile Money · Core Banking · SMS / OTP · KYC · Your Plugin   |   Vouchers · Commerce · Logistics",
        "voiceover": (
            "Connect mobile money, banking, SMS, and KYC through the plugin marketplace. "
            "Need something unique? Build your own plugin."
        ),
        "vo_file": "vo_05_plugins.wav",
        "visual": (
            "The Flow Builder canvas stays open as the Plugin Marketplace panel appears beside it. "
            "3D service tiles ('Mobile Money', 'Core Banking', 'SMS / OTP', 'KYC') snap into the "
            "payment flow as a glowing data pulse travels from Customer Input -> Integration -> Result. "
            "A teammate leans in and points as a custom 'Your Plugin' node joins the canvas above "
            "'OTP · Vouchers · Commerce · Logistics' category pills."
        ),
        "characters": "Lead engineer and teammate collaborating at the workflow station.",
        "music": "Energetic stereo arpeggio lead with magnetic connection clicks and data-pulse shimmer.",
    },
    {
        "id": "engineering_control",
        "seconds": 6.0,
        "label": "OPERATIONAL CONTROL",
        "title": "Test clearly. Release deliberately. Stay in control.",
        "spec": "Simulate · Validate · Deploy · Track sessions (90.3% completion) · Roll back with confidence",
        "voiceover": "Simulate. Validate. Deploy. Track sessions. Roll back with confidence.",
        "vo_file": "vo_06_control.wav",
        "visual": (
            "Five-beat operational sequence: (1) Simulate on the 3D feature phone; (2) Validate "
            "with a green 'v1.0.0 Validated' badge; (3) Deploy with the '#80004d' Release button; "
            "(4) Track sessions on the live Operations Dashboard ('dashboard.png', 90.3% completion "
            "rate and 3D telemetry bars); (5) Roll back with confidence via the release rollback card."
        ),
        "characters": "Engineer and teammate reviewing the Operations Dashboard with an approving nod.",
        "music": "Five precise confirmation tones synced to Simulate, Validate, Deploy, Track, and Roll back.",
    },
    {
        "id": "customer_outcome_outro",
        "seconds": 5.0,
        "label": "SHORTCODE EXPRESS",
        "title": "ShortCode Express — Be fluent.\nBuild your first USSD flow.",
        "spec": "rhyoliteprime.com   |   Powered by Sapo DSL Engine",
        "voiceover": "Build beyond the smartphone. ShortCode Express. Be fluent.",
        "vo_file": "vo_07_outro.wav",
        "visual": (
            "Return to the shop as the customer's phone displays 'Payment successful' and both "
            "customer and merchant smile and give a thumbs-up with circular green check badges. "
            "A glowing workflow connector sweeps across the frame to underline the 3D ShortCode Express "
            "wordmark, 'Be fluent.' tagline, and persistent 'Build your first USSD flow | rhyoliteprime.com' "
            "call to action."
        ),
        "characters": "African customer and merchant smiling with thumbs-up and green check badges.",
        "music": "Payment confirmation chime resolving into a warm C-major sonic signature.",
    },
]


def total_seconds():
    return sum(s["seconds"] for s in SHOTS)


def total_frames():
    return int(round(total_seconds() * FPS))


def stage_times(index):
    start = sum(s["seconds"] for s in SHOTS[:index])
    return start, start + SHOTS[index]["seconds"]


def stage_frames(index):
    t0, t1 = stage_times(index)
    f0 = 1 + int(round(t0 * FPS))
    f1 = int(round(t1 * FPS))
    return f0, f1


def timecode(seconds):
    m, s = divmod(int(round(seconds)), 60)
    return f"{m:02d}:{s:02d}"


def display_label(label):
    return label.title().replace("Shortcode", "ShortCode").replace("Ussd", "USSD")


def markdown():
    total = total_seconds()
    lines = []
    lines.append("# ShortCode Express — “Build Beyond the Smartphone” (Blender Advert Script)")
    lines.append("")
    lines.append(
        f"**Runtime:** {int(total)} seconds ({total_frames()} frames at {FPS} fps), 1920x1080, "
        f"{len(SHOTS)} scenes."
    )
    lines.append("")
    lines.append(
        "**Campaign:** “Be Fluent” — ShortCode Express (Powered by Sapo DSL Engine) from RhyolitePrime."
    )
    lines.append("")
    lines.append("## Shot list")
    lines.append("")
    lines.append("| Time | Scene | On-screen headline | Spec / Sub-line | Voiceover |")
    lines.append("|---|---|---|---|---|")
    for i, shot in enumerate(SHOTS):
        start, end = stage_times(i)
        title = shot["title"].replace("\n", " / ")
        vo = shot.get("voiceover", "")
        lines.append(
            f"| {timecode(start)}-{timecode(end)} | {display_label(shot['label'])} | {title} | "
            f"{shot['spec'].replace('|', chr(92) + '|')} | {vo} |"
        )
    lines.append("")
    for i, shot in enumerate(SHOTS):
        start, end = stage_times(i)
        lines.append(f"## Scene {i + 1}. {display_label(shot['label'])} ({timecode(start)}-{timecode(end)})")
        lines.append("")
        lines.append(f"**On-screen text:** {shot['title'].replace(chr(10), ' / ')}")
        lines.append("")
        lines.append(f"**Sub-line:** {shot['spec']}")
        lines.append("")
        lines.append(f"**Voiceover (`{shot.get('vo_file', '')}`):** \"{shot.get('voiceover', '')}\"")
        lines.append("")
        lines.append(f"**Visual:** {shot['visual']}")
        lines.append("")
        lines.append(f"**Characters:** {shot['characters']}")
        lines.append("")
        lines.append(f"**Music & SFX cue:** {shot['music']}")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    if "--markdown" in sys.argv:
        print(markdown())
    else:
        for i, s in enumerate(SHOTS):
            t0, t1 = stage_times(i)
            print(f"Scene {i + 1}: {s['id']} ({timecode(t0)}-{timecode(t1)}) -> {s['title'].replace(chr(10), ' / ')}")
