"""Shot list for the RhyolitePrime PVC gas hose advert.

This file is the single source of truth for the advert: the Blender builder
reads it to build the scenes, and `python3 shots.py --markdown` regenerates
../SCRIPT.md from it so the written script and the animation never drift apart.

Timing: 9 stages x 5 seconds at 24 fps = 45 seconds (1080 frames).
Music: 96 BPM, 4/4, so each 5 second stage is exactly two bars.
"""

FPS = 24
SHOT_SECONDS = 5.0
BPM = 96

# Product specs from the RhyolitePrime sheet:
#   3/8 inch PVC gas hose: orange
#   5/16 inch PVC gas hose: red and blue
# The colour assigned to each application below is a creative choice (the
# brief does not say which hose goes where). Oxyacetylene uses red for fuel gas
# and blue for oxygen, which is the common convention; confirm against the
# local standard before publishing.

SHOTS = [
    {
        "id": "intro",
        "label": "INTRODUCING",
        "title": "High Quality Industrial PVC Gas Hose\nfrom RhyolitePrime",
        "spec": "RhyolitePrime Industrial PVC Gas Hoses",
        "hose": "orange",
        "voiceover": "Introducing high-quality industrial PVC gas hoses, from RhyolitePrime.",
        "vo_file": "vo_01_intro.wav",
        "visual": (
            "Dark steel studio. An orange 3/8 inch hose with a visible three-layer reinforced "
            "cross-section (black inner bore, white braided reinforcement, orange PVC jacket) "
            "uncoils across the floor and forms an underline as the RhyolitePrime wordmark rises "
            "in 3D. A framed product photo of the red, blue and yellow hoses pops in above the "
            "wordmark. The camera pushes in smoothly."
        ),
        "characters": "None",
        "music": "Intro groove fades in on a C major / A minor pad with a hose uncoil whoosh, bell stinger, and voiceover.",
    },
    {
        "id": "welding_cutting",
        "label": "WELDING & CUTTING",
        "title": "Consistent performance under pressure",
        "spec": "3/8 inch PVC gas hose | Orange",
        "hose": "orange",
        "voiceover": "For welding and cutting, consistent performance under intense pressure.",
        "vo_file": "vo_02_welding_cutting.wav",
        "visual": (
            "Fabrication workshop. A welder in a dark helmet sweeps a cutting torch across a steel "
            "plate on a workbench, leaving a glowing cut kerf. Sparks spray from the moving torch tip. "
            "An orange hose with brass fittings runs from a gas cylinder on a trolley to the torch."
        ),
        "characters": (
            "African welder in a visor helmet, leather jacket, apron and gloves. Flips up the visor "
            "and ends with a thumbs-up, a bright smile and a circular green check badge."
        ),
        "music": "Bass and clap drive in with torch ignition, cutting hiss, and spark crackle.",
    },
    {
        "id": "oxyacetylene",
        "label": "OXYACETYLENE WELDING",
        "title": "Built for high-pressure industrial work",
        "spec": "5/16 inch PVC gas hose | Red (fuel) and blue (oxygen)",
        "hose": "red_blue",
        "voiceover": "Twin red and blue hoses, built for high-pressure oxyacetylene work.",
        "vo_file": "vo_03_oxyacetylene.wav",
        "visual": (
            "Two cylinders on a cart, one red (fuel) and one blue (oxygen). Red and blue 5/16 inch "
            "hoses with brass fittings run to a welding torch. The welder lights a bright flame and "
            "tracks the torch along a pipe seam as the glowing weld bead advances."
        ),
        "characters": (
            "African welder in a visor helmet, leather jacket, apron and gloves. Flips up the visor "
            "and ends with a thumbs-up, a bright smile and a circular green check badge."
        ),
        "music": "Arpeggio lead enters over the progression with oxyacetylene torch hum and weld crackle.",
    },
    {
        "id": "domestic",
        "label": "DOMESTIC GAS CONNECTIONS",
        "title": "Reliable, safety-focused connections at home",
        "spec": "3/8 inch PVC gas hose | Orange",
        "hose": "orange",
        "voiceover": "In the home kitchen, reliable, safety-focused gas connections every day.",
        "vo_file": "vo_04_domestic.wav",
        "visual": (
            "Bright home kitchen. A cook in an apron stirs a simmering pot on a four-burner stove. "
            "An orange hose with brass fittings runs from a cylinder beside the cabinet to the stove "
            "inlet. Blue burner flames glow under the pot as gentle steam rises."
        ),
        "characters": "African home cook in an apron. Ends with a thumbs-up, a smile and a circular green check badge.",
        "music": "Warm, lighter section with piezo igniter clicks, burner whoosh, and soft simmer.",
    },
    {
        "id": "commercial_kitchen",
        "label": "COMMERCIAL & INDUSTRIAL KITCHENS",
        "title": "Long service life, even in busy kitchens",
        "spec": "3/8 inch PVC gas hose | Orange",
        "hose": "orange",
        "voiceover": "Engineered for long service life, even in the busiest commercial kitchens.",
        "vo_file": "vo_05_commercial_kitchen.wav",
        "visual": (
            "Busy restaurant kitchen. A chef works a stainless range and griddle with a spatula "
            "beside a deep fryer under an extraction hood. Steam rises while an orange hose with "
            "brass fittings feeds the range from the wall manifold."
        ),
        "characters": "African chef in a white jacket, toque and apron. Ends with a thumbs-up, a smile and a circular green check badge.",
        "music": "Full groove with a bright lead and commercial griddle sizzle.",
    },
    {
        "id": "outdoor_camping",
        "label": "OUTDOOR & CAMPING",
        "title": "Built to withstand the outdoors",
        "spec": "5/16 inch PVC gas hose | Red",
        "hose": "red",
        "voiceover": "Tough, weather-resistant hoses, built to withstand the great outdoors.",
        "vo_file": "vo_06_outdoor_camping.wav",
        "visual": (
            "Campsite at golden hour, with pine trees and a tent. Two campers turn sausages on a "
            "portable gas grill fed by a red hose from a propane cylinder. A small generator and "
            "camp stove sit nearby."
        ),
        "characters": (
            "Two African campers by the grill: one in a hi-vis jacket, one in overalls and a straw hat. "
            "Both end with a thumbs-up, a smile and a circular green check badge."
        ),
        "music": "Tempo steady, with a higher melody over the chords and outdoor grill sizzle.",
    },
    {
        "id": "agriculture",
        "label": "AGRICULTURE & FARMS",
        "title": "Dependable supply for farm operations",
        "spec": "3/8 inch PVC gas hose | Orange",
        "hose": "orange",
        "voiceover": "Dependable gas supply to keep agricultural and farm operations running.",
        "vo_file": "vo_07_agriculture.wav",
        "visual": (
            "Poultry house at dawn. A farmer checks a gas brooder heater hanging above a group of "
            "chicks. An orange hose with brass fittings runs from a cylinder to the brooder hood. "
            "A crop dryer burner glows in the next bay."
        ),
        "characters": "African farmer in a straw hat, overalls and leather gloves, with chicks. Ends with a thumbs-up, a smile and a circular green check badge.",
        "music": "Mellow arrangement with a gentle bass line, brooder hum, and soft chick peeps.",
    },
    {
        "id": "manufacturing",
        "label": "MANUFACTURING & INDUSTRIAL LINES",
        "title": "Non-corrosive gases and compressed air",
        "spec": "5/16 inch PVC gas hose | Blue",
        "hose": "blue",
        "voiceover": "Ideal for manufacturing lines, non-corrosive gases, and compressed air.",
        "vo_file": "vo_08_manufacturing.wav",
        "visual": (
            "Factory floor. Boxes move along a conveyor past a glowing furnace. A worker in a hard hat "
            "actuates a pneumatic tool on passing crates as a blue 5/16 inch hose carries compressed "
            "air from an overhead pipe rack."
        ),
        "characters": "African factory worker in a hard hat, hi-vis vest and gloves. Ends with a thumbs-up, a smile and a circular green check badge.",
        "music": "Driving rhythm with rhythmic pneumatic air bursts and a rising filter.",
    },
    {
        "id": "outro",
        "label": "WHY RHYOLITEPRIME",
        "title": "Competitive bulk pricing\nReliable availability\nResponsive technical support",
        "spec": "WhatsApp 055-385-9517   |   Call 053-276-0832   |   sales@rhyoliteprime.com",
        "hose": "orange",
        "voiceover": "RhyolitePrime. Bulk pricing, reliable stock, and responsive support.",
        "vo_file": "vo_09_outro.wav",
        "visual": (
            "Back to the dark studio. The orange three-layer reinforced hose loops into a hero emblem "
            "as the three commitments appear one by one and hold on screen alongside the RhyolitePrime "
            "wordmark and contact details."
        ),
        "characters": "None",
        "music": "Resolves to a C major chord with a long resonant tail.",
    },
]

