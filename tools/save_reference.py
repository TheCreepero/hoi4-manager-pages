"""Store a game capture under reference/ and keep the index of that folder.

    python -I tools/save_reference.py --scene army_selection --image <capture.png> --kind vanilla
    python -I tools/save_reference.py --scene army_selection --image <capture.png> --kind mod --capture template-dropdown
    python -I tools/save_reference.py --index

reference/ keeps one capture per screen for planning a redesign and for comparing later:

    reference/vanilla/<screen>.jpg         the whole 2560x1440 frame without the mod, compressed: what is beside
                                           the panel and where it could grow
    reference/vanilla/<screen>-panel.png   the scene's crop region at 1:1 without loss: read text and measure here
    reference/mod/...                      the same for the screen as the mod last left it
    reference/manifest.csv                 game version, mod version and date of each capture
    reference/README.md                    the index, rewritten from the manifest by --index

tools/Invoke-GameCheck.ps1 -SaveReference calls this for every scene it captures. The conversion lives here
and not in tools/GameHarness.ps1 on purpose; see the note at the top of that file.
"""

import argparse
import csv
import datetime
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import guiparse as gp  # noqa: E402

from PIL import Image  # noqa: E402

REPO_ROOT = gp.REPO_ROOT
REFERENCE_DIR = os.path.join(REPO_ROOT, "reference")
MANIFEST = os.path.join(REFERENCE_DIR, "manifest.csv")
FIELDS = ["Kind", "Scene", "Capture", "Phase", "Full", "Panel", "Crop", "GameVersion", "ModVersion", "Date"]
JPEG_QUALITY = 88


def load_scene(name):
    path = name if os.path.isfile(name) else os.path.join(REPO_ROOT, "tools", "scenes", name + ".json")
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def versions():
    game = "unknown"
    game_dir = gp.find_game_dir()
    if game_dir:
        settings = os.path.join(game_dir, "launcher-settings.json")
        if os.path.isfile(settings):
            with open(settings, encoding="utf-8", errors="replace") as handle:
                game = json.load(handle).get("rawVersion", game)
    mod = "unknown"
    descriptor = os.path.join(REPO_ROOT, "descriptor.mod")
    if os.path.isfile(descriptor):
        m = re.search(r'version\s*=\s*"([^"]+)"', gp.read_text(descriptor))
        if m:
            mod = m.group(1)
    return game, mod


