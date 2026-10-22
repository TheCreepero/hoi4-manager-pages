"""The measured part of a design's review (wiki/Design-Language.md, "Review questions"): what a tool can say about a
layout and its figures before anyone judges them.

    python -I tools/ux_audit.py A10            # scratch/phases/A10/audit.json and figures/<group>-squint.webp

Reads scratch/phases/<id>/layout.json, design.json and build/build.json, whichever exist, and writes:
  - the linter's findings (tools/lint_layout.py);
  - the contrast of every text of the layout against what stands behind it in the mock-up, as the WCAG 2 ratio of
    the glyphs' luminance to the ground's (layout.CONTRAST: 4.5, or 3 for text of 24 px and up, or 19 px and up in
    a bold font); a text the game draws with a shadow reads better than its ratio says, so a low ratio is a
    question for the review, not a verdict;
  - the fonts the layout uses, with a count each (the spread of sizes);
  - buttons smaller than 24 px on a side, where the layout gives their size or sprite;
  - per figure group, the vanilla, proposed and built figures blurred and grey (the squint test: what still
    stands out is what the eye finds first), as figures/<group>-squint.webp.
tools/make_design_page.py shows audit.json and the squinted figures on the design page. The designer runs this
before handing in, the orchestrator at gates A and B.
"""
import argparse
import json
import os
import re
import sys

from PIL import Image, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import layout as layoutmod  # noqa: E402
import lint_layout  # noqa: E402

REPO_ROOT = layoutmod.REPO_ROOT
SQUINT_BLUR = 4
SMALL_TARGET = 24
BUTTON = re.compile(r"(button|btn)", re.I)


# ---------------------------------------------------------------- contrast
def luminance(rgb):
    """WCAG 2 relative luminance of an sRGB colour."""
    def lin(c):
        c /= 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb[:3]
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def ratio(l1, l2):
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def font_class(font):
    """'large' or 'normal' from the font's name: its size in px and whether it is bold (hoi_20b, hoi_24header)."""
    m = re.match(r"^[a-z]+_(\d+)([a-z]*)$", font or "")
    if not m:
        return "normal"
    size, suffix = int(m.group(1)), m.group(2)
    bold = "b" in suffix or "header" in suffix
    return "large" if size >= 24 or (size >= 19 and bold) else "normal"


def text_of(item):
    if item["kind"] == "move":
        return item.get("sample")
    return item.get("text")


def without_text(lay):
    """The layout with every text taken out (the ground the texts stand on)."""
    out = json.loads(json.dumps(lay))
    for window in out["windows"]:
        kept = []
        for item in window.get("items", []):
            if item["kind"] in ("caption", "text"):
                continue
            if item["kind"] == "move" and (item.get("sample") or item.get("samples")):
                item.pop("sample", None)
                item.pop("samples", None)
                item["draw"] = False           # the full mock-up draws no sprite under a sample either
            kept.append(item)
        window["items"] = kept
    return out


