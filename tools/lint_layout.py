"""Hold a phase's layout file to the ruleset of wiki/Design-Language.md: fonts by role, the gaps between cards, the
content inset, table row pitches, the steel head bands, the pieces of the layout's look and the close button.

    python -I tools/lint_layout.py scratch/phases/A10/layout.json
    python -I tools/lint_layout.py scratch/phases/A10/layout.json --json scratch/phases/A10/lint.json

An error breaks a rule; a warning is worth a look. An item may carry `"why": "..."` and the layout may carry
`"exceptions": [{"rule": "gap", "why": "..."}]`: the findings they cover are reported as excepted, with the reason,
and do not fail. Exit 1 when an error is left. The designer runs it before handing in (stage 2), the orchestrator at
gate A; tools/ux_audit.py carries the result onto the design page.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import layout as layoutmod  # noqa: E402

REPO_ROOT = layoutmod.REPO_ROOT
CARD_KINDS = ("card", "steel")
TITLE_KINDS = ("title", "steel_title")
CLOSE = re.compile(r"(^|_)close(_button)?$", re.I)
CLOSE_SIZE = (32, 33)          # GFX_closebutton
NEAR = 24                      # two cards closer than this are neighbours, and their gap is the card gap


class Finding(dict):
    pass


def finding(level, rule, window, item, message):
    name = (item or {}).get("name") or (item or {}).get("path") or ""
    return Finding(level=level, rule=rule, window=window, item=name, message=message, why=(item or {}).get("why"))


def box(item):
    return item["x"], item["y"], item["x"] + item.get("w", 0), item["y"] + item.get("h", item.get("row", 0) * item.get("rows", 1))


def overlap(a0, a1, b0, b1):
    return min(a1, b1) - max(a0, b0) > 0


def lint(lay):
    look = layoutmod.style(lay)
    allowed = set(layoutmod.fonts_of(look))
    out = []
    for window in lay["windows"]:
        wpath = window["path"]
        its = layoutmod.items(window)
        cards = [i for i in its if i["kind"] in CARD_KINDS]
        titles = [i for i in its if i["kind"] in TITLE_KINDS]

        # the pieces of the look
        for item in its:
            if look == "steel" and item["kind"] in ("title", "card", "head"):
                out.append(finding("warn", "look", wpath, item, "a %s of the card style in a steel layout; the steel look uses %s"
                                   % (item["kind"], {"title": "steel_title", "card": "steel", "head": "a steel card's head band"}[item["kind"]])))
            if look == "card" and item["kind"] in layoutmod.STEEL_KINDS:
                out.append(finding("warn", "look", wpath, item, "a steel piece in a card-style layout"))
        if look == "steel" and window.get("background") and window["background"] not in (layoutmod.GROUND, "GFX_1440p_PD_black_tile"):
            out.append(finding("warn", "look", wpath, None, "the window ground is %s; the steel look stands on %s" % (window["background"], layoutmod.GROUND)))

        # fonts by role
        for item in its:
            font = item.get("font")
            if not font or item["kind"] not in ("caption", "text", "move"):
                continue
            role = item.get("role")
            if role:
                if role not in layoutmod.FONTS:
                    out.append(finding("error", "font", wpath, item, "unknown role %r (one of %s)" % (role, ", ".join(layoutmod.FONTS))))
                elif font not in layoutmod.FONTS[role][look]:
                    out.append(finding("error", "font", wpath, item, "%s for a %s; the %s look uses %s" % (font, role, look, " or ".join(layoutmod.FONTS[role][look]))))
            elif font not in allowed:
                out.append(finding("error", "font", wpath, item, "%s is not a font of the %s look (%s)" % (font, look, ", ".join(sorted(allowed)))))

        # steel head bands and table rows
        for item in its:
            if item["kind"] == "steel" and item.get("head") and item["head"] not in layoutmod.STEEL_HEADS:
                out.append(finding("error", "head", wpath, item, "a head band of %d rows; the look has %s" % (item["head"], " or ".join(map(str, layoutmod.STEEL_HEADS)))))
            if item["kind"] == "bands" and item["row"] not in layoutmod.ROW_PITCHES:
                out.append(finding("error", "row", wpath, item, "rows of %d; a table row is %s" % (item["row"], ", ".join(map(str, layoutmod.ROW_PITCHES)))))

        # the gap between neighbouring cards
        gap = layoutmod.GAP["card"]
        for i, a in enumerate(cards):
            ax0, ay0, ax1, ay1 = box(a)
            for b in cards[i + 1:]:
                bx0, by0, bx1, by1 = box(b)
                if overlap(ax0, ax1, bx0, bx1):
                    d = by0 - ay1 if by0 >= ay1 else ay0 - by1 if ay0 >= by1 else None
                elif overlap(ay0, ay1, by0, by1):
                    d = bx0 - ax1 if bx0 >= ax1 else ax0 - bx1 if ax0 >= bx1 else None
                else:
                    continue
                if d is None:
                    out.append(finding("error", "gap", wpath, b, "overlaps the card %s" % a["name"]))
                elif d < NEAR and d != gap:
                    out.append(finding("error", "gap", wpath, b, "%d from the card %s; cards stand %d apart" % (d, a["name"], gap)))

        # the content inset: texts inside a card start at least 8 from its edges
        inner = layoutmod.GAP["inner"]
        for item in its:
            if item["kind"] not in ("caption", "text", "move") or "x" not in item or "y" not in item:
                continue
            for card in cards:
                cx0, cy0, cx1, cy1 = box(card)
                if cx0 <= item["x"] < cx1 and cy0 <= item["y"] < cy1:
                    if item["x"] - cx0 < inner:
                        out.append(finding("warn", "inset", wpath, item, "%d from the left edge of %s; content stands %d inside" % (item["x"] - cx0, card["name"], inner)))
                    right = cx1 - (item["x"] + item.get("w", 0))
                    if item.get("w") and right < inner:
                        out.append(finding("warn", "inset", wpath, item, "%d from the right edge of %s; content stands %d inside" % (right, card["name"], inner)))
                    break

        # the close button at the title strip's right edge (user decision 2026-10-21)
        closes = [i for i in its if i["kind"] == "move" and CLOSE.search(i["path"].split("/")[-1])]
        for title in titles:
            tx0, ty0, tx1, ty1 = box(title)
            if not closes:
                out.append(finding("warn", "close", wpath, title, "the layout does not place the close button; it belongs at the strip's right edge"))
            for item in closes:
                w, h = item.get("w", CLOSE_SIZE[0]), item.get("h", CLOSE_SIZE[1])
                x = item.get("x", 0)
                if x < 0 and window.get("size"):
                    x += window["size"][0]
                inside = tx1 - (x + w)
                middle = abs((item.get("y", 0) + h / 2) - (ty0 + ty1) / 2)
                lo, hi = layoutmod.CLOSE_INSIDE
                if not lo <= inside <= hi or middle > layoutmod.CLOSE_SLACK:
                    out.append(finding("error", "close", wpath, item, "the close button ends %d inside the strip's right edge and sits %.0f off its middle; it ends %d to %d inside, within %d of the middle"
                                       % (inside, middle, lo, hi, layoutmod.CLOSE_SLACK)))

    waived = {e.get("rule"): e.get("why") for e in lay.get("exceptions", [])}
    for f in out:
        why = f["why"] or waived.get(f["rule"])
        if why and f["level"] == "error":
            f["level"], f["why"] = "excepted", why
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check a layout file against the design ruleset.")
    parser.add_argument("layout")
    parser.add_argument("--json", metavar="OUT", help="also write the findings as JSON")
    args = parser.parse_args(argv)
    path = args.layout if os.path.isabs(args.layout) else os.path.join(REPO_ROOT, args.layout)
    lay = layoutmod.load(path)
    findings = lint(lay)
    for f in findings:
        line = "%-8s %-6s %s %s: %s" % (f["level"], f["rule"], f["window"], f["item"], f["message"])
        if f["level"] == "excepted":
            line += " (why: %s)" % f["why"]
        print(line)
    counts = {level: sum(1 for f in findings if f["level"] == level) for level in ("error", "warn", "excepted")}
    print("%s, %s look: %d error(s), %d warning(s), %d excepted" % (args.layout, layoutmod.style(lay), counts["error"], counts["warn"], counts["excepted"]))
    if args.json:
        out = args.json if os.path.isabs(args.json) else os.path.join(REPO_ROOT, args.json)
        with open(out, "w", encoding="utf-8", newline="\n") as handle:
            json.dump({"layout": args.layout, "style": layoutmod.style(lay), "counts": counts, "findings": findings}, handle, indent=2)
            handle.write("\n")
    return 1 if counts["error"] else 0


if __name__ == "__main__":
    sys.exit(main())
