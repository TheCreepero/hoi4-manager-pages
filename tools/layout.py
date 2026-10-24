"""The layout file of a phase: one JSON file that the mock-up (tools/mockup.py) is drawn from and whose numbers the
builder writes into the generator (tools/build_managers.py, tools/build_records.py), so the design is written once.
The shape is given in wiki/Workflow.md, "Handoff files"; the design language it draws is in wiki/Design-Language.md.

    import layout
    lay = layout.load("scratch/phases/A10/layout.json")
    for window in lay["windows"]:
        for item in layout.items(window):      # repeats expanded, names and keys filled in
            ...

A layout may name its look (`style`: "steel", the default since 2026-10-21, or "card" for the screens built before);
tools/lint_layout.py checks the layout against the ruleset below and wiki/Design-Language.md.

A layout names a phase (`id`), a prefix for the widgets and sprites it adds (`prefix`: widgets `mod1440_<prefix>_*`,
sprites `GFX_1440p_<PREFIX>_*`), the override file, the scene, the capture the mock-up is drawn on, and the windows.
A window is a guiedit path ("strategicairview", "strategicairview/details_wnd"), where it stands on the screen
(`at`, for the mock-up), its own position, size and background (for the file), the child after which the plates
are inserted (`after`), and its items, in drawing order, with x and y relative to the window:

  kind      what it is                                      file                        mock-up
  title     the title strip (header_bg.dds)                 iconType + tile sprite      the tile
  card      a card plate (tiled_plain_bg_small.dds)         iconType + tile sprite      the tile
  head      a head bar (tiled_header_1.dds)                 iconType + tile sprite      the tile
  bands     the bands of a table: one plate per even row    iconType per band + sprite  the tiles
            (x, y, w, row, rows; `every` = 2)
  plate     a plate on a texture (texture, border) or on    iconType (+ tile sprite)    the tile or the sprite
            an existing sprite (sprite)
  steel     a steel card (the default look, C1): optional   iconType + bitmap sprite    the bitmap
            `head` rows (27, or 38 with buttons), `bottom`  (a DDS cut from the steel
                                                            bar by stretch_background)
  steel_title  the steel title strip                       iconType + bitmap sprite    the bitmap
  inset     a near-black inset (tiled_window_thin_border)   iconType + tile sprite      the tile
  caption   a text of the mod (key, text, font, w, h,       instantTextboxType          the text
            format)
  move      a vanilla widget at its new place (path, x, y,  position, size or maxWidth, the sample text or the
            w, h, font, format, fixed, sprite, sample, set) font, sprite, fixedsize     sprite, when given
  text      a sample text (font, text, w, align)            -                           the text
  sprite    a sprite (name, frame, w, h)                    -                           the sprite
  paste     a piece of the panel capture (box, x, y)        -                           the piece

Any item may carry `repeat`: {"var": "n", "range": [1, 12]} or {"var": "n", "values": [...]}, with `dx` and `dy`
per step; "{n}" and "{i}" (0-based) in `path`, `name`, `key`, `text`, `sample` are filled in, and a list under
`texts`, `samples` or `keys` gives one value per step. An item may carry its own `after` (the plates of a chart go after the
chart's background, not after the window's).
"""
import json
import os
import re

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The tiles of the plates (wiki/Design-Language.md): texture and border of each plate kind.
PLATES = {
    "title": ("gfx/interface/header_bg.dds", (61, 21)),
    "card": ("gfx/interface/tiles/tiled_plain_bg_small.dds", (16, 16)),
    "head": ("gfx/interface/tiles/tiled_header_1.dds", (8, 8)),
    "bands": ("gfx/interface/tiles/black_bg_tile.dds", (3, 3)),
    "inset": ("gfx/interface/tiles/tiled_window_thin_border.dds", (8, 8)),
}
# The steel pieces are bitmaps cut from the steel bar at their size (tools/stretch_background.py, steel_piece).
STEEL_KINDS = ("steel", "steel_title")
STEEL_DIR = "gfx/interface/mod1440"
PLATE_KINDS = ("title", "card", "head", "bands", "plate", "inset") + STEEL_KINDS

