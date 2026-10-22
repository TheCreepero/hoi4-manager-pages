"""Build larger backgrounds from vanilla textures by copying pixels only.

Every output is assembled from columns and rows of vanilla textures: kept, repeated, or copied in
mirrored order. No pixel is drawn; a card (A8) lays vanilla plates over each other as the game would draw
them. So the result keeps the vanilla look. Re-run after a
game update that changes a source texture.

    python tools/stretch_background.py [--game-dir DIR] [--preview DIR] [--only NAME]

Needs Pillow. Outputs go to gfx/interface/mod1440/ as uncompressed 32-bit DDS, the format the
vanilla files use.
"""

import argparse
import os
import re
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(REPO_ROOT, "gfx", "interface", "mod1440")


def widen_periodic(frame, width, period, split, top, bottom, right_cap):
    """Widen a frame whose inner pattern repeats every `period` columns.

    Columns left of `split` are kept. From `split` on, the last full period before `split` is
    repeated, which continues the pattern without a seam. The edge rows (above `top`, from `bottom`
    down) of the vanilla right part and the last `right_cap` columns are then copied back, so the
    right edge bar, border and rivets end up where they belong.
    """
    w, h = frame.size
    out = Image.new("RGBA", (width, h))
    out.paste(frame.crop((0, 0, split, h)), (0, 0))

    tile = frame.crop((split - period, 0, split, h))
    for x in range(split, width, period):
        out.paste(tile, (x, 0))

    right_x = split + (width - w)
    out.paste(frame.crop((split, 0, w, top)), (right_x, 0))
    out.paste(frame.crop((split, bottom, w, h)), (right_x, bottom))
    out.paste(frame.crop((w - right_cap, 0, w, h)), (width - right_cap, 0))
    return out


def widen_spread(frame, width, left_cap, right_cap):
    """Widen a frame whose middle is a smooth gradient without a pattern.

    The first `left_cap` and last `right_cap` columns are kept. The columns between them are spread
    evenly over the new width, each one shown one or more times, which keeps the gradient smooth.
    """
    w, h = frame.size
    out = Image.new("RGBA", (width, h))
    out.paste(frame.crop((0, 0, left_cap, h)), (0, 0))
    out.paste(frame.crop((w - right_cap, 0, w, h)), (width - right_cap, 0))

    source_span = w - left_cap - right_cap
    target_span = width - left_cap - right_cap
    for i in range(target_span):
        x = left_cap + i * source_span // target_span
        out.paste(frame.crop((x, 0, x + 1, h)), (left_cap + i, 0))
    return out


def widen_mirror(frame, width, split):
    """Widen a frame whose middle is an irregular texture without a pattern or gradient.

    The new columns go in at `split`: the columns left of it mirrored, then the same columns again
    the right way round. Every join is between a column and its own copy, so no seam shows. The
    added width must be even, and the columns it is taken from must be plain.
    """
    w, h = frame.size
    half, odd = divmod(width - w, 2)
    if odd or half > split:
        raise ValueError("widen_mirror needs an even added width of at most twice the split column")
    out = Image.new("RGBA", (width, h))
    out.paste(frame.crop((0, 0, split, h)), (0, 0))
    section = frame.crop((split - half, 0, split, h))
    out.paste(section.transpose(Image.FLIP_LEFT_RIGHT), (split, 0))
    out.paste(section, (split + half, 0))
    out.paste(frame.crop((split, 0, w, h)), (split + 2 * half, 0))
    return out


def widen_mirror_multi(frame, inserts):
    """Apply widen_mirror at several columns, to widen each painted area of a frame by its own amount.

    `inserts` lists (split column, added width) in the columns of the vanilla frame. They are
    applied from right to left, so an insert does not move the columns of the ones still to come.
    """
    for split, added in sorted(inserts, reverse=True):
        frame = widen_mirror(frame, frame.width + added, split)
    return frame


def grow(image, axis, inserts):
    """Insert columns (axis "x") or rows (axis "y") into an image without drawing a pixel.

    `inserts` lists (split, added) or (split, added, period), in the lines of the image as passed in.
    They are applied from the far end back, so an insert does not move the lines of the ones still
    to come.

    Without a period, the added/2 lines before `split` go in mirrored and then once more the right
    way round, so every join is between a line and its own copy. This suits plain and irregular
    areas. With a period, the `added` lines before `split` go in once more as they are, which
    continues a pattern of that period without a seam; `added` must be a multiple of the period.
    """
    horizontal = axis == "x"
    for split, added, *rest in sorted(inserts, reverse=True):
        period = rest[0] if rest else None
        w, h = image.size
        if period:
            if added % period or added > split:
                raise ValueError(f"insert at {split}: {added} is not a multiple of the period {period}, or too long")
            pieces = [image.crop((split - added, 0, split, h) if horizontal else (0, split - added, w, split))]
        else:
            half, odd = divmod(added, 2)
            if odd or half > split:
                raise ValueError(f"insert at {split}: a mirrored insert needs an even length of at most twice the split")
            block = image.crop((split - half, 0, split, h) if horizontal else (0, split - half, w, split))
            pieces = [block.transpose(Image.FLIP_LEFT_RIGHT if horizontal else Image.FLIP_TOP_BOTTOM), block]
        if horizontal:
            out = Image.new("RGBA", (w + added, h))
            out.paste(image.crop((0, 0, split, h)), (0, 0))
            x = split
            for piece in pieces:
                out.paste(piece, (x, 0))
                x += piece.width
            out.paste(image.crop((split, 0, w, h)), (x, 0))
        else:
            out = Image.new("RGBA", (w, h + added))
            out.paste(image.crop((0, 0, w, split)), (0, 0))
            y = split
            for piece in pieces:
                out.paste(piece, (0, y))
                y += piece.height
            out.paste(image.crop((0, split, w, h)), (0, y))
        image = out
    return image


def grow_bands(image, axis, bands):
    """Grow each band of an image with its own inserts and put the bands back together.

    For axis "x" a band is a range of rows, (first row, end row, inserts), and its inserts add
    columns; for axis "y" it is a range of columns whose inserts add rows. The bands must cover the
    image and all grow by the same amount. This is how a bitmap with several painted areas grows
    area by area: each band gets its inserts where that band is plain.
    """
    horizontal = axis == "x"
    w, h = image.size
    parts, at = [], 0
    for start, end, inserts in bands:
        if start != at:
            raise ValueError(f"bands leave a gap or overlap at {at}")
        band = image.crop((0, start, w, end) if horizontal else (start, 0, end, h))
        parts.append(grow(band, axis, inserts))
        at = end
    if at != (h if horizontal else w):
        raise ValueError(f"bands end at {at}, the image at {h if horizontal else w}")
    sizes = {part.width if horizontal else part.height for part in parts}
    if len(sizes) != 1:
        raise ValueError(f"bands grow to different sizes: {sorted(sizes)}")
    return join(parts, "y" if horizontal else "x")


def join(parts, axis):
    """Put images side by side (axis "x") or one above the other (axis "y")."""
    horizontal = axis == "x"
    width = sum(p.width for p in parts) if horizontal else max(p.width for p in parts)
    height = max(p.height for p in parts) if horizontal else sum(p.height for p in parts)
    out = Image.new("RGBA", (width, height))
    at = 0
    for part in parts:
        out.paste(part, (at, 0) if horizontal else (0, at))
        at += part.width if horizontal else part.height
    return out


def spread(first, last, count, length, period):
    """`count` inserts of `length` lines each, evenly spaced from `first` to `last`, for grow().

    Many short inserts keep a gradient smooth where one long insert would show as a step.
    """
    step = (last - first) / max(1, count - 1)
    return [(int(round(first + i * step)), length, period) for i in range(count)]


# Army and army group badge. Both are painted alike: the name field (columns 57-229 of the top band),
# the commander box (66-219), the stats box (221-297), a plain right area (297-429) and the tray
# along the bottom (64-428). The inserts widen the name field and commander box, the stats box and
# the right area.
BADGE_INSERTS = [(200, 100), (295, 48), (425, 100)]

# ---------------------------------------------------------------------------------------------
# Unit details windows (division, ship, air wing, railway gun). All four bitmaps are painted alike:
# a main part of 553 columns (title bar, header strip, a paper with three stat columns and a
# printed line every 20 rows, a lower panel) and a side part of 303 columns (a header bar above a
# panel hatched with a pattern of 3 pixels in both directions).
#
# The numbers below are shared with the widget positions in interface/zz_1440p_unit_details.gui:
# a stat column grows by STAT_COLUMN columns and a stat row by STAT_ROW rows.

STAT_COLUMN = 78          # 155 -> 233 px for a label and its value in the 22 px typewriter font
STAT_ROW = 8              # 20 -> 28 px per row
SIDE_GROWTH = 90          # side part: 30 periods of its hatch
MAIN_GROWTH = 3 * STAT_COLUMN

# The frame line above the paper (rows 66-77) has thicker stretches; these columns are plain in it.
PAPER_FRAME_COLUMNS = [(126, STAT_COLUMN), (350, STAT_COLUMN), (496, STAT_COLUMN)]


def paper_columns():
    """Column inserts for the paper: each stat column (16-182, 186-357, 361-529) takes STAT_COLUMN / 3
    inserts of 3 columns, spread over its width.

    The printed lines are dotted with a period of about 3 columns, so a copy of 3 columns leaves
    them even, and many short copies stretch the paper grain evenly where one mirrored insert would
    show every stain twice.
    """
    count = STAT_COLUMN // 3
    return spread(24, 176, count, 3, 3) + spread(196, 352, count, 3, 3) + spread(372, 526, count, 3, 3)


def paper_rows(first, bands, last_band_rows=8, per_band=STAT_ROW):
    """Row inserts for a paper with `bands` stat rows: every band between two printed lines takes
    STAT_ROW rows, each a copy of one of its own rows.

    `first` is the first row of the first band; a band starts every 20 rows and has 16 plain rows.
    The last band ends at the bottom edge of the paper and is shorter, so its copies are taken from
    its first rows.
    """
    rows = []
    # a band has 16 plain rows: up to 8 copies go after every second one; more copies cycle through
    # rows 1 to 15, so several copies of one row follow each other (a plain row repeated is still plain)
    offset = (lambda i: 1 + 2 * i) if per_band <= 8 else (lambda i: 1 + i % 15)
    for band in range(bands - 1):
        rows += [(first + 20 * band + offset(i), 1, 1) for i in range(per_band)]
    rows += [(first + 20 * (bands - 1) + 1 + i, 1, 1) for i in range(last_band_rows)]
    return rows


def stretched(first, last, added):
    """`added` single-column (or single-row) copies spread from `first` to `last`: an even stretch
    for an irregular texture without a pattern, such as scratched metal."""
    return spread(first, last, added, 1, 1)


