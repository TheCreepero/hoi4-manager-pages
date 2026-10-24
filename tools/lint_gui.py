"""Hold the written pages (interface/mod1440_*.gui) to the ruleset of wiki/Design-Language.md: what tools/lint_layout.py
does for a proposal, done for what ships.

    python -I tools/lint_gui.py
    python -I tools/lint_gui.py --json scratch/lint_gui.json

Each top-level window is judged in its own look: the steel look when it stands on the steel ground, the card look
otherwise. Rules: `font` (a font outside the look), `row` (a band of a table whose rows are not 24, 32 or 48 high),
`title` (a title strip of another height than the look's), `close` (a close button away from the strip's right edge),
`look` (a page still in the card look; a warning, since the pages move to steel one phase at a time).

A deviation the pages have today is listed in tools/design_exceptions.json with its reason: {"rule", "window",
"item", "why"}, the item being the font, the sprite of the band, the strip or the button; window and item may be
patterns ("mod1440_records_*") where one cause covers several. A listed finding is reported
as excepted; a finding that is not listed, and an exception that no longer matches a finding, fail. Exit 1 then.
"""
import argparse
import fnmatch
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guiparse  # noqa: E402
import layout as layoutmod  # noqa: E402
from lint_layout import finding  # noqa: E402

REPO_ROOT = layoutmod.REPO_ROOT
EXCEPTIONS = os.path.join(REPO_ROOT, "tools", "design_exceptions.json")
TITLE_HEIGHT = {"card": 44, "steel": 46}
BAND = re.compile(r"^GFX_1440p_SG_(?:stripe|pick)_(\d+)x(\d+)$")
WIDGETS = ("containerwindowtype", "windowtype", "instanttextboxtype", "textboxtype", "buttontype", "icontype", "gridboxtype")


def position(node):
    at = node.block("position")
    if at is None:
        return 0, 0
    return int(guiparse.number(at.get("x"), 0)), int(guiparse.number(at.get("y"), 0))


def size(node):
    of = node.block("size")
    if of is None:
        return None
    width, height = guiparse.number(of.get("width")), guiparse.number(of.get("height"))
    return (int(width), int(height)) if width is not None and height is not None else None


def ground(node):
    background = node.block("background")
    if background is None:
        return None
    return background.get("quadTextureSprite") or background.get("spriteType")


def widgets(node, x=0, y=0):
    """Every widget below a window with its place in the window: (node, x, y)."""
    for child in node.blocks():
        if child.key.lower() not in WIDGETS:
            continue
        dx, dy = position(child)
        yield child, x + dx, y + dy
        if child.key.lower() in ("containerwindowtype", "windowtype"):
            for inner in widgets(child, x + dx, y + dy):
                yield inner


def item(name):
    return {"name": name}


def lint_window(window, look):
    wname = window.name
    out = []
    fonts = set(layoutmod.fonts_of(look))
    seen = set()
    for node, _x, _y in widgets(window):
        for key in ("font", "buttonFont"):
            font = node.get(key)
            if font and font not in fonts and font not in seen:
                seen.add(font)
                out.append(finding("error", "font", wname, item(font), "%s is not a font of the %s look (%s)" % (font, look, ", ".join(sorted(fonts)))))
        for key in ("spriteType", "quadTextureSprite"):
            band = BAND.match(node.get(key) or "")
            if band and int(band.group(2)) not in layoutmod.ROW_PITCHES and band.group(0) not in seen:
                seen.add(band.group(0))
                out.append(finding("error", "row", wname, item(band.group(0)), "rows of %s; a table row is %s"
                                   % (band.group(2), ", ".join(map(str, layoutmod.ROW_PITCHES)))))

    strips = [(node, x, y) for node, x, y in widgets(window) if ground(node) == layoutmod.TITLE_STRIP and size(node)]
    closes = [(node, x, y) for node, x, y in widgets(window) if node.get("quadTextureSprite") == layoutmod.CLOSE_BUTTON and x >= 0 and y >= 0]
    for strip, sx, sy in strips:
        sw, sh = size(strip)
        if sh != TITLE_HEIGHT[look]:
            out.append(finding("error", "title", wname, item(strip.name), "a title strip %d high; the %s look's is %d" % (sh, look, TITLE_HEIGHT[look])))
        lo, hi = layoutmod.CLOSE_INSIDE
        cw, ch = layoutmod.CLOSE_SIZE
        for close, cx, cy in closes:
            inside = (sx + sw) - (cx + cw)
            middle = abs((cy + ch / 2.0) - (sy + sh / 2.0))
            if not lo <= inside <= hi or middle > layoutmod.CLOSE_SLACK:
                out.append(finding("error", "close", wname, item(close.name), "the close button ends %d inside the strip's right edge and sits %.0f off its middle; it ends %d to %d inside, within %d of the middle"
                                   % (inside, middle, lo, hi, layoutmod.CLOSE_SLACK)))
    return out


def lint(paths):
    out = []
    for path in paths:
        for window in guiparse.top_level_windows(guiparse.parse_file(path)):
            look = "steel" if ground(window) == layoutmod.GROUND else "card"
            if look != layoutmod.DEFAULT_STYLE and ground(window) == layoutmod.CARD_GROUND:
                out.append(finding("warn", "look", window.name, None, "the card look; the steel look is the default since 2026-10-21"))
            out.extend(lint_window(window, look))
    return out


def load_exceptions(path):
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)["exceptions"]


def apply_exceptions(findings, exceptions):
    used = set()
    for f in findings:
        for n, e in enumerate(exceptions):
            if e["rule"] == f["rule"] and fnmatch.fnmatchcase(f["window"], e["window"]) and fnmatch.fnmatchcase(f["item"], e["item"]):
                f["level"], f["why"] = "excepted", e["why"]
                used.add(n)
    for n, e in enumerate(exceptions):
        if n not in used:
            findings.append(finding("error", "stale", e["window"], item(e["item"]), "tools/design_exceptions.json lists a %s finding that no longer occurs: remove the exception" % e["rule"]))
    return findings


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check the written pages against the design ruleset.")
    parser.add_argument("files", nargs="*", help="the .gui files (default: interface/mod1440_*.gui)")
    parser.add_argument("--exceptions", default=EXCEPTIONS, help="the listed deviations (default: tools/design_exceptions.json)")
    parser.add_argument("--json", metavar="OUT", help="also write the findings as JSON")
    args = parser.parse_args(argv)
    paths = args.files or sorted(glob.glob(os.path.join(REPO_ROOT, "interface", "mod1440_*.gui")))
    findings = apply_exceptions(lint(paths), load_exceptions(args.exceptions))
    for f in findings:
        line = "%-8s %-6s %s %s: %s" % (f["level"], f["rule"], f["window"], f["item"], f["message"])
        if f["level"] == "excepted":
            line += " (why: %s)" % f["why"]
        print(line)
    counts = {level: sum(1 for f in findings if f["level"] == level) for level in ("error", "warn", "excepted")}
    print("%d file(s): %d error(s), %d warning(s), %d excepted" % (len(paths), counts["error"], counts["warn"], counts["excepted"]))
    if args.json:
        out = args.json if os.path.isabs(args.json) else os.path.join(REPO_ROOT, args.json)
        with open(out, "w", encoding="utf-8", newline="\n") as handle:
            json.dump({"files": [os.path.relpath(p, REPO_ROOT) for p in paths], "counts": counts, "findings": findings}, handle, indent=2)
            handle.write("\n")
    return 1 if counts["error"] else 0


if __name__ == "__main__":
    sys.exit(main())