# ---------------------------------------------------------------- the ruleset in numbers
# wiki/Design-Language.md says the same in words; tools/lint_layout.py holds a layout to it.
STYLES = ("steel", "card")
DEFAULT_STYLE = "steel"                  # user decision 2026-10-21: the C1 look is the default
GROUND = "GFX_1440p_steel_ground"        # the near-black window ground of the steel look
GAP = {"icon_text": 4, "inner": 8, "card": 6, "column": 16}
ROW_PITCHES = (24, 32, 48)               # a table row: one line of hoi_18mbs, values beside icons, two lines
STEEL_HEADS = (27, 38)                   # a steel card's head band: a line of text, or text with buttons
FONTS = {                                # role -> the fonts the role may use, by look
    "title": {"steel": ("hoi_36header",), "card": ("hoi_30header",)},
    "name": {"steel": ("hoi_24header",), "card": ("hoi_20b",)},
    "figure": {"steel": ("hoi_24header", "hoi_20b"), "card": ("hoi_20b",)},
    "value": {"steel": ("hoi_20b",), "card": ("hoi_20b",)},
    "caption": {"steel": ("hoi_18mbs",), "card": ("hoi_18mbs",)},
    "button": {"steel": ("hoi_16mbs",), "card": ("hoi_16mbs",)},
}
CLOSE_INSIDE = (2, 8)                    # the close button's right edge this far inside the title strip's
CLOSE_SLACK = 4                          # and its middle this close to the strip's middle
CLOSE_SIZE = (32, 33)                    # GFX_closebutton

# ---------------------------------------------------------------- the pieces of the pages
# tools/build_managers.py and tools/build_records.py write every page from these; tools/lint_gui.py holds the files
# they write to the ruleset above. The sprites of the mod are declared in interface/mod1440_ui.gfx.
CARD_GROUND = "GFX_tiled_window_1b_thin_border"     # the window ground of the card look
CARD_PLATE = "GFX_tiled_plain_bg_small"             # a card, and the ground of a list that scrolls
TITLE_STRIP = "GFX_tiled_header"                    # the title strip of a page
CLOSE_BUTTON = "GFX_closebutton"
HEAD = "GFX_1440p_SG_head_%d"                       # a head plate 30 high
HEAD_SIZED = "GFX_1440p_SG_head_%dx%d"              # a head plate of any other height
STRIPE = "GFX_1440p_SG_stripe_%dx%d"                # the darker band of every second row
PICK = "GFX_1440p_SG_pick_%dx%d"                    # the lighter band of the chosen row


def head_sprite(width, height=None):
    return HEAD % width if height is None else HEAD_SIZED % (width, height)

# The review questions a design answers in design.json `heuristics` (wiki/Design-Language.md, "Review questions"):
# Nielsen's ten heuristics and the game usability heuristics of Pinelle et al. (2008), cut to what a redesign here can change.
HEURISTICS = [
    ("H1", "At a glance", "The values the player checks most are readable without hovering, scrolling or opening anything."),
    ("H2", "The game's words", "Vanilla terms, icons and units; no new name for a vanilla thing."),
    ("H3", "A way out", "ESCAPE and the close button at the title strip's right edge close it; nothing covers the map without need."),
    ("H4", "Consistency", "The pieces, fonts, spacing and hotkeys of the ruleset; the linter is clean or each exception has its reason."),
    ("H5", "Muscle memory", "Frequent buttons keep vanilla's order and relative place, or the move is argued; destructive buttons stand apart from frequent ones."),
    ("H6", "State is shown", "The selection, the open tab, the filters on and the folded parts are visible, not remembered."),
    ("H7", "Shortcuts", "Frequent actions have a hotkey from the shared table."),
    ("H8", "One subject per card", "Related values side by side, nothing shown twice, no empty space without a reason."),
    ("H9", "Hierarchy and legibility", "The squinted figure keeps the title, the heads and the key figures; no text under the contrast floor."),
    ("H10", "Long text and many mods", "Long names, many rows and other mods' values fit: fixed boxes, scrolling, tools/check_playset.py read."),
]
CONTRAST = {"normal": 4.5, "large": 3.0}  # WCAG 2 ratios; large is 24 px and up, or 19 px and up in a bold font


