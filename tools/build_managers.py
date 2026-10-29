"""Writes the scripted GUIs of HOI4 Manager Pages (the "managers" of Milestone D) from the tables in this file.
Split from the HOI4 1440p UI Mod on 2026-10-21; the names (mod1440_*, GFX_1440p_SG_*) stay.

    python -I tools/build_managers.py          write the files
    python -I tools/build_managers.py --check  exit 1 when a file on disk differs from what would be written

Everything it writes is generated: change this file, not its output. The game reads the output again while it
runs (wiki/Engine-Facts.md, X23), so a change here shows a few seconds after the script has run.

    interface/mod1440_<manager>.gui                         the containers
    common/scripted_guis/mod1440_<manager>.txt              what shows when, and what the buttons do
    common/scripted_effects/mod1440_effects.txt             the counting a click or a new day asks for
    common/on_actions/mod1440_on_actions.txt                the hooks that run the counting
    common/synchronized_dynamic_tokens/mod1440_tokens.txt   every name used after "@" (Engine Facts X24)
    localisation/<language>/mod1440_l_<language>.yml        the texts (UTF-8 with BOM), English under every language
    tools/scenes/<page>.json                                where each page stands, its recipe and sample values

The Records window of Milestone E (War Diary, Officers, Government, Wars) is written by tools/build_records.py,
which this file imports: interface/mod1440_records.gui, common/scripted_guis/mod1440_records.txt and
common/scripted_effects/mod1440_records.txt, and its hooks go into the one on_actions file.

Rules the output follows (wiki/Scripted-GUIs.md): a button changes the panel, moves the camera or writes a
record; own country only; names carry the prefix mod1440_; no loop in anything drawn every tick.
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# "python -I" leaves the script's folder off the path; the role-play pages live in a module beside this file
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_records  # noqa: E402
import layout  # noqa: E402

# The fonts by role and the grounds (wiki/Design-Language.md, tools/layout.py): the pages took the fonts of the
# steel look and keep the grounds of the card look until a phase moves them to steel.
FONT_TITLE, FONT_CARD, FONT_VALUE, FONT_LABEL, FONT_SMALL = (
    layout.FONTS[role]["steel"][0] for role in ("title", "name", "value", "caption", "button"))

PAGE_BG = layout.CARD_GROUND
CARD_BG = layout.CARD_PLATE

# the languages the game ships (the folders of its localisation directory)
LANGUAGES = ["english", "braz_por", "french", "german", "japanese", "korean", "polish", "russian", "simp_chinese", "spanish"]


# ---------------------------------------------------------------- output collectors

class Build:
    def __init__(self):
        self.loc = {}       # key -> text
        self.files = {}     # relative path -> content

    def key(self, name, value):
        """Registers a text of the mod and returns its localisation key."""
        key = "MOD1440_" + name.upper()
        if key in self.loc and self.loc[key] != value:
            raise ValueError("two texts for " + key)
        self.loc[key] = value
        return key


B = Build()


# ---------------------------------------------------------------- .gui pieces

def indent(text_block, tabs=1):
    return "".join(("\t" * tabs + line if line.strip() else line) for line in text_block.splitlines(True))


def text(name, x, y, width, key, font=FONT_LABEL, fmt="left", height=24, tooltip=None, fixed=False):
    """fixed: the box keeps its height, and a text that needs more lines is cut there instead of running into
    what stands below it (a name another mod makes longer)."""
    tip = ' pdx_tooltip = "%s"' % tooltip if tooltip else ""
    tip += " fixedsize = yes" if fixed else ""
    return ('instantTextboxType = { name = "%s" position = { x = %d y = %d } font = "%s" text = "%s" '
            'maxWidth = %d maxHeight = %d format = %s%s }\n' % (name, x, y, font, key, width, height, fmt, tip))


def icon(name, x, y, sprite):
    return 'iconType = { name = "%s" position = { x = %d y = %d } spriteType = "%s" }\n' % (name, x, y, sprite)


def button(name, x, y, sprite, key=None, font=FONT_SMALL, shortcut=None, tooltip=None):
    extra = ""
    if key:
        extra += ' buttonFont = "%s" buttonText = "%s"' % (font, key)
    if shortcut:
        extra += ' shortcut = "%s"' % shortcut
    if tooltip:
        extra += ' pdx_tooltip = "%s"' % tooltip
    return ('buttonType = { name = "%s" position = { x = %d y = %d } quadTextureSprite = "%s" '
            'clicksound = click_default%s }\n' % (name, x, y, sprite, extra))


def box(name, x, y, width, height, body, background=None):
    bg = '\tbackground = { name = "Background" quadTextureSprite = "%s" }\n' % background if background else ""
    return ('containerWindowType = {\n\tname = "%s"\n\tposition = { x = %d y = %d }\n'
            '\tsize = { width = %d height = %d }\n%s%s}\n' % (name, x, y, width, height, bg, indent(body)))


# ---------------------------------------------------------------- script pieces

def block(name, body):
    return "%s = {\n%s}\n" % (name, indent(body))


def scripted_gui(name, window, parent=None, visible="always = yes\n", effects="", triggers="", properties="",
                 lists="", dirty=None):
    body = 'context_type = player_context\nwindow_name = "%s"\n' % window
    if parent:
        body += "parent_window_token = %s\n" % parent
    body += "\n" + block("visible", visible)
    if dirty:
        body += "\ndirty = %s\n" % dirty
    for key, part in (("dynamic_lists", lists), ("properties", properties), ("effects", effects), ("triggers", triggers)):
        if part:
            body += "\n" + block(key, part)
    # the panel is for the player's eyes: the AI never looks at it
    body += "\n" + block("ai_enabled", "always = no\n")
    return block(name, body)


def more_than_zero(variable):
    return "check_variable = { %s > 0 }\n" % variable


def iff(limit, body, keyword="if"):
    return block(keyword, "limit = { %s }\n" % limit + body)


def els(body):
    return block("else", body)


def setv(variable, value):
    return "set_variable = { %s = %s }\n" % (variable, value)


def tmp(variable, value):
    return "set_temp_variable = { %s = %s }\n" % (variable, value)


def is_one(variable):
    return "check_variable = { %s = 1 }" % variable


def flip(variable):
    return iff(is_one(variable), setv(variable, 0)) + els(setv(variable, 1))


# ---------------------------------------------------------------- the look every page shares

# Dark cards on the page; a figure as a tile, a small label over a large value on a plate; every table under a
# bar of column heads, with a darker band on every second row and a lighter one on the chosen row; shares as
# bars. The sprites are tiles of vanilla textures at the sizes the pages use (interface/mod1440_ui.gfx).
TILE_W, TILE_H = 156, 64
STRIPE, PICK, head_sprite = layout.STRIPE, layout.PICK, layout.head_sprite
# The mark of the sorted column: the game's small arrow (22x28) at about half its size, on the upper right corner
# of the head. A head is 30 px high and its text starts 8 px down, so the arrow covers no letter of a narrow head.
ARROW, ARROW_DX, ARROW_DY = 0.55, 13, -9
BAR = {105: "GFX_1440p_SG_bar", 300: "GFX_1440p_SG_bar_wide"}     # other lengths: GFX_1440p_SG_bar_<length>


def tile_sprite(width=TILE_W, height=TILE_H):
    return "GFX_1440p_SG_tile" if (width, height) == (TILE_W, TILE_H) else "GFX_1440p_SG_tile_%dx%d" % (width, height)


def bar_sprite(length, low=False):
    """A lying bar that script fills, 0 to 100: green, or the orange of a strength bar for a low value."""
    if low:
        return "GFX_1440p_SG_bar_low_%d" % length
    return BAR.get(length, "GFX_1440p_SG_bar_%d" % length)


def plain(name, x, y, width, key, font=None, fmt="left", height=24):
    """A text that lets a click through to the button under it."""
    return ('instantTextboxType = { name = "%s" position = { x = %d y = %d } font = "%s" text = "%s" '
            'maxWidth = %d maxHeight = %d format = %s alwaystransparent = yes }\n'
            % (name, x, y, font or FONT_LABEL, key, width, height, fmt))


def scaled(name, x, y, sprite, scale, tooltip=None):
    tip = ' pdx_tooltip = "%s"' % tooltip if tooltip else ""
    return 'iconType = { name = "%s" position = { x = %d y = %d } spriteType = "%s" scale = %s%s }\n' % (name, x, y, sprite, scale, tip)


def listing(name, grid, x, y, width, height, row_height):
    """A list that scrolls: the rows are stacked by their own height (Engine Facts X10)."""
    inner = ('gridboxtype = {\n\tname = "%s"\n\tposition = { x = 0 y = 0 }\n\tsize = { width = %d height = 100%%%% }\n'
             '\tslotsize = { width = 1 height = 1 }\n\tadd_horizontal = no\n\tformat = "UPPER_LEFT"\n}\n' % (grid, width - 30))
    return ('containerWindowType = {\n\tname = "%s"\n\tposition = { x = %d y = %d }\n\tsize = { width = %d height = %d }\n'
            '\tverticalScrollbar = "right_vertical_slider"\n\tscroll_wheel_factor = %d\n\tsmooth_scrolling = yes\n'
            '\tbackground = { name = "Background" quadTextureSprite = "%s" }\n%s}\n'
            % (name, x, y, width, height, row_height * 3, CARD_BG, indent(inner)))


def row(name, width, height, body):
    return 'containerWindowType = {\n\tname = "%s"\n\tsize = { width = %d height = %d }\n%s}\n' % (name, width, height, indent(body))


def heads(name, x, y, width, labels):
    """A bar of column heads over a table: (x, width, text, format, tooltip or None) each."""
    inner = ""
    for n, (lx, lw, label, fmt, tip) in enumerate(labels):
        inner += text("%s_%d" % (name, n), lx, 5, lw, B.key("%s_%d" % (name, n), label), FONT_SMALL, fmt, 20,
                      tooltip=B.key("%s_%d_tt" % (name, n), tip) if tip else None)
    return box(name, x, y, width, 30, inner, head_sprite(240))


def tile(name, x, y, label, value, tip=None, when=None, width=TILE_W, zero=None):
    """A figure: a plate with a small label over a large value. Returns the widgets and their triggers.
    when: a trigger for the whole tile. zero: a variable; the value then shows only above zero and a plain 0
    otherwise (some values read "0.0" at zero, and a colour is for a number that says something)."""
    tooltip = B.key(name + "_tt", tip) if tip else None
    out = icon(name + "_bg", x, y, tile_sprite(width))
    out += text(name + "_l", x + 6, y + 7, width - 12, B.key(name + "_l", label), FONT_SMALL, "centre", 20, tooltip=tooltip)
    out += text(name, x + 6, y + 30, width - 12, B.key(name, value), FONT_VALUE, "centre", 26, tooltip=tooltip)
    triggers = "".join(block(part + "_visible", when) for part in (name + "_bg", name + "_l", name)) if when else ""
    if zero:
        out += text(name + "_z", x + 6, y + 30, width - 12, "0", FONT_VALUE, "centre", 26, tooltip=tooltip)
        triggers += block(name + "_visible", more_than_zero(zero))
        triggers += block(name + "_z_visible", "NOT = { %s }\n" % more_than_zero(zero).strip())
    return out, triggers


def card(name, x, y, width, height, title, inner):
    return box(name, x, y, width, height,
               text(name + "_title", 14, 8, width - 28, B.key(name + "_title", title), FONT_CARD, height=30) + inner, CARD_BG)


def stripes(name, x, y, width, row_height, rows):
    """The darker bands of a table whose rows stand in the file: one behind every second row."""
    return "".join(icon("%s_%d" % (name, n), x, y + n * row_height, STRIPE % (width, row_height)) for n in range(1, rows, 2))


def title_strip(name, window_width, height=50):
    """The title strip across the top of a page, 3 inside the window's edge."""
    return box(name, 3, 3, window_width - 6, height, "", layout.TITLE_STRIP)


def page_title(name, width, words):
    return text(name, 22, 8, width, B.key(name, words), FONT_TITLE, height=40)


def close_button(name, x, y, shortcut="ESCAPE", tooltip=None):
    """The close button at the right end of the title strip (wiki/Design-Language.md, "Fixed places")."""
    return button(name, x, y, layout.CLOSE_BUTTON, shortcut=shortcut, tooltip=tooltip)


# ---------------------------------------------------------------- Army readiness (D2), docked to Recruit & Deploy

# The kinds of land equipment: every archetype a land sub-unit asks for, with the sprite of its picture and that
# picture's size (tools/equipment_kinds_table.py, made from the game by tools/make_game_tables.py). A playset with
# a map of its own has a table of its own (tools/equipment_kinds_mods_table.py, made with --mods), and script counts
# the kinds of the table whose number of states the loaded game has (Engine Facts X72), the game's otherwise. The
# name of a kind is the game's own text for the archetype, so it follows the player's language.
from equipment_kinds_table import KINDS as AR_KINDS  # noqa: E402
try:
    from equipment_kinds_mods_table import MAPS as AR_MAPS  # noqa: E402
except ImportError:
    AR_MAPS = []
AR_TABLES = [(0, AR_KINDS)] + [(states, rows) for _mods, states, rows in AR_MAPS]
EQUIPMENT = [row[0] for row in AR_KINDS]        # the game's kinds (tools/check_playset.py compares the playset with them)

# The page: a window of its own on the screen (no parent_window_token, Engine Facts X7; phase D8, 2026-10-21), at
# the place it had while docked to Recruit & Deploy: beside the template panel of the mod's panel, which ends at
# 1246 (vanilla's at 914). 975 wide: it stops short of the theatre box under the clock (screen x 2234). Two
# scripted GUIs one under the other: the head (title strip and figures), which is the whole page in its short form,
# and the body (equipment and armies); a group of widgets is hidden only as a scripted GUI of its own (X15). Free,
# it shows over the vanilla window too, which cuts off what is docked to its tab (X6), and it cannot close with the
# tab: closed by default, opened by its handle.
# Round 2 (2026-10-17, wiki/phases/D2-army-readiness.md): the figures as three banded tables; heads that sort; a
# click on an army chooses it, and the equipment card shows that army's own kinds; where the troops stand; the
# commander's skill and four levels, and the army's name under him on a locally patched game [SCR-078].
AR_X, AR_Y, AR_W = 1250, 78, 975   # screen coordinates (D8: a free window)
# The handle of a free page (D8): docked to its tab, inside the 550 px every version of the tab's panel has, at the
# same place on Politics and on Recruit & Deploy: tab 359,12 (screen 353,90), 92x34.
HANDLE_X, HANDLE_Y, HANDLE_W, HANDLE_H = 359, 12, 92, 34
PAGE_CLOSE_TT = "Hide this page and give the map back (Shift+M or Escape). It stays open when its tab closes."
AR_H = 1210                     # ends where the template panel ends, above the army portraits of the bottom bar
AR_HEAD = 60                    # height of the title strip
AR_SUM_H = 244                  # the head: title strip and the three tables of figures
# The page background (GFX_tiled_window_1b_thin_border) fades out over its outer 5 px (alpha 0 to 152): two free
# windows edge to edge show 10 px of map between them (D8 fix round 1). The body starts that much higher and is
# that much taller, its content moved down by it, so that its opaque border meets the head's (screen y 317).
AR_SHADOW = 5
AR_OVERLAP = 2 * AR_SHADOW
AR_BODY_Y = AR_Y + AR_SUM_H - AR_OVERLAP   # 312 on the screen
AR_IN = AR_W - 28               # what a card has between the margins of the page: 947
AR_TABLE = AR_IN - 28           # a table inside a card: 919
AR_ROW_W = AR_TABLE - 30        # a row beside the scrollbar: 889
AR_EQ_ROW, AR_EQ_ROWS = 32, 9   # the equipment list: nine rows on the screen
AR_AL_ROW, AR_AL_ROWS = 50, 10  # the armies list: ten rows on the screen
LOW = 75                        # a bar is orange below this many percent
# A picture of a kind stands in a box; the game's pictures are of many sizes, and an icon has one scale. So a row
# has one icon per scale, and script shows the one its kind needs: the largest scale at which the picture fits.
AR_SCALES = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4]
AR_PIC_BOX = (84, 30)           # in an equipment row
AR_WORST_BOX = (52, 22)         # the worst equipped kind in an army row, over its share
# The figures: three cards of 311x174, 6 apart, from y 66 of the head. In each a head bar of 299x30 and five rows
# of 26 from y 40, every second on a band; the label at x 14, the value right-aligned 8 px inside the band, a bar
# of 64 between them where a row has one.
AR_FIG_Y, AR_FIG_W, AR_FIG_H, AR_FIG_GAP = 66, 311, 174, 6
AR_FIG_ROW, AR_FIG_TOP = 26, 40
AR_FIG_RIGHT = 297              # right edge of a value
AR_FIG_LABEL_W = 190            # a label without a bar: the longest, "Without a commander", and room to spare
AR_FIG_VALUE_X = 204            # left edge of a value without a bar: 93 px for "12500K" or "1500.0K"
AR_FIG_BAR = 64
SORT_TIP = "\\nClick to sort, click again to turn the order."
LOW_TIP = "\\nClick to sort, the lowest first; click again to turn the order."

# (name, label, value, tooltip, zero, bar). zero: (variable, text) when the value shows only above zero and the
# text otherwise; bar: (x, variable of its fill, trigger for the bar or "").
AR_FIGURES = [
    ("Manpower", [
        ("mp_free", "Free manpower", "[?manpower_k|0]K", "Men you can still call up: the manpower of the top bar.", None, None),
        ("mp_training", "In training", "[?amount_manpower_in_deployment_queue|*1]",
         "Men of the divisions in training. Queue a division and this rises.", ("amount_manpower_in_deployment_queue", "0"), None),
        ("mp_army", "In the army", "[?deployed_army_manpower_k|0]K",
         "Men of the divisions in the field.\\nIn the navy: [?deployed_navy_manpower_k|0]K\\nIn the air force: [?deployed_airforce_manpower_k|0]K", None, None),
        ("mp_garrison", "Garrisons need", "§Y[?garrison_manpower_need|*1]§!", "Men the garrisons of your occupied states ask for.",
         ("garrison_manpower_need", "0"), None),
        ("casualties", "Casualties", "[?casualties_k|1]K", "Men your country has lost in all of its wars, as the war overview counts them.",
         ("casualties_k", "0"), None),
    ]),
    ("Army", [
        ("divisions", "Divisions", "[?num_divisions|0]", "Divisions in the field, with [?num_battalions|0] battalions. Divisions in training are not counted.", None, None),
        ("fighting", "Fighting", "[?mod1440_ar_fight|Y0]",
         "Divisions in combat, as of the last count: the sum over the commanders of single armies, so that an army group is not counted twice. Divisions without a commander are not in it.",
         ("mod1440_ar_fight", "0"), None),
        ("low_str", "Under strength", "[?mod1440_ar_low_str|Y0]", "Divisions below 75% strength, as of the last count.", ("mod1440_ar_low_str", "0"), None),
        ("low_org", "Low organisation", "[?mod1440_ar_low_org|Y0]", "Divisions below 50% organisation, as of the last count.", ("mod1440_ar_low_org", "0"), None),
        ("no_cmd", "Without a commander", "[?mod1440_ar_nocmd|Y0]",
         "Divisions in no army with a commander, as of the last count: your divisions less those the commanders of single armies lead.",
         ("mod1440_ar_nocmd", "0"), None),
    ]),
    ("Stocks", [
        ("eq_field", "Equipped in the field", "[?mod1440_ar_eqf|0]%",
         "The pieces of equipment your divisions in the field hold, as a share of what they need, over every kind; a kind held beyond its need counts as full. As of the last count. Orange below %d%%. Infantry equipment outweighs the rest: the Short column and the Worst column of the armies show a kind that is short." % LOW,
         ("mod1440_ar_eqn", "§g-§!"), (156, "mod1440_ar_eqf", more_than_zero("mod1440_ar_eqn"))),
        ("k_short", "Kinds short", "§O[?mod1440_ar_kshort|0]§!",
         "Kinds of equipment your divisions in the field have less of than they need, as of the last count: the kinds with a number in the Short column.",
         ("mod1440_ar_kshort", "0"), None),
        ("k_red", "Stock cannot cover", "[?mod1440_ar_kred|R0]",
         "Of those, the kinds whose stock cannot fill the gap, as of the last count: Short in red.", ("mod1440_ar_kred", "0"), None),
        ("fuel", "Fuel", "[?fuel_k|0]K of [?max_fuel_k|0]K",
         "Fuel in store, of the most you can store: the numbers of the top bar. The bar is their share as of the last count, orange below %d%%." % LOW,
         None, (66, "mod1440_ar_fuel", "")),
        ("xp", "Army experience", "[?army_experience|0]", "Army experience to spend on templates and equipment.", None, None),
    ]),
]

# The heads of the two tables: one plate per column, in the row's coordinates (key, head, x, width, align, order,
# tooltip). order: "H" a click sorts largest first, "L" lowest first, "" the column does not sort; the first column
# gives the first order back. The arrow of the sorted column: ARROW, ARROW_DX, ARROW_DY of the shared look.
AR_EQ_COLS = [
    ("kind", "Kind", 0, 344, "left", "H", "The kind of equipment, with the game's picture of it.\\nClick: back to the first order, the worst equipped first, then the kinds only in stock."),
    ("stock", "In stock", 348, 88, "right", "H", "Equipment in the stockpile that no division and no training has taken: the number of the logistics tab, as of the last count. It is the country's, also while an army is chosen (grey then)." + SORT_TIP),
    ("field", "In the field", 440, 84, "right", "H", "Equipment in the hands of the divisions in the field; while an army is chosen, of that army's divisions. Red when it is less than they need." + SORT_TIP),
    ("need", "Needed", 528, 84, "right", "H", "What the templates of the divisions in the field ask for; while an army is chosen, that army's. Divisions in training are not counted." + SORT_TIP),
    ("short", "Short", 616, 84, "right", "H", "What the divisions lack: needed less in the field. Red when the stock cannot fill it, orange when it can." + SORT_TIP),
    ("fill", "Equipped", 704, 185, "left", "L", ("In the field as a share of needed. Orange below %d%%." % LOW) + LOW_TIP),
]
AR_AL_COLS = [
    ("cmd", "Commander", 0, 312, "centre", "H", "A general or field marshal who commands troops: his portrait, name and skill, and under them the army's name and his attack, defence, planning and logistics. The army's name stands there when the game gives it to the page (a locally patched game); otherwise the army is known by its commander, as on its badge.\\nClick: back to the game's order of commanders."),
    ("where", "Location", 316, 130, "centre", "", "The state where most of his divisions stand, as of the last count: a click moves the camera there. Under it the state of his headquarters. At sea: none of his divisions stands in a state of yours, of your faction or of an enemy."),
    ("div", "Div", 450, 38, "centre", "H", "Divisions under this commander. Grey for a field marshal who leads an army group: its divisions are counted again under the generals of its armies." + SORT_TIP),
    ("inf", "Inf", 492, 30, "centre", "", "Divisions that are mostly infantry."),
    ("arm", "Arm", 524, 30, "centre", "", "Divisions that are mostly armour."),
    ("mot", "Mot", 556, 30, "centre", "", "Divisions that are mostly motorised."),
    ("mech", "Mech", 588, 32, "centre", "", "Divisions that are mostly mechanised."),
    ("oth", "Oth", 622, 30, "centre", "", "Divisions of every other kind: cavalry, artillery, rocket and special, as of the last count (the row's tooltip names them). The five add up to Div."),
    ("fight", "Fighting", 656, 56, "centre", "H", "Divisions of this commander in combat now, and how many of them attack and defend." + SORT_TIP),
    ("plan", "Planning", 716, 54, "centre", "L", "The planning bonus his divisions have built up, as a share of the most they can have, as of the last count." + LOW_TIP),
    ("equip", "Equipped", 774, 54, "centre", "L", ("The pieces of equipment his divisions hold, as a share of what they need, over every kind; a kind held beyond its need counts as full. As of the last count. Orange below %d%%." % LOW) + LOW_TIP),
    ("worst", "Worst", 832, 57, "centre", "L", ("The worst equipped kind of his army, with what it has as a share of what its templates ask for, as of the last count. Orange below %d%%. The row's tooltip names the kind." % LOW) + LOW_TIP),
]
AR_LEVELS = [("atk", "attack_level", "GFX_trait_attack"), ("def", "defense_level", "GFX_trait_defense"),
             ("pln", "planning_level", "GFX_trait_planning"), ("log", "logistics_level", "GFX_trait_logistics")]
AR_KINDS_ROW = [("inf", "num_infantry"), ("arm", "num_armored"), ("mot", "num_motorized"), ("mech", "num_mechanized"), ("oth", "mod1440_al_oth")]
# The sort keys of the armies list, one array each, kept by the count (a sort counts nothing)
AR_AL_KEYS = {"div": "num_units", "fight": "num_units_in_combat", "plan": "mod1440_al_plan", "equip": "mod1440_al_eq", "worst": "mod1440_al_fill"}
AR_SORT_LAST = -2100000         # what a picked key becomes: below every key a sort can meet


def ar_text(name, x, y, width, key, font=FONT_LABEL, fmt="left", height=24, fixed=False):
    """A text that lets a click through to the button under it; fixed: a box of its own size for a name another
    mod can make longer (W28)."""
    return ('instantTextboxType = { name = "%s" position = { x = %d y = %d } font = "%s" text = "%s" '
            'maxWidth = %d maxHeight = %d format = %s alwaystransparent = yes%s }\n'
            % (name, x, y, font, key, width, height, fmt, " fixedsize = yes" if fixed else ""))


def ar_scale(width, height, box):
    """The index in AR_SCALES of the largest scale at which a picture fits its box."""
    fit = min(box[0] / float(width), box[1] / float(height), 1.0)
    for n, scale in enumerate(AR_SCALES):
        if scale <= fit + 0.001:
            return n
    return len(AR_SCALES) - 1


def ar_pictures(prefix, x, y, box, image):
    """One icon per scale in a box of a row, each shown by script for the kinds of its scale; the sprite is named
    by script (image). Each stands in the middle of the box's height for the pictures of its scale."""
    heights = {}
    for _states, rows in AR_TABLES:
        for _kind, _sprite, width, height in rows:
            heights.setdefault(ar_scale(width, height, box), []).append(height * AR_SCALES[ar_scale(width, height, box)])
    out, props = "", ""
    for n, scale in enumerate(AR_SCALES):
        seen = sorted(heights.get(n, [box[1]]))
        middle = seen[len(seen) // 2]
        out += scaled("%s_%d" % (prefix, n), x, y + int((box[1] - middle) // 2), "GFX_archetype_infantry_equipment_medium", scale)
        props += block("%s_%d" % (prefix, n), 'image = "%s"\n' % image)
    return out, props


def ar_plates(prefix, columns, sort_effect, by, up):
    """The heads of a table in its card: a plate per column at card x 14 + column x, y 36; a sortable column is a
    button whose click sorts (the first column gives the first order back), the others a plate. Returns the
    widgets and their effects."""
    out, effects = "", ""
    for n, (key, label, cx, cw, fmt, order, tip) in enumerate(columns):
        x = 14 + cx
        tooltip = B.key("%s_%s_tt" % (prefix, key), tip)
        if order:
            out += button("%s_%s" % (prefix, key), x, 36, head_sprite(cw), tooltip=tooltip)
            if n == 0:
                effects += block("%s_%s_click" % (prefix, key), setv(by, 0) + setv(up, 0) + sort_effect)
            else:
                effects += block("%s_%s_click" % (prefix, key), iff("check_variable = { %s = %d }" % (by, n), flip(up))
                                 + els(setv(by, n) + setv(up, 0)) + sort_effect)
        else:
            out += icon("%s_%s" % (prefix, key), x, 36, head_sprite(cw))
        lx, lw = (x + 8, cw - 16) if fmt == "left" else ((x, cw - 8) if fmt == "right" else (x, cw))
        if order:
            out += ar_text("%s_%s_l" % (prefix, key), lx, 42, lw, B.key("%s_%s_l" % (prefix, key), label), FONT_SMALL, fmt, 20)
        else:
            out += text("%s_%s_l" % (prefix, key), lx, 42, lw, B.key("%s_%s_l" % (prefix, key), label), FONT_SMALL, fmt, 20, tooltip=tooltip)
    return out, effects


def ar_arrows(prefix, columns, variable, asc):
    """The arrow of the sorted column, which script moves (X4): down for largest first, up for lowest first."""
    first = 14 + columns[0][2] + columns[0][3] - ARROW_DX
    out = scaled("%s_arrow_down" % prefix, first, 36 + ARROW_DY, "GFX_arrow_down_small", ARROW)
    out += scaled("%s_arrow_up" % prefix, first, 36 + ARROW_DY, "GFX_arrow_up_small", ARROW)
    props = block("%s_arrow_down" % prefix, "x = %s\n" % variable) + block("%s_arrow_up" % prefix, "x = %s\n" % variable)
    trig = block("%s_arrow_down_visible" % prefix, "NOT = { %s }\n" % is_one(asc)) + block("%s_arrow_up_visible" % prefix, is_one(asc) + "\n")
    return out, props, trig


def army_readiness():
    effects = ""
    triggers = ""
    properties = ""
    counted = more_than_zero("mod1440_ar_counted")
    # 1 = open (D8; it was mod1440_ar_folded, 0 = open: a save of an earlier build reads 0 here, so its page is closed)
    shown = is_one("mod1440_ar_open")
    small = "check_variable = { mod1440_ar_small = 1 }"
    chosen = is_one("mod1440_ar_has_sel") + "\n"
    all_armies = "NOT = { %s }\n" % is_one("mod1440_ar_has_sel")

    # ---- the head: title strip, the date of the count and its button, the size, the fold
    head = title_strip("ar_head", AR_W)
    head += page_title("ar_title", 350, "Army Readiness")
    head += text("ar_counted", 380, 20, 270, B.key("ar_counted", "Counted [?mod1440_ar_counted.GetDateStringNoHourLong]"), FONT_SMALL, "right", 20)
    triggers += block("ar_counted_visible", counted)
    head += button("ar_count", 662, 10, "GFX_button_123x34", B.key("ar_count", "Count again"), tooltip=B.key(
        "ar_count_tt", "Goes through every division, every kind of equipment and every commander once. The counted figures, the equipment, the armies and where they stand are from the last time this ran: at the start of each day, and on this button."))
    effects += block("ar_count_click", "mod1440_ar_count = yes\n")
    head += button("ar_small", 795, 13, "GFX_sort_button_100x29", B.key("ar_small", "Summary"), tooltip=B.key(
        "ar_small_tt", "Fold the page to its figures: the map below them is free for picking a deploy location."))
    head += button("ar_full", 795, 13, "GFX_sort_button_100x29", B.key("ar_full", "Full"), tooltip=B.key(
        "ar_full_tt", "Show the equipment and the armies again."))
    effects += block("ar_small_click", setv("mod1440_ar_small", 1))
    effects += block("ar_full_click", setv("mod1440_ar_small", 0) + "mod1440_ar_count = yes\n")
    triggers += block("ar_small_visible", "NOT = { %s }\n" % small) + block("ar_full_visible", small + "\n")
    # the game writes the shortcut into the tooltip by itself (Engine Facts X8)
    head += close_button("ar_fold", AR_W - 66, 10, "shift+m", B.key("ar_fold_tt", PAGE_CLOSE_TT))
    # Escape on a twin off the screen: one widget has one shortcut (Engine Facts GUW-006); a free window takes
    # Escape before the open tab (X9)
    head += close_button("ar_fold_esc", -1000, -1000)
    effects += block("ar_fold_click", setv("mod1440_ar_open", 0))
    effects += block("ar_fold_esc_click", setv("mod1440_ar_open", 0))

    # ---- the figures: three banded tables of five rows
    for c, (title, rows) in enumerate(AR_FIGURES):
        inner = icon("ar_card_%d_head" % c, 6, 6, head_sprite(AR_FIG_W - 12))
        inner += ar_text("ar_card_%d_title" % c, 14, 11, AR_FIG_W - 28, B.key("ar_card_%d_title" % c, title), FONT_LABEL, height=22)
        for n, (name, label, value, tip, zero, bar) in enumerate(rows):
            y = AR_FIG_TOP + n * AR_FIG_ROW
            if n % 2:
                inner += icon("ar_card_%d_band_%d" % (c, n), 6, y, STRIPE % (AR_FIG_W - 12, AR_FIG_ROW))
            tooltip = B.key("ar_%s_tt" % name, tip)
            label_w = bar[0] - 16 if bar else AR_FIG_LABEL_W
            value_x = bar[0] + AR_FIG_BAR + 6 if bar else AR_FIG_VALUE_X
            inner += text("ar_%s_l" % name, 14, y + 3, label_w, B.key("ar_%s_l" % name, label), FONT_LABEL, height=22, tooltip=tooltip)
            inner += text("ar_" + name, value_x, y + 1, AR_FIG_RIGHT - value_x, B.key("ar_" + name, value), FONT_VALUE, "right", 24, tooltip=tooltip)
            if zero:
                variable, twin = zero
                twin_key = "0" if twin == "0" else B.key("ar_row_dash", twin)
                inner += text("ar_%s_z" % name, value_x, y + 1, AR_FIG_RIGHT - value_x, twin_key, FONT_VALUE, "right", 24, tooltip=tooltip)
                triggers += block("ar_%s_visible" % name, more_than_zero(variable))
                triggers += block("ar_%s_z_visible" % name, "NOT = { %s }\n" % more_than_zero(variable).strip())
            if bar:
                bx, variable, when = bar
                inner += icon("ar_%s_bar" % name, bx, y + 8, bar_sprite(AR_FIG_BAR)) + icon("ar_%s_low" % name, bx, y + 8, bar_sprite(AR_FIG_BAR, low=True))
                properties += block("ar_%s_bar" % name, "frame = %s\n" % variable) + block("ar_%s_low" % name, "frame = %s\n" % variable)
                low = "check_variable = { %s < %d }\n" % (variable, LOW)
                triggers += block("ar_%s_bar_visible" % name, counted + when + "NOT = { %s }\n" % low.strip())
                triggers += block("ar_%s_low_visible" % name, counted + when + low)
        head += box("ar_card_%d" % c, 14 + c * (AR_FIG_W + AR_FIG_GAP), AR_FIG_Y, AR_FIG_W, AR_FIG_H, inner, CARD_BG)

    # ---- equipment: the kinds in use, or the chosen army's, from the arrays of the last count
    body = ""
    eq_h = 68 + AR_EQ_ROWS * AR_EQ_ROW + 8
    # the captions end at card x 919 (page 933), the chosen army's before the All armies button (card 812)
    inner = text("ar_eq_caption", 286, 13, 633, B.key("ar_eq_caption", "§gAll armies: [?mod1440_ar_fill^num|0] of [?mod1440_ar_kinds|0] kinds in use. Click a head to sort, an army below to see its own.§!"),
                 FONT_SMALL, "right", 20, tooltip=B.key("ar_eq_caption_tt", "A kind is listed while you have some in stock or your divisions in the field need some. The numbers are from the last count."))
    inner += text("ar_eq_caption_army", 286, 13, 518, B.key("ar_eq_caption_army", "§gThe army of§! §Y[?mod1440_ar_sel.GetName]§!§g: [?mod1440_ar_fill^num|0] kinds it needs§!"),
                  FONT_SMALL, "right", 20, tooltip=B.key("ar_eq_caption_army_tt", "The kinds the chosen army's divisions need or hold, as of the last count: In the army and Needed are that army's, In stock is the country's (grey). Click his row again, or All armies, for the whole country."), fixed=True)
    inner += button("ar_eq_all", 812, 8, "GFX_sort_button_100x29", B.key("ar_eq_all", "All armies"),
                    tooltip=B.key("ar_eq_all_tt", "Back to the equipment of the whole country."))
    triggers += block("ar_eq_caption_visible", all_armies) + block("ar_eq_caption_army_visible", chosen) + block("ar_eq_all_visible", chosen)
    effects += block("ar_eq_all_click", setv("mod1440_ar_has_sel", 0) + "mod1440_ar_list = yes\nmod1440_ar_marks = yes\n")
    plates, more = ar_plates("ar_eh", AR_EQ_COLS, "mod1440_ar_eq_sort = yes\n", "mod1440_ar_eq_by", "mod1440_ar_eq_up")
    inner += plates
    effects += more
    # In the field becomes In the army while an army is chosen
    field = [c for c in AR_EQ_COLS if c[0] == "field"][0]
    inner += ar_text("ar_eh_field_army", 14 + field[2], 42, field[3] - 8, B.key("ar_eh_field_army", "In the army"), FONT_SMALL, "right", 20)
    triggers += block("ar_eh_field_l_visible", all_armies) + block("ar_eh_field_army_visible", chosen)
    arrows, more, trig = ar_arrows("ar_eq", AR_EQ_COLS, "mod1440_ar_eq_arrow_x", "mod1440_ar_eq_asc")
    inner += arrows
    properties += more
    triggers += trig
    inner += listing("ar_eq_list", "ar_eq_grid", 14, 68, AR_TABLE, AR_EQ_ROWS * AR_EQ_ROW, AR_EQ_ROW)
    inner += text("ar_eq_none", 28, 80, 700, B.key("ar_eq_none", "No kind of land equipment in stock or needed."), FONT_SMALL)
    triggers += block("ar_eq_none_visible", "check_variable = { mod1440_ar_fill^num < 1 }\n")
    body += card("ar_equipment", 14, 6, AR_IN, eq_h, "Equipment", inner)

    # A row of the list: the list's array holds the share of each kind (the bar's fill, "v"); the other values are
    # elements of the arrays beside it at the row's index ("i", Engine Facts X50).
    def at(array):
        return "mod1440_ar_%s^i" % array

    edge = {key: cx + cw - 8 for key, label, cx, cw, fmt, order, tip in AR_EQ_COLS}
    width = {key: cw - 8 for key, label, cx, cw, fmt, order, tip in AR_EQ_COLS}
    eq = icon("ar_er_stripe", 0, 0, STRIPE % (AR_ROW_W, AR_EQ_ROW))
    eq_triggers = block("ar_er_stripe_visible", "check_variable = { %s = 1 }\n" % at("odd"))
    pictures, more = ar_pictures("ar_er_pic", 8, 1, AR_PIC_BOX, "[?%s.GetTokenKey]" % at("pic"))
    eq += pictures
    properties += more
    eq_triggers += "".join(block("ar_er_pic_%d_visible" % n, "check_variable = { %s = %d }\n" % (at("cls"), n)) for n in range(len(AR_SCALES)))
    eq += text("ar_er_name", 100, 6, 240, B.key("ar_er_name", "[?%s.GetTokenLocalizedKey]" % at("kind")), FONT_LABEL, height=22, fixed=True)

    def cell(name, key, value, font=FONT_VALUE, y=4):
        return text("ar_er_" + name, edge[key] - width[key], y, width[key], B.key("ar_er_" + name, value), font, "right", 24)

    short = "check_variable = { %s > 0 }\n" % at("short")
    eq += cell("stock", "stock", "[?%s|0]" % at("stock")) + cell("stock_shared", "stock", "§g[?%s|0]§!" % at("stock"))
    eq_triggers += block("ar_er_stock_visible", all_armies) + block("ar_er_stock_shared_visible", chosen)
    eq += cell("field", "field", "[?%s|0]" % at("field")) + cell("field_short", "field", "[?%s|R0]" % at("field"))
    eq += cell("need", "need", "[?%s|0]" % at("need"))
    eq += cell("short", "short", "[?%s|R0]" % at("short")) + cell("short_covered", "short", "§O[?%s|0]§!" % at("short"))
    eq_triggers += block("ar_er_field_visible", "NOT = { %s }\n" % short.strip()) + block("ar_er_field_short_visible", short)
    eq_triggers += block("ar_er_short_visible", short + "check_variable = { %s = 1 }\n" % at("red"))
    eq_triggers += block("ar_er_short_covered_visible", short + "check_variable = { %s = 0 }\n" % at("red"))
    eq += icon("ar_er_bar", 722, 10, bar_sprite(110)) + icon("ar_er_low", 722, 10, bar_sprite(110, low=True))
    eq += text("ar_er_pct", 884 - 50, 6, 50, B.key("ar_er_pct", "[?%s|0]%%" % at("fill")), FONT_LABEL, "right", 24)
    needed = "check_variable = { %s > 0 }\n" % at("need")
    eq_triggers += block("ar_er_bar_visible", needed + "check_variable = { v > %d }\n" % (LOW - 1))
    eq_triggers += block("ar_er_low_visible", needed + "check_variable = { v < %d }\n" % LOW)
    eq_triggers += block("ar_er_pct_visible", needed)
    properties += block("ar_er_bar", "frame = v\n") + block("ar_er_low", "frame = v\n")
    triggers += eq_triggers

    # ---- armies: one row per general who has troops
    armies_y = 6 + eq_h + 10
    armies_h = AR_H - AR_SUM_H - armies_y - 14
    # D2 fix round 2: the army's name under each commander is the player's choice (decision 8): it comes from a
    # local patch of hoi4.exe [SCR-078], and an unpatched game writes "Himself" there. The toggle stands beside the
    # card's title, its second frame for "on" (as the choices of the States page).
    inner = button("ar_names", 130, 5, "GFX_sort_button_100x29", B.key("ar_names", "Army names"), tooltip=B.key(
        "ar_names_tt", "Shows each army's name under its commander. Needs the local patch of hoi4.exe (Modding Manager, Set-HoiArmyNameProperty.ps1); without it this line would read Himself."))
    properties += block("ar_names", "frame = mod1440_ar_names_fr\n")
    effects += block("ar_names_click", iff(is_one("mod1440_ar_names"), setv("mod1440_ar_names", 0) + setv("mod1440_ar_names_fr", 1))
                     + els(setv("mod1440_ar_names", 1) + setv("mod1440_ar_names_fr", 2)))
    inner += text("ar_al_caption", 240, 13, 679, B.key("ar_al_caption", "§g[?mod1440_ar_leaders^num|0] commanders with troops. Click one for his army's equipment, right-click for the map.§!"),
                 FONT_SMALL, "right", 20)
    # D2 fix round 1: one commander in the singular
    inner += text("ar_al_caption_one", 240, 13, 679, B.key("ar_al_caption_one", "§g1 commander with troops. Click him for his army's equipment, right-click for the map.§!"),
                  FONT_SMALL, "right", 20)
    triggers += block("ar_al_caption_visible", "check_variable = { mod1440_ar_leaders^num > 1 }\n")
    triggers += block("ar_al_caption_one_visible", "check_variable = { mod1440_ar_leaders^num = 1 }\n")
    plates, more = ar_plates("ar_ah", AR_AL_COLS, "mod1440_ar_al_sort = yes\nmod1440_ar_marks = yes\n", "mod1440_ar_al_by", "mod1440_ar_al_up")
    inner += plates
    effects += more
    arrows, more, trig = ar_arrows("ar_al", AR_AL_COLS, "mod1440_ar_al_arrow_x", "mod1440_ar_al_asc")
    inner += arrows
    properties += more
    triggers += trig
    inner += listing("ar_al_list", "ar_al_grid", 14, 68, AR_TABLE, AR_AL_ROWS * AR_AL_ROW, AR_AL_ROW)
    inner += text("ar_al_none", 28, 84, 700, B.key("ar_al_none", "No army has a commander yet. An army is listed here once it has one."), FONT_SMALL)
    triggers += block("ar_al_none_visible", "check_variable = { mod1440_ar_leaders^num < 1 }\n")
    body += card("ar_armies", 14, armies_y, AR_IN, armies_h, "Armies", inner)

    # A row: the row's scope is the commander. His levels, kinds and fighting are live; the rest is of the last
    # count. The whole row is a transparent button under the Location button: a click chooses his army, a
    # right-click moves the camera to where his troops stand.
    col = {key: (cx, cw) for key, label, cx, cw, fmt, order, tip in AR_AL_COLS}
    picked = is_one("mod1440_al_pick") + "\n"
    entry = icon("ar_row_stripe", 0, 0, STRIPE % (AR_ROW_W, AR_AL_ROW))
    entry += icon("ar_row_pick", 0, 0, PICK % (AR_ROW_W, AR_AL_ROW))
    row_triggers = block("ar_row_stripe_visible", is_one("mod1440_al_odd") + "\nNOT = { %s }\n" % picked.strip()) + block("ar_row_pick_visible", picked)
    # E7: the row's scope is the commander, a unit leader: the game draws his face [SGUI-053]. The table of portraits
    # and the unknown leader shown until it had looked him up (ar_row_unknown) are gone.
    entry += scaled("ar_row_face", 4, 2, "GFX_portrait_unknown", 0.22)
    properties += block("ar_row_face", build_records.GAME_FACE)
    # line 1: his name and skill; line 2: the army's name (empty on an unpatched game) and his four levels
    entry += ar_text("ar_row_name", 46, 5, 210, B.key("ar_row_name", "§Y[THIS.GetName]§!"), FONT_LABEL, height=22, fixed=True)
    entry += icon("ar_row_skill_bg", 262, 4, "GFX_1440p_SG_tile_30x24")
    entry += ar_text("ar_row_skill", 262, 6, 30, B.key("ar_row_skill", "[?skill_level|0]"), FONT_LABEL, "centre", 22)
    # the army's name: on the patched game a property of the army leader gives it [SCR-078]; shown while the
    # player has Army names on, and not for a field marshal of an army group, whom the patch does not answer
    names = "check_variable = { ROOT.mod1440_ar_names = 1 }\n"
    group = "is_leading_army_group = yes\n"
    entry += ar_text("ar_row_army", 46, 28, 137, B.key("ar_row_army", "[THIS.GetHerselfHimselfCap]"), FONT_SMALL, height=20, fixed=True)
    row_triggers += block("ar_row_army_visible", names + "NOT = { %s }\n" % group.strip())
    for k, (name, variable, sprite) in enumerate(AR_LEVELS):
        x = 189 + k * 31
        entry += scaled("ar_row_%s_icon" % name, x, 28, sprite, 0.6)
        entry += ar_text("ar_row_%s" % name, x + 18, 28, 13, B.key("ar_row_%s" % name, "[?%s|0]" % variable), FONT_SMALL, height=20)
    # Location: under the button, the state of his headquarters
    lx, lw = col["where"]
    # D2 fix round 2: in the game the Location pass set mod1440_al_loc to Brandenburg (game.log), and the row's
    # "mod1440_al_loc > 0" stayed false while the row read the numbers set beside it: a variable that holds a state
    # set from THIS is not asked "> 0" (the Records keep a kind number beside each scope they store). Location is
    # asked by its count of divisions, a plain number. The HQ (state_deployed, an undocumented variable, SCR-069) is
    # left as it was until a check with a deployed HQ shows which form holds (tools/check_effects.py,
    # mod1440_chk_ar_row, logs each form as the row sees it).
    hq = more_than_zero("mod1440_al_hq")
    entry += ar_text("ar_row_hq", lx, 31, lw, B.key("ar_row_hq", "§gHQ§! [?mod1440_al_hq.GetName]"), FONT_SMALL, "centre", 20, fixed=True)
    entry += ar_text("ar_row_hq_none", lx, 31, lw, B.key("ar_row_hq_none", "§gHQ not deployed§!"), FONT_SMALL, "centre", 20)
    row_triggers += block("ar_row_hq_visible", hq) + block("ar_row_hq_none_visible", "NOT = { %s }\n" % hq.strip())
    where = more_than_zero("mod1440_al_lcnt")
    entry += ar_text("ar_row_loc_none", lx, 7, lw, B.key("ar_row_loc_none", "§gat sea§!"), FONT_SMALL, "centre", 20)
    row_triggers += block("ar_row_loc_none_visible", "NOT = { %s }\n" % where.strip())
    # divisions: grey for a field marshal who leads an army group, whose divisions are counted again under his generals
    group = "is_leading_army_group = yes\n"
    dx, dw = col["div"]
    entry += ar_text("ar_row_div", dx, 13, dw, B.key("ar_row_div", "[?num_units|0]"), FONT_VALUE, "centre", 24)
    entry += ar_text("ar_row_div_group", dx, 13, dw, B.key("ar_row_div_group", "§g[?num_units|0]§!"), FONT_VALUE, "centre", 24)
    row_triggers += block("ar_row_div_visible", "NOT = { is_leading_army_group = yes }\n") + block("ar_row_div_group_visible", group)
    for name, variable in AR_KINDS_ROW:
        kx, kw = col[name]
        entry += ar_text("ar_row_%s" % name, kx, 15, kw, B.key("ar_row_%s" % name, "[?%s|0]" % variable), FONT_LABEL, "centre", 22)
        entry += ar_text("ar_row_%s_none" % name, kx, 15, kw, B.key("ar_row_dash", "§g-§!"), FONT_LABEL, "centre", 22)
        row_triggers += block("ar_row_%s_visible" % name, more_than_zero(variable))
        row_triggers += block("ar_row_%s_none_visible" % name, "NOT = { %s }\n" % more_than_zero(variable).strip())
    fighting = more_than_zero("num_units_in_combat")
    fx, fw = col["fight"]
    entry += ar_text("ar_row_fight", fx, 4, fw, B.key("ar_row_fight", "§Y[?num_units_in_combat|0]§!"), FONT_VALUE, "centre", 24)
    entry += ar_text("ar_row_split", fx - 4, 28, fw + 8, B.key("ar_row_split", "§g[?num_units_offensive_combats|0] att [?num_units_defensive_combats|0] def§!"), FONT_SMALL, "centre", 20)
    entry += ar_text("ar_row_fight_none", fx, 15, fw, B.key("ar_row_dash", "§g-§!"), FONT_LABEL, "centre", 22)
    row_triggers += block("ar_row_fight_visible", fighting) + block("ar_row_split_visible", fighting)
    row_triggers += block("ar_row_fight_none_visible", "NOT = { %s }\n" % fighting.strip())
    # planning and equipped: a share over a bar of 46
    px, pw = col["plan"]
    entry += ar_text("ar_row_plan", px, 6, pw, B.key("ar_row_plan", "[?mod1440_al_plan|0]%"), FONT_LABEL, "centre", 22)
    entry += icon("ar_row_plan_bar", px + 4, 31, bar_sprite(pw - 8))
    properties += block("ar_row_plan_bar", "frame = mod1440_al_plan\n")
    ex, ew = col["equip"]
    low_eq = "check_variable = { mod1440_al_eq < %d }\n" % LOW
    entry += ar_text("ar_row_eq", ex, 6, ew, B.key("ar_row_eq", "[?mod1440_al_eq|0]%"), FONT_LABEL, "centre", 22)
    entry += ar_text("ar_row_eq_low", ex, 6, ew, B.key("ar_row_eq_low", "§O[?mod1440_al_eq|0]%§!"), FONT_LABEL, "centre", 22)
    entry += icon("ar_row_eq_bar", ex + 4, 31, bar_sprite(ew - 8)) + icon("ar_row_eq_lowbar", ex + 4, 31, bar_sprite(ew - 8, low=True))
    properties += block("ar_row_eq_bar", "frame = mod1440_al_eq\n") + block("ar_row_eq_lowbar", "frame = mod1440_al_eq\n")
    row_triggers += block("ar_row_eq_visible", "NOT = { %s }\n" % low_eq.strip()) + block("ar_row_eq_low_visible", low_eq)
    row_triggers += block("ar_row_eq_bar_visible", "NOT = { %s }\n" % low_eq.strip()) + block("ar_row_eq_lowbar_visible", low_eq)
    # the worst equipped kind: its picture over its share
    wx, ww = col["worst"]
    worst = "check_variable = { mod1440_al_wk = 1 }\n"
    pictures, more = ar_pictures("ar_row_worst", wx + 3, 3, AR_WORST_BOX, "[?mod1440_al_wpic.GetTokenKey]")
    entry += pictures
    properties += more
    row_triggers += "".join(block("ar_row_worst_%d_visible" % n, worst + "check_variable = { mod1440_al_wcls = %d }\n" % n) for n in range(len(AR_SCALES)))
    low = "check_variable = { mod1440_al_fill < %d }\n" % LOW
    entry += ar_text("ar_row_pct", wx, 28, ww, B.key("ar_row_pct", "[?mod1440_al_fill|0]%"), FONT_SMALL, "centre", 20)
    entry += ar_text("ar_row_pct_low", wx, 28, ww, B.key("ar_row_pct_low", "§O[?mod1440_al_fill|0]%§!"), FONT_SMALL, "centre", 20)
    row_triggers += block("ar_row_pct_visible", worst + "NOT = { %s }\n" % low.strip()) + block("ar_row_pct_low_visible", worst + low)
    # the row's button: one transparent button over the whole row, with no condition, under the Location button.
    # D2 fix round 4: fix rounds 2 and 3 had stacked six such buttons, one per rank and Army names, to name the
    # rank in the tooltip; in the game a click then chose nobody, as if every button under the pointer ran its
    # click and the choice was turned on and off again (one button, round 1, chose). The tooltip names no rank.
    details = ("\\n\\n"
               "Entrenched [?avg_unit_entrenchment_ratio|%0], ready for the plan [?unit_ratio_ready_for_plan|%0]\\n"
               "Battle plans [?num_battle_plans|0], traits [?num_traits|0]\\n"
               "Combats on average: attacks [?avg_offensive_combat_status|%0], defences [?avg_defensive_combat_status|%0]\\n"
               "Other divisions: cavalry [?num_cavalry|0], artillery [?num_artillery|0], rocket [?num_rocket|0], special [?num_special|0]\\n"
               "Worst equipped: [?mod1440_al_wkind.GetTokenLocalizedKey], [?mod1440_al_whave|0] of [?mod1440_al_wneed|0]\\n\\n"
               "Click: his army's equipment above; click again for all armies. Right-click: the camera to where his troops stand.")
    go = iff(more_than_zero("mod1440_al_lcnt").strip(),tmp("ar_go", "mod1440_al_loc") + block("var:ar_go", block("ROOT", "goto_state = PREV\n")))
    entry += button("ar_row_hit", 0, 0, "GFX_1440p_SG_hit_%dx%d" % (AR_ROW_W, AR_AL_ROW),
                    tooltip=B.key("ar_row_hit_tt", "§Y[THIS.GetName]§!" + details))
    effects += block("ar_row_hit_click", "mod1440_of_me = yes\n" + block("ROOT", "mod1440_ar_choose = yes\n"))
    effects += block("ar_row_hit_right_click", go)
    # the Location button over it: the state where most of his divisions stand
    entry += button("ar_row_loc", lx, 3, head_sprite(lw, 26), tooltip=B.key("ar_row_loc_tt", "Show where most of his divisions stand"))
    entry += ('iconType = { name = "ar_row_loc_icon" position = { x = %d y = 5 } spriteType = "GFX_countryaction_gotolocation_big" '
              'scale = 0.68 alwaystransparent = yes }\n' % (lx + 4))
    entry += ar_text("ar_row_loc_name", lx + 26, 7, lw - 30, B.key("ar_row_loc_name", "[?mod1440_al_loc.GetName]"), FONT_SMALL, "centre", 20, fixed=True)
    row_triggers += "".join(block("%s_visible" % name, where) for name in ("ar_row_loc", "ar_row_loc_icon", "ar_row_loc_name"))
    effects += block("ar_row_loc_click", go)
    triggers += row_triggers

    gui = box("mod1440_army_readiness", AR_X, AR_Y, AR_W, AR_SUM_H, head, PAGE_BG)
    gui += box("mod1440_army_readiness_body", AR_X, AR_BODY_Y, AR_W, AR_H - AR_SUM_H + AR_OVERLAP,
               box("ar_body_in", 0, AR_OVERLAP, AR_W, AR_H - AR_SUM_H, body), PAGE_BG)
    gui += row("mod1440_army_readiness_eqrow", AR_ROW_W, AR_EQ_ROW, eq)
    gui += row("mod1440_army_readiness_row", AR_ROW_W, AR_AL_ROW, entry)

    # ---- the handle that brings the page back, in the form it was left in: in the title strip of Recruit & Deploy,
    # at the place of the Figures handle on Politics (D8), clear of the title and of the close button of every version
    handle = button("ar_unfold", 0, 0, "GFX_1440p_SG_button_92", B.key("ar_unfold", "Readiness"), shortcut="shift+m",
                    tooltip=B.key("ar_unfold_tt", "Army Readiness: your manpower, divisions, equipment and commanders"))
    gui += box("mod1440_army_readiness_handle", HANDLE_X, HANDLE_Y, HANDLE_W, HANDLE_H, handle)

    # Each scripted GUI takes the effects, triggers and properties of the widgets in its own window and rows.
    def mine(part, names):
        out = ""
        for m in re.finditer(r"^(\w+) = \{\n(?:\t[^\n]*\n)*?\}\n", part, re.M):
            widget = re.sub(r"_(right_click|click|visible)$", "", m.group(1))
            if widget in names:
                out += m.group(0)
        return out

    head_names = set(re.findall(r'name = "(\w+)"', head))
    body_names = set(re.findall(r'name = "(\w+)"', body + eq + entry))
    script = scripted_gui(
        "mod1440_army_readiness", "mod1440_army_readiness",
        visible=shown + "\n",
        effects=mine(effects, head_names), triggers=mine(triggers, head_names), properties=mine(properties, head_names))
    script += "\n" + scripted_gui(
        "mod1440_army_readiness_body", "mod1440_army_readiness_body",
        visible="%s\nNOT = { %s }\n" % (shown, small),
        lists=(block("ar_eq_grid", 'array = mod1440_ar_fill\nentry_container = "mod1440_army_readiness_eqrow"\n')
               + block("ar_al_grid", 'array = mod1440_ar_leaders\nchange_scope = yes\nentry_container = "mod1440_army_readiness_row"\n')),
        effects=mine(effects, body_names), triggers=mine(triggers, body_names), properties=mine(properties, body_names))
    script += "\n" + scripted_gui(
        "mod1440_army_readiness_handle", "mod1440_army_readiness_handle", "deployment_tab",
        visible="NOT = { %s }\n" % shown,
        # one free page at a time: opening this one closes National Figures
        effects=block("ar_unfold_click", setv("mod1440_ar_open", 1) + setv("mod1440_nf_shown", 0) + "mod1440_ar_count = yes\n"))
    return gui, script, ar_count()


# The arrays of the equipment list, one element per kind in use, in the order of the list: the text key of the
# kind, the sprite of its picture as a text key, the scale of the picture, stock, in the field, needed, short, the
# share, whether the stock falls short of the gap (red) and the band of every second row. The count keeps them
# unsorted too (mod1440_ar_u_*, with the key of the first order), and a sort re-orders those.
AR_ARRAYS = ["kind", "pic", "cls", "stock", "field", "need", "short", "fill", "red", "odd"]


def ar_sort(by, up, asc, arrow_x, columns, count, value_of, keys, pick):
    """Script that puts a list into the order of its chosen column: the setting of the column (asc: lowest first,
    the arrow's x), then the key of each element (value_of(n) gives the script that sets ar_v for column n, at index
    ar_i), then the elements by their key, largest first (the key of a lowest-first order is turned)."""
    setup = ""
    sortable = [(n, c) for n, c in enumerate(columns) if c[5]]     # n: the column's number, as the head's click sets it
    for first, (n, (key, label, cx, cw, fmt, order, tip)) in enumerate(sortable):
        setup += iff("check_variable = { %s = %d }" % (by, n), tmp("ar_asc", 1 if order == "L" else 0) + setv(arrow_x, 14 + cx + cw - ARROW_DX),
                     "if" if first == 0 else "else_if")
    setup += iff("check_variable = { %s = 1 }" % up, iff("check_variable = { ar_asc = 1 }", tmp("ar_asc", 0)) + els(tmp("ar_asc", 1)))
    setup += setv(asc, "ar_asc")
    chain = ""
    for first, (n, (key, label, cx, cw, fmt, order, tip)) in enumerate(sortable):
        chain += iff("check_variable = { %s = %d }" % (by, n), value_of(n, key), "if" if first == 0 else "else_if")
    making = ("clear_array = %s\n" % keys
              + block("for_loop_effect", "start = 0\nend = %s\nvalue = ar_i\n" % count + tmp("ar_v", 0) + chain
                      + iff("check_variable = { ar_asc = 1 }", "multiply_temp_variable = { ar_v = -1 }\n")
                      + "add_to_array = { %s = ar_v }\n" % keys))
    taking = block("for_loop_effect", "start = 0\nend = %s\nvalue = ar_step\n" % count
                   + block("find_highest_in_array", "array = %s\nvalue = ar_high\nindex = ar_at\n" % keys)
                   + pick + setv("%s^ar_at" % keys, AR_SORT_LAST))
    return setup, making + taking


def ar_count():
    """The scripted effects of the counting: mod1440_ar_count, the equipment list, the sorts, the chosen army, and
    the effects of each table of kinds."""
    tables = ""
    for m, (states, rows) in enumerate(AR_TABLES):
        kinds, army, worst = "", "", ""
        for kind, sprite, width, height in rows:
            what = tmp("ar_tok", "token:" + kind) + tmp("ar_pic", "token:" + sprite) + tmp("ar_cls", ar_scale(width, height, AR_PIC_BOX))
            # the country: every kind in stock or needed, for the figures, and for the list while no army is chosen
            kinds += (tmp("ar_s", "num_equipment@" + kind) + tmp("ar_d", "num_target_equipment_in_armies@" + kind)
                      + iff("OR = { check_variable = { ar_s > 0 } check_variable = { ar_d > 0 } }", (
                          tmp("ar_f", "num_equipment_in_armies@" + kind) + "mod1440_ar_calc = yes\n"
                          + iff("check_variable = { ar_d > 0 }", "mod1440_ar_tally = yes\n")
                          + iff("check_variable = { ar_listing = 1 }", what + "mod1440_ar_add = yes\n"))))
            # the chosen army: what its divisions hold and need, against the country's stock
            army += (tmp("ar_s", "num_equipment@" + kind) + tmp("ar_f", 0) + tmp("ar_d", 0)
                     + block("var:mod1440_ar_sel", tmp("ar_f", "num_equipment@" + kind) + tmp("ar_d", "num_target_equipment@" + kind))
                     + iff("OR = { check_variable = { ar_f > 0 } check_variable = { ar_d > 0 } }", what + "mod1440_ar_calc = yes\nmod1440_ar_add = yes\n"))
            # a commander: his worst equipped kind, and what his divisions hold of what they need
            worst += iff("check_variable = { num_target_equipment@%s > 0 }" % kind, (
                tmp("al_t", "num_target_equipment@" + kind) + tmp("al_h", "num_equipment@" + kind)
                + tmp("al_share", "al_h") + "divide_temp_variable = { al_share = al_t }\nmultiply_temp_variable = { al_share = 100 }\n"
                + iff("check_variable = { al_share < mod1440_al_fill }", (
                    setv("mod1440_al_fill", "al_share") + setv("mod1440_al_wk", 1)
                    + setv("mod1440_al_wpic", "token:" + sprite) + setv("mod1440_al_wcls", ar_scale(width, height, AR_WORST_BOX))
                    + setv("mod1440_al_wkind", "token:" + kind) + setv("mod1440_al_whave", "al_h") + setv("mod1440_al_wneed", "al_t")))
                + "mod1440_ar_held = yes\n"))
        source = "the game's own kinds" if not states else "the kinds of a playset with %d states" % states
        tables += ("\n# Army Readiness: %s (%d), for the country in scope: the figures of the equipment, and the list\n"
                   "# while no army is chosen (ar_listing = 1).\n" % (source, len(rows))
                   + block("mod1440_ar_kinds_%d" % m, setv("mod1440_ar_kinds", len(rows)) + kinds)
                   + "\n# Army Readiness: %s, for the list of the chosen army mod1440_ar_sel of the country in scope.\n" % source
                   + block("mod1440_ar_akinds_%d" % m, army)
                   + "\n# Army Readiness: the worst equipped kind of %s, and al_have and al_need, in the scope of a general.\n" % source
                   + block("mod1440_ar_worst_%d" % m, worst))

    def pick(effect):
        """The effect of the table of the loaded map (the temporary ar_map); the game's own otherwise."""
        if len(AR_TABLES) == 1:
            return "%s_0 = yes\n" % effect
        out = ""
        for m in range(1, len(AR_TABLES)):
            out += iff("check_variable = { ar_map = %d }" % m, "%s_%d = yes\n" % (effect, m), "if" if m == 1 else "else_if")
        return out + els("%s_0 = yes\n" % effect)

    states = tmp("ar_map", 0)
    if len(AR_TABLES) > 1:
        # the map does not change in a game: its states are counted once per country
        states += iff("check_variable = { mod1440_ar_states = 0 }", tmp("ar_n", 0) + block("every_state", "add_to_temp_variable = { ar_n = 1 }\n")
                      + setv("mod1440_ar_states", "ar_n"))
        states += "".join(iff("check_variable = { mod1440_ar_states = %d }" % n, tmp("ar_map", m)) for m, (n, _rows) in enumerate(AR_TABLES) if m)

    # A kind: its share, what is short and whether the stock can fill it, from ar_s (stock), ar_f (in the field) and
    # ar_d (needed). A share is worked out as have / need * 100, dividing first: the product of a large stock and
    # 100 is more than a script number is sure to hold.
    calc = (tmp("ar_fill", 0) + tmp("ar_short", 0) + tmp("ar_red", 0) + tmp("ar_key", 0)
            + iff("check_variable = { ar_d > 0 }", (
                tmp("ar_fill", "ar_f") + "divide_temp_variable = { ar_fill = ar_d }\nmultiply_temp_variable = { ar_fill = 100 }\n"
                + iff("check_variable = { ar_fill > 100 }", tmp("ar_fill", 100))
                + tmp("ar_short", "ar_d") + "subtract_from_temp_variable = { ar_short = ar_f }\n"
                + iff("check_variable = { ar_short < 0 }", tmp("ar_short", 0))
                # A text cuts the fraction of a number off, and equipment in the field has one: the gap is
                # rounded up, so that it is what "Needed" less "In the field" gives on the page (X65).
                + tmp("ar_whole", "ar_short") + "round_temp_variable = ar_whole\n"
                + iff("check_variable = { var = ar_whole value = ar_short compare = less_than }", "add_to_temp_variable = { ar_whole = 1 }\n")
                + tmp("ar_short", "ar_whole")
                + iff("check_variable = { ar_short > 0 } check_variable = { var = ar_s value = ar_short compare = less_than }", tmp("ar_red", 1))
                # the key of the first order: the worse equipped, the higher; a kind only in stock comes after them all
                + tmp("ar_key", 200) + "subtract_from_temp_variable = { ar_key = ar_fill }\n")))
    add = "".join("add_to_array = { mod1440_ar_u_%s = ar_%s }\n" % (a, v) for a, v in (
        ("kind", "tok"), ("pic", "pic"), ("cls", "cls"), ("stock", "s"), ("field", "f"), ("need", "d"),
        ("short", "short"), ("fill", "fill"), ("red", "red"), ("key", "key")))
    # The figures of the head: the pieces held of what is needed, in thousands (a sum of every kind of a large
    # army is more than a script number holds), and the kinds short and those the stock cannot fill.
    tally = (tmp("ar_t", "ar_f") + iff("check_variable = { ar_t > ar_d }", tmp("ar_t", "ar_d"))
             + "divide_temp_variable = { ar_t = 1000 }\nadd_to_temp_variable = { ar_have_k = ar_t }\n"
             + tmp("ar_t", "ar_d") + "divide_temp_variable = { ar_t = 1000 }\nadd_to_temp_variable = { ar_need_k = ar_t }\n"
             + iff("check_variable = { ar_short > 0 }", "add_to_temp_variable = { ar_ks = 1 }\n")
             + iff("check_variable = { ar_red = 1 }", "add_to_temp_variable = { ar_kr = 1 }\n"))
    held = (iff("check_variable = { al_h > al_t }", tmp("al_h", "al_t"))
            + "divide_temp_variable = { al_h = 1000 }\nadd_to_temp_variable = { al_have = al_h }\n"
            + "divide_temp_variable = { al_t = 1000 }\nadd_to_temp_variable = { al_need = al_t }\n")

    # The list: the kinds of the country or of the chosen army, then the order of the chosen column
    unsorted = "".join("clear_array = mod1440_ar_u_%s\n" % a for a in AR_ARRAYS if a != "odd") + "clear_array = mod1440_ar_u_key\n"
    listing_script = (
        "mod1440_ar_map = yes\n" + unsorted
        + tmp("ar_listing", 1) + iff(is_one("mod1440_ar_has_sel"), tmp("ar_listing", 0))
        + tmp("ar_have_k", 0) + tmp("ar_need_k", 0) + tmp("ar_ks", 0) + tmp("ar_kr", 0)
        + pick("mod1440_ar_kinds")
        + setv("mod1440_ar_eqn", "ar_need_k") + setv("mod1440_ar_eqf", 0)
        + iff("check_variable = { ar_need_k > 0 }", setv("mod1440_ar_eqf", "ar_have_k") + "divide_variable = { mod1440_ar_eqf = ar_need_k }\n"
              + "multiply_variable = { mod1440_ar_eqf = 100 }\nclamp_variable = { var = mod1440_ar_eqf min = 0 max = 100 }\n")
        + setv("mod1440_ar_kshort", "ar_ks") + setv("mod1440_ar_kred", "ar_kr")
        + iff(is_one("mod1440_ar_has_sel"), pick("mod1440_ar_akinds"))
        + "mod1440_ar_eq_sort = yes\n")

    def eq_value(n, key):
        if key == "kind":
            return tmp("ar_v", "mod1440_ar_u_key^ar_i")
        if key == "fill":       # a kind only in stock comes after every kind that is needed
            return tmp("ar_v", 101) + iff("check_variable = { mod1440_ar_u_need^ar_i > 0 }", tmp("ar_v", "mod1440_ar_u_fill^ar_i"))
        return tmp("ar_v", "mod1440_ar_u_%s^ar_i" % key)
    setup, order = ar_sort("mod1440_ar_eq_by", "mod1440_ar_eq_up", "mod1440_ar_eq_asc", "mod1440_ar_eq_arrow_x", AR_EQ_COLS,
                           "mod1440_ar_u_key^num", eq_value, "mod1440_ar_eq_keys",
                           "".join("add_to_array = { mod1440_ar_%s = mod1440_ar_u_%s^ar_at }\n" % (a, a) for a in AR_ARRAYS if a != "odd")
                           + "add_to_array = { mod1440_ar_odd = ar_par }\n" + iff("check_variable = { ar_par = 0 }", tmp("ar_par", 1)) + els(tmp("ar_par", 0)))
    eq_sort = "".join("clear_array = mod1440_ar_%s\n" % a for a in AR_ARRAYS) + tmp("ar_par", 0) + setup + order

    def al_value(n, key):
        return tmp("ar_v", "mod1440_ar_lk_%s^ar_i" % key)
    setup, order = ar_sort("mod1440_ar_al_by", "mod1440_ar_al_up", "mod1440_ar_al_asc", "mod1440_ar_al_arrow_x",
                           AR_AL_COLS,
                           "mod1440_ar_l_game^num", lambda n, key: tmp("ar_v", 0) if key == "cmd" else al_value(n, key),
                           "mod1440_ar_al_keys", "add_to_array = { mod1440_ar_leaders = mod1440_ar_l_game^ar_at }\n")
    al_sort = ("clear_array = mod1440_ar_leaders\n" + setup
               + iff("check_variable = { mod1440_ar_al_by = 0 }", block("for_each_loop", "array = mod1440_ar_l_game\nvalue = ar_l\nadd_to_array = { mod1440_ar_leaders = ar_l }\n"))
               + els(order))
    # the marks of the rows: the band of every second row, and the light band of the chosen army
    marks = (tmp("ar_sel", -1) + iff(is_one("mod1440_ar_has_sel"), tmp("ar_sel", "mod1440_ar_sel")) + tmp("al_odd", 0)
             + block("for_each_loop", "array = mod1440_ar_leaders\nvalue = ar_l\n" + block("var:ar_l", (
                 setv("mod1440_al_odd", "al_odd") + setv("mod1440_al_pick", 0)
                 + iff("check_variable = { ar_l = ar_sel }", setv("mod1440_al_pick", 1))))
                 + iff("check_variable = { al_odd = 0 }", tmp("al_odd", 1)) + els(tmp("al_odd", 0))))
    # a click on a row (of_me: the commander): choose his army, or let it go when it was the chosen one
    choose = (iff("check_variable = { mod1440_ar_has_sel = 1 } check_variable = { mod1440_ar_sel = of_me }", setv("mod1440_ar_has_sel", 0))
              + block("else_if", "limit = { NOT = { check_variable = { of_me = 0 } } }\n" + setv("mod1440_ar_sel", "of_me") + setv("mod1440_ar_has_sel", 1))
              + "mod1440_ar_list = yes\nmod1440_ar_marks = yes\n")

    # The fuel bar, the share of what can be stored
    fuel = setv("mod1440_ar_fuel", 0) + iff("check_variable = { max_fuel_k > 0 }", (
        setv("mod1440_ar_fuel", "fuel_k") + "divide_variable = { mod1440_ar_fuel = max_fuel_k }\nmultiply_variable = { mod1440_ar_fuel = 100 }\n"
        + "clamp_variable = { var = mod1440_ar_fuel min = 0 max = 100 }\n"))

    # Where an army stands, for a player's country: the states where its divisions can be (controlled by the
    # country, by a country of its faction or by an enemy), each read once per commander with num_units_in_state.
    # D2 fix round 1: built as the Records find the general on the spot (SCR-021, mod1440_of_best): the state in a
    # temporary variable, then the country's own loop over its leaders, and the states from controlled_states as
    # the States page takes them. The first build kept the states in a temporary array and looped over it in
    # each leader's scope; in the game it found no state for a general whose 30 divisions stood in Germany.
    where = iff("check_variable = { ar_player = 1 }", (
        tmp("ar_me", "THIS")
        + block("for_each_scope_loop", "array = controlled_states\nmod1440_ar_here = yes\n")
        + block("every_country", "limit = { NOT = { tag = PREV } OR = { is_in_faction_with = PREV has_war_with = PREV } }\n"
                + block("for_each_scope_loop", "array = controlled_states\nmod1440_ar_here = yes\n"))))
    here = (tmp("ar_st", "THIS") + block("var:ar_me", block("every_army_leader", (
        "limit = { check_variable = { num_units > 0 } }\n" + tmp("al_n", "num_units_in_state@var:ar_st")
        + iff("check_variable = { al_n > mod1440_al_lcnt }", setv("mod1440_al_lcnt", "al_n") + setv("mod1440_al_loc", "ar_st"))))))
    location = setv("mod1440_al_loc", 0) + setv("mod1440_al_lcnt", 0)

    # The game's own loop over the leaders: its array army_leaders holds nothing in the place of a general whose
    # command came by an effect, and neither does THIS. mod1440_of_me gives what a variable can hold of him
    # (tools/build_records.py, places()).
    general = (setv("mod1440_al_fill", 101) + setv("mod1440_al_wk", 0) + tmp("al_have", 0) + tmp("al_need", 0) + pick("mod1440_ar_worst")
               + iff("check_variable = { mod1440_al_fill > 100 }", setv("mod1440_al_fill", 100))
               + setv("mod1440_al_eq", 100) + iff("check_variable = { al_need > 0 }", (
                   setv("mod1440_al_eq", "al_have") + "divide_variable = { mod1440_al_eq = al_need }\nmultiply_variable = { mod1440_al_eq = 100 }\n"
                   + "clamp_variable = { var = mod1440_al_eq min = 0 max = 100 }\n"))
               + setv("mod1440_al_hq", "state_deployed")
               + setv("mod1440_al_plan", "avg_unit_planning_ratio") + "multiply_variable = { mod1440_al_plan = 100 }\n"
               + "clamp_variable = { var = mod1440_al_plan min = 0 max = 100 }\n"
               # Oth: the divisions none of the four kinds counts (cavalry, artillery, rocket, special)
               + setv("mod1440_al_oth", "num_units")
               + "".join("subtract_from_variable = { mod1440_al_oth = %s }\n" % v for v in ("num_infantry", "num_armored", "num_motorized", "num_mechanized"))
               + "clamp_variable = { var = mod1440_al_oth min = 0 max = 10000 }\n"
               + location
               # E7: no portrait is looked up here any more: the row draws the game's own (ar_row_face)
               + iff("check_variable = { of_me = ar_sel }", tmp("ar_found", 1))
               + "add_to_array = { PREV.mod1440_ar_l_game = of_me }\n"
               + "".join("add_to_array = { PREV.mod1440_ar_lk_%s = %s }\n" % (k, v) for k, v in AR_AL_KEYS.items()))
    # a player's record first learns whether the numbers of text keys have moved since the save was made: the
    # portraits looked up before are stale then (fix round 1; this runs before the Records' daily round)
    leaders = (iff("check_variable = { ar_player = 1 } check_variable = { mod1440_ev_begun = 1 }", "mod1440_tk_check = yes\n")
               + "mod1440_of_refs = yes\n"
               + tmp("ar_sel", -1) + iff(is_one("mod1440_ar_has_sel"), tmp("ar_sel", "mod1440_ar_sel"))
               + tmp("ar_found", 0) + tmp("ar_fight", 0) + tmp("ar_led", 0)
               + "clear_array = mod1440_ar_l_game\n" + "".join("clear_array = mod1440_ar_lk_%s\n" % k for k in AR_AL_KEYS)
               + block("every_army_leader", (
                   "limit = { check_variable = { num_units > 0 } }\n"
                   # Fighting and Without a commander: the commanders of single armies, so that an army group's
                   # divisions are not counted twice
                   + iff("is_leading_army = yes", "add_to_temp_variable = { ar_fight = num_units_in_combat }\nadd_to_temp_variable = { ar_led = num_units }\n")
                   + "mod1440_of_me = yes\n"
                   + iff("NOT = { check_variable = { of_me = 0 } }", general)))
               # an army that no longer has troops is let go
               + iff("check_variable = { mod1440_ar_has_sel = 1 } check_variable = { ar_found = 0 }", setv("mod1440_ar_has_sel", 0))
               + setv("mod1440_ar_fight", "ar_fight") + setv("mod1440_ar_nocmd", "num_divisions")
               + "subtract_from_variable = { mod1440_ar_nocmd = ar_led }\nclamp_variable = { var = mod1440_ar_nocmd min = 0 max = 100000 }\n"
               + where
               + "mod1440_ar_al_sort = yes\nmod1440_ar_marks = yes\n")
    count = (
        "# Army Readiness: the counted figures, the list of generals with troops and where they stand, and the\n"
        "# equipment list, for the country in scope. Runs at the start of a game for every country, each day for a\n"
        "# player, and on a click.\n"
        + block("mod1440_ar_count",
                tmp("ar_player", 0) + iff("is_ai = no", tmp("ar_player", 1))
                # the frame of the Army names toggle (1 off, 2 on), also for a save that has no such variable
                + setv("mod1440_ar_names_fr", 1) + iff(is_one("mod1440_ar_names"), setv("mod1440_ar_names_fr", 2))
                + "set_variable = { mod1440_ar_low_str = 0 }\nset_variable = { mod1440_ar_low_org = 0 }\n"
                + block("every_country_division", "limit = { unit_strength < 0.75 }\nadd_to_variable = { PREV.mod1440_ar_low_str = 1 }\n")
                + block("every_country_division", "limit = { unit_organization < 0.5 }\nadd_to_variable = { PREV.mod1440_ar_low_org = 1 }\n")
                + fuel + "mod1440_ar_map = yes\n" + leaders + "mod1440_ar_list = yes\n"
                + "set_variable = { mod1440_ar_counted = global.date }\n")
        + "\n# Army Readiness: for the state in scope, the commanders with troops of the country ar_me; each keeps the\n"
        "# state where he has the most divisions (mod1440_al_loc, and their number mod1440_al_lcnt).\n"
        + block("mod1440_ar_here", here)
        + "\n# Army Readiness: the table of kinds of the loaded map, in the temporary ar_map (0: the game's own).\n"
        + block("mod1440_ar_map", states)
        + "\n# Army Readiness: the equipment list of the country in scope, from its stock and its divisions, or from the\n"
        "# chosen army's, with the figures of the equipment; then the order of the chosen column.\n"
        + block("mod1440_ar_list", listing_script)
        + "\n# Army Readiness: a kind in use, from ar_s (stock), ar_f (in the field) and ar_d (needed).\n"
        + block("mod1440_ar_calc", calc)
        + "\n# Army Readiness: a kind into the unsorted arrays of the list, with ar_tok, ar_pic and ar_cls.\n"
        + block("mod1440_ar_add", add)
        + "\n# Army Readiness: a kind the country's divisions need, into the figures of the head.\n"
        + block("mod1440_ar_tally", tally)
        + "\n# Army Readiness: a kind a general's divisions need (al_h of al_t) into al_have and al_need, in thousands.\n"
        + block("mod1440_ar_held", held)
        + "\n# Army Readiness: the equipment list in the order of its chosen column (mod1440_ar_eq_by, _up), from the\n"
        "# unsorted arrays of the last list. Counts nothing.\n"
        + block("mod1440_ar_eq_sort", eq_sort)
        + "\n# Army Readiness: the armies in the order of their chosen column (mod1440_ar_al_by, _up), from the game's\n"
        "# order and the keys of the last count. Counts nothing.\n"
        + block("mod1440_ar_al_sort", al_sort)
        + "\n# Army Readiness: the band of every second army row and the light band of the chosen army.\n"
        + block("mod1440_ar_marks", marks)
        + "\n# Army Readiness: a click on the row of the commander of_me, for the country in scope.\n"
        + block("mod1440_ar_choose", choose)
        + tables)
    return count


# The scene of Army Readiness (tools/scenes/army_readiness.json): the samples of the design's mock-ups
# (scratch/phases/D2/mock_d2r2.py), a German army of 1939 at war. Rows hold one text per row in drawing order;
# "" draws nothing, for the twin script hides in that row.
DASH = "§g-§!"
AR_SAMPLE_ARMIES = [
    # name, skill, levels, troops, HQ, div, (inf, arm, mot, mech, oth), fighting (att, def), planning, equipped, worst %
    ("Gerd von Rundstedt", 4, (5, 3, 5, 2), "Schlesien", "Schlesien", 36, (30, 2, 4, 0, 0), None, 100, 92, 72),
    ("Fedor von Bock", 4, (5, 3, 5, 3), "Pommern", "Pommern", 30, (24, 3, 3, 0, 0), None, 85, 88, 67),
    ("Heinz Guderian", 4, (5, 2, 4, 3), "Westpreussen", "Ostpreussen", 8, (2, 4, 2, 0, 0), (3, 2, 1), 42, 89, 61),
    ("Erich von Manstein", 4, (4, 3, 5, 2), "Schlesien", "", 12, (11, 0, 1, 0, 0), None, 100, 95, 86),
    ("Wilhelm Ritter von Leeb", 3, (3, 3, 2, 2), "Westfalen", "Westfalen", 14, (14, 0, 0, 0, 0), None, 64, 96, 84),
    ("Günther von Kluge", 3, (5, 3, 4, 3), "Brandenburg", "Brandenburg", 12, (11, 0, 1, 0, 0), None, 100, 97, 91),
    ("Johannes Blaskowitz", 3, (2, 3, 3, 2), "Sachsen", "", 10, (10, 0, 0, 0, 0), None, 90, 98, 93),
    ("Erwin von Witzleben", 3, (4, 3, 2, 4), "Rheinland", "Rheinland", 8, (6, 0, 0, 0, 2), None, 30, 98, 95),
    ("Wilhelm List", 3, (3, 3, 2, 2), "Ostmark", "Ostmark", 6, (4, 0, 0, 0, 2), None, 100, 99, 97),
    ("Kurt von Hammerstein-Equord", 2, (2, 2, 2, 1), "Bayern", "", 4, (4, 0, 0, 0, 0), None, 0, 100, 100),
]
AR_SAMPLE_NAMES = ["Heeresgruppe Süd", "Heeresgruppe Nord", "2. Panzerarmee", "11. Armee", "Army 5",
                   "4. Armee", "8. Armee", "1. Armee", "Army 9", "Armeeabteilung Kempf"]
AR_SAMPLE_GROUPS = {0, 1}       # field marshals leading an army group: Div in grey
AR_SAMPLE_CHOSEN = 2            # Guderian, in the state "chosen"
# (kind, stock, in the field, needed): the country, and Guderian's army against the country's stock
AR_SAMPLE_KINDS = [("light_tank_chassis", 0, 1450, 2160), ("support_equipment", 40, 2280, 3150), ("artillery_equipment", 120, 3790, 4420),
                   ("infantry_equipment", 21400, 79100, 86400), ("motorized_equipment", 1200, 2900, 3100), ("anti_tank_equipment", 310, 1080, 1080),
                   ("armored_car_equipment", 0, 288, 288), ("anti_air_equipment", 140, 0, 0), ("medium_tank_chassis", 12, 0, 0)]
AR_SAMPLE_ARMY = [("light_tank_chassis", 0, 620, 1010), ("support_equipment", 40, 118, 160), ("motorized_equipment", 1200, 1340, 1460),
                  ("infantry_equipment", 21400, 3420, 3600), ("artillery_equipment", 120, 288, 288), ("armored_car_equipment", 0, 96, 96)]


def ar_eq_samples(kinds):
    out = {"ar_er_name": [], "ar_er_stock": [], "ar_er_stock_shared": [], "ar_er_field": [], "ar_er_field_short": [],
           "ar_er_need": [], "ar_er_short": [], "ar_er_short_covered": [], "ar_er_pct": []}
    for kind, stock, field, need in kinds:
        short = max(0, need - field)
        out["ar_er_name"].append("$%s$" % kind)
        out["ar_er_stock"].append(str(stock))
        out["ar_er_stock_shared"].append("§g%d§!" % stock)
        out["ar_er_field"].append("" if short else str(field))
        out["ar_er_field_short"].append("§R%d§!" % field if short else "")
        out["ar_er_need"].append(str(need))
        out["ar_er_short"].append("§R%d§!" % short if short and stock < short else "")
        out["ar_er_short_covered"].append("§O%d§!" % short if short and stock >= short else "")
        out["ar_er_pct"].append("%d%%" % (field * 100 // need) if need else "")
    return out


def ar_row_samples():
    out = {}

    def put(widget, value):
        out.setdefault(widget, []).append(value)
    for n, (name, skill, levels, troops, hq, div, kinds, fight, plan, equip, worst) in enumerate(AR_SAMPLE_ARMIES):
        put("ar_row_name", "§Y%s§!" % name)
        put("ar_row_skill", str(skill))
        put("ar_row_army", AR_SAMPLE_NAMES[n])
        for (key, _variable, _sprite), level in zip(AR_LEVELS, levels):
            put("ar_row_%s" % key, str(level))
        put("ar_row_loc_name", troops)
        put("ar_row_hq", "§gHQ§! %s" % hq if hq else "")
        put("ar_row_hq_none", "" if hq else "§gHQ not deployed§!")
        group = n in AR_SAMPLE_GROUPS
        put("ar_row_div", "" if group else str(div))
        put("ar_row_div_group", "§g%d§!" % div if group else "")
        for (key, _variable), value in zip(AR_KINDS_ROW, kinds):
            put("ar_row_%s" % key, str(value) if value else "")
            put("ar_row_%s_none" % key, "" if value else DASH)
        put("ar_row_fight", "§Y%d§!" % fight[0] if fight else "")
        put("ar_row_split", "§g%d att %d def§!" % fight[1:] if fight else "")
        put("ar_row_fight_none", "" if fight else DASH)
        put("ar_row_plan", "%d%%" % plan)
        put("ar_row_eq", "%d%%" % equip if equip >= LOW else "")
        put("ar_row_eq_low", "§O%d%%§!" % equip if equip < LOW else "")
        put("ar_row_pct", "%d%%" % worst if worst >= LOW else "")
        put("ar_row_pct_low", "§O%d%%§!" % worst if worst < LOW else "")
    return out


def ar_scene():
    pictures_eq = ["ar_er_pic_%d" % n for n in range(len(AR_SCALES)) if n != ar_scale(81, 23, AR_PIC_BOX)]
    pictures_row = ["ar_row_worst_%d" % n for n in range(len(AR_SCALES)) if n != ar_scale(81, 23, AR_WORST_BOX)]
    zeros = ["ar_%s_z" % name for title, rows in AR_FIGURES for name, label, value, tip, zero, bar in rows if zero]
    head_hide = ["ar_full", "ar_eq_field_low", "ar_fuel_low"] + zeros
    body_hide = ["ar_eq_none", "ar_al_none", "ar_al_caption_one", "ar_eq_caption_army", "ar_eq_all", "ar_eh_field_army", "ar_eq_arrow_up", "ar_al_arrow_up"]
    eq_hide = ["ar_er_low", "ar_er_stock_shared"] + pictures_eq
    row_hide = (["ar_row_pick", "ar_row_army",
                 "ar_row_loc_none", "ar_row_eq_lowbar"] + pictures_row)
    names_hide = [h for h in row_hide if h != "ar_row_army"]
    # with Army names on: the army's name under each commander, none under a field marshal of an army group
    names_samples = {"ar_row_army": ["" if n in AR_SAMPLE_GROUPS else name for n, name in enumerate(AR_SAMPLE_NAMES)]}
    body_states = ["", "sorted", "pick", "chosen", "names"]
    samples_head = {"ar_mp_free": "412K", "ar_mp_training": "38.4K", "ar_mp_army": "1310K", "ar_mp_garrison": "§Y128.8K§!",
                    "ar_casualties": "61.2K", "ar_divisions": "172", "ar_fighting": "§Y3§!", "ar_low_str": "§Y6§!",
                    "ar_low_org": "§Y2§!", "ar_no_cmd": "§Y38§!", "ar_eq_field": "91%", "ar_k_short": "§O5§!",
                    "ar_k_red": "§R2§!", "ar_fuel": "297K of 371K", "ar_xp": "37"}
    chosen_name = AR_SAMPLE_ARMIES[AR_SAMPLE_CHOSEN][0]
    stock_arrow = [c for c in AR_EQ_COLS if c[0] == "stock"][0]
    return {
        "phase": "D2", "file": "mod1440_army_readiness.gui", "screenshot": "reference/vanilla/recruit_deploy.jpg",
        "windows": [
            {"name": "mod1440_army_readiness", "at": [AR_X, AR_Y], "freeWindow": True, "hide": head_hide,
             "drawIn": body_states + ["summary"],
             "_note": "The head: title strip and three tables of figures, the whole page in its short form. A window of its own at its screen position (D8, X7). Hidden here: the twin of a value that script shows in its place (a plain 0, a dash, an orange bar, the Full button of the short form)."},
            {"name": "mod1440_army_readiness_body", "at": [AR_X, AR_BODY_Y], "freeWindow": True, "drawIn": body_states,
             "rows": {"ar_eq_grid": AR_EQ_ROWS, "ar_al_grid": AR_AL_ROWS},
             "listRows": {"ar_eq_grid": "mod1440_army_readiness_eqrow", "ar_al_grid": "mod1440_army_readiness_row"},
             "hide": body_hide,
             "_note": "The body, under the head while the page is in its full form: the equipment and the armies, sorted in their first orders (the arrows on Kind and Commander), no army chosen."},
            {"name": "mod1440_army_readiness_eqrow", "skip": True, "hide": eq_hide, "only": {"ar_er_stripe": [1, 3, 5, 7]},
             "_note": "A row per kind in use. The renderer draws one sprite and one fill for every row: in the game each row has the picture of its kind at its scale, and a bar of its share (orange below 75%)."},
            {"name": "mod1440_army_readiness_row", "skip": True, "hide": row_hide, "only": {"ar_row_stripe": [1, 3, 5, 7, 9]},
             "_note": "A row per commander with troops, Army names off (its default; the state names shows them). Twins script shows per row stand in the samples, with an empty text where the other one shows. The portrait is the renderer's unknown leader: in the game each row draws its commander's own face (E7, image = portrait)."},
            {"name": "mod1440_army_readiness_handle", "at": [HANDLE_X - 6, HANDLE_Y + 78], "drawIn": ["closed"],
             "_note": "Docked to Recruit & Deploy (the tab's corner at -6,78), shown only while the page is closed: the state closed."},
        ],
        "samples": {
            "mod1440_army_readiness": samples_head,
            "mod1440_army_readiness_body": {
                "ar_eq_caption": "§gAll armies: 9 of %d kinds in use. Click a head to sort, an army below to see its own.§!" % len(AR_KINDS),
                "ar_eq_caption_army": "§gThe army of§! §Y%s§!§g: %d kinds it needs§!" % (chosen_name, len(AR_SAMPLE_ARMY)),
                "ar_al_caption": "§g12 commanders with troops. Click one for his army's equipment, right-click for the map.§!"},
            "mod1440_army_readiness_eqrow": ar_eq_samples(AR_SAMPLE_KINDS),
            "mod1440_army_readiness_row": ar_row_samples(),
        },
        "setup": [{"move": "open_recruit_deploy"},
                  {"clickWidget": "mod1440_army_readiness_handle/ar_unfold", "state": "closed", "wait": 1.5,
                   "_note": "the page is closed until asked for (D8); the click also counts"}],
        # the equipment sorted by In stock; a click on the first army row (it chooses an army only where one has
        # a commander: assign a general first, see the checklist); Summary
        "captures": [
            {"name": "sorted", "steps": [{"clickWidget": "mod1440_army_readiness_body/ar_eh_stock", "wait": 1.0}],
             "place": {"mod1440_army_readiness_body": {"ar_eq_arrow_down": [14 + stock_arrow[2] + stock_arrow[3] - ARROW_DX, 36 + ARROW_DY]}},
             "_note": "In stock sorted largest first: the arrow on its plate (the renderer moves it as script does; the rows keep the samples' order)."},
            # the row button's centre lies in the Location button (row x 316 to 446): aim 300 px left of it, at the
            # commander's name (row x 144), as fix round 4's launch found
            {"name": "pick", "steps": [{"clickWidget": "mod1440_army_readiness_row/ar_row_hit#0", "offset": [-300, 0], "wait": 1.2}],
             "_note": "Chooses the first army; in the clean state Army 1 has no commander and the click meets an empty list. The renderer's picture of a chosen army is the state chosen."},
            {"name": "summary", "steps": [{"clickWidget": "mod1440_army_readiness/ar_small", "wait": 1.0}],
             "hide": {"mod1440_army_readiness": ["ar_small"] + head_hide[1:]},
             "_note": "Summary: the head alone, the map free under it."},
        ],
        "teardown": [{"clickWidget": "mod1440_army_readiness/ar_full", "state": "summary", "wait": 1.0},
                     {"clickWidget": "mod1440_army_readiness_body/ar_eh_kind", "wait": 0.8},
                     {"clickWidget": "mod1440_army_readiness_body/ar_eq_all", "state": "chosen", "wait": 0.8,
                      "_note": "lets a chosen army go; where none was chosen the click meets the card's caption"},
                     {"key": "shift+m", "wait": 0.8, "_note": "close it again: the page remembers per country whether it is open"}],
        "states": [
            {"name": "chosen", "_note": "Guderian's army chosen (figure chosen of the design): his row on the light band, the equipment card with his army's kinds, In the army against Needed, the country's stock in grey, All armies.",
             "hide": {"mod1440_army_readiness_body": [h for h in body_hide if h not in ("ar_eq_caption_army", "ar_eq_all", "ar_eh_field_army")] + ["ar_eq_caption", "ar_eh_field_l"],
                      "mod1440_army_readiness_eqrow": [h for h in eq_hide if h != "ar_er_stock_shared"] + ["ar_er_stock"],
                      "mod1440_army_readiness_row": [h for h in names_hide if h != "ar_row_pick"]},
             "only": {"mod1440_army_readiness_row": {"ar_row_stripe": [1, 3, 5, 7, 9], "ar_row_pick": [AR_SAMPLE_CHOSEN]},
                      "mod1440_army_readiness_eqrow": {"ar_er_stripe": [1, 3, 5]}},
             "frames": {"mod1440_army_readiness_body": {"ar_names": 2}},
             "rows": {"ar_eq_grid": len(AR_SAMPLE_ARMY)},
             "samples": {"mod1440_army_readiness_eqrow": ar_eq_samples(AR_SAMPLE_ARMY), "mod1440_army_readiness_row": names_samples}},
            {"name": "names", "_note": "Army names on, on the locally patched game [SCR-078]: the army's name under each commander of a single army; the toggle on its second frame. Off (the default, and what an unpatched game should keep) is the scene's own state.",
             "hide": {"mod1440_army_readiness_row": names_hide},
             "frames": {"mod1440_army_readiness_body": {"ar_names": 2}},
             "samples": {"mod1440_army_readiness_row": names_samples}},
            {"name": "closed", "_note": "The tab with the page closed (the default, D8): the Readiness handle in the title strip at screen 353,90, no page."},
        ],
        "expect": ["mod1440_army_readiness/ar_fold", "mod1440_army_readiness/ar_count", "mod1440_army_readiness/ar_small"],
        "crop": [1240, 70, 1000, 1230],
        "manual": [
            "Army names on, on the locally patched game: the name of his army under each commander (Army 1, or the name you gave it); a field marshal of an army group has none; on an unpatched game the toggle stays off",
            "A field marshal leading an army group (two armies under him): his Div in grey, and Fighting and Without a commander not counting his divisions twice; a 1936 start has none",
            "The row's tooltip: entrenchment, readiness for the plan and the average combat progress read as shares; tooltips of the plates and figures",
            "After some days at war: Fighting, Casualties and Location against the map and the war overview",
        ],
        "checklist": AR_CHECKLIST,
    }


# --- D8 --- the free page (scratch/phases/D8/design.json, openInGame); the first runs over the vanilla windows
AR_CHECKLIST_D8 = [
    "D8, run 1 over the VANILLA Recruit & Deploy window (a scratch copy of the mod without interface/zz_1440p_recruit_deploy.gui's clipping = no lines, or without the override): the tab opens with no page and the Readiness handle in the vanilla title strip at screen 353,90 (92x34, 'Readiness', between the title, which ends at 291, and the close button at 491), drawn whole and not cut off; its tooltip 'Army Readiness: your manpower, divisions, equipment and commanders' with the game's Shift+M",
    "D8, over the vanilla window: a click on the handle opens the page at once, the head at 1250,78 (975x244) and the body at 1250,322 (975x966), drawn whole with 336 px of map between the vanilla templates panel (ends at 914) and the page; every button of the page answers a click (Count again, Summary, a column head, an army row, the close button); the lists filled",
    "D8: Summary leaves the head alone at 1250,78 and the map under it free (no body, no frame left); Full brings the body back flush under the head at y 322 with no seam; both forms with the reworked panel as well (run 2, the mod as committed)",
    "D8: the handle is gone while the page is open; the close button (909,10 on the page), Shift+M and Escape each close the page and bring the handle back. Escape order: with the page open, the first Escape closes the page only (Recruit & Deploy stays), the second closes the tab",
    "D8: close Recruit & Deploy by its own button or its tab key while the page is open: the page stays on the screen over the map; Shift+M and Escape still close it; open it again, close the tab, open Politics and its Figures handle (and once Shift+M there): Army Readiness closes and only National Figures is open",
    "D8: a save of the build before D8 with Army Readiness open (mod1440_ar_folded 0) loads with the page closed and the handle shown; the handle opens it and the count runs (Counted <today> in the title strip)",
]
# --- end D8 ---

AR_CHECKLIST = AR_CHECKLIST_D8 + [
    "The head: three tables, Manpower, Army and Stocks, five rows each on alternating bands, labels at the left and values at the right edge of each band; Count again, Summary and the close button in the title strip as before",
    "Manpower: Free manpower against the top bar's manpower; In the army's tooltip names the navy and the air force; Casualties reads 0 in a 1936 start",
    "Army: Divisions 30 for Germany in 1936 (its tooltip 315 battalions); Fighting 0; Without a commander 30 while Army 1 has no commander (the army overview's divisions), 0 after a general is assigned and Count again pressed",
    "Stocks: Equipped in the field 100% with a full green bar, Kinds short 0, Stock cannot cover 0 for Germany in 1936; Fuel 297K of 371K as the top bar with its bar at that share; Army experience as the top bar",
    "Summary folds the page to the head with no seam; Full brings the equipment and the armies back; the close button, Shift+M and Escape close the page, the Readiness handle and Shift+M open it again in the form it was left in",
    "Equipment: a plate per column; a click on In stock sorts largest first with the arrow on its plate's corner, a second click turns the order (arrow up); Equipped sorts the lowest first (arrow up); Kind gives the first order back (arrow on Kind). Kind names stand in 240 px and none runs into In stock",
    "Assign a general to Army 1 (the army badge) and press Count again: his row shows his portrait, his name in yellow and his skill on a plate as on the badge, and attack, defence, planning and logistics as in his leader window",
    "That row: Div is the badge's division count; Inf, Arm, Mot, Mech and Oth add up to Div; Location names the state where most of Army 1 stands (the map) and a click on it moves the camera there; HQ not deployed under it, or the HQ's state once deployed",
    "Line 2 of the row: with Army names off (the default) it holds the four levels only. Click Army names beside the card's title: the button takes its chosen look, and on the locally patched game each commander of a single army gets his army's name there (Army 1, or a name given to it, also right after renaming); a field marshal of an army group gets none; an unpatched game would read Himself. Click it again: off",
    "Click the row: it takes the light band, the equipment card reads The army of <his name>: N kinds it needs, In the field becomes In the army, In stock turns grey, All armies shows; In the army against the sum of his divisions (division details); click the row again, or All armies, for the country",
    "Right-click the row: the camera moves to the Location state and the row is not chosen; a click on the Location button does the same",
    "Hover the row: the tooltip gives his name, entrenchment, readiness for the plan, battle plans, traits, the average combat progress, the other divisions and the worst kind with its numbers (Light Tank: 620 of 1010 style)",
    "Sort the armies by Div, Fighting, Planning, Equipped and Worst: the arrow follows and the chosen army keeps its light band after a sort and after Count again",
    "A general without a number (mod1440_chk_by_effect, then given an army; or a general of Add German Generals AI REWORK): listed with his values, chosen by a click, his equipment shown",
    "error.log: no line naming mod1440, no Could not find sprite type, no invalid scope line, also with the playset's 55 kinds",
]
# --- E7 --- the commanders' faces through the game (image = portrait, SGUI-053)
AR_CHECKLIST += [
    "E7 with Road to 56: each commander's row shows his own face, the same as on his army's badge and in his leader window: Keitel or Halder "
    "if given an army (texture files, the unknown leader before E7), the others as the game's commander picker; no row with the unknown leader "
    "unless the game shows him so",
    "E7: error.log has no line naming 'portrait', mod1440_p_officer or the on_startup line 'mod1440_pop_round: Invalid Scope'",
]
# --- end E7 ---


# ---------------------------------------------------------------- States (D3), docked to Construction

# One row per state the player controls, in a table card, and under it a band of four cards for the chosen
# state (redesign of 2026-10-16, scratch/redesign/d3-states). A column is (name, value of the state, width,
# head, tip, group): the head is ("text", caption), ("building", frame of GFX_buildings_strip) or ("resource",
# frame of GFX_resources_strip); the tip is a text of the game ("$key$") or of the mod; columns of one group
# stand together, with a gap to the next group. A resource is shown as the list effect's rounded copy of the
# state's number: "|0" cuts a fraction off and the state view rounds (Engine Facts X65).
# --- D10 --- the building columns 52 -> 46 and the resource columns 56 -> 54 make room for In a year (68) after People:
# the row stays 1414 and the page 1472 (scratch/phases/D10/layout.json). In a year sorts by the state's fall in a year
# (mod1440_pop_fall, the largest fall first) and shows its change (mod1440_pop_dy), both worked out in the monthly round.
ST_B_W, ST_R_W = 46, 54
STATE_COLUMNS = [
    ("free", "mod1440_st_free", 100, ("text", "Free"), "Free building slots for factories and the other buildings that share slots, counted when the list was made. The bar is the share of the slots that shared buildings already take; it counts the game's own shared buildings only, so a building another mod adds is not in it (the free number is the game's own).", "free"),
    ("infra", "infrastructure_level", ST_B_W, ("building", 3), "Infrastructure.", "build"),
    ("civ", "industrial_complex_level", ST_B_W, ("building", 1), "Civilian factories.", "build"),
    ("mil", "arms_factory_level", ST_B_W, ("building", 2), "Military factories.", "build"),
    ("dock", "building_level@dockyard", ST_B_W, ("building", 4), "Naval dockyards.", "build"),
    ("refinery", "building_level@synthetic_refinery", ST_B_W, ("building", 10), "Synthetic refineries.", "build"),
    ("silo", "building_level@fuel_silo", ST_B_W, ("building", 14), "Fuel silos.", "build"),
    ("air", "building_level@air_base", ST_B_W, ("building", 5), "Air base.", "build"),
    ("aa", "building_level@anti_air_building", ST_B_W, ("building", 9), "Anti-air.", "build"),
    ("radar", "building_level@radar_station", ST_B_W, ("building", 11), "Radar station.", "build"),
    ("oil", "mod1440_st_r_oil", ST_R_W, ("resource", 1), "Oil.", "res"),
    ("aluminium", "mod1440_st_r_aluminium", ST_R_W, ("resource", 2), "Aluminium.", "res"),
    ("rubber", "mod1440_st_r_rubber", ST_R_W, ("resource", 3), "Rubber.", "res"),
    ("tungsten", "mod1440_st_r_tungsten", ST_R_W, ("resource", 4), "Tungsten.", "res"),
    ("steel", "mod1440_st_r_steel", ST_R_W, ("resource", 5), "Steel.", "res"),
    ("chromium", "mod1440_st_r_chromium", ST_R_W, ("resource", 6), "Chromium.", "res"),
    ("coal", "mod1440_st_r_coal", ST_R_W, ("resource", 7), "Coal.", "res"),
    ("pop", "state_population_k", 84, ("text", "People"), "Population of the state, in thousands.", "people"),
    ("pop_year", "mod1440_pop_fall", 68, ("text", "In a year"), "The change of the state's population over the last twelve months, in percent: §Rred§! a fall, §Ggreen§! a rise. Written down on the first of each month; empty with fewer than thirteen months.", "people"),
    ("compliance", "compliance", 60, ("text", "Compl."), "Compliance, for a state that is not a core of yours.", "occ"),
    ("resistance", "resistance", 60, ("text", "Resist."), "Resistance, for a state that is not a core of yours.", "occ"),
]
STATE_GROUPS = [("free", "Slots"), ("build", "Buildings"), ("res", "Resources"), ("people", "Population"), ("occ", "Occupation")]
# the head icons of the narrower columns: the building strip at 0.6 from x+9 (was 12), the resources at 0.9 from x+15 (16)
ST_ICON_DX = {"building": 9, "resource": 15}
# --- end D10 ---
# The game's name of each building column, for damaged_building_level@ (the three with a variable of their own)
ST_BUILDING = {"infra": "infrastructure", "civ": "industrial_complex", "mil": "arms_factory", "dock": "dockyard",
               "refinery": "synthetic_refinery", "silo": "fuel_silo", "air": "air_base", "aa": "anti_air_building",
               "radar": "radar_station"}
# The game's buildings that take a shared slot (shares_slots = yes in common/buildings): the five the slots card
# names with their icon, and the others, counted together. A building another mod adds is not counted (rule 6).
ST_SHARED = [("civ", "industrial_complex", 1), ("mil", "arms_factory", 2), ("dock", "dockyard", 4),
             ("refinery", "synthetic_refinery", 10), ("silo", "fuel_silo", 14)]
ST_SHARED_OTHER = ["rocket_site", "nuclear_reactor", "nuclear_reactor_heavy_water", "commercial_nuclear_reactor",
                   "energy_infrastructure", "industrial_infrastructure", "mega_gun_emplacement", "stronghold_network"]
# The game's state categories (common/state_category); their names are text keys of the game
ST_CATEGORIES = ["megalopolis", "metropolis", "large_city", "city", "large_town", "town", "rural", "pastoral",
                 "wasteland", "enclave", "large_island", "small_island", "tiny_island"]
ST_RESOURCES = ["oil", "aluminium", "rubber", "tungsten", "steel", "chromium", "coal"]

# From the corner of the construction panel (screen -9,78), whose building column ends at x 700.
ST_X, ST_Y = 712, 0
ST_NAME = 200
ST_GAP = 10                     # between the groups of columns
ST_FREE_BAR = 62                # the slot bar takes the first 62 px of the free column (6 margin, 56 bar)


def state_layout():
    """The left edge of every column in a row, the width of a row, and what each group spans."""
    x, last = ST_NAME, None
    edges, spans = {}, {}
    for name, value, width, head, tip, group in STATE_COLUMNS:
        if group != last:
            x += ST_GAP
            last = group
        edges[name] = x
        spans[group] = (spans.get(group, (x, x))[0], x + width)
        x += width
    return edges, x, spans


ST_EDGE, ST_ROWS_W, ST_SPAN = state_layout()
ST_W = 14 + ST_ROWS_W + 30 + 14                             # the page: margins, rows, scrollbar
ST_H = 1210                                                 # ends above the army portraits of the bottom bar
ST_ROW = 30
ST_ROWS = 26                                                # rows on the screen: Germany's 24 fit
# The cards stand 7 px inside the page: the rows and their scrollbar take the page's width less 14 a side,
# which is where the rows stood before the cards (the page keeps its place and width).
ST_CARD_X = 7
ST_CARD_W = ST_W - 2 * ST_CARD_X
ST_TABLE_Y = 62
# The captions stand 27 px above the heads, clear of the arrow of the sorted column, which reaches 9 px above
# its head: in the game a caption 22 px above ran into it (check of 2026-10-13).
ST_CAPTION_Y, ST_HEAD_Y = ST_TABLE_Y + 4, ST_TABLE_Y + 31
ST_LIST_Y = ST_HEAD_Y + 34
ST_LIST_H = ST_ROWS * ST_ROW
ST_TOTAL_Y = ST_LIST_Y + ST_LIST_H + 6
ST_TABLE_H = ST_TOTAL_Y + ST_ROW + 9 - ST_TABLE_Y
ST_BAND_Y = ST_TABLE_Y + ST_TABLE_H + 12
ST_BAND_H = ST_H - 14 - ST_BAND_Y
# the four cards of the band: the state, its building slots, its buildings, occupation
ST_CARDS = [("state", None, 430), ("slots", "Building Slots", 300), ("build", "Buildings", 404)]
ST_CARDS.append(("occ", "Occupation", ST_CARD_W - sum(w for n, t, w in ST_CARDS) - 3 * 12))
ST_CARD_AT = {}
_x = 0
for _name, _title, _w in ST_CARDS:
    ST_CARD_AT[_name] = (_x, _w)
    _x += _w + 12
ST_CHIP_W = 96                  # four chips side by side in the card of the state
# --- D10 --- the three right cards and the graph card that takes their place stand from x 442 of the band (page 449)
ST_CARDS_X0 = ST_CARD_AT["slots"][0]
ST_PEOPLE_W = 58                # the state's People in its card, clear of the switch: "41250K" is 52 px
ST_POP_SWITCH = (147, 1153)     # the Population switch, page x and y: the state card's bottom row, left of Show on map
# --- end D10 ---
ST_SAMPLES = {                  # what the renderer writes for the values of the band (tools/scenes/states.json)
    "THIS.GetName": "Hessen", "THIS.GetCapitalVictoryPointName": "Frankfurt", "?mod1440_st_cat.GetTokenLocalizedKey": "Dense Urban Region",
    "THIS.Owner.GetNameDef": "the German Reich", "?mod1440_sr_from.GetNameWithFlag": "Poland", "?mod1440_sr_date.GetDateStringNoHourLong": "27 September, 1939",
    "?mod1440_st_free|G0": "§G6§!", "?mod1440_st_slots|0": "9", "?mod1440_st_used_n|0": "3", "?mod1440_st_used_other|0": "1",
    "?mod1440_st_dmg|0": "3", "?days_since_last_strategic_bombing|0": "4", "?state_population_k|0": "3802",
    "?compliance|1": "8.4", "?compliance_speed|+=2": "+0.12", "?resistance|1": "31.6", "?resistance_speed|-=2": "-0.05",
    "?resistance_target|1": "40.0", "?mod1440_st_r_coal|0": "16",
}


def st_sample(window, inside):
    """A sample for a value of the States page, or None for the shared rules of sample_for."""
    if window == "mod1440_states_row" and inside.startswith("?mod1440_st_r_"):
        return "250"
    # D10: the three right cards and the country's modifiers stand in mod1440_states_cards and its row
    if window in ("mod1440_states_card", "mod1440_states_cards_row") or window in ("mod1440_states", "mod1440_states_cards") and inside.startswith("?modifier@"):
        if inside in ST_SAMPLES:
            return ST_SAMPLES[inside]
        if inside.startswith("?damaged_building_level"):
            return "2"
        if inside.startswith("?modifier@"):
            return {"compliance_growth": "-2.0%", "resistance_target": "+5.0%"}.get(inside.split("@")[1].split("|")[0], "+5.0%")
        if inside.startswith("?mod1440_st_r_"):
            return "0"
        if inside.startswith(("?infrastructure", "?industrial", "?arms_factory", "?building_level")):
            return {"?infrastructure_level|0": "4", "?industrial_complex_level|0": "2", "?arms_factory_level|0": "1"}.get(inside, "0")
    return None


def free_slot_tree(low, high):
    """Script that finds how many shared building slots are free in the state in scope, between low and high.
    The trigger takes a written number only (Engine Facts X20), so the search is written out: five questions."""
    if low == high:
        return "set_variable = { mod1440_st_free = %d }\n" % low
    middle = (low + high) // 2
    question = block("free_building_slots", "building = industrial_complex\nsize > %d\ninclude_locked = no\n" % middle)
    return block("if", block("limit", question) + free_slot_tree(middle + 1, high)) + block("else", free_slot_tree(low, middle))


def strip(name, x, y, sprite, frame, scale):
    """A frame of a strip of icons (buildings, resources), which lets a click through."""
    return ('iconType = { name = "%s" position = { x = %d y = %d } spriteType = "%s" frame = %d scale = %s '
            'alwaystransparent = yes }\n' % (name, x, y, sprite, frame, scale))


def states_band():
    """The band under the table: four cards for the chosen state. The cards and what belongs to the country
    stand in the page; what belongs to the state is a list of one row (the array mod1440_st_card holds the
    chosen state), so that its texts and triggers run in the state's scope (Engine Facts X10, X36, X39).
    D10: the three right cards (Building Slots, Buildings, Occupation) stand in a scripted GUI of their own,
    mod1440_states_cards, with a list of one row of their own (mod1440_states_cards_row) and the country's
    modifiers, so that the Population view's graph card (mod1440_states_pop) takes their place without the two
    ever drawn over each other: a nested container cannot be hidden (X15). The state card stays in the page.
    Returns the page's widgets, the state card's row, the cards' window and row, the triggers of the page, of the
    state card's row and of the cards' window, the effects and the properties."""
    page, entry, triggers, row_triggers, effects, properties = "", "", "", "", "", ""
    cards, card_triggers, card_properties = "", "", ""      # --- D10 --- the window of the three right cards
    for name, title, width in ST_CARDS:
        x, w = ST_CARD_AT[name]
        inner = text("st_band_%s_title" % name, 14, 8, w - 28, B.key("st_band_%s_title" % name, title), FONT_CARD, height=30) if title else ""
        if name == "state":
            page += box("st_band_%s" % name, ST_CARD_X + x, ST_BAND_Y, w, ST_BAND_H, inner, CARD_BG)
        else:
            cards += box("st_band_%s" % name, x - ST_CARDS_X0, 0, w, ST_BAND_H, inner, CARD_BG)
    page += text("st_c_none", ST_CARD_X + 14, ST_BAND_Y + 14, 400, B.key("st_c_none", "No state is listed. Choose All in the title strip."), FONT_LABEL)
    triggers += block("st_c_none_visible", "check_variable = { mod1440_st_rows^num < 1 }\n")

    owned, core = "is_owned_by = ROOT\n", "is_core_of = ROOT\n"
    noncore = "NOT = { is_core_of = ROOT }\n"

    # ---- the state: flag, name, capital and category, owner, the War Diary's record, chips, resources, people
    x0 = ST_CARD_AT["state"][0]
    entry += icon("st_c_flag", x0 + 14, 12, "GFX_flag_small2")
    properties += block("st_c_flag", 'image = "[THIS.Owner.GetFlag]"\n')
    entry += text("st_c_name", x0 + 66, 10, 350, B.key("st_c_name", "[THIS.GetName]"), FONT_CARD, height=30, fixed=True)
    entry += text("st_c_where", x0 + 66, 42, 350, B.key("st_c_where", "Capital [THIS.GetCapitalVictoryPointName]  ·  [?mod1440_st_cat.GetTokenLocalizedKey]"), FONT_SMALL, height=20, fixed=True)
    entry += text("st_c_where_cap", x0 + 66, 42, 350, B.key("st_c_where_cap", "Capital [THIS.GetCapitalVictoryPointName]"), FONT_SMALL, height=20, fixed=True)
    row_triggers += block("st_c_where_visible", "NOT = { check_variable = { mod1440_st_cat = 0 } }\n")
    row_triggers += block("st_c_where_cap_visible", "check_variable = { mod1440_st_cat = 0 }\n")
    for name, value, condition in (
            ("core", "Core of §Y[THIS.Owner.GetNameDef]§!", owned + core),
            ("owned", "Owned by §Y[THIS.Owner.GetNameDef]§!, not a core", owned + noncore),
            ("held", "Owned by §Y[THIS.Owner.GetNameDef]§!, held by you", "NOT = { is_owned_by = ROOT }\n")):
        entry += text("st_c_owner_%s" % name, x0 + 14, 70, 402, B.key("st_c_owner_%s" % name, value), FONT_SMALL, height=20, fixed=True)
        row_triggers += block("st_c_owner_%s_visible" % name, condition)
    # the record E1 keeps on a state (tools/build_records.py): every state carries a country once the Records
    # have begun, so the text never names a variable that is not there (Engine Facts X73)
    entry += text("st_c_taken", x0 + 14, 94, 402, B.key("st_c_taken", "Taken from §Y[?mod1440_sr_from.GetNameWithFlag]§! on [?mod1440_sr_date.GetDateStringNoHourLong]"), FONT_SMALL, height=20, fixed=True)
    entry += text("st_c_untaken", x0 + 14, 94, 402, B.key("st_c_untaken", "§gIn your hands since before the record began.§!"), FONT_SMALL, height=20)
    row_triggers += block("st_c_taken_visible", "check_variable = { mod1440_sr_day > 0 }\n")
    row_triggers += block("st_c_untaken_visible", "NOT = { check_variable = { mod1440_sr_day > 0 } }\n")
    # chips: four places, each with the first of its labels that applies
    chips = [
        [("core", "§GCore§!", owned + core), ("noncore", "Not a core", owned + noncore), ("occupied", "§YOccupied§!", "NOT = { is_owned_by = ROOT }\n")],
        [("coastal", "Coastal", "is_coastal = yes\n"), ("inland", "§gInland§!", "is_coastal = no\n")],
        [("capital", "§YCapital§!", "is_capital = yes\n")],
        [("island", "Island", "is_island_state = yes\n"), ("dmz", "§RDemilitarised§!", "is_island_state = no\nis_demilitarized_zone = yes\n"),
         ("border", "§RBorder war§!", "is_island_state = no\nis_demilitarized_zone = no\nhas_border_war = yes\n")],
    ]
    for place, options in enumerate(chips):
        for name, label, condition in options:
            entry += box("st_c_chip_%s" % name, x0 + 14 + place * (ST_CHIP_W + 6), 120, ST_CHIP_W, 26,
                         text("st_c_chip_%s_t" % name, 0, 4, ST_CHIP_W, B.key("st_c_chip_%s" % name, label), FONT_SMALL, "centre", 20),
                         head_sprite(240))
            row_triggers += block("st_c_chip_%s_visible" % name, condition)
    for n, resource in enumerate(ST_RESOURCES):
        rx = x0 + 14 + n * 57
        entry += strip("st_c_res_icon_%d" % n, rx, 156, "GFX_resources_strip", n + 1, 0.9)
        variable = "mod1440_st_r_" + resource
        entry += text("st_c_res_%d" % n, rx + 26, 157, 30, B.key("st_c_res_%d" % n, "[?%s|0]" % variable), FONT_LABEL, height=22)
        entry += text("st_c_res_%d_z" % n, rx + 26, 157, 30, B.key("st_c_res_z", "§g-§!"), FONT_LABEL, height=22)
        row_triggers += block("st_c_res_%d_visible" % n, more_than_zero(variable))
        row_triggers += block("st_c_res_%d_z_visible" % n, "NOT = { %s }\n" % more_than_zero(variable).strip())
    entry += text("st_c_people_l", x0 + 14, 194, 80, B.key("st_c_people_l", "People"), FONT_SMALL, height=20)
    # D10: 58 wide (was 160), clear of the Population switch beside it; "41250K" is 52 px
    entry += text("st_c_people", x0 + 80, 192, ST_PEOPLE_W, B.key("st_c_people", "[?state_population_k|0]K"), FONT_LABEL, height=22)
    entry += button("st_c_goto", x0 + ST_CARD_AT["state"][1] - 162, ST_BAND_H - 46, "GFX_button_148x34", B.key("st_c_goto", "Show on map"),
                    tooltip=B.key("st_c_goto_tt", "Moves the camera to this state and hides the page"))
    effects += block("st_c_goto_click", block("ROOT", "goto_state = PREV\nset_variable = { mod1440_st_open = 0 }\nadd_to_variable = { mod1440_st_dirty = 1 }\n"))

    # ---- D10: the state card's row is done; from here on entry and row_triggers are the row of the window
    # mod1440_states_cards, whose x counts from that window
    state_entry, entry = entry, ""
    state_row_triggers, row_triggers = row_triggers, ""

    # ---- building slots: the free count, a bar of the used share, the shared buildings by icon
    x0, w = ST_CARD_AT["slots"]
    x0 -= ST_CARDS_X0
    entry += text("st_c_free", x0 + 14, 44, 60, B.key("st_c_free", "[?mod1440_st_free|G0]"), FONT_TITLE, height=40)
    entry += text("st_c_of", x0 + 74, 58, w - 88, B.key("st_c_of", "free of [?mod1440_st_slots|0]"), FONT_LABEL, height=22)
    tip = B.key("st_c_bar_tt", "Shared slots in use: the shared buildings over the free slots and the shared buildings. Only the game's own shared buildings are counted; a building another mod adds is not, so with such a mod the bar is short. The free number is the game's own.")
    entry += scaled("st_c_bar", x0 + 14, 98, bar_sprite(w - 28), 1, tooltip=tip)
    card_properties += block("st_c_bar", "frame = mod1440_st_used\n")
    entry += text("st_c_used", x0 + 14, 120, w - 28, B.key("st_c_used", "[?mod1440_st_used_n|0] used by shared buildings:"), FONT_SMALL, height=20)
    for n, (name, building, frame) in enumerate(ST_SHARED):
        sx = x0 + 14 + n * 54
        entry += strip("st_c_sh_icon_%s" % name, sx, 144, "GFX_buildings_strip", frame, 0.6)
        value = dict((c[0], c[1]) for c in STATE_COLUMNS)[name]
        entry += text("st_c_sh_%s" % name, sx + 28, 146, 24, B.key("st_c_sh_%s" % name, "[?%s|0]" % value), FONT_LABEL, height=22)
        entry += text("st_c_sh_%s_z" % name, sx + 28, 146, 24, B.key("st_c_sh_z", "§g-§!"), FONT_LABEL, height=22)
        row_triggers += block("st_c_sh_%s_visible" % name, more_than_zero(value))
        row_triggers += block("st_c_sh_%s_z_visible" % name, "NOT = { %s }\n" % more_than_zero(value).strip())
    entry += text("st_c_sh_other", x0 + 14, 176, w - 28, B.key("st_c_sh_other", "and [?mod1440_st_used_other|0] in other shared buildings"), FONT_SMALL, height=20)
    row_triggers += block("st_c_sh_other_visible", more_than_zero("mod1440_st_used_other"))
    entry += text("st_c_note", x0 + 14, 200, w - 28, B.key("st_c_note", "§gThe game's own shared buildings only§!"), FONT_SMALL, height=20)

    # ---- buildings: the nine icons, the level under each, a damaged level in red, damage and bombing
    x0, w = ST_CARD_AT["build"]
    x0 -= ST_CARDS_X0
    for n, (name, value, width, head, tip_text, group) in enumerate(c for c in STATE_COLUMNS if c[5] == "build"):
        bx = x0 + 12 + n * 42
        damaged = "damaged_building_level@" + ST_BUILDING[name]
        entry += strip("st_c_b_icon_%s" % name, bx, 44, "GFX_buildings_strip", head[1], 0.9)
        entry += text("st_c_b_%s" % name, bx - 2, 90, 46, B.key("st_c_b_%s" % name, "[?%s|0]" % value), FONT_VALUE, "centre", 26)
        entry += text("st_c_b_%s_z" % name, bx - 2, 90, 46, B.key("st_c_b_z", "§g-§!"), FONT_VALUE, "centre", 26)
        entry += text("st_c_b_%s_dmg" % name, bx - 2, 118, 46, B.key("st_c_b_%s_dmg" % name, "§R-[?%s|0]§!" % damaged), FONT_SMALL, "centre", 20)
        row_triggers += block("st_c_b_%s_visible" % name, more_than_zero(value))
        row_triggers += block("st_c_b_%s_z_visible" % name, "NOT = { %s }\n" % more_than_zero(value).strip())
        row_triggers += block("st_c_b_%s_dmg_visible" % name, more_than_zero(damaged))
    entry += text("st_c_dmg", x0 + 14, 150, w - 28, B.key("st_c_dmg", "§R[?mod1440_st_dmg|0] levels damaged§!, in red above"), FONT_SMALL, height=20)
    entry += text("st_c_nodmg", x0 + 14, 150, w - 28, B.key("st_c_nodmg", "§gNo building is damaged.§!"), FONT_SMALL, height=20)
    row_triggers += block("st_c_dmg_visible", more_than_zero("mod1440_st_dmg"))
    row_triggers += block("st_c_nodmg_visible", "NOT = { %s }\n" % more_than_zero("mod1440_st_dmg").strip())
    # What the game gives for a state never bombed is not known yet (a 1936 start has none): a day count
    # from 1 to ten years is taken as a bombing, anything else as none.
    bombed = "check_variable = { days_since_last_strategic_bombing > 0 }\ncheck_variable = { days_since_last_strategic_bombing < 3650 }\n"
    entry += text("st_c_bombed", x0 + 14, 172, w - 28, B.key("st_c_bombed", "Last bombed [?days_since_last_strategic_bombing|0] days ago"), FONT_SMALL, height=20)
    entry += text("st_c_unbombed", x0 + 14, 172, w - 28, B.key("st_c_unbombed", "§gNot bombed.§!"), FONT_SMALL, height=20)
    row_triggers += block("st_c_bombed_visible", bombed)
    row_triggers += block("st_c_unbombed_visible", "NOT = { AND = { %s } }\n" % bombed.replace("\n", " ").strip())

    # ---- occupation: the state's figures for a state that is not a core, then the country's modifiers
    x0, w = ST_CARD_AT["occ"]
    x0 -= ST_CARDS_X0
    for n, (name, label, value) in enumerate((
            ("compliance", "$COMPLIANCE$", "[?compliance|1]%  [?compliance_speed|+=2]"),
            ("resistance", "$RESISTANCE$", "[?resistance|1]%  [?resistance_speed|-=2]"),
            ("target", "Resistance target", "[?resistance_target|1]%"))):
        y = 44 + n * 21
        entry += text("st_c_occ_%s_l" % name, x0 + 14, y, 130, B.key("st_c_occ_%s_l" % name, label), FONT_SMALL, height=20)
        entry += text("st_c_occ_%s" % name, x0 + 140, y, w - 154, B.key("st_c_occ_%s" % name, value), FONT_SMALL, "right", 20)
        row_triggers += block("st_c_occ_%s_l_visible" % name, noncore) + block("st_c_occ_%s_visible" % name, noncore)
    entry += text("st_c_occ_core", x0 + 14, 44, w - 28, B.key("st_c_occ_core", "§gA core of yours: no occupation.§!"), FONT_SMALL, height=20)
    row_triggers += block("st_c_occ_core_visible", core)
    # D10: the country's modifiers belong to the cards' window, after its list of one row (drawn over it)
    mods = text("st_c_mod_caption", x0 + 14, 112, w - 28, B.key("st_c_mod_caption", "§gYour country's modifiers§!"), FONT_SMALL, height=20)
    for n, (key, token, fmt) in enumerate((("MODIFIER_COMPLIANCE_GROWTH", "compliance_growth", "+=%1"),
                                           ("MODIFIER_RESISTANCE_TARGET", "resistance_target", "-=%1"),
                                           ("MODIFIER_REQUIRED_GARRISON_FACTOR", "required_garrison_factor", "-=%1"))):
        y = 134 + n * 21
        variable = "modifier@" + token
        mods += text("st_c_mod_%d_l" % n, x0 + 14, y, 190, key, FONT_SMALL, height=20)
        mods += text("st_c_mod_%d" % n, x0 + 200, y, w - 214, B.key("st_c_mod_%d" % n, "[?%s|%s]" % (variable, fmt)), FONT_SMALL, "right", 20)
        mods += text("st_c_mod_%d_z" % n, x0 + 200, y, w - 214, B.key("st_c_mod_z", "§g-§!"), FONT_SMALL, "right", 20)
        changed = "NOT = { check_variable = { %s = 0 } }\n" % variable
        card_triggers += block("st_c_mod_%d_visible" % n, changed) + block("st_c_mod_%d_z_visible" % n, "check_variable = { %s = 0 }\n" % variable)

    # the lists of one row: the state card's in the page, after its card; the three cards' in their window, between
    # the cards and the country's modifiers: drawn over the one, under the other
    def one_row(name, x, y, width):
        return ('gridboxtype = {\n\tname = "%s"\n\tposition = { x = %d y = %d }\n\tsize = { width = %d height = %d }\n'
                '\tslotsize = { width = 1 height = 1 }\n\tadd_horizontal = no\n\tformat = "UPPER_LEFT"\n}\n' % (name, x, y, width, ST_BAND_H))
    state_w = ST_CARD_AT["state"][1]
    page += one_row("st_card_grid", ST_CARD_X, ST_BAND_Y, state_w)
    # --- D10 --- the switch of the Population view, in the state card's bottom row (page 147,1153): drawn over the row
    page += button("st_pop_view", ST_POP_SWITCH[0], ST_POP_SWITCH[1], "GFX_sort_button_120x29", B.key("st_pop_view", "Population"),
                   tooltip=B.key("st_pop_view_tt", "Shows the chosen state's population month by month in place of its slots, buildings and "
                                 "occupation; a click on a row then draws that state. Click again for the cards. The page remembers the view."))
    effects += block("st_pop_view_click", flip("mod1440_pop_view") + setv("mod1440_pop_vf", 1)
                     + iff(is_one("mod1440_pop_view"), setv("mod1440_pop_vf", 2) + "mod1440_pop_draw = yes\n")
                     + "add_to_variable = { mod1440_st_dirty = 1 }\n")
    properties += block("st_pop_view", "frame = mod1440_pop_vf\n")
    cards_w = ST_CARD_W - ST_CARDS_X0
    cards += one_row("st_cards_grid", 0, 0, cards_w) + mods
    cards_gui = box("mod1440_states_cards", ST_X + ST_CARD_X + ST_CARDS_X0, ST_Y + ST_BAND_Y, cards_w, ST_BAND_H, cards)
    cards_gui += row("mod1440_states_cards_row", cards_w, ST_BAND_H, entry)
    return (page, row("mod1440_states_card", state_w, ST_BAND_H, state_entry), cards_gui, triggers, state_row_triggers,
            card_triggers + row_triggers, effects, properties, card_properties)


def states_table():
    effects = ""
    triggers = ""
    properties = ""

    # ---- title strip, with the choices of which states to list: each a button with a second frame for "chosen"
    body = title_strip("st_head", ST_W)
    body += page_title("st_title", 170, "States")
    body += text("st_hint", ST_W - 86 - 590, 18, 590, B.key("st_hint", "Click a state for its card, right-click to see it on the map. Shift+M hides the page."), FONT_SMALL, "right")
    body += close_button("st_fold", ST_W - 66, 10, "shift+m", B.key("st_fold_tt", "Hide this page and give the map back"))
    effects += block("st_fold_click", "set_variable = { mod1440_st_open = 0 }\nadd_to_variable = { mod1440_st_dirty = 1 }\n")
    choices = [("all", "All", 0, "Every state you control."), ("core", "Cores", 1, "Only the states that are cores of yours."),
               ("other", "Occupied", 2, "Only the states that are not cores of yours.")]
    for i, (name, label, value, tip) in enumerate(choices):
        body += button("st_show_%s" % name, 200 + i * 104, 13, "GFX_sort_button_100x29", B.key("st_show_%s" % name, label),
                       tooltip=B.key("st_show_%s_tt" % name, tip))
        effects += block("st_show_%s_click" % name, "set_variable = { mod1440_st_show = %d }\nmod1440_st_list = yes\n" % value)
        properties += block("st_show_%s" % name, "frame = mod1440_st_frame_%d\n" % value)
    body += button("st_only_free", 200 + 3 * 104 + 16, 13, "GFX_sort_button_140x29", B.key("st_only_free", "With free slots"),
                   tooltip=B.key("st_only_free_tt", "Only the states with a free slot for a factory."))
    effects += block("st_only_free_click", flip("mod1440_st_only_free") + "mod1440_st_list = yes\n")
    properties += block("st_only_free", "frame = mod1440_st_frame_free\n")
    body += button("st_refresh", 200 + 3 * 104 + 16 + 160, 13, "GFX_sort_button_100x29", B.key("st_refresh", "Refresh"),
                   tooltip=B.key("st_refresh_tt", "Makes the list again. It is made when the page opens, when you sort or choose, and at the start of each day while the page is open. The numbers of a row, the totals and the cards are from that moment."))
    effects += block("st_refresh_click", "mod1440_st_list = yes\n")

    # ---- the table card: a caption over each group of columns
    body += box("st_table", ST_CARD_X, ST_TABLE_Y, ST_CARD_W, ST_TABLE_H, "", CARD_BG)
    for group, caption in STATE_GROUPS:
        low, high = ST_SPAN[group]
        body += text("st_group_%s" % group, 14 + low, ST_CAPTION_Y, high - low, B.key("st_group_%s" % group, "§g%s§!" % caption), FONT_SMALL, "centre", 20)

    # ---- column heads: a click sorts, a second click turns the order
    body += button("st_sort_name", 14, ST_HEAD_Y, head_sprite(ST_NAME), B.key("st_sort_name", "State"),
                   tooltip=B.key("st_sort_name_tt", "Back to the order of the game."))
    effects += block("st_sort_name_click", "set_variable = { mod1440_st_sort_by = 0 }\nmod1440_st_list = yes\n")
    keys = ""           # script: the value the list is sorted by
    arrows = ""         # script: where the arrow of the sorted column stands
    sums = ""           # script: this state's values added to the totals
    clear = ""          # script: the totals back to zero
    picked = is_one("mod1440_st_picked") + "\n"
    unpicked = "NOT = { %s }\n" % picked.strip()
    owned, held = "is_owned_by = ROOT\n", "NOT = { is_owned_by = ROOT }\n"
    entry = icon("st_row_stripe", 0, 0, STRIPE % (ST_ROWS_W, ST_ROW))
    entry += icon("st_row_pick", 0, 0, PICK % (ST_ROWS_W, ST_ROW))
    entry += button("st_row", 0, 0, head_sprite(ST_NAME), tooltip=B.key("st_row_tt", "Click: this state's cards under the table. Right-click: show it on the map and hide the page."))
    # the owner's flag beside the name of a state that is held but not owned
    entry += 'iconType = { name = "st_row_flag" position = { x = 8 y = 7 } spriteType = "GFX_flag_smallest" alwaystransparent = yes }\n'
    properties += block("st_row_flag", 'image = "[THIS.Owner.GetFlag]"\n')
    # the name: yellow on the chosen row, another colour for a state that is not a core of yours
    names = [("name", 10, "[THIS.GetName]", owned + "is_core_of = ROOT\n" + unpicked),
             ("occ", 10, "§L[THIS.GetName]§!", owned + "NOT = { is_core_of = ROOT }\n" + unpicked),
             ("chosen", 10, "§Y[THIS.GetName]§!", owned + picked),
             ("held", 36, "§L[THIS.GetName]§!", held + unpicked),
             ("held_chosen", 36, "§Y[THIS.GetName]§!", held + picked)]
    row_triggers = block("st_row_stripe_visible", is_one("mod1440_st_odd") + "\n") + block("st_row_pick_visible", picked)
    row_triggers += block("st_row_flag_visible", held)
    for name, nx, value, condition in names:
        entry += plain("st_row_%s" % name, nx, 4, ST_NAME - nx - 6, B.key("st_row_%s" % name, value), height=22)
        row_triggers += block("st_row_%s_visible" % name, condition)
    # the used share of the shared slots, left of the free count
    entry += scaled("st_row_bar", ST_EDGE["free"] + 6, 11, bar_sprite(ST_FREE_BAR - 6), 1, tooltip=B.key("st_row_bar_tt", "Shared slots in use. Only the game's own shared buildings are counted: with a mod that adds some, the bar is short. The free number is the game's own."))
    properties += block("st_row_bar", "frame = mod1440_st_used\n")
    row_triggers += block("st_row_bar_visible", more_than_zero("mod1440_st_slots"))
    total = text("st_total_label", 10, 5, ST_NAME - 16, B.key("st_total_label", "Total of the [?mod1440_st_rows^num|0] listed"), FONT_SMALL, height=20)
    for number, (name, value, width, head, tip, group) in enumerate(STATE_COLUMNS, start=1):
        x = 14 + ST_EDGE[name]
        # --- D10 --- In a year sorts the largest fall first
        order = "\\nClick to sort, the largest fall first; click again to turn the order." if name == "pop_year" else "\\nClick to sort, click again to turn the order."
        tip_key = B.key("st_sort_%s_tt" % name, tip + order)
        if head[0] == "text":
            body += button("st_sort_%s" % name, x, ST_HEAD_Y, head_sprite(width), B.key("st_sort_%s" % name, head[1]), tooltip=tip_key)
        else:
            body += button("st_sort_%s" % name, x, ST_HEAD_Y, head_sprite(width), tooltip=tip_key)
            sprite, scale, dx, dy = (("GFX_buildings_strip", 0.6, ST_ICON_DX["building"], 1) if head[0] == "building"
                                     else ("GFX_resources_strip", 0.9, ST_ICON_DX["resource"], 3))
            body += ('iconType = { name = "st_icon_%s" position = { x = %d y = %d } spriteType = "%s" frame = %d scale = %s '
                     'alwaystransparent = yes }\n' % (name, x + dx, ST_HEAD_Y + dy, sprite, head[1], scale))
        effects += block("st_sort_%s_click" % name, (
            iff("check_variable = { mod1440_st_sort_by = %d }" % number, flip("mod1440_st_up"))
            + els(setv("mod1440_st_sort_by", number) + setv("mod1440_st_up", 0))
            + "mod1440_st_list = yes\n"))
        keys += iff("check_variable = { ROOT.mod1440_st_sort_by = %d }" % number, tmp("st_key", value), "if" if number == 1 else "else_if")
        arrows += iff("check_variable = { mod1440_st_sort_by = %d }" % number, setv("mod1440_st_arrow_x", x + width - ARROW_DX),
                      "if" if number == 1 else "else_if")
        fmt = {"pop": "|0]K", "free": "|G0]"}.get(name, "|0]")
        # a value stands in the middle of its column, under the middle of its head; the free count in the
        # middle of what the bar leaves of its column
        cell_x, cell_w = (ST_EDGE[name] + ST_FREE_BAR, width - ST_FREE_BAR) if name == "free" else (ST_EDGE[name], width)
        if name == "pop_year":
            # --- D10 --- the change in a year, red for a fall and green for a rise, empty when 0 or unknown; the total
            # is the summed population of the listed states now against twelve months before, in the bar's white
            change = "[?mod1440_pop_dy|=1]%"
            entry += text("st_cell_pop_year", cell_x, 4, cell_w, B.key("st_cell_pop_year", "§R%s§!" % change), FONT_LABEL, "centre", 22)
            entry += text("st_cell_pop_year_up", cell_x, 4, cell_w, B.key("st_cell_pop_year_up", "§G%s§!" % change), FONT_LABEL, "centre", 22)
            row_triggers += block("st_cell_pop_year_visible", "check_variable = { mod1440_pop_dy < 0 }\n")
            row_triggers += block("st_cell_pop_year_up_visible", "check_variable = { mod1440_pop_dy > 0 }\n")
            total += text("st_total_pop_year", cell_x, 4, cell_w, B.key("st_total_pop_year", "[?mod1440_st_sum_pop_year|=1]%"), FONT_LABEL, "centre", 22)
            triggers += block("st_total_pop_year_visible", is_one("mod1440_st_pop_has") + "\nNOT = { check_variable = { mod1440_st_sum_pop_year = 0 } }\n")
            sums += iff(is_one("mod1440_pop_hy"), "add_to_variable = { ROOT.mod1440_st_pop_ya = mod1440_pop_ya }\n"
                        "add_to_variable = { ROOT.mod1440_st_pop_last = mod1440_pop_last }\n")
            clear += setv("mod1440_st_pop_ya", 0) + setv("mod1440_st_pop_last", 0)
            continue
        entry += text("st_cell_%s" % name, cell_x, 4, cell_w, B.key("st_cell_%s" % name, "[?%s%s" % (value, fmt)), FONT_LABEL, "centre", 22)
        if group == "occ":
            row_triggers += block("st_cell_%s_visible" % name, "NOT = { is_core_of = ROOT }\n")
            continue
        if group == "build":
            # a damaged building: its level in red, in place of the plain one
            damaged = more_than_zero("damaged_building_level@" + ST_BUILDING[name])
            entry += text("st_cell_%s_dmg" % name, cell_x, 4, cell_w, B.key("st_cell_%s_dmg" % name, "[?%s|R0]" % value), FONT_LABEL, "centre", 22)
            row_triggers += block("st_cell_%s_visible" % name, more_than_zero(value) + "NOT = { %s }\n" % damaged.strip())
            row_triggers += block("st_cell_%s_dmg_visible" % name, damaged)
        elif name != "pop":
            row_triggers += block("st_cell_%s_visible" % name, more_than_zero(value))
        # the total of the column, over the states that are listed
        total += text("st_total_%s" % name, cell_x, 4, cell_w,
                      B.key("st_total_%s" % name, "[?mod1440_st_sum_%s%s" % (name, "|0]K" if name == "pop" else "|0]")), FONT_LABEL, "centre", 22)
        triggers += block("st_total_%s_visible" % name, more_than_zero("mod1440_st_sum_%s" % name))
        sums += "add_to_variable = { ROOT.mod1440_st_sum_%s = %s }\n" % (name, value)
        clear += setv("mod1440_st_sum_%s" % name, 0)
    # the arrow that marks the sorted column: script moves it there
    first = 14 + ST_EDGE[STATE_COLUMNS[0][0]] + STATE_COLUMNS[0][2] - ARROW_DX
    body += scaled("st_arrow_down", first, ST_HEAD_Y + ARROW_DY, "GFX_arrow_down_small", ARROW)
    body += scaled("st_arrow_up", first, ST_HEAD_Y + ARROW_DY, "GFX_arrow_up_small", ARROW)
    properties += block("st_arrow_down", "x = mod1440_st_arrow_x\n") + block("st_arrow_up", "x = mod1440_st_arrow_x\n")
    triggers += block("st_arrow_down_visible", more_than_zero("mod1440_st_sort_by") + "NOT = { check_variable = { mod1440_st_up = 1 } }\n")
    triggers += block("st_arrow_up_visible", more_than_zero("mod1440_st_sort_by") + "check_variable = { mod1440_st_up = 1 }\n")

    # ---- the list, and under it the totals
    body += listing("st_list", "st_grid", 14, ST_LIST_Y, ST_ROWS_W + 30, ST_LIST_H, ST_ROW)
    body += box("st_totals", 14, ST_TOTAL_Y, ST_ROWS_W, ST_ROW, total, head_sprite(240))
    # A click chooses the state for the band; a right-click moves the camera there and hides the page (the
    # left click of the first build). The row's scope is the state.
    effects += block("st_row_click", block("ROOT", "set_variable = { mod1440_st_sel = PREV }\nmod1440_st_pick = yes\n"))
    effects += block("st_row_right_click", block("ROOT", "goto_state = PREV\nset_variable = { mod1440_st_open = 0 }\nadd_to_variable = { mod1440_st_dirty = 1 }\n"))

    # ---- the band of the chosen state
    (band, card_row, cards_gui, band_triggers, card_triggers, cards_triggers, band_effects, band_properties,
     cards_properties) = states_band()
    body += band
    triggers += band_triggers
    effects += band_effects
    properties += band_properties
    # --- D10 --- the graph card of the Population view
    pop_gui, pop_script = states_pop()

    gui = box("mod1440_states", ST_X, ST_Y, ST_W, ST_H, body, PAGE_BG)
    gui += row("mod1440_states_row", ST_ROWS_W, ST_ROW, entry)
    gui += card_row
    gui += cards_gui + pop_gui
    handle = button("st_unfold", 0, 0, "GFX_button_148x34", B.key("st_unfold", "States"), shortcut="shift+m",
                    tooltip=B.key("st_unfold_tt", "Show every state you control as a table"))
    gui += box("mod1440_states_handle", ST_X, 8, 148, 34, handle)

    script = scripted_gui(
        "mod1440_states", "mod1440_states", "construction_tab",
        visible="check_variable = { mod1440_st_open = 1 }\n", dirty="mod1440_st_dirty",
        lists=(block("st_grid", 'array = mod1440_st_rows\nchange_scope = yes\nentry_container = "mod1440_states_row"\n')
               + block("st_card_grid", 'array = mod1440_st_card\nchange_scope = yes\nentry_container = "mod1440_states_card"\n')),
        effects=effects, triggers=triggers + row_triggers + card_triggers, properties=properties)
    # --- D10 --- the two views of the band's right part, windows of their own over the page and never shown together:
    # the three cards (Building Slots, Buildings, Occupation) and the graph card (Population). Declared after the page.
    shown = "check_variable = { mod1440_st_open = 1 }\n"
    script += "\n" + scripted_gui(
        "mod1440_states_cards", "mod1440_states_cards", "construction_tab",
        visible=shown + "NOT = { %s }\n" % is_one("mod1440_pop_view"), dirty="mod1440_st_dirty",
        lists=block("st_cards_grid", 'array = mod1440_st_card\nchange_scope = yes\nentry_container = "mod1440_states_cards_row"\n'),
        triggers=cards_triggers, properties=cards_properties)
    script += "\n" + pop_script
    script += "\n" + scripted_gui(
        "mod1440_states_handle", "mod1440_states_handle", "construction_tab",
        visible="NOT = { check_variable = { mod1440_st_open = 1 } }\n",
        effects=block("st_unfold_click", "set_variable = { mod1440_st_open = 1 }\nmod1440_st_list = yes\n"))

    frames = "".join("set_variable = { mod1440_st_frame_%s = 1 }\n" % n for n in ("0", "1", "2", "free"))
    frames += "".join(block("if", "limit = { check_variable = { mod1440_st_show = %d } }\nset_variable = { mod1440_st_frame_%d = 2 }\n" % (v, v))
                      for v in (0, 1, 2))
    frames += block("if", "limit = { check_variable = { mod1440_st_only_free = 1 } }\nset_variable = { mod1440_st_frame_free = 2 }\n")
    # --- D10 --- the frame of the Population switch, and the change in a year of the listed states together: their
    # population of the newest month against twelve months before, of the states that have both (mod1440_pop_hy)
    frames += setv("mod1440_pop_vf", 1) + iff(is_one("mod1440_pop_view"), setv("mod1440_pop_vf", 2))
    pop_total = (setv("mod1440_st_sum_pop_year", 0) + setv("mod1440_st_pop_has", 0)
                 + iff("check_variable = { mod1440_st_pop_ya > 0 }", (
                     setv("mod1440_st_sum_pop_year", "mod1440_st_pop_last") + "subtract_from_variable = { mod1440_st_sum_pop_year = mod1440_st_pop_ya }\n"
                     + pop_percent("mod1440_st_sum_pop_year", "mod1440_st_pop_ya", "variable") + setv("mod1440_st_pop_has", 1))))
    # every second row of the list gets the darker band (the variable is the state's own)
    bands = tmp("st_odd", 0) + block("for_each_scope_loop", (
        "array = mod1440_st_rows\n" + setv("mod1440_st_odd", "st_odd")
        + iff("check_variable = { st_odd = 0 }", tmp("st_odd", 1)) + els(tmp("st_odd", 0))))
    # what the cards and the slot bar need of each state, kept on the state when the list is made
    shared = "".join("add_to_variable = { mod1440_st_used_n = building_level@%s }\n" % b for n, b, f in ST_SHARED[1:])
    other = "".join("add_to_variable = { mod1440_st_used_other = building_level@%s }\n" % b for b in ST_SHARED_OTHER)
    figures = (
        setv("mod1440_st_used_n", "building_level@" + ST_SHARED[0][1]) + shared
        + setv("mod1440_st_used_other", 0) + other
        + "add_to_variable = { mod1440_st_used_n = mod1440_st_used_other }\n"
        + setv("mod1440_st_slots", "mod1440_st_free") + "add_to_variable = { mod1440_st_slots = mod1440_st_used_n }\n"
        + setv("mod1440_st_used", 0)
        + iff("check_variable = { mod1440_st_slots > 0 }", setv("mod1440_st_used", "mod1440_st_used_n")
              + "multiply_variable = { mod1440_st_used = 100 }\ndivide_variable = { mod1440_st_used = mod1440_st_slots }\n")
        + "".join(setv("mod1440_st_r_" + r, "resource@" + r) + "round_variable = mod1440_st_r_%s\n" % r for r in ST_RESOURCES)
        + setv("mod1440_st_dmg", 0)
        + "".join("add_to_variable = { mod1440_st_dmg = damaged_building_level@%s }\n" % b for b in ST_BUILDING.values())
        + "".join(iff("has_state_category = %s" % c, setv("mod1440_st_cat", "token:" + c), "if" if n == 0 else "else_if")
                  for n, c in enumerate(ST_CATEGORIES))
        + els(setv("mod1440_st_cat", 0))
        + setv("mod1440_st_picked", 0))
    listing_script = (
        "# States: makes the list of the page again, for the country in scope. For each state it controls: count the\n"
        "# free shared slots and what the cards need, keep the state if the choices of the page want it and add it\n"
        "# to the totals; then sort, and choose the state of the cards.\n"
        + block("mod1440_st_list", (
            "clear_array = mod1440_st_rows\n" + clear
            + block("for_each_scope_loop", (
                "array = controlled_states\n"
                + free_slot_tree(0, 31) + figures
                + "set_temp_variable = { st_keep = 1 }\n"
                + block("if", block("limit", "check_variable = { ROOT.mod1440_st_show = 1 }\nNOT = { is_core_of = ROOT }\n") + "set_temp_variable = { st_keep = 0 }\n")
                + block("if", block("limit", "check_variable = { ROOT.mod1440_st_show = 2 }\nis_core_of = ROOT\n") + "set_temp_variable = { st_keep = 0 }\n")
                + block("if", block("limit", "check_variable = { ROOT.mod1440_st_only_free = 1 }\ncheck_variable = { mod1440_st_free < 1 }\n") + "set_temp_variable = { st_keep = 0 }\n")
                + iff("check_variable = { st_keep = 1 }", "add_to_array = { ROOT.mod1440_st_rows = THIS }\n" + sums)))
            + pop_total
            + "mod1440_st_sort = yes\n" + bands + arrows + frames
            + "mod1440_st_pick = yes\n"))
        + "\n# States: the state of the cards, for the country in scope. The one in mod1440_st_sel if it is listed, else\n"
        "# the first of the list. Its row gets the mark of the chosen row, the others lose theirs (as on the Officers page).\n"
        + block("mod1440_st_pick", (
            block("for_each_scope_loop", "array = mod1440_st_rows\n" + setv("mod1440_st_picked", 0))
            + "clear_array = mod1440_st_card\n"
            + iff("check_variable = { mod1440_st_rows^num > 0 }", (
                iff("NOT = { is_in_array = { array = mod1440_st_rows value = mod1440_st_sel } }", setv("mod1440_st_sel", "mod1440_st_rows^0"))
                + block("var:mod1440_st_sel", setv("mod1440_st_picked", 1))
                + "add_to_array = { mod1440_st_card = mod1440_st_sel }\n"))
            + iff(is_one("mod1440_pop_view"), "mod1440_pop_draw = yes\n")       # --- D10 --- the graph follows the chosen state
            + "add_to_variable = { mod1440_st_dirty = 1 }\n"))
        + "\n# States: puts the list into the order of the chosen column, largest first, or smallest first when turned.\n"
        "# The search for the next largest is the game's own loop, so 150 states take a few milliseconds (X22).\n"
        + block("mod1440_st_sort", block("if", (
            "limit = { check_variable = { mod1440_st_sort_by > 0 } }\n"
            "clear_array = mod1440_st_keys\n"
            + block("for_each_scope_loop", (
                "array = mod1440_st_rows\nset_temp_variable = { st_key = 0 }\n" + keys
                + block("if", "limit = { check_variable = { ROOT.mod1440_st_up = 1 } }\nmultiply_temp_variable = { st_key = -1 }\n")
                + "add_to_array = { ROOT.mod1440_st_keys = st_key }\n"))
            + "clear_array = mod1440_st_sorted\n"
            + block("for_loop_effect", (
                "start = 0\nend = mod1440_st_rows^num\nvalue = st_step\n"
                + block("find_highest_in_array", "array = mod1440_st_keys\nvalue = st_high\nindex = st_at\n")
                + "add_to_array = { mod1440_st_sorted = mod1440_st_rows^st_at }\n"
                "set_variable = { mod1440_st_keys^st_at = -2000000 }\n"))
            + "clear_array = mod1440_st_rows\n"
            + block("for_each_loop", "array = mod1440_st_sorted\nvalue = st_copy\nadd_to_array = { mod1440_st_rows = st_copy }\n")))))
    daily = block("if", "limit = { check_variable = { mod1440_st_open = 1 } }\nmod1440_st_list = yes\n")
    return gui, script, listing_script, daily


# ---------------------------------------------------------------- State population history (D10), on the States page

# --- D10 ---
# Every state of the map is written down on the first of each month (its state_population_k), ten years at most, in
# one round a month for the whole game (mod1440_pop_round): one array per state, mod1440_pop_k, a value a month, and
# the months for all in three global arrays (the date, its year, its day number). The States page shows the chosen
# state's months in a graph card that takes the place of the band's three right cards, the Population view
# (scratch/phases/D10/design.json, layout.json; decisions of 2026-10-26).
POP_KEEP = 120                  # months kept: ten years, for every state (decision 3)
POP_GAP = 20                    # days at least between two rounds: on_monthly runs for each player, the round once
POP_X, POP_Y = ST_X + ST_CARD_X + ST_CARDS_X0, ST_Y + ST_BAND_Y        # the graph card on construction_tab (page 449,964)
POP_W, POP_H = ST_CARD_W - ST_CARDS_X0, ST_BAND_H                        # 1016 x 232: the three cards and their gaps
POP_CHART_X, POP_CHART_Y = 78, 48       # the frame of the graph in the card (page 527,1012), 608 x 172
POP_CHART_W, POP_CHART_H = 600, 152     # the columns, as wide in every range
POP_INSET, POP_AXIS = 4, 20             # the columns stand 4 inside the frame; the years under them
POP_STEPS = POP_CHART_H                 # heights a column can have: one per pixel (History's H_STEPS pattern, X17)
POP_YEARS = 10                          # year marks: ten years have at most ten first months
# The ranges: (months, px from one column to the next, a column's width, caption). 24 x 25 = 60 x 10 = 120 x 5.
POP_RANGES = [(24, 25, 22, "2 years"), (60, 10, 8, "5 years"), (120, 5, 4, "10 years")]
POP_RANGE_X, POP_RANGE_W, POP_ZOOM_X, POP_BUTTON_Y = 234, 100, 546, 8
# the table of figures beside the chart (page 1151,972): a head bar of 30 and seven rows of 24; its columns from its
# left edge, (x, width)
POP_TAB_X, POP_TAB_Y, POP_TAB_W, POP_HEAD, POP_ROW = 702, 8, 300, 30, 24
POP_TAB_COLS = {"label": (8, 76), "people": (84, 72), "pct": (168, 50), "month": (220, 72)}


def pop_first_x(step):
    """Card x of the first year mark: a text 40 wide under the middle of the first column."""
    return POP_CHART_X + POP_INSET + step // 2 - 20


def pop_percent(variable, base, kind="temp_variable"):
    """Script: the change held in `variable` as a percentage of `base`. A variable keeps three decimals and holds at
    most about 2.1 million, and a large state's change times 100 could pass that: times 10, over the base, times 10,
    which leaves the percentage in steps of 0.01."""
    return ("multiply_{k} = {{ {v} = 10 }}\ndivide_{k} = {{ {v} = {b} }}\nmultiply_{k} = {{ {v} = 10 }}\n"
            .format(k=kind, v=variable, b=base))


def pop_change(name, x, y, width, variable, has, suffix, font, same=True):
    """A change in the table of figures: green for a rise, red for a fall, a grey dash for none (same), nothing
    while it is not known (has). Returns the widgets and their triggers."""
    number = "[?%s|=1]%s" % (variable, suffix)
    known = is_one(has) + "\n"
    out = text(name + "_up", x, y, width, B.key(name + "_up", "§G%s§!" % number), font, "right", 24)
    out += text(name + "_dn", x, y, width, B.key(name + "_dn", "§R%s§!" % number), font, "right", 24)
    triggers = (block(name + "_up_visible", known + "check_variable = { %s > 0 }\n" % variable)
                + block(name + "_dn_visible", known + "check_variable = { %s < 0 }\n" % variable))
    if same:
        out += text(name + "_same", x, y, width, B.key("pop_same", DASH), font, "right", 24)
        triggers += block(name + "_same_visible", known + "check_variable = { %s = 0 }\n" % variable)
    return out, triggers


# The rows of the table of figures: (name, label, tooltip, people: (kind, variable), percent variable or None, month
# variable, the variable that says the row is known). kind "value" a number of thousands, "change" a signed change.
POP_TABLE = [
    ("latest", "Latest", "The newest month written down for this state: the changes count from it. Today's People in the state card is a newer number until the next first of the month.",
     ("value", "mod1440_pop_latest"), None, "mod1440_pop_d0", "mod1440_pop_hl"),
    ("month", "In a month", "The change since the month before; Month is the month compared with.",
     ("change", "mod1440_pop_cm"), "mod1440_pop_cmp", "mod1440_pop_d1", "mod1440_pop_hm"),
    ("year", "In a year", "The change since twelve months before; Month is the month compared with.",
     ("change", "mod1440_pop_cy"), "mod1440_pop_cyp", "mod1440_pop_d2", "mod1440_pop_hy"),
    ("first", "Since first", "The change since the first month written down for this state (ten years at most).",
     ("change", "mod1440_pop_cf"), "mod1440_pop_cfp", "mod1440_pop_d3", "mod1440_pop_hf"),
    ("max", "Highest", "The highest month written down for this state, and its month.",
     ("value", "mod1440_pop_max"), None, "mod1440_pop_d4", "mod1440_pop_hl"),
    ("min", "Lowest", "The lowest month written down for this state, and its month.",
     ("value", "mod1440_pop_min"), None, "mod1440_pop_d5", "mod1440_pop_hl"),
]


def states_pop():
    """The graph card of the Population view: a scripted GUI of its own over the band's three right cards, shown
    while the page is open and the view is on (a nested container cannot be hidden, X15). The title, the range and
    Zoom in; the chart with one grid per range, whose columns are progress bars script fills (X17), the months before
    the state was the player's in the unit list's preparing colour; the scale, the year marks and the line of the
    month taken, which script moves (X4); the table of figures. Returns the .gui windows and the scripted GUI."""
    triggers, properties, effects = "", "", ""
    has = more_than_zero("mod1440_pop_valid")
    inner = text("pop_title", 14, 8, 118, B.key("pop_title", "Population"), FONT_CARD, height=30)
    inner += text("pop_unit", 132, 15, 90, B.key("pop_unit", "§gin thousands§!"), FONT_SMALL, height=20)
    # the range: 2, 5 or 10 years, the chosen one on frame 2; until the player picks one, the shortest that holds
    # every month written down
    for k, (span, step, width, caption) in enumerate(POP_RANGES):
        name = "pop_range_%d" % span
        inner += button(name, POP_RANGE_X + k * (POP_RANGE_W + 4), POP_BUTTON_Y, "GFX_sort_button_100x29", B.key(name, caption),
                        tooltip=B.key(name + "_tt", "The last %s on the graph, a column a month. Until you pick a range, the graph takes the "
                                                    "shortest that holds every month written down." % caption))
        effects += block(name + "_click", setv("mod1440_pop_range", span) + "mod1440_pop_draw = yes\n")
        properties += block(name, "frame = mod1440_pop_rf_%d\n" % span)
    # Zoom in is on by default for a population (decision 4): mod1440_pop_flat is 1 when the player turned it off
    inner += button("pop_zoom", POP_ZOOM_X, POP_BUTTON_Y, "GFX_sort_button_140x29", B.key("pop_zoom", "Zoom in"), tooltip=B.key(
        "pop_zoom_tt", "On: the columns start at the lowest month instead of at zero, so that a fall of a few percent shows; the "
                       "scale on the left gives the numbers. Click to start them at zero, again to zoom in."))
    effects += block("pop_zoom_click", flip("mod1440_pop_flat") + "mod1440_pop_draw = yes\n")
    properties += block("pop_zoom", "frame = mod1440_pop_zf\n")

    # the scale on the left: five heights, from the foot of the columns to the top
    for k in range(5):
        inner += text("pop_scale_%d" % k, 14, POP_CHART_Y + POP_CHART_H - k * (POP_CHART_H // 4) - 10, POP_CHART_X - 22,
                      B.key("pop_scale_%d" % k, "[?mod1440_pop_s%d|1]" % k), FONT_SMALL, "right", 20)
        triggers += block("pop_scale_%d_visible" % k, has)
    # the chart: bands on the second and fourth quarter, one grid per range, of which script fills one
    chart = "".join(icon("pop_band_%d" % k, POP_INSET, k * (POP_CHART_H // 4), STRIPE % (POP_CHART_W, POP_CHART_H // 4)) for k in (1, 3))
    columns, lists = "", ""
    for span, step, width, caption in POP_RANGES:
        chart += ('gridboxtype = {\n\tname = "pop_grid_%d"\n\tposition = { x = %d y = 0 }\n\tsize = { width = %d height = %d }\n'
                  '\tslotsize = { width = %d height = %d }\n\tadd_horizontal = yes\n\tmax_slots_horizontal = %d\n\tformat = "UPPER_LEFT"\n}\n'
                  % (span, POP_INSET, POP_CHART_W, POP_CHART_H + POP_AXIS, step, POP_CHART_H + POP_AXIS, span))
        lists += block("pop_grid_%d" % span, 'array = mod1440_pop_bars_%d\nentry_container = "mod1440_states_pop_col_%d"\n' % (span, span))
        # a column: the month's height (v, -1 for a month before the state's record: no column), in the preparing
        # colour before the state came into the player's hands (mod1440_pop_pre_<span>), in green from then on
        at = (step - width) // 2
        cells = ""
        for widget, sprite, words in (("pop_pre", "column_prep", ", before it was yours"), ("pop_bar", "column", "")):
            tip = B.key(widget + "_tt", "[?mod1440_pop_sdate^i.GetDateStringNoHourLong]: [?mod1440_pop_now^i|1]K%s" % words)
            cells += ('iconType = { name = "%s%d" position = { x = %d y = 0 } spriteType = "GFX_1440p_SG_%s_%dx%d" pdx_tooltip = "%s" }\n'
                      % (widget, span, at, sprite, width, POP_CHART_H, tip))
            properties += block("%s%d" % (widget, span), "frame = v\n")
        columns += row("mod1440_states_pop_col_%d" % span, step, POP_CHART_H + POP_AXIS, cells)
        before = "check_variable = { mod1440_pop_pre_%d^i = 1 }" % span
        triggers += block("pop_pre%d_visible" % span, "check_variable = { v > -1 }\n%s\n" % before)
        triggers += block("pop_bar%d_visible" % span, "check_variable = { v > -1 }\nNOT = { %s }\n" % before)
    inner += box("pop_chart", POP_CHART_X, POP_CHART_Y, POP_CHART_W + 2 * POP_INSET, POP_CHART_H + POP_AXIS, chart, CARD_BG)
    # a state with no month written down (a game that got the mod after its start, until the first of next month)
    inner += text("pop_none", POP_CHART_X + 20, POP_CHART_Y + 50, POP_CHART_W - 40, B.key(
        "pop_none", "Nothing is written down for this state yet. Every state is written down on the first of each month: the first "
                    "column comes then."), FONT_LABEL, height=48)
    triggers += block("pop_none_visible", "NOT = { %s }\n" % has.strip())

    # Under the columns, the year at each first month of a new year; the line of the first month in the player's
    # hands. Script moves them (x properties, X4).
    for k in range(POP_YEARS):
        inner += text("pop_year_%d" % k, pop_first_x(POP_RANGES[0][1]), POP_CHART_Y + POP_CHART_H + 1, 40,
                      B.key("pop_year_%d" % k, "[?mod1440_pop_yl_%d|0]" % k), FONT_SMALL, "centre", 18)
        properties += block("pop_year_%d" % k, "x = mod1440_pop_yx_%d\n" % k)
        triggers += block("pop_year_%d_visible" % k, more_than_zero("mod1440_pop_yl_%d" % k))
    inner += ('iconType = { name = "pop_mark" position = { x = %d y = %d } spriteType = "GFX_1440p_SG_line_2x%d" alwaystransparent = yes }\n'
              % (POP_CHART_X + POP_INSET, POP_CHART_Y, POP_CHART_H))
    properties += block("pop_mark", "x = mod1440_pop_mark_x\n")
    triggers += block("pop_mark_visible", is_one("mod1440_pop_mark") + "\n")

    # ---- the table of figures: a head bar and seven rows, a band on every second
    tx = POP_TAB_X
    inner += icon("pop_head", tx, POP_TAB_Y, head_sprite(POP_TAB_W))
    for name, label, tip in (("people", "People", "In thousands, as the game's People."),
                             ("pct", "%", "The change in percent of the month compared with."),
                             ("month", "Month", "The month the row's number belongs to; for a change, the month compared with.")):
        cx, cw = POP_TAB_COLS[name]
        inner += text("pop_h_%s" % name, tx + cx, POP_TAB_Y + 4, cw, B.key("pop_h_%s" % name, label), FONT_LABEL, "right", 22,
                      tooltip=B.key("pop_h_%s_tt" % name, tip))
    top = POP_TAB_Y + POP_HEAD
    inner += stripes("pop_stripe", tx, top, POP_TAB_W, POP_ROW, len(POP_TABLE) + 1)
    lx, lw = POP_TAB_COLS["label"]
    px, pw = POP_TAB_COLS["people"]
    cx, cw = POP_TAB_COLS["pct"]
    mx, mw = POP_TAB_COLS["month"]
    for r, (name, label, tip, (kind, variable), pct, month, known) in enumerate(POP_TABLE):
        y = top + r * POP_ROW
        inner += text("pop_l_%s" % name, tx + lx, y + 3, lw, B.key("pop_l_%s" % name, label), FONT_LABEL, height=22,
                      tooltip=B.key("pop_l_%s_tt" % name, tip))
        if kind == "value":
            inner += text("pop_v_%s" % name, tx + px, y + 2, pw, B.key("pop_v_%s" % name, "[?%s|1]K" % variable), FONT_VALUE, "right", 24)
            triggers += block("pop_v_%s_visible" % name, is_one(known) + "\n")
        else:
            part, more = pop_change("pop_v_%s" % name, tx + px, y + 2, pw, variable, known, "K", FONT_VALUE)
            inner += part
            triggers += more
        if pct:
            part, more = pop_change("pop_p_%s" % name, tx + cx, y + 3, cw, pct, known, "%", FONT_LABEL, same=False)
            inner += part
            triggers += more
        inner += text("pop_m_%s" % name, tx + mx, y + 3, mw, B.key("pop_m_%s" % name, "§g[?%s.GetDateStringNoHour]§!" % month), FONT_LABEL, "right", 22)
        triggers += block("pop_m_%s_visible" % name, is_one(known) + "\n")
    # Yours since: the day the state came into the player's hands, from the War Diary's record on the state (E1)
    y = top + len(POP_TABLE) * POP_ROW
    tip = B.key("pop_l_since_tt", "The day this state came into your hands, as the War Diary keeps it. On the graph the months before it "
                                  "are blue-grey, a yellow line marks the first month in your hands. A dash: yours since before the record began.")
    inner += text("pop_l_since", tx + lx, y + 3, lw + pw + cw, B.key("pop_l_since", "§YYours since§!"), FONT_LABEL, height=22, tooltip=tip)
    inner += text("pop_m_since", tx + mx, y + 3, mw, B.key("pop_m_since", "§g[?mod1440_pop_since.GetDateStringNoHour]§!"), FONT_LABEL, "right", 22)
    inner += text("pop_m_since_none", tx + mx, y + 3, mw, B.key("pop_m_since_none", DASH), FONT_LABEL, "right", 22)
    triggers += block("pop_m_since_visible", is_one("mod1440_pop_taken") + "\n")
    triggers += block("pop_m_since_none_visible", "NOT = { %s }\n" % is_one("mod1440_pop_taken"))

    gui = box("mod1440_states_pop", POP_X, POP_Y, POP_W, POP_H, inner, CARD_BG) + columns
    script = scripted_gui(
        "mod1440_states_pop", "mod1440_states_pop", "construction_tab",
        visible="check_variable = { mod1440_st_open = 1 }\n%s\n" % is_one("mod1440_pop_view"), dirty="mod1440_st_dirty",
        lists=lists, effects=effects, triggers=triggers, properties=properties)
    return gui, script


def pop_script():
    """The monthly round over every state and the drawing of the chosen state. Returns the scripted effects."""
    # ---- the round: once a month in all
    month = (
        "".join("add_to_array = { global.mod1440_pop_%s = global.%s }\n" % (a, g) for a, g in (("date", "date"), ("year", "year"), ("days", "num_days")))
        + iff("check_variable = { global.mod1440_pop_date^num > %d }" % POP_KEEP,
              "".join("remove_from_array = { array = global.mod1440_pop_%s index = 0 }\n" % a for a in ("date", "year", "days")))
        + tmp("pr_n", "global.mod1440_pop_date^num")
        + block("every_state", (
            # a state with fewer months than the dates (a save of an earlier build has none) gets -1 for the months
            # before its first, which draws no column and counts for nothing (as History pads its newer series)
            tmp("pr_p", "pr_n") + "subtract_from_temp_variable = { pr_p = mod1440_pop_k^num }\nsubtract_from_temp_variable = { pr_p = 1 }\n"
            + iff("check_variable = { pr_p > 0 }", block("for_loop_effect", "start = 0\nend = pr_p\nvalue = pr_q\n"
                                                         "add_to_array = { array = mod1440_pop_k value = -1 index = 0 }\n"))
            + "add_to_array = { mod1440_pop_k = state_population_k }\n"
            + iff("check_variable = { mod1440_pop_k^num > pr_n }", "remove_from_array = { array = mod1440_pop_k index = 0 }\n")
            + "mod1440_pop_year = yes\n")))
    year = (
        setv("mod1440_pop_dy", 0) + setv("mod1440_pop_fall", 0) + setv("mod1440_pop_hy", 0) + setv("mod1440_pop_ya", 0) + setv("mod1440_pop_last", 0)
        + tmp("pr_i", "mod1440_pop_k^num") + "subtract_from_temp_variable = { pr_i = 13 }\n"
        + iff("check_variable = { pr_i > -1 }", (
            tmp("pr_a", "mod1440_pop_k^pr_i") + "add_to_temp_variable = { pr_i = 12 }\n" + tmp("pr_b", "mod1440_pop_k^pr_i")
            + iff("check_variable = { pr_a > 0 } check_variable = { pr_b > -1 }", (
                setv("mod1440_pop_hy", 1) + setv("mod1440_pop_ya", "pr_a") + setv("mod1440_pop_last", "pr_b")
                + setv("mod1440_pop_dy", "pr_b") + "subtract_from_variable = { mod1440_pop_dy = pr_a }\n"
                + pop_percent("mod1440_pop_dy", "pr_a", "variable")
                + setv("mod1440_pop_fall", 0) + "subtract_from_variable = { mod1440_pop_fall = mod1440_pop_dy }\n")))))
    opened = "is_ai = no\n%s\n%s\n" % (is_one("mod1440_st_open"), is_one("mod1440_pop_view"))
    round_ = (
        tmp("pr_gap", "global.num_days") + "subtract_from_temp_variable = { pr_gap = global.mod1440_pop_day }\n"
        + iff("check_variable = { pr_gap > %d }" % (POP_GAP - 1), (
            setv("global.mod1440_pop_day", "global.num_days") + "mod1440_pop_month = yes\n"
            # an open page in the Population view gets the new month at once
            + block("every_country", "limit = { %s }\nmod1440_pop_draw = yes\n" % opened.replace("\n", " ").strip()))))

    # ---- the drawing, for the country in scope
    draw = "".join("clear_temp_array = pd_%s\n" % a for a in ("date", "year", "day", "all"))
    for arr, g in (("date", "date"), ("year", "year"), ("day", "days")):
        draw += block("for_each_loop", "array = global.mod1440_pop_%s\nvalue = pd_v\nadd_to_temp_array = { pd_%s = pd_v }\n" % (g, arr))
    draw += tmp("pd_since", 0) + tmp("pd_sdate", 0)
    draw += iff("check_variable = { mod1440_st_card^num > 0 }", block("var:mod1440_st_sel", (
        block("for_each_loop", "array = mod1440_pop_k\nvalue = pd_v\nadd_to_temp_array = { pd_all = pd_v }\n")
        + iff("check_variable = { mod1440_sr_day > 0 }", tmp("pd_since", "mod1440_sr_day") + tmp("pd_sdate", "mod1440_sr_date")))))
    # n: the state's months that have a date; the newest of both stand at the end of their arrays
    draw += (tmp("pd_n", "pd_all^num") + iff("check_variable = { pd_date^num < pd_n }", tmp("pd_n", "pd_date^num"))
             + tmp("pd_va", "pd_all^num") + "subtract_from_temp_variable = { pd_va = pd_n }\n"
             + tmp("pd_da", "pd_date^num") + "subtract_from_temp_variable = { pd_da = pd_n }\n")
    # the range: the player's, or the shortest that holds every month written down
    draw += (tmp("pd_span", "mod1440_pop_range")
             + iff("check_variable = { pd_span = 0 }", tmp("pd_span", POP_RANGES[0][0])
                   + "".join(iff("check_variable = { pd_n > %d }" % POP_RANGES[k - 1][0], tmp("pd_span", POP_RANGES[k][0])) for k in range(1, len(POP_RANGES))))
             + "".join(setv("mod1440_pop_rf_%d" % r[0], 1) for r in POP_RANGES)
             + "".join(iff("check_variable = { pd_span = %d }" % span, tmp("pd_step", step) + tmp("pd_yoff", pop_first_x(step))
                           + tmp("pd_mx", POP_CHART_X + POP_INSET + (step - width) // 2 - 1) + setv("mod1440_pop_rf_%d" % span, 2), "if" if k == 0 else "else_if")
                       for k, (span, step, width, caption) in enumerate(POP_RANGES))
             + tmp("pd_from", "pd_n") + "subtract_from_temp_variable = { pd_from = pd_span }\n" + iff("check_variable = { pd_from < 0 }", tmp("pd_from", 0))
             + tmp("pd_cnt", "pd_n") + "subtract_from_temp_variable = { pd_cnt = pd_from }\n")
    # every month: the first, the highest and the lowest written down, those of the range, and the first month in the
    # player's hands (pd_t, the first whose day is not before the day the state was taken; pd_n when none is)
    first_of = lambda pre: tmp(pre + "hi", "pd_v") + tmp(pre + "lo", "pd_v")   # noqa: E731
    draw += ("".join(tmp(v, 0) for v in ("pd_valid", "pd_hi", "pd_lo", "pd_hi_k", "pd_lo_k", "pd_first", "pd_first_k", "pd_shn", "pd_shi", "pd_slo"))
             + tmp("pd_t", "pd_n")
             + block("for_loop_effect", (
                 "start = 0\nend = pd_n\nvalue = pd_k\n"
                 + tmp("pd_j", "pd_k") + "add_to_temp_variable = { pd_j = pd_va }\n" + tmp("pd_v", "pd_all^pd_j")
                 + tmp("pd_i", "pd_k") + "add_to_temp_variable = { pd_i = pd_da }\n"
                 + iff("check_variable = { pd_since > 0 } check_variable = { pd_t = pd_n }", tmp("pd_dd", "pd_day^pd_i")
                       + iff("NOT = { check_variable = { pd_dd < pd_since } }", tmp("pd_t", "pd_k")))
                 + iff("check_variable = { pd_v > -1 }", (
                     "add_to_temp_variable = { pd_valid = 1 }\n"
                     + iff("check_variable = { pd_valid = 1 }", tmp("pd_first", "pd_v") + tmp("pd_first_k", "pd_k") + first_of("pd_")
                           + tmp("pd_hi_k", "pd_k") + tmp("pd_lo_k", "pd_k"))
                     + els(iff("check_variable = { pd_v > pd_hi }", tmp("pd_hi", "pd_v") + tmp("pd_hi_k", "pd_k"))
                           + iff("check_variable = { pd_v < pd_lo }", tmp("pd_lo", "pd_v") + tmp("pd_lo_k", "pd_k")))
                     + iff("NOT = { check_variable = { pd_k < pd_from } }", (
                         "add_to_temp_variable = { pd_shn = 1 }\n"
                         + iff("check_variable = { pd_shn = 1 }", first_of("pd_s"))
                         + els(iff("check_variable = { pd_v > pd_shi }", tmp("pd_shi", "pd_v"))
                               + iff("check_variable = { pd_v < pd_slo }", tmp("pd_slo", "pd_v"))))))))))
    draw += setv("mod1440_pop_valid", "pd_valid") + setv("mod1440_pop_n", "pd_n")

    # the table of figures: the newest month, its changes in a month, a year and since the first month, the highest
    # and the lowest, and the day the state came into the player's hands
    def date_of(variable, index):
        return tmp("pd_di", index) + "add_to_temp_variable = { pd_di = pd_da }\n" + tmp("pd_dv", "pd_date^pd_di") + setv(variable, "pd_dv")

    def change(back, has, variable, pct, month):
        return iff("check_variable = { pd_n > %d }" % back, (
            tmp("pd_bk", "pd_n") + "subtract_from_temp_variable = { pd_bk = %d }\n" % (back + 1)
            + tmp("pd_j", "pd_bk") + "add_to_temp_variable = { pd_j = pd_va }\n" + tmp("pd_b", "pd_all^pd_j")
            + iff("check_variable = { pd_b > -1 }", (
                setv(has, 1) + setv(variable, "pd_l") + "subtract_from_variable = { %s = pd_b }\n" % variable + setv(pct, 0)
                + iff("check_variable = { pd_b > 0 }", setv(pct, variable) + pop_percent(pct, "pd_b", "variable"))
                + date_of(month, "pd_bk")))))

    draw += "".join(setv("mod1440_pop_%s" % v, 0) for v in ("hl", "hm", "hy", "hf", "taken"))
    draw += iff("check_variable = { pd_n > 0 }", (
        tmp("pd_j", "pd_n") + "add_to_temp_variable = { pd_j = pd_va }\nsubtract_from_temp_variable = { pd_j = 1 }\n" + tmp("pd_l", "pd_all^pd_j")
        + iff("check_variable = { pd_l > -1 }", (
            setv("mod1440_pop_hl", 1) + setv("mod1440_pop_latest", "pd_l")
            + tmp("pd_last", "pd_n") + "subtract_from_temp_variable = { pd_last = 1 }\n" + date_of("mod1440_pop_d0", "pd_last")
            + change(1, "mod1440_pop_hm", "mod1440_pop_cm", "mod1440_pop_cmp", "mod1440_pop_d1")
            + change(12, "mod1440_pop_hy", "mod1440_pop_cy", "mod1440_pop_cyp", "mod1440_pop_d2")
            + iff("check_variable = { pd_valid > 1 }", (
                setv("mod1440_pop_hf", 1) + setv("mod1440_pop_cf", "pd_l") + "subtract_from_variable = { mod1440_pop_cf = pd_first }\n"
                + setv("mod1440_pop_cfp", 0)
                + iff("check_variable = { pd_first > 0 }", setv("mod1440_pop_cfp", "mod1440_pop_cf") + pop_percent("mod1440_pop_cfp", "pd_first", "variable"))
                + date_of("mod1440_pop_d3", "pd_first_k")))
            + setv("mod1440_pop_max", "pd_hi") + date_of("mod1440_pop_d4", "pd_hi_k")
            + setv("mod1440_pop_min", "pd_lo") + date_of("mod1440_pop_d5", "pd_lo_k")))))
    draw += iff("check_variable = { pd_since > 0 }", setv("mod1440_pop_taken", 1) + setv("mod1440_pop_since", "pd_sdate"))

    # the scale: from zero, or zoomed in (the default) from the lowest month of the range, to its highest
    draw += (tmp("pd_base", 0) + iff("NOT = { %s }" % is_one("mod1440_pop_flat"), tmp("pd_base", "pd_slo"))
             + tmp("pd_range", "pd_shi") + "subtract_from_temp_variable = { pd_range = pd_base }\n"
             + tmp("pd_quarter", "pd_range") + "divide_temp_variable = { pd_quarter = 4 }\n"
             + setv("mod1440_pop_s0", "pd_base")
             + "".join(setv("mod1440_pop_s%d" % k, "mod1440_pop_s%d" % (k - 1)) + "add_to_variable = { mod1440_pop_s%d = pd_quarter }\n" % k for k in (1, 2, 3))
             + setv("mod1440_pop_s4", "pd_shi"))
    # the months of the range as column heights, 0 to POP_STEPS; -1 for a month before the state's record
    draw += ("".join("clear_array = mod1440_pop_bars_%d\nclear_array = mod1440_pop_pre_%d\n" % (r[0], r[0]) for r in POP_RANGES)
             + "".join("clear_array = mod1440_pop_%s\n" % a for a in ("now", "sdate", "syear"))
             + block("for_loop_effect", (
                 "start = 0\nend = pd_cnt\nvalue = pd_k\n"
                 + tmp("pd_kk", "pd_k") + "add_to_temp_variable = { pd_kk = pd_from }\n"
                 + tmp("pd_j", "pd_kk") + "add_to_temp_variable = { pd_j = pd_va }\n" + tmp("pd_v", "pd_all^pd_j")
                 + tmp("pd_i", "pd_kk") + "add_to_temp_variable = { pd_i = pd_da }\n"
                 + tmp("pd_dv", "pd_date^pd_i") + "add_to_array = { mod1440_pop_sdate = pd_dv }\n"
                 + tmp("pd_dv", "pd_year^pd_i") + "add_to_array = { mod1440_pop_syear = pd_dv }\n"
                 + "add_to_array = { mod1440_pop_now = pd_v }\n"
                 + tmp("pd_bar", -1)
                 + iff("check_variable = { pd_v > -1 }", (
                     tmp("pd_bar", 0)
                     + iff("check_variable = { pd_range > 0 }", tmp("pd_bar", "pd_v") + "subtract_from_temp_variable = { pd_bar = pd_base }\n"
                           "divide_temp_variable = { pd_bar = pd_range }\nmultiply_temp_variable = { pd_bar = %d }\n" % POP_STEPS)
                     # every month the same: the columns stand at full height
                     + iff("NOT = { check_variable = { pd_v = 0 } }", tmp("pd_bar", POP_STEPS), "else_if")
                     # from the lowest month, the lowest keeps a sliver: it was written down
                     + iff("NOT = { check_variable = { pd_base = 0 } }", iff("check_variable = { pd_bar < 4 }", tmp("pd_bar", 4)))
                     + iff("check_variable = { pd_bar < 0 }", tmp("pd_bar", 0)) + iff("check_variable = { pd_bar > %d }" % POP_STEPS, tmp("pd_bar", POP_STEPS))))
                 + tmp("pd_pre", 0) + iff("check_variable = { pd_since > 0 } check_variable = { pd_kk < pd_t }", tmp("pd_pre", 1))
                 + "".join(iff("check_variable = { pd_span = %d }" % r[0], "add_to_array = { mod1440_pop_bars_%d = pd_bar }\nadd_to_array = { mod1440_pop_pre_%d = pd_pre }\n"
                               % (r[0], r[0]), "if" if k == 0 else "else_if") for k, r in enumerate(POP_RANGES)))))
    # the year marks under the first month of each year after the first month on the graph
    marks = "".join(iff("check_variable = { pd_slot = %d }" % k, setv("mod1440_pop_yl_%d" % k, "pd_y") + setv("mod1440_pop_yx_%d" % k, "pd_x"),
                        "if" if k == 0 else "else_if") for k in range(POP_YEARS))
    draw += ("".join(setv("mod1440_pop_yl_%d" % k, 0) for k in range(POP_YEARS)) + tmp("pd_before", 0) + tmp("pd_slot", 0)
             + block("for_each_loop", (
                 "array = mod1440_pop_syear\nvalue = pd_y\nindex = pd_yi\n"
                 + iff("check_variable = { pd_yi > 0 } check_variable = { pd_y > 0 }", iff("NOT = { check_variable = { pd_y = pd_before } }", (
                     tmp("pd_x", "pd_yi") + "multiply_temp_variable = { pd_x = pd_step }\nadd_to_temp_variable = { pd_x = pd_yoff }\n"
                     + marks + "add_to_temp_variable = { pd_slot = 1 }\n")))
                 + tmp("pd_before", "pd_y"))))
    # the line of the first month in the player's hands, when it stands inside the range
    draw += (setv("mod1440_pop_mark", 0) + tmp("pd_ts", "pd_t") + "subtract_from_temp_variable = { pd_ts = pd_from }\n"
             + iff("check_variable = { pd_since > 0 } check_variable = { pd_ts > 0 } check_variable = { pd_ts < pd_cnt }", (
                 setv("mod1440_pop_mark", 1) + setv("mod1440_pop_mark_x", "pd_ts") + "multiply_variable = { mod1440_pop_mark_x = pd_step }\n"
                 + "add_to_variable = { mod1440_pop_mark_x = pd_mx }\n")))
    draw += (setv("mod1440_pop_zf", 1) + iff("NOT = { %s }" % is_one("mod1440_pop_flat"), setv("mod1440_pop_zf", 2))
             + "add_to_variable = { mod1440_st_dirty = 1 }\n")

    # an effect stands before the effects that call it: a game left open learns a new one called from an earlier one
    # of the same file only at its second reload (X70)
    return ("# States, population history (D10), in a state's scope: its change over the last twelve months in percent\n"
            "# (mod1440_pop_dy), the fall the In a year column sorts by (mod1440_pop_fall), and the two months the totals add\n"
            "# up (mod1440_pop_ya, _last).\n"
            + block("mod1440_pop_year", year)
            + "\n# States (D10): the month itself, without the guard: the date, its year and day number for all, and each state's\n"
            "# state_population_k; the oldest past %d months is forgotten. Counts nothing but the states (rule 5).\n" % POP_KEEP
            + block("mod1440_pop_month", month)
            + "\n# States (D10): the chosen state's months, for the country in scope: the range, the scale, the column heights of\n"
            "# the range (the months before the state came into the player's hands marked), the year marks, the line of the\n"
            "# month taken and the table of figures. On a row click, the switch, a range, Zoom in, and after the round while\n"
            "# the page is open; never in a trigger drawn each tick (rule 5).\n"
            + block("mod1440_pop_draw", draw)
            + "\n# States (D10): once a month in all, every state of the map written down. Called from each player's on_monthly\n"
            "# and once from on_startup; runs when the last round is %d days or more ago, and sets the stamp first, so that\n" % POP_GAP
            + "# several players, or an on_monthly that fires on another day for another country, make one round a month.\n"
            "# Then an open page in the Population view is drawn again.\n"
            + block("mod1440_pop_round", round_))
# --- D10 --- The scene: the page in the cards view as before (Hessen on 1 January 1936), and the Population view as
# the design draws it (scratch/phases/D10/work/data.py): Warsaw under Devastation Overhaul, held by Germany, written
# down from 1 January 1936 to 1 January 1945 (109 months), taken from Poland on 27 September 1939, the list sorted by
# In a year. The render states population, years2 and flat draw it; a check of 1 January 1936 has one month.
POP_SAMPLE_TAKEN = 45           # the first month in German hands, 1 October 1939
POP_SAMPLE_SINCE = "1939.9.27"


def pop_sample_series():
    """The Warsaw sample of the design, month by month from January 1936 to January 1945."""
    v, out = 2650.0, []
    for j in range(109):
        y, m = 1936 + j // 12, j % 12 + 1
        if (y, m) == (1939, 9):
            v *= 0.9996
        elif (y, m) == (1939, 10):
            v *= 0.952
        elif (1939, 10) < (y, m) < (1944, 9):
            v *= 0.9984 if m % 3 else 0.9971
        elif (y, m) == (1944, 9):
            v *= 0.936
        elif (y, m) == (1944, 10):
            v *= 0.925
        elif (y, m) == (1944, 11):
            v *= 0.988
        elif (y, m) > (1944, 11):
            v *= 0.997
        out.append(round(v, 1))
    return out


POP_SAMPLE = pop_sample_series()
# the list of the design's page figure, sorted by In a year, the largest fall first: (name, change, colour of the name)
POP_SAMPLE_ROWS = [
    ("Warsaw", -16.1, "Y"), ("Kraków", -9.8, "L"), ("Ermland-Masuren", -8.9, ""), ("Rhineland", -7.2, ""),
    ("Westfalen", -6.6, ""), ("Danzig", -5.9, "L"), ("Holstein", -5.1, ""), ("Brandenburg", -4.8, ""),
    ("Hessen", -3.4, ""), ("Sachsen", -3.1, ""), ("Hannover", -2.9, ""), ("Württemberg", -2.5, ""),
    ("Weser-Ems", -2.2, ""), ("Hinterpommern", -1.9, ""), ("Oberbayern", -1.6, ""), ("Lower Silesia", -1.3, ""),
    ("Franken", -1.1, ""), ("Moselland", -0.9, ""), ("Niederbayern", -0.7, ""), ("Vorpommern", -0.6, ""),
    ("Thüringen", -0.4, ""), ("Mecklenburg", -0.3, ""), ("Bohemia", -0.2, "L"), ("Luxembourg", 0.0, "L"),
]


def pop_date(j):
    return "%d.%d.1" % (1936 + j // 12, j % 12 + 1)


def pop_table_sample():
    """The table of figures for the Warsaw sample: the samples of the texts shown and the twins hidden."""
    v = POP_SAMPLE
    n = len(v)
    samples, hide = {}, []
    hi, lo = max(v), min(v)
    samples["pop_v_latest"] = "%.1fK" % v[-1]
    samples["pop_m_latest"] = "§g%s§!" % pop_date(n - 1)
    for name, back in (("month", 1), ("year", 12), ("first", n - 1)):
        old = v[n - 1 - back]
        change = round(v[-1] - old, 1)
        pct = (v[-1] - old) / old * 100.0
        shown = "dn" if change < 0 else "up" if change > 0 else "same"
        hide += ["pop_v_%s_%s" % (name, s) for s in ("up", "dn", "same") if s != shown]
        if shown != "same":
            samples["pop_v_%s_%s" % (name, shown)] = ("§R%+.1fK§!" if change < 0 else "§G%+.1fK§!") % change
        pshown = "dn" if pct < 0 else "up"
        hide.append("pop_p_%s_%s" % (name, "up" if pshown == "dn" else "dn"))
        samples["pop_p_%s_%s" % (name, pshown)] = ("§R%+.1f%%§!" if pct < 0 else "§G%+.1f%%§!") % pct
        samples["pop_m_%s" % name] = "§g%s§!" % pop_date(n - 1 - back)
    samples["pop_v_max"] = "%.1fK" % hi
    samples["pop_m_max"] = "§g%s§!" % pop_date(v.index(hi))
    samples["pop_v_min"] = "%.1fK" % lo
    samples["pop_m_min"] = "§g%s§!" % pop_date(v.index(lo))
    samples["pop_m_since"] = "§g%s§!" % POP_SAMPLE_SINCE
    return samples, hide + ["pop_none", "pop_m_since_none"]


def pop_graph_sample(span, zoom=True):
    """The graph of the Warsaw sample over the last span months as mod1440_pop_draw draws it: the window's hidden
    widgets, samples, places of the year marks and the line, frames, rows of the grids, and the column window's
    "only" and fills."""
    step, width = [(r[1], r[2]) for r in POP_RANGES if r[0] == span][0]
    v = POP_SAMPLE
    first = max(0, len(v) - span)
    shown = v[first:]
    hi, lo = max(shown), min(shown)
    base = lo if zoom else 0.0
    rng = hi - base
    samples, hide = pop_table_sample()
    for k in range(5):
        samples["pop_scale_%d" % k] = "%.1f" % (hi if k == 4 else base + k * rng / 4.0)
    place = {}
    marks = [i for i in range(1, len(shown)) if (first + i) % 12 == 0]
    for k, i in enumerate(marks):
        place["pop_year_%d" % k] = [pop_first_x(step) + i * step, POP_CHART_Y + POP_CHART_H + 1]
        samples["pop_year_%d" % k] = str(1936 + (first + i) // 12)
    hide += ["pop_year_%d" % k for k in range(len(marks), POP_YEARS)]
    ts = POP_SAMPLE_TAKEN - first
    if 0 < ts < len(shown):
        place["pop_mark"] = [POP_CHART_X + POP_INSET + (step - width) // 2 - 1 + ts * step, POP_CHART_Y]
    else:
        hide.append("pop_mark")
    only = {"pop_pre%d" % span: [], "pop_bar%d" % span: []}
    fills = {"pop_pre%d" % span: [], "pop_bar%d" % span: []}
    for i, x in enumerate(shown):
        h = (x - base) / rng * POP_CHART_H if rng > 0 else POP_CHART_H
        if base != 0 and h < 4:
            h = 4
        h = max(0.0, min(float(POP_CHART_H), h))
        w = "pop_pre%d" % span if first + i < POP_SAMPLE_TAKEN else "pop_bar%d" % span
        only[w].append(i)
        fills[w].append(round(h / POP_CHART_H, 3))
    frames = {"pop_range_%d" % span: 2, "pop_zoom": 2 if zoom else 1}
    rows = {"pop_grid_%d" % r[0]: (len(shown) if r[0] == span else 0) for r in POP_RANGES}
    col = {"name": "mod1440_states_pop_col_%d" % span, "only": only, "fills": {w: f for w, f in fills.items() if f}}
    return hide, samples, place, frames, rows, col


# what script hides in the default state: the band as Hessen shows it on 1 January 1936 (a core, inland, six of nine
# slots free, coal its only resource, nothing damaged), every row a core that is not the chosen one
ST_CARD_HIDE = (["st_c_where_cap", "st_c_owner_owned", "st_c_owner_held", "st_c_taken", "st_c_chip_noncore", "st_c_chip_occupied",
                 "st_c_chip_coastal", "st_c_chip_capital", "st_c_chip_island", "st_c_chip_dmz", "st_c_chip_border"]
                + ["st_c_res_%d" % n for n in range(6)] + ["st_c_res_6_z"])
ST_CARDS_HIDE = (["st_c_sh_other", "st_c_dmg", "st_c_bombed", "st_c_sh_civ_z", "st_c_sh_mil_z"]
                 + ["st_c_sh_%s" % n for n in ("dock", "refinery", "silo")]
                 + ["st_c_b_%s_z" % n for n in ("infra", "civ", "mil")]
                 + ["st_c_b_%s" % n for n in ("dock", "refinery", "silo", "air", "aa", "radar")]
                 + ["st_c_b_%s_dmg" % n for n in ST_BUILDING]
                 + ["st_c_occ_%s%s" % (n, part) for n in ("compliance", "resistance", "target") for part in ("", "_l")])
ST_ROW_HIDE = (["st_row_occ", "st_row_chosen", "st_row_held", "st_row_held_chosen", "st_row_flag", "st_row_pick"]
               + ["st_cell_%s_dmg" % c[0] for c in STATE_COLUMNS if c[5] == "build"] + ["st_cell_compliance", "st_cell_resistance"])
ST_PAGE_HIDE = ["st_arrow_up", "st_arrow_down", "st_c_none"]
ST_CARDS_AT = [ST_X - 9 + ST_CARD_X + ST_CARDS_X0, 78 + ST_Y + ST_BAND_Y]       # the tab's corner at -9,78
ST_POP_STATES = ["population", "pop_row", "years2", "flat"]
ST_CARD_STATES = ["", "pick", "cards", "sort_year", "goto", "back"]


def st_pop_state(name, span, zoom, steps, note):
    """A render state of the Population view, the Warsaw sample: the page's list sorted by In a year with Warsaw
    chosen, its state card, and the graph card over the three cards."""
    hide, samples, place, frames, rows, col = pop_graph_sample(span, zoom)
    occ = [r for r, (n, c, colour) in enumerate(POP_SAMPLE_ROWS) if colour == "L"]
    names = [r for r, (n, c, colour) in enumerate(POP_SAMPLE_ROWS) if colour == ""]
    state_rows = {"st_grid": 24, "st_card_grid": 1, "st_cards_grid": 0}
    state_rows.update(rows)
    return {
        "name": name, "steps": steps, "_note": note,
        "hide": {"mod1440_states": ["st_arrow_up", "st_c_none"],
                 "mod1440_states_row": [w for w in ST_ROW_HIDE if w not in ("st_row_occ", "st_row_chosen", "st_row_pick")] + ["st_cell_pop_year_up"],
                 "mod1440_states_card": [w for w in ST_CARD_HIDE if w not in ("st_c_owner_owned", "st_c_taken", "st_c_chip_noncore")]
                 + ["st_c_owner_core", "st_c_untaken", "st_c_chip_core"],
                 "mod1440_states_pop": hide},
        "only": {"mod1440_states_row": {"st_row_name": names, "st_row_occ": occ, "st_row_chosen": [0], "st_row_pick": [0],
                                        "st_cell_pop_year": [r for r, (n, c, colour) in enumerate(POP_SAMPLE_ROWS) if c < 0]},
                 col["name"]: col["only"]},
        "fills": {col["name"]: col["fills"]},
        "place": {"mod1440_states": {"st_arrow_down": [14 + ST_EDGE["pop_year"] + 68 - ARROW_DX, ST_HEAD_Y + ARROW_DY]},
                  "mod1440_states_pop": place},
        "frames": {"mod1440_states": {"st_pop_view": 2}, "mod1440_states_pop": frames},
        "rows": state_rows,
        "samples": {"mod1440_states_pop": samples,
                    # a sample list holds one text per drawn instance: the rows each twin is shown in
                    "mod1440_states_row": {"st_row_name": [POP_SAMPLE_ROWS[r][0] for r in names],
                                           "st_row_occ": ["§L%s§!" % POP_SAMPLE_ROWS[r][0] for r in occ],
                                           "st_row_chosen": ["§Y%s§!" % POP_SAMPLE_ROWS[0][0]],
                                           "st_cell_pop_year": ["§R%+.1f%%§!" % c if c < 0 else "" for n, c, colour in POP_SAMPLE_ROWS]},
                    "mod1440_states_card": {"st_c_name": "Warsaw", "st_c_where": "Capital Warsaw  ·  Large City",
                                            "st_c_owner_owned": "Owned by §Ythe German Reich§!, not a core",
                                            "st_c_taken": "Taken from §YPoland§! on 27 September, 1939", "st_c_people": "1906K"}},
    }


def st_scene():
    """The scene of the States page (D3, D10)."""
    pop_hide, pop_samples, pop_place, pop_frames, pop_rows, pop_col = pop_graph_sample(120)
    windows = [
        {"name": "mod1440_states", "at": [703, 78], "sidePanel": True,
         "rows": {"st_grid": 24, "st_card_grid": 1},
         "listRows": {"st_grid": "mod1440_states_row", "st_card_grid": "mod1440_states_card"},
         "hide": ST_PAGE_HIDE,
         "_note": "Docked to Construction: the tab's corner at -9,78 plus the container's 712,0. The vanilla window has clipping = no. The state card under the table is a list of one row, the chosen state."},
        {"name": "mod1440_states_row", "skip": True, "hide": ST_ROW_HIDE + ["st_cell_pop_year_up"],
         "_note": "Every row is drawn as a core of yours that is not the chosen one: script shows the other names, the flag, the mark of the chosen row and the red levels instead where they apply. In a year: the sample falls of the design."},
        {"name": "mod1440_states_card", "skip": True, "hide": ST_CARD_HIDE,
         "_note": "The state card as Hessen shows it on 1 January 1936: a core, inland, coal its only resource."},
        # D10: the three right cards in a scripted GUI of their own over the page, shown in the cards view
        {"name": "mod1440_states_cards", "at": ST_CARDS_AT, "sidePanel": True, "drawIn": ST_CARD_STATES,
         "rows": {"st_cards_grid": 1}, "listRows": {"st_cards_grid": "mod1440_states_cards_row"},
         "hide": ["st_c_mod_0_z", "st_c_mod_1_z", "st_c_mod_2"],
         "_note": "D10: Building Slots, Buildings and Occupation, a scripted GUI of their own docked to Construction at 1161,964 (page 449,964), shown while the Population view is off. The third modifier is 0 for Germany in 1936 and shows its grey dash."},
        {"name": "mod1440_states_cards_row", "skip": True, "hide": ST_CARDS_HIDE,
         "_note": "The three cards as Hessen shows them on 1 January 1936: six of nine slots free, nothing damaged, a core."},
        # D10: the graph card of the Population view
        {"name": "mod1440_states_pop", "at": ST_CARDS_AT, "sidePanel": True, "drawIn": ST_POP_STATES,
         "rows": pop_rows, "listRows": {"pop_grid_%d" % r[0]: "mod1440_states_pop_col_%d" % r[0] for r in POP_RANGES},
         "hide": pop_hide, "place": pop_place, "frames": pop_frames,
         "_note": "D10: the graph card, a scripted GUI of its own at the three cards' place, shown while the Population view is on; the render states population, years2 and flat draw the design's Warsaw sample (109 months). The two range grids not in use are empty."},
    ] + [{"name": "mod1440_states_pop_col_%d" % r[0], "skip": True} for r in POP_RANGES]
    pop_view = {"clickWidget": "mod1440_states/st_pop_view", "wait": 1.2}
    population = st_pop_state("population", 120, True, [pop_view],
                              "The Population view: the chosen state's months in place of the three cards. Rendered with the design's Warsaw sample; a check of 1 January 1936 shows one column (the month on_startup wrote) unless effect mod1440_chk_pop_months ran first.")
    pop_row = st_pop_state("pop_row", 120, True, [{"clickWidget": "mod1440_states_row/st_row#0", "wait": 1.2}],
                           "A click on the first row in the Population view: the graph and the figures follow the chosen state.")
    years2 = st_pop_state("years2", 24, True, [{"clickWidget": "mod1440_states_pop/pop_range_24", "state": "population", "wait": 1.0}],
                          "2 years: the last 24 months as columns of 22 px; the year marks under their Januaries.")
    flat = st_pop_state("flat", 24, False, [{"clickWidget": "mod1440_states_pop/pop_zoom", "state": "population", "wait": 1.0}],
                        "Zoom in off: the columns stand on zero and the scale starts at 0.")
    cards = {"name": "cards", "steps": [{"clickWidget": "mod1440_states_pop/pop_zoom", "state": "population", "wait": 0.8},
                                        {"clickWidget": "mod1440_states_pop/pop_range_120", "state": "population", "wait": 0.8},
                                        {"clickWidget": "mod1440_states/st_pop_view", "wait": 1.2}],
             "_note": "Zoom in and 10 years again, then the switch back: the three cards return."}
    sort_year = {"name": "sort_year", "steps": [{"clickWidget": "mod1440_states/st_sort_pop_year", "wait": 1.2}],
                 "_note": "A click on In a year sorts by the largest fall; on 1 January 1936 no state has a year yet, so the cells are empty and the order is the game's."}
    samples = {"mod1440_states_row": {"st_cell_pop_year": ["§R%+.1f%%§!" % c if c < 0 else "" for n, c, colour in POP_SAMPLE_ROWS]},
               "mod1440_states": {"st_total_pop_year": "-3.6%"},
               "mod1440_states_pop": pop_samples}
    return {
        "phase": "D3", "file": "mod1440_states.gui", "screenshot": "reference/vanilla/construction.jpg",
        "windows": windows, "samples": samples,
        "setup": [{"move": "open_construction"}, {"key": "shift+m", "wait": 1.5, "_note": "the page is hidden until asked for"}],
        # A left click on the fourth row chooses it; D10: the Population view, a row, a range and Zoom in, back to the
        # cards, In a year sorted; a right-click on the third moves the camera and hides the page; Shift+M brings the
        # page back with the state still chosen. The teardown then hides it as before.
        "captures": [{"name": "pick", "steps": [{"clickWidget": "mod1440_states_row/st_row#3", "wait": 1.2}]},
                     population, pop_row, years2, flat, cards, sort_year,
                     {"name": "goto", "steps": [{"clickWidget": "mod1440_states_row/st_row#2", "button": "right", "wait": 1.5}]},
                     {"name": "back", "steps": [{"key": "shift+m", "wait": 1.5}]}],
        "teardown": [{"key": "shift+m", "wait": 0.8, "_note": "hide it again: the page remembers per country whether it is open"}],
        "expect": ["mod1440_states/st_fold", "mod1440_states/st_refresh", "mod1440_states/st_pop_view", "mod1440_states_cards/st_band_slots"],
        "crop": [690, 70, ST_W + 30, 1230],
        "manual": ["A country with occupied states: the Occupied choice, compliance and resistance, the other colour of a name, the owner's flag in the row and the card, the occupation card",
                   "A bombed state: the red levels in its row and card, the line of damage and the day of the last bombing",
                   "Tooltips: the slot bar of a row and of the slots card say that only the game's own shared buildings are counted",
                   "D10, the user's game: a month written by the real monthly hook (the first of a month passes), with the user's playset (Road to 56, Devastation Overhaul): the new column, In a year after thirteen months, the totals",
                   "D10, the user's game: the save's size before and after ten years of months for every state (about 137,000 numbers with Road to 56)",
                   "D10, the user's game: a state taken in a war, its months before in blue-grey and the yellow line at the first month in the player's hands"],
        "checklist": ST_CHECKLIST,
    }


# The game checker's list (scratch/phases/D10/build/build.json): a check that stays in January 1936; the effects of
# tools/check_effects.py run from the console with nothing selected
ST_CHECKLIST = [
    "The page opens with the first state of the list chosen: its row on the light band, its name yellow, its cards under the table",
    "A left click on another state chooses it: the band and the mark follow, the page stays open",
    "A right-click on a state, and Show on map in the band, move the camera there and hide the page",
    "Sort by a column, choose Cores, press Refresh: the chosen state keeps its mark while it is listed",
    "Hessen against its state view: 6 free of 9 slots, the slot bar a third full, coal 17 (the state view's number), buildings 4, 2, 1",
    "The state card: Capital Frankfurt and Dense Urban Region, Core of the German Reich, the Core and Inland chips",
    "The occupation card: compliance growth -2.0% and resistance target +5.0% as on National Figures, required garrisons a grey dash",
    "A click on a column head sorts, a second click turns the order; State gives the game's order back",
    "The totals against the sum of a column",
    # D10
    "D10 table (no effect): the building columns 46 px and the resource columns 54 px wide, their icons centred over the values; a caption Population over People and In a year; the row still ends at the scrollbar and the page at 1472 px",
    "D10 1 January 1936, no effect: In a year is empty in every row and in the totals bar (one month written down by on_startup)",
    "D10 drawn over or under (capture population, no effect): after the Population switch the graph card stands over the three right cards with nothing of them showing through; after a second click (capture cards) the three cards are back and the graph is gone. If neither the graph nor the cards show, see fallbacks",
    "D10 1 January 1936, the Population view, no effect: one column at the left of the 2-year range, 22 px wide, at full height; its tooltip gives 1 January, 1936 and the state's population as the People column has it; Latest equals the People of the state card; In a month, In a year and Since first empty; Highest and Lowest equal Latest; Yours since a grey dash",
    "D10 the switch keeps frame 2 (gold chevrons) while on; a click on another row in the Population view (capture pop_row) draws that state at once; Shift+M and the close button hide the page and the graph card with it",
    "D10 after `effect mod1440_chk_pop_months` (120 made-up months for every state, the page open): 120 columns of 4 px on the 10-year range by default, year marks 1937 to 1945 under the columns of their Januaries, Zoom in on (frame 2), the lowest column a 4 px sliver",
    "D10 after `effect mod1440_chk_pop_months`: 2 years and 5 years show the last 24 and 60 months (columns of 22 and 8 px); Zoom in off starts the columns at zero and the scale at 0; the scale's five values against the tooltips of the highest and the lowest column",
    "D10 after `effect mod1440_chk_pop_months`: In a year in every row, red, different from state to state, and the totals bar's In a year in white; a click on the In a year head sorts the largest fall first, a second click turns it; the arrow stands on its head",
    "D10 after `effect mod1440_chk_pop_months`: the table of figures against the columns: Latest is the last column's tooltip (today's People), In a month the last less the one before, In a year the last less the 13th from the end, in thousands and in percent, red for a fall (the made-up dates are all 1 January 1936)",
    "D10 after `effect mod1440_chk_pop_months` then `effect mod1440_chk_pop_taken` (Brandenburg, state 64, taken between month 44 and 45 of the made-up record): with Brandenburg chosen the first 45 columns of the 10-year range are blue-grey, the rest green, a 2 px yellow line before the 46th; Yours since gives a date; on 5 years the line moves with its month, on 2 years it is gone and every column is green",
    "D10 after `effect mod1440_chk_pop_clear` (a save of an earlier build: no months): the graph card says that nothing is written down yet, no column, no scale, no value in the table; In a year empty everywhere",
    "D10 after `effect mod1440_chk_pop_round` and `effect mod1440_chk_pop_round10` (paused): game.log has the MOD1440 lines with their times before and after one round and ten rounds over every state, and the months counted; the graph gains the months. Once in vanilla (1081 states); with Road to 56 (1143) if granted",
    "D10 after `effect mod1440_chk_pop_twice`: game.log says the guarded round twice on one day wrote one month (months before and after differ by one; the stamp equals today's day number)",
    "D10 the value check: the chosen state's People in its card and the graph's Latest (no effect: the month on_startup wrote) against the population of the same state in the game's state view (select the state on the map)",
    "D10 error.log: no line names mod1440_pop, mod1440_states_pop, mod1440_states_cards, GFX_1440p_SG_column_*x152 or GFX_1440p_SG_line_2x152",
]
# --- end D10 ---


# ---------------------------------------------------------------- National Figures and History (D4, D5), docked to Politics

# One page beside the politics panel (redesign of 2026-10-16, wiki/phases/D4-national-figures.md): twenty figures
# as tiles that also choose the graph, the chosen figure month by month across the page, and the summed modifiers
# in four lists that show what applies, or all of them.
#
# A row is (label, value, format): the label is a text key of the game (it then follows the player's language)
# or a text of the mod; the value is a variable of the country; the format is what follows the bar in
# "[?value|format]". "+" colours a gain green, "-" colours a gain red (for costs and penalties), "=" adds
# the sign. A value from "modifier@" is the country's summed modifier, the number the game works with.
def modifier_row(key, token, fmt="+=%1"):
    return (key, "modifier@" + token, fmt)


# The groups of summed modifiers: (name, title, column, rows).
FIGURES = [
    ("politics", "Politics", 0, [
        ("Political power per day", "political_power_daily", "+=2"),
        modifier_row("MODIFIER_POLITICAL_POWER_FACTOR", "political_power_factor"),
        modifier_row("MODIFIER_STABILITY_WEEKLY", "stability_weekly", "+=%2"),
        ("Stability from modifiers", "modifier@stability_factor", "+=%1"),
        modifier_row("MODIFIER_WAR_SUPPORT_WEEKLY", "war_support_weekly", "+=%2"),
        ("War support from modifiers", "modifier@war_support_factor", "+=%1"),
        modifier_row("MODIFIER_DRIFT_DEFENCE_FACTOR", "drift_defence_factor"),
        ("Command power per day", "command_power_daily", "+=2"),
        modifier_row("MODIFIER_MAX_COMMAND_POWER", "max_command_power", "+=0"),
        modifier_row("MODIFIER_OPINION_GAIN_MONTHLY_FACTOR", "opinion_gain_monthly_factor"),
        modifier_row("MODIFIER_TRADE_OPINION_FACTOR", "trade_opinion_factor"),
        modifier_row("MODIFIER_JUSTIFY_WAR_GOAL_TIME", "justify_war_goal_time", "-=%1"),
    ]),
    ("manpower", "Manpower", 2, [
        modifier_row("MODIFIER_CONSCRIPTION_FACTOR", "conscription", "%2"),
        modifier_row("MODIFIER_CONSCRIPTION_TOTAL_FACTOR", "conscription_factor"),
        modifier_row("MODIFIER_WEEKLY_MANPOWER", "weekly_manpower", "+=0"),
        modifier_row("MODIFIER_GLOBAL_MONTHLY_POPULATION", "monthly_population"),
        modifier_row("MODIFIER_GLOBAL_NON_CORE_MANPOWER", "non_core_manpower"),
        modifier_row("MODIFIER_MOBILIZATION_SPEED", "mobilization_speed"),
        modifier_row("MODIFIER_TRAINING_TIME_ARMY_FACTOR", "training_time_army_factor", "-=%1"),
        modifier_row("MODIFIER_SPECIAL_FORCES_CAP", "special_forces_cap"),
    ]),
    ("occupation", "Occupation and Diplomacy", 0, [
        modifier_row("MODIFIER_COMPLIANCE_GROWTH", "compliance_growth"),
        modifier_row("MODIFIER_RESISTANCE_TARGET", "resistance_target", "-=%1"),
        modifier_row("MODIFIER_RESISTANCE_GROWTH", "resistance_growth", "-=%1"),
        modifier_row("MODIFIER_RESISTANCE_DECAY", "resistance_decay"),
        modifier_row("MODIFIER_REQUIRED_GARRISON_FACTOR", "required_garrison_factor", "-=%1"),
        modifier_row("MODIFIER_SURRENDER_LIMIT", "surrender_limit"),
        modifier_row("MODIFIER_GUARANTEE_COST", "guarantee_cost", "-=%1"),
        modifier_row("MODIFIER_SEND_VOLUNTEER_SIZE", "send_volunteer_size", "+=0"),
    ]),
    ("industry", "Industry", 1, [
        modifier_row("MODIFIER_INDUSTRIAL_CAPACITY_FACTOR", "industrial_capacity_factory"),
        modifier_row("MODIFIER_INDUSTRIAL_CAPACITY_DOCKYARD_FACTOR", "industrial_capacity_dockyard"),
        modifier_row("MODIFIER_PRODUCTION_FACTORY_MAX_EFFICIENCY_FACTOR", "production_factory_max_efficiency_factor"),
        modifier_row("MODIFIER_PRODUCTION_FACTORY_EFFICIENCY_GAIN_FACTOR", "production_factory_efficiency_gain_factor"),
        modifier_row("MODIFIER_PRODUCTION_FACTORY_START_EFFICIENCY_FACTOR", "production_factory_start_efficiency_factor"),
        modifier_row("MODIFIER_LINE_CHANGE_PRODUCTION_EFFICIENCY_FACTOR", "line_change_production_efficiency_factor"),
        modifier_row("MODIFIER_PRODUCTION_SPEED_BUILDINGS_FACTOR", "production_speed_buildings_factor"),
        modifier_row("MODIFIER_GLOBAL_BUILDING_SLOTS_FACTOR", "global_building_slots_factor"),
        ("Share of factories on consumer goods", "modifier@consumer_goods_expected_value", "%1"),
        modifier_row("MODIFIER_CONSUMER_GOODS_FACTOR", "consumer_goods_factor", "-=%1"),
        ("Civilian to military conversion cost", "modifier@conversion_cost_civ_to_mil_factor", "-=%1"),
        modifier_row("MODIFIER_INDUSTRY_REPAIR_FACTOR", "industry_repair_factor"),
        modifier_row("MODIFIER_LOCAL_RESOURCES_FACTOR", "local_resources_factor"),
        modifier_row("MODIFIER_MIN_EXPORT_FACTOR", "min_export", "%1"),
        modifier_row("MODIFIER_PRODUCTION_LACK_OF_RESOURCE_PENALTY_FACTOR", "production_lack_of_resource_penalty_factor", "-=%1"),
        modifier_row("MODIFIER_FUEL_GAIN_FACTOR", "fuel_gain_factor"),
        modifier_row("MODIFIER_MAX_FUEL_FACTOR", "max_fuel_factor"),
        modifier_row("MODIFIER_PRODUCTION_OIL_FACTOR", "production_oil_factor"),
        modifier_row("MODIFIER_EQUIPMENT_CAPTURE", "equipment_capture"),
    ]),
    ("army", "Army", 2, [
        modifier_row("MODIFIER_ARMY_ORG_FACTOR", "army_org_factor"),
        modifier_row("MODIFIER_ARMY_MORALE_FACTOR", "army_morale_factor"),
        ("Division attack", "modifier@army_attack_factor", "+=%1"),
        ("Division defense", "modifier@army_defence_factor", "+=%1"),
        ("Attack on core territory", "modifier@army_core_attack_factor", "+=%1"),
        ("Defense on core territory", "modifier@army_core_defence_factor", "+=%1"),
        modifier_row("MODIFIER_ARMY_INFANTRY_ATTACK_FACTOR", "army_infantry_attack_factor"),
        modifier_row("MODIFIER_ARMY_ARMOR_ATTACK_FACTOR", "army_armor_attack_factor"),
        modifier_row("MODIFIER_BREAKTHROUGH", "breakthrough_factor"),
        modifier_row("MODIFIER_ARMY_SPEED_FACTOR", "army_speed_factor"),
        modifier_row("MODIFIER_PLANNING_SPEED", "planning_speed"),
        modifier_row("MODIFIER_MAX_PLANNING", "max_planning"),
        modifier_row("MODIFIER_DIG_IN_SPEED_FACTOR", "dig_in_speed_factor"),
        modifier_row("MODIFIER_MAX_DIG_IN_FACTOR", "max_dig_in_factor"),
        modifier_row("MODIFIER_LAND_REINFORCE_RATE", "land_reinforce_rate"),
        modifier_row("MODIFIER_SUPPLY_CONSUMPTION_FACTOR", "supply_consumption_factor", "-=%1"),
        modifier_row("MODIFIER_ATTRITION", "attrition", "-=%1"),
        modifier_row("MODIFIER_OUT_OF_SUPPLY_FACTOR", "out_of_supply_factor", "-=%1"),
        ("Army experience gain", "modifier@experience_gain_army_factor", "+=%1"),
    ]),
    ("research", "Research and Intelligence", 3, [
        modifier_row("MODIFIER_RESEARCH_SPEED_FACTOR", "research_speed_factor"),
        modifier_row("MODIFIER_DECRYPTION_FACTOR", "decryption_factor"),
        modifier_row("MODIFIER_ENCRYPTION_FACTOR", "encryption_factor"),
        modifier_row("MODIFIER_OPERATIVE_SLOT", "operative_slot", "+=0"),
        modifier_row("MODIFIER_INTELLIGENCE_AGENCY_DEFENSE", "intelligence_agency_defense"),
        modifier_row("MODIFIER_INTEL_NETWORK_GAIN_FACTOR", "intel_network_gain_factor"),
    ]),
    ("navy", "Navy", 3, [
        modifier_row("MODIFIER_NAVY_ORG_FACTOR", "navy_org_factor"),
        modifier_row("MODIFIER_NAVAL_MORALE_FACTOR", "naval_morale_factor"),
        modifier_row("MODIFIER_NAVAL_SPEED_FACTOR", "naval_speed_factor"),
        modifier_row("MODIFIER_NAVY_MAX_RANGE_FACTOR", "navy_max_range_factor"),
        modifier_row("MODIFIER_NAVAL_HIT_CHANCE", "naval_hit_chance"),
        modifier_row("MODIFIER_NAVAL_DAMAGE_FACTOR", "naval_damage_factor"),
        modifier_row("MODIFIER_NAVAL_DEFENSE_FACTOR", "naval_defense_factor"),
        modifier_row("MODIFIER_POSITIONING", "positioning"),
        modifier_row("MODIFIER_NAVAL_COORDINATION", "naval_coordination"),
        modifier_row("MODIFIER_SPOTTING_CHANCE", "spotting_chance"),
        modifier_row("MODIFIER_CONVOY_RAIDING_EFFICIENCY_FACTOR", "convoy_raiding_efficiency_factor"),
        modifier_row("MODIFIER_MISSION_CONVOY_ESCORT_EFFICIENCY", "convoy_escort_efficiency"),
        modifier_row("MODIFIER_STAT_CARRIER_SORTIE_EFFICIENCY", "sortie_efficiency"),
        modifier_row("MODIFIER_NAVY_FUEL_CONSUMPTION_FACTOR", "navy_fuel_consumption_factor", "-=%1"),
        ("Navy experience gain", "modifier@experience_gain_navy_factor", "+=%1"),
    ]),
    ("air", "Air Force", 3, [
        modifier_row("MODIFIER_AIR_ATTACK_FACTOR", "air_attack_factor"),
        modifier_row("MODIFIER_AIR_DEFENCE_FACTOR", "air_defence_factor"),
        modifier_row("MODIFIER_AIR_AGILITY_FACTOR", "air_agility_factor"),
        modifier_row("MODIFIER_AIR_RANGE_FACTOR", "air_range_factor"),
        modifier_row("MODIFIER_AIR_MISSION_EFFICIENCY", "air_mission_efficiency"),
        modifier_row("MODIFIER_AIR_SUPERIORITY_EFFICIENCY", "air_superiority_efficiency"),
        modifier_row("MODIFIER_AIR_CAS_EFFICIENCY", "air_cas_efficiency"),
        modifier_row("MODIFIER_STRATEGIC_BOMBER_BOMBING_FACTOR", "air_strategic_bomber_bombing_factor"),
        modifier_row("MODIFIER_AIR_BOMBING_TARGETTING", "air_bombing_targetting"),
        modifier_row("MODIFIER_AIR_DETECTION", "air_detection"),
        modifier_row("MODIFIER_AIR_ACE_GENERATION_CHANCE_FACTOR", "air_ace_generation_chance_factor"),
        modifier_row("MODIFIER_AIR_ACCIDENTS_FACTOR", "air_accidents_factor", "-=%1"),
        modifier_row("MODIFIER_AIR_WEATHER_PENALTY", "air_weather_penalty", "-=%1"),
        modifier_row("MODIFIER_AIR_NIGHT_PENALTY", "air_night_penalty", "-=%1"),
        modifier_row("MODIFIER_AIR_FUEL_CONSUMPTION_FACTOR", "air_fuel_consumption_factor", "-=%1"),
        ("Air experience gain", "modifier@experience_gain_air_factor", "+=%1"),
    ]),
]
# The four lists, left to right: (title, the groups they hold in this order)
NF_COLUMNS = [("Politics and Diplomacy", ["politics", "occupation"]), ("Industry", ["industry"]),
              ("Army and Manpower", ["manpower", "army"]), ("Navy, Air and Research", ["research", "navy", "air"])]
# How a value of a list row is written: the kind a row carries in its list (0 is the head of a group)
NF_FORMATS = ["+=%1", "-=%1", "+=%2", "+=2", "+=0", "%1", "%2"]
RESOURCES = ["oil", "aluminium", "rubber", "tungsten", "steel", "chromium", "coal"]
# --- D9 --- the Equipment table: six vanilla archetypes every army fields (rule 6, decision 4 of 2026-10-22)
NF_EQUIP = ["infantry_equipment", "support_equipment", "artillery_equipment", "anti_tank_equipment", "anti_air_equipment",
            "motorized_equipment"]

# A figure is (caption, value of the country, factor, unit, decimals, rise): the value is written down on the
# first of each month, times the factor (100 turns a 0 to 1 share into a percentage). decimals is how the
# number is written, rise the colour of a change: "+" a rise is green, "-" a rise is red. The first twelve are
# the series of the build before 2026-10-16, in their order: a save keeps their arrays mod1440_h_0 to _11. The
# eight after them start later in such a save and get -1 in front, for the months they were not written down.
SERIES = [
    ("Free manpower", "manpower_k", 1, "in thousands", 1, "+"),
    ("Manpower in the field", "deployed_total_manpower_k", 1, "in thousands", 1, "+"),
    ("Divisions", "num_divisions", 1, "", 0, "+"),
    ("Civilian factories", "num_of_civilian_factories", 1, "", 0, "+"),
    ("Military factories", "num_of_military_factories", 1, "", 0, "+"),
    ("Dockyards", "num_of_naval_factories", 1, "", 0, "+"),
    ("Stability", "stability", 100, "in percent", 1, "+"),
    ("War support", "has_war_support", 100, "in percent", 1, "+"),
    ("Fuel", "fuel_k", 1, "in thousands", 1, "+"),
    ("Infantry equipment", "num_equipment@infantry_equipment", 1, "in stock", 0, "+"),
    ("Casualties", "casualties_k", 1, "in thousands", 1, "-"),
    ("Political power", "political_power", 1, "", 0, "+"),
    ("Research slots", "amount_research_slots", 1, "", 0, "+"),
    ("Technologies", "num_researched_technologies", 1, "researched so far", 0, "+"),
    ("Command power", "command_power", 1, "", 1, "+"),
    ("States controlled", "num_controlled_states", 1, "", 0, "+"),
    ("Convoys in stock", "num_equipment@convoy", 1, "", 0, "+"),
    ("Trains in stock", "num_equipment@train_equipment", 1, "", 0, "+"),
    ("Ships", "num_ships", 1, "", 0, "+"),
    ("Planes on airfields", "num_deployed_planes", 1, "", 0, "+"),
    # --- D4 round 2 (2026-10-17): eleven more, written down from the first month of a game with this build; a save
    # of an earlier build gets their padding for the months before (resource@<r>, army_experience, navy_experience,
    # air_experience and party_popularity_100@ruling_party: dynamic_variables_documentation.md, country scope)
] + [("$PRODUCTION_MATERIALS_%s$ balance" % r.upper(), "resource@" + r, 1, "", 0, "+") for r in RESOURCES] + [
    ("Army experience", "army_experience", 1, "", 1, "+"),
    ("Navy experience", "navy_experience", 1, "", 1, "+"),
    ("Air experience", "air_experience", 1, "", 1, "+"),
    ("Ruling party popularity", "party_popularity_100@ruling_party", 1, "in percent", 1, "+"),
    # --- D9 (2026-10-22, scratch/phases/D9/design.json): nine more. 31 the dead of every war, the mod's own total
    # that never falls (the game's casualties_k counts only the wars in progress); 32 the dead of the month before
    # the record; 33 to 38 the equipment balances of the Equipment table (stock less what the field is short of);
    # 39 surrender progress. 31 and 32 are back-filled from series 10 on a save of an earlier build (mod1440_h_cas_fill).
    ("Casualties, all wars", "mod1440_h_cas_sum", 1, "in thousands", 1, "-"),
    ("Casualties in the month", "mod1440_h_cas_mon", 1, "in thousands", 1, "-"),
] + [("$%s$ balance" % kind, "mod1440_nf_eq_b_%d" % k, 1, "in thousands", 1, "+") for k, kind in enumerate(NF_EQUIP)] + [
    ("Surrender progress", "surrender_progress", 100, "in percent", 1, "-"),
]
H_OLD = 12              # series a save of the build before 2026-10-16 has
# A resource balance can be -1 or lower, so its series (20 to 26) pad with a number below every balance, and a month
# counts above H_RES_LOW; the other newer series pad with -1 (D4 round 2, deviation accepted with the design).
H_RES = list(range(20, 27))
H_RES_PAD = -2100000
H_RES_LOW = -2000000
# --- D9 --- the casualty series (drawn in the strength bar's colour), the equipment balances (which pad as the
# resource balances do: a balance goes below zero), the series of the month (its deadliest month drawn in gold)
H_CAS_SUM, H_CAS_MON, H_SURRENDER = 31, 32, 39
H_LOSS = [H_CAS_SUM, H_CAS_MON]
H_EQ = list(range(33, 39))
H_DEEP = H_RES + H_EQ

# A share on a plate, as the Records' pages use it (tools/build_records.py): the National Figures page had it first.
NF_GAP = 5                      # between the tiles of a band of ten
NF_WIDE = 2 * TILE_W + NF_GAP   # a plate that takes the place of two tiles


def gauge(name, x, y, label, value, variable, tip=None, wide=True):
    """A share on a plate: its name and its value over a bar that script fills from <variable>, 0 to 100.
    A wide gauge has name and value side by side, a narrow one has them one over the other."""
    tooltip = B.key(name + "_tt", tip) if tip else None
    width = NF_WIDE if wide else TILE_W
    out = icon(name + "_bg", x, y, tile_sprite(width))
    if wide:
        out += text(name + "_l", x + 10, y + 9, 110, label, FONT_SMALL, "left", 20, tooltip=tooltip)
        out += text(name, x + 120, y + 6, width - 130, B.key(name, value), FONT_VALUE, "right", 26, tooltip=tooltip)
        out += icon(name + "_bar", x + 8, y + 42, bar_sprite(300))
    else:
        out += text(name + "_l", x + 6, y + 5, width - 12, label, FONT_SMALL, "centre", 20, tooltip=tooltip)
        out += text(name, x + 6, y + 23, width - 12, B.key(name, value), FONT_VALUE, "centre", 24, tooltip=tooltip)
        out += icon(name + "_bar", x + 8, y + 49, bar_sprite(140))
    return out, block(name + "_bar", "frame = %s\n" % variable)


def through(name, x, y, sprite):
    """An icon that lets a click through to the button under it."""
    return 'iconType = { name = "%s" position = { x = %d y = %d } spriteType = "%s" alwaystransparent = yes }\n' % (name, x, y, sprite)


def nf_token(name, words):
    """A text of the mod that script holds as a text key (X37). The key is lower case, as the probe's were and as
    the Records' are (tools/build_records.py, token)."""
    key = "mod1440_" + name
    if B.loc.get(key, words) != words:
        raise ValueError("two texts for " + key)
    B.loc[key] = words
    return "token:" + key


def label_token(name, i, label):
    """A modifier's label as a text key that script holds: a label in capitals is a key of the game; a text of the
    mod gets a key in lower case."""
    if re.match(r"^[A-Z][A-Z0-9_]*$", label):
        return "token:" + label
    return nf_token("nf_%s_%d" % (name, i), label.strip())


# --- D4 round 2 (2026-10-17) ---
# The figures as two banded tables, the resources as a third card whose rows also draw the graph, a graph of 2, 5
# or 10 years across the card, and a Changed view of the modifiers (scratch/phases/D4/design.json; the user chose
# every recommended option on 2026-10-17). The widget names nf_t<series> of the rows stay those of the tiles, so a
# recipe's click on nf_t4 still chooses Military factories.

# The two tables of figures, left to right: (head, series) per group, two groups per card.
NF_TABLES = [
    [("Government", [11, 14, 6, 7, 30, 15]), ("Industry and research", [3, 4, 5, 8, 12, 13])],
    # D9: Manpower and war with the two casualty rows and surrender progress; the game's casualties (series 10, still
    # written down) is the grey extra of the total, infantry equipment (series 9, still written down) went to the
    # Equipment table (decisions 1 and 5 of 2026-10-22)
    [("Manpower and war", [0, 1, 2, H_CAS_SUM, H_CAS_MON, H_SURRENDER]), ("Stock and experience", [16, 17, 18, 19, 27, 28, 29])],
]
NF_SPARKS = [n for table in NF_TABLES for _head, rows in table for n in rows]     # the 25 rows with a sparkline
# D9: a Now that can be below zero gets a red twin with its sign (a second cue beside the colour)
NF_NOW_NEG = {11: ("political_power", "[?political_power|0]")}

# A row of a table: (its value today, a grey value beside it or None, tooltip). Every value is a dynamic variable
# of the game's documentation/dynamic_variables_documentation.md (country scope).
NF_ROWS = {
    11: ("[?political_power|0]", "[?political_power_daily|=2] a day", "Political power, and what you gain each day."),
    14: ("[?command_power|1]", "[?command_power_daily|=2] a day", "Command power, and what you gain each day."),
    6: ("[?stability|%1]", "[?modifier@stability_weekly|=%2] a week", "Stability, and what the weekly modifiers add to it each week."),
    7: ("[?has_war_support|%1]", "[?modifier@war_support_weekly|=%2] a week", "War support, and what the weekly modifiers add to it each week."),
    30: ("[?party_popularity_100@ruling_party|1]%", None, "The popularity of the party in power, as the politics panel shows it among the parties."),
    15: ("[?num_controlled_states|0]", "[?num_core_states|0] cores", "States you control, and how many states are your cores."),
    3: ("£civ_factory [?num_of_civilian_factories|0]", "[?num_of_civilian_factories_available_for_projects|0] free",
        "Your civilian factories, and how many of them are free for construction once consumer goods and trade have taken theirs."),
    4: ("£mil_factory [?num_of_military_factories|0]", "[?num_of_available_military_factories|0] idle",
        "Your military factories, and how many of them have no production line."),
    5: ("£nav_dockyard_texticon [?num_of_naval_factories|0]", "[?num_of_available_naval_factories|0] idle",
        "Your dockyards, and how many of them have no production line."),
    8: ("[?fuel_k|1]K", "of [?max_fuel_k|1]K", "Fuel in your stockpile, and what the stockpile can hold."),
    12: ("[?amount_research_slots|0]", None, "Your research slots."),
    13: ("[?num_researched_technologies|0]", None, "Technologies you have researched."),
    0: ("[?manpower_k|1]K", "[?amount_manpower_in_deployment_queue|*1] training",
        "Men you can still call up: the manpower of the top bar. Beside it, the men of the divisions in training."),
    1: ("[?deployed_total_manpower_k|1]K", None, "Men in your divisions, ships and air wings."),
    2: ("[?num_divisions|0]", None, "Divisions in the field."),
    10: ("[?casualties_k|1]K", None, "Men lost in all your wars. A rise is red."),
    9: ("[?num_equipment@infantry_equipment|0]", None, "Infantry equipment in the stockpile."),
    16: ("[?num_equipment@convoy|0]", None, "Convoys that no trade, supply route or naval invasion uses."),
    17: ("[?num_equipment@train_equipment|0]", None, "Trains in the stockpile."),
    18: ("[?num_ships|0]", None, "Your ships."),
    19: ("[?num_deployed_planes|0]", None, "Planes in your air wings."),
    27: ("[?army_experience|1]", None, "Army experience, which templates, doctrines and designs cost. The top bar shows it too."),
    28: ("[?navy_experience|1]", None, "Navy experience, which ship designs and doctrines cost. The top bar shows it too."),
    29: ("[?air_experience|1]", None, "Air experience, which aircraft designs and doctrines cost. The top bar shows it too."),
    # --- D9 ---
    H_CAS_SUM: ("[?mod1440_h_cas_sum|1]K", "[?casualties_k|1]K in wars",
                "Men lost in all your wars, ended or not. The game's own number, in grey beside it, counts only the wars you are "
                "in now and drops a war's dead when it ends; this page adds its rise each day (since "
                "[?mod1440_h_cas_from.GetDateStringNoHourLong]) and keeps it. A rise is red."),
    H_CAS_MON: ("[?mod1440_h_cas_mon|1]K", "worst [?mod1440_h_cas_worst|1]K",
                "Men lost this month so far; beside it the deadliest month written down. On the graph each column holds the "
                "dead of the month that ends on its date. A rise is red."),
    H_SURRENDER: ("[?surrender_progress|%1]", None, "How close you are to capitulation: at 100% the country surrenders. A rise is red."),
}

# A window of its own on the screen (no parent_window_token, Engine Facts X7; phase D8, 2026-10-21): beside the
# politics panel, which is 550 wide from screen -6, and short of the theatre box under the clock (screen x 2234);
# from under the top bar to above the army portraits.
NF_X, NF_Y, NF_W, NF_H = 550, 78, 1680, 1210
NF_IN = NF_W - 28                       # a band of cards between the margins of the page: 1652
NF_CARD_GAP = 6                              # between the cards of a band
NF_HEAD_H = 28                          # the head bar of a table
NF_ROW = 26                             # a row of a table and of a list of modifiers
# band 1: two tables of figures and the resources
NF_FIG_Y, NF_FIG_H, NF_FIG_W = 56, 418, 600     # D9: 418 (was 388), thirteen rows and two head bars a card
NF_FROW_W = NF_FIG_W - 16               # a row of a figure table: 584
NF_RES_X = 14 + 2 * (NF_FIG_W + NF_CARD_GAP)                 # 1226
NF_RES_W = NF_IN - 2 * (NF_FIG_W + NF_CARD_GAP)              # 440
NF_RROW_W = NF_RES_W - 16               # a row of the resource table: 424
# the columns of a figure row, from the row's left edge (design.json, measured in mock_figures.py)
NF_C_NAME, NF_C_NAME_W = 8, 150         # the longest name, "Ruling party popularity", is 138 px
NF_C_NOW = 250                          # right edge of the value; "12500.0K" is 63 px
NF_C_EXTRA, NF_C_EXTRA_W = 258, 96      # grey, a box of its own size; "125.4K training" is 89 px
NF_C_MONTH, NF_C_YEAR, NF_C_CHANGE_W = 428, 502, 72     # right edges; "+12500.0K" is 71 px
NF_C_SPARK = 512                        # twelve columns 4 px wide on 6 px steps, 18 high: to 584
NF_SPARK_N, NF_SPARK_STEP, NF_SPARK_W, NF_SPARK_H = 12, 6, 4, 18
# the columns of the resource table: right edges of Balance, Made, Used, Import, Export, Month, 52 px each
NF_R_COLS = [164, 216, 268, 320, 372, 420]
# D9: the Equipment table under the resources: the name in a box of 136 px (the game's name of the kind), right
# edges of Stock, Short, Balance and Month (scratch/phases/D9/layout.json)
NF_E_NAME_W = 136
NF_E_COLS = [(216, 60), (276, 56), (344, 64), (420, 60)]
# band 2: the graph
NF_GRAPH_Y, NF_GRAPH_H = NF_FIG_Y + NF_FIG_H + NF_CARD_GAP, 336      # 480 (D9: 336 high, was 322)
NF_NUM_X, NF_NUM_W = 330, 118           # the seven numbers of the chosen figure: a head bar and one row
NF_RANGE_X, NF_RANGE_W, NF_ZOOM_X = 1172, 100, 1498
# band 3: four lists of modifiers
NF_COL_Y = NF_GRAPH_Y + NF_GRAPH_H + NF_CARD_GAP                     # 778
NF_COL_W, NF_COL_H = 404, NF_H - 14 - NF_COL_Y                 # 404 x 374 (D9, was 418)
NF_LIST_ROWS = 12       # D9: twelve rows (decision 7 of 2026-10-22), the rest scrolls
NF_LIST_W = NF_COL_W - 16               # a list in its card, with its scrollbar
# The count beside a card's title (D8 fix round 2): a fixed box after the longest title, "Navy, Air and Research"
# and "Politics and Diplomacy", 242 px in hoi_24header from x 14, plus 14 px; right-aligned to the card's margin.
# 120 px: "188 of 188 apply" is 96 px and "88 since 1938.12.30" 112 in hoi_16mbs, so the date is the short form.
NF_COUNT_X = 14 + 242 + 14
NF_COUNT_W = NF_COL_W - 14 - NF_COUNT_X       # 120
NF_ROW_W = NF_LIST_W - 30               # a row of it: 358

H_KEEP = 120            # months kept: ten years
H_CHART_X, H_CHART_Y = 70, 84           # the frame of the graph in its card (D9: 12 px lower, for the dates)
H_CHART_W, H_CHART_H = 1560, 200        # the columns: as wide in every range
H_STEPS = H_CHART_H     # heights a column can have (the "steps" of the column sprite): one per pixel
H_AXIS = 20             # under the columns: the years
H_YEARS = 10            # year marks under the graph: ten years have at most ten first months
H_INSET = 4             # the columns stand this far inside the frame of the graph
# The ranges: (months, px from one column to the next, a column's width, caption). 24 x 65 = 60 x 26 = 120 x 13.
H_RANGES = [(24, 65, 57, "2 years"), (60, 26, 22, "5 years"), (120, 13, 11, "10 years")]
H_CHART_TOP = NF_GRAPH_Y + H_CHART_Y    # page y of the columns' top: the zero line counts from here


def h_floor(n):
    """A month of series n counts when its value is above this: every month of the first twelve; a month written
    down of a newer series, which has the padding below it for the months before it was written down."""
    if n < H_OLD:
        return None
    return H_RES_LOW if n in H_DEEP else -1


def h_known(n, index):
    """A trigger: the month at index of series n was written down (always yes for the first twelve)."""
    low = h_floor(n)
    return "always = yes" if low is None else "check_variable = { mod1440_h_%d^%s > %d }" % (n, index, low)


def h_suffix(n):
    unit = SERIES[n][3]
    return "K" if unit == "in thousands" else ("%" if unit == "in percent" else "")


def head_bar(name, x, y, width, title, caps=(), height=NF_HEAD_H):
    """The head bar of a table: the vanilla header tile, the title in yellow, the column heads in white
    (x, width, text, format, tooltip or None each)."""
    out = icon(name, x, y, head_sprite(width, height))
    out += text(name + "_t", x + 8, y + 5, 220, B.key(name + "_t", "§Y%s§!" % title), FONT_SMALL, height=20)
    for k, (cx, cw, label, fmt, tip) in enumerate(caps):
        out += text("%s_%d" % (name, k), x + cx, y + 5, cw, B.key("%s_%d" % (name, k), label), FONT_SMALL, fmt, 20,
                    tooltip=B.key("%s_%d_tt" % (name, k), tip) if tip else None)
    return out


def nf_change(name, right, y, variable, has, rise, decimals, suffix):
    """A change in a table: green for a gain, red for a loss (for a figure whose rise is bad, casualties, the other
    way round), a grey dash for no change, nothing while there is no month to compare with. Three texts, of which a
    trigger shows one. Returns the widgets and their triggers."""
    number = "[?%s|=%d]%s" % (variable, decimals, suffix)
    up, down = ("§G", "§R") if rise == "+" else ("§R", "§G")
    x = right - NF_C_CHANGE_W
    out = plain(name + "_up", x, y, NF_C_CHANGE_W, B.key(name + "_up", up + number + "§!"), FONT_LABEL, "right", 22)
    out += plain(name + "_down", x, y, NF_C_CHANGE_W, B.key(name + "_down", down + number + "§!"), FONT_LABEL, "right", 22)
    out += plain(name + "_same", x, y, NF_C_CHANGE_W, B.key("nf_same", DASH), FONT_LABEL, "right", 22)
    known = "check_variable = { %s = 1 }\n" % has
    triggers = (block(name + "_up_visible", known + "check_variable = { %s > 0 }\n" % variable)
                + block(name + "_down_visible", known + "check_variable = { %s < 0 }\n" % variable)
                + block(name + "_same_visible", known + "check_variable = { %s = 0 }\n" % variable))
    return out, triggers


def nf_pick(n, x, y, width, name):
    """The hit area of a row that chooses series n for the graph, its pick band and its name, white or, chosen,
    yellow. Returns the widgets (the band before the hit area, the texts after it), the triggers and the effect."""
    chosen = "check_variable = { mod1440_h_series = %d }\n" % n
    out = through(name + "_pick", x, y, PICK % (width, NF_ROW))
    return (out, block(name + "_pick_visible", chosen)
            + block(name + "_l_visible", "NOT = { %s }\n" % chosen.strip()) + block(name + "_ly_visible", chosen),
            block(name + "_click", "set_variable = { mod1440_h_series = %d }\nmod1440_h_draw = yes\n" % n))


def figure_tables():
    """Band 1: the two tables of figures and the resource card. Returns the cards, the sparkline containers,
    the dynamic lists, triggers, properties and effects."""
    cards, sparks, lists, triggers, properties, effects = "", "", "", "", "", ""
    click = "\\nClick to see its months on the graph."
    for c, groups in enumerate(NF_TABLES):
        inner = ""
        y = 8
        for g, (title, rows) in enumerate(groups):
            # D9: the legend that stood under the resources is in these tooltips
            caps = [(NF_C_NOW - 60, 60, "Now", "right", "Today's value; beside it in grey what goes with it. Below zero it is red, with its sign. "
                     "A click on a row draws its months on the graph below."),
                    (NF_C_MONTH - 66, 66, "Month", "right", "The change since the month before: the newest month written down less the one before. "
                     "§GGreen§! is a gain, §Rred§! a loss; for casualties, surrender and costs the other way round."),
                    (NF_C_YEAR - 66, 66, "Year", "right", "The change since twelve months before. §GGreen§! is a gain, §Rred§! a loss; for "
                     "casualties, surrender and costs the other way round."),
                    (NF_C_SPARK, 72, "12 months", "left", "The last twelve months, a column each, from the lowest of them to the highest. "
                     "When a month is below zero, the months above it stand on a zero level and those below hang §Rred§! from it.")] if g == 0 else []
            inner += head_bar("nf_fh_%d_%d" % (c, g), 8, y, NF_FROW_W, title, caps)
            y += NF_HEAD_H
            for r, n in enumerate(rows):
                ry = y + r * NF_ROW
                caption, variable, factor, unit, decimals, rise = SERIES[n]
                now, extra, tip = NF_ROWS[n]
                name = "nf_t%d" % n
                if r % 2:
                    inner += icon(name + "_band", 8, ry, STRIPE % (NF_FROW_W, NF_ROW))
                band, more, clicked = nf_pick(n, 8, ry, NF_FROW_W, name)
                inner += band
                triggers += more
                effects += clicked
                inner += button(name, 8, ry, "GFX_1440p_SG_hit_%dx%d" % (NF_FROW_W, NF_ROW), tooltip=B.key(name + "_tt", tip + click))
                label = B.key("h_series_%d" % n, caption)
                inner += plain(name + "_l", 8 + NF_C_NAME, ry + 4, NF_C_NAME_W, label, FONT_SMALL, height=20)
                inner += plain(name + "_ly", 8 + NF_C_NAME, ry + 4, NF_C_NAME_W, B.key(name + "_ly", "§Y%s§!" % caption), FONT_SMALL, height=20)
                inner += plain(name + "_v", 8 + NF_C_NOW - 92, ry + 2, 92, B.key(name + "_v", now), FONT_LABEL, "right", 22)
                if n in NF_NOW_NEG:     # D9: below zero, red with its sign
                    below = "check_variable = { %s < 0 }" % NF_NOW_NEG[n][0]
                    inner += plain(name + "_vn", 8 + NF_C_NOW - 92, ry + 2, 92, B.key(name + "_vn", "§R%s§!" % NF_NOW_NEG[n][1]), FONT_LABEL, "right", 22)
                    triggers += block(name + "_v_visible", "NOT = { %s }\n" % below) + block(name + "_vn_visible", below + "\n")
                if extra:
                    inner += ar_text(name + "_x", 8 + NF_C_EXTRA, ry + 4, NF_C_EXTRA_W, B.key(name + "_x", "§g%s§!" % extra), FONT_SMALL, height=20, fixed=True)
                for part, right, has in (("m", NF_C_MONTH, "hm"), ("y", NF_C_YEAR, "hy")):
                    out, more = nf_change("%s_%s" % (name, part), 8 + right, ry + 2, "mod1440_h_tab_d%s^%d" % (part, n),
                                          "mod1440_h_tab_%s^%d" % (has, n), rise, decimals, h_suffix(n))
                    inner += out
                    triggers += more
                # the sparkline: a grid of twelve columns from the array mod1440_h_sp_<n>, with its own row container
                inner += ('gridboxtype = {\n\tname = "nf_sp%d_grid"\n\tposition = { x = %d y = %d }\n\tsize = { width = %d height = %d }\n'
                          '\tslotsize = { width = %d height = %d }\n\tadd_horizontal = yes\n\tmax_slots_horizontal = %d\n\tformat = "UPPER_LEFT"\n}\n'
                          % (n, 8 + NF_C_SPARK, ry + 4, NF_SPARK_N * NF_SPARK_STEP, NF_SPARK_H, NF_SPARK_STEP, NF_SPARK_H, NF_SPARK_N))
                lists += block("nf_sp%d_grid" % n, 'array = mod1440_h_sp_%d\nentry_container = "mod1440_figures_spark_%d"\n' % (n, n))
                # D9: a month below zero hangs red from the zero level (mod1440_h_spz_<n>, a height of the column): the
                # red bar fills to the zero level and a mask of the column's own background covers it up to the month's
                # height; a month above it fills to its height and the mask covers it up to the zero level. The sign of
                # each month is in mod1440_h_spn_<n>; a figure that never goes below zero has a zero level of 0.
                tip = B.key("nf_sp_tt", "A month of the last twelve: the lowest of them stands lowest, the highest full; below zero a month hangs red.")
                colour = "spark_loss" if n in H_LOSS else "spark"
                neg = "check_variable = { mod1440_h_spn_%d^i = 1 }" % n
                sparks += row("mod1440_figures_spark_%d" % n, NF_SPARK_STEP, NF_SPARK_H, (
                    'iconType = { name = "nf_sp%d" position = { x = 0 y = 0 } spriteType = "GFX_1440p_SG_%s_%dx%d" pdx_tooltip = "%s" }\n'
                    % (n, colour, NF_SPARK_W, NF_SPARK_H, tip)
                    + 'iconType = { name = "nf_spr%d" position = { x = 0 y = 0 } spriteType = "GFX_1440p_SG_spark_red_%dx%d" pdx_tooltip = "%s" }\n'
                    % (n, NF_SPARK_W, NF_SPARK_H, tip)
                    + through("nf_spm%d" % n, 0, 0, "GFX_1440p_SG_spark_mask_%dx%d" % (NF_SPARK_W, NF_SPARK_H))
                    + through("nf_spn%d" % n, 0, 0, "GFX_1440p_SG_spark_mask_%dx%d" % (NF_SPARK_W, NF_SPARK_H))))
                properties += (block("nf_sp%d" % n, "frame = v\n") + block("nf_spr%d" % n, "frame = mod1440_h_spz_%d\n" % n)
                               + block("nf_spm%d" % n, "frame = mod1440_h_spz_%d\n" % n) + block("nf_spn%d" % n, "frame = v\n"))
                triggers += (block("nf_sp%d_visible" % n, "check_variable = { v > -1 }\nNOT = { %s }\n" % neg)
                             + block("nf_spr%d_visible" % n, "check_variable = { v > -1 }\n%s\n" % neg)
                             + block("nf_spm%d_visible" % n, "check_variable = { v > -1 }\nNOT = { %s }\ncheck_variable = { mod1440_h_spz_%d > 0 }\n" % (neg, n))
                             + block("nf_spn%d_visible" % n, "check_variable = { v > -1 }\n%s\n" % neg))
            y += len(rows) * NF_ROW + 4
        cards += box("nf_fig_%d" % c, 14 + c * (NF_FIG_W + NF_CARD_GAP), NF_FIG_Y, NF_FIG_W, NF_FIG_H, inner, CARD_BG)

    # the resources: the live table of the build before, with the change of the balance in a month; a row draws
    # the balance on the graph (series 20 to 26)
    cols = [("balance", "Balance", "resource", "+=0", "What is left after your own use and your exports."),
            ("made", "Made", "resource_produced", "0", "Produced in your states."),
            ("used", "Used", "resource_consumed", "0", "Used by your production lines."),
            ("in", "Import", "resource_imported", "0", "Bought from other countries."),
            ("out", "Export", "resource_exported", "0", "Sold to other countries.")]
    caps = [(right - 48, 48, caption, "right", tip) for (cname, caption, variable, fmt, tip), right in zip(cols, NF_R_COLS)]
    caps.append((NF_R_COLS[5] - 48, 48, "Month", "right", "The change of the balance since the month before."))
    inner = head_bar("nf_rh", 8, 8, NF_RROW_W, "Resources", caps)
    for r, resource in enumerate(RESOURCES):
        n = H_RES[r]
        ry = 8 + NF_HEAD_H + r * NF_ROW
        name = "nf_t%d" % n
        if r % 2:
            inner += icon(name + "_band", 8, ry, STRIPE % (NF_RROW_W, NF_ROW))
        band, more, clicked = nf_pick(n, 8, ry, NF_RROW_W, name)
        inner += band
        triggers += more
        effects += clicked
        inner += button(name, 8, ry, "GFX_1440p_SG_hit_%dx%d" % (NF_RROW_W, NF_ROW), tooltip=B.key(name + "_tt", "The balance of this resource: made and bought, less what your lines use and what you sell." + click))
        label = "£resources_strip|%d  $PRODUCTION_MATERIALS_%s$" % (r + 1, resource.upper())
        inner += plain(name + "_l", 16, ry + 2, 110, B.key("nf_res_name_%d" % r, label), FONT_SMALL, height=22)
        inner += plain(name + "_ly", 16, ry + 2, 110, B.key(name + "_ly", "£resources_strip|%d  §Y$PRODUCTION_MATERIALS_%s$§!" % (r + 1, resource.upper())), FONT_SMALL, height=22)
        for (cname, caption, variable, fmt, tip), right in zip(cols, NF_R_COLS):
            inner += plain("nf_res_%s_%d" % (cname, r), 8 + right - 48, ry + 2, 48,
                           B.key("nf_res_%s_%d" % (cname, r), "[?%s@%s|%s]" % (variable, resource, fmt)), FONT_LABEL, "right", 22)
        out, more = nf_change("%s_m" % name, 8 + NF_R_COLS[5], ry + 2, "mod1440_h_tab_dm^%d" % n, "mod1440_h_tab_hm^%d" % n, "+", 0, "")
        inner += out
        triggers += more
    # D9: the legend that stood here is in the tooltips of the column heads; the Equipment table takes its place
    part, more, clicked = equipment_table(8 + NF_HEAD_H + len(RESOURCES) * NF_ROW + 4)
    inner += part
    triggers += more
    effects += clicked
    cards += box("nf_res", NF_RES_X, NF_FIG_Y, NF_RES_W, NF_FIG_H, inner, CARD_BG)
    triggers += resource_triggers()
    return cards, sparks, lists, triggers, properties, effects


def resource_triggers():
    return "".join(block("nf_res_%s_%d_visible" % (cname, r), more_than_zero("%s@%s" % (variable, resource)))
                   for r, resource in enumerate(RESOURCES)
                   for cname, variable in (("made", "resource_produced"), ("used", "resource_consumed"),
                                           ("in", "resource_imported"), ("out", "resource_exported")))


# --- D9 ---
def equipment_table(y):
    """The Equipment table under the resources, from card y: a head bar and a row per kind of NF_EQUIP with its stock,
    what the field is short of, the balance (green above zero, red below with its sign) and its change in a month.
    The values are the daily count mod1440_nf_equip (in thousands), so the numbers of a row always agree; a row
    draws its balance on the graph (series 33 to 38). Returns the widgets, triggers and effects."""
    out, triggers, effects = "", "", ""
    tips = [("Stock", "In the stockpile, in thousands."),
            ("Short", "What your divisions in the field lack of it, in thousands: what they need less what they hold, as Army "
                      "Readiness counts it. Divisions in training are not counted."),
            ("Balance", "The stock less what the field is short of, in thousands: §Rred§! below zero, when the field lacks more "
                        "than the stockpile holds."),
            ("Month", "The change of the balance since the month before.")]
    caps = [(right - width, width, caption, "right", tip) for (right, width), (caption, tip) in zip(NF_E_COLS, tips)]
    out += head_bar("nf_eh", 8, y, NF_RROW_W, "Equipment", caps)
    y += NF_HEAD_H
    (s_right, s_w), (d_right, d_w), (b_right, b_w), (m_right, _m_w) = NF_E_COLS
    for k, kind in enumerate(NF_EQUIP):
        n = H_EQ[k]
        ry = y + k * NF_ROW
        name = "nf_t%d" % n
        if k % 2:
            out += icon(name + "_band", 8, ry, STRIPE % (NF_RROW_W, NF_ROW))
        band, more, clicked = nf_pick(n, 8, ry, NF_RROW_W, name)
        out += band
        triggers += more
        effects += clicked
        out += button(name, 8, ry, "GFX_1440p_SG_hit_%dx%d" % (NF_RROW_W, NF_ROW), tooltip=B.key("nf_eq_tt", (
            "This kind of equipment: in stock, what your divisions in the field are short of, and the balance of the two. "
            "Counted each day.\\nClick to see the balance's months on the graph.")))
        # the game's name of the kind, in a box of its own size (another mod may make it longer, W28)
        out += ar_text(name + "_l", 16, ry + 4, NF_E_NAME_W, B.key("nf_eq_name_%d" % k, "$%s$" % kind), FONT_SMALL, height=20, fixed=True)
        out += ar_text(name + "_ly", 16, ry + 4, NF_E_NAME_W, B.key(name + "_ly", "§Y$%s$§!" % kind), FONT_SMALL, height=20, fixed=True)
        s, d, b = ("mod1440_nf_eq_%s_%d" % (part, k) for part in "sdb")
        for widget, right, width, words, shown in (
                ("nf_eq_s_%d" % k, s_right, s_w, "[?%s|1]K" % s, "check_variable = { %s > 0 }" % s),
                ("nf_eq_s0_%d" % k, s_right, s_w, "0", "NOT = { check_variable = { %s > 0 } }" % s),
                ("nf_eq_d_%d" % k, d_right, d_w, "§R[?%s|1]K§!" % d, "check_variable = { %s > 0 }" % d),
                ("nf_eq_d0_%d" % k, d_right, d_w, DASH, "NOT = { check_variable = { %s > 0 } }" % d),
                ("nf_eq_b_%d" % k, b_right, b_w, "§G[?%s|=1]K§!" % b, "check_variable = { %s > 0 }" % b),
                ("nf_eq_bn_%d" % k, b_right, b_w, "§R[?%s|=1]K§!" % b, "check_variable = { %s < 0 }" % b),
                ("nf_eq_b0_%d" % k, b_right, b_w, "0", "check_variable = { %s = 0 }" % b)):
            key = B.key("nf_same", DASH) if words == DASH else B.key("nf_eq_zero", "0") if words == "0" else B.key(widget, words)
            out += plain(widget, 8 + right - width, ry + 2, width, key, FONT_LABEL, "right", 22)
            triggers += block(widget + "_visible", shown + "\n")
        part, more = nf_change("%s_m" % name, 8 + m_right, ry + 2, "mod1440_h_tab_dm^%d" % n, "mod1440_h_tab_hm^%d" % n, "+", 1, "K")
        out += part
        triggers += more
    return out, triggers, effects


def equipment_count():
    """The daily count of the Equipment table, for the country in scope: per kind the stock, the shortfall of the
    divisions in the field (what they need less what they hold, never below 0; X29: divisions in training are not
    counted) and the balance, in thousands. Six blocks of three variables, no loop (rule 5)."""
    body = ""
    for k, kind in enumerate(NF_EQUIP):
        s, d, b = ("mod1440_nf_eq_%s_%d" % (part, k) for part in "sdb")
        body += (tmp("nf_es", "num_equipment@" + kind) + tmp("nf_ed", "num_target_equipment_in_armies@" + kind)
                 + tmp("nf_ef", "num_equipment_in_armies@" + kind) + "subtract_from_temp_variable = { nf_ed = nf_ef }\n"
                 + iff("check_variable = { nf_ed < 0 }", tmp("nf_ed", 0))
                 + setv(s, "nf_es") + "divide_variable = { %s = 1000 }\n" % s
                 + setv(d, "nf_ed") + "divide_variable = { %s = 1000 }\n" % d
                 + setv(b, "nf_es") + "subtract_from_variable = { %s = nf_ed }\ndivide_variable = { %s = 1000 }\n" % (b, b))
    return ("# National Figures: the Equipment table of the country in scope (D9), each day for a player and before each\n"
            "# monthly record: stock, shortfall in the field and balance of six kinds, in thousands.\n"
            + block("mod1440_nf_equip", body))
# --- end D9 ---


# --- D9 --- the note under a figure's name on the graph: the deadliest month of the month's casualties (the month on
# the graph whose column is gold), what the total counts, what an equipment balance is
H_NOTES = {H_CAS_SUM: "§gThe dead of every war, ended or not§!",
           H_CAS_MON: "§YDeadliest: the month to [?mod1440_h_max_date.GetDateStringNoHourLong]§!"}
H_NOTES.update({n: "§gIn stock less what the field is short of§!" for n in H_EQ})


def h_first_x(step):
    """Page x of the first year mark (a text 40 wide under the middle of the first column)."""
    return 14 + H_CHART_X + H_INSET + step // 2 - 20


def figure_graph():
    """Band 2: the chosen figure's name, seven numbers, the range, and its months as columns. Returns its inside,
    the widgets of the page (year marks and zero line: script moves them), the column entries, the dynamic lists,
    triggers, properties, effects and the script that places the year marks."""
    triggers, properties, effects = "", "", ""
    some = more_than_zero("mod1440_h_valid")
    inner = ""
    for n, (caption, variable, factor, unit, decimals, rise) in enumerate(SERIES):
        # the name, and under it in grey what the columns show
        chosen = "check_variable = { mod1440_h_series = %d }\n" % n
        inner += text("h_name_%d" % n, 14, 10, 312, B.key("h_name_%d" % n, caption), FONT_CARD, height=30)
        inner += text("h_unit_%d" % n, 14, 40, 312, B.key("h_unit_%d" % n, "§gThe last [?mod1440_h_yrs|0] years of [?mod1440_h_total|0] months%s§!"
                                                           % (", " + unit if unit else "")), FONT_SMALL, height=20)
        triggers += block("h_name_%d_visible" % n, chosen) + block("h_unit_%d_visible" % n, chosen + some)
        if n in H_NOTES:        # D9: a third line, the figure's note
            inner += text("h_note_%d" % n, 14, 60, 312, B.key("h_note_%d" % n, H_NOTES[n]), FONT_SMALL, height=20)
            triggers += block("h_note_%d_visible" % n, chosen + some)

    def number(name, x, y, width, variable, font, fmt, signed=False, when="", tooltip=None):
        """A number of the chosen figure with its own decimals, and a change in the colours of its figure: one text
        for each way of writing, of which a trigger shows one."""
        out, extra = "", ""
        for decimals in (0, 1):
            for rise in (("+", "-") if signed else ("",)):
                widget = "%s_%d%s" % (name, decimals, {"+": "", "-": "r", "": ""}[rise])
                out += text(widget, x, y, width, B.key(widget, "[?%s|%s%s%d]" % (variable, rise, "=" if signed else "", decimals)), font, fmt, 24,
                            tooltip=tooltip)
                shown = some + when + "check_variable = { mod1440_h_dec = %d }\n" % decimals
                if signed:
                    shown += "check_variable = { mod1440_h_rise = %d }\nNOT = { check_variable = { %s = 0 } }\n" % (1 if rise == "+" else 0, variable)
                extra += block(widget + "_visible", shown)
        if signed:
            # no change: a grey dash, as in the tables
            out += text(name + "_same", x, y, width, B.key("nf_same", DASH), font, fmt, 24, tooltip=tooltip)
            extra += block(name + "_same_visible", some + when + "check_variable = { %s = 0 }\n" % variable)
        return out, extra

    # The seven numbers as one row of a table. Latest stays: it is the month the changes count from, which is not
    # today's value in the table above until the next first of the month.
    plates = [("latest", "Latest", "mod1440_h_latest", False, "", "The newest month written down: the changes count from it."),
              ("dm", "In a month", "mod1440_h_dm", True, is_one("mod1440_h_has_m") + "\n", "The change since the month before."),
              ("dy", "In a year", "mod1440_h_dy", True, is_one("mod1440_h_has_y") + "\n", "The change since twelve months before."),
              ("max", "Highest", "mod1440_h_max", False, "", "The highest month on the graph: [?mod1440_h_max_date.GetDateStringNoHourLong]."),
              ("min", "Lowest", "mod1440_h_min", False, "", "The lowest month on the graph: [?mod1440_h_min_date.GetDateStringNoHourLong]."),
              ("change", "Over the range", "mod1440_h_change", True, "", "The newest month less the oldest month on the graph.")]
    inner += icon("h_nums_head", NF_NUM_X, 8, head_sprite(NF_NUM_W * (len(plates) + 1), 26))
    # D9: the month's casualties (series 32) read Deadliest for Highest and In the range, the sum of the months on the
    # graph, for Over the range; Highest and Lowest give their month under the number ("to" it for a monthly count)
    month = "check_variable = { mod1440_h_series = %d }" % H_CAS_MON
    other = "NOT = { %s }" % month
    twins = {"max": ("Deadliest", "The deadliest month on the graph: the month to [?mod1440_h_max_date.GetDateStringNoHourLong]."),
             "change": ("In the range", "The dead of the months on the graph, added up.")}
    for k, (name, label, variable, signed, when, tip) in enumerate(plates):
        x = NF_NUM_X + k * NF_NUM_W
        tooltip = B.key("h_%s_tt" % name, tip)
        inner += text("h_%s_l" % name, x, 12, NF_NUM_W, B.key("h_%s_l" % name, "§g%s§!" % label), FONT_SMALL, "centre", 18, tooltip=tooltip)
        if name == "change":
            when += other + "\n"
        part, more = number("h_" + name, x, 36, NF_NUM_W, variable, FONT_LABEL, "centre", signed, when, tooltip)
        inner += part
        triggers += more
        if name in twins:
            twin = "sum" if name == "change" else name + "32"
            words, twin_tip = twins[name]
            twin_tt = B.key("h_%s_tt" % twin, twin_tip)
            inner += text("h_%s_l" % twin, x, 12, NF_NUM_W, B.key("h_%s_l" % twin, "§g%s§!" % words), FONT_SMALL, "centre", 18, tooltip=twin_tt)
            triggers += block("h_%s_l_visible" % name, other + "\n") + block("h_%s_l_visible" % twin, month + "\n")
            if name == "change":
                part, more = number("h_sum", x, 36, NF_NUM_W, "mod1440_h_sum", FONT_LABEL, "centre", False, month + "\n", twin_tt)
                inner += part
                triggers += more
        if name in ("max", "min"):
            for suffix, words, shown in (("d", "§g[?mod1440_h_%s_date.GetDateStringNoHour]§!" % name, other),
                                         ("d32", "§gto [?mod1440_h_%s_date.GetDateStringNoHour]§!" % name, month)):
                inner += text("h_%s_%s" % (name, suffix), x, 58, NF_NUM_W, B.key("h_%s_%s" % (name, suffix), words), FONT_SMALL, "centre", 18,
                              tooltip=tooltip)
                triggers += block("h_%s_%s_visible" % (name, suffix), some + shown + "\n")
    x = NF_NUM_X + len(plates) * NF_NUM_W
    tooltip = B.key("h_months_tt", "Months on the graph, of the months written down for this figure (120 at most).")
    inner += text("h_months_l", x, 12, NF_NUM_W, B.key("h_months_l", "§gMonths§!"), FONT_SMALL, "centre", 18, tooltip=tooltip)
    inner += text("h_months", x, 36, NF_NUM_W, B.key("h_months", "[?mod1440_h_valid|0] of [?mod1440_h_total|0]"), FONT_LABEL, "centre", 24, tooltip=tooltip)

    # the range: 2, 5 or 10 years; until the player picks one, the shortest that holds every month written down
    for k, (span, step, width, caption) in enumerate(H_RANGES):
        x = NF_RANGE_X + k * (NF_RANGE_W + 4)
        name = "h_range_%d" % span
        # the form of the working sort buttons (Zoom in, the Records filters): the caption on the button, the chosen
        # range on frame 2 (gold chevrons). A button without buttonText under two caption twins drew nothing and took
        # no click in the game (D8 fix round 1)
        inner += button(name, x, 10, "GFX_sort_button_100x29", B.key(name, caption), tooltip=B.key(name + "_tt", (
            "The last %s on the graph, a column a month. Until you pick a range, the graph takes the shortest that holds "
            "every month written down." % caption)))
        effects += block(name + "_click", setv("mod1440_h_range", span) + "mod1440_h_draw = yes\n")
        properties += block(name, "frame = mod1440_h_rf_%d\n" % span)
    inner += button("h_zoom", NF_ZOOM_X, 10, "GFX_sort_button_140x29", B.key("h_zoom", "Zoom in"), tooltip=B.key(
        "h_zoom_tt", "The columns start at the lowest month instead of at zero, so that small changes show."))
    effects += block("h_zoom_click", flip("mod1440_h_zoom") + "mod1440_h_draw = yes\n")
    properties += block("h_zoom", "frame = mod1440_h_zoom_frame\n")

    # the scale on the left: five heights, from the foot of the columns to the top
    for k in range(5):
        part, more = number("h_scale_%d" % k, 14, H_CHART_Y + H_CHART_H - k * (H_CHART_H // 4) - 10, H_CHART_X - 20,
                            "mod1440_h_s%d" % k, FONT_SMALL, "right")
        inner += part
        triggers += more
    # the columns stand on bands a quarter of the height each, and have the years under them; one grid per range,
    # of which script fills one and empties the other two (a nested container cannot be hidden, X15)
    chart = "".join(icon("h_band_%d" % k, H_INSET, k * (H_CHART_H // 4), STRIPE % (H_CHART_W, H_CHART_H // 4)) for k in (1, 3))
    columns, lists = "", ""
    tip = B.key("h_bar_tt", "[?mod1440_h_sdate^i.GetDateStringNoHourLong]: [?mod1440_h_now^i|1]")
    for span, step, width, caption in H_RANGES:
        chart += ('gridboxtype = {\n\tname = "h_grid_%d"\n\tposition = { x = %d y = 0 }\n\tsize = { width = %d height = %d }\n'
                  '\tslotsize = { width = %d height = %d }\n\tadd_horizontal = yes\n\tmax_slots_horizontal = %d\n\tformat = "UPPER_LEFT"\n}\n'
                  % (span, H_INSET, H_CHART_W, H_CHART_H + H_AXIS, step, H_CHART_H + H_AXIS, span))
        lists += block("h_grid_%d" % span, 'array = mod1440_h_bars_%d\nentry_container = "mod1440_figures_col_%d"\n' % (span, span))
        # a column: a month that was not written down for this figure (-1) is left out. D9: the casualty series in the
        # strength bar's colour, the deadliest month of series 32 in gold; a month below zero hangs red from the zero
        # level (mod1440_h_zero_h): the red bar fills to the zero level and a mask of the column's own background
        # covers it up to the month's height; a month above zero fills to its height and the mask covers it up to the
        # zero level. The sign of each month is in mod1440_h_neg_<span>; a figure that never goes below zero has a
        # zero level of 0 and draws as before.
        at = (step - width) // 2
        cells = ""
        for widget, sprite, has_tip in (("h_bar", "column", True), ("h_loss", "column_loss", True), ("h_gold", "column_gold", True),
                                        ("h_red", "column_red", True), ("h_mask", "mask", False), ("h_maskn", "mask", False)):
            if has_tip:
                cells += ('iconType = { name = "%s%d" position = { x = %d y = 0 } spriteType = "GFX_1440p_SG_%s_%dx%d" pdx_tooltip = "%s" }\n'
                          % (widget, span, at, sprite, width, H_CHART_H, tip))
            else:
                cells += through("%s%d" % (widget, span), at, 0, "GFX_1440p_SG_%s_%dx%d" % (sprite, width, H_CHART_H))
        columns += row("mod1440_figures_col_%d" % span, step, H_CHART_H + H_AXIS, cells)
        known = "check_variable = { v > -1 }\n"
        neg = "check_variable = { mod1440_h_neg_%d^i = 1 }" % span
        gold = "check_variable = { mod1440_h_gold = 1 } check_variable = { i = mod1440_h_max_i }"
        loss = is_one("mod1440_h_loss")
        for widget, frame, shown in (("h_bar", "v", "NOT = { %s }\nNOT = { %s }\n" % (neg, loss)),
                                     ("h_loss", "v", "%s\nNOT = { AND = { %s } }\n" % (loss, gold)),
                                     ("h_gold", "v", gold + "\n"),
                                     ("h_red", "mod1440_h_zero_h", neg + "\n"),
                                     ("h_mask", "mod1440_h_zero_h", "NOT = { %s }\ncheck_variable = { mod1440_h_zero_h > 0 }\n" % neg),
                                     ("h_maskn", "v", neg + "\n")):
            properties += block("%s%d" % (widget, span), "frame = %s\n" % frame)
            triggers += block("%s%d_visible" % (widget, span), known + shown)
    inner += box("h_chart", H_CHART_X, H_CHART_Y, H_CHART_W + 2 * H_INSET, H_CHART_H + H_AXIS, chart, CARD_BG)
    below = H_CHART_Y + H_CHART_H + H_AXIS + 4
    inner += text("h_from", H_CHART_X + H_INSET, below, 300, B.key("h_from", "[?mod1440_h_first.GetDateStringNoHourLong]"), FONT_SMALL, height=20)
    inner += text("h_to", H_CHART_X + H_INSET + H_CHART_W - 300, below, 300, B.key("h_to", "[?mod1440_h_last.GetDateStringNoHourLong]"), FONT_SMALL, "right", 20)
    # a game that got the mod after its start, and a figure the build before this one did not write down, have
    # nothing until the first of the next month
    inner += text("h_none", H_CHART_X + 20, H_CHART_Y + 80, 1000, B.key(
        "h_none", "Nothing is written down for this figure yet. The first column comes on the first of next month."), FONT_LABEL)
    triggers += block("h_none_visible", "NOT = { %s }\n" % some.strip())
    for name in ("h_from", "h_to", "h_months", "h_months_l"):
        triggers += block(name + "_visible", some)

    # Under the columns, the year at each first month of a new year on the graph; a 2 px line at zero for a figure
    # that goes below it. They belong to the page, and script moves them (x and y properties, Engine Facts X4).
    page = ""
    marks = ""          # script: the k-th year mark gets its year and its place
    for k in range(H_YEARS):
        page += text("h_year_%d" % k, h_first_x(H_RANGES[0][1]), H_CHART_TOP + H_CHART_H + 1, 40,
                     B.key("h_year_%d" % k, "[?mod1440_h_yl_%d|0]" % k), FONT_SMALL, "centre", 18)
        properties += block("h_year_%d" % k, "x = mod1440_h_yx_%d\n" % k)
        triggers += block("h_year_%d_visible" % k, more_than_zero("mod1440_h_yl_%d" % k))
        marks += iff("check_variable = { h_slot = %d }" % k, setv("mod1440_h_yl_%d" % k, "h_y") + setv("mod1440_h_yx_%d" % k, "h_x"),
                     "if" if k == 0 else "else_if")
    page += 'iconType = { name = "h_zero" position = { x = %d y = %d } spriteType = "GFX_1440p_SG_line_%dx2" alwaystransparent = yes }\n' % (
        14 + H_CHART_X + H_INSET, H_CHART_TOP + H_CHART_H - 1, H_CHART_W)
    properties += block("h_zero", "y = mod1440_h_zero_y\n")
    triggers += block("h_zero_visible", is_one("mod1440_h_zero") + "\n")
    # D9: the scale's own 0 beside the zero line, moved with it
    page += plain("h_scale_zero", 14 + 14, H_CHART_TOP + H_CHART_H - 10, H_CHART_X - 20, B.key("h_scale_zero", "0"), FONT_SMALL, "right", 20)
    properties += block("h_scale_zero", "y = mod1440_h_zero_sy\n")
    triggers += block("h_scale_zero_visible", is_one("mod1440_h_zero") + "\n")
    # the years of the months on the graph get a mark under the first month of each year after the first
    place = ("".join(setv("mod1440_h_yl_%d" % k, 0) for k in range(H_YEARS)) + tmp("h_before", 0) + tmp("h_slot", 0)
        + block("for_each_loop", (
            "array = mod1440_h_syear\nvalue = h_y\nindex = h_yi\n"
            + iff("check_variable = { h_yi > 0 }", iff("check_variable = { h_y > 0 }", iff("NOT = { check_variable = { h_y = h_before } }", (
                tmp("h_x", "h_yi") + "multiply_temp_variable = { h_x = h_step }\nadd_to_temp_variable = { h_x = h_off }\n"
                + marks + "add_to_temp_variable = { h_slot = 1 }\n"))))
            + tmp("h_before", "h_y"))))
    return inner, page, columns, lists, triggers, properties, effects, place


# How the change of a modifier is coloured in the Changed view: a row whose format is plain (no colour for its
# value) gets the sense of its change here; the others take it from their format.
NF_CHANGE_SENSE = {"modifier@consumer_goods_expected_value": "-", "modifier@min_export": "-"}


def nf_change_format(value, fmt):
    sense = fmt[0] if fmt[0] in "+-" else NF_CHANGE_SENSE.get(value, "+")
    return sense + "=" + fmt.lstrip("+-").lstrip("=")


NF_CHANGES = []         # the ways a change is written, in the order first met
for _name, _title, _column, _entries in FIGURES:
    for _label, _value, _fmt in _entries:
        if nf_change_format(_value, _fmt) not in NF_CHANGES:
            NF_CHANGES.append(nf_change_format(_value, _fmt))
NF_NOW = [fmt.lstrip("+-") for fmt in NF_FORMATS]       # the value now, grey, in the Changed view
NF_VIEWS = [("applies", "What applies", "Only the modifiers that are not 0."),
            ("all", "All modifiers", "Every modifier the page knows, those that are 0 in grey."),
            ("changed", "Changed", "The modifiers that are not what they were on the first of the month, with the change "
                                   "and the value now. The first of each month writes the values down again.")]
NF_MODIFIERS = [value for _name, _title, _column, entries in FIGURES for _label, value, _fmt in entries]    # mod1440_nf_was


def modifier_lists():
    """The four cards of summed modifiers, each one list of the groups it holds. Returns the cards, the four row
    containers, the dynamic lists, triggers and the fill effect."""
    cards, rows, lists, triggers, fill = "", "", "", "", ""
    groups = {name: (title, column, entries) for name, title, column, entries in FIGURES}
    first = {}          # the index in mod1440_nf_was of each group's first modifier
    count = 0
    for name, title, column, entries in FIGURES:
        first[name] = count
        count += len(entries)
    changed = "check_variable = { mod1440_nf_all = 2 }"
    was = "check_variable = { mod1440_nf_was^num > 0 }"
    for c, (title, names) in enumerate(NF_COLUMNS):
        x = 14 + c * (NF_COL_W + 12)
        total = sum(len(groups[g][2]) for g in names)
        inner = text("nf_c%d_count" % c, NF_COUNT_X, 16, NF_COUNT_W, B.key("nf_c%d_count" % c, "§g[?mod1440_nf_a%d|0] of %d apply§!" % (c, total)),
                     FONT_SMALL, "right", 20, fixed=True)
        inner += text("nf_c%d_since" % c, NF_COUNT_X, 16, NF_COUNT_W, B.key(
            "nf_c%d_since" % c, "§g[?mod1440_nf_a%d|0] since [?mod1440_nf_was_date.GetDateStringNoHour]§!" % c), FONT_SMALL, "right", 20,
            tooltip=B.key("nf_since_tt", "The modifiers that are not what they were on [?mod1440_nf_was_date.GetDateStringNoHourLong], the first of this month (on the first day of a game: the day it started)."),
            fixed=True)
        triggers += (block("nf_c%d_count_visible" % c, "NOT = { %s }\n" % changed)
                     + block("nf_c%d_since_visible" % c, changed + "\n" + was + "\n"))
        inner += listing("nf_l%d" % c, "nf_l%d_grid" % c, 8, 44, NF_LIST_W, NF_LIST_ROWS * NF_ROW + 8, NF_ROW)
        inner += text("nf_c%d_none" % c, 20, 56, NF_LIST_W - 50, B.key("nf_none", "§gThe first comparison comes on the first of next month.§!"),
                      FONT_SMALL, height=44)
        triggers += block("nf_c%d_none_visible" % c, changed + "\nNOT = { %s }\n" % was)
        lists += block("nf_l%d_grid" % c, 'array = mod1440_nf_c%d_k\nentry_container = "mod1440_figures_row_%d"\n' % (c, c))
        cards += card("nf_col%d" % c, x, NF_COL_Y, NF_COL_W, NF_COL_H, title, inner)

        # A row of the list: the head of a group (kind 0), a modifier with the kind of its format (1 to 7), or in
        # the Changed view a modifier that changed (10 + kind). The label is a text key held in an array; the value
        # a copy of the modifier when the list was made; in the Changed view also the change and how it is written.
        arr = "mod1440_nf_c%d_" % c
        p = "nf_r%d_" % c
        head = "check_variable = { v = 0 }\n"
        line = "check_variable = { v > 0 }\ncheck_variable = { v < 10 }\n"
        moved = "check_variable = { v > 10 }\n"
        zero = "check_variable = { %sv^i = 0 }\n" % arr
        some = "NOT = { %s }\n" % zero.strip()
        entry = icon(p + "stripe", 0, 0, STRIPE % (NF_ROW_W, NF_ROW))
        entry += icon(p + "head", 0, 0, head_sprite(NF_ROW_W, NF_ROW))
        entry += text(p + "hname", 8, 4, 220, B.key(p + "hname", "§Y[?%st^i.GetTokenLocalizedKey]§!" % arr), FONT_SMALL, height=20)
        entry += text(p + "hcount", NF_ROW_W - 8 - 100, 4, 100, B.key(p + "hcount", "§g[?%sv^i|0] of [?%sn^i|0]§!" % (arr, arr)), FONT_SMALL, "right", 20)
        entry += text(p + "hchange", 232, 4, 56, B.key("nf_r_hchange", "§gchange§!"), FONT_SMALL, "right", 20)
        entry += text(p + "hnow", 294, 4, 56, B.key("nf_r_hnow", "§gnow§!"), FONT_SMALL, "right", 20)
        entry += text(p + "label", 8, 4, 250, B.key(p + "label", "[?%st^i.GetTokenLocalizedKey]" % arr), FONT_SMALL, height=20, fixed=True)
        entry += text(p + "dim", 8, 4, 250, B.key(p + "dim", "§g[?%st^i.GetTokenLocalizedKey]§!" % arr), FONT_SMALL, height=20, fixed=True)
        entry += text(p + "clabel", 8, 4, 220, B.key(p + "label", "[?%st^i.GetTokenLocalizedKey]" % arr), FONT_SMALL, height=20, fixed=True)
        row_triggers = block(p + "stripe_visible", "check_variable = { v > 0 }\ncheck_variable = { mod1440_odd^i = 1 }\n")
        for part in ("head", "hname"):
            row_triggers += block(p + part + "_visible", head)
        row_triggers += block(p + "hcount_visible", head + "NOT = { %s }\n" % changed)
        row_triggers += block(p + "hchange_visible", head + changed + "\n") + block(p + "hnow_visible", head + changed + "\n")
        row_triggers += block(p + "label_visible", line + some) + block(p + "dim_visible", line + zero) + block(p + "clabel_visible", moved)
        for k, fmt in enumerate(NF_FORMATS, start=1):
            entry += text(p + "v%d" % k, NF_ROW_W - 8 - 86, 2, 86, B.key(p + "v%d" % k, "[?%sv^i|%s]" % (arr, fmt)), FONT_LABEL, "right", 22)
            row_triggers += block(p + "v%d_visible" % k, "check_variable = { v = %d }\n" % k + some)
            entry += text(p + "n%d" % k, 292, 2, 58, B.key(p + "n%d" % k, "§g[?%sv^i|%s]§!" % (arr, NF_NOW[k - 1])), FONT_LABEL, "right", 22)
            row_triggers += block(p + "n%d_visible" % k, "check_variable = { v = %d }\n" % (10 + k))
        for k, fmt in enumerate(NF_CHANGES, start=1):
            entry += text(p + "d%d" % k, 218, 2, 70, B.key(p + "d%d" % k, "[?%sd^i|%s]" % (arr, fmt)), FONT_LABEL, "right", 22)
            row_triggers += block(p + "d%d_visible" % k, moved + "check_variable = { %sx^i = %d }\n" % (arr, k))
        rows += row("mod1440_figures_row_%d" % c, NF_ROW_W, NF_ROW, entry)
        triggers += row_triggers

        # The script that makes the list. Per group: count what applies and what changed, then a head (in the
        # Changed view only for a group with a change), then each modifier that applies, every one, or each that
        # changed since mod1440_h_record wrote mod1440_nf_was on the first of the month.
        def add(kind, token, value, total, how, change):
            return "".join("add_to_array = { %s%s = %s }\n" % (arr, part, v) for part, v in
                           (("k", kind), ("t", token), ("v", value), ("n", total), ("x", how), ("d", change)))
        fill += "".join("clear_array = %s%s\n" % (arr, part) for part in "ktvnxd") + setv("mod1440_nf_a%d" % c, 0)
        for g in names:
            title_g, column, entries = groups[g]
            fill += tmp("nf_g", 0) + tmp("nf_c", 0)
            for i, (label, value, fmt) in enumerate(entries):
                at = first[g] + i
                fill += tmp("nf_x", value) + iff("NOT = { check_variable = { nf_x = 0 } }", "add_to_temp_variable = { nf_g = 1 }\n")
                fill += iff("check_variable = { mod1440_nf_was^num > %d }" % at, tmp("nf_w", "mod1440_nf_was^%d" % at) + iff(
                    "NOT = { check_variable = { nf_x = nf_w } }", "add_to_temp_variable = { nf_c = 1 }\n"))
            fill += iff(changed, iff("check_variable = { nf_c > 0 }", add(0, nf_token("nf_grp_%s" % g, title_g), "nf_c", len(entries), 0, 0))
                        + "add_to_variable = { mod1440_nf_a%d = nf_c }\n" % c)
            fill += els(add(0, nf_token("nf_grp_%s" % g, title_g), "nf_g", len(entries), 0, 0) + "add_to_variable = { mod1440_nf_a%d = nf_g }\n" % c)
            for i, (label, value, fmt) in enumerate(entries):
                at = first[g] + i
                kind = NF_FORMATS.index(fmt) + 1
                token = label_token(g, i, label)
                fill += tmp("nf_x", value)
                fill += iff(changed, iff("check_variable = { mod1440_nf_was^num > %d }" % at, tmp("nf_w", "mod1440_nf_was^%d" % at) + iff(
                    "NOT = { check_variable = { nf_x = nf_w } }", tmp("nf_d", "nf_x") + "subtract_from_temp_variable = { nf_d = nf_w }\n"
                    + add(10 + kind, token, "nf_x", 0, NF_CHANGES.index(nf_change_format(value, fmt)) + 1, "nf_d"))))
                fill += iff("OR = { %s NOT = { check_variable = { nf_x = 0 } } }" % is_one("mod1440_nf_all"),
                            add(kind, token, "nf_x", 0, 0, 0), "else_if")
    return cards, rows, lists, triggers, fill


def national_figures():
    triggers, properties, effects = "", "", ""

    # ---- title strip: the title, the date of the last record, the three views of the modifiers, the close button
    body = title_strip("nf_head", NF_W)
    body += page_title("nf_title", 300, "National Figures")
    body += text("nf_last", 330, 18, 720, B.key(
        "nf_last", "§gWritten down on the first of each month, the last on [?mod1440_h_last.GetDateStringNoHourLong]§!"), FONT_SMALL, height=20,
        tooltip=B.key("nf_last_tt", "The figures of the tables are today's; their months, the changes and the graph come from what is written down."))
    body += text("nf_last_none", 330, 18, 720, B.key("nf_last_none", "§gWritten down on the first of each month§!"), FONT_SMALL, height=20)
    recorded = "check_variable = { mod1440_h_date^num > 0 }"
    triggers += block("nf_last_visible", recorded + "\n") + block("nf_last_none_visible", "NOT = { %s }\n" % recorded)
    body += text("nf_views", 1060, 18, 76, B.key("nf_views", "§gModifiers:§!"), FONT_SMALL, "right", 20, tooltip=B.key(
        "nf_views_tt", "The summed modifiers below: the sums over every law, spirit, advisor, technology and focus."))
    for k, (name, caption, tip) in enumerate(NF_VIEWS):
        x = 1146 + k * 144
        # the caption on the button and the chosen view on frame 2, as the range buttons and the Records filters
        # (D8 fix round 1: the button without buttonText under caption twins drew nothing and took no click)
        body += button("nf_view_%s" % name, x, 13, "GFX_sort_button_140x29", B.key("nf_view_%s" % name, caption),
                       tooltip=B.key("nf_view_%s_tt" % name, tip))
        effects += block("nf_view_%s_click" % name, setv("mod1440_nf_all", k) + "mod1440_nf_fill = yes\n")
        properties += block("nf_view_%s" % name, "frame = mod1440_nf_frame_%s\n" % name)
    body += close_button("nf_fold", NF_W - 66, 10, "shift+m", B.key("nf_fold_tt", PAGE_CLOSE_TT))
    # Escape on a twin off the screen (GUW-006): the free window takes it before Politics (X9)
    body += close_button("nf_fold_esc", -1000, -1000)
    effects += block("nf_fold_click", setv("mod1440_nf_shown", 0))
    effects += block("nf_fold_esc_click", setv("mod1440_nf_shown", 0))

    # ---- the tables, the graph of the chosen figure, the modifiers
    cards, sparks, lists, more, props, clicks = figure_tables()
    body += cards
    triggers += more
    properties += props
    effects += clicks
    inner, page, columns, graph_lists, more, props, clicks, place = figure_graph()
    triggers += more
    properties += props
    effects += clicks
    body += box("nf_graph", 14, NF_GRAPH_Y, NF_IN, NF_GRAPH_H, inner, CARD_BG)
    body += page
    cards, rows, list_lists, more, fill = modifier_lists()
    body += cards
    triggers += more

    gui = box("mod1440_figures", NF_X, NF_Y, NF_W, NF_H, body, PAGE_BG)
    gui += columns + sparks + rows
    # The button that opens it sits in the title strip of Politics. Between x 230 and 356 another mod has its own
    # button there (Better Mechanics: Production, "Economy Status"), and the game's own stands from 454 on: the
    # button takes the 92 px between them, with the short caption.
    handle = button("nf_toggle", 0, 0, "GFX_1440p_SG_button_92", B.key("nf_toggle", "Figures"), shortcut="shift+m",
                    tooltip=B.key("nf_toggle_tt", "National Figures: show the figures, their months and the summed modifiers of your country"))
    gui += box("mod1440_figures_handle", HANDLE_X, HANDLE_Y, HANDLE_W, HANDLE_H, handle)

    # A window of its own (D8): it shows over the vanilla Politics window too, and stays open when Politics closes;
    # the handle is docked to the tab and shows while the page is closed. mod1440_nf_shown (it was mod1440_nf_open):
    # a save of an earlier build reads 0, so a page saved open is closed. No dirty: the tables are live texts.
    script = scripted_gui("mod1440_figures", "mod1440_figures",
                          visible="check_variable = { mod1440_nf_shown = 1 }\n",
                          lists=graph_lists + lists + list_lists, effects=effects, triggers=triggers, properties=properties)
    opened = "mod1440_nf_fill = yes\nmod1440_h_draw = yes\n"
    # one free page at a time: opening this one closes Army Readiness
    script += "\n" + scripted_gui("mod1440_figures_handle", "mod1440_figures_handle", "politics_tab",
                                  visible="NOT = { %s }\n" % is_one("mod1440_nf_shown"),
                                  effects=block("nf_toggle_click", setv("mod1440_nf_shown", 1) + setv("mod1440_ar_open", 0) + opened))

    frames = "".join(setv("mod1440_nf_frame_%s" % name, 1) for name, caption, tip in NF_VIEWS) + "".join(
        iff("check_variable = { mod1440_nf_all = %d }" % k, setv("mod1440_nf_frame_%s" % name, 2), "if" if k == 0 else "else_if")
        for k, (name, caption, tip) in enumerate(NF_VIEWS))
    script_effects = (
        "# National Figures: the four lists of summed modifiers, for the country in scope: per group a head and each\n"
        "# modifier that is not 0, every one in the All view, or each that is not what it was on the first of the month\n"
        "# in the Changed view, with a copy of its value. Runs when the page opens, when the view changes and each day\n"
        "# while it is open.\n"
        + block("mod1440_nf_fill", "mod1440_rec_odd = yes\n" + fill + frames))
    # Each day while the page is open: the lists and the graph, so that a page left open in a saved game is right
    # again after a day at most.
    # D9: before that, every day, the casualty step (the total that never falls and the month so far) and the count of
    # the Equipment table, for the player only (the hook's limit) and without a loop (rule 5)
    daily = "mod1440_h_cas_step = yes\nmod1440_nf_equip = yes\n" + iff(is_one("mod1440_nf_shown"), "mod1440_nf_fill = yes\nmod1440_h_draw = yes\n")
    return gui, script, script_effects, daily, place


# --- D9 --- the casualties of every war
CAS_FIRST = "if = { limit = { NOT = { check_variable = { mod1440_h_cas_ver = 1 } } } mod1440_h_cas_fill = yes }\n"


def casualty_script():
    """The total of every war (series 31) and the dead of the month (series 32): the daily step on the game's
    casualties_k, which counts only the wars in progress and falls when a war ends, and the back-fill of a save of an
    earlier build from series 10, once (mod1440_h_cas_ver)."""
    fill = ("clear_array = mod1440_h_%d\nclear_array = mod1440_h_%d\n" % (H_CAS_SUM, H_CAS_MON) + tmp("h_cs", 0) + tmp("h_cp", 0)
            + block("for_each_loop", (
                "array = mod1440_h_10\nvalue = h_cv\nindex = h_ci\n"
                + iff("check_variable = { h_ci = 0 }", tmp("h_cs", "h_cv") + "add_to_array = { array = mod1440_h_%d value = -1 }\n" % H_CAS_MON)
                + els(tmp("h_cd", "h_cv") + "subtract_from_temp_variable = { h_cd = h_cp }\n" + iff("check_variable = { h_cd < 0 }", tmp("h_cd", 0))
                      + "add_to_temp_variable = { h_cs = h_cd }\nadd_to_array = { mod1440_h_%d = h_cd }\n" % H_CAS_MON)
                + "add_to_array = { mod1440_h_%d = h_cs }\n" % H_CAS_SUM + tmp("h_cp", "h_cv")))
            # what the game's number rose by since the last month written down belongs to this month
            + tmp("h_cd", "casualties_k") + "subtract_from_temp_variable = { h_cd = h_cp }\n" + iff("check_variable = { h_cd < 0 }", tmp("h_cd", 0))
            + setv("mod1440_h_cas_sum", "h_cs") + "add_to_variable = { mod1440_h_cas_sum = h_cd }\n" + setv("mod1440_h_cas_mon", "h_cd")
            + setv("mod1440_h_cas_last", "casualties_k") + setv("mod1440_h_cas_from", "global.date") + setv("mod1440_h_cas_ver", 1))
    step = (CAS_FIRST + tmp("h_ct", "casualties_k") + tmp("h_cd", "h_ct") + "subtract_from_temp_variable = { h_cd = mod1440_h_cas_last }\n"
            + iff("check_variable = { h_cd > 0 }", "add_to_variable = { mod1440_h_cas_sum = h_cd }\nadd_to_variable = { mod1440_h_cas_mon = h_cd }\n")
            + setv("mod1440_h_cas_last", "h_ct"))
    return ("# National Figures (D9): series 31 and 32 of a save without them, once, from series 10 (the game's casualties_k on\n"
            "# the first of each month): the total adds each rise of series 10 and nothing for a fall; the month is the rise\n"
            "# (-1 for the first month). Then the total, the month so far and the baseline from today's casualties_k.\n"
            + block("mod1440_h_cas_fill", fill)
            + "\n# National Figures (D9): each day for a player, and before each monthly record: a rise of the game's casualties_k\n"
            "# since the day before is added to the total (mod1440_h_cas_sum) and to the month so far (mod1440_h_cas_mon); a\n"
            "# fall (a war ended) only moves the baseline mod1440_h_cas_last. The total never falls.\n"
            + block("mod1440_h_cas_step", step))


def history_script(place):
    """The monthly record of the figures and of the modifiers for the Changed view, and the drawing of the tables'
    changes, the sparklines and the chosen figure. Returns the effects and the monthly hook."""
    pad = ""            # script: a figure of a newer build gets its padding for the months it was not written down
    for n in range(H_OLD, len(SERIES)):
        pad += (tmp("h_p", "mod1440_h_date^num") + "subtract_from_temp_variable = { h_p = mod1440_h_%d^num }\n" % n
                + iff("check_variable = { h_p > 0 }", block("for_loop_effect", (
                    "start = 0\nend = h_p\nvalue = h_q\nadd_to_array = { array = mod1440_h_%d value = %d index = 0 }\n"
                    % (n, H_RES_PAD if n in H_DEEP else -1)))))
    record = ""
    for n, (caption, value, factor, unit, decimals, rise) in enumerate(SERIES):
        if n == H_CAS_MON:
            # D9: the dead since the record before; the first record of a game has no month before it (-1, no column)
            record += (tmp("h_v", value) + iff("check_variable = { mod1440_h_date^num = 0 }", tmp("h_v", -1))
                       + "add_to_array = { mod1440_h_%d = h_v }\n" % n)
        elif factor == 1:
            record += "add_to_array = { mod1440_h_%d = %s }\n" % (n, value)
        else:
            record += "set_temp_variable = { h_v = %s }\nmultiply_temp_variable = { h_v = %d }\nadd_to_array = { mod1440_h_%d = h_v }\n" % (value, factor, n)
    record += setv("mod1440_h_cas_mon", 0)
    forget = "".join("remove_from_array = { array = mod1440_h_%d index = 0 }\n" % n for n in range(len(SERIES)))
    # the modifiers as they are on the first of the month, for the Changed view
    was = "clear_array = mod1440_nf_was\n" + "".join("add_to_array = { mod1440_nf_was = %s }\n" % value for value in NF_MODIFIERS)
    was += setv("mod1440_nf_was_date", "global.date")

    table = ""          # script: today's value of each figure, its change in a month and in a year, its sparkline
    copies = ""         # script: the chosen figure's months on the graph and how it is written
    for n, (caption, value, factor, unit, decimals, rise) in enumerate(SERIES):
        s = "mod1440_h_%d" % n
        table += (tmp("h_now", 0) + tmp("h_dm", 0) + tmp("h_hm", 0) + tmp("h_dy", 0) + tmp("h_hy", 0)
                  + iff("check_variable = { h_n > 0 }", tmp("h_now", "%s^h_i1" % s))
                  + iff("check_variable = { h_n > 1 }", iff("%s %s" % (h_known(n, "h_i1"), h_known(n, "h_i2")),
                        tmp("h_dm", "%s^h_i1" % s) + "subtract_from_temp_variable = { h_dm = %s^h_i2 }\n" % s + tmp("h_hm", 1)))
                  + iff("check_variable = { h_n > 12 }", iff("%s %s" % (h_known(n, "h_i1"), h_known(n, "h_i13")),
                        tmp("h_dy", "%s^h_i1" % s) + "subtract_from_temp_variable = { h_dy = %s^h_i13 }\n" % s + tmp("h_hy", 1)))
                  + "".join("add_to_array = { mod1440_h_tab_%s = h_%s }\n" % (part, part) for part in ("now", "dm", "hm", "dy", "hy")))
        if n in NF_SPARKS:
            # the last twelve months, the oldest first; a month before the record or not written down is the padding
            table += ("clear_array = mod1440_h_spin\n" + block("for_loop_effect", (
                "start = 0\nend = %d\nvalue = h_k\n" % NF_SPARK_N + tmp("h_j", "h_n")
                + "subtract_from_temp_variable = { h_j = %d }\nadd_to_temp_variable = { h_j = h_k }\n" % NF_SPARK_N + tmp("h_sv", H_RES_PAD)
                + iff("check_variable = { h_j > -1 }", iff(h_known(n, "h_j"), tmp("h_sv", "%s^h_j" % s)))
                + "add_to_array = { mod1440_h_spin = h_sv }\n"))
                + "mod1440_h_spark = yes\nclear_array = mod1440_h_sp_%d\n" % n
                + block("for_each_loop", "array = mod1440_h_spout\nvalue = h_sv\nadd_to_array = { mod1440_h_sp_%d = h_sv }\n" % n)
                # D9: the sign of each month and the zero level of this sparkline
                + "clear_array = mod1440_h_spn_%d\n" % n
                + block("for_each_loop", "array = mod1440_h_spsign\nvalue = h_sv\nadd_to_array = { mod1440_h_spn_%d = h_sv }\n" % n)
                + setv("mod1440_h_spz_%d" % n, "mod1440_h_spz"))
        low = h_floor(n)
        copies += iff("check_variable = { mod1440_h_series = %d }" % n, (
            block("for_loop_effect", "start = 0\nend = h_cnt\nvalue = h_k\n" + tmp("h_j", "h_k") + "add_to_temp_variable = { h_j = h_from }\n"
                  + tmp("h_v", "%s^h_j" % s) + "add_to_array = { mod1440_h_now = h_v }\n")
            + setv("mod1440_h_dec", decimals) + setv("mod1440_h_rise", 1 if rise == "+" else 0) + tmp("h_floor", H_RES_PAD - 1 if low is None else low)
            + block("for_each_loop", "array = %s\nvalue = h_v\n" % s + iff("check_variable = { h_v > h_floor }", "add_to_temp_variable = { h_total = 1 }\n"))
            + "".join(setv("mod1440_h_%s" % part, "mod1440_h_tab_%s^%d" % (part, n)) for part in ("dm", "dy"))
            + setv("mod1440_h_has_m", "mod1440_h_tab_hm^%d" % n) + setv("mod1440_h_has_y", "mod1440_h_tab_hy^%d" % n)
            # D9: the casualty series in the strength bar's colour, the deadliest month of the month's series in gold
            + setv("mod1440_h_loss", 1 if n in H_LOSS else 0) + setv("mod1440_h_gold", 1 if n == H_CAS_MON else 0)), "if" if n == 0 else "else_if")
    counts = "check_variable = { h_v > h_floor }"
    spans = "".join(iff("check_variable = { h_span = %d }" % span, tmp("h_step", step) + tmp("h_off", h_first_x(step))
                        + setv("mod1440_h_rf_%d" % span, 2), "if" if k == 0 else "else_if")
                    for k, (span, step, width, caption) in enumerate(H_RANGES))
    # the range: the player's, or the shortest that holds every month written down
    span = (tmp("h_span", "mod1440_h_range")
            + iff("check_variable = { h_span = 0 }", tmp("h_span", H_RANGES[0][0])
                  + "".join(iff("check_variable = { h_n > %d }" % H_RANGES[k - 1][0], tmp("h_span", H_RANGES[k][0])) for k in range(1, len(H_RANGES))))
            + setv("mod1440_h_span", "h_span") + setv("mod1440_h_yrs", "h_span") + "divide_variable = { mod1440_h_yrs = 12 }\n"
            + "".join(setv("mod1440_h_rf_%d" % r[0], 1) for r in H_RANGES) + spans
            + tmp("h_from", "h_n") + "subtract_from_temp_variable = { h_from = h_span }\n"
            + iff("check_variable = { h_from < 0 }", tmp("h_from", 0))
            + tmp("h_cnt", "h_n") + "subtract_from_temp_variable = { h_cnt = h_from }\n")
    # the months on the graph, their dates and years
    shown = ("".join("clear_array = mod1440_h_%s\n" % a for a in ("now", "sdate", "syear"))
             + block("for_loop_effect", "start = 0\nend = h_cnt\nvalue = h_k\n" + tmp("h_j", "h_k") + "add_to_temp_variable = { h_j = h_from }\n"
                     + tmp("h_v", "mod1440_h_date^h_j") + "add_to_array = { mod1440_h_sdate = h_v }\n"
                     + tmp("h_v", "mod1440_h_year^h_j") + "add_to_array = { mod1440_h_syear = h_v }\n"))
    # the foot of the columns: zero; the lowest month when zoomed in or when the figure goes below zero (a resource
    # balance); the top: the highest month, or zero for a figure below zero all along
    scale = (tmp("h_base", 0) + iff("OR = { %s check_variable = { h_min < 0 } }" % is_one("mod1440_h_zoom"), tmp("h_base", "h_min"))
             + tmp("h_top", "h_max") + iff("NOT = { %s } check_variable = { h_top < 0 }" % is_one("mod1440_h_zoom"), tmp("h_top", 0))
             + tmp("h_range", "h_top") + "subtract_from_temp_variable = { h_range = h_base }\n"
             + tmp("h_quarter", "h_range") + "divide_temp_variable = { h_quarter = 4 }\n"
             + setv("mod1440_h_s0", "h_base")
             + "".join(setv("mod1440_h_s%d" % k, "mod1440_h_s%d" % (k - 1)) + "add_to_variable = { mod1440_h_s%d = h_quarter }\n" % k for k in (1, 2, 3))
             + setv("mod1440_h_s4", "h_top")
             # a 2 px line at zero while the foot is below it
             + setv("mod1440_h_zero", 0) + setv("mod1440_h_zero_h", 0)
             + iff("check_variable = { h_base < 0 } check_variable = { h_top > -0.001 } check_variable = { h_range > 0 }", (
                 setv("mod1440_h_zero", 1) + tmp("h_z", 0) + "subtract_from_temp_variable = { h_z = h_base }\n"
                 "divide_temp_variable = { h_z = h_range }\nmultiply_temp_variable = { h_z = %d }\n" % H_CHART_H
                 + setv("mod1440_h_zero_y", H_CHART_TOP + H_CHART_H - 1) + "subtract_from_variable = { mod1440_h_zero_y = h_z }\n"
                 # D9: the zero level as a column height (the masks and the red columns), and the scale's own 0 beside it
                 + setv("mod1440_h_zero_h", "h_z") + setv("mod1440_h_zero_sy", "mod1440_h_zero_y") + "subtract_from_variable = { mod1440_h_zero_sy = 10 }\n"))
             # D9: zoomed in on a figure below zero all along, the zero level stands over the top: every month hangs
             + iff("check_variable = { h_top < 0 }", setv("mod1440_h_zero_h", H_CHART_H), "else_if"))
    bars = ("".join("clear_array = mod1440_h_bars_%d\nclear_array = mod1440_h_neg_%d\n" % (r[0], r[0]) for r in H_RANGES) + block("for_each_loop", (
        "array = mod1440_h_now\nvalue = h_v\n" + tmp("h_bar", -1) + tmp("h_ng", 0) + iff(counts, (
            tmp("h_bar", 0) + iff("check_variable = { h_v < 0 }", tmp("h_ng", 1))
            + iff("check_variable = { h_range > 0 }", tmp("h_bar", "h_v") + "subtract_from_temp_variable = { h_bar = h_base }\n"
                  "divide_temp_variable = { h_bar = h_range }\nmultiply_temp_variable = { h_bar = %d }\n" % H_STEPS)
            # every month the same: the columns stand at full height
            + iff("NOT = { check_variable = { h_v = 0 } }", tmp("h_bar", H_STEPS), "else_if")
            # from the lowest month, the lowest keeps a sliver: it was written down
            + iff("NOT = { check_variable = { h_base = 0 } }", iff("check_variable = { h_bar < 4 }", tmp("h_bar", 4)))
            + iff("check_variable = { h_bar < 0 }", tmp("h_bar", 0)) + iff("check_variable = { h_bar > %d }" % H_STEPS, tmp("h_bar", H_STEPS))))
        + "".join(iff("check_variable = { h_span = %d }" % r[0], "add_to_array = { mod1440_h_bars_%d = h_bar }\nadd_to_array = { mod1440_h_neg_%d = h_ng }\n"
                      % (r[0], r[0]), "if" if k == 0 else "else_if")
                  for k, r in enumerate(H_RANGES)))))
    spark = (
        "# National Figures: the sparkline of a row, from mod1440_h_spin (twelve months, the padding %d for a month not\n" % H_RES_PAD
        + "# written down) into mod1440_h_spout: heights 2 to %d between the lowest and the highest of the twelve, %d for\n" % (NF_SPARK_H, NF_SPARK_H)
        + "# twelve equal months that are not 0, -1 for no column. D9: the sign of each month into mod1440_h_spsign (1 below\n"
        + "# zero) and the zero level into mod1440_h_spz: the height of zero between the lowest and the highest, 0 when no\n"
        + "# month is below zero, %d when every month is.\n" % NF_SPARK_H
        + block("mod1440_h_spark", (
            tmp("h_shi", H_RES_PAD) + tmp("h_slo", -H_RES_PAD)
            + block("for_each_loop", "array = mod1440_h_spin\nvalue = h_sv\n" + iff("check_variable = { h_sv > %d }" % H_RES_LOW, (
                iff("check_variable = { h_sv > h_shi }", tmp("h_shi", "h_sv")) + iff("check_variable = { h_sv < h_slo }", tmp("h_slo", "h_sv")))))
            + tmp("h_sr", "h_shi") + "subtract_from_temp_variable = { h_sr = h_slo }\n" + "clear_array = mod1440_h_spout\n"
            + "clear_array = mod1440_h_spsign\n" + setv("mod1440_h_spz", 0)
            + iff("check_variable = { h_slo < 0 } check_variable = { h_sr > 0 }", (
                setv("mod1440_h_spz", 0) + "subtract_from_variable = { mod1440_h_spz = h_slo }\ndivide_variable = { mod1440_h_spz = h_sr }\n"
                "multiply_variable = { mod1440_h_spz = %d }\nadd_to_variable = { mod1440_h_spz = 2 }\n" % (NF_SPARK_H - 2)))
            + iff("check_variable = { h_slo < 0 }", setv("mod1440_h_spz", NF_SPARK_H), "else_if")
            + block("for_each_loop", "array = mod1440_h_spin\nvalue = h_sv\n" + tmp("h_sh", -1) + tmp("h_sn", 0) + iff("check_variable = { h_sv > %d }" % H_RES_LOW, (
                tmp("h_sh", 0) + iff("check_variable = { h_sv < 0 }", tmp("h_sn", 1))
                + iff("check_variable = { h_sr > 0 }", tmp("h_sh", "h_sv") + "subtract_from_temp_variable = { h_sh = h_slo }\n"
                      "divide_temp_variable = { h_sh = h_sr }\nmultiply_temp_variable = { h_sh = %d }\nadd_to_temp_variable = { h_sh = 2 }\n" % (NF_SPARK_H - 2))
                # twelve equal months: full above zero; below zero they hang from the top (the zero level) to the foot
                + iff("check_variable = { h_sv > 0 }", tmp("h_sh", NF_SPARK_H), "else_if")))
                + "add_to_array = { mod1440_h_spout = h_sh }\nadd_to_array = { mod1440_h_spsign = h_sn }\n"))))
    effects = (
        casualty_script() + "\n" + equipment_count() + "\n"
        + "# History: writes today's figures of the country in scope down, and forgets the oldest month past ten years;\n"
        "# then the summed modifiers as they are today, for the Changed view of National Figures. Runs at the start of a\n"
        "# game for every country and on the first of each month for a player. D9: first the casualty step and the\n"
        "# Equipment table's count, so that series 31 to 38 have today's values.\n"
        + block("mod1440_h_record", (
            "mod1440_h_cas_step = yes\nmod1440_nf_equip = yes\n"
            + record + "add_to_array = { mod1440_h_date = global.date }\nadd_to_array = { mod1440_h_year = global.year }\n" + pad
            + iff("check_variable = { mod1440_h_date^num > %d }" % H_KEEP, forget
                  + "remove_from_array = { array = mod1440_h_date index = 0 }\nremove_from_array = { array = mod1440_h_year index = 0 }\n")
            + was
            + iff(is_one("mod1440_nf_shown"), "mod1440_nf_fill = yes\nmod1440_h_draw = yes\n")))
        + "\n" + spark
        + "\n# History: today's value, the changes and the sparkline of each figure for the tables, then the chosen figure's\n"
        + "# months in the range as column heights, 0 to %d, between the foot of the graph (zero, or the lowest month) and\n" % H_STEPS
        + "# its top. A month of a newer figure that was not written down (its padding) is drawn as no column and counts for nothing.\n"
        + block("mod1440_h_draw", (
            CAS_FIRST + pad + tmp("h_n", "mod1440_h_date^num")
            + "".join(tmp("h_i%d" % k, "h_n") + "subtract_from_temp_variable = { h_i%d = %d }\n" % (k, k) for k in (1, 2, 13))
            + "".join("clear_array = mod1440_h_tab_%s\n" % part for part in ("now", "dm", "hm", "dy", "hy"))
            + table
            # an older save has months without a year: they get 0 in front, which draws no mark
            + block("for_loop_effect", "start = 0\nend = %d\nvalue = h_pad\n" % H_KEEP + iff(
                "check_variable = { mod1440_h_year^num < mod1440_h_date^num }", "add_to_array = { array = mod1440_h_year value = 0 index = 0 }\n"))
            + span + shown + tmp("h_total", 0) + copies
            + tmp("h_max", 0)
            + block("find_highest_in_array", "array = mod1440_h_now\nvalue = h_max\nindex = h_at\n")
            # the lowest month, the first month and how many count, with a loop of the page's own: no script of the
            # game uses find_lowest_in_array
            + tmp("h_min", "h_max") + tmp("h_min_at", 0) + tmp("h_valid", 0) + tmp("h_first", 0) + tmp("h_sum", 0)
            + block("for_each_loop", "array = mod1440_h_now\nvalue = h_v\nindex = h_vi\n" + iff(counts, (
                iff("check_variable = { h_valid = 0 }", tmp("h_first", "h_v")) + "add_to_temp_variable = { h_sum = h_v }\n"
                + "add_to_temp_variable = { h_valid = 1 }\n" + iff("check_variable = { h_v < h_min }", tmp("h_min", "h_v") + tmp("h_min_at", "h_vi")))))
            + iff("check_variable = { h_valid = 0 }", tmp("h_max", 0) + tmp("h_min", 0) + tmp("h_at", 0))
            + setv("mod1440_h_max", "h_max") + setv("mod1440_h_min", "h_min") + setv("mod1440_h_valid", "h_valid") + setv("mod1440_h_total", "h_total")
            # D9: the month of the highest column (gold for the month's casualties), the sum of the months on the graph
            # (In the range), and the deadliest month written down of series 32 (the row's grey extra)
            + setv("mod1440_h_max_i", "h_at") + setv("mod1440_h_sum", "h_sum")
            + tmp("h_w", 0) + block("find_highest_in_array", "array = mod1440_h_%d\nvalue = h_w\n" % H_CAS_MON)
            + iff("check_variable = { h_w < 0 }", tmp("h_w", 0)) + setv("mod1440_h_cas_worst", "h_w")
            + iff("check_variable = { h_cnt > 0 }", setv("mod1440_h_max_date", "mod1440_h_sdate^h_at") + setv("mod1440_h_min_date", "mod1440_h_sdate^h_min_at"))
            + scale + bars
            + place
            + setv("mod1440_h_latest", 0) + setv("mod1440_h_change", 0)
            + iff("check_variable = { h_cnt > 0 }", (
                tmp("h_last", "h_cnt") + "subtract_from_temp_variable = { h_last = 1 }\n"
                + setv("mod1440_h_latest", "mod1440_h_now^h_last")
                + setv("mod1440_h_change", "mod1440_h_latest") + "subtract_from_variable = { mod1440_h_change = h_first }\n"
                + setv("mod1440_h_first", "mod1440_h_sdate^0") + setv("mod1440_h_last", "mod1440_h_date^h_i1")))
            + setv("mod1440_h_zoom_frame", 1) + iff(is_one("mod1440_h_zoom"), setv("mod1440_h_zoom_frame", 2)))))
    monthly = "mod1440_h_record = yes\n"
    return effects, monthly


# --- D9 --- The scenes draw the page as Germany might stand on 15 March 1942 after 75 months, with the made-up figures
# of the design's mock-ups (scratch/phases/D9/work/data.py): a war from September 1939 to June 1941, a second from
# December 1941, infantry equipment short since the second began. Casualties in the month chosen, 5 years, What
# applies; the capture "changed" draws the Changed view, the captures "total" and "infantry" of the history scene
# draw Casualties, all wars and the infantry equipment balance.
NF_SCENE_CHOSEN = H_CAS_MON
NF_SCENE_SPAN = 60
NF_SAMPLE_N = 75                # months written down: index j is the first of the month January 1936 + j
NF_MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
                  "November", "December"]


def nf_sample_series():
    """The made-up months of series 31, 32 and 33 (None: not written down) and the dead of each calendar month."""
    loss = [0.0] * NF_SAMPLE_N
    for k, v in enumerate([42.5, 18.0, 6.2, 4.1, 3.0, 2.2, 3.5, 9.4, 96.8, 182.4, 12.3, 8.8, 7.5, 9.2, 6.1, 5.4, 4.8, 31.6,
                           88.2, 120.5, 40.3, 15.7]):
        loss[44 + k] = v                # September 1939 to June 1941
    for m, v in ((71, 30.0), (72, 60.0), (73, 70.0)):
        loss[m] = v                     # December 1941 to February 1942
    total = [round(sum(loss[:j]), 1) for j in range(NF_SAMPLE_N)]
    month = [None] + [loss[j - 1] for j in range(1, NF_SAMPLE_N)]
    infantry = []
    for j in range(NF_SAMPLE_N):
        v = (2.0 + j * 0.25 if j < 30 else 9.5 - (j - 30) * 0.2 if j < 44 else 6.7 - (j - 44) * 0.9 if j < 56
             else -4.1 + (j - 56) * 1.0 if j < 68 else 7.9 + (j - 68) * 0.6 if j < 71 else 9.1 - (j - 70) * 5.4)
        infantry.append(round(v, 1))
    return {H_CAS_SUM: total, H_CAS_MON: month, H_EQ[0]: infantry}, loss


NF_SAMPLE_SERIES, NF_SAMPLE_LOSS = nf_sample_series()
_T, _M = NF_SAMPLE_SERIES[H_CAS_SUM], NF_SAMPLE_SERIES[H_CAS_MON]
NF_SAMPLE = {   # series: (now, extra, change in a month, in a year, the twelve months of the sparkline)
    11: ("86", "+1.85 a day", -42, 60, [120, 60, 10, -45, -80, -50, 0, 30, 55, 70, 128, 86]),
    14: ("64.2", "+0.92 a day", 8.0, -12.0, [76, 70, 58, 50, 44, 40, 46, 52, 60, 66, 56, 64]),
    6: ("62.0%", "-0.05% a week", -1.0, -9.0, [71, 70, 70, 69, 68, 67, 66, 66, 65, 64, 63, 62]),
    7: ("71.5%", "+0.10% a week", 2.5, -4.5, [76, 75, 74, 72, 70, 68, 66, 65, 66, 67, 69, 71.5]),
    30: ("81.0%", None, 0.0, 3.0, [78, 78, 79, 79, 79, 80, 80, 80, 81, 81, 81, 81]),
    15: ("44", "31 cores", 2, 6, [38, 38, 38, 39, 40, 41, 41, 42, 42, 42, 42, 44]),
    3: ("£civ_factory 61", "8 free", 1, 6, [55, 55, 56, 56, 57, 58, 58, 59, 59, 60, 60, 61]),
    4: ("£mil_factory 88", "0 idle", 2, 19, [69, 71, 72, 74, 76, 78, 80, 82, 84, 85, 86, 88]),
    5: ("£nav_dockyard_texticon 16", "1 idle", 0, 1, [15, 15, 15, 15, 15, 16, 16, 16, 16, 16, 16, 16]),
    8: ("212.4K", "of 610.0K", -38.2, -120.5, [332, 350, 371, 390, 402, 360, 330, 300, 280, 262, 250, 212]),
    12: ("6", None, 0, 1, [5, 5, 5, 5, 5, 6, 6, 6, 6, 6, 6, 6]),
    13: ("164", None, 3, 27, [137, 140, 142, 145, 147, 150, 152, 155, 157, 159, 161, 164]),
    0: ("412.8K", "64.2K training", -88.4, -620.3, [1033, 1010, 980, 960, 940, 900, 880, 820, 760, 640, 501, 412]),
    1: ("3124.6K", None, 92.0, 880.1, [2244, 2300, 2380, 2450, 2520, 2600, 2680, 2760, 2840, 2950, 3032, 3124]),
    2: ("188", None, 4, 42, [146, 150, 154, 158, 162, 166, 170, 174, 178, 181, 184, 188]),
    H_CAS_SUM: ("909.9K", "191.4K in wars", round(_T[74] - _T[73], 1), round(_T[74] - _T[62], 1), _T[63:75]),
    H_CAS_MON: ("31.4K", "worst 182.4K", round(_M[74] - _M[73], 1), round(_M[74] - _M[62], 1), _M[63:75]),
    H_SURRENDER: ("4.0%", None, 1.5, 4.0, [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2.5, 4.0]),
    16: ("96", None, -18, -110, [206, 200, 190, 182, 170, 160, 150, 140, 130, 120, 114, 96]),
    17: ("520", None, 4, 48, [472, 476, 480, 484, 488, 492, 496, 500, 504, 508, 516, 520]),
    18: ("88", None, -2, 9, [79, 80, 81, 82, 83, 84, 85, 86, 87, 89, 90, 88]),
    19: ("3210", None, -140, 860, [2350, 2420, 2500, 2600, 2700, 2800, 2900, 3000, 3100, 3200, 3350, 3210]),
    27: ("74.0", None, 12.0, 30.0, [44, 50, 56, 30, 36, 42, 48, 54, 60, 66, 62, 74]),
    28: ("18.4", None, 2.0, 6.1, [12, 13, 13, 14, 14, 15, 15, 16, 16, 17, 16, 18]),
    29: ("52.0", None, -6.0, 22.0, [30, 32, 34, 36, 38, 40, 44, 48, 52, 56, 58, 52]),
}
# the resources: balance, made, used, import, export, balance a month before
NF_SAMPLE_RES = [(-24, 18, 42, 0, 0, -18), (-8, 36, 44, 0, 0, -6), (-26, 0, 26, 0, 0, -21), (-11, 3, 14, 0, 0, -9),
                 (44, 196, 152, 0, 0, 58), (-14, 4, 18, 0, 0, -11), (160, 270, 70, 0, 40, 172)]
# the Equipment table: stock, short, balance, change of the balance in a month, in thousands
NF_SAMPLE_EQ = [(0.0, 12.4, -12.4, -5.1), (1.2, 0.0, 1.2, 0.3), (3.4, 0.6, 2.8, -0.4), (0.8, 0.0, 0.8, 0.1),
                (0.0, 1.1, -1.1, -0.2), (4.6, 2.2, 2.4, -1.0)]
# the lists of What applies: (group, applies, of, [(label, value, colour)]); colour + green, - red, 0 white
NF_SAMPLE_LISTS = [
    [("Politics", 12, [("Political power per day", "+2.15", "+"), ("Political Power Gain", "+15.0%", "+"),
                       ("Weekly Stability", "+0.10%", "+"), ("Stability from modifiers", "+10.0%", "+"),
                       ("War support from modifiers", "+15.0%", "+"), ("Ideology drift defense", "+20.0%", "+"),
                       ("Command power per day", "+0.92", "+")]),
     ("Occupation and Diplomacy", 8, [("Compliance Growth Speed", "-2.0%", "-"), ("Resistance Target", "+5.0%", "-"),
                                      ("Surrender Limit", "-9.0%", "-")])],
    [("Industry", 19, [("Factory Output", "+15.0%", "+"), ("Dockyard Output", "+10.0%", "+"),
                       ("£prod_eff_cap  Production Efficiency Cap", "+10.0%", "+"), ("£prod_eff Production Efficiency growth", "+10.0%", "+"),
                       ("Construction Speed", "+20.0%", "+"), ("Share of factories on consumer goods", "20.0%", "0"),
                       ("Consumer Goods Factories factor", "-5.0%", "+"), ("Resources to Market", "25.0%", "0")])],
    [("Manpower", 8, [("Recruitable Population", "5.00%", "0"), ("Recruitable Population Factor", "+5.0%", "+"),
                      ("Division training time", "-10.0%", "+")]),
     ("Army", 19, [("Division Organization", "+5.0%", "+"), ("Max planning", "+10.0%", "+"), ("Reinforce Rate", "+5.0%", "+"),
                   ("Supply Consumption", "-5.0%", "+"), ("Army experience gain", "+10.0%", "+")])],
    [("Research and Intelligence", 6, [("Research Speed", "+5.0%", "+"), ("Encryption", "+10.0%", "+")]),
     ("Navy", 15, [("Naval Speed", "+5.0%", "+")]),
     ("Air Force", 16, [("Air Mission Efficiency", "+5.0%", "+"), ("Air Accidents Chance", "-10.0%", "+")])],
]
# the Changed view, what is not as it was on 1 June 1938: (group, [(label, change, now, colour of the change)])
NF_SAMPLE_CHANGED = [
    [("Politics", [("Political power per day", "+0.25", "+2.15", "+"), ("War support from modifiers", "+5.0%", "+15.0%", "+"),
                   ("Stability from modifiers", "-5.0%", "+10.0%", "-")]),
     ("Occupation and Diplomacy", [("Surrender Limit", "-4.0%", "-9.0%", "-")])],
    [("Industry", [("Factory Output", "+5.0%", "+15.0%", "+"), ("Consumer Goods Factories factor", "-5.0%", "-5.0%", "+"),
                   ("Share of factories on consumer goods", "-5.0%", "20.0%", "+")])],
    [("Manpower", [("Division training time", "-10.0%", "-10.0%", "+")]), ("Army", [("Max planning", "+10.0%", "+10.0%", "+")])],
    [("Research and Intelligence", [("Research Speed", "+5.0%", "+5.0%", "+")])],
]
NF_SAMPLE_COLOUR = {"+": "§G%s§!", "-": "§R%s§!", "0": "%s"}


def nf_sample_change(name, value, decimals, rise, suffix, hide, samples):
    """The sample of a change in a table: which of its three texts shows, with what."""
    shown = "same" if value == 0 else ("up" if value > 0 else "down")
    for part in ("up", "down", "same"):
        if part != shown:
            hide.append("%s_%s" % (name, part))
    if value:
        good = (value > 0) == (rise == "+")
        samples["%s_%s" % (name, shown)] = ("§G%s§!" if good else "§R%s§!") % (("%+." + str(decimals) + "f") % value + suffix)


def nf_sample_lists(view):
    """The rows, which widgets show in which row ("only") and the samples of the four lists of a view."""
    windows = []
    rows = {}
    for c, groups in enumerate(NF_SAMPLE_LISTS if view == "applies" else NF_SAMPLE_CHANGED):
        p = "nf_r%d_" % c
        heads, lines, odd = [], [], []
        samples = {p + part: [] for part in ("hname", "hcount", "label", "v1", "clabel", "d1", "n1")}
        i = 0
        for group in groups:
            heads.append(i)
            samples[p + "hname"].append("§Y%s§!" % group[0])
            entries = group[2] if view == "applies" else group[1]
            if view == "applies":
                samples[p + "hcount"].append("§g%d of %d§!" % (len(entries), group[1]))
            i += 1
            for entry in entries:
                lines.append(i)
                if i % 2:
                    odd.append(i)
                if view == "applies":
                    label, value, colour = entry
                    samples[p + "label"].append(label)
                    samples[p + "v1"].append(NF_SAMPLE_COLOUR[colour] % value)
                else:
                    label, change, now, colour = entry
                    samples[p + "clabel"].append(label)
                    samples[p + "d1"].append(NF_SAMPLE_COLOUR[colour] % change)
                    samples[p + "n1"].append("§g%s§!" % now)
                i += 1
        rows["nf_l%d_grid" % c] = i
        if view == "applies":
            only = {p + "head": heads, p + "hname": heads, p + "hcount": heads, p + "stripe": odd, p + "label": lines, p + "v1": lines}
            hide = [p + part for part in ("dim", "clabel", "hchange", "hnow")] + ["%sv%d" % (p, k) for k in range(2, len(NF_FORMATS) + 1)]
            hide += ["%sn%d" % (p, k) for k in range(1, len(NF_FORMATS) + 1)] + ["%sd%d" % (p, k) for k in range(1, len(NF_CHANGES) + 1)]
        else:
            only = {p + "head": heads, p + "hname": heads, p + "hchange": heads, p + "hnow": heads, p + "stripe": odd,
                    p + "clabel": lines, p + "d1": lines, p + "n1": lines}
            hide = [p + part for part in ("dim", "label", "hcount")] + ["%sv%d" % (p, k) for k in range(1, len(NF_FORMATS) + 1)]
            hide += ["%sn%d" % (p, k) for k in range(2, len(NF_FORMATS) + 1)] + ["%sd%d" % (p, k) for k in range(2, len(NF_CHANGES) + 1)]
        windows.append(("mod1440_figures_row_%d" % c, hide, only, {k: v for k, v in samples.items() if v}))
    return windows, rows


def nf_date(j, short=False):
    """The date of the record j of the made-up months (the first of the month January 1936 + j)."""
    year, month = 1936 + j // 12, j % 12
    return "%d.%d.1" % (year, month + 1) if short else "1 %s, %d" % (NF_MONTH_NAMES[month], year)


def nf_spark_sample(values):
    """The sparkline of twelve made-up months as mod1440_h_spark draws it: per widget the rows it shows in ("only")
    and its fills. A month below zero hangs red from the zero level."""
    valid = [v for v in values if v is not None]
    hi, lo = max(valid), min(valid)
    sr = hi - lo
    zero = 0.0
    if lo < 0:
        zero = (2 + (NF_SPARK_H - 2) * (0 - lo) / float(sr)) if sr > 0 else float(NF_SPARK_H)
    only = {"sp": [], "spr": [], "spm": [], "spn": []}
    fills = {"sp": [], "spr": [], "spm": [], "spn": []}
    for i, v in enumerate(values):
        if v is None:
            continue
        h = (2 + (NF_SPARK_H - 2) * (v - lo) / float(sr)) if sr > 0 else (float(NF_SPARK_H) if v > 0 else 0.0)
        parts = (("spr", zero), ("spn", h)) if v < 0 else (("sp", h),) + ((("spm", zero),) if zero > 0 else ())
        for part, height in parts:
            only[part].append(i)
            fills[part].append(round(height / NF_SPARK_H, 3))
    return only, fills


def nf_graph_sample(n, span):
    """The graph of series n over the last span months of the made-up months, as mod1440_h_draw draws it (no zoom):
    the page's widgets the script hides, the samples, the places of the year marks and the zero line, the column
    window's "only" and fills, and the rows of the three grids."""
    caption, variable, factor, unit, dec, rise = SERIES[n]
    months = NF_SAMPLE_SERIES[n]
    first = max(0, len(months) - span)
    shown = months[first:]
    valid = [v for v in shown if v is not None]
    hi, lo = max(valid), min(valid)
    base = lo if lo < 0 else 0.0
    top = hi if hi >= 0 else 0.0
    rng = top - base
    zero_on = base < 0 and top > -0.001 and rng > 0
    zero = -base / rng * H_CHART_H if zero_on else 0.0
    at_max = shown.index(hi)
    at_min = shown.index(lo)
    month = n == H_CAS_MON
    hide = ["h_name_%d" % k for k in range(len(SERIES)) if k != n] + ["h_unit_%d" % k for k in range(len(SERIES)) if k != n]
    hide += ["h_note_%d" % k for k in H_NOTES if k != n] + ["h_none"]
    if not zero_on:
        hide += ["h_zero", "h_scale_zero"]
    # mod1440_h_total counts the months written down: the first record of series 32 (-1, no month before it) is not one
    total = len([v for v in months if v is not None])
    samples = {"h_unit_%d" % n: "§gThe last %d years of %d months%s§!" % (span // 12, total, ", " + unit if unit else ""),
               "h_from": nf_date(first), "h_to": nf_date(len(months) - 1), "h_months": "%d of %d" % (len(valid), total)}
    if month:
        samples["h_note_%d" % n] = "§YDeadliest: the month to %s§!" % nf_date(first + at_max)

    def number(v):
        return ("%." + str(dec) + "f") % v

    def change(name, value):
        """A signed number of the plates: the variant the trigger shows, the others hidden."""
        variants = ["h_%s_%d%s" % (name, d, r) for d in (0, 1) for r in ("", "r")] + ["h_%s_same" % name]
        shown_one = "h_%s_same" % name if value == 0 else "h_%s_%d%s" % (name, dec, "" if rise == "+" else "r")
        hide.extend(w for w in variants if w != shown_one)
        if value:
            good = (value > 0) == (rise == "+")
            samples[shown_one] = ("§G%s§!" if good else "§R%s§!") % (("%+." + str(dec) + "f") % value)

    for name, value in (("latest", shown[-1]), ("max", hi), ("min", lo)):
        hide.append("h_%s_%d" % (name, 1 - dec))
        samples["h_%s_%d" % (name, dec)] = number(value)
    change("dm", round(months[-1] - months[-2], 3))
    change("dy", round(months[-1] - months[-13], 3))
    if month:
        hide += ["h_change_%d%s" % (d, r) for d in (0, 1) for r in ("", "r")] + ["h_change_same", "h_sum_%d" % (1 - dec)]
        hide += ["h_max_l", "h_change_l", "h_max_d", "h_min_d"]
        samples["h_sum_%d" % dec] = number(sum(valid))
        samples["h_max_d32"] = "§gto %s§!" % nf_date(first + at_max, True)
        samples["h_min_d32"] = "§gto %s§!" % nf_date(first + at_min, True)
    else:
        change("change", round(valid[-1] - valid[0], 3))
        hide += ["h_sum_0", "h_sum_1", "h_max32_l", "h_sum_l", "h_max_d32", "h_min_d32"]
        samples["h_max_d"] = "§g%s§!" % nf_date(first + at_max, True)
        samples["h_min_d"] = "§g%s§!" % nf_date(first + at_min, True)
    for k in range(5):
        hide.append("h_scale_%d_%d" % (k, 1 - dec))
        samples["h_scale_%d_%d" % (k, dec)] = number(top if k == 4 else base + k * rng / 4.0)
    # the year marks under the first month of each year after the first month on the graph
    step = [r[1] for r in H_RANGES if r[0] == span][0]
    place = {}
    marks = [i for i in range(1, len(shown)) if (first + i) % 12 == 0]
    for k, i in enumerate(marks):
        place["h_year_%d" % k] = [h_first_x(step) + i * step, H_CHART_TOP + H_CHART_H + 1]
        samples["h_year_%d" % k] = str(1936 + (first + i) // 12)
    hide += ["h_year_%d" % k for k in range(len(marks), H_YEARS)]
    if zero_on:
        y = int(round(H_CHART_TOP + H_CHART_H - 1 - zero))
        place["h_zero"] = [14 + H_CHART_X + H_INSET, y]
        place["h_scale_zero"] = [28, y - 10]
    # the columns: one row per month on the graph
    widgets = ["h_bar", "h_loss", "h_gold", "h_red", "h_mask", "h_maskn"]
    only = {w: [] for w in widgets}
    fills = {w: [] for w in widgets}
    for i, v in enumerate(shown):
        if v is None:
            continue
        h = (v - base) / rng * H_CHART_H if rng > 0 else (H_CHART_H if v else 0)
        if base != 0 and h < 4:
            h = 4
        h = max(0, min(H_CHART_H, h))
        if n in H_LOSS:
            parts = [("h_gold", h)] if (month and i == at_max) else [("h_loss", h)]
        elif v < 0:
            parts = [("h_red", zero), ("h_maskn", h)]
        else:
            parts = [("h_bar", h)] + ([("h_mask", zero)] if zero > 0 else [])
        for w, height in parts:
            only[w].append(i)
            fills[w].append(round(height / float(H_CHART_H), 3))
    col = "mod1440_figures_col_%d" % span
    column = {"only": {col: {"%s%d" % (w, span): only[w] for w in widgets}},
              "fills": {col: {"%s%d" % (w, span): fills[w] for w in widgets if fills[w]}}}
    rows = {"h_grid_%d" % r[0]: (len(shown) if r[0] == span else 0) for r in H_RANGES}
    return hide, samples, place, column, rows


def nf_page_hide(n):
    """What script hides in the tables while series n is chosen: the pick bands and yellow names of the other rows,
    the white name of the chosen one."""
    figures = [k for k in range(len(SERIES)) if k in NF_SPARKS or k in H_DEEP]
    return (["nf_t%d_pick" % k for k in figures if k != n] + ["nf_t%d_ly" % k for k in figures if k != n] + ["nf_t%d_l" % n]
            + ["nf_last_none"] + ["nf_c%d_since" % c for c in range(len(NF_COLUMNS))] + ["nf_c%d_none" % c for c in range(len(NF_COLUMNS))])


def nf_scene():
    """The windows of the National Figures page for its two scenes, their samples, the bars' fills, the state of the
    Changed view and the states of the graph of two other figures (captures of the history scene)."""
    n = NF_SCENE_CHOSEN
    span = NF_SCENE_SPAN
    graph_hide, graph_samples, place, column, rows = nf_graph_sample(n, span)
    hide = []           # the tables' widgets script hides, whichever figure is chosen
    samples = dict(graph_samples)
    for k, (now, extra, dm, dy, spark) in NF_SAMPLE.items():
        decimals, rise = SERIES[k][4], SERIES[k][5]
        samples["nf_t%d_v" % k] = now
        if extra:
            samples["nf_t%d_x" % k] = "§g%s§!" % extra
        nf_sample_change("nf_t%d_m" % k, dm, decimals, rise, h_suffix(k), hide, samples)
        nf_sample_change("nf_t%d_y" % k, dy, decimals, rise, h_suffix(k), hide, samples)
    hide += ["nf_t%d_vn" % k for k in NF_NOW_NEG]      # political power is above zero in the sample
    for r, (balance, made, used, bought, sold, before) in enumerate(NF_SAMPLE_RES):
        samples["nf_res_balance_%d" % r] = ("§G%+d§!" if balance >= 0 else "§R%+d§!") % balance
        for cname, value in (("made", made), ("used", used), ("in", bought), ("out", sold)):
            if value:
                samples["nf_res_%s_%d" % (cname, r)] = "%d" % value
            else:
                hide.append("nf_res_%s_%d" % (cname, r))
        nf_sample_change("nf_t%d_m" % H_RES[r], balance - before, 0, "+", "", hide, samples)
    for k, (stock, short, balance, dm) in enumerate(NF_SAMPLE_EQ):
        if stock > 0:
            samples["nf_eq_s_%d" % k] = "%.1fK" % stock
            hide.append("nf_eq_s0_%d" % k)
        else:
            hide.append("nf_eq_s_%d" % k)
        if short > 0:
            samples["nf_eq_d_%d" % k] = "§R%.1fK§!" % short
            hide.append("nf_eq_d0_%d" % k)
        else:
            hide.append("nf_eq_d_%d" % k)
        shown_b = "nf_eq_b_%d" % k if balance > 0 else "nf_eq_bn_%d" % k if balance < 0 else "nf_eq_b0_%d" % k
        hide += [w for w in ("nf_eq_b_%d" % k, "nf_eq_bn_%d" % k, "nf_eq_b0_%d" % k) if w != shown_b]
        if balance:
            samples[shown_b] = ("§G%+.1fK§!" if balance > 0 else "§R%+.1fK§!") % balance
        nf_sample_change("nf_t%d_m" % H_EQ[k], dm, 1, "+", "K", hide, samples)
    table_hide = hide
    hide = nf_page_hide(n) + graph_hide + table_hide
    samples["nf_last"] = "§gWritten down on the first of each month, the last on 1 March, 1942§!"
    list_rows = {"h_grid_%d" % s: "mod1440_figures_col_%d" % s for s, step_, width, caption in H_RANGES}
    spark_windows = {}
    for k in NF_SPARKS:
        rows["nf_sp%d_grid" % k] = NF_SPARK_N
        list_rows["nf_sp%d_grid" % k] = "mod1440_figures_spark_%d" % k
        only, fills = nf_spark_sample(NF_SAMPLE[k][4])
        spark_windows["mod1440_figures_spark_%d" % k] = {
            "only": {"nf_%s%d" % (part, k): rows_ for part, rows_ in only.items()},
            "fills": {"nf_%s%d" % (part, k): f for part, f in fills.items() if f}}
    lists, list_counts = nf_sample_lists("applies")
    rows.update(list_counts)
    for c in range(len(NF_COLUMNS)):
        list_rows["nf_l%d_grid" % c] = "mod1440_figures_row_%d" % c
        samples["nf_c%d_count" % c] = "§g%d of %d apply§!" % (sum(len(g[2]) for g in NF_SAMPLE_LISTS[c]), sum(g[1] for g in NF_SAMPLE_LISTS[c]))
    applies_hide = list(hide)
    frames = {"nf_view_applies": 2, "h_range_%d" % span: 2}
    windows = [{"name": "mod1440_figures", "at": [NF_X, NF_Y], "freeWindow": True, "rows": rows, "listRows": list_rows,
                "hide": applies_hide, "place": place, "frames": frames,
                "drawIn": ["", "all", "changed", "ten_years", "oil", "total", "infantry"],
                "_note": "A window of its own at its screen position (D8, X7). Germany on 15 March 1942 after 75 months, made-up figures as the D9 design's mock-ups: Casualties in the month chosen, 5 years, What applies. Script hides the pick bands and names of the other figures, the changes of the sign a row does not have, the ways of writing a number it does not use, the twins of a value by its sign; the two range grids not in use are empty."}]
    col = "mod1440_figures_col_%d" % span
    for s, step_, width, caption in H_RANGES:
        name = "mod1440_figures_col_%d" % s
        w = {"name": name, "skip": True}
        if name == col:
            w["only"] = column["only"][col]
            w["fills"] = column["fills"][col]
        windows.append(w)
    for k in NF_SPARKS:
        name = "mod1440_figures_spark_%d" % k
        windows.append({"name": name, "skip": True, "only": spark_windows[name]["only"], "fills": spark_windows[name]["fills"]})
    for name, row_hide, only, row_samples in lists:
        windows.append({"name": name, "skip": True, "hide": row_hide, "only": only})
    windows.append({"name": "mod1440_figures_handle", "at": [HANDLE_X - 6, HANDLE_Y + 78], "drawIn": ["closed"],
                    "_note": "Docked to Politics (the tab's corner at -6,78), shown only while the page is closed: the state closed."})
    scene_samples = {"mod1440_figures": samples}
    scene_samples.update({name: row_samples for name, row_hide, only, row_samples in lists})
    # the Changed view: the capture after a click on Changed, as the renderer draws it (render_gui.py --state changed)
    changed_lists, changed_counts = nf_sample_lists("changed")
    changed_rows = dict(rows)
    changed_rows.update(changed_counts)
    changed_hide = {"mod1440_figures": [h for h in hide if not h.startswith("nf_c") or "_none" in h]
                    + ["nf_c%d_count" % c for c in range(len(NF_COLUMNS))]}
    changed_samples = {"mod1440_figures": {"nf_c%d_since" % c: "§g%d since 1942.3.1§!" % sum(len(g[1]) for g in NF_SAMPLE_CHANGED[c])
                                           for c in range(len(NF_COLUMNS))}}
    changed_only = {}
    for name, row_hide, only, row_samples in changed_lists:
        changed_hide[name] = row_hide
        changed_only[name] = only
        changed_samples[name] = row_samples
    changed = {"name": "changed", "steps": [{"clickWidget": "mod1440_figures/nf_view_changed", "wait": 1.0}],
               "hide": changed_hide, "only": changed_only, "rows": changed_rows, "samples": changed_samples,
               "frames": {"mod1440_figures": {"nf_view_changed": 2, "h_range_%d" % span: 2}},
               "_note": "The Changed view as the renderer draws it with the design's made-up month; in a check of 1 January 1936 the lists say that the first comparison comes on the first of next month (or, after effect mod1440_chk_changed, list the made-up changes)."}
    # D9: two more figures on the graph, for the history scene: the total of every war, and the infantry equipment balance
    # with its months below zero hanging red (the renderer draws them with --state total and --state infantry)
    graphs = []
    for name, k, note in (("total", H_CAS_SUM, "Casualties, all wars on the graph over the same made-up months: the total never falls when the first war ends (June 1941)."),
                          ("infantry", H_EQ[0], "The infantry equipment balance over the made-up months: green above the zero line, red hanging below it, the scale's own 0.")):
        g_hide, g_samples, g_place, g_column, g_rows = nf_graph_sample(k, span)
        state_hide = nf_page_hide(k) + g_hide + table_hide
        state_rows = dict(rows)
        state_rows.update(g_rows)
        graphs.append({"name": name, "steps": [{"clickWidget": "mod1440_figures/nf_t%d" % k, "scene": "national_figures", "wait": 1.0}],
                       "hide": {"mod1440_figures": state_hide}, "samples": {"mod1440_figures": g_samples},
                       "place": {"mod1440_figures": g_place}, "rows": state_rows,
                       "only": g_column["only"], "fills": g_column["fills"],
                       "frames": {"mod1440_figures": frames}, "_note": note})
    return windows, scene_samples, changed, graphs


# --- D8 --- the free page (scratch/phases/D8/design.json, openInGame)
NF_CHECKLIST_D8 = [
    "D8, run 1 over the VANILLA Politics window (a scratch copy of the mod without interface/zz_1440p_politics.gui's clipping = no line, or without the override): Politics opens with no page and the Figures handle at screen 353,90; the handle (or Shift+M) opens the page at 550,78, 1680x1210, drawn whole and not cut off at the panel's 550 px; the tables, the graph and the four lists filled; every part takes clicks (a table row, the range buttons, the view buttons, a list's scrollbar)",
    "D8: the Figures handle is hidden while the page is open; the close button at 1614,10 (its tooltip names Shift+M and Escape), Shift+M and Escape each close the page and bring the handle back; the first Escape closes the page only, the second closes Politics",
    "D8: close Politics while the page is open: the page stays over the map; Shift+M and Escape still close it; open it again, close Politics, open Recruit & Deploy and its Readiness handle: National Figures closes and only Army Readiness is open",
    "D8: a save of the build before D8 with National Figures open (mod1440_nf_open 1) loads with the page closed; the handle opens it filled",
]
# --- end D8 ---

NF_CHECKLIST = NF_CHECKLIST_D8 + [
    "The page stands beside the politics panel (1680x1210 from screen 550,78) and takes clicks; the Figures button and Shift+M open it, the close button, Shift+M and Escape close it (the first Escape the page, the second Politics)",
    "The title strip: 'Written down on the first of each month, the last on 1 January, 1936'; 'Modifiers:' and three buttons What applies, All modifiers, Changed, the chosen one with the second frame and a yellow caption",
    "Two tables of figures: Government and Industry and research; Manpower and war and Stock and experience (D9); each head bar in yellow, the first with the column heads Now, Month, Year, 12 months; every second row on a darker band",
    "Compare each Now with the game: political power and command power and their daily gain with the top bar's tooltips; stability and war support and their weekly change with the top bar; ruling party popularity with the politics panel's party ring (Germany 1936: 40.0%); states and cores with the state list; factories and free/idle with the top bar's tooltips (35 civilian, 28 military, 10 dockyards); fuel with the top bar; free manpower with the top bar, training with Army Readiness; divisions, equipment, convoys, trains, ships, planes as before; army, navy and air experience with the top bar's experience tooltips",
    "On 1 January 1936 (one month) the Month and Year columns are empty and every sparkline has one column at full height on the right",
    "A click on a row of either table and of the resource table draws its figure: the row on the lighter band with its name yellow, the graph's name and its line 'The last 2 years of 1 months'",
    "The resource card: the seven rows with the game's icons, Balance, Made, Used, Import, Export against the logistics tab (Germany 1936: balances 3, 104, -5, 3, 177, 1, 195); no legend under them (D9: its words are in the column heads' tooltips), the Equipment table in its place",
    "The graph: the seven numbers in one row under a head bar; the buttons 2 years (chosen), 5 years, 10 years and Zoom in; 24 column slots of 57 px across 1560 px; one column on 1 January 1936; the tooltip of a column, of Highest and of Lowest give the month",
    "The 5 years and 10 years buttons: the columns become 22 and 11 px wide on 26 and 13 px steps, and the other two grids draw nothing (no column and no tooltip of another range)",
    "After `effect mod1440_chk_months` (tools/check_effects.py): 120 months, the fit range 10 years; every table row has its Month, Year and twelve sparkline columns; a click on a resource row draws a balance that goes below zero from its lowest month, with the zero line across the graph (an orange 2 px line) at the scale's 0",
    "What applies: only the modifiers that are not 0 (Germany 1936: 11, 8, 10 and 7 rows with the heads); All modifiers: every one, those that are 0 in grey; each list scrolls; 12 rows show (D9, was 14), the cards 374 high from page y 822",
    "Changed on 1 January 1936: each card reads '0 since 1936.1.1' with an empty list (the startup record is the comparison of day 1; the line 'The first comparison comes on the first of next month.' shows only for a save without that record); after `effect mod1440_chk_changed`: the changed modifiers with the change (green or red in the modifier's own sense) and the value now in grey, the heads 'change' and 'now', the cards '<n> since 1936.1.1' at the right of the title strip, clear of the title on all four cards (Politics and Diplomacy, Navy, Air and Research)",
    "Every figure row's tooltip, a sparkline's tooltip and the column heads' tooltips",
] + [
    # --- D9 --- (scratch/phases/D9/design.json; the check effects of tools/check_effects.py)
    "D9 band 1: three cards 418 high at page y 56 (600, 600, 440 wide); Manpower and war lists Free manpower, Manpower in the field, Divisions, Casualties, all wars (grey extra '0.0K in wars'), Casualties in the month (grey 'worst 0.0K'), Surrender progress; Stock and experience has no Infantry equipment row (7 rows); card 1 keeps 26 px free at its foot; nothing overlaps or is cut",
    "D9, against the game on 1 January 1936: Casualties, all wars 0.0K and its grey 'in wars' 0.0K (the war screen has no war); Surrender progress 0.0% (war screen); Casualties in the month 0.0K",
    "D9 Equipment table under the resources: head bar 'Equipment' with Stock, Short, Balance, Month; six rows with the game's names (Infantry Equipment, Support Equipment, Towed Artillery, Towed Anti-Tank, Towed Anti-Aircraft, Truck) in 136 px boxes; compare each Stock with the production tab's stockpile of that kind (in thousands), each Short with Army Readiness's shortfall of the kind (a grey dash when the field lacks nothing), and Balance = Stock less Short, green with '+' above zero",
    "D9: `effect mod1440_chk_equip_short` (made-up values until the next day's count): Infantry Equipment reads Stock 0, Short 12.4K in red, Balance -12.4K in red with its minus sign; Towed Anti-Aircraft Short 1.1K, Balance -1.1K red",
    "D9: `effect mod1440_chk_pp_negative` (political power -200): the Political power row's Now reads -200 (or the game's number) in red with its sign",
    "D9: a click on an Equipment row chooses it (lighter band, yellow name) and draws its balance: name '<kind> balance', the line 'In stock less what the field is short of' under the unit line",
    "D9: the column heads' tooltips carry the legend's words (Now: red below zero; Month and Year: green a gain, red a loss, the other way round for casualties, surrender and costs; 12 months: red months below zero); the Equipment heads' tooltips (Stock, Short as Army Readiness counts it, Balance, Month)",
    "D9 graph card: 336 high at page y 480; the frame of the columns at page y 564 (12 px lower than before); the year marks, From and To dates follow; the range buttons and Zoom in at page y 490",
]
NF_HISTORY_CHECKLIST_D9 = [
    "D9: after `effect mod1440_chk_months` (130 made-up months): choose Casualties in the month: columns in the strength bar's brown, the deadliest month's column gold, under the name the yellow line 'Deadliest: the month to <date>' naming the gold column's date; the plates read Deadliest (not Highest) and In the range (the sum of the months on the graph, not Over the range), with 'to <yyyy.m.d>' under Deadliest and Lowest; the column of the first record (-1) is missing",
    "D9: after `effect mod1440_chk_months`: Casualties, all wars rises during the made-up war and stays level after it (never falls), in brown, with the line 'The dead of every war, ended or not'; game.log has 'MOD1440 check: casualties' with series 10 back to 0 while 31 keeps its last value",
    "D9: after `effect mod1440_chk_months`, the Infantry Equipment row: months above zero green from the zero line up, months below zero red hanging from the zero line down, the orange zero line and the scale's own '0' at its left on the same height; the dates under Highest and Lowest (yyyy.m.d) match the highest and lowest columns' tooltips. If the red columns stand from the foot instead, or green columns show their lower part dark-masked wrongly, the mask layer failed (fallback in build.json)",
    "D9: after `effect mod1440_chk_months`, the Political power row's sparkline: months below zero hang red from a zero level, months above stand on it; a sparkline of a figure never below zero is drawn as before",
    "D9: a column's tooltip on a red (negative) column gives its date and value; hovering the masked lower part of a green column still shows a tooltip",
    "D9 back-fill: `effect mod1440_chk_months_d4` (a save of the build before D9: 31 series, a war in series 10 that rises and ends, no series 31 to 39, no mod1440_h_cas_ver), then close and open the page: Casualties, all wars and Casualties in the month have months back to the first, the total never falls when series 10 does; game.log 'MOD1440 check: backfill' shows cas_ver 1 and the counts of 31 and 32 equal to the months; the equipment balances and surrender progress say 'Nothing is written down for this figure yet' until a record",
    "D9 daily step: `effect mod1440_chk_cas_rise` adds 12.0K to Casualties, all wars and to Casualties in the month; `effect mod1440_chk_cas_fall` (the game's value 50K lower than the day before, a war ended) changes neither; game.log 'MOD1440 check: cas' lines give the sums",
    "D9: 2, 5 and 10 years with a casualty series and with the infantry balance: the brown, gold, red and mask columns follow the range (57, 22, 11 px); the other grids draw nothing",
]
NF_SCENE = nf_scene()
# --- end D4 round 2 ---


# ---------------------------------------------------------------- Top bar strip (D7), on the top bar of every screen

# Values the vanilla top bar keeps in its tooltips, in the empty middle of the bar (x 1042 to 2152, the band's
# flat interior y 3 to 31; scratch/phases/D7/design.json, round 2). The user chose on 2026-10-17 that the values
# are chosen in the game: an edit button opens a panel of eighteen, each with its width and a switch; the chips
# stand in the order of the catalogue and close up from the left. A chip is the game's value box at its own width,
# the game's icon and the value in the top bar's font; its label is in the tooltip.
#
# A chip is three widgets side by side in the strip's container (a nested container follows no x and no _visible,
# Engine Facts X15). Each has an x from a country variable and shows while its switch is on (X4). The effect
# mod1440_tb_place sets those variables on a click only, never on a tick (rule 5); the texts read game values
# directly and follow them without a dirty variable (X2). A save of an earlier build has none of the variables:
# the fixed twin, the eight defaults at fixed places, shows until the first click on the edit button or the next
# day sets them (on_startup does not run when a save is loaded).
TB_X, TB_Y = 1042, 3            # the strip's container, 912x28: y 3 to 31 is the band's flat interior
TB_ROOM = 912                   # px for chips, 1042 to 1954: 16 before the edit button
TB_BOX_Y, TB_H = 1, 26          # a chip's box: 26 high at screen y 4 (the vanilla boxes: 26 at y 5)
TB_TEXT_Y = TB_BOX_Y + 4        # the value at box y + 4, as on the vanilla bar (box y 5, text y 8)
TB_PAD_L, TB_ICON_GAP = 3, 4    # the icon 3 px into the box, the value 4 px after it
TB_GAP, TB_GROUP_GAP = 4, 16    # between chips of a group, and where the group changes
TB_EDIT = (1970, 4, 28, 26)     # the edit button, 4 px left of the Records handle (2002)
TB_VER = 1                      # mod1440_tb_ver: the strip of this build is set up for the country
TB_PANEL_X, TB_PANEL_Y, TB_PANEL_W = 2152 - 842, 40, 842    # under the band, its right edge on the handle's
TB_GROUPS = ["Gains", "Factories", "Fuel", "Manpower", "Resources"]
TB_COLUMNS = [["Gains", "Factories", "Fuel"], ["Manpower", "Resources"]]
TB_RES_NAMES = ["Oil", "Aluminium", "Rubber", "Tungsten", "Steel", "Chromium", "Coal"]
TB_RES_TIP = "%s balance: produced and bought, less what your lines use and what you sell. Red, with the game's crossed icon, below 0."


def tb_chip(name, group, label, width, sprite, frame, scale, icon_w, icon_h, text_x, value, tip, default, twin=None, below=None, widest=None):
    """One value of the catalogue. Sizes measured by the design (scratch/phases/D7/custom-layout.json), widened by
    TB_TEXT_MARGIN in fix round 1 of D2 (2026-10-17): 3 px,
    the icon, 4 px, the value at its widest, 5 px. twin: the value in another colour, shown while `below`
    (a trigger) holds; for a resource also the game's crossed icon. widest: the widest plausible value as it
    reads, without its colour codes, which the text box must hold with TB_TEXT_MARGIN to spare (tb_widths())."""
    return {"name": name, "group": group, "label": label, "width": width, "sprite": sprite, "frame": frame, "scale": scale,
            "icon": (icon_w, icon_h), "text_x": text_x, "text_w": width - text_x - 5, "value": value, "tip": tip,
            "default": default, "twin": twin, "below": below, "widest": widest}


def tb_idle(variable):
    return "check_variable = { %s > 0 }" % variable


# The catalogue, in the order the chips stand. Every value is in the game's documentation folder: the dynamic
# variables political_power_daily, command_power_daily, num_of_*_factories, num_of_available_*_factories,
# num_of_civilian_factories_available_for_projects, fuel_k, max_fuel_k, deployed_total_manpower_k,
# amount_manpower_in_deployment_queue, resource@<r> and modifier@<m>; stability_weekly, war_support_weekly and
# consumer_goods_factor are modifiers.
TB_CHIPS = [
    tb_chip("pp", "Gains", "Political power per day", 93, "GFX_pol_power_icon", 1, 1.0, 27, 27, 34,
            "[?political_power_daily|+=1]§g/d§!", "Political power you gain each day. The top bar shows the stock.", True, widest="+99.9/d"),
    tb_chip("cp", "Gains", "Command power per day", 90, "GFX_command_power", 1, 1.0, 24, 22, 31,
            "[?command_power_daily|+=2]§g/d§!", "Command power you gain each day, up to the most you can hold.", True, widest="+9.99/d"),
    tb_chip("stab", "Gains", "Stability per week", 109, "GFX_stability_icon", 1, 1.0, 27, 24, 34,
            "[?modifier@stability_weekly|+=%1]§g/wk§!",
            "Stability changes by this much each week (the weekly modifiers). The top bar shows where it stands.", True, widest="+9.9%/wk"),
    tb_chip("ws", "Gains", "War support per week", 108, "GFX_war_support_icon", 1, 1.0, 26, 24, 33,
            "[?modifier@war_support_weekly|+=%1]§g/wk§!",
            "War support changes by this much each week (the weekly modifiers). The top bar shows where it stands.", True, widest="+9.9%/wk"),
    tb_chip("civ", "Factories", "Civilian factories, free", 114, "GFX_civ_factory", 1, 1.2, 22, 22, 29,
            "[?num_of_civilian_factories|0]  §g[?num_of_civilian_factories_available_for_projects|0] free§!",
            "Civilian factories, and how many are free for construction once consumer goods and trade have taken theirs.", True,
            widest="999  99 free"),
    tb_chip("mil", "Factories", "Military factories, idle", 110, "GFX_mil_factory", 1, 1.2, 22, 22, 29,
            "[?num_of_military_factories|0]  §g[?num_of_available_military_factories|0] idle§!",
            "Military factories, and how many have no production line. Yellow while any stands idle.", True,
            twin="[?num_of_military_factories|0]  §Y[?num_of_available_military_factories|0] idle§!",
            below=tb_idle("num_of_available_military_factories"), widest="999  99 idle"),
    tb_chip("dock", "Factories", "Dockyards, idle", 102, "GFX_nav_dockyard_texticon", 1, 1.1, 22, 22, 29,
            "[?num_of_naval_factories|0]  §g[?num_of_available_naval_factories|0] idle§!",
            "Dockyards, and how many have no production line. Yellow while any stands idle.", True,
            twin="[?num_of_naval_factories|0]  §Y[?num_of_available_naval_factories|0] idle§!",
            below=tb_idle("num_of_available_naval_factories"), widest="99  99 idle"),
    tb_chip("cg", "Factories", "Consumer goods", 77, "GFX_consumer_goods_texticon", 1, 1.0, 20, 20, 27,
            "[?modifier@consumer_goods_factor|%1]", "Consumer goods: the share of your civilian factories that the people's needs take.", False,
            widest="99.9%"),
    tb_chip("fuel", "Fuel", "Fuel in store", 131, "GFX_fuel_state", 1, 1.0, 26, 24, 33,
            "[?fuel_k|0]K§g/[?max_fuel_k|0]K§!",
            "Fuel in store, of what your silos and refineries can hold. The top bar shows how long it lasts.", True, widest="9999K/9999K"),
    tb_chip("mp_field", "Manpower", "Manpower in the field", 122, "GFX_manpower_icon", 1, 0.9, 24, 24, 31,
            "[?deployed_total_manpower_k|0]K§g field§!", "Men in your divisions, ships and air wings.", False, widest="99999K field"),
    tb_chip("mp_train", "Manpower", "Manpower in training", 142, "GFX_manpower_icon", 1, 0.9, 24, 24, 31,
            "[?amount_manpower_in_deployment_queue|*1]§g training§!", "Men of the divisions in training.", False, widest="999.9K training"),
] + [tb_chip("res_" + res, "Resources", TB_RES_NAMES[r], 64, "GFX_resources_strip", r + 1, 0.7, 19, 19, 26,
             "[?resource@%s|0]" % res, TB_RES_TIP % TB_RES_NAMES[r], False,
             twin="§R[?resource@%s|0]§!" % res, below="check_variable = { resource@%s < 0 }" % res, widest="-999")
     for r, res in enumerate(RESOURCES)]
TB_DEFAULT = [c["name"] for c in TB_CHIPS if c["default"]]


def tb_place(on):
    """What mod1440_tb_place does, for the .gui positions and the scenes: in catalogue order each chip that is on
    stands at the cursor, which then moves by the chip's width and 4, or 16 where the group changes. Returns the
    right end (px used) and the x of each chip in the strip's container."""
    x, last, out = 0, None, {}
    for c in TB_CHIPS:
        if c["name"] not in on:
            continue
        if last is not None:
            x += TB_GAP if c["group"] == last else TB_GROUP_GAP
        out[c["name"]] = x
        x += c["width"]
        last = c["group"]
    return x, out


def tb_icon(name, x, y, sprite, frame=None, scale=None, tooltip=None, transparent=False):
    extra = (" frame = %d" % frame if frame else "") + (" scale = %s" % scale if scale and scale != 1.0 else "")
    extra += ' pdx_tooltip = "%s"' % tooltip if tooltip else ""
    extra += " alwaystransparent = yes" if transparent else ""
    return 'iconType = { name = "%s" position = { x = %d y = %d } spriteType = "%s"%s }\n' % (name, x, y, sprite, extra)


def tb_icon_dy(c):
    """The icon in the middle of the box's height, never above the band's interior (screen y 3)."""
    return max((TB_H - c["icon"][1]) // 2, -1)


def tb_parts(c, x):
    """Where each widget of a chip stands with its box at x: {widget suffix: (x, y)}."""
    n = c["name"]
    icon = (x + TB_PAD_L, TB_BOX_Y + tb_icon_dy(c))
    value = (x + c["text_x"], TB_TEXT_Y)
    parts = {n + "_bg": (x, TB_BOX_Y), n + "_icon": icon, n: value}
    if c["twin"]:
        parts[n + ("_neg" if n.startswith("res_") else "_idle")] = value
    if n.startswith("res_"):
        parts[n + "_miss"] = icon
    return parts


def tb_widgets(prefix, c, x):
    """The widgets of one chip, named <prefix>_<chip>..., with the box at x."""
    n = c["name"]
    tip = B.key("tb_%s_tt" % n, c["tip"])
    pos = tb_parts(c, x)
    out = tb_icon("%s_%s_bg" % (prefix, n), pos[n + "_bg"][0], pos[n + "_bg"][1], "GFX_1440p_SG_topbox_%dx%d" % (c["width"], TB_H), tooltip=tip)
    out += tb_icon("%s_%s_icon" % (prefix, n), pos[n + "_icon"][0], pos[n + "_icon"][1], c["sprite"], c["frame"], c["scale"], tooltip=tip)
    if n.startswith("res_"):
        out += tb_icon("%s_%s_miss" % (prefix, n), pos[n + "_miss"][0], pos[n + "_miss"][1], "GFX_missing_resources_strip", c["frame"], c["scale"], tooltip=tip)
    out += text("%s_%s" % (prefix, n), pos[n][0], pos[n][1], c["text_w"], B.key("tb_%s" % n, c["value"]), FONT_LABEL, height=22, tooltip=tip, fixed=True)
    if c["twin"]:
        twin = n + ("_neg" if n.startswith("res_") else "_idle")
        out += text("%s_%s" % (prefix, twin), pos[twin][0], pos[twin][1], c["text_w"], B.key("tb_%s" % twin, c["twin"]), FONT_LABEL, height=22, tooltip=tip, fixed=True)
    return out


def tb_triggers(prefix, c, on):
    """What shows of a chip: everything while its switch is on (on: a trigger, or "" for the fixed twin); a value
    with a twin shows the one its trigger asks for."""
    n = c["name"]
    shown = on + "\n" if on else ""
    out = block("%s_%s_bg_visible" % (prefix, n), shown) if on else ""
    if c["twin"]:
        twin = n + ("_neg" if n.startswith("res_") else "_idle")
        out += block("%s_%s_visible" % (prefix, n), shown + "NOT = { %s }\n" % c["below"])
        out += block("%s_%s_visible" % (prefix, twin), shown + c["below"] + "\n")
    elif on:
        out += block("%s_%s_visible" % (prefix, n), shown)
    if n.startswith("res_"):
        out += block("%s_%s_icon_visible" % (prefix, n), shown + "NOT = { %s }\n" % c["below"])
        out += block("%s_%s_miss_visible" % (prefix, n), shown + c["below"] + "\n")
    elif on:
        out += block("%s_%s_icon_visible" % (prefix, n), shown)
    return out


def tb_switch(n):
    return "check_variable = { mod1440_tb_on_%s = 1 }" % n


def tb_refused(c):
    """Off, and less room left than the chip and a group gap need: the most a chip can add to the strip."""
    return "NOT = { %s } check_variable = { mod1440_tb_room < %d }" % (tb_switch(c["name"]), c["width"] + TB_GROUP_GAP)


def tb_strip():
    """The moving strip, its fixed twin and the edit button: three scripted GUIs on the top bar."""
    _right, at = tb_place(TB_DEFAULT)
    body, triggers, properties = "", "", ""
    fixed, fixed_triggers = "", ""
    for c in TB_CHIPS:
        n = c["name"]
        # the .gui places a chip where the defaults put it; script moves it (a chip that is off stands at 0, hidden)
        body += tb_widgets("tb", c, at.get(n, 0))
        triggers += tb_triggers("tb", c, tb_switch(n))
        for suffix, variable in ((("_bg", "x"), ("_icon", "xi"), ("_miss", "xi"), ("", "xt"), ("_idle", "xt"), ("_neg", "xt"))):
            if n + suffix in tb_parts(c, 0):
                properties += block("tb_%s%s" % (n, suffix), "x = mod1440_tb_%s_%s\n" % (variable, n))
        if c["default"]:
            fixed += tb_widgets("tbf", c, at[n])
            fixed_triggers += tb_triggers("tbf", c, "")
    gui = box("mod1440_top_bar_strip", TB_X, TB_Y, TB_ROOM, 28, body)
    gui += box("mod1440_top_bar_fixed", TB_X, TB_Y, TB_ROOM, 28, fixed)
    current = "check_variable = { mod1440_tb_ver = %d }\n" % TB_VER
    script = scripted_gui("mod1440_top_bar_strip", "mod1440_top_bar_strip", "top_bar", visible=current,
                          triggers=triggers, properties=properties)
    script += scripted_gui("mod1440_top_bar_fixed", "mod1440_top_bar_fixed", "top_bar", visible="NOT = { %s }\n" % current.strip(),
                           triggers=fixed_triggers)
    # the edit button: the chip's box as a button with the game's edit-list picture, in a container of its own so
    # that it stays when every chip is off
    ex, ey, ew, eh = TB_EDIT
    edit = button("tb_edit", 0, 0, "GFX_1440p_SG_topbtn_%dx%d" % (ew, eh),
                  tooltip=B.key("tb_edit_tt", "Choose the values of this strip."))
    edit += tb_icon("tb_edit_icon", (ew - 22) // 2, (eh - 22) // 2, "GFX_edit_list_icon", transparent=True)
    gui += box("mod1440_top_bar_edit", ex, ey, ew, eh, edit)
    script += scripted_gui("mod1440_top_bar_edit", "mod1440_top_bar_edit", "top_bar", effects=block(
        "tb_edit_click", iff("NOT = { %s }" % current.strip(), "mod1440_tb_default = yes\n") + flip("mod1440_tb_setup")))
    return gui, script


TB_CARD_Y, TB_CARD_W, TB_CARD_GAP, TB_MARGIN = 84, 400, 14, 14
TB_HEAD_H, TB_ROW = 30, 32


def tb_rows():
    """Each value's row in the panel: (chip, card x, row y), relative to the panel; and the cards' height."""
    rows, heights = [], []
    for col, groups in enumerate(TB_COLUMNS):
        cx = TB_MARGIN + col * (TB_CARD_W + TB_CARD_GAP)
        y = TB_CARD_Y + 8
        for group in groups:
            rows.append((None, cx, y, group))
            y += TB_HEAD_H + 2
            for c in TB_CHIPS:
                if c["group"] == group:
                    rows.append((c, cx, y, group))
                    y += TB_ROW
        heights.append(y - TB_CARD_Y)
    return rows, max(heights) + 8


def tb_panel():
    """The panel of the edit button: the width used, the eighteen values in five groups with their width and a
    switch, Default and close."""
    rows, card_h = tb_rows()
    foot_y = TB_CARD_Y + card_h + 12
    height = foot_y + 34 + 14
    body = title_strip("tb_head", TB_PANEL_W, 44)
    body += text("tb_title", 16, 11, 500, B.key("tb_title", "Top bar values"), FONT_CARD, height=30)
    body += close_button("tb_close", TB_PANEL_W - 50, 8, tooltip=B.key("tb_close_tt", "Close"))
    body += icon("tb_used_bar", 16, 60, bar_sprite(300))
    body += text("tb_used", 330, 56, TB_PANEL_W - 330 - 16, B.key(
        "tb_used", "[?mod1440_tb_used|0] of %d px used, [?mod1440_tb_room|0] left. A value that needs more stays off." % TB_ROOM), FONT_SMALL, height=20)
    properties = block("tb_used_bar", "frame = mod1440_tb_used_pct\n")
    triggers, effects = "", ""
    for col in range(len(TB_COLUMNS)):
        body += box("tb_card_%d" % col, TB_MARGIN + col * (TB_CARD_W + TB_CARD_GAP), TB_CARD_Y, TB_CARD_W, card_h, "", CARD_BG)
    n_in_group = 0
    for c, cx, y, group in rows:
        if c is None:
            body += heads("tb_head_%d" % TB_GROUPS.index(group), cx + 8, y, TB_CARD_W - 16, [
                (8, 200, group, "left", None), (242, 60, "Width", "left", None), (322, 60, "Shown", "left", None)])
            n_in_group = 0
            continue
        n = c["name"]
        if n_in_group % 2:
            body += icon("tb_s_%s_stripe" % n, cx + 8, y, STRIPE % (TB_CARD_W - 16, TB_ROW))
        n_in_group += 1
        tip = B.key("tb_%s_tt" % n, c["tip"])
        # the chip's icon at most 24 px high, in the middle of a 26 px column
        k = min(1.0, 24.0 / c["icon"][1])
        w, h = int(round(c["icon"][0] * k)), int(round(c["icon"][1] * k))
        body += tb_icon("tb_s_%s_icon" % n, cx + 16 + (26 - w) // 2, y + (TB_ROW - h) // 2, c["sprite"], c["frame"], round(c["scale"] * k, 3), tooltip=tip)
        label = B.key("tb_s_%s" % n, c["label"])
        body += text("tb_s_%s_name" % n, cx + 50, y + 5, 220, label, FONT_LABEL, height=22, tooltip=tip, fixed=True)
        body += text("tb_s_%s_name_off" % n, cx + 50, y + 5, 220, B.key("tb_s_%s_grey" % n, "§g%s§!" % c["label"]), FONT_LABEL, height=22, tooltip=tip, fixed=True)
        need = c["width"] + TB_GROUP_GAP
        need_tip = B.key("tb_s_%s_need_tt" % n, "Needs %d px of the strip: %d for the value and up to %d between groups. "
                         "[?mod1440_tb_room|0] px are left; turn another value off first." % (need, c["width"], TB_GROUP_GAP))
        body += text("tb_s_%s_w" % n, cx + 230, y + 7, 70, B.key("tb_s_w_%d" % c["width"], "§g%d px§!" % c["width"]), FONT_SMALL, "right", 20)
        body += text("tb_s_%s_w_off" % n, cx + 230, y + 7, 70, B.key("tb_s_w_%d_off" % c["width"], "§R%d px§!" % c["width"]), FONT_SMALL, "right", 20, tooltip=need_tip)
        # the switch: the game's gold box, empty while the value is off, ticked while it is on (two buttons, X4)
        body += ('buttonType = { name = "tb_s_%s_off" position = { x = %d y = %d } quadTextureSprite = "GFX_checkbox_gold_32" frame = 1 '
                 'clicksound = click_default pdx_tooltip = "%s" }\n' % (n, cx + 338, y, B.key("tb_s_%s_on_tt" % n, "Show %s on the top bar. It needs %d px of the strip; a value that does not fit stays off." % (c["label"].lower() if not n.startswith("res_") else c["label"], need))))
        body += ('buttonType = { name = "tb_s_%s_on" position = { x = %d y = %d } quadTextureSprite = "GFX_checkbox_gold_32" frame = 2 '
                 'clicksound = click_default pdx_tooltip = "%s" }\n' % (n, cx + 338, y, B.key("tb_s_off_tt", "Take this value off the top bar.")))
        refused = tb_refused(c)
        triggers += block("tb_s_%s_name_visible" % n, "NOT = { AND = { %s } }\n" % refused)
        triggers += block("tb_s_%s_name_off_visible" % n, refused + "\n")
        triggers += block("tb_s_%s_w_visible" % n, "NOT = { AND = { %s } }\n" % refused)
        triggers += block("tb_s_%s_w_off_visible" % n, refused + "\n")
        triggers += block("tb_s_%s_off_visible" % n, "NOT = { %s }\n" % tb_switch(n))
        triggers += block("tb_s_%s_off_click_enabled" % n, "NOT = { check_variable = { mod1440_tb_room < %d } }\n" % need)
        triggers += block("tb_s_%s_on_visible" % n, tb_switch(n) + "\n")
        effects += block("tb_s_%s_off_click" % n, setv("mod1440_tb_on_%s" % n, 1) + "mod1440_tb_place = yes\n")
        effects += block("tb_s_%s_on_click" % n, setv("mod1440_tb_on_%s" % n, 0) + "mod1440_tb_place = yes\n")
    body += button("tb_default", 16, foot_y, "GFX_button_123x34", B.key("tb_default", "Default"), tooltip=B.key(
        "tb_default_tt", "The eight values the strip starts with: political power and command power per day, stability and "
                         "war support per week, the three kinds of factories, and fuel."))
    body += text("tb_foot", 156, foot_y + 8, TB_PANEL_W - 156 - 16, B.key(
        "tb_foot", "§gThe values stand in the order of this list. Your choice is kept with your country.§!"), FONT_SMALL, height=20)
    effects += block("tb_close_click", setv("mod1440_tb_setup", 0))
    effects += block("tb_default_click", "mod1440_tb_default = yes\n")
    gui = box("mod1440_top_bar_setup", TB_PANEL_X, TB_PANEL_Y, TB_PANEL_W, height, body, PAGE_BG)
    script = scripted_gui("mod1440_top_bar_setup", "mod1440_top_bar_setup", "top_bar", visible=is_one("mod1440_tb_setup") + "\n",
                          effects=effects, triggers=triggers, properties=properties)
    return gui, script, height


def tb_effects():
    """mod1440_tb_place: the x of every chip that is on, the width used and the room left; mod1440_tb_default:
    the eight defaults on, the rest off. Both run on a click, on the first day of a save without them, and once
    at the start of a game."""
    place = tmp("tb_c", 0) + tmp("tb_g", 0)
    for c in TB_CHIPS:
        n, g = c["name"], TB_GROUPS.index(c["group"]) + 1
        place += iff(tb_switch(n), (
            iff("check_variable = { tb_g = %d }" % g, "add_to_temp_variable = { tb_c = %d }\n" % TB_GAP)
            + iff("check_variable = { tb_g > 0 }", "add_to_temp_variable = { tb_c = %d }\n" % TB_GROUP_GAP, "else_if")
            + setv("mod1440_tb_x_%s" % n, "tb_c")
            + setv("mod1440_tb_xi_%s" % n, "tb_c") + "add_to_variable = { mod1440_tb_xi_%s = %d }\n" % (n, TB_PAD_L)
            + setv("mod1440_tb_xt_%s" % n, "tb_c") + "add_to_variable = { mod1440_tb_xt_%s = %d }\n" % (n, c["text_x"])
            + "add_to_temp_variable = { tb_c = %d }\n" % c["width"] + tmp("tb_g", g)))
    place += setv("mod1440_tb_used", "tb_c") + setv("mod1440_tb_room", TB_ROOM) + "subtract_from_variable = { mod1440_tb_room = tb_c }\n"
    place += (setv("mod1440_tb_used_pct", "tb_c") + "multiply_variable = { mod1440_tb_used_pct = 100 }\n"
              + "divide_variable = { mod1440_tb_used_pct = %d }\n" % TB_ROOM)
    default = "".join(setv("mod1440_tb_on_%s" % c["name"], 1 if c["default"] else 0) for c in TB_CHIPS)
    default += setv("mod1440_tb_ver", TB_VER) + "mod1440_tb_place = yes\n"
    # the effect that another one calls stands first in the file (Engine Facts X70)
    return block("mod1440_tb_place", place) + "\n" + block("mod1440_tb_default", default)


def tb_daily():
    """A save of an earlier build, or a country the player takes over later: the defaults on the next day."""
    return iff("NOT = { check_variable = { mod1440_tb_ver = %d } }" % TB_VER, "mod1440_tb_default = yes\n")


# --- D2 fix round 1 (2026-10-17): the game cut "+2.32/d" with dots in its box of 51 px, a text the fonts make
# exactly 51 px wide, and the cut fell between the two characters of a colour code ("Could not find coloring for
# character '.'", twice a frame). A chip's text box holds its widest plausible value with this much to spare.
TB_TEXT_MARGIN = 3


def tb_widths():
    """Stops the build when a chip's box cannot hold its widest value (the game's font, where the game is
    installed: the width is the sum of the glyphs' advances, GUW-012)."""
    import guiparse
    game = guiparse.find_game_dir()
    if not game:
        return
    font = guiparse.load_font(FONT_LABEL, game)
    for c in TB_CHIPS:
        need = font.width(c["widest"]) + TB_TEXT_MARGIN
        if c["text_w"] < need:
            raise ValueError("top bar chip %s: its text box is %d px, %r needs %d" % (c["name"], c["text_w"], c["widest"], need))


def top_bar():
    tb_widths()
    gui, script = tb_strip()
    panel_gui, panel_script, _height = tb_panel()
    return gui + panel_gui, script + panel_script, tb_effects()


# The scene: samples of Germany on 1 January 1936 where they are known (35, 28 and 10 factories, 8 military
# factories idle, fuel 297K of 371K, the resource balance D4 checked), the others as the design drew them.
TB_SAMPLES = {
    "pp": "§G+2.3§!§g/d§!", "cp": "§G+0.85§!§g/d§!", "stab": "§G+0.2%§!§g/wk§!", "ws": "§G+0.3%§!§g/wk§!",
    "civ": "35  §g3 free§!", "mil": "28  §g8 idle§!", "mil_idle": "28  §Y8 idle§!", "dock": "10  §g0 idle§!", "dock_idle": "10  §Y0 idle§!",
    "cg": "25.0%", "fuel": "297K§g/371K§!", "mp_field": "1310K§g field§!", "mp_train": "38.4K§g training§!",
}
for _r, (_res, _value) in enumerate(zip(RESOURCES, ["3", "104", "-5", "3", "177", "1", "195"])):
    TB_SAMPLES["res_" + _res] = _value
    TB_SAMPLES["res_%s_neg" % _res] = "§R%s§!" % _value
TB_CHOSEN = ["pp", "stab", "ws", "civ", "mil", "dock", "res_oil", "res_rubber", "res_steel"]   # figure custom-chosen-detail


def tb_strip_hide(on, below=()):
    """What script hides of the moving strip with these values on; below: the chips whose twin shows (8 military
    factories idle; rubber below 0)."""
    hide = []
    for c in TB_CHIPS:
        n = c["name"]
        parts = list(tb_parts(c, 0))
        if n not in on:
            hide += ["tb_" + p for p in parts]
        elif c["twin"]:
            twin = n + ("_neg" if n.startswith("res_") else "_idle")
            hide += ["tb_" + (n if n in below else twin)]
            if n.startswith("res_"):
                hide += ["tb_" + n + ("_icon" if n in below else "_miss")]
    return hide


def tb_panel_hide(on):
    used, _at = tb_place(on)
    hide = []
    for c in TB_CHIPS:
        n = c["name"]
        refused = n not in on and TB_ROOM - used < c["width"] + TB_GROUP_GAP
        hide.append("tb_s_%s_%s" % (n, "off" if n in on else "on"))
        hide += ["tb_s_%s_name" % n, "tb_s_%s_w" % n] if refused else ["tb_s_%s_name_off" % n, "tb_s_%s_w_off" % n]
    return hide


def tb_used_sample(on):
    used, _at = tb_place(on)
    return "%d of %d px used, %d left. A value that needs more stays off." % (used, TB_ROOM, TB_ROOM - used)


def tb_scene():
    right, at = tb_place(TB_DEFAULT)
    chosen_right, chosen_at = tb_place(TB_CHOSEN)
    # the design measured these (scratch/phases/D7/custom-layout.json): the build must stand where it drew them
    assert (right, [TB_X + at[n] for n in TB_DEFAULT]) == (909, [1042, 1139, 1233, 1346, 1470, 1588, 1702, 1820]), at   # D2 fix round 1
    assert chosen_right == 884, chosen_right
    assert right <= TB_ROOM
    samples = {"tb_" + k: v for k, v in TB_SAMPLES.items()}
    place = {}
    for n, x in chosen_at.items():
        c = next(c for c in TB_CHIPS if c["name"] == n)
        for part, (px, py) in tb_parts(c, x).items():
            place["tb_" + part] = [px, py]
    strip_states = ["", "panel", "escape", "chosen"]
    windows = [
        {"name": "mod1440_top_bar_strip", "at": [TB_X, TB_Y], "drawIn": strip_states,
         "hide": tb_strip_hide(TB_DEFAULT, below=("mil",)),
         "_note": "The moving strip with its eight defaults. Script shows the yellow twin of military factories (8 idle) and the grey dockyards (0 idle), and hides the ten values that are off."},
        {"name": "mod1440_top_bar_fixed", "at": [TB_X, TB_Y], "drawIn": ["old_save"], "hide": ["tbf_mil", "tbf_dock_idle"],
         "_note": "The fixed twin: the eight defaults at fixed places, shown instead of the moving strip in a save of an earlier build until the first click on the edit button or the next day."},
        {"name": "mod1440_top_bar_edit", "at": [TB_EDIT[0], TB_EDIT[1]]},
        {"name": "mod1440_records_handle", "at": [2002, 3], "_note": "From mod1440_records.gui (tools/build_records.py): moved to the right end and lowered to 28 px in D7.",
         # --- E1 --- the red twin of the count (a new line of War and peace) is drawn in the War Diary's badge figure only
         "hide": ["rec_badge_war"]},
        {"name": "mod1440_top_bar_setup", "at": [TB_PANEL_X, TB_PANEL_Y], "drawIn": ["panel", "chosen"], "hide": tb_panel_hide(TB_DEFAULT),
         "_note": "The panel of the edit button, shown while mod1440_tb_setup is 1. With the defaults 3 px are left, so every value that is off is refused."},
    ]
    return {
        "phase": "D7", "file": "mod1440_top_bar.gui", "screenshot": "reference/vanilla/politics.jpg",
        "windows": windows,
        "samples": {"mod1440_top_bar_strip": samples, "mod1440_top_bar_fixed": {"tbf_" + k: v for k, v in TB_SAMPLES.items()},
                    "mod1440_top_bar_setup": {"tb_used": tb_used_sample(TB_DEFAULT)}},
        "setup": [{"wait": 1.0, "_note": "the clean state: the strip is on the top bar of every screen"}],
        "captures": [
            {"name": "panel", "steps": [{"clickWidget": "mod1440_top_bar_edit/tb_edit", "wait": 1.2}]},
            {"name": "escape", "steps": [{"key": "escape", "wait": 1.0, "_note": "the panel's close button takes Escape (SGUI-008); the game menu must not open"}]},
        ],
        "states": [
            {"name": "chosen", "_note": "Another choice, drawn by the renderer only (figure custom-chosen-detail of the design): command power and fuel off, oil, rubber (below 0, red with the crossed icon) and steel on; the panel open over it, 31 px left, so every value that is off is refused.",
             "hide": {"mod1440_top_bar_strip": tb_strip_hide(TB_CHOSEN, below=("mil", "res_rubber")),
                      "mod1440_top_bar_setup": tb_panel_hide(TB_CHOSEN)},
             "place": {"mod1440_top_bar_strip": place},
             "samples": {"mod1440_top_bar_setup": {"tb_used": tb_used_sample(TB_CHOSEN)}}},
            {"name": "old_save", "_note": "A save of a build before D7, until the first click on the edit button or the next day: the fixed twin of the eight defaults."},
        ],
        "expect": ["mod1440_top_bar_strip/tb_mil_bg", "mod1440_top_bar_strip/tb_fuel_bg", "mod1440_top_bar_edit/tb_edit", "mod1440_records_handle/rec_toggle"],
        "crop": [1030, 0, 1130, 600],
        "manual": [
            "Every value against the game's own number (Scripted GUIs rule 3); hover the tooltips",
            "A save of a build before D7: the fixed twin until the first click on the edit button or the next day",
            "A switch and the chips moving (a capture shows one state; the checker clicks a switch by hand in an open game, or the user does)",
            "A country with nuclear bombs: the nukes counter (x 970 to 1026) stays clear of the strip",
        ],
        "checklist": TB_CHECKLIST,
    }


TB_CHECKLIST = [
    "The strip stands inside the top bar's dark band: the chips' boxes at y 4 to 29 (or 6 to 31 if the 2 px of SGUI-007 apply), never on the band's lower edge (y 32 to 35) or the alerts row (y 40); measure in the 1:1 capture",
    "Eight chips from x 1042 to 1951 in this order: political power per day, command power per day, stability per week, war support per week, civilian factories (free), military factories (idle), dockyards (idle), fuel; then the edit button at 1970 and the Records handle at 2002 to 2152, 28 px high, clear of the clock plate (2168)",
    "Political power per day against the political power tooltip of the top bar",
    "Command power per day against the command power tooltip",
    "Stability and war support per week against the weekly change in their tooltips (the chip reads the modifiers stability_weekly and war_support_weekly; the tooltip may also apply a weekly factor)",
    "Civilian factories and free against the factory tooltip of the top bar (35, and the free ones once consumer goods and trade have taken theirs)",
    "Military factories and idle against the factory tooltip and the production screen (28 and 8 idle for Germany 1936): the idle count yellow while above 0; dockyards 10 and 0 idle, grey",
    "Fuel against the fuel tooltip of the top bar (297K of 371K for Germany 1936)",
    "Hover every chip: its tooltip names the value and says what the number means",
    "The edit button opens the panel at 1310,40 (842x544) under the band, clear of the alerts row; Escape and the close button close it, and Escape does not open the game menu",
    "With the defaults the panel says 909 of 912 px used, 3 left: every value that is off is refused (dimmed box, grey name, red width; its tooltip names the room it needs)",
    "Untick command power: the six chips after it move 91 px left at once, 94 px are left, and consumer goods and the seven resources become free to tick; tick oil: it stands after fuel with its own icon",
    "Consumer goods, manpower in the field and in training, and each resource against the game's numbers (production tab, Recruit & Deploy, trade tab) once ticked",
    "Default brings the eight back, in their places; the choice survives a save and a load",
    "error.log names no mod1440 file and has no Could not find sprite type line for a GFX_1440p_SG_topbox, topbtn or button_150x28 sprite",
    "No chip value is cut with dots (political power per day reads +2.3/d, command power +0.28/d for Germany in 1936), and error.log has no Could not find coloring for character line (D2 fix round 1)",
]

# ---------------------------------------------------------------- scenes: what the renderer and the harness need

# One scene per page (tools/scenes/<name>.json, see wiki/Game-Recipes.md): where the page stands on the screen,
# the recipe that brings it up, the widgets that prove it is up, and a sample for every text that holds a
# value, so that the renderer draws numbers and the tests measure them against their boxes.
SCENES = {
    "army_readiness": ar_scene(),      # D2 round 2
    "states": st_scene(),        # D3, D10
    # --- D4 round 2 ---
    "national_figures": {
        "phase": "D4", "file": "mod1440_figures.gui", "screenshot": "reference/vanilla/politics.jpg",
        "windows": NF_SCENE[0], "samples": NF_SCENE[1],
        "setup": [{"move": "open_politics"}, {"key": "shift+m", "wait": 1.5, "_note": "the page is hidden until asked for"}],
        "captures": [{"name": "all", "steps": [{"clickWidget": "mod1440_figures/nf_view_all", "wait": 1.0}]}, NF_SCENE[2]],
        "states": [{"name": "closed", "_note": "Politics with the page closed (the default): the Figures handle in the title strip at screen 353,90, no page."}],
        "teardown": [{"clickWidget": "mod1440_figures/nf_view_applies", "wait": 0.8},
                     {"key": "shift+m", "wait": 0.8, "_note": "hide it again: the page remembers per country whether it is open"}],
        "expect": ["mod1440_figures/nf_fold", "mod1440_figures/nf_view_all", "mod1440_figures/nf_view_changed", "mod1440_figures/h_zoom",
                   "mod1440_figures/h_range_24"],
        "crop": [540, 64, 1700, 1234],
        "manual": ["The advisor and law picker opened from the panel: it stands above the page",
                   "More than one month in the user's game: the Month and Year columns, the sparklines, the fit range growing from 2 to 5 years, and the Changed view after a real first of the month",
                   "Speed 5 with the page open: no stutter from the 25 sparklines, the graph and the four lists",
                   "D9, the user's game: a war that ends; the next days Casualties, all wars keeps its number while the grey 'in wars' falls, and the next first of the month writes a column of the month's dead",
                   "D9, the user's game: a save of the build before D9 with a finished war; the first opening back-fills Casualties, all wars and Casualties in the month from the old Casualties months"],
        "checklist": NF_CHECKLIST,
    },
    "history": {
        "phase": "D5", "file": "mod1440_figures.gui", "screenshot": "reference/vanilla/politics.jpg",
        "windows": NF_SCENE[0], "samples": NF_SCENE[1],
        "setup": [{"move": "open_politics"}, {"key": "shift+m", "wait": 1.5},
                  {"clickWidget": "mod1440_figures/nf_t4", "scene": "national_figures", "wait": 1.0}],
        "captures": [{"name": "ten_years", "steps": [{"clickWidget": "mod1440_figures/h_range_120", "scene": "national_figures", "wait": 1.0}]},
                     {"name": "oil", "steps": [{"clickWidget": "mod1440_figures/nf_t20", "scene": "national_figures", "wait": 1.0}]}] + NF_SCENE[3],
        "teardown": [{"clickWidget": "mod1440_figures/nf_t0", "scene": "national_figures", "wait": 0.8}, {"key": "shift+m", "wait": 0.8}],
        "expect": ["mod1440_figures/h_zoom", "mod1440_figures/nf_t4", "mod1440_figures/h_range_120", "mod1440_figures/nf_t31",
                   "mod1440_figures/nf_t33"],
        "crop": [540, 64, 1700, 800],
        "manual": ["More than one month: the graph gets a column on the first of each month, which no check lets pass"],
        "checklist": ["A click on a table row draws its figure; the chosen row has the lighter band and a yellow name",
                      "1 January 1936: one column at the left of the 2-year range, 57 px wide; its tooltip gives 1 January, 1936 and the value",
                      "10 years: the column is 11 px wide; the 2-year and 5-year grids draw nothing",
                      "A resource row (Oil) draws the oil balance; Germany 1936: 3",
                      "After `effect mod1440_chk_months`: 120 months, the 10-year range by default, year marks 1937 to 1946 under the first column of each year; 2 years and 5 years show the last 24 and 60 months with the marks under their Januaries; Zoom in starts the columns at the lowest month",
                      "After `effect mod1440_chk_months`, a resource row: a balance below zero draws from its lowest month and the orange zero line stands at the scale's 0",
                      "After `effect mod1440_chk_months_twenty` (a save of the 2026-10-16 build): the eleven new figures say 'Nothing is written down for this figure yet' and their table rows have no Month, Year or sparkline",
                      "The seven numbers against the columns; the tooltips of Highest and Lowest name their month"] + NF_HISTORY_CHECKLIST_D9,
    },
    # --- end D4 round 2 ---
    "top_bar": tb_scene(),      # d7-top-bar
}

SAMPLE_VALUES = {
    "manpower_k": "12500", "deployed_army_manpower_k": "4300", "deployed_navy_manpower_k": "310", "deployed_airforce_manpower_k": "275",
    "num_divisions": "350", "num_battalions": "3400", "army_experience": "500", "mod1440_ar_low_str": "24", "mod1440_ar_low_org": "17",
    "skill_level": "4", "num_units": "24", "num_units_in_combat": "12", "num_infantry": "20", "num_armored": "3", "num_motorized": "1",
    "mod1440_al_fill": "87", "mod1440_st_free": "12", "state_population_k": "12500", "compliance": "45", "resistance": "20",
    "mod1440_st_rows^num": "152", "mod1440_h_max": "1332.6", "mod1440_h_half": "666.3", "mod1440_h_latest": "1250.4",
    "fuel_k": "297.2", "max_fuel_k": "371.5", "num_ships": "38", "num_deployed_planes": "992", "num_controlled_states": "24",
    "amount_research_slots": "4", "num_researched_technologies": "55",
    "mod1440_h_date^num": "120", "mod1440_h_valid": "120", "mod1440_st_sum_pop": "125000",
    "mod1440_h_yrs": "10", "mod1440_h_total": "120",     # D4 round 2: the line under the chosen figure's name
    "num_equipment@convoy": "1250", "num_equipment@train_equipment": "250",
}


def sample_for(window, text_value):
    """A text with its values written in, as wide as the game will make it."""
    def one(match):
        inside = match.group(1)
        if window.startswith(("mod1440_records", "mod1440_state_card")):
            return build_records.sample(inside)
        if window.startswith("mod1440_states") and st_sample(window, inside) is not None:      # d3-states
            return st_sample(window, inside)
        if "GetName" in inside:
            return "Gerd von Rundstedt" if "army_readiness" in window else "Niederschlesien"
        if "GetDateStringNoHourLong" in inside:
            return "30 September, 1944"
        if "GetDateString" in inside:
            return "1936.1.1"
        if not inside.startswith("?"):
            return ""
        variable, _, fmt = inside[1:].partition("|")
        if "%" in fmt:
            return ("+" if "=" in fmt else "") + ("100%" if fmt.endswith("0") else "25.0%")
        if "*" in fmt:
            return "128.8K"
        if "=" in fmt:
            return "+2.32" if fmt.endswith("2") else "+104"
        if "GetTokenLocalizedKey" in variable and window.startswith("mod1440_figures"):
            return "Share of factories on consumer goods"
        if variable in SAMPLE_VALUES:
            return SAMPLE_VALUES[variable]
        if "_fill" in variable or variable.startswith("mod1440_nf_"):
            return "87"
        if variable.startswith("mod1440_h_yl_"):
            return str(1936 + int(variable[len("mod1440_h_yl_"):]))
        if variable.startswith("mod1440_h_"):
            return "1332.6"
        if variable.startswith(("mod1440_ar_short", "mod1440_st_sum")):
            return "1250"
        if variable.startswith(("building_level", "infrastructure", "industrial", "arms_factory")):
            return "20"
        if variable.startswith("resource"):
            return "250"
        if variable.startswith("num_of_"):
            return "128"
        return "1250000" if "equipment" in variable else "12500"
    return re.sub(r"\[([^\]]+)\]", one, text_value)


def scene_files(gui_by_file):
    """tools/scenes/<name>.json for every page, with a sample for each text of its windows that holds a value."""
    import json
    samples_by_window = {}
    for content in gui_by_file.values():
        starts = [(m.start(), m.group(1)) for m in re.finditer(r'^\tcontainerWindowType = \{\n\t\tname = "(mod1440_\w+)"', content, re.M)]
        for index, (start, window) in enumerate(starts):
            end = starts[index + 1][0] if index + 1 < len(starts) else len(content)
            for m in re.finditer(r'instantTextboxType = \{ name = "(\w+)"[^\n]*? text = "([^"]*)"', content[start:end]):
                value = B.loc.get(m.group(2), m.group(2))
                if "[" in value:
                    samples_by_window.setdefault(window, {})[m.group(1)] = sample_for(window, value)
    out = {}
    for name, scene in list(SCENES.items()) + list(build_records.SCENES.items()):
        windows = [w["name"] for w in scene["windows"]]
        document = {
            "_comment": "Generated by tools/build_managers.py: change the scene there. Keys are explained in wiki/Game-Recipes.md and in tools/scenes/recruit_deploy.json.",
            "screen": name, "phase": scene["phase"], "file": scene["file"], "screenshot": scene["screenshot"],
            "modOnly": True,
            "windows": scene["windows"],
            "samples": {w: samples_by_window[w] for w in windows if w in samples_by_window},
            "setup": scene["setup"], "captures": scene.get("captures", []), "expect": scene["expect"], "crop": scene["crop"],
            "manual": scene["manual"], "checklist": scene["checklist"],
        }
        for window, extra in scene.get("samples", {}).items():     # d2-readiness: samples of the scene's own
            document["samples"].setdefault(window, {}).update(extra)
        if "teardown" in scene:
            document["teardown"] = scene["teardown"]
        if "captures" in scene:
            document["captures"] = scene["captures"]
        # --- e-diary-wars: states the renderer can draw and the harness cannot bring up (render_gui.py --state)
        if "states" in scene:
            document["states"] = scene["states"]
        out["tools/scenes/%s.json" % name] = json.dumps(document, indent=2, ensure_ascii=True) + "\n"
    return out



# ---------------------------------------------------------------- assembling the files

HEADER_GUI = "# Generated by tools/build_managers.py. Scripted GUI containers of the mod (wiki/Scripted-GUIs.md).\n"
HEADER_TXT = "# Generated by tools/build_managers.py.\n"


def build():
    gui, script, count = army_readiness()
    B.files["interface/mod1440_army_readiness.gui"] = HEADER_GUI + "guiTypes = {\n" + indent(gui) + "}\n"
    B.files["common/scripted_guis/mod1440_army_readiness.txt"] = HEADER_TXT + block("scripted_gui", script)
    gui, script, listing, states_daily = states_table()
    B.files["interface/mod1440_states.gui"] = HEADER_GUI + "guiTypes = {\n" + indent(gui) + "}\n"
    B.files["common/scripted_guis/mod1440_states.txt"] = HEADER_TXT + block("scripted_gui", script)
    gui, script, shares, figures_daily, place = national_figures()
    recording, monthly = history_script(place)
    history_daily = ""      # since D4 and D5 are one page, its daily drawing is part of figures_daily
    B.files["interface/mod1440_figures.gui"] = HEADER_GUI + "guiTypes = {\n" + indent(gui) + "}\n"
    B.files["common/scripted_guis/mod1440_figures.txt"] = HEADER_TXT + block("scripted_gui", script)
    # --- D10 --- the population round and drawing stand before the listing, which calls the drawing
    B.files["common/scripted_effects/mod1440_effects.txt"] = (HEADER_TXT + count + "\n" + pop_script() + "\n" + listing + "\n" + shares
                                                              + "\n" + recording)
    # The top bar strip (D7): the strip, its fixed twin, the edit button and the panel
    gui, script, tb_script = top_bar()
    B.files["interface/mod1440_top_bar.gui"] = HEADER_GUI + "guiTypes = {\n" + indent(gui) + "}\n"
    B.files["common/scripted_guis/mod1440_top_bar.txt"] = HEADER_TXT + block("scripted_gui", script)
    B.files["common/scripted_effects/mod1440_top_bar.txt"] = HEADER_TXT + tb_script
    # The Records window of Milestone E: its pages, its recording and its hooks (tools/build_records.py)
    gui, script, records_effects, hooks, more_files = build_records.build(sys.modules[__name__])
    for rel, content in more_files.items():
        B.files[rel] = content
    B.files["interface/mod1440_records.gui"] = HEADER_GUI + "guiTypes = {\n" + indent(gui) + "}\n"
    B.files["common/scripted_guis/mod1440_records.txt"] = HEADER_TXT + block("scripted_gui", script)
    B.files["common/scripted_effects/mod1440_records.txt"] = HEADER_TXT + records_effects
    # The hooks. A new game: count and write down once for every country, so that whichever country the
    # player takes has its numbers from the first day. After that only a player's country costs time.
    B.files["common/on_actions/mod1440_on_actions.txt"] = HEADER_TXT + block("on_actions", (
        # D10: the state population round once: it covers every state of the map itself. E7: called in each country's
        # scope, as on_monthly does; outside every scope the game refused it ("mod1440_pop_round: Invalid Scope ...
        # provided: None", E7 launch 1). Its stamp (global.mod1440_pop_day) lets the first country make the round and
        # the others pass.
        block("on_startup", block("effect", block("every_country", "mod1440_ar_count = yes\n" + monthly
                                                 + block("if", "limit = { is_ai = no }\nmod1440_ev_init = yes\nmod1440_tb_default = yes\n")
                                                 + "mod1440_pop_round = yes\n")))
        + block("on_daily", block("effect", block("if", "limit = { is_ai = no }\nmod1440_ar_count = yes\n" + states_daily
                                                  + figures_daily + history_daily + "mod1440_rec_daily = yes\n" + tb_daily())))
        # D10: the population round after History's record; it is guarded, so it runs once a month in all
        + block("on_monthly", block("effect", block("if", "limit = { is_ai = no }\n" + monthly + "mod1440_pop_round = yes\n")))
        + "".join(block(name, block("effect", body)) for name, body in sorted(hooks.items()))))

    everything = "".join(B.files.values()) + "".join(B.loc.values())
    # A sprite the pages name and interface/mod1440_ui.gfx does not declare would show as nothing in the game,
    # and a new sprite needs a restart of the game (Engine Facts X27): better to stop here.
    declared = set(re.findall(r'name = "(GFX_1440p_\w+)"', io.open(os.path.join(ROOT, "interface", "mod1440_ui.gfx"), encoding="utf-8").read()))
    missing = sorted(set(re.findall(r"GFX_1440p_\w+", "".join(c for rel, c in B.files.items() if rel.endswith(".gui")))) - declared)
    if missing:
        raise ValueError("not declared in interface/mod1440_ui.gfx: " + ", ".join(missing))
    # A tooltip shows a "$key$" of its text as written: the game's name is put in a text box only (the sort
    # tooltips of the States page, fix round of 2026-10-16).
    tips = set(re.findall(r'pdx_tooltip = "(\w+)"', "".join(c for rel, c in B.files.items() if rel.endswith(".gui"))))
    nested = sorted(t for t in tips if re.search(r"\$\w+\$", B.loc.get(t, "")))
    if nested:
        raise ValueError("a $key$ in a tooltip is not resolved: " + ", ".join(nested))
    B.files.update(scene_files({rel: content for rel, content in B.files.items() if rel.endswith(".gui")}))
    # every name used after "@" and every text key held as "token:<key>" (Engine Facts X24, X37); "@var:x" is a variable
    tokens = sorted(set(re.findall(r"@(?!var:)([A-Za-z_][A-Za-z0-9_]*)", everything)) | set(re.findall(r"token:([A-Za-z_][A-Za-z0-9_]*)", everything)))
    B.files["common/synchronized_dynamic_tokens/mod1440_tokens.txt"] = "".join(t + "\n" for t in tokens)
    # The texts are English. Every other language of the game gets the same file under its own header:
    # without one the game shows the bare key. The names taken from the game ($key$ and plain keys such as
    # infantry_equipment) follow the player's language by themselves.
    entries = "".join(' %s:0 "%s"\n' % (key, value) for key, value in sorted(B.loc.items()))
    for language in LANGUAGES:
        B.files["localisation/%s/mod1440_l_%s.yml" % (language, language)] = "\ufeffl_%s:\n" % language + entries
    for rel, content in B.files.items():
        if rel.endswith((".gui", ".txt")) and content.count("{") != content.count("}"):
            raise ValueError("unbalanced braces in " + rel)


def main(argv):
    build()
    stale = []
    for rel, content in sorted(B.files.items()):
        path = os.path.join(ROOT, rel)
        current = io.open(path, encoding="utf-8", newline="").read() if os.path.isfile(path) else None
        if current is not None and current.replace("\r\n", "\n") == content:   # a checkout may carry CRLF
            continue
        stale.append(rel)
        if "--check" not in argv:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            io.open(path, "w", encoding="utf-8", newline="\n").write(content)
            print("wrote", rel)
    if "--check" in argv and stale:
        print("out of date (run python -I tools/build_managers.py): " + ", ".join(stale))
        return 1
    if not stale:
        print("all files are up to date")
    else:
        # A running game reads a changed localisation file with any reload of common/scripted_guis, and a
        # changed .gui file only for the scripted GUIs whose own file it reads again (Engine Facts X23).
        # So every file there gets a new time stamp, written or not.
        for rel in sorted(B.files):
            if rel.startswith("common/scripted_guis/") and rel not in stale:
                os.utime(os.path.join(ROOT, rel), None)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