def measure(full, ground, box):
    """(text luminance, ground luminance) inside box, or None when no glyph is drawn there."""
    a = full.crop(box).convert("RGB")
    b = ground.crop(box).convert("RGB")
    pa, pb = list(a.getdata()), list(b.getdata())
    lums = sorted(luminance(p) for p in pb)
    if not lums:
        return None
    lg = lums[len(lums) // 2]
    changed = [luminance(x) for x, y in zip(pa, pb) if sum(abs(i - j) for i, j in zip(x, y)) > 60]
    if len(changed) < 6:
        return None
    changed.sort(key=lambda l: abs(l - lg), reverse=True)
    core = changed[:max(3, len(changed) * 3 // 10)]     # the glyphs' cores, not their edges
    return sorted(core)[len(core) // 2], lg


def contrast(lay, game_dir=None):
    from mockup import Mockup
    size = tuple(lay.get("size", (2560, 1440)))
    full = Mockup(lay.get("frame"), panel=lay.get("panel"), game_dir=game_dir, size=size)
    full.draw_layout(lay)
    ground = Mockup(lay.get("frame"), panel=lay.get("panel"), game_dir=game_dir, size=size)
    ground.draw_layout(without_text(lay))
    rows = []
    for window in lay["windows"]:
        ox, oy = layoutmod.window_screen_origin(window)
        for item in layoutmod.items(window):
            text = text_of(item)
            if item["kind"] not in ("caption", "text", "move") or not text or "x" not in item:
                continue
            font = item.get("font", "hoi_18mbs")
            x, y = ox + item["x"], oy + item.get("y", 0)
            w = item.get("w") or full.text_width(font, text)
            h = full.line_height(font) + 4
            box = (int(x), int(y), int(min(x + w, full.canvas.width)), int(min(y + h, full.canvas.height)))
            if box[2] <= box[0] or box[3] <= box[1]:
                continue
            got = measure(full.canvas, ground.canvas, box)
            if not got:
                continue
            need = layoutmod.CONTRAST[font_class(font)]
            r = ratio(*got)
            rows.append({"window": window["path"], "item": item.get("name") or item.get("path", ""), "font": font,
                         "text": re.sub(r"§.", "", text)[:40], "ratio": round(r, 2), "needed": need, "ok": r >= need})
    return rows


# ---------------------------------------------------------------- fonts and targets
def fonts(lay):
    counts = {}
    for window in lay["windows"]:
        for item in layoutmod.items(window):
            if item["kind"] in ("caption", "text", "move") and item.get("font"):
                counts[item["font"]] = counts.get(item["font"], 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: -kv[1]))


def targets(lay, game_dir=None):
    small = []
    renderer = None
    for window in lay["windows"]:
        for item in layoutmod.items(window):
            if item["kind"] != "move" or not BUTTON.search(item["path"].split("/")[-1]):
                continue
            w, h = item.get("w"), item.get("h")
            if (w is None or h is None) and item.get("sprite"):
                if renderer is None:
                    from mockup import Mockup
                    renderer = Mockup(None, game_dir=game_dir, size=(8, 8))
                try:
                    tex = renderer.texture(item["sprite"])
                    sprite = renderer.renderer.sprite(item["sprite"])
                    w = w or tex.width // max(1, sprite.frames)
                    h = h or tex.height
                except Exception:      # a sprite the renderer cannot find: no size to judge
                    continue
            if w is not None and h is not None and min(w, h) < SMALL_TARGET:
                small.append({"window": window["path"], "item": item["path"], "size": [w, h]})
    return small


# ---------------------------------------------------------------- the squint figures
def squint(phase_dir):
    import make_design_page as page
    design = page.read_json(os.path.join(phase_dir, "design.json"))
    if not design:
        return []
    build = page.read_json(os.path.join(phase_dir, "build", "build.json"))
    out = []
    folder = os.path.join(phase_dir, "figures", "squint")
    os.makedirs(folder, exist_ok=True)
    for group, figs in page.figure_rows(design, build).items():
        tiles = []
        for fig in figs:
            if fig.get("kind") not in ("vanilla", "proposed", "build"):
                continue
            src = os.path.join(phase_dir, "build" if fig["folder"] == "build" else "", fig["file"])
            if not os.path.isfile(src):
                continue
            img = Image.open(src).convert("RGB").filter(ImageFilter.GaussianBlur(SQUINT_BLUR)).convert("L").convert("RGB")
            name = "%s-%s" % (fig.get("kind"), os.path.basename(fig["file"]))
            img.save(os.path.join(folder, name))
            tiles.append(dict(fig, file=os.path.join("figures", "squint", name), caption="squinted"))
        if len(tiles) >= 2:
            path = page.composite(tiles, phase_dir, os.path.join(phase_dir, "figures", "%s-squint.webp" % group))
            out.append(os.path.relpath(path, phase_dir).replace("\\", "/"))
    return out


def audit(phase_dir, game_dir=None):
    result = {"id": os.path.basename(phase_dir)}
    lay_path = os.path.join(phase_dir, "layout.json")
    if os.path.isfile(lay_path):
        lay = layoutmod.load(lay_path)
        findings = lint_layout.lint(lay)
        result["style"] = layoutmod.style(lay)
        result["lint"] = {"counts": {lv: sum(1 for f in findings if f["level"] == lv) for lv in ("error", "warn", "excepted")},
                          "findings": findings}
        result["contrast"] = contrast(lay, game_dir)
        result["fonts"] = fonts(lay)
        result["targets"] = targets(lay, game_dir)
    result["squint"] = squint(phase_dir)
    out = os.path.join(phase_dir, "audit.json")
    with open(out, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")
    return out, result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Measure a design: linter, contrast, fonts, targets, squinted figures.")
    parser.add_argument("id", help="the phase id (A10), or a path to its handoff folder")
    parser.add_argument("--phases-dir", default=os.path.join("scratch", "phases"))
    parser.add_argument("--game-dir")
    args = parser.parse_args(argv)
    folder = args.id if os.path.isdir(args.id) else os.path.join(REPO_ROOT, args.phases_dir, args.id)
    out, result = audit(os.path.abspath(folder), args.game_dir)
    lint = result.get("lint", {}).get("counts")
    low = [c for c in result.get("contrast", []) if not c["ok"]]
    print(os.path.relpath(out, REPO_ROOT))
    if lint is not None:
        print("linter: %d error(s), %d warning(s), %d excepted" % (lint["error"], lint["warn"], lint["excepted"]))
        print("contrast: %d of %d texts under the floor" % (len(low), len(result["contrast"])))
        for c in low:
            print("  %.2f < %.1f  %s %s (%s): %s" % (c["ratio"], c["needed"], c["window"], c["item"], c["font"], c["text"]))
        print("fonts: " + ", ".join("%s x%d" % kv for kv in result["fonts"].items()))
        for t in result["targets"]:
            print("small target: %s %s %dx%d" % (t["window"], t["item"], t["size"][0], t["size"][1]))
    print("squinted: " + (", ".join(result["squint"]) or "no figure group with two figures"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