def style(lay):
    return lay.get("style", DEFAULT_STYLE)


def fonts_of(look):
    """Every font the ruleset allows in a look."""
    return sorted({f for role in FONTS.values() for f in role[look]})
TEXT_KINDS = ("caption", "text")
KINDS = PLATE_KINDS + TEXT_KINDS + ("move", "sprite", "paste")
FORMATS = ("left", "center", "centre", "right")


class LayoutError(Exception):
    pass


def load(path):
    """The layout, checked: every item has a known kind and the fields its kind needs."""
    with open(path, encoding="utf-8") as handle:
        lay = json.load(handle)
    for key in ("id", "prefix", "windows"):
        if key not in lay:
            raise LayoutError("%s: no %r" % (path, key))
    if style(lay) not in STYLES:
        raise LayoutError("%s: style %r (one of %s)" % (path, style(lay), ", ".join(STYLES)))
    if not re.match(r"^[a-z][a-z0-9]*$", lay["prefix"]):
        raise LayoutError("%s: the prefix is lower-case letters and digits (%r)" % (path, lay["prefix"]))
    for window in lay["windows"]:
        if "path" not in window:
            raise LayoutError("%s: a window has no path" % path)
        for item in window.get("items", []):
            _check(item, window["path"], path)
    return lay


def _check(item, window, path):
    kind = item.get("kind")
    where = "%s: %s" % (path, window)
    if kind not in KINDS:
        raise LayoutError("%s: unknown kind %r (one of %s)" % (where, kind, ", ".join(KINDS)))
    need = {
        "title": ("name", "x", "y", "w", "h"), "card": ("name", "x", "y", "w", "h"), "head": ("name", "x", "y", "w", "h"),
        "bands": ("name", "x", "y", "w", "row", "rows"), "plate": ("name", "x", "y"), "inset": ("name", "x", "y", "w", "h"),
        "steel": ("name", "x", "y", "w", "h"), "steel_title": ("name", "x", "y", "w", "h"),
        "caption": ("name", "x", "y", "w", "key"), "move": ("path",), "text": ("font", "x", "y"),
        "sprite": ("name", "x", "y"), "paste": ("box", "x", "y"),
    }[kind]
    lists = {"key": "keys", "text": "texts", "sample": "samples"}
    for key in need:
        if key not in item and not (item.get("repeat") and lists.get(key) in item):
            raise LayoutError("%s: a %s item needs %r (%s)" % (where, kind, key, json.dumps(item)[:80]))
    if kind == "plate" and "sprite" not in item and not ("texture" in item and "w" in item and "h" in item):
        raise LayoutError("%s: a plate names a sprite, or a texture with w and h (%s)" % (where, item["name"]))
    if kind in STEEL_KINDS and item.get("h", 0) < steel_min_height(item):
        raise LayoutError("%s: the steel piece %s is %d high; it needs %d (edges and head)" % (where, item["name"], item["h"], steel_min_height(item)))
    if item.get("format", "left") not in FORMATS:
        raise LayoutError("%s: format %r" % (where, item.get("format")))


def items(window):
    """The window's items with every `repeat` expanded, in drawing order."""
    out = []
    for item in window.get("items", []):
        rep = item.get("repeat")
        if not rep:
            out.append(dict(item))
            continue
        var = rep.get("var", "n")
        values = rep["values"] if "values" in rep else list(range(rep["range"][0], rep["range"][1] + 1))
        for i, value in enumerate(values):
            step = dict(item)
            del step["repeat"]
            fill = {var: value, "i": i}
            for key in ("path", "name", "key", "text", "sample"):
                if isinstance(step.get(key), str):
                    step[key] = _fill(step[key], fill)
            if "texts" in step:
                step["text"] = step["texts"][i] if i < len(step["texts"]) else ""
            if "samples" in step:
                step["sample"] = step["samples"][i] if i < len(step["samples"]) else ""
            if "keys" in step:
                step["key"] = step["keys"][i] if i < len(step["keys"]) else ""
            step["x"] = step.get("x", 0) + rep.get("dx", 0) * i
            step["y"] = step.get("y", 0) + rep.get("dy", 0) * i
            out.append(step)
    return out