def read_manifest():
    if not os.path.isfile(MANIFEST):
        return []
    with open(MANIFEST, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_manifest(rows):
    rows.sort(key=lambda r: (r["Kind"], r["Phase"], r["Scene"], r["Capture"]))
    with open(MANIFEST, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n", quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)


def save(scene_name, image_path, kind, capture):
    scene = load_scene(scene_name)
    kind_dir = os.path.join(REFERENCE_DIR, kind)
    os.makedirs(kind_dir, exist_ok=True)
    base = scene["screen"] + ("-" + capture if capture else "")
    frame = Image.open(image_path).convert("RGB")
    frame.save(os.path.join(kind_dir, base + ".jpg"), "JPEG", quality=JPEG_QUALITY, optimize=True)

    x, y, w, h = [int(v) for v in scene["crop"]]
    x, y = max(0, x), max(0, y)
    w, h = min(w, frame.width - x), min(h, frame.height - y)
    frame.crop((x, y, x + w, y + h)).save(os.path.join(kind_dir, base + "-panel.png"), "PNG", optimize=True)

    game, mod = versions()
    rows = [r for r in read_manifest() if not (r["Kind"] == kind and r["Scene"] == scene["screen"] and r["Capture"] == capture)]
    rows.append({
        "Kind": kind, "Scene": scene["screen"], "Capture": capture, "Phase": str(scene.get("phase", "")),
        "Full": "%s/%s.jpg" % (kind, base), "Panel": "%s/%s-panel.png" % (kind, base), "Crop": "%d %d %d %d" % (x, y, w, h),
        "GameVersion": game, "ModVersion": mod if kind == "mod" else "", "Date": datetime.date.today().isoformat(),
    })
    write_manifest(rows)
    print("reference: reference/%s/%s.jpg and -panel.png" % (kind, base))


def scene_titles():
    titles = {}
    scenes_dir = os.path.join(REPO_ROOT, "tools", "scenes")
    for name in sorted(os.listdir(scenes_dir)):
        if not name.endswith(".json"):
            continue
        scene = load_scene(os.path.join(scenes_dir, name))
        m = re.match(r"Scene for the (.+?)\. ", scene.get("_comment", ""))
        titles[scene["screen"]] = m.group(1) if m else scene["screen"]
    return titles


def write_index():
    rows = read_manifest()
    titles = scene_titles()
    lines = [
        "# Reference captures",
        "",
        "One capture of every screen the mod works on or plans to, taken by `tools/Invoke-GameCheck.ps1 -SaveReference` at 2560x1440 in a paused 1936 game as Germany. Use them to plan a redesign, to compare before and after, and to see what a game update changed.",
        "",
        "- `vanilla/` is the game without the mod. `mod/` is the screen as the mod last left it, for the screens it has reworked.",
        "- `<screen>.jpg` is the whole frame, compressed: what is beside the panel and where it could grow.",
        "- `<screen>-panel.png` is the panel region at 1:1 without loss: read text and measure edges here, never in the JPEG.",
        "- The menu screens the harness clicks through (`reference/harness/`) stay in the 1440p UI mod; the click positions are in `tools/GameHarness.ps1`.",
        "- Split from the HOI4 1440p UI Mod on 2026-10-21: the frames the page scenes draw over (`vanilla/`), the same screens with that mod and the pages themselves (`mod/`).",
        "- `manifest.csv` records the game version and date of each capture. This file is rewritten from it; do not edit it by hand.",
        "",
        "How each screen is brought up is in [wiki/Game-Recipes.md](../wiki/Game-Recipes.md). To refresh, for example after a game update:",
        "",
        "```powershell",
        ".\\tools\\Invoke-GameCheck.ps1 -All -Vanilla -SaveReference        # every screen without the mod, about six minutes",
        ".\\tools\\Invoke-GameCheck.ps1 army_readiness -SaveReference        # one page with the mod, when its phase closes",
        "```",
        "",
        "`python -I tools\\render_gui.py --scene <screen> --over` draws a proposal on top of the vanilla frame.",
    ]
    for kind, heading in (("vanilla", "## Vanilla"), ("mod", "## With the mod")):
        kind_rows = sorted((r for r in rows if r["Kind"] == kind), key=lambda r: (r["Phase"], r["Scene"], r["Capture"]))
        if not kind_rows:
            continue
        lines += ["", heading, ""]
        if kind == "vanilla":
            lines += ["| Phase | Screen | Frame | Panel | Game | Date |", "|---|---|---|---|---|---|"]
        else:
            lines += ["| Phase | Screen | Frame | Panel | Game | Mod | Date |", "|---|---|---|---|---|---|---|"]
        for r in kind_rows:
            title = titles.get(r["Scene"], r["Scene"])
            if r["Capture"]:
                title += ", " + r["Capture"]
            frame = "[%s](%s)" % (os.path.basename(r["Full"]), r["Full"])
            panel = "[%s](%s)" % (os.path.basename(r["Panel"]), r["Panel"])
            cells = [r["Phase"], title, frame, panel, r["GameVersion"]]
            if kind == "mod":
                cells.append(r["ModVersion"])
            cells.append(r["Date"])
            lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    os.makedirs(REFERENCE_DIR, exist_ok=True)
    with open(os.path.join(REFERENCE_DIR, "README.md"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines))
    print("reference/README.md rewritten (%d captures)" % len(rows))


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--scene", help="scene name from tools/scenes/ (or a path)")
    ap.add_argument("--image", help="the capture to store, a PNG from scratch/checks")
    ap.add_argument("--kind", choices=("vanilla", "mod"), help="without the mod, or with it")
    ap.add_argument("--capture", default="", help="name of an extra capture of the scene (an opened dropdown, another tab)")
    ap.add_argument("--index", action="store_true", help="rewrite reference/README.md from the manifest")
    args = ap.parse_args(argv)
    if args.scene or args.image or args.kind:
        if not (args.scene and args.image and args.kind):
            ap.error("--scene, --image and --kind go together")
        save(args.scene, args.image, args.kind, args.capture)
    if args.index:
        write_index()
    if not (args.scene or args.index):
        ap.print_help()
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