APPLICATIONS_NOTE = (
    "Each application gets its own 5 second stage. The intro and outro bookend "
    "the seven application stages and can be removed from SHOTS if not needed."
)


def display_label(label):
    return label.title().replace("Rhyoliteprime", "RhyolitePrime")


def stage_times(index):
    start = index * SHOT_SECONDS
    return start, start + SHOT_SECONDS


def timecode(seconds):
    m, s = divmod(int(round(seconds)), 60)
    return f"{m:02d}:{s:02d}"


def markdown():
    total = SHOT_SECONDS * len(SHOTS)
    lines = []
    lines.append("# RhyolitePrime Industrial PVC Gas Hoses: Advert Script")
    lines.append("")
    lines.append(f"**Runtime:** {int(total)} seconds, 1920x1080, {FPS} fps, {len(SHOTS)} stages of {int(SHOT_SECONDS)} seconds each.")
    lines.append("")
    lines.append(
        "**Music & Audio:** one background track (96 BPM, C major / A minor) with stage-specific diegetic "
        "sound effects, a bell stinger on each key selling point, and a spoken voiceover track (`advert/audio/`) "
        "with automatic music ducking."
    )
    lines.append("")
    lines.append(APPLICATIONS_NOTE)
    lines.append("")
    lines.append("## Shot list")
    lines.append("")
    lines.append("| Time | Stage | Key selling point (on screen) | Spec line (on screen) | Voiceover |")
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
        lines.append(f"## {i + 1}. {display_label(shot['label'])} ({timecode(start)}-{timecode(end)})")
        lines.append("")
        lines.append(f"**Key selling point on screen:** {shot['title'].replace(chr(10), ' / ')}")
        lines.append("")
        lines.append(f"**Spec line:** {shot['spec']}")
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
            print(i, s["id"], timecode(stage_times(i)[0]), s["title"].replace("\n", " / "))
