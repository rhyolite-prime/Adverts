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
        "title": "High Quality Industrial PVC Gas Hose\nfrom Rhyolite Prime",
        "spec": "RhyolitePrime Industrial PVC Gas Hoses",
        "hose": "orange",
        "visual": (
            "Dark steel studio. An orange 3/8 inch hose uncoils from the centre of the frame, "
            "sweeps across the floor and forms an underline as the RhyolitePrime wordmark rises "
            "in 3D. The camera pushes in slowly."
        ),
        "characters": "None",
        "music": "Intro groove fades in on a C major / A minor pad, with a bell stinger on the title.",
    },
    {
        "id": "welding_cutting",
        "label": "WELDING & CUTTING",
        "title": "Consistent performance under pressure",
        "spec": "3/8 inch PVC gas hose | Orange",
        "hose": "orange",
        "visual": (
            "Fabrication workshop. A welder in a dark helmet cuts a steel plate on a workbench "
            "with a cutting torch. Sparks spray across the frame. An orange hose runs from a "
            "gas cylinder on a trolley to the torch."
        ),
        "characters": "Welder in a helmet and work jacket",
        "music": "Bass and clap drive in; sparks are synced to the hi-hats.",
    },
    {
        "id": "oxyacetylene",
        "label": "OXYACETYLENE WELDING",
        "title": "Built for high-pressure industrial work",
        "spec": "5/16 inch PVC gas hose | Red (fuel) and blue (oxygen)",
        "hose": "red_blue",
        "visual": (
            "Two cylinders on a cart, one red (fuel) and one blue (oxygen). Red and blue 5/16 inch "
            "hoses run to a welding torch. The welder lights a bright flame and runs a bead along "
            "a pipe seam, and the glow flickers."
        ),
        "characters": "Welder with a torch and gloves",
        "music": "Arpeggio lead enters over the progression.",
    },
    {
        "id": "domestic",
        "label": "DOMESTIC GAS CONNECTIONS",
        "title": "Reliable, safety-focused connections at home",
        "spec": "3/8 inch PVC gas hose | Orange",
        "hose": "orange",
        "visual": (
            "Bright home kitchen. A cook in an apron lights a four-burner stove. An orange hose runs "
            "from a cylinder behind the cabinet to the stove inlet. Blue burner flames glow under a pot."
        ),
        "characters": "Home cook in an apron",
        "music": "Warm, lighter section with a soft hi-hat pattern.",
    },
    {
        "id": "commercial_kitchen",
        "label": "COMMERCIAL & INDUSTRIAL KITCHENS",
        "title": "Long service life, even in busy kitchens",
        "spec": "3/8 inch PVC gas hose | Orange",
        "hose": "orange",
        "visual": (
            "Busy restaurant kitchen. A chef works a range with a griddle and a deep fryer under an "
            "extraction hood. Steam rises while an orange hose feeds the range from the wall."
        ),
        "characters": "Chef in a white jacket and toque",
        "music": "Full groove with a bright lead.",
    },
    {
        "id": "outdoor_camping",
        "label": "OUTDOOR & CAMPING",
        "title": "Built to withstand the outdoors",
        "spec": "5/16 inch PVC gas hose | Red",
        "hose": "red",
        "visual": (
            "Campsite at golden hour, with pine trees and a tent. Two campers cook on a portable gas "
            "grill fed by a red hose from a propane cylinder. A small generator and camp stove sit nearby."
        ),
        "characters": "Two campers, one seated on a log",
        "music": "Tempo steady, with a higher melody over the chords.",
    },
    {
        "id": "agriculture",
        "label": "AGRICULTURE & FARMS",
        "title": "Dependable supply for farm operations",
        "spec": "3/8 inch PVC gas hose | Orange",
        "hose": "orange",
        "visual": (
            "Poultry house at dawn. A farmer checks a gas brooder heater hanging above a group of "
            "chicks. An orange hose runs through the wall from an outside cylinder. A crop dryer "
            "burner glows in the next bay."
        ),
        "characters": "Farmer in a straw hat and overalls, with chicks",
        "music": "Mellow arrangement with a gentle bass line.",
    },
    {
        "id": "manufacturing",
        "label": "MANUFACTURING & INDUSTRIAL LINES",
        "title": "Non-corrosive gases and compressed air",
        "spec": "5/16 inch PVC gas hose | Blue",
        "hose": "blue",
        "visual": (
            "Factory floor. Boxes move along a conveyor past a furnace. A worker in a hard hat uses a "
            "pneumatic tool, and a blue 5/16 inch hose carries compressed air from an overhead pipe rack."
        ),
        "characters": "Factory worker in a hard hat and hi-vis vest",
        "music": "Driving rhythm with a rising filter.",
    },
    {
        "id": "outro",
        "label": "WHY RHYOLITEPRIME",
        "title": "Competitive bulk pricing\nReliable availability\nResponsive technical support",
        "spec": "WhatsApp 055-385-9517   |   Call 053-276-0832   |   sales@rhyoliteprime.com",
        "hose": "orange",
        "visual": (
            "Back to the dark studio. The orange hose from the intro loops into a circle and the three "
            "commitments appear one by one. The wordmark returns as the final card."
        ),
        "characters": "None",
        "music": "Resolves to a C major chord with a long tail.",
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
        "**Music:** one background track (96 BPM, C major / A minor) that runs under the whole advert. "
        "Each stage has its own chord change and a bell stinger on the stage's key selling point."
    )
    lines.append("")
    lines.append(APPLICATIONS_NOTE)
    lines.append("")
    lines.append("## Shot list")
    lines.append("")
    lines.append("| Time | Stage | Key selling point (on screen) | Spec line (on screen) |")
    lines.append("|---|---|---|---|")
    for i, shot in enumerate(SHOTS):
        start, end = stage_times(i)
        title = shot["title"].replace("\n", " / ")
        lines.append(f"| {timecode(start)}-{timecode(end)} | {display_label(shot['label'])} | {title} | {shot['spec'].replace('|', chr(92) + '|')} |")
    lines.append("")
    for i, shot in enumerate(SHOTS):
        start, end = stage_times(i)
        lines.append(f"## {i + 1}. {display_label(shot['label'])} ({timecode(start)}-{timecode(end)})")
        lines.append("")
        lines.append(f"**Key selling point on screen:** {shot['title'].replace(chr(10), ' / ')}")
        lines.append("")
        lines.append(f"**Spec line:** {shot['spec']}")
        lines.append("")
        lines.append(f"**Visual:** {shot['visual']}")
        lines.append("")
        lines.append(f"**Characters:** {shot['characters']}")
        lines.append("")
        lines.append(f"**Music cue:** {shot['music']}")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    if "--markdown" in sys.argv:
        print(markdown())
    else:
        for i, s in enumerate(SHOTS):
            print(i, s["id"], timecode(stage_times(i)[0]), s["title"].replace("\n", " / "))