def side_panel(side, height_growth, header_split=75):
    """The side part of a details bitmap, SIDE_GROWTH columns wider and `height_growth` rows taller.

    The header bar and the bottom edge take one mirrored insert. The hatched panel between them
    (rows 32 to its end) takes many inserts of one period each, which keeps its hatch and its
    gradient unbroken.
    """
    h = side.height
    body_end = h - 11
    side = grow_bands(side, "x", [
        (0, 32, [(header_split, SIDE_GROWTH)]),
        (32, body_end, spread(20, 270, SIDE_GROWTH // 3, 3, 3)),
        (body_end, h, [(150, SIDE_GROWTH)]),
    ])
    if height_growth % 3:
        raise ValueError("the side panel grows in periods of 3 rows")
    return grow(side, "y", spread(60, body_end - 20, height_growth // 3, 3, 3))


# --- a3-unit-details (redesign build, 2026-10-16) ---
# The division and ship details windows have a 10x10 rectangle (S20), so a tiled sprite as their Background
# would take that size [SPR-001]: their Background is the dark plain tile laid out at the window's size here,
# as the engine lays out a corneredTileSpriteType with tilingCenter (corners kept, edges and centre repeated).
def tiled_window(width, height, border=64):
    """A compose function: the source tile (tiles/tiled_plain_bg.dds) laid out at width x height."""

    def compose(source):
        sw, sh = source.size
        bx, by = min(border, sw // 2), min(border, sh // 2)
        src_cols = [(0, bx), (bx, sw - bx), (sw - bx, sw)]
        src_rows = [(0, by), (by, sh - by), (sh - by, sh)]
        dst_cols = [(0, bx), (bx, width - bx), (width - bx, width)]
        dst_rows = [(0, by), (by, height - by), (height - by, height)]
        out = Image.new("RGBA", (width, height))
        for (sy1, sy2), (dy1, dy2) in zip(src_rows, dst_rows):
            for (sx1, sx2), (dx1, dx2) in zip(src_cols, dst_cols):
                piece = source.crop((sx1, sy1, sx2, sy2))
                for ty in range(dy1, dy2, sy2 - sy1):
                    for tx in range(dx1, dx2, sx2 - sx1):
                        out.paste(piece.crop((0, 0, min(sx2 - sx1, dx2 - tx), min(sy2 - sy1, dy2 - ty))), (tx, ty))
        return out

    return compose


def band_of(compose, box):
    """A compose function: one area of another composed bitmap. The blue picture band of the ship and
    air wing bitmaps of the first build becomes a plate of its own."""
    return lambda source: compose(source).crop(box)


# Sizes of the redesigned unit details windows (interface/zz_1440p_unit_details.gui).
UD_DIVISION_SIZE = (1186, 562)
UD_SHIP_SIZE = (794, 462)
UD_SHIP_BAND = (4, 446, 776, 580)       # 772x134 out of the first build's ship bitmap
UD_AIR_BAND = (4, 437, 776, 581)        # 772x144 out of the first build's air wing bitmap
# --- end a3-unit-details ---


# A3 redo: the paper of the ship, air wing and railway gun bitmaps is taller, so that two rows of stat
# cards (194 and 142 px) fit on it: 7 bands of 24 rows and a last band of 7, 175 rows in all (it was 64).
SMALL_PER_BAND = 24
SMALL_LAST_BAND = 7
SMALL_PAPER_GROWTH = 7 * SMALL_PER_BAND + SMALL_LAST_BAND


def small_details(frame_band, bottom_inserts):
    """A compose function for the ship and air wing details bitmaps, 856x409 to 1180x475.

    They are painted like the division bitmap, with 8 stat rows and one lower panel:
      0-32     title bar                     33-65    header strip (name field, columns 110-378)
      66-77    frame line above the paper    78-257   paper, printed lines every 20 rows from 119
      258-...  frame line below the paper (`frame_band`: its end row and its column inserts)
      ...      lower panel, plain between columns 12 and 532
      last 10  bottom edge (`bottom_inserts`)
    """
    frame_end, frame_inserts = frame_band

    def compose(source):
        h = source.height
        main = grow_bands(source.crop((0, 0, 553, h)), "x", [
            (0, 33, [(400, MAIN_GROWTH)]),
            (33, 66, [(370, MAIN_GROWTH)]),
            (66, 78, PAPER_FRAME_COLUMNS),
            (78, 258, paper_columns()),
            (258, frame_end, frame_inserts),
            (frame_end, h - 10, stretched(20, 520, MAIN_GROWTH)),
            (h - 10, h, bottom_inserts),
        ])
        rows = paper_rows(104, 8, last_band_rows=SMALL_LAST_BAND, per_band=SMALL_PER_BAND) + stretched(300, 380, 2)
        main = grow(main, "y", rows)
        side = side_panel(source.crop((553, 0, 856, h)), sum(row[1] for row in rows))
        return join([main, side], "x")

    return compose


# Template tab of the division window: a board with a tree of five regiment columns (vertical lines
# at columns 18, 103, 188, 273 and 358, hanging from a line in row 83), a support box (columns
# 447-518, rows 91-294) and a regimental support box (columns 25-437, rows 332-400).
TEMPLATE_COLUMN = 46      # 85 -> 131 px per regiment column; 5 columns and 4 px in the support box
TEMPLATE_ROW = 8          # 46 -> 54 px per regiment row


def template_board(source):
    """The template board, 548x423 to 782x465: it fills the main part of the enlarged window.

    Columns: each regiment column is stretched between its line and the next; the ornament above
    the tree (rows 28-82, columns 115-385) moves as a whole so its stem still meets the middle of
    the tree. Rows: the five regiment rows are stretched, the support box along with them.
    """
    w, h = source.size
    columns = []
    for first, last in ((30, 100), (106, 186), (191, 271), (277, 354), (362, 434)):
        columns += stretched(first, last, TEMPLATE_COLUMN)
    columns += stretched(455, 510, MAIN_GROWTH - 5 * TEMPLATE_COLUMN)
    left = 5 * TEMPLATE_COLUMN // 2 + 1          # keeps the stem above the middle of the tree line
    board = grow_bands(source, "x", [
        (0, 28, [(300, MAIN_GROWTH)]),
        (28, 83, [(105, left), (500, MAIN_GROWTH - left)]),
        (83, 402, columns),
        (402, h, [(300, MAIN_GROWTH)]),
    ])
    rows = 5 * TEMPLATE_ROW
    rest = 42 - rows
    support = 447 + 5 * TEMPLATE_COLUMN - 1      # first column of the support box after the growth
    return grow_bands(board, "y", [
        (0, support, stretched(90, 326, rows) + stretched(360, 395, rest)),
        (support, board.width, stretched(95, 290, rows) + stretched(300, 410, rest)),
    ])


def hq_board(source):
    """The picture behind an HQ template, 521x388 to 755x430. The painting (columns 0-313) keeps
    its size; the dark panel beside it grows, and the plain strip below the painting is repeated."""
    board = grow(source, "x", [(515, MAIN_GROWTH)])
    return grow(board, "y", [(386, 36)] + stretched(348, 384, 6))


# ---------------------------------------------------------------------------------------------
# A4: fleet panel. Every bitmap of the panel is 493 columns wide in vanilla (the panel is 492) and
# grows by FLEET_GROWTH columns. The fleet card and the task force card are painted alike: a blue
# title bar with a black name plate (columns 44-302), boxes on scratched metal, a tray.
FLEET_GROWTH = 248        # 492 -> 740 px: one line per ship with the class name whole
FLEET_PLATE = 148         # of which the name plate takes this much
SHIP_ROW_CUT = [(14, 3), (26, 3)]   # a ship row loses 6 rows: 41 -> 35 px per row


def cut(image, axis, spans):
    """Remove columns (axis "x") or rows (axis "y"): `spans` lists (first, count) in the lines of the
    image as passed in. Short spans spread over a gradient leave no visible step."""
    horizontal = axis == "x"
    w, h = image.size
    keep, at = [], 0
    for first, count in sorted(spans):
        keep.append(image.crop((at, 0, first, h) if horizontal else (0, at, w, first)))
        at = first + count
    keep.append(image.crop((at, 0, w, h) if horizontal else (0, at, w, h)))
    return join(keep, axis)


def fleet_card(source):
    """Fleet card, 493x166 to 741x166. Bands of rows:
      0-39     title bar: the name plate grows, the count badge (columns 322-405, its rim down to
               row 37) moves with it
      40-92    commander: the name box (columns 78-224) and the stats box (224-297) grow by 60 each
      93-128   composition tray (columns 78-405)
      129-165  metal and the blue footer
    """
    rest = FLEET_GROWTH - FLEET_PLATE
    return grow_bands(source, "x", [
        (0, 40, stretched(70, 280, FLEET_PLATE) + stretched(412, 480, rest)),
        (40, 93, stretched(90, 215, 60) + stretched(232, 290, 60) + stretched(310, 460, FLEET_GROWTH - 120)),
        (93, 129, stretched(90, 395, FLEET_GROWTH)),
        (129, source.height, stretched(20, 460, FLEET_GROWTH)),
    ])


TASK_FORCE_TRAY = (79, 39)   # rows of the composition tray, which the wide card does without


def task_force_card(source):
    """Task force card, 493x125 to 741x86. Bands of rows:
      0-31     title bar, as on the fleet card
      32-78    the mission box (columns 8-380) takes the growth but 30 columns, which go to the
               box for the order buttons (387-482)
      79-117   composition tray (columns 8-482): cut, the counters sit in the mission box
      118-124  bottom edge
    """
    rest = FLEET_GROWTH - FLEET_PLATE
    wide = grow_bands(source, "x", [
        (0, 32, stretched(70, 280, FLEET_PLATE) + stretched(310, 480, rest)),
        (32, 79, stretched(20, 370, FLEET_GROWTH - 30) + stretched(395, 475, 30)),
        (79, source.height, stretched(20, 470, FLEET_GROWTH)),
    ])
    return cut(wide, "y", [TASK_FORCE_TRAY])


POPUP_GROWTH = 80         # composition editor and home base picker: 524 -> 604 and 375 -> 455
TRANSFER_GROWTH = 160     # "Select Ships to Transfer": 535 -> 695, a ship on one line


def ship_row(right_cap, growth=FLEET_GROWTH):
    """One frame of the ship row, 493x47 to 741x41 (or by another growth): a fine mesh that repeats
    every 29 columns, edge bars in rows 0-5 and 40-46, and (selected frame) a chevron in the last columns."""
    def widen(frame):
        wide = widen_periodic(frame, frame.width + growth, period=29, split=330, top=6, bottom=40, right_cap=right_cap)
        return cut(wide, "y", SHIP_ROW_CUT)
    return widen


# ---------------------------------------------------------------------------------------------
# A5, Recruit & Deploy and Division Templates. The numbers are shared with the widget positions in
# interface/zz_1440p_recruit_deploy.gui.

DEPLOY_GROWTH = 90        # left panel, 550 -> 640: the name of a division in training gets it
TEMPLATE_GROWTH = 240     # a template row, 341 -> 581: name, cap, Train, Edit and toggles on one line
TEMPLATE_PANEL_GROWTH = 243   # the template panel, 375 -> 618
TEMPLATE_SPLIT = 85       # first column right of the icon box's frame line


# Redesign (2026-10-16): every template in training is one card on the 575 px spine of the priority
# rows. The code inserts the card's rows one by one (a head, a band, a line per division, a foot), so
# the card's frame is the vanilla tiled window frame (tiles/tiled_window2_1b_border.dds, 190x190,
# corners of 64) drawn at the spine's width and cut into one slice per row window. Rows of the frame:
#   0-3 soft shadow, 4-11 rim, 12-27 inner shadow, 28-159 plain inside, 160-177 inner shadow,
#   178-185 rim, 186-189 soft shadow.
# The head is the top of the frame under the gap between two cards (transparent); the band and the
# line are rows of the plain inside, so they join each other in any order; the foot is the lower rim.

CARD_WIDTH = 575          # the step-2 priority rows
CARD_GAP = 6              # Design Rules, "Spacing": two cards stacked
CARD_FRAME_BORDER = 64    # the borderSize of GFX_tiled_window2_1b_border
CARD_HEAD_ROWS = range(0, 78)       # 84 with the gap: military_deployment_conveyor_view
CARD_BAND_ROWS = range(40, 72)      # 32: military_deployment_conveyor_summary_view
CARD_LINE_ROWS = range(40, 80)      # 40: military_deployment_line_view
CARD_FOOT_ROWS = range(178, 187)    # 9: military_deployment_conveyor_end_view, the rim and one shadow row
LOCATION_GROWTH = 60      # location button of a card, 223 -> 283 (its chevrons repeat every 15 columns)


def card_frame(source, width=CARD_WIDTH, border=CARD_FRAME_BORDER):
    """The frame at `width` columns: corners and edges kept, the middle columns repeated as the game
    tiles a corneredTileSpriteType with tilingCenter."""
    w, h = source.size
    out = Image.new("RGBA", (width, h))
    out.paste(source.crop((0, 0, border, h)), (0, 0))
    tile = source.crop((border, 0, w - border, h))
    for x in range(border, width - border, tile.width):
        out.paste(tile.crop((0, 0, min(tile.width, width - border - x), h)), (x, 0))
    out.paste(source.crop((w - border, 0, w, h)), (width - border, 0))
    return out


def tile9(image, width, height, border, mirror=False):
    """`image` at width x height as the game draws a corneredTileSpriteType with tilingCenter: corners of
    `border` kept, edges and middle repeated (never scaled). With `mirror`, every second repeat across is
    flipped, so that each join is between a column and its own copy: no seam where the middle has a
    gradient from side to side."""
    w, h = image.size
    bx, by = (border, border) if isinstance(border, int) else border
    out = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    src_x = [(0, bx), (bx, w - bx), (w - bx, w)]
    src_y = [(0, by), (by, h - by), (h - by, h)]
    dst_x = [(0, bx), (bx, width - bx), (width - bx, width)]
    dst_y = [(0, by), (by, height - by), (height - by, height)]
    for (sy1, sy2), (dy1, dy2) in zip(src_y, dst_y):
        for (sx1, sx2), (dx1, dx2) in zip(src_x, dst_x):
            piece = image.crop((sx1, sy1, sx2, sy2))
            flipped = piece.transpose(Image.FLIP_LEFT_RIGHT) if mirror else piece
            for ty in range(dy1, dy2, piece.height):
                for i, tx in enumerate(range(dx1, dx2, piece.width)):
                    part = flipped if i % 2 else piece
                    out.paste(part.crop((0, 0, min(piece.width, dx2 - tx), min(piece.height, dy2 - ty))), (tx, ty))
    return out


# The row of a template, 581x48: a plate with the symbol's tile at 3,4 (84x40), in one bitmap so that
# the code's swap of Background and Background_obsolete swaps the tile with the plate. The plain row is
# GFX_tiled_plain_bg_small with the tile of the priority rows (deploy_priority_icon_bg.dds); the row of a
# decommissioned template is the brown GFX_deployment_item_bg (corners of 18x16: its plain inside runs from
# column 18 to 50) with the copper symbol box of the vanilla
# decommissioned row (deployment_named_division_obsolete_bg.dds, columns 7-85, rows 7-67).
TEMPLATE_PLATE = (581, 48)
TEMPLATE_TILE = (3, 4, 84, 40)


def template_plate(plate_border, tile_texture, tile_box, tile_border):
    def compose(source, game_dir):
        plate = tile9(source, TEMPLATE_PLATE[0], TEMPLATE_PLATE[1], plate_border, mirror=True)
        tile = Image.open(os.path.join(game_dir, *tile_texture.split("/"))).convert("RGBA")
        if tile_box:
            tile = tile.crop(tile_box)
        x, y, w, h = TEMPLATE_TILE
        plate.alpha_composite(tile9(tile, w, h, tile_border), (x, y))
        return plate
    return compose


def card_slice(rows, gap=0):
    """A compose function: the rows `rows` of the card frame, under `gap` transparent rows."""
    def compose(source):
        frame = card_frame(source)
        out = Image.new("RGBA", (CARD_WIDTH, gap + len(rows)), (0, 0, 0, 0))
        for i, row in enumerate(rows):
            out.paste(frame.crop((0, row, CARD_WIDTH, row + 1)), (0, gap + i))
        return out
    return compose


def template_row(mesh_rows, strip_rows, mesh_period):
    """Row of a template, 346x78 to 586x54 (the brown twin of a decommissioned template: 348x79 to
    588x55). The vanilla row is an icon box (columns 0-84) beside a meshed name box with a metal
    strip for the buttons under it. The one-line row does without the strip:
      icon box   loses 24 rows of its plain inside, in six spans between its corner rivets
      name box   loses 12 rows of mesh and 12 of the 13 rows of the strip, then grows by
                 TEMPLATE_GROWTH columns: plain lines above and below, two pieces of the mesh
    """
    def compose(source):
        w, h = source.size
        box = cut(source.crop((0, 0, TEMPLATE_SPLIT, h)), "y", [(18, 4), (25, 4), (32, 4), (39, 4), (46, 4), (52, 4)])
        first_mesh, strip = mesh_rows[0], strip_rows[0]
        name = cut(source.crop((TEMPLATE_SPLIT, 0, w, h)), "y", [(first_mesh + 4, 4), (first_mesh + 14, 4), (first_mesh + 24, 4), (strip, 12)])
        mesh_end = mesh_rows[1] - 12
        half = TEMPLATE_GROWTH // 2   # the mesh runs from column 7 to 251 of the name part: two pieces fit
        if TEMPLATE_GROWTH % 2 or half % mesh_period or half > 120:
            raise ValueError("the template row cannot grow by %d columns" % TEMPLATE_GROWTH)
        name = grow_bands(name, "x", [
            (0, first_mesh, stretched(20, 240, TEMPLATE_GROWTH)),
            (first_mesh, mesh_end, [(130, half, mesh_period), (244, half, mesh_period)]),
            (mesh_end, name.height, stretched(20, 240, TEMPLATE_GROWTH)),
        ])
        return join([box, name], "x")
    return compose


# ---------------------------------------------------------------------------------------------
# A6, the army overview tab (divisions, fleets, air wings). The numbers are shared with the widget
# positions in interface/zz_1440p_army_overview.gui.

OVERVIEW_GROWTH = 350     # panel 550 -> 900 (title bar, picture strip)
OVERVIEW_ROW = 738        # rows of the list since the redesign of 2026-10-16: 13 margin, rows, 25 for the
                          # scrollbar, then the rail of cards at the right (modifiers, counts by type)
OVERVIEW_BARS = 48        # the olive part beside the type icon takes the two bars lying down


def overview_gap(source, x0, x1, width):
    """An olive gap between two dark boxes at `width`: its two ends kept, the plain middle dropped."""
    half = width // 2
    return join([source.crop((x0, 0, x0 + half, 35)), source.crop((x1 - (width - half), 0, x1, 35))], "x")


def overview_army_row(source):
    """Division row, 509x35 to 738x35. The vanilla row is an olive part (columns 0-123: details
    button, type icon, bars, level), a dark name box (124-295), an olive gap (296-305), a dark box
    for theatre and army on two lines (306-447) and an olive end with the army marker (448-508).
    The wide row has the theatre and the army (its shield and its name together) in a box each:
      olive 164 | name 262 | gap 6 | theatre 160 | gap 6 | army 140"""
    left = grow(source.crop((0, 0, 124, 35)), "x", stretched(98, 120, OVERVIEW_BARS - 8))
    name = grow(source.crop((124, 0, 296, 35)), "x", stretched(12, 160, 90))
    gap = overview_gap(source, 296, 306, 6)
    box = source.crop((306, 0, 448, 35))
    theatre = grow(box, "x", stretched(12, 130, 18))
    army = cut(box, "x", [(60, 1), (90, 1)])
    out = join([left, name, gap, theatre, gap, army], "x")
    assert out.width == OVERVIEW_ROW, out.width
    return out


def overview_navy_row(source):
    """Fleet row, 509x35 to 738x35: a dark icon box (0-110), an olive part with the pride mark, the
    bars and the admiral (111-166), a dark name box (167-316), a gap (317-323), a dark region box
    (324-447) and an olive end with the mission and the ship count (448-508).
      icon 111 | olive 104 | name 272 | gap 7 | region 183 | end 61"""
    out = join([
        source.crop((0, 0, 111, 35)),
        grow(source.crop((111, 0, 167, 35)), "x", stretched(4, 22, OVERVIEW_BARS)),
        grow(source.crop((167, 0, 317, 35)), "x", stretched(12, 138, 122)),
        source.crop((317, 0, 324, 35)),
        grow(source.crop((324, 0, 448, 35)), "x", stretched(12, 112, 59)),
        source.crop((448, 0, 509, 35)),
    ], "x")
    assert out.width == OVERVIEW_ROW, out.width
    return out


def overview_air_row(source):
    """Air wing row, 509x35 to 738x35: a dark icon box with the plane count (0-96), an olive part with
    the bar and the ace (97-136), then three dark boxes: name (137-266), base (267-392) and region with
    the missions under it (393-508), the last one up to the row's end. The name box is the widest: a
    wing of the user's playset is "Kampfgeschwader 253 'General Wever'" (258 px in hoi_18mbs).
      icon 97 | olive 88 | name 266 | base 134 | region 153"""
    out = join([
        source.crop((0, 0, 97, 35)),
        grow(source.crop((97, 0, 137, 35)), "x", stretched(6, 34, OVERVIEW_BARS)),
        grow(source.crop((137, 0, 267, 35)), "x", stretched(12, 118, 136)),
        grow(source.crop((267, 0, 393, 35)), "x", stretched(12, 114, 8)),
        grow(source.crop((393, 0, 509, 35)), "x", stretched(12, 100, 37)),
    ], "x")
    assert out.width == OVERVIEW_ROW, out.width
    return out


# ---------------------------------------------------------------------------------------------
# A8, the theatre boxes at the top right (theatreselector.gui), as cards (redesign of 2026-10-16). A box
# is a window of 420x88 at x 310; its card is drawn 424x86 over it, as vanilla's 305 over 300, and the
# rows under a box are drawers of the same width. The numbers are shared with
# interface/zz_1440p_theatre_bar.gui. Fix round 1 (2026-10-16): the title plate 40 high instead of 32,
# so that its grey part (rows 8-37 of the card) holds the 28 px chips at y 9; the card 8 taller.

CARD_W, CARD_H = 424, 86
CARD_STRIPE = (5, 4, 6)          # x, y, width of the colour stripe down the card and its rows
CARD_TITLE = (12, 4, 404, 40)    # the title plate: x, y, width, height
CARD_BAND_W = 404                # the units band (assign_button), at x 12 y 46


def tile_nine(image, border, width, height):
    """An image laid out at `width` x `height` the way a corneredTileSpriteType with tilingCenter = yes
    lays it out: the corners kept, the edges and the middle repeated. Pixel copies only."""
    bx, by = min(border[0], image.width // 2), min(border[1], image.height // 2)
    out = Image.new("RGBA", (width, height))
    cols = [(0, bx, 0, bx), (bx, image.width - bx, bx, width - bx), (image.width - bx, image.width, width - bx, width)]
    rows = [(0, by, 0, by), (by, image.height - by, by, height - by), (image.height - by, image.height, height - by, height)]
    for sy1, sy2, dy1, dy2 in rows:
        for sx1, sx2, dx1, dx2 in cols:
            piece = image.crop((sx1, sy1, sx2, sy2))
            for y in range(dy1, dy2, piece.height):
                for x in range(dx1, dx2, piece.width):
                    out.paste(piece.crop((0, 0, min(piece.width, dx2 - x), min(piece.height, dy2 - y))), (x, y))
    return out


def frames_of(image, count):
    width = image.width // count
    return [image.crop((i * width, 0, (i + 1) * width, image.height)) for i in range(count)]


def colour_stripe(piece, height):
    """A stripe of CARD_STRIPE's width from a plain coloured piece, its rows repeated to `height`."""
    return piece.resize((CARD_STRIPE[2], height), Image.NEAREST)


def theatre_card(source, tile, header):
    """The card of a theatre box, five frames of 424x86 in the order of theater_group_bg.dds (army
    gold, grey, navy blue, reserve fleets striped blue, air red), which the code switches between.

    Each frame: tiled_plain_bg_small laid out at the card's size (border 16), a 6 px stripe of the
    frame's own colour (rows 8-34 of the plain part at columns 236-242 of the vanilla frame), and the
    title plate unit_list_header (border 24x12) at 404x40."""
    x, y, w, h = CARD_TITLE
    out = []
    for frame in frames_of(source, 5):
        card = tile_nine(tile, (16, 16), CARD_W, CARD_H)
        card.paste(colour_stripe(frame.crop((236, 8, 242, 34)), CARD_H - 2 * CARD_STRIPE[1]), CARD_STRIPE[:2])
        card.alpha_composite(tile_nine(header, (24, 12), w, h), (x, y))
        out.append(card)
    return join(out, "x")


def theatre_band(frame):
    """One frame of the units band (assign_group_button), 299x35 to 404x35: oak leaves at both ends;
    the grey frame has hands at 15-35 and 262-282 and an emblem at 129-168, so the columns go in on
    both sides of the emblem."""
    added = CARD_BAND_W - frame.width
    return grow(frame, "x", stretched(60, 115, added // 2) + stretched(185, 240, added - added // 2))


def theatre_drawer(source, tile, bottom):
    """A row under a box (a middle row, or the last with `bottom`), four frames of 424x33
    or 424x39 in the order of theatre_dropdown_middle.dds (grey, green, blue, red).

    The card's side borders run on (the middle rows of tiled_plain_bg_small; the bottom piece takes its
    bottom border too, and closes the card), the stripe goes on in the frame's own colour (columns
    150-156, rows 6-26 of the vanilla frame), and the vanilla frame spread to 404 columns is the plate."""
    height = 39 if bottom else 33
    out = []
    for frame in frames_of(source, 4):
        tall = tile_nine(tile, (16, 16), CARD_W, height + (16 if bottom else 32))
        row = tall.crop((0, 16, CARD_W, 16 + height))
        row.paste(colour_stripe(frame.crop((150, 6, 156, 26)), height - (6 if bottom else 0)), (CARD_STRIPE[0], 0))
        plate = widen_spread(frame, CARD_W - 20, 24, 24).crop((0, 2, CARD_W - 20, 31))
        row.alpha_composite(plate, (12, 2))
        out.append(row)
    return join(out, "x")


# ---------------------------------------------------------------------------------------------
# Production (phase C1). A production line is painted as a header band (rows 0-27) over a body: the
# equipment plate (columns 2-278, a clasp at 122-150 of its top and bottom edge), a dark gap
# (278-320, plain to 300), the factory slots (320-470) and the resource column (470-510). A line grows
# from 511 to 780 columns: the plate by PROD_PLATE in its plain middle (160-260), the dark gap by
# PROD_GAP. The numbers are shared with the widget positions in interface/zz_1440p_production.gui.
# (Round 1 made the lines 1000 wide and the plate 142 wider; the game draws the picture at a fixed
# place [GUL-041] and the tester found the panel too wide and empty, 2026-10-16.)

PROD_PLATE = 20           # equipment plate 278 -> 298: 20 free on each side of the picture
PROD_GAP = 249            # the gap becomes the column of manufacturer, deploy location and ready date


def production_columns(frame, gap=True):
    """A production line bitmap, or a piece of one (the equipment plate, an overlay), grown by the
    plate insert and, unless `gap` is false, the gap insert."""
    inserts = stretched(160, 260, PROD_PLATE)
    if gap:
        inserts += stretched(284, 300, PROD_GAP)
    return grow(frame, "x", inserts)


# --- C1 ---
# Round 2, bold variant (2026-10-20): every card of the production panel is cut from vanilla's gunmetal
# steel bar (tiled_frontend_upper_bar, the main menu's riveted bar), recoloured only: the top band
# lightened is the head, its rule and groove divide head from body, the body is darkened graphite, and the
# columns sit in near-black insets of tiled_window_thin_border. Sizes are shared with
# interface/zz_1440p_production.gui and scratch/phases/C1/mock_c1r2b.py.

STEEL_BAR = "gfx/interface/tiles/tiled_frontend_upper_bar.dds"
CARD_INSET = "gfx/interface/tiles/tiled_window_thin_border.dds"
NAVAL_STRIP = "gfx/interface/naval_production_item_slots_strip.dds"
HEAD_H = 27                # a line card's head band, rows 0-26; the plate and the picture start at 27 [GUL-041]
CARD_GAP = 6               # transparent rows under every line card: 110 + 6 = the window's 116 (collapsed 60 + 6)
LINE_W = 780
PROD_X, PROD_W = 310, 266  # the production inset's column and width
FAC_X, FAC_W = 620, 158    # the factories inset


def _gain(image, factor, box):
    """Lighten or darken the colours of a box of `image` (alpha kept)."""
    piece = image.crop(box)
    r, g, b, a = piece.split()
    r, g, b = (ch.point(lambda v: min(255, int(v * factor))) for ch in (r, g, b))
    image.paste(Image.merge("RGBA", (r, g, b, a)), box[:2])


def _htile(src, width, side=24):
    """The columns of `src` laid out at `width`: `side` columns kept at each end (with the corner rivets), the middle repeated."""
    out = Image.new("RGBA", (width, src.height))
    mid = src.crop((side, 0, src.width - side, src.height))
    for x in range(side, width - side, mid.width):
        out.paste(mid.crop((0, 0, min(mid.width, width - side - x), src.height)), (x, 0))
    out.paste(src.crop((0, 0, side, src.height)), (0, 0))
    out.paste(src.crop((src.width - side, 0, src.width, src.height)), (width - side, 0))
    return out


def steel_plate(bar, width, height, head=0, head_gain=1.9, bottom_rows=15, body_gain=0.8):
    """A steel card of width x height from the steel bar `bar` (484x128): rows 0-8 the edge, with `head` rows
    the top band (rows 12-27 repeated, lightened) ending in the bright rule (33) and the groove (34-35),
    then the body (rows 44-100 repeated, darkened) and the bottom edge; 24 columns kept at each side."""
    rows = list(range(0, 9))
    if head:
        band = list(range(12, 28))
        rows += [band[i % len(band)] for i in range(head - 10)] + [33, 34, 35]
    body = list(range(44, 101))
    rows += [body[i % len(body)] for i in range(height - len(rows) - bottom_rows)] + list(range(128 - bottom_rows, 128))
    src = Image.new("RGBA", (bar.width, len(rows)))
    for dy, sy in enumerate(rows):
        src.paste(bar.crop((0, sy, bar.width, sy + 1)), (0, dy))
    _gain(src, body_gain, (0, head + 2 if head else 9, bar.width, len(rows) - 4))
    if head:
        _gain(src, head_gain, (0, 4, bar.width, head - 1))
    return _htile(src, width)


def slot_box(strip):
    """A factory slot box, 28x22, in the steel look: one cell of the mesh of vanilla's three-row slot tray
    (the last frame of naval_production_item_slots_strip, 511 wide, cell at 325-352 x 55-76) turned grey and
    lightened x2, in a 1 px frame lit from the top left."""
    from PIL import ImageOps
    cell = strip.crop((strip.width - 511 + 347, 55, strip.width - 511 + 374, 76)).convert("L")
    cell = cell.point(lambda v: min(255, int(v * 2.1 + 6)))
    box = Image.new("RGBA", (28, 22), (22, 23, 25, 255))
    box.paste(Image.new("RGBA", (27, 21), (74, 76, 80, 255)), (0, 0))
    box.paste(ImageOps.colorize(cell, (0, 0, 0), (255, 255, 255)).convert("RGBA").crop((0, 0, 26, 20)), (1, 1))
    return box


def _inset(card, inset_tile, x, y, w, h):
    card.alpha_composite(tile_nine(inset_tile, (8, 8), w, h), (x, y))


def line_card(bar, inset_tile, box, slot_rows=0, collapsed=False):
    """A line card: the steel plate with its head, the black insets of the production column (and of the
    factory slots, with `slot_rows` rows of slot boxes), CARD_GAP transparent rows below."""
    h = 60 if collapsed else 110
    card = steel_plate(bar, LINE_W, h, head=HEAD_H)
    if collapsed:
        _inset(card, inset_tile, PROD_X - 4, 29, PROD_W + 8, 28)
    else:
        _inset(card, inset_tile, PROD_X - 4, 29, PROD_W + 8, h - 33)
        _inset(card, inset_tile, FAC_X - 2, 29, FAC_W, h - 33)
        for r in range(slot_rows):
            for c in range(5):
                card.alpha_composite(box, (FAC_X + 3 + 30 * c, 34 + 23 * r))
    out = Image.new("RGBA", (LINE_W, h + CARD_GAP), (0, 0, 0, 0))
    out.paste(card, (0, 0))
    return out


def _ring(card, width=2):
    """The card's outline `width` px thick (its alpha minus the same eroded), as a light steel stroke."""
    from PIL import ImageChops, ImageFilter
    alpha = card.getchannel("A")
    inner = alpha.filter(ImageFilter.MinFilter(2 * width + 1))
    mask = ImageChops.subtract(alpha, inner)
    out = Image.new("RGBA", card.size, (214, 219, 224, 255))
    out.putalpha(mask)
    return out


def selection_outline(bar, collapsed=False):
    """GFX_1440p_PD_line_selected: the 2 px light steel outline of a card's shape."""
    return _ring(steel_plate(bar, LINE_W, 60 if collapsed else 110, head=HEAD_H))


def mio_tint(bar):
    """GFX_1440p_PD_line_has_mio: a warm tint over the head band only, so the name stays readable."""
    band = steel_plate(bar, LINE_W, 60, head=HEAD_H).crop((0, 0, LINE_W, HEAD_H))
    out = Image.new("RGBA", band.size, (205, 150, 55, 255))
    out.putalpha(band.getchannel("A").point(lambda v: v * 85 // 255))
    return out


def title_strip(bar):
    return steel_plate(bar, 816, 46, head=40, head_gain=1.25, bottom_rows=4)


def top_materials(bar):
    return steel_plate(bar, 500, 92)


def top_figures(bar, inset_tile):
    """The figures table: the steel head band is the head bar, rows 1 and 3 on a black band (the plain
    middle of the inset texture, no frame), row 2 on the graphite."""
    card = steel_plate(bar, 306, 92, head=HEAD_H)
    band = _htile(inset_tile.crop((10, 10, 180, 30)), 294, side=0)
    for r in (0, 2):
        card.alpha_composite(band, (6, 27 + 20 * r))
    return card


def top_filters(bar, source):
    """The filter strip: a steel strip with the twelve cells (the checkbox's tray and its count box, cut
    from the vanilla top, production_win_top.dds) at 66 columns each, a 6 px gap after the sixth."""
    card = steel_plate(bar, 812, 36, bottom_rows=6)
    x = 6
    for top in (176, 207):
        for k in range(6):
            c = 13 + 85 * k
            for a, b, dx in ((c, c + 44, 0), (c + 63, c + 85, 44)):
                card.alpha_composite(source.crop((a, top + 6, b, top + 34)), (x + dx, 3))
            x += 66
        x += 6
    return card


def goods_card(bar):
    """The consumer goods line: a steel plate without a head, 780x69, CARD_GAP transparent rows below."""
    out = Image.new("RGBA", (LINE_W, 69 + CARD_GAP), (0, 0, 0, 0))
    out.paste(steel_plate(bar, LINE_W, 69), (0, 0))
    return out


def naval_strip_301(source):
    """The collapsed naval equipment strip (vanilla 352 wide) cut to the card's 301: its left 290 columns
    and its own right end."""
    return join([source.crop((0, 0, 290, source.height)), source.crop((source.width - 11, 0, source.width, source.height))], "x")


# --- end C1 ---


def steel_piece(bar, kind, width, height, head=0, head_gain=1.9, bottom_rows=15):
    """A piece of the steel look (the default since 2026-10-21) at its size, as a layout file names it
    (tools/layout.py, steel_params): a "steel" card, with `head` rows of head band or none, or the
    "steel_title" strip. tools/apply_layout.py writes it as a DDS, tools/mockup.py draws it."""
    return steel_plate(bar, width, height, head=head, head_gain=head_gain, bottom_rows=bottom_rows)


# ---------------------------------------------------------------------------------------------
# General selection (phase C2). The window grows from 550x607 to 800x1180, a general's row from 510x98
# to 760x124 with a portrait box 32 wider. Shared with interface/zz_1440p_leader_selection.gui.

LEADER_ROW_WIDTH = 760
LEADER_ROW_HEIGHT = 124
LEADER_PORTRAIT_GROWTH = 32   # the white portrait box, 64 -> 96 columns


def leader_window(source):
    """The window: its header band holds a painted search field (columns 175-315), so the columns go in
    to its right (375-500, plain); the rows go in across the plain dark middle (110-520), which darkens
    towards the bottom, as many single rows so the gradient stays smooth."""
    out = grow(source, "x", [(500, 250)])
    return grow(out, "y", stretched(110, 520, 1180 - source.height))


def leader_row(source):
    """A general's row: the white portrait box (56-120) takes columns from its plain inside; the paper
    takes a mirrored insert from the plain right half (321-430); the rows go in across the stripes of
    the emblem column and the plain paper under the name (66-79)."""
    paper = LEADER_ROW_WIDTH - source.width - LEADER_PORTRAIT_GROWTH
    out = grow(source, "x", [(100, LEADER_PORTRAIT_GROWTH), (430, paper)])
    return grow(out, "y", [(79, LEADER_ROW_HEIGHT - source.height)])


# --- c2-state-rows (fix round 1, 2026-10-16) ---
# The code swaps a general's row background by vanilla name for every state but the plain one (hoi4.exe 1.19.3,
# FUN_141ad3580: field marshal, active, unavailable, faction commander), each 510x98 like the plain row. They are
# declared again at 760x124 in interface/zz_1440p_vanilla_sprites.gfx [LOAD-012], built here to the plain row's
# layout: the portrait box 32 wider (56-152), the paper's features where the plain row has them, the capacity box
# 250 to the right. Rows 0-3 and 93-97 of every source are transparent: the gap between two rows.
LEADER_STRIPE_PERIOD = 30          # the diagonal stripes of an active row repeat every 30 columns and 30 rows
LEADER_SEAL = (262, 53, 31)        # centre and radius of the seal an active row carries over its name line


def _insert(image, axis, split, added, donor=None, period=None):
    """One insert of grow(); with `donor` (an image of the same size) the inserted lines are the donor's."""
    spec = [(split, added, period)] if period else [(split, added)]
    out = grow(image, axis, spec)
    if donor is not None:
        fill = grow(donor, axis, spec)
        box = (split, 0, split + added, out.height) if axis == "x" else (0, split, out.width, split + added)
        out.paste(fill.crop(box), box[:2])
    return out


def _column_bands(image, bands):
    """Grow column ranges of an image by rows, each with its own function, and put them back together."""
    return join([grow_rows(image.crop((start, 0, end, image.height))) for start, end, grow_rows in bands], "x")


def leader_row_state(source, plain):
    """A state row on plain paper: field marshal, faction commander, unavailable. Painted like the plain row
    plus a banner under the title, a star watermark (columns 315-400, rows 8-90), stars in the emblem column
    (rows 52-70) and a tinted capacity box. Columns 408-510 equal the plain row's, so the paper's columns go in
    at 430 from the plain row (its plain 321-430), which keeps the star single. Rows go in at 79 left of the
    darker right panel (which starts at column 305, a tonal edge that hides the join), at 88 in the emblem
    column, below its stars, and at 91 in the right panel, below the star, from the plain row."""
    added = LEADER_ROW_HEIGHT - source.height
    paper = LEADER_ROW_WIDTH - source.width - LEADER_PORTRAIT_GROWTH
    wide = _insert(_insert(source, "x", 430, paper, donor=plain), "x", 100, LEADER_PORTRAIT_GROWTH)
    plain_wide = _insert(_insert(plain, "x", 430, paper), "x", 100, LEADER_PORTRAIT_GROWTH)
    panel = 305 + LEADER_PORTRAIT_GROWTH
    right = plain_wide.crop((panel, 0, plain_wide.width, plain_wide.height))
    return _column_bands(wide, [
        (0, 56, lambda band: _insert(band, "y", 88, added)),
        (56, panel, lambda band: _insert(band, "y", 79, added)),
        (panel, wide.width, lambda band: _insert(band, "y", 91, added, donor=right)),
    ])


def leader_row_striped(source):
    """An active row: diagonal stripes over the whole paper (30 columns apart, rising to the right), dashes
    along its top and bottom and a seal over the name line. Every insert of the paper is a whole number of
    stripe periods, so the stripes run on without a break: 210 columns at 430 (120 and 90, both from the plain
    stripes of the darker right panel, 310-430, so the name line, the banner's end and the panel's edge stay
    single) and 30 rows at 79. The other 8 columns go in as single copies spread over 124-140, the dark edge
    of the paper beside the portrait box, where the stripes bend a little to take up the shift; the 4 rows too many come off the transparent gap (2 above, 2 below). The seal is
    lifted out first (its disc filled with the stripes two periods to its left, which carry the same name line
    and banner) and laid back at its place after the rows went in, 40 columns right like the paper around it."""
    period = LEADER_STRIPE_PERIOD
    cx, cy, radius = LEADER_SEAL
    clean = source.copy()
    seal = Image.new("RGBA", source.size)
    for y in range(max(0, cy - radius), min(source.height, cy + radius + 1)):
        for x in range(cx - radius, cx + radius + 1):
            if (x - cx) ** 2 + (y - cy) ** 2 <= radius * radius:
                seal.putpixel((x, y), source.getpixel((x, y)))
                clean.putpixel((x, y), source.getpixel((x - 2 * period, y)))
    paper_shift = 8
    insert = LEADER_ROW_WIDTH - source.width - LEADER_PORTRAIT_GROWTH - paper_shift   # 210, 7 periods
    rows = LEADER_STRIPE_PERIOD                                                        # 30, one period
    first = 4 * period
    wide = grow(clean, "x", [(100, LEADER_PORTRAIT_GROWTH), *stretched(124, 140, paper_shift),
                             (430, first, period), (430, insert - first, period)])
    box_end = 120 + LEADER_PORTRAIT_GROWTH
    tall = _column_bands(wide, [
        (0, 56, lambda band: _insert(band, "y", 88, rows)),
        (56, box_end, lambda band: _insert(band, "y", 79, rows)),
        (box_end, wide.width, lambda band: _insert(band, "y", 79, rows, period=rows)),
    ])
    tall.alpha_composite(seal, (LEADER_PORTRAIT_GROWTH + paper_shift, 0))
    trim = (rows + source.height - LEADER_ROW_HEIGHT) // 2
    return tall.crop((0, trim, tall.width, trim + LEADER_ROW_HEIGHT))
# --- end c2-state-rows ---


# ---------------------------------------------------------------------------------------------
# Priority rows of Recruit & Deploy (A5, step 2): 493 to 575 columns, as wide as the training cards
# under them. A row is the icon box (0-95), a plain band (100-350), a lighter band behind the priority
# buttons (355-385) and the end. The columns go in from the plain band. The code puts these
# backgrounds on the rows by their vanilla names, which the mod declares again
# (interface/zz_1440p_vanilla_sprites.gfx). The label plate and the equipment meter grow with them.

PRIORITY_ROW_WIDTH = 575
PRIORITY_TITLE_GROWTH = 52    # label plate 159 -> 211
PRIORITY_METER_GROWTH = 40    # equipment meter 108 -> 148


def priority_row(source):
    return grow(source, "x", [(300, PRIORITY_ROW_WIDTH - source.width)])


# --- e-diary-wars ---
# E4, 2026-10-16: the file of a war in the Records window, on the game's war overview frame (waroverview_bg_tiled.dds,
# 1168x506: a top plate with crossed swords, two bands, two panels of a dotted mesh with a gradient). It narrows to
# 1092 by taking columns out of the plain middle of each panel (in every band the columns there are plain: the dark
# centre of the top plate, the bands, the panel bodies, the bottom rim), in multiples of the mesh's period of 4, and
# grows to 1090 high in the panel bodies above their corner ornaments, in copies of 4 rows spread over the gradient.
WAR_FILE_W, WAR_FILE_H = 1092, 1090


def war_file(source):
    narrow = cut(source, "x", [(400, 40), (732, 36)])
    added = WAR_FILE_H - narrow.height
    return grow(narrow, "y", spread(232, 420, added // 4, 4, 4))


def frame_of(source, count, n):
    """Frame n of a strip of count frames side by side."""
    width = source.width // count
    return source.crop((n * width, 0, (n + 1) * width, source.height))
# --- end e-diary-wars ---


# --- a2-division-list (redesign build, 2026-10-16) ---
# The division card of the selected army's list: two frames of 638x48 (fix round 1: 42 -> 48, the row window
# 44 -> 50, so the markers of line 2 end inside the hatch or green), the card tile of the A9 badge
# (tiles/tiled_plain_bg_small.dds laid out as a corneredTileSpriteType with border 16) with the inside of the
# vanilla row (unit_entry_bg.dds, 390x33 a frame) over it, 4 px in: frame 1 (not selected) the row's hatch,
# frame 2 (selected) the row's green at about 60 % and a 3 px rail of the green's own edge at the left.
DIVISION_CARD = (638, 48)
DIVISION_CARD_INSET = 4
DIVISION_CARD_ALPHA = 150        # of 255: how much of the hatch and of the green shows over the tile
DIVISION_CARD_RAIL = 3


def division_card(source, tile):
    width, height = DIVISION_CARD
    inner_w, inner_h = width - 2 * DIVISION_CARD_INSET, height - 2 * DIVISION_CARD_INSET
    hatch_frame, green_frame = frames_of(source, 2)
    out = []
    for selected in (False, True):
        card = tile_nine(tile, (16, 16), width, height)
        inner = Image.new("RGBA", (inner_w, inner_h))
        if selected:
            # the green: its plain part (columns 4-385, rows 3-29) spread over the inside, one column and
            # one row copied one or more times (a smooth gradient without a pattern)
            plain = green_frame.crop((4, 3, green_frame.width - 4, green_frame.height - 3))
            for y in range(inner_h):
                sy = y * plain.height // inner_h
                for x in range(inner_w):
                    r, g, b, _a = plain.getpixel((x * plain.width // inner_w, sy))
                    inner.putpixel((x, y), (r, g, b, DIVISION_CARD_ALPHA))
            rail = green_frame.crop((green_frame.width - 10, 3, green_frame.width - 10 + DIVISION_CARD_RAIL, green_frame.height - 3))
            for y in range(inner_h):
                inner.paste(rail.crop((0, y * rail.height // inner_h, DIVISION_CARD_RAIL, y * rail.height // inner_h + 1)), (0, y))
        else:
            # the hatch: diagonal lines that repeat every 30 columns, each row the one above moved one column
            # right, so a row below the vanilla 27 is row 3 moved by as many columns (pixel copies only)
            for y in range(inner_h):
                for x in range(inner_w):
                    r, g, b, _a = hatch_frame.getpixel((60 + (x - y) % 30, 3))
                    inner.putpixel((x, y), (r, g, b, DIVISION_CARD_ALPHA))
        card.alpha_composite(inner, (DIVISION_CARD_INSET, DIVISION_CARD_INSET))
        out.append(card)
    return join(out, "x")


# The deploy button of the HQ bar, 310x42 to 548x42 a frame: the label part (columns 0-104) and the end cap
# (296-309) kept, the plain dark template part right of the label spread with single-column copies.
DEPLOY_HQ_WIDTH = 548


def deploy_hq_button(frame):
    return grow(frame, "x", stretched(130, 280, DEPLOY_HQ_WIDTH - frame.width))
# --- end a2-division-list ---


# --- d2-readiness: an archetype picture for mechanized equipment, whose own picture is the motorized truck ---
ARCHETYPE_HEIGHT = 28       # as high as the truck and the tanks of the game's archetype pictures


def _brightness(pixel):
    return 0.299 * pixel[0] + 0.587 * pixel[1] + 0.114 * pixel[2]


def archetype_picture(source, **archetypes):
    """A technology picture in the look of the archetype pictures. The shape is the picture's: its largest
    piece (the level mark beside it is dropped), cropped and scaled to ARCHETYPE_HEIGHT. The colours are the
    archetypes': their opaque pixels are ranked by brightness, and each pixel of the shape takes the colour of
    the same rank, its brightness ranked with a slight fall from the top left as the archetypes are lit."""
    w, h = source.size
    px = source.load()
    solid = lambda x, y: px[x, y][3] >= 24     # noqa: E731
    seen, pieces = set(), []
    for y in range(h):
        for x in range(w):
            if (x, y) in seen or not solid(x, y):
                continue
            stack, piece = [(x, y)], []
            seen.add((x, y))
            while stack:
                cx, cy = stack.pop()
                piece.append((cx, cy))
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in seen and solid(nx, ny):
                        seen.add((nx, ny))
                        stack.append((nx, ny))
            pieces.append(piece)
    largest = max(len(piece) for piece in pieces)
    keep = set(p for piece in pieces if len(piece) >= largest * 0.05 for p in piece)
    shape = Image.new("RGBA", (w, h))
    sp = shape.load()
    for y in range(h):
        for x in range(w):
            near = any((x + dx, y + dy) in keep for dx in (-1, 0, 1) for dy in (-1, 0, 1))
            if (x, y) in keep or (near and px[x, y][3] < 24):
                sp[x, y] = px[x, y]
    shape = shape.crop(shape.getbbox())
    width = round(shape.width * ARCHETYPE_HEIGHT / shape.height)
    small = shape.convert("RGBa").resize((width, ARCHETYPE_HEIGHT), Image.LANCZOS).convert("RGBA")
    colours = sorted((p for image in archetypes.values() for p in image.getdata() if p[3] == 255), key=_brightness)
    mp = small.load()
    rank = sorted((0.75 * _brightness(mp[x, y]) / 255.0 + 0.25 * (1.0 - 0.8 * y / ARCHETYPE_HEIGHT - 0.2 * x / width), x, y)
                  for y in range(ARCHETYPE_HEIGHT) for x in range(width) if mp[x, y][3] > 0)
    out = Image.new("RGBA", (width, ARCHETYPE_HEIGHT))
    op = out.load()
    for n, (_key, x, y) in enumerate(rank):
        op[x, y] = colours[n * (len(colours) - 1) // max(1, len(rank) - 1)][:3] + (mp[x, y][3],)
    return out
# --- end d2-readiness ---

# --- A10 ---
def ar_sky(source):
    """The sky of the mission card of the air region window (A10): columns 14-538 and rows 152-430 of
    strategic_air_bg.dds, so that the combat widgets keep their vanilla places over it."""
    return source.crop((14, 152, 538, 430))


def ar_channel_cell(width):
    """The cell of a channel button, two frames of `width` x 24 (the code sets frame 2 on a ticked channel):
    frame 1 transparent, frame 2 the pick band of the house (tiles/tiled_bg_noframe.dds, border 12)."""
    def compose(source):
        out = Image.new("RGBA", (width * 2, 24), (0, 0, 0, 0))
        out.paste(tile_nine(source, (12, 12), width, 24), (width, 0))
        return out
    return compose
# --- end A10 ---


# One entry per output texture. `frames` lists one widening call per frame of the source, left to right;
# `compose` is a function that builds the whole output from the source instead.
JOBS = [
    {
        # Air wing, gun emplacement and rocket rows: frame 1 striped (unselected), frame 2 red (selected).
        # Edge bars sit at columns 52-105 and 405-473, the border and bars in rows 0-5 and 41-47,
        # the corner rivets within 10 columns of each end.
        "source": "gfx/interface/airview/wing_entry_bg.dds",
        "output": "av_wing_entry_bg.dds",
        "frames": [
            lambda f: widen_periodic(f, 784, period=73, split=390, top=6, bottom=41, right_cap=10),
            lambda f: widen_periodic(f, 784, period=62, split=390, top=6, bottom=41, right_cap=10),
        ],
    },
    # --- a2-division-list: the division card (replaces the widened vanilla row uv_unit_entry_bg.dds) and the
    # deploy button of the HQ bar ---
    {
        "source": "gfx/interface/unitcontrol/unit_entry_bg.dds",
        "output": "uv_division_card.dds",
        "extra": {"tile": "gfx/interface/tiles/tiled_plain_bg_small.dds"},
        "compose": lambda source, tile: division_card(source, tile),
    },
    {
        "source": "gfx/interface/deploy_army_hq_button.dds",
        "output": "uv_deploy_hq_button.dds",
        "frames": [
            lambda f: deploy_hq_button(f),
            lambda f: deploy_hq_button(f),
        ],
    },
    # --- end a2-division-list ---
    {
        # Footer plate of the unassigned divisions list: a dark plate with an irregular texture
        # and a soft border, plain between columns 100 and 273.
        "source": "gfx/interface/unitlist_unassigned_bg.dds",
        "output": "uv_unitlist_unassigned_bg.dds",
        "frames": [
            lambda f: widen_mirror(f, 644, split=273),
        ],
    },
    {
        # Army badge, 437 to 685 wide.
        "source": "gfx/interface/unitcontrol/army_group_bg.dds",
        "output": "uv_army_bg.dds",
        "frames": [
            lambda f: widen_mirror_multi(f, BADGE_INSERTS),
        ],
    },
    {
        # Army group badge, 436 to 684 wide.
        "source": "gfx/interface/unitcontrol/army_group_group_bg.dds",
        "output": "uv_army_group_bg.dds",
        "frames": [
            lambda f: widen_mirror_multi(f, BADGE_INSERTS),
        ],
    },
    {
        # Division details (a3-unit-details redesign): the dark plain tile at the window's size.
        "source": "gfx/interface/tiles/tiled_plain_bg.dds",
        "output": "ud_division_bg.dds",
        "compose": tiled_window(*UD_DIVISION_SIZE),
    },
    {
        # Ship details (a3-unit-details redesign): the same tile at the main panel's size.
        "source": "gfx/interface/tiles/tiled_plain_bg.dds",
        "output": "ud_ship_bg.dds",
        "compose": tiled_window(*UD_SHIP_SIZE),
    },
    {
        # Frame of the hard and soft attack bar, 207 to 363 wide: plain lines between its ends.
        "source": "gfx/interface/softness_ratio_frame.dds",
        "output": "ud_softness_frame.dds",
        "compose": lambda source: grow(source, "x", [(100, 2 * STAT_COLUMN)]),
    },
    {
        # Name field of the identity card (a3-unit-details redesign): the vanilla division window's name
        # field (columns 109-379, rows 36-66), 271 to 506 wide.
        "source": "gfx/interface/unit_stats_bg.dds",
        "output": "ud_name_field.dds",
        "compose": lambda source: grow(source.crop((109, 36, 380, 67)), "x", stretched(40, 230, 235)),
    },
    {
        # Experience field of the identity card: the vanilla one (columns 382-525), 144 to 118 wide.
        "source": "gfx/interface/unit_stats_bg.dds",
        "output": "ud_experience_field.dds",
        "compose": lambda source: cut(source.crop((382, 36, 526, 67)), "x", [(40 + 2 * i, 1) for i in range(26)]),
    },
    {
        # Picture band of the ship and railway gun windows (a3-unit-details redesign): the blue band of the
        # first build's ship bitmap, cut out as a plate.
        "source": "gfx/interface/naval_unit_stats_bg.dds",
        "output": "ud_class_band.dds",
        "compose": band_of(small_details((272, stretched(120, 400, 2 * STAT_COLUMN) + stretched(420, 530, STAT_COLUMN)),
                                         stretched(370, 540, MAIN_GROWTH)), UD_SHIP_BAND),
    },
    {
        # Picture band of the air wing window, the same way.
        "source": "gfx/interface/air_unit_stats_bg.dds",
        "output": "ud_air_band.dds",
        "compose": band_of(small_details((278, stretched(20, 530, MAIN_GROWTH)), stretched(370, 530, MAIN_GROWTH)),
                           UD_AIR_BAND),
    },
    {
        # Row of an air wing on a carrier and of a plane type in a wing, 268 to 358 wide: a plain
        # dark box with rounded corners.
        "source": "gfx/interface/air_unit_stats_equip_entry.dds",
        "output": "ud_wing_entry_bg.dds",
        "compose": lambda source: grow(source, "x", [(134, SIDE_GROWTH)]),
    },
    {
        "source": "gfx/interface/unit_stats_template_tab_bg.dds",
        "output": "ud_template_bg.dds",
        "compose": template_board,
    },
    {
        "source": "gfx/interface/army_hq_unit_details_bg.dds",
        "output": "ud_template_hq_bg.dds",
        "compose": hq_board,
    },
    {
        # A4, fleet card.
        "source": "gfx/interface/naviesview/fleet_bg.dds",
        "output": "fl_fleet_bg.dds",
        "compose": fleet_card,
    },
    {
        # Gold outline of a selected fleet card, 497 to 745 wide: plain lines between its corners.
        "source": "gfx/interface/naviesview/fleet_bg_hl.dds",
        "output": "fl_fleet_bg_hl.dds",
        "compose": lambda source: grow(source, "x", [(250, FLEET_GROWTH)]),
    },
    {
        "source": "gfx/interface/naviesview/task_force_bg.dds",
        "output": "fl_task_force_bg.dds",
        "compose": task_force_card,
    },
    {
        "source": "gfx/interface/naviesview/task_force_bg_hl.dds",
        "output": "fl_task_force_bg_hl.dds",
        "compose": lambda source: cut(grow(source, "x", [(250, FLEET_GROWTH)]), "y", [(45, TASK_FORCE_TRAY[1])]),
    },
    {
        # Toolbar plate between the fleet card and the task forces: scratched metal with a rivet
        # in each corner.
        "source": "gfx/interface/naviesview/task_force_actions_bg.dds",
        "output": "fl_task_force_actions_bg.dds",
        "compose": lambda source: grow(source, "x", stretched(20, 470, FLEET_GROWTH)),
    },
    {
        # Ship rows: frame 1 unselected, frame 2 selected (lighter, with a chevron at the right end).
        "source": "gfx/interface/naval_unit_ship_entry.dds",
        "output": "fl_ship_entry.dds",
        "frames": [ship_row(12), ship_row(34)],
    },
    {
        # Gold outline of a selected ship row, 490x43 to 738x37: plain lines and a thick right end.
        "source": "gfx/interface/naviesview/naval_unit_ship_entry_highlight.dds",
        "output": "fl_ship_entry_highlight.dds",
        "compose": lambda source: cut(grow(source, "x", [(245, FLEET_GROWTH)]), "y", [(12, 2), (20, 2), (28, 2)]),
    },
    {
        # Home base button of the fleet card, 124 to 184 wide: an anchor badge and a name bar that
        # is plain between columns 45 and 115.
        "source": "gfx/interface/naval_deploy_button.dds",
        "output": "fl_home_base_button.dds",
        "compose": lambda source: grow(source, "x", stretched(45, 115, 60)),
    },
    {
        # A4 step 2. Row of the composition editor, 493 to 573 wide: a plate for the remove button
        # (columns 0-40), then a plain bar.
        "source": "gfx/interface/task_force_comp_unit_bg.dds",
        "output": "fl_comp_entry.dds",
        "compose": lambda source: grow(source, "x", stretched(60, 470, POPUP_GROWTH)),
    },
    {
        # The "+" row under them: a plain bar.
        "source": "gfx/interface/task_force_comp_add_bg.dds",
        "output": "fl_comp_add.dds",
        "compose": lambda source: grow(source, "x", stretched(30, 470, POPUP_GROWTH)),
    },
    {
        # Header and menu bar of the composition editor, 505 to 585 wide: scratched metal, rivets
        # in the corners.
        "source": "gfx/interface/frontend_task_force_composition_editor_upper_bar.dds",
        "output": "fl_comp_editor_bar.dds",
        "compose": lambda source: grow(source, "x", stretched(30, 475, POPUP_GROWTH)),
    },
    {
        # Row of the home base picker, 335 to 415 wide: an icon plate (columns 0-33), then a
        # meshed name bar.
        "source": "gfx/interface/deploy_port_fleet_bg.dds",
        "output": "fl_home_base_entry.dds",
        "compose": lambda source: grow(source, "x", stretched(60, 320, POPUP_GROWTH)),
    },
    {
        # Header of the transfer window, 516 to 676 wide.
        "source": "gfx/interface/tradeview/trade_header.dds",
        "output": "fl_transfer_header.dds",
        "compose": lambda source: grow(source, "x", stretched(30, 490, TRANSFER_GROWTH)),
    },
    {
        # Ship rows of the transfer window, 653x41.
        "source": "gfx/interface/naval_unit_ship_entry.dds",
        "output": "fl_transfer_ship_entry.dds",
        "frames": [ship_row(12, TRANSFER_GROWTH), ship_row(34, TRANSFER_GROWTH)],
    },
    {
        # A5 redesign. The card of a template in training: one frame in four slices (card_slice), the
        # head (575x84 with the 6 px gap on top), the band of the summary row (575x32), a division in
        # training (575x40) and the foot (575x9).
        "source": "gfx/interface/tiles/tiled_window2_1b_border.dds",
        "output": "rd_conveyor_bg.dds",
        "compose": card_slice(CARD_HEAD_ROWS, gap=CARD_GAP),
    },
    {
        "source": "gfx/interface/tiles/tiled_window2_1b_border.dds",
        "output": "rd_summary_bg.dds",
        "compose": card_slice(CARD_BAND_ROWS),
    },
    {
        "source": "gfx/interface/tiles/tiled_window2_1b_border.dds",
        "output": "rd_line_bg.dds",
        "compose": card_slice(CARD_LINE_ROWS),
    },
    {
        "source": "gfx/interface/tiles/tiled_window2_1b_border.dds",
        "output": "rd_end_line.dds",
        "compose": card_slice(CARD_FOOT_ROWS),
    },
    {
        # Location button of a card, 223 to 283 wide: frame 1 plain, frame 2 with chevrons every
        # 15 columns.
        "source": "gfx/interface/conveyor_location_btn.dds",
        "output": "rd_location_btn.dds",
        "frames": [
            lambda f: grow(f, "x", stretched(45, 200, LOCATION_GROWTH)),
            lambda f: grow(f, "x", [(170, LOCATION_GROWTH, 15)]),
        ],
    },
    {
        # Header of the Recruit & Deploy panel, 543 to 633 wide: scratched metal up to the box of
        # the close button at column 491.
        "source": "gfx/interface/header_bg.dds",
        "output": "rd_header_bg.dds",
        "compose": lambda source: grow(source, "x", stretched(120, 480, DEPLOY_GROWTH)),
    },
    {
        # Strip under that header, 533 to 623 wide.
        "source": "gfx/interface/deployment_binding.dds",
        "output": "rd_binding.dds",
        "compose": lambda source: grow(source, "x", stretched(40, 490, DEPLOY_GROWTH)),
    },
    {
        # Header of the Division Templates panel, 375 to 618 wide: plain between columns 70 and 365.
        "source": "gfx/interface/subview_header_bg_375x101.dds",
        "output": "rd_templates_header.dds",
        "compose": lambda source: grow(source, "x", stretched(75, 360, TEMPLATE_PANEL_GROWTH)),
    },
    {
        # Row of a template: the mesh of the name box is rows 12-49, the strip under it 53-65.
        "source": "gfx/interface/deployment_named_division_bg.dds",
        "output": "rd_template_entry.dds",
        "compose": template_row(mesh_rows=(12, 50), strip_rows=(53, 66), mesh_period=4),
    },
    {
        # Its brown twin for a decommissioned template: mesh rows 13-48, strip 52-64.
        "source": "gfx/interface/deployment_named_division_obsolete_bg.dds",
        "output": "rd_template_entry_obsolete.dds",
        "compose": template_row(mesh_rows=(13, 49), strip_rows=(52, 65), mesh_period=12),
    },
    {
        # A5 redesign: the plates of a template row with the symbol's tile (template_plate).
        "source": "gfx/interface/tiles/tiled_plain_bg_small.dds",
        "output": "rd_template_plate.dds",
        "compose": template_plate(16, "gfx/interface/deploy_priority_icon_bg.dds", None, 16),
        "game_dir": True,
    },
    {
        "source": "gfx/interface/deployment_item_bg.dds",
        "output": "rd_template_plate_obsolete.dds",
        "compose": template_plate((18, 16), "gfx/interface/deployment_named_division_obsolete_bg.dds", (7, 7, 86, 68), 14),
        "game_dir": True,
    },
    {
        # A6. Rows of the army overview: a division, a fleet, an air wing.
        "source": "gfx/interface/armyoverview_entry_bg.dds",
        "output": "ao_army_entry.dds",
        "compose": overview_army_row,
    },
    {
        "source": "gfx/interface/armyoverview_naval_entry_bg.dds",
        "output": "ao_navy_entry.dds",
        "compose": overview_navy_row,
    },
    {
        "source": "gfx/interface/armyoverview_air_entry_bg.dds",
        "output": "ao_air_entry.dds",
        "compose": overview_air_row,
    },
    {
        # Title bar, 543 to 893 wide: scratched metal up to the box of the close button at column 491.
        "source": "gfx/interface/header_bg.dds",
        "output": "ao_header_bg.dds",
        "compose": lambda source: grow(source, "x", stretched(120, 480, OVERVIEW_GROWTH)),
    },
    {
        # Picture strip under the title, three frames (army, navy, air) of 522 to 872: a painting that
        # fades into a dark plate, plain from column 300 to the rim.
        "source": "gfx/interface/overview_top_strip.dds",
        "output": "ao_top_strip.dds",
        "frames": [lambda f: grow(f, "x", stretched(320, 505, OVERVIEW_GROWTH))] * 3,
    },
    {
        # Box of the filter, 190 to 320 wide: a dark field with rounded ends.
        "source": "gfx/interface/edittextbox_bg1.dds",
        "output": "ao_filter_bg.dds",
        "compose": lambda source: grow(source, "x", stretched(20, 170, 130)),
    },
    {
        # Plate under the list ("Active in 1 Theater(s)"), 516 to 866 wide.
        "source": "gfx/interface/tradeview/trade_header.dds",
        "output": "ao_bottom.dds",
        "compose": lambda source: grow(source, "x", stretched(30, 490, OVERVIEW_GROWTH)),
    },
    {
        # A8. The card of a theatre box: five frames (army, grey, navy, reserve fleets, air).
        "source": "gfx/interface/theater/theater_group_bg.dds",
        "extra": {"tile": "gfx/interface/tiles/tiled_plain_bg_small.dds",
                  "header": "gfx/interface/unitcontrol/unit_list_header.dds"},
        "output": "ts_card.dds",
        "compose": theatre_card,
    },
    {
        # The units band of a card: four frames (army, assign mode, navy, air).
        "source": "gfx/interface/theater/assign_group_button.dds",
        "output": "ts_band.dds",
        "frames": [theatre_band] * 4,
    },
    {
        # The rows under a box: the middle rows (GFX_1440p_TS_drawer_middle) and the last row, declared
        # again under its vanilla name GFX_theatre_dropdown_bottom in interface/zz_1440p_vanilla_sprites.gfx.
        # Four frames each (grey, green, blue, red).
        "source": "gfx/interface/theater/theatre_dropdown_middle.dds",
        "extra": {"tile": "gfx/interface/tiles/tiled_plain_bg_small.dds"},
        "output": "ts_drawer_middle.dds",
        "compose": lambda source, tile: theatre_drawer(source, tile, bottom=False),
    },
    {
        "source": "gfx/interface/theater/theatre_dropdown_middle.dds",
        "extra": {"tile": "gfx/interface/tiles/tiled_plain_bg_small.dds"},
        "output": "ts_drawer_bottom.dds",
        "compose": lambda source, tile: theatre_drawer(source, tile, bottom=True),
    },
    {
        # A strategic region under a box, 198x39 to 318x39, three frames: plain between 30 and 165.
        # Kept as the fallback of the region row's tile plate (GFX_1440p_TS_region_plate), should the
        # tile not show the button states (wiki/phases/A8-theatre-bar.md).
        "source": "gfx/interface/theatre_selection_background.dds",
        "output": "ts_region_bg.dds",
        "frames": [lambda f: grow(f, "x", stretched(40, 160, 120))] * 3,
    },
    {
        # A7. The plane card of the air wing reorganisation window, 458x80 to 572x86, two frames: olive
        # bands, plain from column 60 to the dark column at 365; the clasps of the top and bottom edges
        # sit at 212-245, so the columns go in after them, and the dark block moves to 479-569. The
        # plain middle band (rows 30-50) takes the 6 rows.
        "source": "gfx/interface/equipment_item_large_02.dds",
        "output": "aw_card.dds",
        "frames": [lambda f: grow(grow(f, "x", stretched(260, 355, 114)), "y", stretched(30, 50, 6))] * 2,
    },
    {
        # Plate of one modifier, 74 to 100 wide: a tile of the Modifiers card in the overview's rail.
        "source": "gfx/interface/modifiers/MODIFIER_bg.dds",
        "output": "ao_modifier_bg.dds",
        "compose": lambda source: grow(source, "x", stretched(14, 56, 26)),
    },
    {
        # A count by type of the overview (the type filter), 90 to 100 wide, and its highlight: a
        # chip of the rail's second card. Plain between the rounded ends.
        "source": "gfx/interface/overview_filter_entry.dds",
        "output": "ao_filter_entry.dds",
        "compose": lambda source: grow(source, "x", stretched(20, 70, 10)),
    },
    {
        "source": "gfx/interface/overview_filter_entry_highlight.dds",
        "output": "ao_filter_entry_highlight.dds",
        "compose": lambda source: grow(source, "x", stretched(20, 70, 10)),
    },
    # C1. Production, round 2 (bold variant): every card is cut from the steel bar (see "C1" above), the
    # equipment plates and overlays keep round 1's art. production_item and the naval strip keep their
    # vanilla sprite names (the code sets them), the others get GFX_1440p_ names.
    {
        # a transparent 4x4: the Background block of a window whose cards are icons of their own (the vanilla
        # backgrounds stay in the file, the widget names being the code's)
        "source": STEEL_BAR,
        "output": "pd_none.dds",
        "compose": lambda source: Image.new("RGBA", (4, 4), (0, 0, 0, 0)),
    },
    {
        "source": STEEL_BAR,
        "output": "pd_title.dds",
        "compose": title_strip,
    },
    {
        "source": STEEL_BAR,
        "output": "pd_top_materials.dds",
        "compose": top_materials,
    },
    {
        "source": STEEL_BAR,
        "output": "pd_top_figures.dds",
        "extra": {"inset_tile": CARD_INSET},
        "compose": top_figures,
    },
    {
        "source": "gfx/interface/production_win_top.dds",
        "output": "pd_top_filters.dds",
        "extra": {"bar": STEEL_BAR},
        "compose": lambda source, bar: top_filters(bar, source),
    },
    {
        # the land line, GFX_production_item: three rows of slot boxes
        "source": STEEL_BAR,
        "output": "pd_line.dds",
        "extra": {"inset_tile": CARD_INSET, "strip": NAVAL_STRIP},
        "compose": lambda source, inset_tile, strip: line_card(source, inset_tile, slot_box(strip), slot_rows=3),
    },
    {
        # GFX_naval_production_item_bg_strip, three frames: one, two and three rows of slot boxes
        "source": STEEL_BAR,
        "output": "pd_naval_line.dds",
        "extra": {"inset_tile": CARD_INSET, "strip": NAVAL_STRIP},
        "compose": lambda source, inset_tile, strip: join([line_card(source, inset_tile, slot_box(strip), slot_rows=n) for n in (1, 2, 3)], "x"),
    },
    {
        "source": STEEL_BAR,
        "output": "pd_line_collapsed.dds",
        "extra": {"inset_tile": CARD_INSET, "strip": NAVAL_STRIP},
        "compose": lambda source, inset_tile, strip: line_card(source, inset_tile, slot_box(strip), collapsed=True),
    },
    {
        "source": STEEL_BAR,
        "output": "pd_goods_line.dds",
        "compose": goods_card,
    },
    {
        "source": STEEL_BAR,
        "output": "pd_line_selected.dds",
        "compose": selection_outline,
    },
    {
        "source": STEEL_BAR,
        "output": "pd_line_selected_collapsed.dds",
        "compose": lambda source: selection_outline(source, collapsed=True),
    },
    {
        # The marker of a line that a military-industrial organisation produces: a tint over the head band only.
        "source": STEEL_BAR,
        "output": "pd_line_has_mio.dds",
        "compose": mio_tint,
    },
    {
        "source": "gfx/interface/prod_land_equipment_item_large.dds",
        "output": "pd_land_item_large.dds",
        "frames": [lambda f: production_columns(f, gap=False)],
    },
    {
        "source": "gfx/interface/prod_naval_equipment_item_large.dds",
        "output": "pd_naval_item_large.dds",
        "frames": [lambda f: production_columns(f, gap=False)],
    },
    {
        "source": "gfx/interface/equipment_item_collapsed.dds",
        "output": "pd_item_collapsed.dds",
        "frames": [lambda f: production_columns(f, gap=False)],
    },
    {
        "source": "gfx/interface/naval_item_collapsed.dds",
        "output": "pd_naval_item_collapsed.dds",
        "compose": naval_strip_301,
    },
    {
        "source": "gfx/interface/outdated_equipment_overlay.dds",
        "output": "pd_outdated_overlay.dds",
        "frames": [lambda f: production_columns(f, gap=False)],
    },
    {
        "source": "gfx/interface/outdated_naval_equipment_overlay.dds",
        "output": "pd_outdated_naval_overlay.dds",
        "frames": [lambda f: production_columns(f, gap=False)],
    },
    {
        "source": "gfx/interface/outdated_equipment_overlay_collapsed.dds",
        "output": "pd_outdated_overlay_collapsed.dds",
        "frames": [lambda f: production_columns(f, gap=False)],
    },
    {
        "source": "gfx/interface/outdated_naval_overlay_collapsed.dds",
        "output": "pd_outdated_naval_overlay_collapsed.dds",
        "frames": [lambda f: production_columns(f, gap=False)],
    },
    {
        # The deploy location button of a ship line, 124 to 266 wide: a round badge (0-36), a plain bar.
        "source": "gfx/interface/naval_deploy_button.dds",
        "output": "pd_deploy_button.dds",
        "compose": lambda source: grow(source, "x", stretched(50, 110, 142)),
    },
    {
        # the same in a collapsed ship line, 194 wide
        "source": "gfx/interface/naval_deploy_button.dds",
        "output": "pd_deploy_button_short.dds",
        "compose": lambda source: grow(source, "x", stretched(50, 110, 70)),
    },
    # C2. General selection: the window and a general's row.
    {
        "source": "gfx/interface/leader_selection_bg.dds",
        "output": "ls_window_bg.dds",
        "compose": leader_window,
    },
    {
        "source": "gfx/interface/leader_selection_entry_bg.dds",
        "output": "ls_entry_bg.dds",
        "compose": leader_row,
    },
    # --- c2-state-rows: the row backgrounds the code puts on a general's row by vanilla name ---
    {
        "source": "gfx/interface/leader_selection_unavailable_entry_bg.dds",
        "output": "ls_entry_unavailable_bg.dds",
        "extra": {"plain": "gfx/interface/leader_selection_unavailable_entry_bg.dds"},
        "compose": lambda source, plain: leader_row_state(source, plain),
    },
    {
        "source": "gfx/interface/marshal_selection_entry_bg.dds",
        "output": "ls_entry_marshal_bg.dds",
        "extra": {"plain": "gfx/interface/leader_selection_entry_bg.dds"},
        "compose": lambda source, plain: leader_row_state(source, plain),
    },
    {
        "source": "gfx/interface/factions/ui/leader_selection_entry_bg_faction.dds",
        "output": "ls_entry_faction_bg.dds",
        "extra": {"plain": "gfx/interface/leader_selection_entry_bg.dds"},
        "compose": lambda source, plain: leader_row_state(source, plain),
    },
    {
        "source": "gfx/interface/leader_selection_active_entry_bg.dds",
        "output": "ls_entry_active_bg.dds",
        "compose": leader_row_striped,
    },
    {
        "source": "gfx/interface/leader_selection_unavailable_active_entry_bg.dds",
        "output": "ls_entry_unavailable_active_bg.dds",
        "compose": leader_row_striped,
    },
    {
        "source": "gfx/interface/marshal_selection_active_entry_bg.dds",
        "output": "ls_entry_marshal_active_bg.dds",
        "compose": leader_row_striped,
    },
    {
        "source": "gfx/interface/factions/ui/leader_selection_active_entry_bg_faction.dds",
        "output": "ls_entry_active_faction_bg.dds",
        "compose": leader_row_striped,
    },
    # --- end c2-state-rows ---
    # A5, step 2. The priority rows of Recruit & Deploy (the lend-lease row uses the garrisons texture),
    # their label plate and their equipment meter.
    {
        "source": "gfx/interface/deploy_reinforcements_entry.dds",
        "output": "rd_reinforcements_entry.dds",
        "compose": priority_row,
    },
    {
        "source": "gfx/interface/deploy_upgrades_entry.dds",
        "output": "rd_upgrades_entry.dds",
        "compose": priority_row,
    },
    {
        "source": "gfx/interface/deploy_supply_entry.dds",
        "output": "rd_supply_entry.dds",
        "compose": priority_row,
    },
    {
        "source": "gfx/interface/deploy_operations_entry.dds",
        "output": "rd_operations_entry.dds",
        "compose": priority_row,
    },
    {
        "source": "gfx/interface/deploy_garrisons_entry.dds",
        "output": "rd_garrisons_entry.dds",
        "compose": priority_row,
    },
    {
        "source": "gfx/interface/deploy_priority_title_bg.dds",
        "output": "rd_priority_title_bg.dds",
        "compose": lambda source: grow(source, "x", [(80, PRIORITY_TITLE_GROWTH)]),
    },
    {
        "source": "gfx/interface/deploy_priority_equipment_meter_bg.dds",
        "output": "rd_priority_meter_bg.dds",
        "compose": lambda source: grow(source, "x", [(80, PRIORITY_METER_GROWTH)]),
    },
    # --- e-diary-wars ---
    {
        # E4: the file of a war, 1092x1090 (GFX_1440p_SG_war_file).
        "source": "gfx/interface/waroverview_bg_tiled.dds",
        "output": "wr_file_bg.dds",
        "compose": war_file,
    },
    # Fix round 1: a tiled sprite draws its whole texture and takes no frame, so the two frames of the intel
    # ledger's tab and of the sort button are cut apart, one texture each (tabs of the Records window, the page
    # arrows of the War Diary).
    {"source": "gfx/interface/intel_ledger/tab_small.dds", "output": "rec_tab_off.dds", "compose": lambda source: frame_of(source, 2, 0)},
    {"source": "gfx/interface/intel_ledger/tab_small.dds", "output": "rec_tab_on.dds", "compose": lambda source: frame_of(source, 2, 1)},
    {"source": "gfx/interface/sort_button_140x29.dds", "output": "rec_sort_off.dds", "compose": lambda source: frame_of(source, 2, 0)},
    # --- end e-diary-wars ---
    # --- d2-readiness ---
    {
        # The picture of mechanized equipment on Army Readiness (GFX_1440p_archetype_mechanized_equipment_medium):
        # the halftrack of the technology in the colours of the archetype pictures beside it.
        "source": "gfx/interface/technologies/mechanized_equipment_1.dds",
        "output": "ar_mechanized_equipment.dds",
        "extra": {"truck": "gfx/interface/archetypes/archetype_motorized_equipment.dds",
                  "car": "gfx/interface/archetypes/archetype_armored_car_equipment.dds",
                  "tank": "gfx/interface/archetypes/archetype_medium_tank_equipment.dds"},
        "compose": archetype_picture,
    },
    # --- end d2-readiness ---
    # --- A10 ---
    {
        "source": "gfx/interface/strategicair/strategic_air_bg.dds",
        "output": "ar_sky.dds",
        "compose": ar_sky,
    },
    {
        "source": "gfx/interface/tiles/tiled_bg_noframe.dds",
        "output": "ar_channel_cell.dds",
        "compose": ar_channel_cell(222),
    },
    {
        # the cell of the fallback that keeps the game's whole channel texts (option A of the design)
        "source": "gfx/interface/tiles/tiled_bg_noframe.dds",
        "output": "ar_channel_cell_400.dds",
        "compose": ar_channel_cell(400),
    },
    # --- end A10 ---
]


from guiparse import find_game_dir  # noqa: E402  (shared with render_gui.py)


def build(job, game_dir):
    def load(rel):
        return Image.open(os.path.join(game_dir, *rel.split("/"))).convert("RGBA")

    source = load(job["source"])
    if "compose" in job:
        # `extra` names further vanilla textures a composed output is built from, passed by keyword;
        # `game_dir` asks for the game folder as the second argument
        extra = {key: load(rel) for key, rel in (job.get("extra") or {}).items()}
        out = job["compose"](source, game_dir, **extra) if job.get("game_dir") else job["compose"](source, **extra)
        return source, [out], out
    count = len(job["frames"])
    frame_width = source.width // count
    frames = [
        widen(source.crop((i * frame_width, 0, (i + 1) * frame_width, source.height)))
        for i, widen in enumerate(job["frames"])
    ]
    return source, frames, join(frames, "x")


def write_preview(job, source, frames, preview_dir):
    """Vanilla frames above the widened ones, on a mid-grey ground, at 2x for inspection."""
    count = 1 if "compose" in job else len(frames)
    frame_width = source.width // count
    rows = [source.crop((i * frame_width, 0, (i + 1) * frame_width, source.height)) for i in range(count)] + frames
    gap = 6
    sheet = Image.new("RGBA", (max(r.width for r in rows) + 2 * gap, sum(r.height + gap for r in rows) + gap), (90, 96, 104, 255))
    y = gap
    for row in rows:
        sheet.alpha_composite(row, (gap, y))
        y += row.height + gap
    if "compose" not in job:   # rows are small, so they are enlarged; a composed window is read at 1:1
        sheet = sheet.resize((sheet.width * 2, sheet.height * 2), Image.NEAREST)
    path = os.path.join(preview_dir, os.path.splitext(job["output"])[0] + "_preview.png")
    sheet.convert("RGB").save(path)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--game-dir", help="Hearts of Iron IV install folder (default: HOI4_GAME_DIR, then Steam)")
    parser.add_argument("--preview", metavar="DIR", help="also write before/after PNG previews to DIR")
    parser.add_argument("--only", metavar="NAME", help="build only the outputs whose file name contains NAME")
    args = parser.parse_args()

    game_dir = find_game_dir(args.game_dir)
    if not game_dir:
        sys.exit("Hearts of Iron IV install not found. Pass --game-dir or set HOI4_GAME_DIR.")

    os.makedirs(OUT_DIR, exist_ok=True)
    for job in JOBS:
        if args.only and args.only not in job["output"]:
            continue
        source, frames, out = build(job, game_dir)
        target = os.path.join(OUT_DIR, job["output"])
        out.save(target)
        print(f"{job['source']} {source.size} -> {os.path.relpath(target, REPO_ROOT)} {out.size}")
        if args.preview:
            os.makedirs(args.preview, exist_ok=True)
            print("   preview:", write_preview(job, source, frames, args.preview))


if __name__ == "__main__":
    main()