def _fill(text, values):
    for key, value in values.items():
        text = text.replace("{%s}" % key, str(value))
    return text


def widget_name(lay, item):
    """mod1440_<prefix>_<name>"""
    return "mod1440_%s_%s" % (lay["prefix"], item["name"])


def sprite_name(lay, item):
    """GFX_1440p_<PREFIX>_<name>, or the existing sprite the item names."""
    if item["kind"] == "plate" and "sprite" in item:
        return item["sprite"]
    return "GFX_1440p_%s_%s" % (lay["prefix"].upper(), item["name"])


def plate_texture(item):
    """(texture path, (border x, border y)) of a plate kind, or None for a plate on an existing sprite."""
    if item["kind"] == "plate":
        if "sprite" in item:
            return None
        return item["texture"], tuple(item.get("border", (0, 0)))
    if item["kind"] in STEEL_KINDS:
        return None
    return PLATES[item["kind"]]


def steel_params(item):
    """(head rows, head gain, bottom rows) of a steel piece, as tools/stretch_background.py steel_piece takes them."""
    h = item["h"]
    if item["kind"] == "steel_title":
        return h - 6, 1.25, 4
    return item.get("head", 0), 1.9, item.get("bottom", 15 if h >= 60 else 6)


def steel_min_height(item):
    head, _gain, bottom = steel_params(dict(item, h=item.get("h", 0)))
    return 9 + (head - 10 + 3 if head else 0) + bottom      # edge, head band and rule, bottom (C1's title strip has no body)


def steel_texture(lay, item):
    """Where the bitmap of a steel piece is written: gfx/interface/mod1440/<prefix>_<name>.dds"""
    return "%s/%s_%s.dds" % (STEEL_DIR, lay["prefix"], item["name"])


def steel_declarations(lay):
    """One (sprite name, texture, kind, (w, h), params) per steel bitmap the layout makes, in the order they appear."""
    seen = {}
    for window in lay["windows"]:
        for item in items(window):
            if item["kind"] not in STEEL_KINDS:
                continue
            name = sprite_name(lay, item)
            key = (item["kind"], (item["w"], item["h"]), steel_params(item))
            if name in seen and seen[name][1:] != key:
                raise LayoutError("%s is made twice with different sizes or heads" % name)
            seen.setdefault(name, (steel_texture(lay, item),) + key)
    return [(name, tex, kind, size, params) for name, (tex, kind, size, params) in seen.items()]


def plate_size(item):
    if item["kind"] == "bands":
        return item["w"], item["row"]
    return item["w"], item["h"]


def band_rows(item):
    """(row number from 1, y) of every band of a `bands` item: the even rows unless `every` says otherwise."""
    every = item.get("every", 2)
    first = item.get("first", every)      # the first banded row, counted from 1
    return [(n, item["y"] + item["row"] * (n - 1)) for n in range(first, item["rows"] + 1, every)]


def plate_declarations(lay):
    """One (sprite name, texture, border, (w, h)) per sprite the layout declares, in the order they first appear."""
    seen = {}
    for window in lay["windows"]:
        for item in items(window):
            if item["kind"] not in PLATE_KINDS:
                continue
            tex = plate_texture(item)
            if tex is None:
                continue
            name = sprite_name(lay, item)
            size = plate_size(item)
            if name in seen and seen[name][2] != size:
                raise LayoutError("%s is declared at two sizes: %s and %s" % (name, seen[name][2], size))
            seen.setdefault(name, (tex[0], tex[1], size))
    return [(name, tex, border, size) for name, (tex, border, size) in seen.items()]


def window_screen_origin(window):
    at = window.get("at", (0, 0))
    return int(at[0]), int(at[1])
