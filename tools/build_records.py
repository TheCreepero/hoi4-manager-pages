"""The role-play pages of Milestone E (wiki/Roleplay-Pages.md): the Records window and what it keeps.

Not run by itself: tools/build_managers.py imports it and writes its output with everything else.

    interface/mod1440_records.gui                        the window's four pages, their rows, the top bar button, the state card
    common/scripted_guis/mod1440_records.txt             what shows when, and what the buttons do
    common/scripted_effects/mod1440_records.txt          the recording, the daily comparison, the lists of the pages
    common/scripted_effects/mod1440_portraits.txt        which sprite the game shows for each general, admiral and head of government
    common/scripted_effects/mod1440_victory_points.txt   the daily look at who holds each victory point
    hooks                                                handed back to build_managers.py, which writes the one on_actions file

What a record is (wiki/Engine-Facts.md): a line of the log holds a date, a text key and up to three scopes (a
state, a country, a character); the name is looked up when the row is drawn (X33, X34, X37). An officer's
record is variables of the mod on the officer himself (X32). Nothing here writes to the game but one command,
add_history_entry, for the unit honours of phase E6.

How the pages look (wiki/Scripted-GUIs.md, "The Records"): dark cards as on the manager pages; figures as
tiles, a small label over a large value; every list striped, with a bar of column heads; names in the game's
highlight yellow; the game's own text icons, flags, portraits, medal strips and progress bars. The sprites are
declared in interface/mod1440_ui.gfx (GFX_1440p_SG_*), all of them tiles of vanilla textures.

Two tables of game content stand beside this file, made by tools/make_game_tables.py: the portrait sprite of
every named character (portraits_table.py) and every victory point (victory_points_table.py).
"""
import os
import re
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import layout  # noqa: E402

M = None        # tools/build_managers.py, set by build(): its helpers write the .gui and script pieces
B = None

REC_X, REC_Y, REC_W, REC_H = 440, 100, 1680, 1220
# The page body every page of the window has, under the title strip and the tab bar (scratch/redesign/CONTRACTS.md)
REC_BODY_X, REC_BODY_Y, REC_BODY_W, REC_BODY_H = 14, 116, 1652, 1090
# The pages by their number, which a save keeps (mod1440_rec_page); TAB_ORDER is the order of their tabs.
PAGES = [("wd", "War Diary"), ("of", "Officers"), ("gv", "Government"), ("wr", "Wars")]
TAB_ORDER = [0, 3, 1, 2]                    # War Diary, Wars, Officers, Government (the user's choice, 2026-10-16)
TAB_W, TAB_H, TAB_GAP, TAB_Y = 236, 44, 6, 64
TAB_SPRITE = "GFX_1440p_SG_tab_236x44"      # the intel ledger's tab; the page in front has the gold chevrons (_on)
TAB_SPRITE_ON = "GFX_1440p_SG_tab_236x44_on"
TAB_ICON = {0: "army_experience", 1: "command_power", 2: "pol_power", 3: "victory_points"}
# what a tab counts, in the window's scope; the Officers page's count is chosen by its own section
OF_TAB_COUNT = "[?mod1440_of_serving|0]"   # the officers serving today, counted by the daily round (e-officers-gov)
# E4 fix round 1: the Wars tab counts wars of today (mod1440_wr_wars, kept by mod1440_wr_count_wars), as its page does
TAB_COUNT = {0: "[?mod1440_ev_date^num|0] lines", 1: OF_TAB_COUNT, 2: "", 3: "[?mod1440_wr_wars|0] at war"}
# what each page is for: the tooltip of its tab (the hints of the old title strip)
PAGE_HINTS = {
    0: "What happened, day by day: written by the mod as the game goes, from the day it is active.",
    1: "Every general and admiral, with what the mod has written down about him. Click one for his record.",
    2: "Who rules and who serves. A date is the day the mod first saw the name in office.",
    3: "One row per war, its enemies joined. Click a war for its file.",     # E4 round 2
}
LOG_KEEP = 1000         # lines of each log (500 until 2026-10-16)
MARK_KEEP = 300         # lines the player has marked: the chronicle, which age never trims
VIEW_ROWS = 200         # rows of the diary on one page of the list, day headers included
BLANK = "token:mod1440_blank"
TILE_W, TILE_H = 156, 64                    # the plate of a figure (build_managers.tile)
SMALL_TILE = 148                            # a narrower plate, where three stand beside a portrait
STRIPE, PICK = layout.STRIPE, layout.PICK   # the bands of every second row and of the chosen row
ODD_ROWS = 512                              # rows a list can stripe
LONG = "GetDateStringNoHourLong"            # "1 January, 1936"
UNKNOWN = "GFX_portrait_unknown"            # the game's picture of a leader it has no portrait of (156x210)
FLAG = "GFX_shield_medium"                  # the game's flag in its frame (82x52)
# A flag whose image is [<country>.GetFlag] is drawn at the size of its sprite's mask, whatever the icon's scale (fix
# round 1: at 0.5 and 0.8 it came out 82x52). A small flag takes the game's 41x26 sprite, as Kaiserreich does.
FLAG_SMALL = "GFX_flag_small2"
VP_MAJOR = 15                               # a victory point worth this much is written into the main log too


# ---------------------------------------------------------------- small pieces

# The pieces every page shares are in tools/build_managers.py: script (block, iff, els, setv, tmp, is_one,
# flip) and the look (plain, scaled, listing, row, heads, tile, card, gauge). Here they are reached by their
# bare names, which reads better in the long page functions below.

def _shared(name):
    def call(*args, **kwargs):
        return getattr(M, name)(*args, **kwargs)
    call.__name__ = name
    return call


block, iff, els, setv, tmp, is_one, flip = (_shared(n) for n in ("block", "iff", "els", "setv", "tmp", "is_one", "flip"))
plain, scaled, listing, row, heads, tile, card, gauge = (
    _shared(n) for n in ("plain", "scaled", "listing", "row", "heads", "tile", "card", "gauge"))


def token(name, words):
    """A text the script holds as a text key (X37). The key is lower case, as the probe's were."""
    key = "mod1440_" + name
    if B.loc.get(key, words) != words:
        raise ValueError("two texts for " + key)
    B.loc[key] = words
    return "token:" + key


def head(prefix, page, hint=None):
    """The frame every page of the window has (e-diary-wars, 2026-10-16): a title strip with the country's flag,
    Records, the country's name and the record's age, and Close; under it a tab bar, one tab per page with its
    family's icon, its name and a live count. What a page is for is the tooltip of its tab (PAGE_HINTS; <hint>
    is not shown). The page itself goes into the body REC_BODY_*. Returns the widgets, effects and properties."""
    body = M.title_strip(prefix + "_head", REC_W, 56)
    # the flag at its own size: an icon whose image is a flag draws it at the size of the sprite's mask, whatever
    # its scale (fix round 1: at 0.8 it came out 82x52 over the title)
    body += flag(prefix + "_flag", 12, 5)
    properties = flown(prefix + "_flag", "ROOT")
    body += M.text(prefix + "_title", 104, 9, 136, B.key("rec_title", "Records"), M.FONT_TITLE, height=44)
    body += M.text(prefix + "_country", 246, 19, 420, B.key("rec_country", "[ROOT.GetName]"), M.FONT_CARD, height=30, fixed=True)
    body += M.text(prefix + "_since", REC_W - 84 - 620, 22, 620, B.key(
        "rec_since", "Kept since [?mod1440_ev_since.%s]  -  [?mod1440_rec_days|0] days on record" % LONG), M.FONT_SMALL, "right", 22)
    effects = ""
    for slot, n in enumerate(TAB_ORDER):
        x = REC_BODY_X + slot * (TAB_W + TAB_GAP)
        tab = "%s_tab_%d" % (prefix, n)
        # each page is a window of its own, so its own tab is written in front (a tiled sprite takes no frame)
        body += M.button(tab, x, TAB_Y, TAB_SPRITE_ON if n == page else TAB_SPRITE, tooltip=B.key("rec_tab_%d_tt" % n, PAGE_HINTS[n]))
        body += plain(tab + "_name", x + 18, TAB_Y + 11, 150, B.key("rec_tab_%d" % n, "£%s  %s" % (TAB_ICON[n], PAGES[n][1])))
        if TAB_COUNT[n]:
            body += plain(tab + "_n", x + TAB_W - 30 - 90, TAB_Y + 13, 90, B.key("rec_tab_%d_n" % n, TAB_COUNT[n]), M.FONT_SMALL, "right", 22)
        effects += block(tab + "_click", setv("mod1440_rec_page", n) + "mod1440_rec_show = yes\n")
    body += M.close_button(prefix + "_close", REC_W - 66, 12, tooltip=B.key("rec_close_tt", "Close"))
    effects += block(prefix + "_close_click", "mod1440_rec_close = yes\n")
    return body, effects, properties


def page_gui(prefix, page, body, **parts):
    visible = "check_variable = { mod1440_rec_open = 1 }\ncheck_variable = { mod1440_rec_page = %d }\n" % page
    gui = M.box("mod1440_records_" + prefix, REC_X, REC_Y, REC_W, REC_H, body, M.PAGE_BG)
    return gui, M.scripted_gui("mod1440_records_" + prefix, "mod1440_records_" + prefix, visible=visible, **parts)


def pad(arrays, count):
    """Script that fills the arrays up to <count> elements, so that a text of a hidden row reads no missing element."""
    first = arrays[0][0]
    return block("for_loop_effect", "start = 0\nend = %d\nvalue = pad_n\n" % count + iff(
        "check_variable = { %s^num < %d }" % (first, count), "".join("add_to_array = { %s = %s }\n" % a for a in arrays)))


def shown_if(names, trigger):
    """The same <widget>_visible trigger for several widgets."""
    return "".join(block(name + "_visible", trigger) for name in names)


# ---------------------------------------------------------------- portraits and flags

# An icon shows another sprite when script names one: the "image" property takes a text, and the text can hold
# a variable (the game's _documentation.md of scripted GUIs; The New Order writes "GFX_[?v.GetTokenKey]").
# A person's portrait: the game declares a sprite for each named character (GFX_portrait_...), and script can
# ask whether a character is a certain one (is_character). So the mod carries the list of who has which sprite
# (portraits_table.py) and puts the sprite's name on the officer as a text key, once. A general the game made
# up has a portrait script cannot learn: he shows the game's picture of an unknown leader.

# The strips of medal pictures are sprites of this mod on the game's own pictures (interface/mod1440_ui.gfx, made
# with tools/list_medals.py --sprites). The game's sprites GFX_medal_icon_<set>_large are in interface/medals.gfx,
# and a mod that brings a file of that name drops the sets its copy lacks: Road to 56 has none for Ethiopia, and
# the game then logs "Could not find sprite type" for every icon that names it.
MEDAL_STRIP = "GFX_1440p_medal_%s"


def table_version(table):
    """A number that changes when a table of game content changes: what script kept from the old one is then
    worked out again."""
    return zlib.crc32(repr(table).encode("utf-8")) % 1000000 + 1


def portrait(name, x, y, scale=1.0):
    """The icon of a portrait: an unknown leader until script names a sprite (see shown())."""
    return scaled(name, x, y, UNKNOWN, scale)


def shown(name, variable):
    """The property that gives a portrait icon the sprite whose name the variable holds as a text key."""
    return block(name, 'image = "[?%s.GetTokenKey]"\n' % variable)


# E7 (2026-10-29): the game's own portrait of a unit leader. "portrait" as an icon's image, in a list row whose scope
# is a general, an admiral or an operative, draws his large portrait with the game's own code: sprites, texture files
# (Road to 56), generated faces and portraits changed by effect alike [SGUI-053, seen in 1.19.4]. Only a unit leader:
# a person without the role draws the unknown man, so a head of government, an advisor who is no general and an
# officer who no longer serves keep the table above (portraits(), the flag fallback of the Wars page).
# A single portrait becomes a list of one row over an array that holds the leader as the mod keeps him (of_me) and is
# filled where the slot is filled, on a click or in the daily round: empty while the slot shows the table instead.
GAME_FACE = 'image = "portrait"\n'


def face_size(scale):
    """The size of a large portrait (156x210) at <scale>, as the game draws it."""
    return int(156 * scale), int(210 * scale)


def game_face(name, scale, through_clicks=False):
    """The row of one game portrait: the container mod1440_records_<name>_row with the icon <name> at 0,0. Its own
    sprite is the unknown leader, whose size and scale the drawn portrait takes. through_clicks: the icon lets a click
    through to a button under it."""
    w, h = face_size(scale)
    icon = through(name, 0, 0, UNKNOWN, scale) if through_clicks else scaled(name, 0, 0, UNKNOWN, scale)
    return row("mod1440_records_%s_row" % name, w, h, icon)


def face_grid(grid, x, y, scale, height=None):
    """The grid of a game portrait's list at x, y: one row of a portrait's size, or rows down <height> (100%)."""
    w, h = face_size(scale)
    tall = "100%%" if height == "full" else str(height or h)
    return ('gridboxtype = {\n\tname = "%s"\n\tposition = { x = %d y = %d }\n\tsize = { width = %d height = %s }\n'
            '\tslotsize = { width = 1 height = 1 }\n\tadd_horizontal = no\n\tformat = "UPPER_LEFT"\n}\n' % (grid, x, y, w, tall))


def face_list(grid, array, name):
    """The dynamic list of a game portrait: one row per element of <array>, its scope the leader."""
    return block(grid, 'array = %s\nchange_scope = yes\nentry_container = "mod1440_records_%s_row"\n' % (array, name))


# E7 gate B (2026-10-29): whether an officer is a unit leader is asked where his scope is entered and kept on him as
# mod1440_of_ul (1 yes, 0 no): in the daily round over every known officer (mod1440_of_gone), when the Officers page
# lists (keep) and when the War Diary's page is made (face()). A list row reads it; a row whose element is the country
# or a character with no scope reads 0. Not mod1440_of_seen_day: the daily round sets that at 24:00 of the day before
# (X53), so during a day every officer looked as if he had left until the Officers page listed again.
UL_MARK = "set_variable = { mod1440_of_ul = 0 }\nif = {\n\tlimit = { is_unit_leader = yes }\n\tset_variable = { mod1440_of_ul = 1 }\n}\n"
SERVES = "check_variable = { mod1440_of_ul = 1 }"


def unit_leader_into(holder, array, flag):
    """Script for the country in scope: <array> holds the character in the variable <holder> when he is a unit leader,
    and is empty otherwise; the temporary <flag> says which (1 when he is)."""
    return ("clear_array = %s\n" % array + tmp(flag, 0) + tmp(flag + "_c", holder)
            + block("var:%s_c" % flag, iff("is_unit_leader = yes", tmp(flag, 1)))
            + iff("check_variable = { %s = 1 }" % flag, "add_to_array = { %s = %s }\n" % (array, holder)))


def flag(name, x, y):
    """The icon of a flag; flown(name, country) says whose."""
    return M.icon(name, x, y, FLAG)


def flown(name, country):
    return block(name, 'image = "[%s.GetFlag]"\n' % country)


def portraits():
    """The script that finds a person's portrait. Returns the text of common/scripted_effects/mod1440_portraits.txt
    and the version of the table it was made from.

    mod1440_p_officer   in the scope of a general or an admiral, PREV his country: leaves the sprite's name on him
    mod1440_p_leader    in the scope of a head of government, PREV his country: leaves it in the temporary p_tok
    """
    from portraits_table import PORTRAITS, TAGS
    # the officers other mods add, when their table has been made (tools/make_game_tables.py --mods): a name the
    # loaded game does not know is not found and logs nothing (Engine Facts X68)
    try:
        from portraits_mods_table import PORTRAITS as others
    except ImportError:
        others = []
    game_own = set(row[0] for row in PORTRAITS)
    PORTRAITS = PORTRAITS + [row for row in others if row[0] not in game_own]
    version = table_version(PORTRAITS)
    unknown = "token:" + UNKNOWN

    def chains(prefix, people):
        """One effect per file of characters, and the script that calls the country's own file first."""
        by_file = {}
        for name, source, sprite in people:
            by_file.setdefault(source, []).append((name, sprite))
        effects, own, others = "", "", ""
        for source in sorted(by_file):
            # is_character writes an error for a character no country has recruited yet (seen in game: "not a
            # valid character"), so the country is asked first whether it has him, which the game's own script
            # does for the same reason
            body = "".join(iff("PREV = { has_character = %s } is_character = %s" % (name, name),
                               tmp("p_tok", "token:" + sprite) + tmp("p_found", 1), "if" if n == 0 else "else_if")
                           for n, (name, sprite) in enumerate(by_file[source]))
            effects += block("mod1440_p_%s_%s" % (prefix, source), body)
            call = "mod1440_p_%s_%s = yes\n" % (prefix, source)
            if source in TAGS:
                own += iff("PREV = { original_tag = %s }" % source, call, "else_if" if own else "if")
            others += iff("check_variable = { p_found = 0 }", call)
        # a person who serves another country than the one whose file names him is found by going through all
        return effects, tmp("p_tok", unknown) + tmp("p_found", 0) + own + iff("check_variable = { p_found = 0 }", others)

    officers, leaders = [], []
    plain_name = re.compile(r"^[A-Za-z0-9_]+$")     # eight names of the game hold a hyphen: left out, a text key may not take it
    for name, source, army, navy, civilian, roles in PORTRAITS:
        if not plain_name.match(name):
            continue
        if "country_leader" in roles and plain_name.match(civilian or army or navy or "-"):
            leaders.append((name, source, civilian or army or navy))
        # D2 fix round 3: also a character whose file gives him no command but an army or navy portrait
        # (officer_by_effect, tools/make_game_tables.py): an effect can make him a general (Martin Bormann)
        if any(role in roles for role in ("corps_commander", "field_marshal", "navy_leader", "officer_by_effect")):
            # an admiral shows his navy portrait, a general his army portrait; whichever the game has otherwise
            first = (navy or army) if roles.strip() == "navy_leader" else (army or navy)
            if plain_name.match(first or civilian or "-"):
                officers.append((name, source, first or civilian))
    officer_effects, find_officer = chains("of", officers)
    leader_effects, find_leader = chains("ld", leaders)
    out = ("# Generated by tools/build_managers.py from tools/portraits_table.py (the game's characters).\n"
           "# The sprite the game shows for a person, as a text key: an icon of the Records window takes it as its image.\n\n"
           "# In the scope of a general or an admiral, PREV his country. %d officers.\n" % len(officers)
           + block("mod1440_p_officer", find_officer + setv("mod1440_p", "p_tok") + stamped("mod1440_p_ver", version))
           + "\n# In the scope of a head of government, PREV his country: the sprite is left in p_tok. %d leaders.\n" % len(leaders)
           + block("mod1440_p_leader", find_leader)
           + "\n" + officer_effects + "\n" + leader_effects)
    return out, version


def leader_portrait(country, variable, version):
    """Script that puts the portrait of a country's head of government into a variable of the country in
    scope. <country> is a variable that holds the country, or THIS. The portrait is looked up when another
    leader rules or the table has changed, and kept on the leader's own country (mod1440_ld_p)."""
    find = (iff("OR = { %s NOT = { check_variable = { mod1440_ld_p_of = country_leader } } }" % stale("mod1440_ld_p_ver", version), (
        tmp("p_ld", "country_leader") + block("var:p_ld", "mod1440_p_leader = yes\n")
        + setv("mod1440_ld_p", "p_tok") + stamped("mod1440_ld_p_ver", version) + setv("mod1440_ld_p_of", "country_leader")))
        + tmp("p_face", "mod1440_ld_p"))
    return (tmp("p_face", "token:" + UNKNOWN) + (find if country == "THIS" else block("var:" + country, iff("exists = yes", find)))
            + setv(variable, "p_face"))


# ---------------------------------------------------------------- the recording

# A kind of line is (name, family, words). The family is the filter of the diary it belongs to:
# 1 war and peace, 2 territory, 3 government, 4 officers, 5 air and sea. A kind's place in this list is its
# number in the counters (mod1440_ct), which a save keeps: add new kinds at the end.
KINDS = [
    ("begins", 1, "The record begins"),
    ("war_on", 1, "War declared on"), ("war_by", 1, "War declared by"), ("war_with", 1, "At war with"),
    ("peace", 1, "Peace with"), ("capitulated", 1, "Capitulated:"), ("we_capitulated", 1, "We capitulated"),
    ("annexed", 1, "Annexed"), ("subject_new", 1, "Made a subject:"), ("subject_gone", 1, "No longer a subject:"),
    ("faction_in", 1, "Joined the faction led by"), ("faction_out", 1, "Left the faction"),
    ("member_in", 1, "Joined our faction:"), ("member_out", 1, "Left our faction:"),
    ("state_taken", 2, "State taken"), ("state_lost", 2, "State lost"),
    ("capital_taken", 2, "Capital taken"), ("capital_lost", 2, "Capital lost"),
    ("landing", 2, "Landing in"), ("airborne", 2, "Airborne landing in"), ("cited", 2, "Divisions cited in"),
    ("party", 3, "The ruling party changed"), ("government", 3, "The government changed"), ("election", 3, "An election was held"),
    ("leader", 3, "New head of government"), ("appointed", 3, "Appointed"), ("dismissed", 3, "Left office"),
    ("commissioned", 4, "Commissioned"), ("promoted", 4, "Promoted to field marshal"), ("level", 4, "Gained a skill level"),
    ("decorated", 4, "Decorated"),
    ("ace_new", 5, "An ace was promoted"), ("ace_lost", 5, "An ace was lost"), ("ace_down", 5, "An enemy ace was shot down"),
    ("pride_lost", 5, "Our pride of the fleet was sunk by"), ("pride_sunk", 5, "Sank the pride of the fleet of"),
    ("vp_taken", 2, "Victory point taken"), ("vp_lost", 2, "Victory point lost"),
    ("commissioned_more", 4, "More officers commissioned"),
    # E1 review (2026-10-22): a change of hands with a country we are not at war with; an officer gone or held; the
    # hooks of R5 the design chose; a casualty step of the daily round
    ("state_received", 2, "Received from"), ("state_handed", 2, "Handed over to"),
    ("officer_gone", 4, "Left the service"), ("officer_captured", 4, "Captured:"),
    ("volunteers_sent", 1, "Volunteers sent to"), ("volunteers_back", 1, "Volunteers recalled from"),
    ("exiled", 3, "Our government went into exile in"), ("exile_hosted", 3, "Hosting the exiled government of"),
    ("reinstated", 3, "Our government is back from exile"), ("cipher", 1, "Broke the cipher of"),
    ("civil_war_won", 1, "Won the civil war against"), ("fought_on", 1, "We fight on: no longer capitulated"),
    ("casualties", 1, "Our casualties passed"),
]
# A run of state lines of one day, kind and country that the diary folds into one row (All and a country's lines)
FOLDED_KINDS = ("state_taken", "state_lost", "state_received", "state_handed")
FOLD_MIN = 3                    # lines a run has before it is folded
# the casualty steps of the daily round, in thousands (casualties_k)
CASUALTY_STEPS = [10, 25, 50, 100, 250, 500, 1000, 2000, 5000]
FAMILY = dict((name, family) for name, family, words in KINDS)
NUMBER = dict((name, n) for n, (name, family, words) in enumerate(KINDS))
# What a line holds. a: whom or what it is about (sa says which: 1 a person, 2 a state, 3 the name of a victory
# point), b: a country (sb 1), c: the officer on the spot (sc 1), p: for a victory point its state, x: 1 when
# the line stands in the other log too.
# k: 1 when the player has marked the line; id: a number of its own (the same in both logs for a line in both),
# by which a mark finds the line again in the other log and in the chronicle.
# n: a number the line carries (E1 review, 2026-10-22): the skill level reached, how many more officers, the divisions
# cited, the casualty step in thousands; 0 for none.
LOG_ARRAYS = ["date", "day", "kind", "fam", "a", "b", "sa", "sb", "c", "sc", "p", "x", "k", "id", "n"]
NEW_ARRAYS = ["c", "sc", "p", "x"]          # a game saved before 2026-10-13 has logs without these
MARK_ARRAYS = ["k", "id"]                   # ... and one saved before 2026-10-16 without these
NUMBER_ARRAYS = ["n"]                       # ... and one saved before 2026-10-22 without this (the chronicle too)
MARK_ID_BASE = {"ev": 0, "tr": 5000}        # the old lines get negative numbers of their own, apart in each log
# the game's own text icon for each family
FAMILY_ICON = {1: "army_experience", 2: "victory_points", 3: "pol_power", 4: "command_power", 5: "air_experience"}


def fill(name, a=None, b=None, state=False, point=False, c=None, sc=None, p=None, n=None):
    """Script that sets what the next line says: its kind, and whom or what it is about. a is a character, a
    state (state=True) or the text key of a victory point's name (point=True); b a country; c an officer,
    written when the temporary variable sc is above zero (or always, without sc); p the state of a point; n a
    number the line carries (part n)."""
    out = tmp("ev_kind", "token:mod1440_ev_" + name) + tmp("ev_fam", FAMILY[name]) + tmp("ev_kid", NUMBER[name])
    out += tmp("ev_sa", (3 if point else 2 if state else 1) if a else 0) + tmp("ev_a", a or 0)
    # the officer has temporary variables of his own: ev_c is the country in the loops of the daily comparison
    out += tmp("ev_sb", 1 if b else 0) + tmp("ev_b", b or 0) + tmp("ev_so", 0) + tmp("ev_o", 0)
    if c:
        officer = tmp("ev_so", 1) + tmp("ev_o", c)
        out += iff("check_variable = { %s > 0 }" % sc, officer) if sc else officer
    return out + tmp("ev_p", p or 0) + tmp("ev_x", 0) + tmp("ev_n", n or 0)


def line(name, a=None, b=None, state=False, log="ev", both=False, **more):
    """Script that writes one line for the country in scope: into one log, or into both."""
    out = fill(name, a, b, state, **more)
    if both:
        return out + tmp("ev_x", 1) + "mod1440_ev_add = yes\nmod1440_tr_add = yes\n"
    return out + "mod1440_%s_add = yes\n" % log


def count(*names):
    """Script that sums the counters of some kinds into the temporary variable ct_sum."""
    return tmp("ct_sum", 0) + "".join("add_to_temp_variable = { ct_sum = mod1440_ct^%d }\n" % NUMBER[name] for name in names)


def recording():
    for name, family, words in KINDS:
        token("ev_" + name, words)
    token("blank", "")
    out = "# The Records: one line of a log, for the country in scope. The caller has set the temporary variables\n"
    out += "# ev_kind, ev_fam, ev_kid and one for each part of a line (tools/build_records.py, fill()). The oldest line goes past %d.\n" % LOG_KEEP
    out += "# Each kind of line is counted (mod1440_ct), a line of the territory log in that log only.\n"
    values = {"date": "global.date", "day": "global.num_days", "kind": "ev_kind", "fam": "ev_fam", "a": "ev_a", "b": "ev_b",
              "sa": "ev_sa", "sb": "ev_sb", "c": "ev_o", "sc": "ev_so", "p": "ev_p", "x": "ev_x", "k": 0, "id": "ev_id", "n": "ev_n"}
    counted = pad([("mod1440_ct", 0)], len(KINDS) + 8) + "add_to_variable = { mod1440_ct^ev_kid = 1 }\n"
    # the state a line names counts it (the state card says how many lines it has)
    named = (iff("check_variable = { ev_sa = 2 }", block("var:ev_a", "add_to_variable = { mod1440_sr_lines = 1 }\n"))
             + iff("check_variable = { ev_sa = 3 }", block("var:ev_p", "add_to_variable = { mod1440_sr_lines = 1 }\n")))
    new_id = "add_to_variable = { mod1440_ln_next = 1 }\n" + tmp("ev_id", "mod1440_ln_next")
    for log in ("ev", "tr"):
        body = "mod1440_ev_grow = yes\n"
        # a line in both logs keeps the number the main log gave it
        body += new_id if log == "ev" else iff("NOT = { check_variable = { ev_x = 1 } }", new_id)
        body += "".join("add_to_array = { mod1440_%s_%s = %s }\n" % (log, part, values[part]) for part in LOG_ARRAYS)
        body += iff("check_variable = { mod1440_%s_date^num > %d }" % (log, LOG_KEEP),
                    "".join("remove_from_array = { array = mod1440_%s_%s index = 0 }\n" % (log, part) for part in LOG_ARRAYS))
        # a line of the territory family that stands in both logs is counted there; one of the main log alone (a
        # landing, an airborne drop) here (E1 review: they were counted in neither)
        body += counted if log == "tr" else iff("NOT = { AND = { check_variable = { ev_fam = 2 } check_variable = { ev_x = 1 } } }", counted)
        body += named if log == "ev" else iff("NOT = { check_variable = { ev_x = 1 } }", named)
        if log == "ev":
            # the badge of the top bar button: lines written while the window was closed, how many of War and
            # peace, and the newest line for its tooltip (its name: the person or state, a point's state, the country)
            body += iff("NOT = { %s }" % is_one("mod1440_rec_open"), "add_to_variable = { mod1440_rec_new = 1 }\n"
                        + iff("check_variable = { ev_fam = 1 }", "add_to_variable = { mod1440_rec_new_war = 1 }\n"))
            body += (setv("mod1440_rec_last_k", "ev_kind") + setv("mod1440_rec_last_d", "global.date") + setv("mod1440_rec_last_n", "THIS")
                     + iff("check_variable = { ev_sb = 1 }", setv("mod1440_rec_last_n", "ev_b"))
                     + iff("OR = { check_variable = { ev_sa = 1 } check_variable = { ev_sa = 2 } }", setv("mod1440_rec_last_n", "ev_a"))
                     + iff("check_variable = { ev_sa = 3 }", setv("mod1440_rec_last_n", "ev_p"), "else_if"))
        # a person the line names by his place says so himself from now on (places())
        body += iff("check_variable = { ev_sa = 1 }", tmp("ch_v", "ev_a") + "mod1440_ch_mark = yes\n")
        body += iff("check_variable = { ev_so = 1 }", tmp("ch_v", "ev_o") + "mod1440_ch_mark = yes\n")
        out += block("mod1440_%s_add" % log, body) + "\n"
    out += "# The Records: a game saved before a line had an officer has logs without the newer parts. They get a 0 for\n"
    out += "# each line that is there, and a capital in the territory log the mark that it stands in the main log too.\n"
    grow = ""
    for log in ("ev", "tr"):
        longer = "check_variable = { mod1440_%s_x^num < mod1440_%s_date^num }" % (log, log)
        fix = block("for_loop_effect", "start = 0\nend = %d\nvalue = gr_n\n" % LOG_KEEP + "".join(
            iff("check_variable = { mod1440_%s_%s^num < mod1440_%s_date^num }" % (log, part, log),
                "add_to_array = { array = mod1440_%s_%s value = 0 index = 0 }\n" % (log, part)) for part in NEW_ARRAYS))
        if log == "tr":
            fix += (tmp("gr_taken", "token:mod1440_ev_capital_taken") + tmp("gr_lost", "token:mod1440_ev_capital_lost")
                    + block("for_each_loop", "array = mod1440_tr_kind\nvalue = gr_k\nindex = gr_i\n" + iff(
                        "OR = { check_variable = { gr_k = gr_taken } check_variable = { gr_k = gr_lost } }", setv("mod1440_tr_x^gr_i", 1))))
        grow += iff(longer, fix)
        # 2026-10-16: the mark and the number of each line. An old line gets a number below zero of its own.
        marks = block("for_loop_effect", "start = 0\nend = %d\nvalue = gr_n\n" % LOG_KEEP + (
            iff("check_variable = { mod1440_%s_k^num < mod1440_%s_date^num }" % (log, log),
                "add_to_array = { array = mod1440_%s_k value = 0 index = 0 }\n" % log)
            + iff("check_variable = { mod1440_%s_id^num < mod1440_%s_date^num }" % (log, log), (
                tmp("gr_v", "mod1440_%s_id^num" % log) + "add_to_temp_variable = { gr_v = %d }\n" % (MARK_ID_BASE[log] + 1)
                + "multiply_temp_variable = { gr_v = -1 }\n"
                + "add_to_array = { array = mod1440_%s_id value = gr_v index = 0 }\n" % log))))
        grow += iff("check_variable = { mod1440_%s_id^num < mod1440_%s_date^num }" % (log, log), marks)
    # 2026-10-22 (E1 review): the number of each line, 0 for the lines a save has; the chronicle too
    for log in ("ev", "tr", "kp"):
        for part in NUMBER_ARRAYS:
            grow += iff("check_variable = { mod1440_%s_%s^num < mod1440_%s_date^num }" % (log, part, log), block(
                "for_loop_effect", "start = 0\nend = %d\nvalue = gr_n\n" % max(LOG_KEEP, MARK_KEEP) + iff(
                    "check_variable = { mod1440_%s_%s^num < mod1440_%s_date^num }" % (log, part, log),
                    "add_to_array = { array = mod1440_%s_%s value = 0 index = 0 }\n" % (log, part))))
    # ... and what the new-line band and the badge's tooltip read: every line written so far counts as seen
    grow += iff("NOT = { check_variable = { mod1440_rec_v = 2 } }", (
        setv("mod1440_rec_v", 2) + setv("mod1440_rec_seen", "mod1440_ln_next") + setv("mod1440_rec_new_war", 0)
        + setv("mod1440_rec_last_n", "THIS") + setv("mod1440_rec_last_k", BLANK) + setv("mod1440_rec_last_d", "global.date")))
    # 2026-10-16: the honours have four occasions, each with its switch (landings and airborne on, a great city
    # off), and count what they wrote by themselves apart from the citations. A record of an earlier build
    # counted both together: that sum stands under "by themselves".
    grow += iff("NOT = { check_variable = { mod1440_hn_v = 1 } } %s" % is_one("mod1440_ev_begun"), (
        setv("mod1440_hn_v", 1) + setv("mod1440_hn_sea", 1) + setv("mod1440_hn_air", 1) + setv("mod1440_hn_vp", 0)
        + setv("mod1440_hn_auto_n", "mod1440_hn_count") + setv("mod1440_hn_cite_n", 0)))
    # first of all: whether the text keys the logs keep still have the numbers they were written with (fix round 1)
    out += block("mod1440_ev_grow", "mod1440_tk_check = yes\n" + grow) + "\n"
    out += "# The Records: which rows of a list are striped: 0, 1, 0, 1 ... for %d rows.\n" % ODD_ROWS
    out += block("mod1440_rec_odd", iff("check_variable = { mod1440_odd^num < %d }" % ODD_ROWS, tmp("odd_v", 0) + block(
        "for_loop_effect", "start = 0\nend = %d\nvalue = odd_n\n" % ODD_ROWS
        + iff("check_variable = { mod1440_odd^num < %d }" % ODD_ROWS, "add_to_array = { mod1440_odd = odd_v }\n")
        + iff("check_variable = { odd_v = 0 }", tmp("odd_v", 1)) + els(tmp("odd_v", 0)))))
    return out


def compare(game, copy, value, new_body, gone_body):
    """Script for the daily comparison of an array of the game with the mod's copy of yesterday: new_body
    runs for each element that is new, gone_body for each that is gone, with the element in the temporary
    variable <value>. The copy is made again afterwards."""
    out = ""
    if new_body:
        out += block("for_each_loop", "array = %s\nvalue = %s\n" % (game, value)
                     + iff("NOT = { is_in_array = { array = %s value = %s } }" % (copy, value), new_body))
    if gone_body:
        out += block("for_each_loop", "array = %s\nvalue = %s\n" % (copy, value)
                     + iff("NOT = { is_in_array = { array = %s value = %s } }" % (game, value), gone_body))
    out += "clear_array = %s\n" % copy
    out += block("for_each_loop", "array = %s\nvalue = %s\nadd_to_array = { %s = %s }\n" % (game, value, copy, value))
    return out


def merged(match, take):
    """Script that goes through the lines of both logs together, newest first, and runs take(log) for each
    line that match(log) holds for (None: every line). Both are functions of the log's name ("ev", "tr") that
    return script; the line's index is in the temporary variable mg_m. A line that stands in both logs is
    taken from the main log."""
    def one(log, pointer):
        test = match(log) if match else None
        inner = iff(test, take(log)) if test else take(log)
        if log == "tr":
            inner = iff("NOT = { check_variable = { mod1440_tr_x^mg_m = 1 } }", inner)
        return tmp("mg_m", pointer) + "subtract_from_temp_variable = { %s = 1 }\n" % pointer + inner

    return (tmp("mg_e", "mod1440_ev_date^num") + "subtract_from_temp_variable = { mg_e = 1 }\n"
            + tmp("mg_t", "mod1440_tr_date^num") + "subtract_from_temp_variable = { mg_t = 1 }\n"
            + tmp("mg_all", "mod1440_ev_date^num") + "add_to_temp_variable = { mg_all = mod1440_tr_date^num }\n"
            + block("for_loop_effect", (
                "start = 0\nend = mg_all\nvalue = mg_i\n" + tmp("mg_log", 0)
                # the newer of the two lines the pointers stand on; on the same day the main log's first
                + iff("check_variable = { mg_e > -1 }", tmp("mg_log", 1) + iff("check_variable = { mg_t > -1 }", (
                    tmp("mg_ed", "mod1440_ev_day^mg_e") + tmp("mg_td", "mod1440_tr_day^mg_t")
                    + iff("check_variable = { mg_td > mg_ed }", tmp("mg_log", 2)))))
                + iff("check_variable = { mg_t > -1 }", tmp("mg_log", 2), "else_if")
                + iff("check_variable = { mg_log = 1 }", one("ev", "mg_e"))
                + iff("check_variable = { mg_log = 2 }", one("tr", "mg_t"), "else_if"))))


# ---------------------------------------------------------------- War Diary (E1)

# The page (e-diary-wars, 2026-10-16; the UX review of E1, 2026-10-22): a card with the list on the left, the
# campaign, the chronicle, the battle honours and what is kept on the right. The list reads like a diary: the day in
# a column on its first line and every line of a day on one band, flags and faces on the lines, names that lead
# somewhere (a country to its lines, an officer to his file), runs of states folded, the lines written while the
# window was closed on the lighter band, and a box at the end of each line that marks it for the chronicle.
WD_W = 1240                     # the card of the list (1172 until the review: the pane gave 68)
WD_ROW = 34
WD_ROW_W = 1198
WD_LIST_X, WD_LIST_Y = 8, 84
# the columns of a row: the day, the family's icon, the words (and a line's number at their right end), what or whom
# it is about on a plate of 260, the country (flag and name, 228), the officer on the spot (face and name, 176), the box
WD_DATE_X, WD_DATE_W = 8, 118
WD_ICON_X, WD_EVENT_X, WD_EVENT_W = 132, 160, 232
WD_A_X, WD_PLATE_W = 398, 260
WD_B_X, WD_B_W = 668, 228
WD_C_X, WD_C_W = 954, 176
WD_MARK_X = 1170
WD_FACE = 0.15                  # a portrait on a line: 23x31 of 156x210
WD_PLATE = layout.head_sprite(WD_PLATE_W, 28)
WD_HIT_B = "GFX_1440p_SG_hit_276x28"        # the country's flag and name: a button with nothing drawn
WD_HIT_A = "GFX_1440p_SG_hit_%dx28" % WD_PLATE_W   # an officer whom the line is about: his face and name
WD_HIT_C = "GFX_1440p_SG_hit_208x28"        # the officer on the spot: his face and name
WD_PANE_X = REC_BODY_X + WD_W + 12
WD_PANE_W = REC_W - WD_PANE_X - 14          # 400
WD_CAMPAIGN_H = 414
WD_CHRON_H = 348
WD_HONOUR_H = 196
WD_KEPT_H = 96
WD_GAP = 12
WD_TROW = 26                    # a row of the pane's tables
WD_PAIR = 188                   # from the first figure of a row to the second
WD_PAIR_W = 172                 # a figure's label and its value, right-aligned
WD_CHRON_LINES = 4              # the newest marked lines the pane shows
WD_CHRON_ROW = 46
WD_CHRON_WORDS = 208             # the words of a marked line: the longest kind measures 202 px in hoi_16mbs
WD_FILTERS = [
    (0, "all", "All", "Everything, newest first. Three or more states of one day, kind and country stand on one row."),
    (1, "war", "War and peace", "Wars declared and ended, capitulations, annexations, subjects, factions, volunteers, ciphers."),
    (2, "land", "Territory", "Every state and every victory point taken, lost or handed over, landings, and the divisions you cited."),
    (3, "gov", "Government", "Parties, elections, heads of government, advisors, a government in exile."),
    (4, "off", "Officers", "Commissions, promotions, skill levels, decorations, officers who left the service or were captured."),
    (5, "air", "Air and sea", "The pride of a fleet. Aces are counted on the Wars page until they can be named."),
    (6, "marked", "Marked", "The lines you marked with the box at their end: the chronicle of your campaign, kept for good."),
]
WD_STATE_FILTER = 7             # the lines of one state, from the state card's Its lines
WD_COUNTRY_FILTER = 8           # the lines of one country, from its name on a line (E1 review)
WD_FOLDING = (0, WD_COUNTRY_FILTER)         # the filters that fold a run of states
# the figures of the campaign: (name, label, kinds counted, tooltip). War and peace and The service, two to a row.
WD_FIGURES = [
    ("wars", "Wars begun", ("war_on", "war_by", "war_with"), "Countries you went to war with since the record began."),
    ("peace", "Wars ended", ("peace",), "Enemies you are no longer at war with."),
    ("cap", "Capitulations", ("capitulated",), "Enemies that capitulated."),
    ("annex", "Annexations", ("annexed",), "Countries you annexed."),
    ("subj", "Subjects made", ("subject_new",), "Countries that became your subjects."),
    ("atwar", "At war today", None, "The enemies you are at war with today (the Wars page)."),
    ("comm", "Commissioned", ("commissioned",), "Generals and admirals who joined your officers."),
    ("prom", "Promotions", ("promoted",), "Generals promoted to field marshal."),
    ("lvl", "Skill levels", ("level",), "Skill levels your officers gained."),
    ("dec", "Decorations", ("decorated",), "Decorations you awarded to officers."),
    ("gone", "Left the service", ("officer_gone",), "Officers who no longer serve: retired, dismissed or fallen."),
    ("govs", "Governments", ("party", "government", "leader"), "Changes of ruling party, of government and of its head."),
]
WD_WAR_ROWS = [("wars", "peace"), ("cap", "annex"), ("subj", "atwar")]
WD_SERVICE_ROWS = [("comm", "prom"), ("lvl", "dec"), ("gone", "govs")]
# ground taken and lost in battle: (name, label, kinds taken, kinds lost); by treaty apart (E1 review)
WD_GROUND = [
    ("st", "States", ("state_taken", "capital_taken"), ("state_lost", "capital_lost")),
    ("vp", "Victory points", ("vp_taken",), ("vp_lost",)),
    ("cap", "Capitals", ("capital_taken",), ("capital_lost",)),
]
WD_TREATY = [("trr", "By treaty: received", ("state_received",), "States that came to you without a battle: an annexation, a peace, a subject's state."),
             ("trh", "handed over", ("state_handed",), "States you handed over without a battle: to a subject, at a peace.")]
WD_BAR = 116
# the honours: (name, variable, words); the first is the switch of before, the others are new
HONOURS = [
    ("cap", "mod1440_hn_auto", "a capital falls"),
    ("sea", "mod1440_hn_sea", "they land from the sea"),
    ("air", "mod1440_hn_air", "they land from the air"),
    ("vp", "mod1440_hn_vp", "a city of %d or more falls" % VP_MAJOR),
]
# what a row of the list needs of a line, and what the list adds: dd 1 on a day's first row (the date shows), fo the
# states folded into the row, nw 1 for a line written since the window was last closed, nu how its number reads (0
# none, 1 as it is, 2 in thousands, 3 in millions), k the mark, src the log the line is in (1 main, 2 territory, 3 the
# chronicle) and si its place there, ap and cp the portraits, st the band of the day
WD_VIEW = ["date", "kind", "fam", "a", "b", "sa", "sb", "c", "sc", "p", "n"]
WD_MORE = ["dd", "fo", "nw", "nu", "k", "src", "si", "ap", "cp", "st",
           "ga", "ua", "gc", "uc"]      # E7: the rows of the lists of faces (the officer or the country) and whether he serves
LOG_SOURCE = {"ev": 1, "tr": 2, "kp": 3}
# the newest marked lines in the pane: what each needs
WD_CHRON = ["date", "kind", "fam", "a", "b", "sa", "sb"]


def checkbox(name, x, y, frame, tooltip=None):
    """The game's gold box at 22 px: frame 1 empty, 2 ticked."""
    tip = ' pdx_tooltip = "%s"' % tooltip if tooltip else ""
    return ('buttonType = { name = "%s" position = { x = %d y = %d } quadTextureSprite = "GFX_checkbox_gold_32" frame = %d '
            'scale = 0.7 clicksound = click_default%s }\n' % (name, x, y, frame, tip))


def fixed(widget):
    """A text box that keeps its size: a name another mod can lengthen ends in dots on its one line (W28)."""
    return widget.replace(" }\n", " fixedsize = yes }\n", 1)


def open_file(officer):
    """Script of a click on an officer's name: the Officers page with his file open, as a click on his row there.
    <officer> holds him by his number or place; 0 (a person who is gone) does nothing."""
    return tmp("wd_o", officer) + iff("NOT = { check_variable = { wd_o = 0 } }", (
        iff(is_one("mod1440_of_has_sel"), block("var:mod1440_of_sel", setv("mod1440_of_picked", 0)))
        + setv("mod1440_of_sel", "wd_o") + setv("mod1440_of_has_sel", 1) + setv("mod1440_of_awarding", 0)
        + block("var:mod1440_of_sel", setv("mod1440_of_picked", 1))
        + setv("mod1440_rec_page", 1) + "mod1440_rec_show = yes\n"))


def war_diary(portrait_version):
    body, effects, properties = head("wd", 0)
    triggers = ""
    kept = ("Main log [?mod1440_ev_date^num|0] of %d lines, territory [?mod1440_tr_date^num|0] of %d." % (LOG_KEEP, LOG_KEEP),
            "The oldest line goes first; a marked line stays.")

    # ---- the card of the list: filters and page arrows, the bar of heads, the list
    inner = ""
    for n, (value, name, label, tip) in enumerate(WD_FILTERS):
        text_icon = "£%s  " % FAMILY_ICON[value] if value in FAMILY_ICON else ""
        # the game's sort button, whose frame 2 has the gold chevrons (a tiled sprite takes no frame: fix round 1)
        inner += M.button("wd_show_%s" % name, 10 + n * 144, 10, "GFX_sort_button_140x29", B.key("wd_show_%s" % name, text_icon + label),
                          tooltip=B.key("wd_show_%s_tt" % name, tip))
        effects += block("wd_show_%s_click" % name, setv("mod1440_wd_filter", value) + "mod1440_wd_first_page = yes\n")
        properties += block("wd_show_%s" % name, "frame = mod1440_wd_frame_%d\n" % value)
    inner += M.button("wd_newer", WD_W - 100, 10, "GFX_1440p_SG_sort_40x29", B.key("wd_newer", "<"),
                      tooltip=B.key("wd_newer_tt", "The newer lines."))
    inner += M.button("wd_older", WD_W - 54, 10, "GFX_1440p_SG_sort_40x29", B.key("wd_older", ">"),
                      tooltip=B.key("wd_older_tt", "The older lines."))
    effects += block("wd_newer_click", iff("check_variable = { mod1440_wd_back^num > 0 }", (
        tmp("wd_b", "mod1440_wd_back^num") + "subtract_from_temp_variable = { wd_b = 1 }\n" + setv("mod1440_wd_from", "mod1440_wd_back^wd_b")
        + "remove_from_array = { array = mod1440_wd_back index = wd_b }\nmod1440_wd_list = yes\n")))
    effects += block("wd_older_click", tmp("wd_next", "mod1440_wd_from") + "add_to_temp_variable = { wd_next = mod1440_wd_shown }\n"
                     + iff("check_variable = { wd_next < mod1440_wd_total } check_variable = { mod1440_wd_shown > 0 }", (
                         "add_to_array = { mod1440_wd_back = mod1440_wd_from }\n" + setv("mod1440_wd_from", "wd_next") + "mod1440_wd_list = yes\n")))
    inner += heads("wd_heads", WD_LIST_X, 48, WD_W - 2 * WD_LIST_X, [
        (WD_DATE_X, WD_DATE_W, "When", "left", None),
        (WD_ICON_X, 250, "What happened", "left", None),
        (WD_A_X, WD_PLATE_W, "Where, or who", "left", "The name of a state or of a victory point is a button: it shows the place on the map. "
                                                       "An officer's name opens his file on the Officers page."),
        (WD_B_X, 260, "Country", "left", "For a state or a victory point: whom it was taken from, lost or handed over to. "
                                         "A country's name is a button: the lines about that country only."),
        (WD_C_X, 160, "Officer", "left", "The general who had the most divisions in the place when it changed hands in battle. "
                                         "His name opens his file.")])
    count_tip = B.key("wd_count_tt", "The lines on this page, of the lines this filter has; a folded row counts its states.\\n" + " ".join(kept))
    inner += M.text("wd_count", WD_W - WD_LIST_X - 10 - 220, 53, 220, B.key("wd_count", "lines [?mod1440_wd_first|0] - [?mod1440_wd_last|0] of [?mod1440_wd_total|0]"),
                    M.FONT_SMALL, "right", 20, tooltip=count_tip)
    # the lines of one state, from its card, and of one country, from its name: the name stands where the Officer head was
    for name, variable in (("state", "mod1440_wd_state"), ("country", "mod1440_wd_country")):
        inner += M.text("wd_count_" + name, WD_W - WD_LIST_X - 10 - 520, 53, 520, B.key(
            "wd_count_" + name, "§Y[?%s.GetName]§!: lines [?mod1440_wd_first|0] - [?mod1440_wd_last|0] of [?mod1440_wd_total|0]" % variable),
            M.FONT_SMALL, "right", 20, tooltip=count_tip)
    state_filter = "check_variable = { mod1440_wd_filter = %d }" % WD_STATE_FILTER
    country_filter = "check_variable = { mod1440_wd_filter = %d }" % WD_COUNTRY_FILTER
    triggers += block("wd_count_visible", M.more_than_zero("mod1440_wd_shown") + "NOT = { %s }\nNOT = { %s }\n" % (state_filter, country_filter))
    triggers += block("wd_count_state_visible", state_filter + "\n") + block("wd_count_country_visible", country_filter + "\n")
    triggers += block("wd_heads_4_visible", "NOT = { %s }\nNOT = { %s }\n" % (state_filter, country_filter))
    triggers += block("wd_heads_3_visible", "NOT = { %s }\n" % country_filter)
    # E7: the officers' faces are two lists of their own in the same scrolling container, over the column of the
    # line's officer (a) and of the officer on the spot (c), one row per line: a line's row holds its officer while he
    # serves (the game draws his face, SGUI-053) and the country otherwise (nothing is drawn). A list row has one scope,
    # and a line's row is the country's; so the faces cannot be in the line's own row. Their icons let clicks through.
    faces = (face_grid("wd_row_gface_grid", WD_A_X + 2, 1, WD_FACE, "full") + face_grid("wd_row_gcface_grid", WD_C_X, 1, WD_FACE, "full"))
    listed = listing("wd_list", "wd_grid", WD_LIST_X, WD_LIST_Y, WD_ROW_W + 30, REC_BODY_H - WD_LIST_Y - 8, WD_ROW)
    inner += listed[:-2] + M.indent(faces) + "}\n"
    inner += M.text("wd_none", 40, WD_LIST_Y + 20, 900, B.key("wd_none", "Nothing of this kind is written down yet."), M.FONT_LABEL)
    triggers += block("wd_none_visible", "check_variable = { mod1440_wd_fam^num < 1 }\n")
    body += M.box("wd_card", REC_BODY_X, REC_BODY_Y, WD_W, REC_BODY_H, inner, M.CARD_BG)

    # ---- a row: one line. The band of its day (or the lighter band of a new line), the date on the day's first row.
    entry = M.icon("wd_row_stripe", 0, 0, STRIPE % (WD_ROW_W, WD_ROW))
    entry += M.icon("wd_row_new", 0, 0, PICK % (WD_ROW_W, WD_ROW))
    triggers += block("wd_row_stripe_visible", "check_variable = { mod1440_wd_st^i = 1 }\ncheck_variable = { mod1440_wd_nw^i = 0 }\n")
    triggers += block("wd_row_new_visible", "check_variable = { mod1440_wd_nw^i = 1 }\n")
    entry += M.text("wd_row_date", WD_DATE_X, 9, WD_DATE_W, B.key("wd_row_date", "[?mod1440_wd_date^i.%s]" % LONG), M.FONT_SMALL, height=20)
    triggers += block("wd_row_date_visible", "check_variable = { mod1440_wd_dd^i = 1 }\n")
    for family, text_icon in sorted(FAMILY_ICON.items()):
        entry += M.text("wd_row_icon_%d" % family, WD_ICON_X, 6, 30, B.key("wd_icon_%d" % family, "£" + text_icon), M.FONT_LABEL, height=24)
        triggers += block("wd_row_icon_%d_visible" % family, "check_variable = { v = %d }\n" % family)
    entry += M.text("wd_row_event", WD_EVENT_X, 8, WD_EVENT_W, B.key("wd_row_event", "[?mod1440_wd_kind^i.GetTokenLocalizedKey]"), M.FONT_LABEL, height=22)
    # the number a line carries, at the right end of its words (part n)
    for suffix, words, unit in (("", "[?mod1440_wd_n^i|0]", 1), ("_k", "[?mod1440_wd_n^i|0] 000", 2), ("_m", "[?mod1440_wd_n^i|0] 000 000", 3)):
        entry += plain("wd_row_n" + suffix, WD_EVENT_X, 6, WD_EVENT_W - 4, B.key("wd_row_n" + suffix, "§Y%s§!" % words), M.FONT_VALUE, "right", 24)
        triggers += block("wd_row_n%s_visible" % suffix, "check_variable = { mod1440_wd_nu^i = %d }\n" % unit)
    # what or whom it is about: a state or a victory point on a plate that moves the camera (a run of states folded:
    # "+N states" at the plate's right end), an officer with his face (a button: his file), another person by name
    fold_tip = B.key("wd_row_go_fold_tt", "Show this place on the map. The Territory filter lists each state of the row.")
    entry += M.button("wd_row_go", WD_A_X, 3, WD_PLATE, tooltip=B.key("wd_row_go_tt", "Show this place on the map"))
    entry += M.button("wd_row_go_fold", WD_A_X, 3, WD_PLATE, tooltip=fold_tip)
    entry += fixed(plain("wd_row_a", WD_A_X + 10, 8, WD_PLATE_W - 20, B.key("wd_row_a", "§Y[?mod1440_wd_a^i.GetName]§!"), height=22))
    entry += fixed(plain("wd_row_point", WD_A_X + 10, 8, WD_PLATE_W - 20, B.key("wd_row_point", "§Y[?mod1440_wd_a^i.GetTokenLocalizedKey]§!"), height=22))
    entry += plain("wd_row_fold", WD_A_X, 9, WD_PLATE_W - 10, B.key("wd_row_fold", "+[?mod1440_wd_fo^i|0] states"), M.FONT_SMALL, "right", 20)
    # the table's portrait, for an officer who no longer serves (E7: the game's face of one who serves is the list
    # wd_row_gface_grid over this spot, and this one is hidden then)
    entry += portrait("wd_row_face", WD_A_X + 2, 1, WD_FACE)
    properties += shown("wd_row_face", "mod1440_wd_ap^i")
    entry += M.button("wd_row_file", WD_A_X, 3, WD_HIT_A, tooltip=B.key("wd_row_file_tt", "Open his file on the Officers page"))
    entry += fixed(plain("wd_row_who", WD_A_X + 34, 8, WD_PLATE_W - 36, B.key("wd_row_who", "§Y[?mod1440_wd_a^i.GetName]§!"), height=22))
    entry += M.text("wd_row_name", WD_A_X + 10, 8, WD_PLATE_W - 10, B.key("wd_row_name", "§Y[?mod1440_wd_a^i.GetName]§!"), M.FONT_LABEL, height=22, fixed=True)
    officer_line = "check_variable = { mod1440_wd_sa^i = 1 }\ncheck_variable = { v = 4 }\n"
    place = "check_variable = { mod1440_wd_sa^i > 1 }\n"
    triggers += block("wd_row_go_visible", place + "check_variable = { mod1440_wd_fo^i = 0 }\n")
    triggers += block("wd_row_go_fold_visible", place + "check_variable = { mod1440_wd_fo^i > 0 }\n")
    triggers += block("wd_row_fold_visible", "check_variable = { mod1440_wd_fo^i > 0 }\n")
    triggers += block("wd_row_a_visible", "check_variable = { mod1440_wd_sa^i = 2 }\n")
    triggers += block("wd_row_point_visible", "check_variable = { mod1440_wd_sa^i = 3 }\n")
    triggers += shown_if(["wd_row_who", "wd_row_file"], officer_line)
    triggers += block("wd_row_face_visible", officer_line + "check_variable = { mod1440_wd_ua^i = 0 }\n")
    triggers += block("wd_row_name_visible", "check_variable = { mod1440_wd_sa^i = 1 }\nNOT = { check_variable = { v = 4 } }\n")
    # the country: in its column, or where the eye looks next for a line about a country alone; its flag and name are
    # a button that shows its lines only (filter 8)
    for suffix, x, test in (("", WD_B_X, "check_variable = { mod1440_wd_sa^i > 0 }\n"), ("_near", WD_A_X, "check_variable = { mod1440_wd_sa^i = 0 }\n")):
        entry += M.icon("wd_row_flag" + suffix, x, 4, FLAG_SMALL)
        properties += flown("wd_row_flag" + suffix, "?mod1440_wd_b^i")
        entry += M.button("wd_row_lines" + suffix, x, 3, WD_HIT_B, tooltip=B.key("wd_row_lines_tt", "Show the lines about this country only"))
        entry += fixed(plain("wd_row_b" + suffix, x + 48, 8, WD_B_W, B.key("wd_row_b", "[?mod1440_wd_b^i.GetName]"), height=22))
        triggers += shown_if(["wd_row_flag" + suffix, "wd_row_lines" + suffix, "wd_row_b" + suffix], "check_variable = { mod1440_wd_sb^i > 0 }\n" + test)
        effects += block("wd_row_lines%s_click" % suffix, setv("mod1440_wd_filter", WD_COUNTRY_FILTER) + setv("mod1440_wd_country", "mod1440_wd_b^i")
                         + "mod1440_wd_first_page = yes\n")
    # the officer on the spot: his face and name, a button that opens his file
    entry += portrait("wd_row_cface", WD_C_X, 1, WD_FACE)
    properties += shown("wd_row_cface", "mod1440_wd_cp^i")
    entry += M.button("wd_row_cfile", WD_C_X, 3, WD_HIT_C, tooltip=B.key("wd_row_file_tt", "Open his file on the Officers page"))
    entry += fixed(plain("wd_row_c", WD_C_X + 32, 8, WD_C_W, B.key("wd_row_c", "§Y[?mod1440_wd_c^i.GetName]§!"), height=22))
    triggers += shown_if(["wd_row_cfile", "wd_row_c"], "check_variable = { mod1440_wd_sc^i = 1 }\n")
    triggers += block("wd_row_cface_visible", "check_variable = { mod1440_wd_sc^i = 1 }\ncheck_variable = { mod1440_wd_uc^i = 0 }\n")
    # E7: the rows of the two lists of faces; a row whose scope is the country (no officer, or one who is no unit leader)
    # reads mod1440_of_ul as 0 and shows nothing
    for name in ("wd_row_gface", "wd_row_gcface"):
        properties += block(name, GAME_FACE)
        triggers += block(name + "_visible", SERVES + "\n")
    effects += block("wd_row_file_click", open_file("mod1440_wd_a^i")) + block("wd_row_cfile_click", open_file("mod1440_wd_c^i"))
    # the mark: an empty box and a ticked one, the same click
    tip = B.key("wd_row_mark_tt", "Mark this line: it goes into the chronicle (the Marked filter) and stays there whatever the age of the log. "
                                  "%d lines at most. Click again to take the mark off." % MARK_KEEP)
    entry += checkbox("wd_row_mark", WD_MARK_X, 6, 1, tip) + checkbox("wd_row_marked", WD_MARK_X, 6, 2, tip)
    triggers += block("wd_row_mark_visible", "check_variable = { mod1440_wd_k^i = 0 }\n")
    triggers += block("wd_row_marked_visible", "check_variable = { mod1440_wd_k^i = 1 }\n")
    for name in ("wd_row_mark", "wd_row_marked"):
        effects += block(name + "_click", tmp("mk_src", "mod1440_wd_src^i") + tmp("mk_si", "mod1440_wd_si^i") + "mod1440_wd_mark = yes\n")
    # the camera goes to the state, or to the state of the victory point
    go = (tmp("wd_go", "mod1440_wd_a^i") + iff("check_variable = { mod1440_wd_sa^i = 3 }", tmp("wd_go", "mod1440_wd_p^i"))
          + block("var:wd_go", block("ROOT", "goto_state = PREV\n" + "mod1440_rec_close = yes\n")))
    effects += block("wd_row_go_click", go) + block("wd_row_go_fold_click", go)

    # ---- the pane (E1 review): banded tables under head bars, two figures to a row
    pw = WD_PANE_W
    sums = ""

    def head_bar(name, y, label, right=()):
        out = M.icon(name + "_bg", 8, y, layout.head_sprite(pw - 16, WD_TROW))
        out += M.text(name, 16, y + 4, 200, B.key(name, label), M.FONT_SMALL, height=20)
        for k, (x, w, words) in enumerate(right):
            out += M.text("%s_%d" % (name, k), x, y + 4, w, B.key("%s_%d" % (name, k), words), M.FONT_SMALL, "right", 20)
        return out

    def band(name, n, y, height=WD_TROW):
        return M.icon(name, 8, y, STRIPE % (pw - 16, height)) if n % 2 else ""

    def figure(name, x, y, label, value, tip):
        tooltip = B.key(name + "_tt", tip) if tip else None
        return (M.text(name + "_l", x, y + 4, WD_PAIR_W, B.key(name + "_l", label), M.FONT_SMALL, height=20, tooltip=tooltip)
                + M.text(name, x, y + 3, WD_PAIR_W, B.key(name, "§Y%s§!" % value), M.FONT_LABEL, "right", 22, tooltip=tooltip))

    def table(prefix, rows, y, stripe_from=0):
        nonlocal sums
        out = ""
        by_name = dict((f[0], f) for f in WD_FIGURES)
        for n, pair in enumerate(rows):
            ry = y + n * WD_TROW
            out += band("%s_band_%d" % (prefix, n), n + stripe_from, ry)
            for k, name in enumerate(pair):
                _, label, kinds, tip = by_name[name]
                out += figure("wd_f_" + name, 16 + k * WD_PAIR, ry, label, "[?mod1440_wd_n_%s|0]" % name, tip)
                sums += (count(*kinds) + setv("mod1440_wd_n_" + name, "ct_sum")) if kinds else setv("mod1440_wd_n_" + name, "mod1440_wr_enemy^num")
        return out, y + len(rows) * WD_TROW

    pane = head_bar("wd_c_war", 44, "War and peace")
    piece, y = table("wd_c_war", WD_WAR_ROWS, 44 + WD_TROW)
    pane += piece
    y += 8
    pane += head_bar("wd_c_ground", y, "Ground, in battle", ((160, 40, "taken"), (330, 54, "lost")))
    y += WD_TROW
    for n, (name, label, taken, lost) in enumerate(WD_GROUND):
        ry = y + n * WD_TROW
        pane += band("wd_g_%s_band" % name, n, ry)
        pane += M.text("wd_g_%s_l" % name, 16, ry + 4, 140, B.key("wd_g_%s_l" % name, label), M.FONT_SMALL, height=20)
        pane += M.text("wd_g_%s_t" % name, 160, ry + 3, 40, B.key("wd_g_%s_t" % name, "§Y[?mod1440_wd_g_%s_t|0]§!" % name), M.FONT_LABEL, "right", 22)
        pane += M.icon("wd_g_%s_bar" % name, 212, ry + 8, M.bar_sprite(WD_BAR))
        pane += M.text("wd_g_%s_x" % name, 330, ry + 3, 54, B.key("wd_g_%s_x" % name, "§Y[?mod1440_wd_g_%s_x|0]§!" % name), M.FONT_LABEL, "right", 22)
        properties += block("wd_g_%s_bar" % name, "frame = mod1440_wd_g_%s_bar\n" % name)
        sums += (count(*taken) + setv("mod1440_wd_g_%s_t" % name, "ct_sum") + count(*lost) + setv("mod1440_wd_g_%s_x" % name, "ct_sum")
                 + tmp("g_all", "mod1440_wd_g_%s_t" % name) + "add_to_temp_variable = { g_all = mod1440_wd_g_%s_x }\n" % name
                 + setv("mod1440_wd_g_%s_bar" % name, 0) + iff("check_variable = { g_all > 0 }", (
                     tmp("g_share", "mod1440_wd_g_%s_t" % name) + "multiply_temp_variable = { g_share = 100 }\n"
                     + "divide_temp_variable = { g_share = g_all }\n" + setv("mod1440_wd_g_%s_bar" % name, "g_share"))))
    y += len(WD_GROUND) * WD_TROW
    for k, (name, label, kinds, tip) in enumerate(WD_TREATY):
        pane += figure("wd_f_" + name, 16 + k * WD_PAIR, y, label, "[?mod1440_wd_n_%s|0]" % name, tip)
        sums += count(*kinds) + setv("mod1440_wd_n_" + name, "ct_sum")
    y += WD_TROW + 8
    pane += head_bar("wd_c_service", y, "The service")
    piece, y = table("wd_c_service", WD_SERVICE_ROWS, y + WD_TROW)
    pane += piece
    body += card("wd_campaign", WD_PANE_X, REC_BODY_Y, pw, WD_CAMPAIGN_H, "The campaign", pane)

    # ---- the chronicle: the newest marked lines (mod1440_wd_ch_*, copied by mod1440_wd_list) and a way to read it all
    cy = REC_BODY_Y + WD_CAMPAIGN_H + WD_GAP
    pane = M.text("wd_ch_n", 16, 44, pw - 32, B.key("wd_ch_n", "The lines you marked, kept for good: [?mod1440_kp_date^num|0] of %d." % MARK_KEEP),
                  M.FONT_SMALL, height=20)
    for k, words in enumerate(("Mark a line with the box at its end; the Marked filter", "reads them as the chapters of your campaign.")):
        pane += M.text("wd_ch_none_%d" % k, 16, 70 + k * 22, pw - 32, B.key("wd_ch_none_%d" % k, words), M.FONT_SMALL, height=20)
        triggers += block("wd_ch_none_%d_visible" % k, "check_variable = { mod1440_wd_ch_n < 1 }\n")
    for k in range(WD_CHRON_LINES):
        ry = 70 + k * WD_CHRON_ROW
        has = "check_variable = { mod1440_wd_ch_n > %d }\n" % k
        if k % 2:
            pane += M.icon("wd_ch_%d_bg" % k, 8, ry, STRIPE % (pw - 16, WD_CHRON_ROW))
            triggers += block("wd_ch_%d_bg_visible" % k, has)
        pane += M.text("wd_ch_%d_d" % k, 16, ry + 3, 300, B.key("wd_ch_%d_d" % k, "§g[?mod1440_wd_ch_date^%d.%s]§!" % (k, LONG)), M.FONT_SMALL, height=20)
        for family, text_icon in sorted(FAMILY_ICON.items()):
            widget = "wd_ch_%d_f%d" % (k, family)
            pane += M.text(widget, 16, ry + 21, 26, B.key("wd_icon_%d" % family, "£" + text_icon), M.FONT_SMALL, height=22)
            triggers += block(widget + "_visible", has + "check_variable = { mod1440_wd_ch_fam^%d = %d }\n" % (k, family))
        pane += M.text("wd_ch_%d" % k, 40, ry + 23, WD_CHRON_WORDS, B.key("wd_ch_%d" % k, "[?mod1440_wd_ch_kind^%d.GetTokenLocalizedKey]" % k),
                       M.FONT_SMALL, height=20, fixed=True)
        # its name: the person or state, a victory point, or the country
        for suffix, words, test in (("s", "[?mod1440_wd_ch_a^%d.GetName]" % k, "OR = { check_variable = { mod1440_wd_ch_sa^%d = 1 } check_variable = { mod1440_wd_ch_sa^%d = 2 } }" % (k, k)),
                                    ("p", "[?mod1440_wd_ch_a^%d.GetTokenLocalizedKey]" % k, "check_variable = { mod1440_wd_ch_sa^%d = 3 }" % k),
                                    ("b", "[?mod1440_wd_ch_b^%d.GetName]" % k, "check_variable = { mod1440_wd_ch_sa^%d = 0 } check_variable = { mod1440_wd_ch_sb^%d = 1 }" % (k, k))):
            widget = "wd_ch_%d_%s" % (k, suffix)
            pane += M.text(widget, 216, ry + 23, 168, B.key(widget, "§Y%s§!" % words), M.FONT_SMALL, "right", 20, fixed=True)
            triggers += block(widget + "_visible", has + test + "\n")
        triggers += block("wd_ch_%d_d_visible" % k, has) + block("wd_ch_%d_visible" % k, has)
    pane += M.button("wd_ch_read", 16, WD_CHRON_H - 41, "GFX_sort_button_202x29", B.key("wd_ch_read", "Read the chronicle"),
                     tooltip=B.key("wd_ch_read_tt", "The Marked filter: every line you marked, newest first."))
    effects += block("wd_ch_read_click", setv("mod1440_wd_filter", 6) + "mod1440_wd_first_page = yes\n")
    body += card("wd_chronicle", WD_PANE_X, cy, pw, WD_CHRON_H, "The chronicle", pane)

    # ---- battle honours: what they are, the four switches in two rows, what they wrote, the last citation
    hy = cy + WD_CHRON_H + WD_GAP
    pane = M.text("wd_hn_1", 16, 42, pw - 32, B.key("wd_hn_1", "A line in your divisions' history (By Blood Alone) when:"), M.FONT_SMALL, height=20)
    for k, (name, variable, words) in enumerate(HONOURS):
        x, ry = 16 + (k % 2) * WD_PAIR, 66 + (k // 2) * 28
        tip = B.key("wd_hn_%s_tt" % name, "Click to switch on or off. A division takes one line a day: the first occasion of the day wins.")
        pane += M.button("wd_hn_%s" % name, x, ry, "GFX_checkbox_gold_32", tooltip=tip).replace("quadTextureSprite", "scale = 0.7 quadTextureSprite")
        pane += M.text("wd_hn_%s_l" % name, x + 28, ry + 2, WD_PAIR - 32, B.key("wd_hn_%s_l" % name, words), M.FONT_SMALL, height=20)
        effects += block("wd_hn_%s_click" % name, flip(variable) + "mod1440_rec_show = yes\n")
        properties += block("wd_hn_%s" % name, "frame = mod1440_hn_f_%s\n" % name)
    ty = 126
    for k, (name, label, variable, tip) in enumerate((
            ("auto", "By themselves", "mod1440_hn_auto_n", "Lines your divisions got by themselves, on the occasions switched on."),
            ("cite", "Cited by you", "mod1440_hn_cite_n", "Lines your divisions got when you cited them from the card of a state."))):
        pane += figure("wd_hn_" + name, 16 + k * WD_PAIR, ty, label, "[?%s|0]" % variable, tip)
    pane += M.text("wd_hn_last", 16, ty + WD_TROW + 6, pw - 32, B.key("wd_hn_last", "Last citation: §Y[?mod1440_hn_last_s.GetName]§!, [?mod1440_hn_last_d.%s]" % LONG),
                   M.FONT_SMALL, height=20)
    pane += M.text("wd_hn_none", 16, ty + WD_TROW + 6, pw - 32, B.key("wd_hn_none", "Select a state you hold to cite the divisions there."), M.FONT_SMALL, height=20)
    triggers += block("wd_hn_last_visible", is_one("mod1440_hn_has_last") + "\n") + block("wd_hn_none_visible", "NOT = { %s }\n" % is_one("mod1440_hn_has_last"))
    body += card("wd_honour", WD_PANE_X, hy, pw, WD_HONOUR_H, "Battle honours", pane)

    # ---- what is kept (the hint of the hotkey went: the top bar button's tooltip and Close say it)
    pane = "".join(M.text("wd_kept_%d" % k, 16, 42 + k * 22, pw - 32, B.key("wd_kept_%d" % k, words), M.FONT_SMALL, height=20)
                   for k, words in enumerate(kept))
    body += card("wd_kept", WD_PANE_X, REC_BODY_Y + REC_BODY_H - WD_KEPT_H, pw, WD_KEPT_H, "Kept", pane)

    gui, script = page_gui("wd", 0, body, dirty="mod1440_rec_dirty",
                           lists=block("wd_grid", 'array = mod1440_wd_fam\nentry_container = "mod1440_records_diary_row"\n')
                           + face_list("wd_row_gface_grid", "mod1440_wd_ga", "wd_row_gface") + face_list("wd_row_gcface_grid", "mod1440_wd_gc", "wd_row_gcface"),
                           effects=effects, triggers=triggers, properties=properties)
    gui += row("mod1440_records_diary_row", WD_ROW_W, WD_ROW, entry)
    # E7: a row of a list of faces is as high as a line, the face at its top
    for name in ("wd_row_gface", "wd_row_gcface"):
        w, h = face_size(WD_FACE)
        gui += row("mod1440_records_%s_row" % name, w, WD_ROW, through(name, 0, 0, UNKNOWN, WD_FACE))

    # ---- script: the page of the list
    unknown = "token:" + UNKNOWN

    def face(source, target, game, served):
        """The officer in <source>: while he is a unit leader (asked here, kept as mod1440_of_ul), the row of the game's
        face holds him (<game>, <served> 1) and the table is not asked (E7); otherwise his table portrait into the
        temporary variable <target>, looked up once."""
        return (tmp(target, unknown) + tmp("wd_ch", source) + tmp("wd_sv", 0) + block("var:wd_ch", (
            UL_MARK + iff(SERVES, tmp("wd_sv", 1))
            + els(officer_table(portrait_version) + tmp(target, "mod1440_p"))))
            + iff("check_variable = { wd_sv = 1 }", tmp(game, "wd_ch") + tmp(served, 1)))

    folded = "OR = { %s }" % " ".join("check_variable = { %%s = wd_f%d }" % k for k in range(len(FOLDED_KINDS)))

    def take(log, index):
        """A line the filter wants: counted, and copied to the page when it is one of those on show. A day's first row
        shows the date and turns the band; a line of a run of states of one day, kind and country (in All and a
        country's lines) adds to the run's row from the third line on."""
        part = lambda name: "mod1440_%s_%s^%s" % (log, name, index)
        last = "mod1440_wd_fam^num"
        remove_last = (tmp("wd_r", last) + "subtract_from_temp_variable = { wd_r = 1 }\n"
                       + "".join("remove_from_array = { array = mod1440_wd_%s index = wd_r }\n" % name for name in WD_VIEW + WD_MORE))
        line_row = (
            "".join("add_to_array = { mod1440_wd_%s = %s }\n" % (name, part(name)) for name in ("date", "kind", "fam", "a", "sa", "sb", "c", "sc", "p", "n"))
            + iff("check_variable = { %s > 0 }" % part("sb"), "add_to_array = { mod1440_wd_b = %s }\n" % part("b")) + els("add_to_array = { mod1440_wd_b = THIS }\n")
            # the day: its first row shows the date, and every row of a day stands on the same band
            + tmp("wd_d", part("day")) + tmp("wd_dd", 0)
            + iff("NOT = { check_variable = { wd_d = wd_day } }", tmp("wd_dd", 1) + tmp("wd_day", "wd_d")
                  + iff("check_variable = { wd_par = 0 }", tmp("wd_par", 1)) + els(tmp("wd_par", 0)))
            + "add_to_array = { mod1440_wd_dd = wd_dd }\nadd_to_array = { mod1440_wd_st = wd_par }\nadd_to_array = { mod1440_wd_fo = 0 }\n"
            # a line written since the window was last closed
            + tmp("wd_nw", 0) + iff("check_variable = { %s > mod1440_rec_seen }" % part("id"), tmp("wd_nw", 1)) + "add_to_array = { mod1440_wd_nw = wd_nw }\n"
            # how its number reads: a casualty step in thousands, or in millions from 1000 on
            + tmp("wd_nu", 0) + iff("check_variable = { %s > 0 }" % part("n"), tmp("wd_nu", 1) + iff("check_variable = { %s = wd_cas }" % part("kind"), (
                tmp("wd_nu", 2) + iff("check_variable = { %s > 999 }" % part("n"), tmp("wd_nu", 3) + tmp("wd_nv", part("n"))
                                      + "divide_temp_variable = { wd_nv = 1000 }\n" + setv("mod1440_wd_n^%s" % "wd_nl", "wd_nv")))))
            + "add_to_array = { mod1440_wd_nu = wd_nu }\n"
            + "add_to_array = { mod1440_wd_k = %s }\nadd_to_array = { mod1440_wd_src = %d }\nadd_to_array = { mod1440_wd_si = %s }\n" % (part("k"), LOG_SOURCE[log], index)
            + tmp("wd_ga", "THIS") + tmp("wd_ua", 0) + tmp("wd_gc", "THIS") + tmp("wd_uc", 0)
            + tmp("wd_ap", unknown) + iff("check_variable = { %s = 1 } check_variable = { %s = 4 }" % (part("sa"), part("fam")), face(part("a"), "wd_ap", "wd_ga", "wd_ua"))
            + tmp("wd_cp", unknown) + iff("check_variable = { %s = 1 }" % part("sc"), face(part("c"), "wd_cp", "wd_gc", "wd_uc"))
            + "add_to_array = { mod1440_wd_ap = wd_ap }\nadd_to_array = { mod1440_wd_cp = wd_cp }\n"
            + "".join("add_to_array = { mod1440_wd_%s = wd_%s }\n" % (n, n) for n in ("ga", "ua", "gc", "uc"))
            + "add_to_temp_variable = { wd_shown = 1 }\n")
        # the place of the row just added, for the casualty number in millions (above) and the start of a run (below)
        line_row = tmp("wd_nl", last) + line_row
        same_run = ("check_variable = { wd_fold = 1 } check_variable = { wd_rn > 0 } check_variable = { %s = 2 } check_variable = { %s = wd_rk } "
                    "check_variable = { %s = wd_rb } check_variable = { %s = wd_rd } check_variable = { wd_rs = wd_prev }"
                    % (part("sa"), part("kind"), part("b"), part("day")))
        foldable = "check_variable = { wd_fold = 1 } check_variable = { %s = 2 } %s" % (part("sa"), folded % ((part("kind"),) * len(FOLDED_KINDS)))
        start_run = (tmp("wd_rn", 1) + tmp("wd_rk", part("kind")) + tmp("wd_rb", part("b")) + tmp("wd_rd", part("day")) + tmp("wd_rs", "wd_seen")
                     + tmp("wd_rr", "wd_nl"))
        fold = ("add_to_temp_variable = { wd_rn = 1 }\n" + tmp("wd_rs", "wd_seen") + "add_to_temp_variable = { wd_shown = 1 }\n"
                # the third line: the second line's row goes, and the first row says two more states; then one more each
                + iff("check_variable = { wd_rn = %d }" % FOLD_MIN, remove_last + setv("mod1440_wd_fo^wd_rr", FOLD_MIN - 1) + setv("mod1440_wd_sc^wd_rr", 0)
                      # E7: and so does his face: the row of the list of faces takes the country
                      + setv("mod1440_wd_gc^wd_rr", "THIS") + setv("mod1440_wd_uc^wd_rr", 0))
                + els("add_to_variable = { mod1440_wd_fo^wd_rr = 1 }\n"))
        return ("add_to_temp_variable = { wd_seen = 1 }\n" + tmp("wd_prev", "wd_seen") + "subtract_from_temp_variable = { wd_prev = 1 }\n"
                + iff("check_variable = { wd_seen > mod1440_wd_from }", (
                    iff("%s check_variable = { wd_rn > %d }" % (same_run, FOLD_MIN - 2), fold)
                    + iff("check_variable = { %s < %d }" % (last, VIEW_ROWS), (
                        line_row
                        + iff(same_run, "add_to_temp_variable = { wd_rn = 1 }\n" + tmp("wd_rs", "wd_seen"))
                        + iff(foldable, start_run, "else_if") + els(tmp("wd_rn", 0))), "else_if")
                    + els(tmp("wd_rn", 0)))))

    def one_log(log, by_family):
        keep = take(log, "wd_m")
        if by_family:
            keep = iff("check_variable = { mod1440_%s_fam^wd_m = mod1440_wd_filter }" % log, keep)
        return block("for_loop_effect", (
            "start = 0\nend = mod1440_%s_date^num\nvalue = wd_n\n" % log
            + tmp("wd_m", "mod1440_%s_date^num" % log) + "subtract_from_temp_variable = { wd_m = 1 }\nsubtract_from_temp_variable = { wd_m = wd_n }\n"
            + keep))

    def of_state(log):
        return ("OR = { AND = { check_variable = { mod1440_%s_sa^mg_m = 2 } check_variable = { mod1440_%s_a^mg_m = mod1440_wd_state } } "
                "AND = { check_variable = { mod1440_%s_sa^mg_m = 3 } check_variable = { mod1440_%s_p^mg_m = mod1440_wd_state } } }" % (log, log, log, log))

    def of_country(log):
        return "check_variable = { mod1440_%s_sb^mg_m = 1 } check_variable = { mod1440_%s_b^mg_m = mod1440_wd_country }" % (log, log)

    # the newest marked lines for the pane: the chronicle is kept in the order of the days, so from its end
    chronicle = ("".join("clear_array = mod1440_wd_ch_%s\n" % part for part in WD_CHRON) + tmp("wd_c", "mod1440_kp_date^num")
                 + block("for_loop_effect", "start = 0\nend = %d\nvalue = wd_ck\n" % WD_CHRON_LINES + (
                     "subtract_from_temp_variable = { wd_c = 1 }\n" + iff("check_variable = { wd_c > -1 }", "".join(
                         "add_to_array = { mod1440_wd_ch_%s = mod1440_kp_%s^wd_c }\n" % (part, part) for part in WD_CHRON))))
                 + setv("mod1440_wd_ch_n", "mod1440_wd_ch_date^num")
                 + pad([("mod1440_wd_ch_date", 0), ("mod1440_wd_ch_kind", BLANK), ("mod1440_wd_ch_fam", 0), ("mod1440_wd_ch_a", 0),
                        ("mod1440_wd_ch_b", "THIS"), ("mod1440_wd_ch_sa", 0), ("mod1440_wd_ch_sb", 0)], WD_CHRON_LINES))

    frames = "".join(setv("mod1440_wd_frame_%d" % v, 1) for v, _, _, _ in WD_FILTERS)
    frames += "".join(iff("check_variable = { mod1440_wd_filter = %d }" % v, setv("mod1440_wd_frame_%d" % v, 2)) for v, _, _, _ in WD_FILTERS)
    kinds = "".join(tmp("wd_f%d" % k, "token:mod1440_ev_" + name) for k, name in enumerate(FOLDED_KINDS)) + tmp("wd_cas", "token:mod1440_ev_casualties")
    folding = tmp("wd_fold", 0) + "".join(iff("check_variable = { mod1440_wd_filter = %d }" % v, tmp("wd_fold", 1)) for v in WD_FOLDING)
    script_effects = (
        "# War Diary: copies the lines the chosen filter wants, newest first, from the chosen place on, into the arrays\n"
        "# the page draws, %d rows at most: the day on a day's first row, the band of the day, the new lines, a run of\n"
        "# states folded in All and in a country's lines. All and the lines of one state or country go through both logs\n"
        "# together; Territory has a log of its own; Marked reads the chronicle; every other filter reads the main log.\n"
        "# Then the figures of the campaign (sums of the counters) and the newest marked lines.\n" % VIEW_ROWS
        + block("mod1440_wd_list", (
            "mod1440_ev_grow = yes\n" + "".join("clear_array = mod1440_wd_%s\n" % part for part in WD_VIEW + WD_MORE)
            + tmp("wd_seen", 0) + tmp("wd_shown", 0) + tmp("wd_day", -1) + tmp("wd_par", 0) + tmp("wd_rn", 0) + kinds + folding
            + iff("check_variable = { mod1440_wd_filter = 0 }", merged(None, lambda log: take(log, "mg_m")))
            + iff("check_variable = { mod1440_wd_filter = 2 }", one_log("tr", False), "else_if")
            + iff("check_variable = { mod1440_wd_filter = 6 }", one_log("kp", False), "else_if")
            + iff("check_variable = { mod1440_wd_filter = %d }" % WD_STATE_FILTER, merged(of_state, lambda log: take(log, "mg_m")), "else_if")
            + iff("check_variable = { mod1440_wd_filter = %d }" % WD_COUNTRY_FILTER, merged(of_country, lambda log: take(log, "mg_m")), "else_if")
            + els(one_log("ev", True))
            + setv("mod1440_wd_total", "wd_seen") + setv("mod1440_wd_shown", "wd_shown")
            + setv("mod1440_wd_first", "mod1440_wd_from") + "add_to_variable = { mod1440_wd_first = 1 }\n"
            + setv("mod1440_wd_last", "mod1440_wd_from") + "add_to_variable = { mod1440_wd_last = wd_shown }\n"
            + frames + pad([("mod1440_ct", 0)], len(KINDS) + 8) + sums + chronicle
            + "add_to_variable = { mod1440_rec_dirty = 1 }\n"))
        + "\n# War Diary: the first page of the chosen filter.\n"
        + block("mod1440_wd_first_page", "clear_array = mod1440_wd_back\n" + setv("mod1440_wd_from", 0) + "mod1440_wd_list = yes\n")
        + "\n# War Diary: the box at the end of a line. mk_src says which log the row was copied from (1 main, 2 territory,\n"
        "# 3 the chronicle), mk_si where in it. A line that is not marked is marked in both logs and copied into the\n"
        "# chronicle, by its day; a marked one loses its mark and leaves the chronicle. Only the mod's own variables.\n"
        + block("mod1440_wd_mark", mark_script())
    )
    return gui, script, script_effects


def mark_script():
    """The script of mod1440_wd_mark (see war_diary())."""
    out = tmp("mk_id", 0) + tmp("mk_on", 0) + tmp("mk_ok", 0)
    for log, n in (("ev", 1), ("tr", 2), ("kp", 3)):
        out += iff("check_variable = { mk_src = %d } check_variable = { mk_si < mod1440_%s_id^num }" % (n, log), (
            tmp("mk_id", "mod1440_%s_id^mk_si" % log) + tmp("mk_on", "mod1440_%s_k^mk_si" % log) + tmp("mk_ok", 1)))

    def set_marks(value):
        return "".join(block("for_each_loop", "array = mod1440_%s_id\nvalue = mk_v\nindex = mk_j\n" % log
                             + iff("check_variable = { mk_v = mk_id }", setv("mod1440_%s_k^mk_j" % log, value))) for log in ("ev", "tr"))

    unmark = (set_marks(0) + tmp("mk_at", -1)
              + block("for_each_loop", "array = mod1440_kp_id\nvalue = mk_v\nindex = mk_j\n" + iff("check_variable = { mk_v = mk_id }", tmp("mk_at", "mk_j")))
              + iff("check_variable = { mk_at > -1 }", "".join("remove_from_array = { array = mod1440_kp_%s index = mk_at }\n" % part for part in LOG_ARRAYS)))
    # the chronicle stands in the order of the days: the line goes in before the first line of a later day
    def value(log, part):
        return "1" if part == "k" else "mod1440_%s_%s^mk_si" % (log, part)

    copy = ""
    for log, n in (("ev", 1), ("tr", 2)):
        copy += iff("check_variable = { mk_src = %d }" % n, (
            tmp("mk_day", "mod1440_%s_day^mk_si" % log) + tmp("mk_at", "mod1440_kp_day^num") + tmp("mk_brk", 0)
            + block("for_each_loop", "array = mod1440_kp_day\nvalue = mk_v\nindex = mk_j\nbreak = mk_brk\n"
                    + iff("check_variable = { mk_v > mk_day }", tmp("mk_at", "mk_j") + tmp("mk_brk", 1)))
            + iff("check_variable = { mk_brk = 1 }", "".join("add_to_array = { array = mod1440_kp_%s value = %s index = mk_at }\n" % (part, value(log, part))
                                                             for part in LOG_ARRAYS))
            + els("".join("add_to_array = { mod1440_kp_%s = %s }\n" % (part, value(log, part)) for part in LOG_ARRAYS))))
    mark = iff("check_variable = { mod1440_kp_date^num < %d } check_variable = { mk_src < 3 }" % MARK_KEEP, set_marks(1) + copy)
    return out + iff("check_variable = { mk_ok = 1 }", iff("check_variable = { mk_on = 1 }", unmark) + els(mark) + "mod1440_wd_list = yes\n")


# ---------------------------------------------------------------- Officers (E2)

# The redesign of 2026-10-16 (e-officers-gov): a table of 22 rows with the rank and status under the name, the
# game's stat icons as heads and each officer's traits as the game's icons; beside it his file as five cards
# (who he is, traits, service record, decorations, War Diary). Award is a mode of the decorations card.
# A column is (name, value of the officer, width, head text or None, head icon or None, what the tooltip says).
# An admiral has no planning and logistics: his third and fourth levels are manoeuvring and coordination, and
# his command is ships.
OF_COLUMNS = [
    ("skill", "skill_level", 56, "Skill", None, "Skill level."),
    ("atk", "attack_level", 44, None, "GFX_trait_attack", "Attack."),
    ("def", "defense_level", 44, None, "GFX_trait_defense", "Defence."),
    ("c3", "planning_level", 44, None, "GFX_trait_planning", "Planning; for an admiral manoeuvring."),
    ("c4", "logistics_level", 44, None, "GFX_trait_logistics", "Logistics; for an admiral coordination."),
    ("traits", "num_traits", 168, "Traits", None, "His traits, as the game's icons: who he is first, the skills he learnt last."),
    ("cmd", "num_units", 60, "Cmd", None, "Divisions under his command today; for an admiral ships."),
    ("won", "mod1440_of_won", 50, "Won", None, "Battles won since the record began."),
    ("lost", "mod1440_of_lost", 50, "Lost", None, "Battles lost since the record began."),
    ("dec", "mod1440_of_dec^num", 88, "Medals", None, "Decorations you have awarded."),
]
OF_NAVY = {"c3": "maneuvering_level", "c4": "coordination_level", "cmd": "num_ships"}
OF_NAVY_ICON = {"c3": "GFX_trait_maneuvering", "c4": "GFX_trait_coordination"}
OF_NUMBERS = ("skill", "atk", "def", "c3", "c4", "cmd", "won", "lost")      # the columns that show a number
OF_FACE_W, OF_FACE = 40, 0.22               # the column of the portrait in a row, and how small it is drawn (34x46)
OF_NAME = 260                               # the name and under it the rank and status
OF_ROW_W = OF_FACE_W + OF_NAME + sum(c[2] for c in OF_COLUMNS)
OF_ROW = 48
OF_HIT = "GFX_1440p_SG_hit_300x48"          # the row's button: the portrait and the name, with nothing drawn
OF_FILTER_Y = REC_BODY_Y                    # the filters stand inside the page's body (the frame's contract)
OF_HEAD_Y = REC_BODY_Y + 38
OF_LIST_Y = OF_HEAD_Y + 32
OF_LIST_H = REC_BODY_Y + REC_BODY_H - OF_LIST_Y
OF_FILTERS = [
    (0, "all", "All", "Every officer serving today."),
    (1, "army", "Army", "Generals and field marshals."),
    (2, "navy", "Navy", "Admirals."),
    (3, "cmd", "With a command", "Officers who lead troops or ships today."),
    (4, "dec", "Decorated", "Officers you have decorated."),
    (5, "former", "Former", "Officers the record knows who serve no longer."),
]
OF_CARD_X = REC_BODY_X + OF_ROW_W + 30 + 12
OF_CARD_W = REC_BODY_X + REC_BODY_W - OF_CARD_X
OF_CARD_Y = REC_BODY_Y
OF_SIDE = 14 + 156 + 16                     # where the text beside the portrait of a file begins
OF_CARD_GAP = 12
# the five cards of the file, top to bottom: (name, height); the diary takes the rest
OF_CARDS = [("head", 240), ("traits", 108), ("rec", 184), ("dec", 220)]
CARD_SPRITE = "GFX_1440p_SG_card_%dx%d"
TRAIT_ICONS = 6         # trait icons in a row, and traits named in a file
TRAIT_STEP = 24         # from one trait icon of a row to the next (an icon is 23x33)
TRAIT_SAMPLE = ["GFX_trait_old_guard", "GFX_trait_brilliant_strategist", "GFX_trait_trait_cautious",
                "GFX_trait_infantry_officer", "GFX_trait_war_hero", "GFX_trait_career_officer"]     # what the renderer draws
TRAIT_PAD = "token:unknown"                 # GFX_trait_unknown, the game's own picture of a trait it cannot show
ROW_MEDALS = 3          # medals at half size in a row
MEDAL_SLOTS = 12        # decorations a country can award at most (Chile has twelve medals)
RACK = 9                # medals at full size on the rack of a file
CARD_LINES = 11         # diary lines a file shows
DEC_LINES = 3           # decorations the file lists by name
DEC_ARRAYS = ["dec", "dec_key", "dec_date", "dec_set", "dec_frame"]     # an officer's decorations, on the officer
SHIP_KINDS = [("k1", "carrier", "Carriers"), ("k2", "capital", "Capital ships"), ("k3", "screen", "Screens"),
              ("k4", "submarine", "Submarines")]
OF_FIGURES = [
    ("won", "Battles won", "[?mod1440_of_c_won|0]", "Counted since the record began."),
    ("lost", "Battles lost", "[?mod1440_of_c_lost|0]", "Counted since the record began."),
    ("states", "States taken", "[?mod1440_of_c_states|0]", "States you took while he had the most divisions in them."),
    ("vps", "Points taken", "[?mod1440_of_c_vps|0]", "Victory points you took from an enemy while he had the most divisions in their state."),
    ("vpl", "Points lost", "[?mod1440_of_c_vpl|0]", "Victory points an enemy took while he had the most divisions in their state."),
    ("decs", "Decorations", "[?mod1440_of_c_dec_n|0]", "Decorations you have awarded him."),
]
# the status of an officer, by what the game says of him: (name, the words in a row, a trigger in his scope)
FORMER = "check_variable = { mod1440_of_seen_day < global.num_days }"


def through(name, x, y, sprite, scale=None):
    """An icon that lets a click through to the button under it."""
    size = " scale = %s" % scale if scale else ""
    return 'iconType = { name = "%s" position = { x = %d y = %d } spriteType = "%s"%s alwaystransparent = yes }\n' % (name, x, y, sprite, size)


def trait_table():
    """The traits script asks an officer about: the game's (tools/traits_table.py) and those the launcher's
    playset adds (traits_mods_table.py, when it has been made). Rows (trait, army/navy/both, sprite)."""
    from traits_table import TRAITS
    try:
        from traits_mods_table import TRAITS as others
    except ImportError:
        others = []
    own = set(row[0] for row in TRAITS)
    plain_name = re.compile(r"^[A-Za-z0-9_]+$")
    return [row for row in TRAITS + [row for row in others if row[0] not in own] if plain_name.match(row[0])]


def trait_cache():
    """The script that keeps an officer's traits on him (mod1440_of_traits), and the version of the table.

    mod1440_of_tr     the traits the table names, as text keys: those with an icon first; padded to six
    mod1440_of_tr_i   how many of them have an icon, mod1440_of_tr_k how many the table named
    mod1440_of_tr_n   num_traits when the array was made: the daily round makes it again when that changes
    mod1440_of_tr_plus  traits beyond the icons a row shows (more than six, no icon, or another mod's)"""
    rows = trait_table()
    version = table_version(rows)

    def tests(kind, with_icon):
        """The tests for one kind of officer, in groups of 16: a group runs while traits are still missing."""
        chosen = [name for name, who, sprite in rows if who in (kind, "both") and bool(sprite) == with_icon]
        out = ""
        for start in range(0, len(chosen), 16):
            body = "".join(iff("has_trait = %s" % name, "add_to_array = { mod1440_of_tr = token:%s }\n" % name) for name in chosen[start:start + 16])
            out += iff("check_variable = { mod1440_of_tr^num < num_traits }", body)
        return out

    body = ("clear_array = mod1440_of_tr\n"
            + iff("is_navy_leader = yes", tests("navy", True)) + els(tests("army", True))
            + setv("mod1440_of_tr_i", "mod1440_of_tr^num")
            + iff("is_navy_leader = yes", tests("navy", False)) + els(tests("army", False))
            + setv("mod1440_of_tr_k", "mod1440_of_tr^num") + setv("mod1440_of_tr_n", "num_traits") + stamped("mod1440_of_tr_v", version)
            # the row shows six icons at most, and +N for every other trait
            + tmp("tr_shown", "mod1440_of_tr_i") + "clamp_temp_variable = { var = tr_shown max = %d }\n" % TRAIT_ICONS
            + setv("mod1440_of_tr_plus", "num_traits") + "subtract_from_variable = { mod1440_of_tr_plus = tr_shown }\n"
            + "clamp_variable = { var = mod1440_of_tr_plus min = 0 }\n"
            + pad([("mod1440_of_tr", TRAIT_PAD)], TRAIT_ICONS))
    army = sum(1 for row in rows if row[1] in ("army", "both"))
    navy = sum(1 for row in rows if row[1] in ("navy", "both"))
    text = ("# Officers: the traits of the officer in scope, kept on him (tools/traits_table.py and traits_mods_table.py:\n"
            "# %d traits; a general is asked about %d, an admiral about %d). Run when num_traits has changed.\n" % (len(rows), army, navy)
            + block("mod1440_of_traits", body))
    return text, version


def medal_tokens(sets, source, target, count, index="md_v"):
    """Script that adds to <target> the strip token of each set number in the array <source> (the decorations
    keep the set as a number: tools/unit_medals_table.py), <count> at most."""
    pick = "".join(iff("check_variable = { %s = %d }" % (index, s), tmp("md_strip", "token:" + MEDAL_STRIP % name), "if" if s == 0 else "else_if")
                   for s, name in enumerate(sets))
    return block("for_each_loop", "array = %s\nvalue = %s\nindex = md_ix\n" % (source, index) + iff(
        "check_variable = { md_ix < %d }" % count, tmp("md_strip", "token:" + MEDAL_STRIP % sets[0]) + pick
        + "add_to_array = { %s = md_strip }\n" % target))


def subject(prefix, k, x, y, width, has):
    """The state or the victory point a line of a file is about: one text for each, script shows which.
    Returns the widgets and their triggers."""
    out = M.text("%s_%d_s" % (prefix, k), x, y, width, B.key("%s_%d_s" % (prefix, k), "§Y[?mod1440_%s_a^%d.GetName]§!" % (prefix, k)), M.FONT_SMALL, height=22)
    out += M.text("%s_%d_p" % (prefix, k), x, y, width, B.key("%s_%d_p" % (prefix, k), "§Y[?mod1440_%s_a^%d.GetTokenLocalizedKey]§!" % (prefix, k)),
                  M.FONT_SMALL, height=22)
    more = has + "check_variable = { mod1440_%s_date^num > %d }\n" % (prefix, k)
    return out, (block("%s_%d_s_visible" % (prefix, k), more + "check_variable = { mod1440_%s_sa^%d = 2 }\n" % (prefix, k))
                 + block("%s_%d_p_visible" % (prefix, k), more + "check_variable = { mod1440_%s_sa^%d = 3 }\n" % (prefix, k)))


def officer_status():
    """The words under an officer's name in a row: (widget suffix, words, trigger in his scope). One is true."""
    ranks = [("fm", "Field Marshal", "is_field_marshal = yes"), ("gen", "General", "is_corps_commander = yes"),
             ("adm", "Admiral", "is_navy_leader = yes")]
    out = []
    for rank, word, trigger in ranks:
        if rank == "adm":
            states = [("off", "§Rno longer serving§!", FORMER),
                      ("cmd", "commands [?num_ships|0] ships", "NOT = { %s } check_variable = { num_ships > 0 }" % FORMER),
                      ("idle", "unassigned", "NOT = { %s } NOT = { check_variable = { num_ships > 0 } }" % FORMER)]
        else:
            free = "NOT = { %s } NOT = { is_general_captured = yes }" % FORMER
            states = [("off", "§Rno longer serving§!", FORMER),
                      ("cap", "§Rcaptured§!", "NOT = { %s } is_general_captured = yes" % FORMER),
                      ("grp", "leads an army group", free + " is_leading_army_group = yes"),
                      ("cmd", "commands [?num_units|0] divisions", free + " NOT = { is_leading_army_group = yes } check_variable = { num_units > 0 }"),
                      ("idle", "unassigned", free + " NOT = { is_leading_army_group = yes } NOT = { check_variable = { num_units > 0 } }")]
        for state, words, condition in states:
            out.append(("%s_%s" % (rank, state), "§g%s · %s§!" % (word, words), "%s %s" % (trigger, condition)))
    return out


def officers(portrait_version):
    from unit_medals_table import MEDALS
    sets = sorted(set(m[1] for m in MEDALS))
    trait_script, trait_version = trait_cache()
    body, effects, properties = head("of", 1, "Every general and admiral, with what the mod has written down about him. Click one for his record.")
    triggers = ""
    row_triggers = ""
    for n, (value, name, label, tip) in enumerate(OF_FILTERS):
        body += M.button("of_show_%s" % name, REC_BODY_X + 2 + n * 146, OF_FILTER_Y, "GFX_sort_button_140x29", B.key("of_show_%s" % name, label),
                         tooltip=B.key("of_show_%s_tt" % name, tip))
        effects += block("of_show_%s_click" % name, setv("mod1440_of_show", value) + "mod1440_of_list = yes\n")
        properties += block("of_show_%s" % name, "frame = mod1440_of_frame_%d\n" % value)
    body += M.text("of_count", REC_BODY_X + 2 + 6 * 146 + 8, OF_FILTER_Y + 4, 100, B.key("of_count", "[?mod1440_of_rows^num|0] listed"), M.FONT_SMALL)

    # ---- column heads: a click sorts, a second click turns the order. A level has the game's icon on its plate.
    x = REC_BODY_X + OF_FACE_W
    body += M.button("of_sort_name", x, OF_HEAD_Y, layout.head_sprite(OF_NAME), B.key("of_sort_name", "Officer"),
                     tooltip=B.key("of_sort_name_tt", "Back to the order of the game."))
    effects += block("of_sort_name_click", setv("mod1440_of_sort_by", 0) + "mod1440_of_list = yes\n")
    x += OF_NAME
    middle = (OF_ROW - 30) // 2 + 4         # the line of a number in the middle of the row
    entry = M.icon("of_row_stripe", 0, 0, STRIPE % (OF_ROW_W, OF_ROW))
    entry += M.icon("of_row_pick", 0, 0, PICK % (OF_ROW_W, OF_ROW))
    # E7: the row's scope is the officer: while he is a unit leader (mod1440_of_ul, UL_MARK) the game draws his face; one
    # who has left the service shows the table's portrait (a character without a unit leader role would draw the unknown man)
    entry += portrait("of_row_face", 3, 1, OF_FACE)
    properties += block("of_row_face", GAME_FACE)
    entry += portrait("of_row_face_table", 3, 1, OF_FACE)
    properties += shown("of_row_face_table", "mod1440_p")
    row_triggers += block("of_row_face_visible", SERVES + "\n") + block("of_row_face_table_visible", "NOT = { %s }\n" % SERVES)
    # the whole of the portrait and the name is the button, and nothing of it is drawn
    entry += M.button("of_row", 0, 0, OF_HIT, tooltip=B.key("of_row_tt", "Show this officer's record"))
    entry += plain("of_row_name", OF_FACE_W + 6, 4, OF_NAME - 10, B.key("of_row_name", "[THIS.GetName]"), height=22)
    entry += plain("of_row_name_sel", OF_FACE_W + 6, 4, OF_NAME - 10, B.key("of_row_name_sel", "§Y[THIS.GetName]§!"), height=22)
    row_triggers += block("of_row_stripe_visible", is_one("mod1440_of_odd") + "\n") + block("of_row_pick_visible", is_one("mod1440_of_picked") + "\n")
    row_triggers += block("of_row_name_visible", "NOT = { %s }\n" % is_one("mod1440_of_picked")) + block("of_row_name_sel_visible", is_one("mod1440_of_picked") + "\n")
    for suffix, words, condition in officer_status():
        widget = "of_row_st_" + suffix
        entry += plain(widget, OF_FACE_W + 6, 26, OF_NAME - 10, B.key(widget, words), M.FONT_SMALL, height=20)
        row_triggers += block(widget + "_visible", condition + "\n")
    keys = ""
    rx = OF_FACE_W + OF_NAME
    for number, (name, value, width, label, picture, tip) in enumerate(OF_COLUMNS, start=1):
        tooltip = B.key("of_sort_%s_tt" % name, tip + "\\nClick to sort, click again to turn the order.")
        if label:
            body += M.button("of_sort_%s" % name, x, OF_HEAD_Y, layout.head_sprite(width), B.key("of_sort_%s" % name, label), tooltip=tooltip)
        else:
            body += M.button("of_sort_%s" % name, x, OF_HEAD_Y, layout.head_sprite(width), tooltip=tooltip)
            body += through("of_sort_%s_icon" % name, x + (width - 27) // 2, OF_HEAD_Y + 2, picture)
        effects += block("of_sort_%s_click" % name, (
            iff("check_variable = { mod1440_of_sort_by = %d }" % number, flip("mod1440_of_up"))
            + els(setv("mod1440_of_sort_by", number) + setv("mod1440_of_up", 0))
            + setv("mod1440_of_arrow_x", x + width - M.ARROW_DX) + "mod1440_of_list = yes\n"))
        key = tmp("of_key", value)
        if name in OF_NAVY:
            key += iff("is_navy_leader = yes", tmp("of_key", OF_NAVY[name]))
        keys += iff("check_variable = { ROOT.mod1440_of_sort_by = %d }" % number, key, "if" if number == 1 else "else_if")
        if name in OF_NUMBERS:
            font = M.FONT_VALUE if name == "skill" else M.FONT_LABEL
            entry += M.text("of_cell_%s" % name, rx + 2, middle, width - 4, B.key("of_cell_%s" % name, "[?%s|0]" % value), font, "centre", 22)
            if name in OF_NAVY:
                entry += M.text("of_cell_%s_navy" % name, rx + 2, middle, width - 4, B.key("of_cell_%s_navy" % name, "[?%s|0]" % OF_NAVY[name]),
                                font, "centre", 22)
                row_triggers += block("of_cell_%s_visible" % name, "NOT = { is_navy_leader = yes }\n")
                row_triggers += block("of_cell_%s_navy_visible" % name, "is_navy_leader = yes\n")
            elif name in ("won", "lost"):
                row_triggers += block("of_cell_%s_visible" % name, M.more_than_zero(value))
        elif name == "traits":
            # his traits as the game's icons, from the array kept on him; +N for those no icon stands for
            for t in range(TRAIT_ICONS):
                widget = "of_row_tr_%d" % t
                entry += M.icon(widget, rx + 4 + t * TRAIT_STEP, 7, TRAIT_SAMPLE[t])
                properties += block(widget, 'image = "GFX_trait_[?mod1440_of_tr^%d.GetTokenKey]"\n' % t)
                row_triggers += block(widget + "_visible", "check_variable = { mod1440_of_tr_i > %d }\n" % t)
            entry += M.text("of_row_tr_more", rx + 4 + TRAIT_ICONS * TRAIT_STEP, 14, width - 8 - TRAIT_ICONS * TRAIT_STEP,
                            B.key("of_row_tr_more", "+[?mod1440_of_tr_plus|0]"), M.FONT_SMALL, height=20)
            row_triggers += block("of_row_tr_more_visible", M.more_than_zero("mod1440_of_tr_plus"))
        elif name == "dec":
            # up to three of his medals at half size: the strip of its set and its frame, kept for the row
            for k in range(ROW_MEDALS):
                widget = "of_row_md_%d" % k
                entry += scaled(widget, rx + 4 + k * 28, 3, MEDAL_STRIP % "ger", 0.5)
                properties += block(widget, 'image = "[?mod1440_of_rm^%d.GetTokenKey]"\nframe = mod1440_of_rf^%d\n' % (k, k))
                row_triggers += block(widget + "_visible", "check_variable = { mod1440_of_dec^num > %d }\n" % k)
        x += width
        rx += width
    first = REC_BODY_X + OF_FACE_W + OF_NAME + OF_COLUMNS[0][2] - M.ARROW_DX
    body += scaled("of_arrow_down", first, OF_HEAD_Y + M.ARROW_DY, "GFX_arrow_down_small", M.ARROW)
    body += scaled("of_arrow_up", first, OF_HEAD_Y + M.ARROW_DY, "GFX_arrow_up_small", M.ARROW)
    properties += block("of_arrow_down", "x = mod1440_of_arrow_x\n") + block("of_arrow_up", "x = mod1440_of_arrow_x\n")
    triggers += block("of_arrow_down_visible", M.more_than_zero("mod1440_of_sort_by") + "NOT = { %s }\n" % is_one("mod1440_of_up"))
    triggers += block("of_arrow_up_visible", M.more_than_zero("mod1440_of_sort_by") + is_one("mod1440_of_up") + "\n")
    body += listing("of_list", "of_grid", REC_BODY_X, OF_LIST_Y, OF_ROW_W + 30, OF_LIST_H, OF_ROW)
    # the row's scope is the officer: the mark of the one chosen before is taken off, his put on; Award ends
    effects += block("of_row_click", (
        "mod1440_of_me = yes\n"
        + block("ROOT", iff(is_one("mod1440_of_has_sel"), block("var:mod1440_of_sel", setv("mod1440_of_picked", 0)))
                + setv("mod1440_of_sel", "of_me") + setv("mod1440_of_has_sel", 1) + setv("mod1440_of_awarding", 0))
        + setv("mod1440_of_picked", 1) + block("ROOT", "mod1440_of_card = yes\n")))

    # ---- the file of the chosen officer: five cards drawn as icons, so that the Award mode can put one card over two
    has = is_one("mod1440_of_has_sel") + "\n"
    award = is_one("mod1440_of_awarding")
    filing = has + "NOT = { %s }\n" % award           # his file, not the Award mode
    awarding = has + award + "\n"
    W = OF_CARD_W
    tops = {}
    y = 0
    for name, height in OF_CARDS:
        tops[name] = y
        y += height + OF_CARD_GAP
    tops["diary"] = y
    diary_h = REC_BODY_H - y
    award_h = REC_BODY_H - tops["dec"]
    inner = ""
    for name, height in OF_CARDS + [("diary", diary_h)]:
        inner += M.icon("of_f_%s_bg" % name, 0, tops[name], CARD_SPRITE % (W, height))
    inner += M.icon("of_f_award_bg", 0, tops["dec"], CARD_SPRITE % (W, award_h))
    triggers += shown_if(["of_f_dec_bg", "of_f_diary_bg"], "NOT = { %s }\n" % award) + block("of_f_award_bg_visible", award + "\n")

    def title(name, words, top, when=None):
        nonlocal inner, triggers
        inner += M.text("of_f_%s_title" % name, 14, top + 8, W - 28, B.key("of_f_%s_title" % name, words), M.FONT_CARD, height=30)
        if when:
            triggers += block("of_f_%s_title_visible" % name, when)

    def variants(name, x, y, width, font, fmt, options):
        """One of several texts on the same spot, each shown when its condition holds."""
        out, extra = "", ""
        for suffix, value, condition in options:
            widget = "of_c_%s%s" % (name, suffix)
            out += M.text(widget, x, y, width, B.key(widget, value), font, fmt, 22)
            extra += block(widget + "_visible", has + condition)
        return out, extra

    def plate(name, x, y, value, icons, tip=None):
        """A level: the game's icon over the number, on a plate. icons: (sprite, condition) each."""
        nonlocal inner, triggers
        inner += M.icon(name + "_bg", x, y, M.tile_sprite(88))
        for n, (sprite, condition) in enumerate(icons):
            inner += M.icon("%s_i%d" % (name, n), x + (88 - 27) // 2, y + 5, sprite)
            triggers += block("%s_i%d_visible" % (name, n), has + condition)
        inner += M.text(name, x + 6, y + 30, 76, B.key(name, value), M.FONT_VALUE, "centre", 26,
                        tooltip=B.key(name + "_tt", tip) if tip else None)
        triggers += block(name + "_bg_visible", has) + block(name + "_visible", has)

    rank3 = "check_variable = { mod1440_of_c_rank = 3 }\n"
    army = "NOT = { %s }\n" % rank3.strip()

    # who he is: portrait, name, rank and status, the levels, his command
    top = tops["head"]
    # E7: a unit leader's face is a list of one row (mod1440_of_c_ul, filled by mod1440_of_card); the table's portrait
    # shows for one who is no unit leader any more
    inner += portrait("of_c_face", 14, top + 14)
    properties += shown("of_c_face", "mod1440_of_c_p")
    inner += face_grid("of_c_gface_grid", 14, top + 14, 1.0)
    properties += block("of_c_gface", GAME_FACE)
    inner += M.text("of_c_name", OF_SIDE, top + 10, W - OF_SIDE - 14, B.key("of_c_name", "[?mod1440_of_sel.GetName]"), M.FONT_TITLE, height=40, fixed=True)
    inner += M.text("of_c_none", 16, top + 18, W - 32, B.key("of_c_none", "Click an officer in the table to open his file."), M.FONT_LABEL)
    triggers += shown_if(["of_c_name"], has) + block("of_c_none_visible", "NOT = { %s }\n" % has.strip())
    triggers += block("of_c_face_visible", has + "check_variable = { mod1440_of_c_ul^num < 1 }\n")
    status = lambda n: "check_variable = { mod1440_of_c_status = %d }\n" % n
    for name, x, width, font, options in (
            ("rank", OF_SIDE + 2, 150, M.FONT_LABEL, [("_1", "§YField Marshal§!", "check_variable = { mod1440_of_c_rank = 1 }\n"),
                                                     ("_2", "§YGeneral§!", "check_variable = { mod1440_of_c_rank = 2 }\n"),
                                                     ("_3", "§YAdmiral§!", rank3)]),
            ("status", OF_SIDE + 130, W - OF_SIDE - 144, M.FONT_SMALL, [
                ("_off", "§Rno longer serving§!", status(4)), ("_cap", "§Rcaptured§!", status(3)),
                ("_grp", "serving  ·  leads an army group", status(2)),
                ("_army", "serving  ·  commands an army", status(1) + army), ("_fleet", "serving  ·  commands a fleet", status(1) + rank3),
                ("_idle", "serving  ·  unassigned", status(0))])):
        piece, extra = variants(name, x, top + 56 + (2 if font == M.FONT_SMALL else 0), width, font, "left", options)
        inner += piece
        triggers += extra
    inner += M.icon("of_c_skill_bg", OF_SIDE, top + 84, M.tile_sprite(88))
    inner += M.text("of_c_skill_l", OF_SIDE + 6, top + 91, 76, B.key("of_c_skill_l", "Skill"), M.FONT_SMALL, "centre", 20)
    inner += M.text("of_c_skill", OF_SIDE + 6, top + 114, 76, B.key("of_c_skill", "[?mod1440_of_c_skill|0]"), M.FONT_VALUE, "centre", 26)
    triggers += shown_if(["of_c_skill_bg", "of_c_skill_l", "of_c_skill"], has)
    for n, (name, column) in enumerate((("atk", "atk"), ("def", "def"), ("c3", "c3"), ("c4", "c4"))):
        sprite = [c[4] for c in OF_COLUMNS if c[0] == column][0]
        icons = [(sprite, army), (OF_NAVY_ICON[column], rank3)] if column in OF_NAVY_ICON else [(sprite, "")]
        tip = [c[5] for c in OF_COLUMNS if c[0] == column][0]
        plate("of_c_" + name, OF_SIDE + (n + 1) * 94, top + 84, "[?mod1440_of_c_%s|0]" % name, icons, tip)
    command = [("div", "Divisions", "[?mod1440_of_c_cmd|0]", "Divisions he commands today."),
               ("bat", "Battalions", "[?mod1440_of_c_bat|0]", "Battalions in those divisions."),
               ("fight", "Fighting", "[?mod1440_of_c_fight|0]", "Divisions of his in a battle today."),
               ("arm", "Armoured", "[?mod1440_of_c_arm|0]", "Divisions of his whose main kind is armour."),
               ("plan", "Planning", "[?mod1440_of_c_plan|%0]", "The planning his divisions have built up, on average.")]
    fleet = [("ships", "Ships", "[?mod1440_of_c_cmd|0]", "Ships he commands today.")] + [
        (short, words, "[?mod1440_of_c_%s|0]" % short, "%s he commands today." % words) for short, kind, words in SHIP_KINDS]
    for group, condition in ((command, army), (fleet, rank3)):
        for n, (name, label, value, tip) in enumerate(group):
            piece, extra = tile("of_c_" + name, OF_SIDE + n * 94, top + 156, label, value, tip, has + condition, width=88)
            inner += piece
            triggers += extra

    # his traits by icon and name; how many he has of how many he can take, and those the table does not know
    top = tops["traits"]
    title("traits", "Traits", top)
    inner += M.text("of_c_tr_count", W - 14 - 260, top + 14, 260, B.key("of_c_tr_count", "[?mod1440_of_c_traits|0] of [?mod1440_of_c_max|0] he can take"),
                    M.FONT_SMALL, "right", 20, tooltip=B.key("of_c_tr_count_tt", "His traits, of the traits the game lets him take."))
    inner += M.text("of_c_tr_other", W - 14 - 260 - 170, top + 14, 160, B.key("of_c_tr_other", "+[?mod1440_of_c_tr_other|0] of other mods"),
                    M.FONT_SMALL, "right", 20, tooltip=B.key("of_c_tr_other_tt", "Traits the mod's table of traits does not name: another mod's."))
    inner += M.text("of_c_tr_over", W - 14 - 260 - 170 - 110, top + 14, 100, B.key("of_c_tr_over", "+[?mod1440_of_c_tr_over|0] more"),
                    M.FONT_SMALL, "right", 20)
    inner += M.text("of_c_tr_none", 18, top + 46, W - 36, B.key("of_c_tr_none", "No trait the mod's table names."), M.FONT_SMALL, height=22)
    triggers += block("of_c_tr_count_visible", has) + block("of_c_tr_other_visible", has + M.more_than_zero("mod1440_of_c_tr_other"))
    triggers += block("of_c_tr_over_visible", has + M.more_than_zero("mod1440_of_c_tr_over"))
    triggers += block("of_c_tr_none_visible", has + "check_variable = { mod1440_of_c_tr_k < 1 }\n")
    for k in range(TRAIT_ICONS):
        tx, ty = 16 + (k % 3) * 212, top + 40 + (k // 3) * 34
        widget = "of_c_tr_%d" % k
        inner += M.icon(widget, tx, ty, TRAIT_SAMPLE[k])
        properties += block(widget, 'image = "GFX_trait_[?mod1440_of_c_tr^%d.GetTokenKey]"\n' % k)
        inner += M.icon(widget + "_x", tx, ty, "GFX_trait_unknown")
        inner += M.text(widget + "_n", tx + 30, ty + 6, 178, B.key(widget + "_n", "[?mod1440_of_c_tr^%d.GetTokenLocalizedKey]" % k), M.FONT_SMALL, height=22, fixed=True)
        triggers += block(widget + "_visible", has + "check_variable = { mod1440_of_c_tr_i > %d }\n" % k)
        triggers += block(widget + "_x_visible", has + "check_variable = { mod1440_of_c_tr_i < %d }\ncheck_variable = { mod1440_of_c_tr_k > %d }\n" % (k + 1, k))
        triggers += block(widget + "_n_visible", has + "check_variable = { mod1440_of_c_tr_k > %d }\n" % k)

    # his service record: six figures, three dates
    top = tops["rec"]
    title("rec", "Service record", top)
    for n, (name, label, value, tip) in enumerate(OF_FIGURES):
        piece, extra = tile("of_c_" + name, 14 + n * 106, top + 42, label, value, tip, has, width=100)
        inner += piece
        triggers += extra
    for n, (name, label) in enumerate((("since", "Commissioned"), ("prom", "Promoted to field marshal"), ("lvl", "Last skill level"))):
        ly = top + 114 + n * 22
        inner += M.text("of_c_%s_l" % name, 18, ly, 280, B.key("of_c_%s_l" % name, label), M.FONT_SMALL, height=22)
        options = [("", "[?mod1440_of_c_%s.%s]" % (name, LONG), is_one("mod1440_of_c_has_%s" % name) + "\n")]
        options.append(("_old", "before the record began" if name == "since" else "-", "NOT = { %s }\n" % is_one("mod1440_of_c_has_%s" % name)))
        piece, extra = variants(name, 300, ly - 2, W - 316, M.FONT_LABEL, "left", options)
        inner += piece
        triggers += extra + block("of_c_%s_l_visible" % name, has)

    # his decorations: the medals side by side, their names; in the Award mode the country's medals over both cards
    top = tops["dec"]
    title("dec", "Decorations", top, has)
    inner += M.button("of_award_on", W - 310, top + 9, "GFX_sort_button_140x29", B.key("of_award_on", "Award..."),
                      tooltip=B.key("of_award_on_tt", "Your country's medals: award him one."))
    inner += M.button("of_takeback", W - 160, top + 9, "GFX_sort_button_140x29", B.key("of_takeback", "Take back last"),
                      tooltip=B.key("of_takeback_tt", "Takes the decoration awarded last from this officer."))
    inner += M.button("of_award_off", W - 160, top + 9, "GFX_sort_button_140x29", B.key("of_award_off", "Back to his file"))
    inner += M.text("of_c_dec_none", 18, top + 46, W - 36, B.key("of_c_dec_none", "None yet. Award... shows the medals of your country."), M.FONT_SMALL, height=22)
    triggers += block("of_award_on_visible", filing) + block("of_award_off_visible", awarding)
    triggers += block("of_takeback_visible", filing + M.more_than_zero("mod1440_of_c_dec_n"))
    triggers += block("of_c_dec_none_visible", filing + "check_variable = { mod1440_of_c_dec_n < 1 }\n")
    effects += block("of_takeback_click", "mod1440_md_takeback = yes\n")
    effects += block("of_award_on_click", setv("mod1440_of_awarding", 1) + "add_to_variable = { mod1440_rec_dirty = 1 }\n")
    effects += block("of_award_off_click", setv("mod1440_of_awarding", 0) + "add_to_variable = { mod1440_rec_dirty = 1 }\n")
    for k in range(RACK):
        more = filing + "check_variable = { mod1440_of_c_dec_n > %d }\n" % k
        tip = B.key("of_c_rack_%d_tt" % k, "[?mod1440_of_c_dec_key^%d.GetTokenLocalizedKey]\\n[?mod1440_of_c_dec_date^%d.%s]" % (k, k, LONG))
        widget = "of_c_rack_%d" % k
        inner += scaled(widget, 18 + k * 62, top + 42, MEDAL_STRIP % "ger", 1.0, tip)
        properties += block(widget, 'image = "[?mod1440_of_c_dec_strip^%d.GetTokenKey]"\nframe = mod1440_of_c_dec_frame^%d\n' % (k, k))
        triggers += block(widget + "_visible", more)
    for k in range(DEC_LINES):
        more = filing + "check_variable = { mod1440_of_c_dec_n > %d }\n" % k
        ly = top + 136 + k * 22
        inner += M.text("of_c_dec_%d" % k, 18, ly, 370, B.key("of_c_dec_%d" % k, "[?mod1440_of_c_dec_key^%d.GetTokenLocalizedKey]" % k),
                        M.FONT_LABEL, height=22, fixed=True)
        inner += M.text("of_c_dec_%d_d" % k, 400, ly + 2, W - 416,
                        B.key("of_c_dec_%d_d" % k, "[?mod1440_of_c_dec_date^%d.%s]" % (k, LONG)), M.FONT_SMALL, height=22)
        triggers += block("of_c_dec_%d_visible" % k, more) + block("of_c_dec_%d_d_visible" % k, more)
    inner += M.text("of_md_hint", 18, top + 42, W - 36, B.key(
        "of_md_hint", "Your country's medals as the game has them: a record only, no bonus, no cost."), M.FONT_SMALL, height=22)
    triggers += block("of_md_hint_visible", awarding)
    for k in range(MEDAL_SLOTS):
        px, py = 18 + (k % 2) * 318, top + 66 + (k // 2) * 74
        more = awarding + "check_variable = { mod1440_md_count > %d }\n" % k
        held = "check_variable = { mod1440_md_has^%d = 1 }\n" % k
        inner += M.icon("of_md_%d_bg" % k, px, py, M.tile_sprite(306, 68))
        inner += scaled("of_md_%d" % k, px + 10, py + 4, MEDAL_STRIP % "ger", 0.7)
        properties += block("of_md_%d" % k, 'image = "[?mod1440_md_strip^%d.GetTokenKey]"\nframe = mod1440_md_frame^%d\n' % (k, k))
        inner += M.text("of_md_%d_name" % k, px + 56, py + 8, 246, B.key("of_md_%d_name" % k, "[?mod1440_md_key^%d.GetTokenLocalizedKey]" % k),
                        M.FONT_LABEL, height=22, fixed=True)
        inner += M.button("of_award_%d" % k, px + 56, py + 34, "GFX_sort_button_100x29", B.key("of_award", "Award"))
        inner += M.text("of_md_%d_held" % k, px + 56, py + 40, 240, B.key("of_md_%d_held" % k, "§Gawarded§! [?mod1440_md_date^%d.%s]" % (k, LONG)),
                        M.FONT_SMALL, height=22)
        triggers += "".join(block(w + "_visible", more) for w in ("of_md_%d_bg" % k, "of_md_%d" % k, "of_md_%d_name" % k))
        triggers += block("of_award_%d_visible" % k, more + "NOT = { %s }\n" % held.strip()) + block("of_md_%d_held_visible" % k, more + held)
        effects += block("of_award_%d_click" % k, tmp("md_k", k) + "mod1440_md_award = yes\n")

    # what the War Diary has about him: his own lines, and the states and victory points he was at
    top = tops["diary"]
    title("diary", "In the War Diary", top, "NOT = { %s }\n" % award)
    inner += M.text("of_ln_order", W - 14 - 200, top + 14, 200, B.key("of_ln_order", "newest first"), M.FONT_SMALL, "right", 20)
    inner += M.text("of_ln_none", 18, top + 44, 500, B.key("of_ln_none", "Nothing yet."), M.FONT_SMALL, height=22)
    triggers += block("of_ln_order_visible", filing) + block("of_ln_none_visible", filing + "check_variable = { mod1440_of_ln_n < 1 }\n")
    for k in range(CARD_LINES):
        more = filing + "check_variable = { mod1440_of_ln_n > %d }\n" % k
        ly = top + 44 + k * 22
        if k % 2:
            inner += M.icon("of_ln_%d_bg" % k, 10, ly - 2, STRIPE % (W - 20, 22))
            triggers += block("of_ln_%d_bg_visible" % k, more)
        inner += M.text("of_ln_%d_d" % k, 18, ly, 150, B.key("of_ln_%d_d" % k, "[?mod1440_of_ln_date^%d.%s]" % (k, LONG)), M.FONT_SMALL, height=22)
        for family, text_icon in sorted(FAMILY_ICON.items()):
            widget = "of_ln_%d_f%d" % (k, family)
            inner += M.text(widget, 170, ly - 2, 26, B.key("wd_icon_%d" % family, "£" + text_icon), M.FONT_SMALL, height=22)
            triggers += block(widget + "_visible", more + "check_variable = { mod1440_of_ln_fam^%d = %d }\n" % (k, family))
        inner += M.text("of_ln_%d" % k, 198, ly, 214, B.key("of_ln_%d" % k, "[?mod1440_of_ln_kind^%d.GetTokenLocalizedKey]" % k), M.FONT_SMALL, height=22)
        piece, extra = subject("of_ln", k, 416, ly, W - 430, filing)
        inner += piece
        triggers += block("of_ln_%d_d_visible" % k, more) + block("of_ln_%d_visible" % k, more) + extra
    body += M.box("of_card", OF_CARD_X, OF_CARD_Y, OF_CARD_W, REC_BODY_H, inner)

    gui, script = page_gui("of", 1, body, dirty="mod1440_rec_dirty",
                           lists=block("of_grid", 'array = mod1440_of_rows\nchange_scope = yes\nentry_container = "mod1440_records_officer_row"\n')
                           + face_list("of_c_gface_grid", "mod1440_of_c_ul", "of_c_gface"),
                           effects=effects, triggers=triggers + row_triggers, properties=properties)
    gui += row("mod1440_records_officer_row", OF_ROW_W, OF_ROW, entry)
    gui += game_face("of_c_gface", 1.0)

    # ---- script
    # THIS is nothing a variable can hold for an officer whose command came by an effect: of_me is (places())
    has_me = "NOT = { check_variable = { of_me = 0 } }"
    stale_traits = "OR = { %s NOT = { check_variable = { mod1440_of_tr_n = num_traits } } }" % stale("mod1440_of_tr_v", trait_version)
    # (E7 gate B: and whether he is a unit leader, mod1440_of_ul, which the game's faces read; E7 fix round 1: and his
    # table portrait, cached once per table and epoch as before E7, for the day he leaves the service)
    mark = setv("mod1440_of_seen_day", "global.num_days") + UL_MARK + officer_table(portrait_version) + "add_to_temp_variable = { of_serving = 1 }\nmod1440_of_me = yes\n" + iff(
        "NOT = { %s } %s" % (is_one("mod1440_of_known"), has_me), (
            setv("mod1440_of_known", 1) + "add_to_array = { PREV.mod1440_of_known = of_me }\n"
            # No hook tells of a command given by an effect. An officer first met after the country's list was made
            # is taken as commissioned on that day; the first few of a day get a line, the others share one.
            + iff("check_variable = { of_had = 1 } NOT = { has_variable = mod1440_of_since_day }", (
                setv("mod1440_of_since", "global.date") + setv("mod1440_of_since_day", "global.num_days")
                + "add_to_temp_variable = { of_new = 1 }\n"
                + iff("check_variable = { of_new < %d }" % (COMM_LINES + 1),
                      fill("commissioned", a="of_me") + block("PREV", "mod1440_ev_add = yes\n"))))))
    # his traits: made again only when he has gained or lost one, or the table has changed
    mark += iff(stale_traits, "mod1440_of_traits = yes\n")
    mark += iff(stale("mod1440_of_md"), "mod1440_of_medals_again = yes\n")
    # an officer who serves no longer is not seen by the daily run: his portrait and traits are looked at when the list is made
    # (E7: the table's portrait for him alone; the face of one who serves is the game's)
    # (E7 fix round 1: the table's portrait of one who has left is the one cached while he served, officer_table())
    keep = UL_MARK + officer_table(portrait_version) + tmp("of_keep", 1)
    keep += iff(stale("mod1440_of_tr_v", trait_version), "mod1440_of_traits = yes\n")
    # his medals: their names and strips are text keys too, made again from the numbers of the medals (fix round 1)
    keep += iff(stale("mod1440_of_md"), "mod1440_of_medals_again = yes\n")
    keep += iff("NOT = { check_variable = { mod1440_of_rm_n = mod1440_of_dec^num } }", "mod1440_of_rack = yes\n")
    keep += iff("check_variable = { mod1440_of_rm^num < %d }" % ROW_MEDALS, "mod1440_of_rack = yes\n")
    keep += iff("check_variable = { ROOT.mod1440_of_show = 5 } NOT = { %s }" % FORMER, tmp("of_keep", 0))
    keep += iff("NOT = { check_variable = { ROOT.mod1440_of_show = 5 } } " + FORMER, tmp("of_keep", 0))
    keep += iff("check_variable = { ROOT.mod1440_of_show = 1 } is_navy_leader = yes", tmp("of_keep", 0))
    keep += iff("check_variable = { ROOT.mod1440_of_show = 2 } NOT = { is_navy_leader = yes }", tmp("of_keep", 0))
    keep += iff("check_variable = { ROOT.mod1440_of_show = 3 } check_variable = { num_units < 1 } check_variable = { num_ships < 1 }", tmp("of_keep", 0))
    keep += iff("check_variable = { ROOT.mod1440_of_show = 4 } check_variable = { mod1440_of_dec^num < 1 }", tmp("of_keep", 0))
    frames = "".join(setv("mod1440_of_frame_%d" % v, 1) for v, _, _, _ in OF_FILTERS)
    frames += "".join(iff("check_variable = { mod1440_of_show = %d }" % v, setv("mod1440_of_frame_%d" % v, 2)) for v, _, _, _ in OF_FILTERS)

    def date_copy(name):
        return (setv("PREV.mod1440_of_c_%s" % name, "mod1440_of_%s" % name) + setv("PREV.mod1440_of_c_has_%s" % name, 0)
                + iff("check_variable = { mod1440_of_%s_day > 0 }" % name, setv("PREV.mod1440_of_c_has_%s" % name, 1)))

    def his(log):
        """A line of a log that is about the chosen officer: he is its person, or the officer on the spot."""
        return ("check_variable = { mod1440_of_ln_date^num < %d } OR = { "
                "AND = { check_variable = { mod1440_%s_sa^mg_m = 1 } check_variable = { mod1440_%s_a^mg_m = mod1440_of_sel } } "
                "AND = { check_variable = { mod1440_%s_sc^mg_m = 1 } check_variable = { mod1440_%s_c^mg_m = mod1440_of_sel } } }"
                % (CARD_LINES, log, log, log, log))

    def his_line(log):
        """The date, the family and the words of the line; and what it is about, unless that is the officer himself."""
        return ("add_to_array = { mod1440_of_ln_date = mod1440_%s_date^mg_m }\nadd_to_array = { mod1440_of_ln_kind = mod1440_%s_kind^mg_m }\n"
                "add_to_array = { mod1440_of_ln_fam = mod1440_%s_fam^mg_m }\n" % (log, log, log)
                + iff("check_variable = { mod1440_%s_sa^mg_m > 1 }" % log,
                      "add_to_array = { mod1440_of_ln_a = mod1440_%s_a^mg_m }\nadd_to_array = { mod1440_of_ln_sa = mod1440_%s_sa^mg_m }\n" % (log, log))
                + els("add_to_array = { mod1440_of_ln_a = 0 }\nadd_to_array = { mod1440_of_ln_sa = 0 }\n"))

    medals = "".join(iff("check_variable = { mod1440_md_id^num < %d } %s" % (MEDAL_SLOTS, available), (
        "add_to_array = { mod1440_md_id = %d }\nadd_to_array = { mod1440_md_key = token:%s }\n"
        "add_to_array = { mod1440_md_set = %d }\nadd_to_array = { mod1440_md_frame = %d }\n"
        "add_to_array = { mod1440_md_strip = token:%s }\n" % (n, name, sets.index(strip), frame, MEDAL_STRIP % strip)))
        for n, (name, strip, frame, available) in enumerate(MEDALS, start=1))
    copy_levels = (
        setv("PREV.mod1440_of_c_skill", "skill_level") + setv("PREV.mod1440_of_c_atk", "attack_level") + setv("PREV.mod1440_of_c_def", "defense_level")
        + setv("PREV.mod1440_of_c_c3", "planning_level") + setv("PREV.mod1440_of_c_c4", "logistics_level")
        + setv("PREV.mod1440_of_c_rank", 2) + setv("PREV.mod1440_of_c_cmd", "num_units")
        + setv("PREV.mod1440_of_c_bat", "num_battalions") + setv("PREV.mod1440_of_c_fight", "num_units_in_combat")
        + setv("PREV.mod1440_of_c_arm", "num_armored") + setv("PREV.mod1440_of_c_plan", "avg_unit_planning_ratio")
        + iff("is_field_marshal = yes", setv("PREV.mod1440_of_c_rank", 1))
        + iff("is_navy_leader = yes", setv("PREV.mod1440_of_c_rank", 3) + setv("PREV.mod1440_of_c_cmd", "num_ships")
              + setv("PREV.mod1440_of_c_c3", "maneuvering_level") + setv("PREV.mod1440_of_c_c4", "coordination_level")
              + "".join(setv("PREV.mod1440_of_c_%s" % short, "num_ships_with_type@" + kind) for short, kind, words in SHIP_KINDS))
        # what he does today: 0 unassigned, 1 a command, 2 an army group, 3 captured, 4 no longer serving
        + setv("PREV.mod1440_of_c_status", 0)
        + iff("OR = { check_variable = { num_units > 0 } check_variable = { num_ships > 0 } }", setv("PREV.mod1440_of_c_status", 1))
        + iff("is_leading_army_group = yes", setv("PREV.mod1440_of_c_status", 2))
        + iff("NOT = { is_navy_leader = yes } is_general_captured = yes", setv("PREV.mod1440_of_c_status", 3))
        + iff(FORMER, setv("PREV.mod1440_of_c_status", 4)))
    copy_traits = (
        iff(stale_traits, "mod1440_of_traits = yes\n")
        + setv("PREV.mod1440_of_c_traits", "num_traits") + setv("PREV.mod1440_of_c_max", "num_max_traits")
        + setv("PREV.mod1440_of_c_tr_i", "mod1440_of_tr_i") + setv("PREV.mod1440_of_c_tr_k", "mod1440_of_tr_k")
        + setv("PREV.mod1440_of_c_tr_other", "num_traits") + "subtract_from_variable = { PREV.mod1440_of_c_tr_other = mod1440_of_tr_k }\n"
        + setv("PREV.mod1440_of_c_tr_over", "mod1440_of_tr_k") + "subtract_from_variable = { PREV.mod1440_of_c_tr_over = %d }\n" % TRAIT_ICONS
        + block("for_each_loop", "array = mod1440_of_tr\nvalue = of_v\nadd_to_array = { PREV.mod1440_of_c_tr = of_v }\n"))
    # E1 review: who left the service or was captured (mod1440_of_gone, once a day after mod1440_of_seen)
    write = lambda kind: fill(kind, a="of_me") + block("PREV", "mod1440_ev_add = yes\n")
    captured = "NOT = { is_navy_leader = yes } is_general_captured = yes"
    first_run = setv("mod1440_of_gone_v", 1) + block("for_each_scope_loop", "array = mod1440_of_known\n" + iff(FORMER, setv("mod1440_of_out", 1))
                                                     + iff(captured, setv("mod1440_of_held", 1)))
    not_met = iff("NOT = { %s }" % is_one("mod1440_of_out"), (
        setv("mod1440_of_out", 1) + "mod1440_of_me = yes\n"
        + iff(has_me, iff("%s NOT = { %s }" % (captured, is_one("mod1440_of_held")), setv("mod1440_of_held", 1) + write("officer_captured"))
              + els(write("officer_gone")))))
    met = (setv("mod1440_of_out", 0)
           + iff(captured, iff("NOT = { %s }" % is_one("mod1440_of_held"), setv("mod1440_of_held", 1) + "mod1440_of_me = yes\n" + iff(has_me, write("officer_captured"))))
           + els(setv("mod1440_of_held", 0)))
    gone_script = iff("NOT = { %s }" % is_one("mod1440_of_gone_v"), first_run) + els(
        block("for_each_scope_loop", "array = mod1440_of_known\n" + UL_MARK + iff(FORMER, not_met) + els(met)))
    script_effects = (
        places()
        + trait_script
        + "\n# Officers: the medals at half size in his row: the strips and frames of his first %d decorations, padded.\n" % ROW_MEDALS
        + block("mod1440_of_rack", (
            "clear_array = mod1440_of_rm\nclear_array = mod1440_of_rf\n"
            + medal_tokens(sets, "mod1440_of_dec_set", "mod1440_of_rm", ROW_MEDALS)
            + block("for_each_loop", "array = mod1440_of_dec_frame\nvalue = md_v\nindex = md_ix\n"
                    + iff("check_variable = { md_ix < %d }" % ROW_MEDALS, "add_to_array = { mod1440_of_rf = md_v }\n"))
            + pad([("mod1440_of_rm", "token:" + MEDAL_STRIP % sets[0]), ("mod1440_of_rf", 1)], ROW_MEDALS)
            + setv("mod1440_of_rm_n", "mod1440_of_dec^num")))
        + "\n# Officers: the names of his decorations again from their numbers, and the strips of his row: text keys whose\n"
        "# numbers have moved since they were written (kept_tokens(), fix round 1).\n"
        + block("mod1440_of_medals_again", (
            block("for_each_loop", "array = mod1440_of_dec\nvalue = md_v\nindex = md_ix\n" + iff(
                "check_variable = { md_ix < mod1440_of_dec_key^num }", "".join(
                    iff("check_variable = { md_v = %d }" % n, setv("mod1440_of_dec_key^md_ix", "token:" + name), "if" if n == 1 else "else_if")
                    for n, (name, strip, frame, available) in enumerate(MEDALS, start=1))))
            + "mod1440_of_rack = yes\n" + stamped("mod1440_of_md")))
        + "\n# Officers: marks every officer who serves today with the day, and adds an officer the record does not know\n"
        "# yet to its list. A retired officer keeps his place in that list (X34). How many serve: the count of the tab.\n"
        + block("mod1440_of_seen", (
            "mod1440_of_refs = yes\n" + tmp("of_had", 0) + iff(is_one("mod1440_of_listed"), tmp("of_had", 1)) + tmp("of_new", 0) + tmp("of_serving", 0)
            # the game's own loops reach every leader; its arrays army_leaders and navy_leaders hold nothing in the
            # place of one without a number
            + block("every_army_leader", mark) + block("every_navy_leader", mark)
            + setv("mod1440_of_listed", 1) + setv("mod1440_of_serving", "of_serving")
            + iff("check_variable = { of_new > %d }" % COMM_LINES, (
                tmp("of_more", "of_new") + "subtract_from_temp_variable = { of_more = %d }\n" % COMM_LINES
                + line("commissioned_more", n="of_more") + "add_to_variable = { mod1440_ct^%d = of_more }\n" % NUMBER["commissioned"]))))
        + "\n# Officers (E1 review, 2026-10-22): once a day after mod1440_of_seen, a line for an officer the record knows who\n"
        "# was not met today (Left the service) or who is held by an enemy (Captured:). The marks mod1440_of_out and\n"
        "# mod1440_of_held on him keep each to one line; met again, free again, the mark clears. The first run takes\n"
        "# those already gone without a line.\n"
        + block("mod1440_of_gone", gone_script)
        + "\n# Officers: makes the list of the page again: who the filter wants, in the order of the chosen column,\n"
        "# every second row marked for its stripe.\n"
        + block("mod1440_of_list", (
            "mod1440_of_seen = yes\nclear_array = mod1440_of_rows\n"
            + block("for_each_scope_loop", "array = mod1440_of_known\n" + keep
                    + iff("check_variable = { of_keep = 1 }", "mod1440_of_me = yes\n" + iff(
                        has_me, "add_to_array = { ROOT.mod1440_of_rows = of_me }\n")))
            + iff("check_variable = { mod1440_of_sort_by > 0 }", (
                "clear_array = mod1440_of_keys\n"
                + block("for_each_scope_loop", "array = mod1440_of_rows\n" + tmp("of_key", 0) + keys
                        + iff(is_one("ROOT.mod1440_of_up"), "multiply_temp_variable = { of_key = -1 }\n")
                        + "add_to_array = { ROOT.mod1440_of_keys = of_key }\n")
                + "clear_array = mod1440_of_sorted\n"
                + block("for_loop_effect", "start = 0\nend = mod1440_of_rows^num\nvalue = of_step\n"
                        + block("find_highest_in_array", "array = mod1440_of_keys\nvalue = of_high\nindex = of_at\n")
                        + "add_to_array = { mod1440_of_sorted = mod1440_of_rows^of_at }\n" + setv("mod1440_of_keys^of_at", -2000000))
                + "clear_array = mod1440_of_rows\n"
                + block("for_each_loop", "array = mod1440_of_sorted\nvalue = of_copy\nadd_to_array = { mod1440_of_rows = of_copy }\n")))
            + tmp("of_par", 0) + block("for_each_scope_loop", "array = mod1440_of_rows\n" + setv("mod1440_of_odd", "of_par")
                                       + iff("check_variable = { of_par = 0 }", tmp("of_par", 1)) + els(tmp("of_par", 0)))
            + frames + "mod1440_md_list = yes\nmod1440_of_card = yes\n"))
        + "\n# Officers: copies the chosen officer's values, traits, record, decorations and diary lines to the country,\n"
        "# where his file reads them. His own values are read in his scope (X33).\n"
        + block("mod1440_of_card", "clear_array = mod1440_of_c_ul\n" + iff(is_one("mod1440_of_has_sel"), (
            "mod1440_ev_grow = yes\n" + "".join("clear_array = mod1440_of_c_%s\n" % part for part in DEC_ARRAYS[1:] + ["dec_strip", "tr"])
            + tmp("of_ul", 0)
            + block("var:mod1440_of_sel", (
                copy_levels + copy_traits
                + setv("PREV.mod1440_of_c_won", "mod1440_of_won") + setv("PREV.mod1440_of_c_lost", "mod1440_of_lost")
                + setv("PREV.mod1440_of_c_states", "mod1440_of_states")
                + setv("PREV.mod1440_of_c_vps", "mod1440_of_vps") + setv("PREV.mod1440_of_c_vpl", "mod1440_of_vpl")
                # E7: a unit leader's face is the game's (mod1440_of_c_ul); the table for one who is no longer
                + iff("is_unit_leader = yes", tmp("of_ul", 1))
                + els(officer_table(portrait_version) + setv("PREV.mod1440_of_c_p", "mod1440_p"))
                + date_copy("since") + date_copy("prom") + date_copy("lvl")
                + "".join(block("for_each_loop", "array = mod1440_of_%s\nvalue = of_v\nadd_to_array = { PREV.mod1440_of_c_%s = of_v }\n" % (part, part))
                          for part in DEC_ARRAYS[1:])))
            + iff("check_variable = { of_ul = 1 }", "add_to_array = { mod1440_of_c_ul = mod1440_of_sel }\n")
            + "clamp_variable = { var = mod1440_of_c_tr_other min = 0 }\nclamp_variable = { var = mod1440_of_c_tr_over min = 0 }\n"
            + setv("mod1440_of_c_dec_n", "mod1440_of_c_dec_key^num")
            + medal_tokens(sets, "mod1440_of_c_dec_set", "mod1440_of_c_dec_strip", RACK)
            + pad([("mod1440_of_c_dec_key", BLANK), ("mod1440_of_c_dec_date", 0), ("mod1440_of_c_dec_set", -1), ("mod1440_of_c_dec_frame", 1)], RACK)
            + pad([("mod1440_of_c_dec_strip", "token:" + MEDAL_STRIP % sets[0])], RACK)
            + pad([("mod1440_of_c_tr", TRAIT_PAD)], TRAIT_ICONS)
            # which of the medals on offer he holds already, and since when
            + block("for_each_loop", "array = mod1440_md_id\nvalue = md_v\nindex = md_i\n" + tmp("md_h", 0) + tmp("md_d", 0)
                    + block("var:mod1440_of_sel", block("for_each_loop", "array = mod1440_of_dec\nvalue = md_w\nindex = md_j\n" + iff(
                        "check_variable = { md_w = md_v }", tmp("md_h", 1) + tmp("md_d", "mod1440_of_dec_date^md_j"))))
                    + setv("mod1440_md_has^md_i", "md_h") + setv("mod1440_md_date^md_i", "md_d"))
            + "".join("clear_array = mod1440_of_ln_%s\n" % part for part in ("date", "kind", "a", "sa", "fam"))
            + merged(his, his_line)
            + setv("mod1440_of_ln_n", "mod1440_of_ln_date^num")
            + pad([("mod1440_of_ln_date", 0), ("mod1440_of_ln_kind", BLANK), ("mod1440_of_ln_a", 0), ("mod1440_of_ln_sa", 0),
                   ("mod1440_of_ln_fam", 0)], CARD_LINES)))
            + iff("NOT = { %s }" % is_one("mod1440_of_has_sel"), setv("mod1440_of_awarding", 0))
            + "add_to_variable = { mod1440_rec_dirty = 1 }\n")
        + "\n# Officers: the medals the country in scope has, by the game's own conditions (tools/unit_medals_table.py),\n"
        "# %d at most. They fill the Award mode of the file.\n" % MEDAL_SLOTS
        + block("mod1440_md_list", (
            "".join("clear_array = mod1440_md_%s\n" % part for part in ("id", "key", "set", "frame", "strip", "has", "date")) + medals
            + setv("mod1440_md_count", "mod1440_md_id^num")
            + pad([("mod1440_md_id", 0), ("mod1440_md_key", BLANK), ("mod1440_md_set", -1), ("mod1440_md_frame", 1),
                   ("mod1440_md_strip", "token:" + MEDAL_STRIP % sets[0]), ("mod1440_md_has", 0), ("mod1440_md_date", 0)], MEDAL_SLOTS)))
        + "\n# Officers: gives the chosen officer the medal of slot md_k, once. A record of the mod: arrays on the\n"
        "# officer. The War Diary gets a line.\n"
        + block("mod1440_md_award", iff(is_one("mod1440_of_has_sel") + " check_variable = { md_k < mod1440_md_count }", (
            tmp("md_id", "mod1440_md_id^md_k") + tmp("md_key", "mod1440_md_key^md_k") + tmp("md_set", "mod1440_md_set^md_k")
            + tmp("md_frame", "mod1440_md_frame^md_k") + tmp("md_done", 0)
            + block("var:mod1440_of_sel", iff("NOT = { is_in_array = { array = mod1440_of_dec value = md_id } }", (
                "add_to_array = { mod1440_of_dec = md_id }\nadd_to_array = { mod1440_of_dec_key = md_key }\n"
                "add_to_array = { mod1440_of_dec_date = global.date }\nadd_to_array = { mod1440_of_dec_set = md_set }\n"
                "add_to_array = { mod1440_of_dec_frame = md_frame }\n" + tmp("md_done", 1) + "mod1440_of_rack = yes\n")))
            + iff("check_variable = { md_done = 1 }", line("decorated", a="mod1440_of_sel"))
            + "mod1440_of_card = yes\n")))
        + block("mod1440_md_takeback", iff(is_one("mod1440_of_has_sel"), (
            block("var:mod1440_of_sel", iff("check_variable = { mod1440_of_dec^num > 0 }", (
                tmp("md_n", "mod1440_of_dec^num") + "subtract_from_temp_variable = { md_n = 1 }\n"
                + "".join("remove_from_array = { array = mod1440_of_%s index = md_n }\n" % part for part in DEC_ARRAYS)
                + "mod1440_of_rack = yes\n")))
            + "mod1440_of_card = yes\n"))))

    # ---- hooks: the officer is the scope, FROM his country (X43)
    human = "FROM = { is_ai = no }"

    def dated(name, kind, n=None):
        # an officer without a number whose place is not known yet: it is looked for before the line is written
        return iff(human, setv("mod1440_of_%s" % name, "global.date") + setv("mod1440_of_%s_day" % name, "global.num_days")
                   + "mod1440_of_me = yes\n"
                   + iff("check_variable = { of_me = 0 }", block("FROM", "mod1440_of_refs = yes\n") + "mod1440_of_me = yes\n")
                   + iff("NOT = { check_variable = { of_me = 0 } }", fill(kind, a="of_me", n=n) + block("FROM", "mod1440_ev_add = yes\n")))

    hooks = {
        "on_unit_leader_created": dated("since", "commissioned"),
        "on_army_leader_promoted": dated("prom", "promoted"),
        "on_unit_leader_level_up": dated("lvl", "level", n="skill_level"),     # part n: the level reached
        "on_army_leader_won_combat": iff(human, "add_to_variable = { mod1440_of_won = 1 }\n"),
        "on_army_leader_lost_combat": iff(human, "add_to_variable = { mod1440_of_lost = 1 }\n"),
        "on_navy_leader_won_combat": iff(human, "add_to_variable = { mod1440_of_won = 1 }\n"),
        "on_navy_leader_lost_combat": iff(human, "add_to_variable = { mod1440_of_lost = 1 }\n"),
    }
    return gui, script, script_effects, hooks


# ---------------------------------------------------------------- characters a variable cannot hold as they are

# A variable holds a unit leader as a number the game gave him, and a character who is no unit leader as his
# place in the game's list of characters (Engine Facts X66, X67). A leader whose command came by an effect
# (add_corps_commander_role and its siblings: 125 uses in the game's own files, and how most mods add generals)
# has no number: THIS is REF_NONE for every one of them. He is a character all the same, and his place leads to
# him. So his place is looked for once (he gets a mark, every place is entered until the mark is met) and kept
# on him as mod1440_ch_at. A place lasts as long as the game loads the same characters: after a game update or
# another set of mods the same number is somebody else. That is noticed (the character at the highest place the
# mod keeps no longer says so himself), everybody is found again and every list that holds a place is put right.
REF_NONE = "-21474.83648"       # what a variable holds of a leader without a number
REF_FIRST = "5368.70912"        # the first place: 2^29 hundred-thousandths
REF_STEP = "0.00001"            # from one place to the next
REF_BLOCKS = 120                # how far the list is searched, in thousands of places (a loop ends after 1000 rounds)
COMM_LINES = 8                  # officers first met on one day who get a line of their own in the War Diary


def places():
    here = "check_variable = { mod1440_ch_at = %s }"
    is_place = "check_variable = { %s > 5368 }"
    # a leader without a number: does his place still lead to him, or has he none yet?
    need = tmp("rf_me", "THIS") + iff("check_variable = { rf_me = %s }" % REF_NONE, (
        iff("check_variable = { mod1440_ch_at > 0 }", (
            tmp("rf_r", "mod1440_ch_at") + tmp("rf_ok", 0)
            + block("PREV", block("var:rf_r", iff(here % "rf_r", tmp("rf_ok", 1))))
            + iff("check_variable = { rf_ok = 0 }", tmp("rf_stale", 1))))
        + els(iff("NOT = { has_variable = mod1440_ch_at }", setv("mod1440_ch_probe", 1) + "add_to_temp_variable = { rf_need = 1 }\n"))))
    lost = iff("has_variable = mod1440_ch_probe", "clear_variable = mod1440_ch_probe\n" + setv("mod1440_ch_at", -1))
    step = (
        block("var:rf_c", (
            iff("has_variable = mod1440_ch_probe", (
                "clear_variable = mod1440_ch_probe\n" + setv("mod1440_ch_at", "rf_c")
                + "add_to_temp_variable = { rf_found = 1 }\n" + tmp("rf_top", "rf_c")))
            + iff("check_variable = { mod1440_ch_at > 0 }", (
                iff("NOT = { %s }" % (here % "rf_c"), (
                    "add_to_temp_array = { rf_old = mod1440_ch_at }\nadd_to_temp_array = { rf_new = rf_c }\n" + setv("mod1440_ch_at", "rf_c")))
                + tmp("rf_top", "rf_c")), "else_if")))
        + "add_to_temp_variable = { rf_c = %s }\n" % REF_STEP)
    going = "OR = { check_variable = { rf_stale = 1 } check_variable = { rf_found < rf_need } }"
    out = (
        "# Characters: what a variable can hold of the officer in scope, in of_me. His number, or for a leader without\n"
        "# one his place; 0 while that is not known.\n"
        + block("mod1440_of_me", tmp("of_me", "THIS") + iff("check_variable = { of_me = %s }" % REF_NONE, (
            tmp("of_me", 0) + iff("check_variable = { mod1440_ch_at > 0 }", tmp("of_me", "mod1440_ch_at")))))
        + "\n# Characters: writes on the character at the place ch_v that he stands there, so that a later day can tell\n"
        "# whether the place is still his. For the scope of a country: a place nobody stands on leaves the scope\n"
        "# where it is, and what THIS is there tells that apart.\n"
        + block("mod1440_ch_mark", iff(is_place % "ch_v", block("var:ch_v", (
            tmp("ch_t", "THIS") + iff("OR = { check_variable = { ch_t = ch_v } check_variable = { ch_t < 0 } }", (
                setv("mod1440_ch_at", "ch_v")
                + iff("check_variable = { ch_v > global.mod1440_ch_top }", setv("global.mod1440_ch_top", "ch_v"))))))))
        + "\n# Characters: for the country in scope, gives every general and admiral without a number his place, and\n"
        "# looks whether the places kept so far still lead to their characters. If not, everybody is found again\n"
        "# (rf_old, rf_new: where each one was and is) and the lists of every country with a record are put right.\n"
        + block("mod1440_of_refs", (
            "mod1440_ch_adopt = yes\n"
            + tmp("rf_stale", 0) + tmp("rf_need", 0) + tmp("rf_found", 0) + "clear_temp_array = rf_old\nclear_temp_array = rf_new\n"
            + iff("check_variable = { global.mod1440_ch_top > 0 }", (
                tmp("rf_r", "global.mod1440_ch_top") + tmp("rf_ok", 0) + block("var:rf_r", iff(here % "rf_r", tmp("rf_ok", 1)))
                + iff("check_variable = { rf_ok = 0 }", tmp("rf_stale", 1))))
            + block("every_army_leader", need) + block("every_navy_leader", need)
            + iff(going, (
                tmp("rf_c", REF_FIRST) + tmp("rf_top", 0)
                + block("for_loop_effect", "start = 0\nend = %d\nvalue = rf_block\n" % REF_BLOCKS + iff(
                    going, block("for_loop_effect", "start = 0\nend = 1000\nvalue = rf_i\n" + step)))
                # one who was not found is not looked for again
                + block("every_army_leader", lost) + block("every_navy_leader", lost)
                + iff("check_variable = { rf_stale = 1 }", (
                    setv("global.mod1440_ch_top", "rf_top")
                    + block("every_country", "limit = { %s }\nmod1440_ch_remap = yes\n" % is_one("mod1440_ev_begun"))))
                + els(iff("check_variable = { rf_top > global.mod1440_ch_top }", setv("global.mod1440_ch_top", "rf_top")))))))
        + "\n# Characters: where the character of the place rm_v stands now, in rm_to: looked up in rf_old and rf_new, and 0\n"
        "# when nobody at that place says it is his (the character is gone, or was never marked).\n"
        + block("mod1440_ch_place", tmp("rm_to", "rm_v") + iff(is_place % "rm_v", (
            tmp("rm_brk", 0)
            + block("for_each_loop", "array = rf_old\nindex = rm_k\nvalue = rm_o\nbreak = rm_brk\n" + iff(
                "check_variable = { rm_o = rm_v }", tmp("rm_to", "rf_new^rm_k") + tmp("rm_brk", 1)))
            + tmp("rm_ok", 0) + block("var:rm_to", iff(here % "rm_to", tmp("rm_ok", 1)))
            + iff("check_variable = { rm_ok = 0 }", tmp("rm_to", 0) + "add_to_temp_variable = { rm_lost = 1 }\n"))))
    )

    def in_array(name, test=None, also=""):
        body = tmp("rm_v", "%s^rm_i" % name) + "mod1440_ch_place = yes\n" + setv("%s^rm_i" % name, "rm_to") + also
        return block("for_loop_effect", "start = 0\nend = %s^num\nvalue = rm_i\n" % name + (iff(test, body) if test else body))

    def in_variable(name):
        return tmp("rm_v", name) + "mod1440_ch_place = yes\n" + setv(name, "rm_to")

    logs = ""
    for log in ("ev", "tr", "kp"):          # kp: the chronicle of marked lines (2026-10-16)
        for part, kind in (("a", "sa"), ("c", "sc")):
            logs += in_array("mod1440_%s_%s" % (log, part), "check_variable = { mod1440_%s_%s^rm_i = 1 }" % (log, kind),
                             iff("check_variable = { rm_to = 0 }", setv("mod1440_%s_%s^rm_i" % (log, kind), 0)))
    offices = "".join(iff(is_one("mod1440_gv_of_%d_has" % k), in_variable("mod1440_gv_of_%d" % k)) for k in range(len(OFFICES)))
    out += (
        "\n# Characters: puts right every place the country in scope keeps, after the game's list of characters has\n"
        "# changed: the people on the lines of both logs, the list of officers, the chosen officer, the offices, the\n"
        "# army chosen on Army Readiness.\n"
        + block("mod1440_ch_remap", (
            tmp("rm_lost", 0) + logs + in_array("mod1440_of_known")
            # an officer who is gone leaves the list
            + "clear_temp_array = rm_keep\n"
            + block("for_each_loop", "array = mod1440_of_known\nvalue = rm_v\n" + iff(
                "NOT = { check_variable = { rm_v = 0 } }", "add_to_temp_array = { rm_keep = rm_v }\n"))
            + "clear_array = mod1440_of_known\n"
            + block("for_each_loop", "array = rm_keep\nvalue = rm_v\nadd_to_array = { mod1440_of_known = rm_v }\n")
            + iff(is_one("mod1440_of_has_sel"), in_variable("mod1440_of_sel")
                  + iff("check_variable = { mod1440_of_sel = 0 }", setv("mod1440_of_has_sel", 0) + "clear_array = mod1440_of_c_ul\n"))
            # --- D2 round 2 --- the army chosen on Army Readiness (tools/build_managers.py), kept as its commander
            + iff(is_one("mod1440_ar_has_sel"), in_variable("mod1440_ar_sel")
                  + iff("check_variable = { mod1440_ar_sel = 0 }", setv("mod1440_ar_has_sel", 0)))
            # the offices: one holder who cannot be found, and the copies are taken again without a line
            + tmp("rm_lost", 0) + in_variable("mod1440_gv_leader") + offices
            + in_array("mod1440_gv_adv") + in_array("mod1440_gv_hc") + in_array("mod1440_gv_rul")
            + iff("check_variable = { rm_lost > 0 }", setv("mod1440_gv_begun", 0))
            # E4 round 2: the heads of government kept on the rows of the wars, at the start and at the end (a head
            # who cannot be found becomes "not recorded")
            + "".join(in_array(name) for name in ("mod1440_wr_lu0", "mod1440_wr_lt0", "mod1440_wr_lt1",
                                                  "mod1440_wo_lu0", "mod1440_wo_lu1", "mod1440_wo_lt0", "mod1440_wo_lt1"))))
    )

    def adopt_array(name, test=None):
        body = tmp("ch_v", "%s^rm_i" % name) + "mod1440_ch_mark = yes\n"
        return block("for_loop_effect", "start = 0\nend = %s^num\nvalue = rm_i\n" % name + (iff(test, body) if test else body))

    adopt = "".join(adopt_array("mod1440_%s_%s" % (log, part), "check_variable = { mod1440_%s_%s^rm_i = 1 }" % (log, kind))
                    for log in ("ev", "tr", "kp") for part, kind in (("a", "sa"), ("c", "sc")))
    out += (
        "\n# Characters: once for a country, marks everybody whose place its lists hold already (a game saved by an\n"
        "# earlier build of the mod).\n"
        + block("mod1440_ch_adopt", iff("NOT = { %s }" % is_one("mod1440_ch_adopted"), (
            setv("mod1440_ch_adopted", 1) + adopt + adopt_array("mod1440_of_known") + "mod1440_gv_marks = yes\n")))
        + "\n# Characters: marks the holders of the offices the Government page keeps.\n"
        + block("mod1440_gv_marks", (
            tmp("ch_v", "mod1440_gv_leader") + "mod1440_ch_mark = yes\n"
            + "".join(iff(is_one("mod1440_gv_of_%d_has" % k), tmp("ch_v", "mod1440_gv_of_%d" % k) + "mod1440_ch_mark = yes\n")
                      for k in range(len(OFFICES)))
            + block("for_each_loop", "array = mod1440_gv_adv\nvalue = ch_v\nmod1440_ch_mark = yes\n")
            + block("for_each_loop", "array = mod1440_gv_hc\nvalue = ch_v\nmod1440_ch_mark = yes\n")
            + block("for_each_loop", "array = mod1440_gv_rul\nvalue = ch_v\nmod1440_ch_mark = yes\n")))
        + "\n"
    )
    return out


# ---------------------------------------------------------------- Government (E3)

# The redesign of 2026-10-16 (e-officers-gov): three columns of cards sized to what they hold. Who rules (the
# head of government at full size, the parties, the laws with their pictures, the heads since the record
# began), who serves (the cabinet and the high command as fixed slots with each advisor's own small portrait
# and role) and the realm (the faction and the subjects as flag tiles, the state and the agency).
GV_COL = (REC_BODY_W - 2 * 12) // 3                 # 542
GV_X = [REC_BODY_X + n * (GV_COL + 12) for n in range(3)]
GV_ROW = 26
GV_IN = GV_COL - 16                                 # a band across a card, 8 from each side
OFFICES = [("army_chief", "is_army_chief", "Chief of the army"), ("navy_chief", "is_navy_chief", "Chief of the navy"),
           ("air_chief", "is_air_chief", "Chief of the air force"), ("theorist", "is_theorist", "Theorist")]
IDEOLOGIES = [("Fascist", "fascism"), ("Democratic", "democratic"), ("Communist", "communism"), ("Neutral", "neutrality")]
# The laws of the vanilla game, by the idea that holds each. Another mod's law reads "another law".
LAWS = [
    ("Economy", ["undisturbed_isolation", "isolation", "civilian_economy", "low_economic_mobilisation", "partial_economic_mobilisation",
                 "war_economy", "tot_economic_mobilisation", "totaler_krieg_economy", "national_defense_state", "new_economic_policy",
                 "new_economic_policy_2", "capital_investment_model", "JAP_war_communism_idea", "SPR_collectivized_society"]),
    ("Trade", ["uncontrolled_exports", "free_trade", "export_focus", "limited_exports", "autarkic_economy", "autarkic_economy_improved",
               "closed_economy", "special_economic_zones"]),
    ("Conscription", ["disarmed_nation", "volunteer_only", "limited_conscription", "extensive_conscription", "service_by_requirement",
                      "all_adults_serve", "scraping_the_barrel", "ETH_chitet_law", "ETH_chitet_law_peace_time", "SWI_citizen_militia_1",
                      "SWI_citizen_militia_2"]),
]
LAW_UNKNOWN = "GFX_idea_unknown"                    # the game's picture of an idea it has none for
SMALL_UNKNOWN = "GFX_idea_unknown"                  # an advisor whose portrait the table does not know (63x63)
GV_SMALL_LARGE = 0.31                               # a large portrait in the place of a small one: 48x65
BEGAN = "before the record"
GV_FIGURES = [("elections", "Elections", ("election",), "Elections held since the record began."),
              ("changes", "Changes of rule", ("party", "government"), "Changes of the ruling party or of the government."),
              ("heads", "New heads", ("leader",), "Heads of government who took office."),
              ("appointed", "Appointments", ("appointed",), "Advisors, chiefs and members of the high command who took office.")]
CABINET_SLOTS = 4       # political advisors (the game gives a country three)
MEMBER_SLOTS = 3        # members of the high command (three in the game)
HEADS_SLOTS = 4         # heads of government the card shows, newest first
HEADS_KEEP = 100        # heads of government the record keeps
SLOT_PARTS = ["", "_since", "_old", "_p", "_r", "_b"]       # holder, since, held when the record began, portrait, role, large
FLAG_TILE = (124, 96)   # a country of the faction or a subject: a plate of 122x90 in a slot of this size


def advisor_table():
    """(character, file, sprite, slot, trait, large) for every advisor role of the game and of the playset."""
    from portraits_table import ADVISORS
    try:
        from portraits_mods_table import ADVISORS as others
    except ImportError:
        others = []
    own = set(row[0] for row in ADVISORS)
    plain_name = re.compile(r"^[A-Za-z0-9_]+$")
    return [row for row in ADVISORS + [row for row in others if row[0] not in own]
            if plain_name.match(row[0]) and plain_name.match(row[4] or "x")]


def advisor_portraits():
    """The script that finds an advisor's small portrait and the role he holds in a slot: one effect per slot,
    mod1440_p_adv_<slot>, in the advisor's scope with PREV his country. It leaves p_tok (the sprite), p_role
    (the text key of the role's trait) and p_big (1: the sprite is a large portrait). Returns the script and
    the version of the table."""
    from portraits_table import TAGS
    rows = advisor_table()
    version = table_version(rows)
    out = ("\n# Advisors (tools/portraits_table.py, ADVISORS): the small portrait and the role of the advisor in scope,\n"
           "# PREV his country, for each kind of seat. %d roles.\n" % len(rows))
    effects = ""
    for slot in ("political_advisor", "high_command", "army_chief", "navy_chief", "air_chief", "theorist"):
        by_file = {}
        for name, source, sprite, where, trait, large in rows:
            if where == slot:
                by_file.setdefault(source, []).append((name, sprite, trait, large))
        own, others = "", ""
        for source in sorted(by_file):
            body = "".join(iff("PREV = { has_character = %s } is_character = %s" % (name, name),
                               # what is not set stays as the effect set it first: the unknown picture, no role, small
                               (tmp("p_tok", "token:" + sprite) if sprite else "") + (tmp("p_role", "token:" + trait) if trait else "")
                               + (tmp("p_big", 1) if large else "") + tmp("p_found", 1), "if" if n == 0 else "else_if")
                           for n, (name, sprite, trait, large) in enumerate(by_file[source]))
            effects += block("mod1440_p_adv_%s_%s" % (slot, source), body)
            call = "mod1440_p_adv_%s_%s = yes\n" % (slot, source)
            if source in TAGS:
                own += iff("PREV = { original_tag = %s }" % source, call, "else_if" if own else "if")
            others += iff("check_variable = { p_found = 0 }", call)
        out += block("mod1440_p_adv_%s" % slot, tmp("p_tok", "token:" + SMALL_UNKNOWN) + tmp("p_role", BLANK) + tmp("p_big", 0) + tmp("p_found", 0)
                     + own + iff("check_variable = { p_found = 0 }", others))
    return out + "\n" + effects, version


def government(portrait_version):
    adv_version = table_version(advisor_table())    # the portraits and roles of advisors (advisor_portraits())
    from laws_table import LAW_PICTURES
    pictures = dict(LAW_PICTURES)
    body, effects, properties = head("gv", 2, "Who rules and who serves. A date is the day the mod first saw the name in office.")
    triggers = ""
    lists = ""
    extra_gui = ""
    bottoms = [REC_BODY_Y] * 3

    def place(column, name, title, inner, height):
        nonlocal body
        body += card("gv_" + name, GV_X[column], bottoms[column], GV_COL, height, title, inner)
        bottoms[column] += height + 12

    def rest(column):
        return REC_BODY_Y + REC_BODY_H - bottoms[column]

    def right(name, words, tip=None):
        """A small text at the right end of a card's title strip."""
        return M.text(name, GV_COL - 14 - 300, 14, 300, B.key(name, words), M.FONT_SMALL, "right", 20,
                      tooltip=B.key(name + "_tt", tip) if tip else None)

    def since(name, x, y, date, old, width, fmt="left", word="", when=""):
        """A date, or the words for an office held when the record began: the widgets and their triggers."""
        out = M.text(name, x, y, width, B.key(name, "%s[?%s.%s]" % (word, date, LONG)), M.FONT_SMALL, fmt, 22)
        out += M.text(name + "_old", x, y, width, B.key("gv_began", BEGAN), M.FONT_SMALL, fmt, 22)
        return out, (block(name + "_visible", when + "check_variable = { %s = 0 }\n" % old)
                     + block(name + "_old_visible", when + "check_variable = { %s = 1 }\n" % old))

    def person(name, x, y, holder, role, began, sprite, big, has, vacant=None, game=False):
        """A seat: the advisor's own small portrait (a large one smaller where the game declares no small one),
        name, role and since when; or the unknown portrait and "vacant". holder etc. are variables, has a
        trigger. Returns the widgets and their triggers. game (E7): a seat that a general or an admiral can hold;
        while he is a unit leader the game draws his face in the place of the large one (the list <name>_gface_grid
        over the array mod1440_<name>_ul, which the daily round fills), and the table's portraits are hidden."""
        nonlocal lists
        out = M.icon(name + "_face", x + 14, y + 2, SMALL_UNKNOWN)
        out += scaled(name + "_big", x + 22, y + 2, UNKNOWN, GV_SMALL_LARGE)
        extra = block(name + "_face", 'image = "[?%s.GetTokenKey]"\n' % sprite) + block(name + "_big", 'image = "[?%s.GetTokenKey]"\n' % sprite)
        table = ""
        if game:
            out += face_grid(name + "_gface_grid", x + 22, y + 2, GV_SMALL_LARGE)
            lists += face_list(name + "_gface_grid", "mod1440_%s_ul" % name, "gv_gface")
            table = "check_variable = { mod1440_%s_ul^num < 1 }\n" % name
        out += M.text(name + "_name", x + 92, y + 6, GV_COL - 92 - 210, B.key(name + "_name", "§Y[?%s.GetName]§!" % holder), M.FONT_LABEL, height=22, fixed=True)
        out += M.text(name + "_role", x + 92, y + 30, GV_COL - 92 - 24, B.key(name + "_role", "[?%s.GetTokenLocalizedKey]" % role), M.FONT_SMALL, height=22, fixed=True)
        piece, more = since(name + "_since", GV_COL - 16 - 190, y + 8, began[0], began[1], 190, "right", "since ", has)
        out += piece
        trig = (block(name + "_face_visible", has + "check_variable = { %s = 0 }\n" % big + table)
                + block(name + "_big_visible", has + "check_variable = { %s = 1 }\n" % big + table)
                + block(name + "_name_visible", has) + block(name + "_role_visible", has) + more)
        if vacant:
            out += scaled(name + "_none", x + 22, y + 2, UNKNOWN, GV_SMALL_LARGE)
            out += M.text(name + "_vacant", x + 92, y + 16, 300, B.key("gv_vacant", "§gvacant§!"), M.FONT_SMALL, height=22)
            trig += block(name + "_none_visible", vacant) + block(name + "_vacant_visible", vacant)
        return out, extra, trig

    # ---- column 1: who rules. The name and the flag, the portrait at full size beside the party and the dates
    inner = M.text("gv_leader", 14, 40, GV_COL - 28 - 100, B.key("gv_leader", "[ROOT.GetLeader]"), M.FONT_TITLE, height=40, fixed=True)
    inner += flag("gv_flag", GV_COL - 14 - 82, 38)
    properties += flown("gv_flag", "ROOT")
    inner += portrait("gv_face", 14, 92)
    properties += shown("gv_face", "mod1440_gv_p")
    for ideology, group in IDEOLOGIES:
        inner += scaled("gv_group_%s" % group, 186, 92, "GFX_ideology_%s_group" % group, 0.6)
        triggers += block("gv_group_%s_visible" % group, "has_government = %s\n" % group)
    inner += M.text("gv_party", 234, 94, GV_COL - 250, B.key("gv_party", "§Y[ROOT.GetRulingParty]§!, [ROOT.GetRulingIdeology]"), M.FONT_LABEL, height=22, fixed=True)
    inner += M.text("gv_party_long", 234, 118, GV_COL - 250, B.key("gv_party_long", "[ROOT.GetRulingPartyLong]"), M.FONT_SMALL, height=22, fixed=True)
    top = 152
    inner += M.text("gv_office_l", 188, top, 110, B.key("gv_office_l", "In office"), M.FONT_SMALL, height=22)
    piece, extra = since("gv_leader_since", 300, top, "mod1440_gv_leader_since", "mod1440_gv_leader_old", GV_COL - 316, word="since ")
    inner += piece
    triggers += extra
    inner += M.text("gv_election_l", 188, top + GV_ROW, 110, B.key("gv_election_l", "Last election"), M.FONT_SMALL, height=22)
    inner += M.text("gv_election", 300, top + GV_ROW, GV_COL - 316, B.key("gv_election", "[ROOT.GetLastElection]"), M.FONT_SMALL, height=22)
    inner += M.text("gv_next_l", 188, top + 2 * GV_ROW, 110, B.key("gv_next_l", "Next election"), M.FONT_SMALL, height=22)
    inner += M.text("gv_next", 300, top + 2 * GV_ROW, GV_COL - 316, B.key("gv_next", "in [?days_until_next_election|0] days"), M.FONT_SMALL, height=22)
    inner += M.text("gv_next_none", 300, top + 2 * GV_ROW, GV_COL - 316, B.key("gv_next_none", "none"), M.FONT_SMALL, height=22)
    triggers += block("gv_next_visible", "check_variable = { days_until_next_election > -1 }\n")
    triggers += block("gv_next_none_visible", "check_variable = { days_until_next_election < 0 }\n")
    sums = ""
    figures = {}
    for name, label, kinds, tip in GV_FIGURES:
        figures[name] = (label, "[?mod1440_gv_n_%s|0]" % name, tip)
        sums += count(*kinds) + setv("mod1440_gv_n_" + name, "ct_sum")
    for n, name in enumerate(("elections", "changes")):
        piece, extra = tile("gv_f_" + name, 186 + n * 171, 238, figures[name][0], figures[name][1], figures[name][2], width=165)
        inner += piece
    place(0, "chief", "Head of government", inner, 316)

    # parties: the group's icon, the name, the leader, the share and a bar as long as it; the ruling party lit
    inner = ""
    for n, (ideology, group) in enumerate(IDEOLOGIES):
        y = 42 + n * 56
        inner += M.icon("gv_p_%d_pick" % n, 8, y - 2, PICK % (GV_IN, 54))
        triggers += block("gv_p_%d_pick_visible" % n, "has_government = %s\n" % group)
        inner += scaled("gv_p_%d_icon" % n, 14, y + 6, "GFX_ideology_%s_group" % group, 0.55)
        inner += M.text("gv_p_%d" % n, 62, y + 2, GV_COL - 62 - 110, B.key("gv_p_%d" % n, "[ROOT.Get%sParty]" % ideology), M.FONT_SMALL, height=22, fixed=True)
        inner += M.text("gv_p_%d_pop" % n, GV_COL - 110, y + 4, 92, B.key("gv_p_%d_pop" % n, "[?party_popularity@%s|%%0]" % group), M.FONT_VALUE, "right", 24)
        inner += M.text("gv_p_%d_who" % n, 62, y + 20, GV_COL - 62 - 110, B.key("gv_p_%d_who" % n, "§Y[ROOT.Get%sLeader]§!" % ideology), M.FONT_SMALL, height=22, fixed=True)
        inner += M.icon("gv_p_%d_bar" % n, 62, y + 40, M.bar_sprite(GV_COL - 80))
        properties += block("gv_p_%d_bar" % n, "frame = mod1440_gv_pop_%d\n" % n)
    place(0, "parties", "Parties", inner, 42 + 4 * 56 + 8)

    # laws: three plates, the kind, the law's own picture, its name
    inner = ""
    for n, (label, ideas) in enumerate(LAWS):
        x = 14 + n * 174
        inner += M.icon("gv_law_%d_bg" % n, x, 42, M.tile_sprite(166, 130))
        inner += M.text("gv_law_%d_l" % n, x + 6, 48, 154, B.key("gv_law_%d_l" % n, "§g%s§!" % label), M.FONT_SMALL, "centre", 20)
        inner += M.icon("gv_law_%d_pic" % n, x + (166 - 64) // 2, 70, LAW_UNKNOWN)
        properties += block("gv_law_%d_pic" % n, 'image = "[?mod1440_gv_law_%d_gfx.GetTokenKey]"\n' % n)
        inner += M.text("gv_law_%d" % n, x + 6, 142, 154, B.key("gv_law_%d" % n, "[?mod1440_gv_law_%d.GetTokenLocalizedKey]" % n), M.FONT_LABEL, "centre", 24, fixed=True)
    place(0, "laws", "Laws", inner, 42 + 130 + 12)

    # the heads of government since the record began, newest first: portrait, name, party, from and to
    inner = right("gv_rul_n", "[?mod1440_gv_rul^num|0] since the record began")
    for k in range(HEADS_SLOTS):
        y = 42 + k * 54
        more = "check_variable = { mod1440_gv_rul^num > %d }\n" % k
        if k == 0:
            inner += M.icon("gv_rul_0_pick", 8, y - 2, PICK % (GV_IN, 52))
            triggers += block("gv_rul_0_pick_visible", more)
        elif k % 2:
            inner += M.icon("gv_rul_%d_bg" % k, 8, y - 2, STRIPE % (GV_IN, 52))
            triggers += block("gv_rul_%d_bg_visible" % k, more)
        inner += portrait("gv_rul_%d_face" % k, 16, y + 1, OF_FACE)
        properties += shown("gv_rul_%d_face" % k, "mod1440_gv_rd_p^%d" % k)
        inner += M.text("gv_rul_%d" % k, 60, y + 4, GV_COL - 60 - 250, B.key("gv_rul_%d" % k, "§Y[?mod1440_gv_rd^%d.GetName]§!" % k), M.FONT_LABEL, height=22, fixed=True)
        triggers += block("gv_rul_%d_face_visible" % k, more) + block("gv_rul_%d_visible" % k, more)
        for g, (ideology, group) in enumerate(IDEOLOGIES, start=1):
            widget = "gv_rul_%d_g%d" % (k, g)
            inner += M.text(widget, 60, y + 26, GV_COL - 60 - 24, B.key(widget, "[ROOT.Get%sParty], %s" % (ideology, ideology)), M.FONT_SMALL, height=22, fixed=True)
            triggers += block(widget + "_visible", more + "check_variable = { mod1440_gv_rd_g^%d = %d }\n" % (k, g))
        for name, words, condition in (
                ("a", "[?mod1440_gv_rd_from^%d.%s] - [?mod1440_gv_rd_to^%d.%s]" % (k, LONG, k, LONG), "check_variable = { mod1440_gv_rd_old^%d = 0 } check_variable = { mod1440_gv_rd_end^%d = 1 }"),
                ("b", "%s - [?mod1440_gv_rd_to^%d.%s]" % (BEGAN, k, LONG), "check_variable = { mod1440_gv_rd_old^%d = 1 } check_variable = { mod1440_gv_rd_end^%d = 1 }"),
                ("c", "since [?mod1440_gv_rd_from^%d.%s]" % (k, LONG), "check_variable = { mod1440_gv_rd_old^%d = 0 } check_variable = { mod1440_gv_rd_end^%d = 0 }"),
                ("d", "%s - today" % BEGAN, "check_variable = { mod1440_gv_rd_old^%d = 1 } check_variable = { mod1440_gv_rd_end^%d = 0 }")):
            widget = "gv_rul_%d_t%s" % (k, name)
            inner += M.text(widget, GV_COL - 16 - 300, y + 6, 300, B.key(widget, words), M.FONT_SMALL, "right", 22)
            triggers += block(widget + "_visible", more + (condition % (k, k)) + "\n")
    place(0, "heads", "Heads of government", inner, rest(0))

    # ---- column 2: who serves. Fixed seats read by written index: an advisor has no scope in a list row (X42)
    def seats(prefix, count, step, top, game=False):
        """count seats of the slot arrays mod1440_gv_<prefix>... Returns the widgets."""
        nonlocal triggers, properties
        out = ""
        for k in range(count):
            y = top + k * step
            has = "check_variable = { mod1440_gv_%s^num > %d }\n" % (prefix, k)
            if k % 2:
                out += M.icon("gv_%s_%d_bg" % (prefix, k), 8, y - 2, STRIPE % (GV_IN, step - 2))
                triggers += block("gv_%s_%d_bg_visible" % (prefix, k), has)
            parts = dict((part, "mod1440_gv_%s_d%s^%d" % (prefix, part, k)) for part in SLOT_PARTS)
            piece, prop, trig = person("gv_%s_%d" % (prefix, k), 0, y, parts[""], parts["_r"], (parts["_since"], parts["_old"]),
                                       parts["_p"], parts["_b"], has, game=game)
            out += piece
            properties += prop
            triggers += trig
        return out

    inner = right("gv_adv_n", "[?mod1440_gv_adv^num|0] appointed")
    inner += seats("adv", CABINET_SLOTS, 76, 44)
    for k in range(CABINET_SLOTS):
        widget = "gv_adv_none_%d" % k
        inner += M.text(widget, 18, 44 + k * 76 + 8, 500, B.key(widget, "§gNo %spolitical advisor is hired.§!" % ("other " if k else "")), M.FONT_SMALL, height=22)
        triggers += block(widget + "_visible", "check_variable = { mod1440_gv_adv^num = %d }\n" % k)
    place(1, "adv", "Cabinet", inner, 44 + CABINET_SLOTS * 76 + 32)

    inner = right("gv_hc_n", "[?mod1440_gv_hc_n|0] appointed")
    for k, (variable, trigger, label) in enumerate(OFFICES):
        y = 42 + k * 92
        holder = "mod1440_gv_of_%d" % k
        has = is_one(holder + "_has") + "\n"
        if k % 2:
            inner += M.icon("gv_of_%d_bg" % k, 8, y - 2, STRIPE % (GV_IN, 90))
        inner += M.text("gv_of_%d_l" % k, 92, y, 300, B.key("gv_of_%d_l" % k, "§g%s§!" % label), M.FONT_SMALL, height=20)
        piece, prop, trig = person("gv_of_%d" % k, 0, y + 18, holder, holder + "_r", (holder + "_since", holder + "_old"), holder + "_p", holder + "_b",
                                   has, "NOT = { %s }\n" % has.strip(), game=True)
        inner += piece
        properties += prop
        triggers += trig
    top = 42 + len(OFFICES) * 92 + 6
    inner += M.text("gv_members_t", 14, top, 300, B.key("gv_members_t", "Members"), M.FONT_CARD, height=30)
    inner += seats("hc", MEMBER_SLOTS, 76, top + 38, game=True)
    inner += M.text("gv_hc_none", 18, top + 46, 500, B.key("gv_hc_none", "§gNobody is appointed.§!"), M.FONT_SMALL, height=22)
    triggers += block("gv_hc_none_visible", "check_variable = { mod1440_gv_hc^num < 1 }\n")
    place(1, "hc", "High command", inner, rest(1))
    # E7: the row of the game's face of a chief or a member who is a unit leader, at the size of the large portrait
    properties += block("gv_gface", GAME_FACE)
    extra_gui += game_face("gv_gface", GV_SMALL_LARGE)

    # ---- column 3: the realm. The faction and the subjects as flag tiles, four to a row
    def countries(name, array, top, height):
        nonlocal lists, extra_gui
        lists += block("gv_%s_grid" % name, 'array = %s\nchange_scope = yes\nentry_container = "mod1440_records_%s_row"\n' % (array, name))
        tile_w, tile_h = FLAG_TILE
        entry = M.icon("gv_%s_row_bg" % name, 0, 0, M.tile_sprite(tile_w - 2, tile_h - 6))
        entry += flag("gv_%s_row_flag" % name, (tile_w - 2 - 82) // 2, 5)
        entry += M.text("gv_%s_row_name" % name, 4, 58, tile_w - 10, B.key("gv_country_tile", "[THIS.GetName]"), M.FONT_SMALL, "centre", 34, fixed=True)
        extra_gui += row("mod1440_records_%s_row" % name, tile_w, tile_h, entry)
        grid = ('gridboxtype = {\n\tname = "gv_%s_grid"\n\tposition = { x = 0 y = 0 }\n\tsize = { width = %d height = 100%%%% }\n'
                '\tslotsize = { width = %d height = %d }\n\tmax_slots_horizontal = 4\n\tadd_horizontal = yes\n\tformat = "UPPER_LEFT"\n}\n'
                % (name, 4 * tile_w, tile_w, tile_h))
        return ('containerWindowType = {\n\tname = "gv_%s_list"\n\tposition = { x = %d y = %d }\n\tsize = { width = %d height = %d }\n'
                '\tverticalScrollbar = "right_vertical_slider"\n\tscroll_wheel_factor = %d\n\tsmooth_scrolling = yes\n%s%s}\n'
                % (name, 14, top, 4 * tile_w + 30, height, tile_h, LIST_BG, M.indent(grid)))

    properties += "".join(block("gv_%s_row_flag" % name, 'image = "[THIS.GetFlag]"\n') for name in ("fac", "sub"))
    inner = right("gv_members_n", "[?mod1440_gv_fac^num|0] members")
    inner += M.text("gv_faction", 14, 40, GV_COL - 28, B.key("gv_faction", "[ROOT.GetFactionName]"), M.FONT_TITLE, height=40, fixed=True)
    inner += M.text("gv_faction_none", 18, 48, GV_COL - 36, B.key("gv_faction_none", "In no faction."), M.FONT_LABEL, height=22)
    inner += M.text("gv_faction_lead", 18, 92, GV_COL - 36, B.key("gv_faction_lead", "led by §Y[?faction_leader.GetNameWithFlag]§!"), M.FONT_LABEL, height=22, fixed=True)
    triggers += block("gv_faction_visible", "is_in_faction = yes\n") + block("gv_faction_none_visible", "is_in_faction = no\n")
    triggers += block("gv_faction_lead_visible", "is_in_faction = yes\n") + block("gv_members_n_visible", "is_in_faction = yes\n")
    inner += countries("fac", "mod1440_gv_fac", 126, 3 * FLAG_TILE[1])
    place(2, "faction", "Faction", inner, 126 + 3 * FLAG_TILE[1] + 26)
    inner = right("gv_subjects_n", "[?mod1440_ev_subjects^num|0]")
    inner += M.text("gv_sub_none", 18, 46, 400, B.key("gv_sub_none", "§gNo subjects.§!"), M.FONT_SMALL, height=22)
    triggers += block("gv_sub_none_visible", "check_variable = { mod1440_ev_subjects^num < 1 }\n")
    inner += countries("sub", "mod1440_ev_subjects", 42, 2 * FLAG_TILE[1])
    place(2, "subjects", "Subjects", inner, 42 + 2 * FLAG_TILE[1] + 50)

    # the state and the agency: the capital, the agency's name, three figures of the record
    inner = M.text("gv_capital_l", 18, 46, 140, B.key("gv_capital_l", "Capital"), M.FONT_SMALL, height=22)
    inner += M.text("gv_capital", 160, 44, GV_COL - 176, B.key("gv_capital", "[ROOT.Capital.GetName]"), M.FONT_LABEL, height=22, fixed=True)
    inner += M.text("gv_agency", 14, 78, GV_COL - 28, B.key("gv_agency", "[ROOT.GetAgency]"), M.FONT_CARD, height=30, fixed=True)
    for n, (name, label, value, tip) in enumerate((("operatives", "Operatives", "[?num_of_operatives|0]", "Operatives your agency has today."),
                                                   ("appointed",) + figures["appointed"], ("heads",) + figures["heads"])):
        piece, extra = tile("gv_f_" + name, 14 + n * 174, 118, label, value, tip, width=166)
        inner += piece
    place(2, "state", "State and intelligence", inner, rest(2))

    gui, script = page_gui("gv", 2, body, lists=lists, effects=effects, triggers=triggers, properties=properties)
    gui += extra_gui

    # ---- script: the daily comparison of offices
    begun = is_one("mod1440_gv_begun")

    def office_array(game, copy, slot):
        """The daily comparison of one array of seats with its copy. A new holder gets today's date, a line in the
        War Diary, and his portrait and role looked up once; a holder kept keeps all three."""
        news = ["mod1440_gv_new" + part for part in SLOT_PARTS]
        lookup = block("var:gv_c", "mod1440_p_adv_%s = yes\n" % slot) + tmp("gv_p", "p_tok") + tmp("gv_r", "p_role") + tmp("gv_b", "p_big")
        return (
            "".join("clear_array = %s\n" % n for n in news)
            + block("for_each_loop", (
                "array = %s\nvalue = gv_c\n" % game + tmp("gv_since", "global.date") + tmp("gv_old", 1) + iff(begun, tmp("gv_old", 0)) + tmp("gv_found", 0)
                + block("for_each_loop", "array = %s\nvalue = gv_o\nindex = gv_j\n" % copy + iff(
                    "check_variable = { gv_o = gv_c }", tmp("gv_found", 1) + tmp("gv_since", "%s_since^gv_j" % copy) + tmp("gv_old", "%s_old^gv_j" % copy)
                    + tmp("gv_p", "%s_p^gv_j" % copy) + tmp("gv_r", "%s_r^gv_j" % copy) + tmp("gv_b", "%s_b^gv_j" % copy)))
                + iff("check_variable = { gv_found = 0 } " + begun, line("appointed", a="gv_c"))
                # a copy of a game saved before the portraits were kept has no portrait: it is looked up now
                + iff("OR = { check_variable = { gv_found = 0 } check_variable = { gv_stale = 1 } }", lookup)
                + "".join("add_to_array = { %s = %s }\n" % (n, v) for n, v in zip(news, ("gv_c", "gv_since", "gv_old", "gv_p", "gv_r", "gv_b")))))
            + block("for_each_loop", "array = %s\nvalue = gv_o\n" % copy + iff(
                "NOT = { is_in_array = { array = %s value = gv_o } } %s" % (game, begun), line("dismissed", a="gv_o")))
            + "".join("clear_array = %s%s\n" % (copy, part) + block(
                "for_each_loop", "array = mod1440_gv_new%s\nvalue = gv_o\nadd_to_array = { %s%s = gv_o }\n" % (part, copy, part))
                for part in SLOT_PARTS))

    def shown_seats(prefix, count):
        """The copy the seats of the page read: the first <count> holders, padded so that a hidden seat reads
        an element that is there."""
        source, target = "mod1440_gv_" + prefix, "mod1440_gv_%s_d" % prefix
        pads = {"": 0, "_since": 0, "_old": 0, "_p": "token:" + SMALL_UNKNOWN, "_r": BLANK, "_b": 0}
        return ("".join("clear_array = %s%s\n" % (target, part) for part in SLOT_PARTS)
                + block("for_each_loop", "array = %s\nvalue = gv_v\nindex = gv_i\n" % source + iff(
                    "check_variable = { gv_i < %d }" % count,
                    "".join("add_to_array = { %s%s = %s%s^gv_i }\n" % (target, part, source, part) for part in SLOT_PARTS)))
                + pad([(target + part, pads[part]) for part in SLOT_PARTS], count))

    offices = ""
    for k, (variable, trigger, label) in enumerate(OFFICES):
        holder = "mod1440_gv_of_%d" % k
        lookup = (tmp("gv_c", holder) + block("var:gv_c", "mod1440_p_adv_%s = yes\n" % variable)
                  + setv(holder + "_p", "p_tok") + setv(holder + "_r", "p_role") + setv(holder + "_b", "p_big"))
        # NOT with two conditions inside means "neither": the test "not this holder already" is written as an OR
        offices += iff("any_character = { %s = yes }" % trigger, iff(
            "OR = { NOT = { %s } NOT = { check_variable = { %s = %s } } }" % (is_one(holder + "_has"), holder, variable), (
                setv(holder, variable) + setv(holder + "_has", 1) + setv(holder + "_since", "global.date") + setv(holder + "_old", 1)
                + iff(begun, setv(holder + "_old", 0) + line("appointed", a=variable)) + lookup))
            + iff("check_variable = { gv_stale = 1 }", lookup, "else_if"))
        offices += els(iff(is_one(holder + "_has"), setv(holder + "_has", 0) + iff(begun, line("dismissed", a=holder))))
        offices += iff(is_one(holder + "_has"), "add_to_temp_variable = { gv_hc_n = 1 }\n")
    laws = ""
    for n, (label, ideas) in enumerate(LAWS):
        laws += setv("mod1440_gv_law_%d" % n, token("gv_law_other", "another law")) + setv("mod1440_gv_law_%d_gfx" % n, "token:" + LAW_UNKNOWN)
        laws += "".join(iff("has_idea = %s" % idea, setv("mod1440_gv_law_%d" % n, "token:" + idea)
                            + setv("mod1440_gv_law_%d_gfx" % n, "token:" + (pictures.get(idea) or LAW_UNKNOWN))) for idea in ideas)
    support = "".join(setv("mod1440_gv_pop_%d" % n, "party_popularity_100@" + group) for n, (ideology, group) in enumerate(IDEOLOGIES))
    # the leader's portrait: looked up when another leader rules, and when the game's list of characters has changed
    face = leader_portrait("THIS", "mod1440_gv_p", portrait_version)
    # the portraits of the heads since the record began, looked up again when the numbers of text keys have moved
    rulers_again = block("for_each_loop", "array = mod1440_gv_rul\nvalue = gv_v\nindex = gv_i\n" + iff(
        "check_variable = { gv_i < mod1440_gv_rul_p^num } NOT = { check_variable = { gv_v = 0 } }",
        tmp("p_tok", "token:" + UNKNOWN) + block("var:gv_v", "mod1440_p_leader = yes\n") + setv("mod1440_gv_rul_p^gv_i", "p_tok")))
    # the heads of government since the record began: a row when another one rules, newest first
    group = tmp("gv_g", 0) + "".join(iff("has_government = %s" % g, tmp("gv_g", n)) for n, (ideology, g) in enumerate(IDEOLOGIES, start=1))
    rul = ["", "_from", "_old", "_to", "_end", "_p", "_g"]
    new_head = (
        iff("check_variable = { mod1440_gv_rul^num > 0 }", setv("mod1440_gv_rul_to^0", "global.date") + setv("mod1440_gv_rul_end^0", 1))
        + group + tmp("gv_cl", "country_leader")
        + "".join("add_to_array = { array = mod1440_gv_rul%s value = %s index = 0 }\n" % (part, value) for part, value in zip(
            rul, ("gv_cl", "mod1440_gv_leader_since", "mod1440_gv_leader_old", 0, 0, "mod1440_gv_p", "gv_g")))
        + iff("check_variable = { mod1440_gv_rul^num > %d }" % HEADS_KEEP, tmp("gv_last", "mod1440_gv_rul^num") + "subtract_from_temp_variable = { gv_last = 1 }\n"
              + "".join("remove_from_array = { array = mod1440_gv_rul%s index = gv_last }\n" % part for part in rul)))
    heads_shown = ("".join("clear_array = mod1440_gv_rd%s\n" % part for part in rul)
                   + block("for_each_loop", "array = mod1440_gv_rul\nvalue = gv_v\nindex = gv_i\n" + iff(
                       "check_variable = { gv_i < %d }" % HEADS_SLOTS,
                       "".join("add_to_array = { mod1440_gv_rd%s = mod1440_gv_rul%s^gv_i }\n" % (part, part) for part in rul)))
                   + pad([("mod1440_gv_rd", 0), ("mod1440_gv_rd_from", 0), ("mod1440_gv_rd_old", 0), ("mod1440_gv_rd_to", 0),
                          ("mod1440_gv_rd_end", 0), ("mod1440_gv_rd_p", "token:" + UNKNOWN), ("mod1440_gv_rd_g", 0)], HEADS_SLOTS))
    script_effects = (
        "\n# Government: compares who holds each office with yesterday's copy. A new name gets today's date, a line\n"
        "# in the War Diary, and his portrait and role; a name that is gone a line. The first run only takes the copy.\n"
        "# Then the heads of government since the record began, the laws in force and their pictures, the length\n"
        "# of the parties' bars, the leader's portrait, the seats the page shows and the figures of the record.\n"
        + block("mod1440_gv_daily", (
            tmp("gv_stale", 0) + iff(stale("mod1440_gv_adv_ver", adv_version), tmp("gv_stale", 1) + rulers_again)
            + iff("NOT = { check_variable = { mod1440_gv_leader = country_leader } }", (
                setv("mod1440_gv_leader", "country_leader") + setv("mod1440_gv_leader_since", "global.date") + setv("mod1440_gv_leader_old", 1)
                + iff(begun, setv("mod1440_gv_leader_old", 0) + line("leader", a="country_leader"))))
            + face
            + iff("OR = { check_variable = { mod1440_gv_rul^num < 1 } NOT = { check_variable = { mod1440_gv_rul^0 = country_leader } } }", new_head)
            + tmp("gv_hc_n", 0) + offices
            + office_array("political_advisor", "mod1440_gv_adv", "political_advisor") + office_array("high_command", "mod1440_gv_hc", "high_command")
            + "add_to_temp_variable = { gv_hc_n = mod1440_gv_hc^num }\n" + setv("mod1440_gv_hc_n", "gv_hc_n")
            + shown_seats("adv", CABINET_SLOTS) + shown_seats("hc", MEMBER_SLOTS) + heads_shown
            # E7: the chiefs and the members of the high command who are unit leaders: the game draws their faces
            + "".join("clear_array = mod1440_gv_of_%d_ul\n" % k + iff(is_one("mod1440_gv_of_%d_has" % k), unit_leader_into(
                "mod1440_gv_of_%d" % k, "mod1440_gv_of_%d_ul" % k, "gv_ul")) for k in range(len(OFFICES)))
            + "".join("clear_array = mod1440_gv_hc_%d_ul\n" % k + iff("check_variable = { mod1440_gv_hc^num > %d }" % k, unit_leader_into(
                "mod1440_gv_hc_d^%d" % k, "mod1440_gv_hc_%d_ul" % k, "gv_ul")) for k in range(MEMBER_SLOTS))
            + laws + support + pad([("mod1440_ct", 0)], len(KINDS) + 8) + sums + setv("mod1440_gv_begun", 1)
            + stamped("mod1440_gv_adv_ver", adv_version)
            + "mod1440_gv_marks = yes\n")))
    return gui, script, script_effects


# ---------------------------------------------------------------- Wars (E4), with the counters of the air war (E5)

# The page, redesign round of 2026-10-28 (scratch/phases/E4/layout.json; the user took every recommendation on
# 2026-10-29): a column of 548 in the steel look (the campaign as a banded table, the wars of today and the finished
# wars, one of the game's war participant plates per war) and the file of the chosen war on the war overview's own
# frame, 1092 wide (gfx/interface/mod1440/wr_file_bg.dds). The window's ground and its frame stay in the card look
# until the other pages move (decision 5).
#
# A war is a group of rows. The record keeps a row per enemy (the save contract); an enemy that fights on the side of
# the enemy of an open row (has_war_together_with), against whom the country has the same role (has_offensive_war_with),
# joins that row's war: grp is the number (id) of the war's first row, and id keeps its meaning for the officers'
# tallies (mod1440_ow_*).
# Casualties: each row keeps both sides' dead in thousands from casualties_inflicted_by: kus ours by this enemy's hand,
# kthem its dead by ours. The reading minus the reading of the row's first day (kus0, kthem0), every day, never
# falling, and once more at the end. `casualties` counted only the wars in progress (X78) and the whole country's loss,
# which made a finished war's dead 0 (fault 1) and every war's the country's whole loss (fault 3).
# Heads of government: both sides' at the start (lu0, lt0) and at the end (lu1, lt1; theirs kept while the war runs),
# with their portraits (pu, pt, text keys) and ideology groups (gu, gt), kept by place (X67) and put right by
# mod1440_ch_remap; nothing of a finished war is looked up today (fault 2).
WR_COL_W = 548
WR_FILE_X = REC_BODY_X + WR_COL_W + 12          # 574
WR_FILE_W = REC_W - 14 - WR_FILE_X              # 1092
WR_PLATE = "GFX_war_participant_entry"          # the game's plate of a war's side: 531x41, green, red, blue
WR_PLATE_W, WR_PLATE_H, WR_ROW = 531, 41, 48
# the four dark slots of the plate: (x, width)
WR_SLOTS = [(268, 50), (320, 73), (396, 72), (471, 49)]
# the three steel cards of the left column: (y, height), each with a head band of 27 (GFX_1440p_WR_<name>, made by
# tools/stretch_background.py from the steel bar)
WR_CARDS = {"campaign": (REC_BODY_Y, 220), "today": (342, 188), "done": (536, 670)}
WR_STEEL_HEAD = 27
WR_LIST_Y = 32                  # the first plate of a list, inside its card
WR_NOW_ROWS, WR_OLD_ROWS = 3, 12
WR_TROW = 24                    # a row of the campaign table and of the file's tables
WR_LINES = 31                   # lines of the War Diary a war's file shows: 10 on the left, 21 (or 13) on the right
WR_LEFT_LINES = 10
WR_RIGHT_SEVERAL = 13           # with the enemies table above them
WR_MARKS = 20                   # marks on the track: the newest lines
WR_COMMANDERS = 5               # officers a file names
WR_FACE = 0.8                   # the portraits of the heads of government: 125x168
WR_SMALL_FACE = 0.22            # an officer: 34x46
WR_ENEMY_ROWS, WR_ENEMY_ROW = 5, 32
# What a row of a war holds. The newer parts stand last: a game saved before them has rows without (see wr_grow).
# id: a number of the war's own, by which an officer keeps what he took in it; ecas0 the enemy's casualties on its
# first day, ecas what they have lost since; for a finished war day0 its first day, oc how it ended (1 peace,
# 2 capitulated, 3 made a subject, 4 annexed, 5 no longer exists, 6 we capitulated, 7 we were made a subject) and fr
# the frame of its plate. cas, cas0, ecas0 and ecas stay in the save and are no longer shown (E4 round 2).
# E4 round 2 (WR_NEW_3, WO_NEW_3): grp the war's number, how it began (1 we declared, 2 they declared, 3 joined, 0 not
# known), kday the day the count of its dead began, kus0/kthem0 the readings of that day, kus/kthem the dead (-1: not
# kept, a war that ended before this build), lu/pu/gu ours and lt/pt/gt theirs, 0 at the start and 1 at the end.
WR_NEW_3 = ["grp", "how", "kday", "kus0", "kthem0", "kus", "kthem", "lu0", "pu0", "gu0", "lt0", "pt0", "gt0", "lt1", "pt1", "gt1"]
WO_NEW_3 = ["grp", "how", "kday", "kus", "kthem", "lu0", "pu0", "gu0", "lu1", "pu1", "gu1", "lt0", "pt0", "gt0", "lt1", "pt1", "gt1"]
WR_PARTS = ["enemy", "since", "day0", "cas0", "taken", "lost", "days", "cas", "capd", "old", "surr", "vpt", "vpl", "id", "ecas0", "ecas"] + WR_NEW_3
WO_PARTS = ["enemy", "since", "until", "days", "cas", "taken", "lost", "outcome", "old", "vpt", "vpl", "id", "day0", "ecas", "oc", "fr"] + WO_NEW_3
WR_NEW = ["vpt", "vpl"]                     # 2026-10-13
WR_NEW_2 = {"wr": ["id", "ecas0", "ecas"], "wo": ["id", "day0", "ecas", "oc", "fr"]}     # 2026-10-16
WO_KEEP = 200
OUTCOMES = [("peace", "Peace"), ("capitulated", "Capitulated"), ("subject", "Made a subject"), ("annexed", "Annexed"), ("gone", "No longer exists"),
            ("we_capitulated", "We capitulated"), ("we_subject", "We were made a subject")]
# the game's icon of each outcome: (sprite, frame, scale), and the plate's frame (1 green, 2 red, 3 blue)
OUTCOME_ICON = {1: ("GFX_peace_conf_icons", 1, 1.3), 2: ("GFX_surrender_icon", 1, 0.85), 3: ("GFX_autonomy_puppet_icon", 1, 0.72),
                4: ("GFX_autonomy_annex_icon", 1, 0.72), 5: ("GFX_autonomy_annex_icon", 1, 0.72), 6: ("GFX_surrender_icon", 2, 0.85),
                7: ("GFX_autonomy_puppet_icon", 1, 0.72)}
OUTCOME_SIZE = {"GFX_peace_conf_icons": (18, 18), "GFX_surrender_icon": (35, 29)}       # others 35x35
DASH = "—"                 # a value the record did not keep
# The campaign, since the record began: (name, label, value, tooltip), the left column's seven, then the right's
WR_CAMPAIGN = [
    ("cas_all", "Casualties, all wars", "[?mod1440_h_cas_sum|1]K", "Your dead of every war since the record began: the running total of National Figures."),
    ("cas_now", "in wars of today", "[?casualties_k|1]K", "Your dead of the wars you fight today, as the game counts them."),
    ("inflicted", "Casualties we inflicted", "[?mod1440_wr_kthem_all|1]K", "The enemies' dead by your hand, summed over every war the record kept them for."),
    ("longest", "Longest war", "[?longest_war_length|0] mo.", "Months of your longest war."),
    ("surrender", "Our surrender", "[?surrender_progress|%0]", "How close your country is to capitulating."),
    ("convoys", "Convoys sunk", "[?convoys_destroyed|0]", "Enemy convoys your country has sunk."),
    ("pride_sunk", "Prides of their fleet sunk", "[?mod1440_ct^%d|0]" % NUMBER["pride_sunk"], "Prides of an enemy fleet your navy sank."),
    ("ws_cas", "War support: casualties", "[?has_casualties_war_support|%1]", "War support lost to casualties."),
    ("ws_con", "War support: convoys", "[?has_convoys_war_support|%1]", "War support lost to sunk convoys."),
    ("ws_bomb", "War support: bombing", "[?has_bombing_war_support|%1]", "War support lost to enemy bombing."),
    ("pride_lost", "Our pride of the fleet lost", "[?mod1440_ct^%d|0]" % NUMBER["pride_lost"], "Times the pride of your fleet was sunk."),
    ("ace_new", "Aces promoted", "[?mod1440_ac_new|0]", "Pilots of yours who became aces."),
    ("ace_lost", "Aces lost", "[?mod1440_ac_lost|0]", "Aces of yours who were killed."),
    ("ace_down", "Enemy aces shot down", "[?mod1440_ac_down|0]", "Enemy aces your air force shot down."),
]
# the file: where things stand on the frame (the top plate, band A, band B, two panels of 510 with strips of 502)
WF_LP, WF_RP, WF_PW = 22, 552, 510
WF_SX = (26, 556)               # the strips and tables of the two panels
WF_SW = 502
WF_TRACK_X, WF_TRACK_W, WF_TRACK_Y = 256, 580, 118
WF_MARK = 20                    # a mark is a text icon of 20x20
WF_SIDE_Y = 158                 # Our side, Their side
WF_PY = 206                     # the portraits
WF_TY = 208                     # the text beside them, rows of 24
WF_FY = 386                     # In this war: its strip, then 4 rows
WF_LY = 516                     # the lower part: commanders, the enemies table, the War Diary
WF_DIARY_Y = 790                # the War Diary under the commanders
WF_RIGHT_Y = WF_LY + 26 + WR_ENEMY_ROWS * WR_ENEMY_ROW + 8      # 710: the War Diary under the enemies table
WF_FACES = {"u": (32, 169), "t": (790, 927)}
WF_TEXT = {"u": ((306, 216), (169, 353), "left"), "t": ((562, 216), (562, 353), "right")}
WF_TALLY = [(334, "st", "States"), (396, "vp", "Points"), (458, "cap", "Capitals")]
INSET = "GFX_1440p_SG_inset_%dx%d"              # the near-black inset of tiled_window_thin_border
IDEOLOGY_SMALL, IDEOLOGY_LARGE = 0.333, 0.667   # the group icon (66x68) beside a name, and in a portrait's place
# the parts of a row of the enemies table (mod1440_we_*), and of the wars of the two lists (mod1440_wv_*, mod1440_wp_*)
WE_PARTS = ["c", "id", "open", "idx", "since", "until", "day0", "end", "oc", "surr", "capd", "kus", "kthem", "st", "sl", "vpt", "vpl", "old", "odd", "pk"]
WV_PARTS = ["g", "c", "first", "n", "d0", "days", "kus", "kthem", "known", "surr", "pk"]
WP_PARTS = ["g", "c", "first", "n", "d0", "year", "kus", "kthem", "known", "oc", "fr", "pk"]
# casualties_inflicted_by asked with numbers from variables (meta_trigger, SCR-054): is the dead of the country
# mod1440_wr_kv by the hand of mod1440_wr_ko more than mod1440_wr_kn thousand?
WR_KT = ('meta_trigger = { text = { [V] = { casualties_inflicted_by = { opponent = [O] thousands > [N] } } } '
         'V = "[?mod1440_wr_kv.GetTag]" O = "[?mod1440_wr_ko.GetTag]" N = "[?mod1440_wr_kn|1]" }')


# A list's container needs a background to cut its rows off and to scroll them: the four lists without one (today's
# and the finished wars, the faction, the subjects) ran on over their cards and took no wheel (fix round 1); every
# list with one scrolls.
LIST_BG = '\tbackground = { name = "Background" quadTextureSprite = "GFX_tiled_window_transparent" }\n'


def war_listing(name, grid, x, y, height, width=WR_PLATE_W, outer=None, step=WR_ROW):
    """A list that scrolls: the rows stand by their own height, the slider beside them."""
    inner = ('gridboxtype = {\n\tname = "%s"\n\tposition = { x = 0 y = 0 }\n\tsize = { width = %d height = 100%%%% }\n'
             '\tslotsize = { width = 1 height = 1 }\n\tadd_horizontal = no\n\tformat = "UPPER_LEFT"\n}\n' % (grid, width))
    return ('containerWindowType = {\n\tname = "%s"\n\tposition = { x = %d y = %d }\n\tsize = { width = %d height = %d }\n'
            '\tverticalScrollbar = "right_vertical_slider"\n\tscroll_wheel_factor = %d\n\tsmooth_scrolling = yes\n%s%s}\n'
            % (name, x, y, outer or (WR_COL_W - x - 2), height, step * 2, LIST_BG, indent_gui(inner)))


def indent_gui(text):
    return M.indent(text)


def icon_frame(name, x, y, sprite, frame, scale=None, tooltip=None):
    """An icon of one frame of a strip, written in the file."""
    extra = (" scale = %s" % scale if scale else "") + (' pdx_tooltip = "%s"' % tooltip if tooltip else "")
    return 'iconType = { name = "%s" position = { x = %d y = %d } spriteType = "%s" frame = %d%s }\n' % (name, x, y, sprite, frame, extra)


def outcome_icons(prefix, cx, cy, variable, triggers_for):
    """The game's icon of each way a war can end, centred on (cx, cy), each shown when <variable> holds its number."""
    out, triggers = "", ""
    for oc, (sprite, frame, scale) in sorted(OUTCOME_ICON.items()):
        widget = "%s_%d" % (prefix, oc)
        w, h = OUTCOME_SIZE.get(sprite, (35, 35))
        w, h = int(w * scale), int(h * scale)
        out += icon_frame(widget, cx - w // 2, cy - h // 2, sprite, frame, scale, B.key("wr_out_%s_tt" % OUTCOMES[oc - 1][0], OUTCOMES[oc - 1][1]))
        triggers += block(widget + "_visible", triggers_for + "check_variable = { %s = %d }\n" % (variable, oc))
    return out, triggers


def steel_card(name, title, inner, right=None):
    """A steel card of the left column (WR_CARDS): its bitmap, the title in its head band, what it holds."""
    y, h = WR_CARDS[name]
    out = M.icon("wr_%s_bg" % name, 0, 0, "GFX_1440p_WR_" + name)
    out += M.text("wr_%s_title" % name, 12, 4, 260, B.key("wr_%s_title" % name, title), M.FONT_LABEL, height=22)
    if right:
        out += M.text("wr_%s_right" % name, 284, 4, 248, B.key("wr_%s_right" % name, right), M.FONT_LABEL, "right", 22)
    return M.box("wr_" + name, REC_BODY_X, y, WR_COL_W, h, out + inner)


def wars(portrait_version):
    body, effects, properties = head("wr", 3)
    triggers = ""

    # ---- the campaign: fourteen figures as a banded table, two pairs of label and value a row
    inner = "".join(M.icon("wr_campaign_band_%d" % n, 8, WR_LIST_Y + n * WR_TROW, STRIPE % (532, WR_TROW)) for n in (1, 3, 5))
    for n, (name, label, value, tip) in enumerate(WR_CAMPAIGN):
        col, r = divmod(n, 7)
        y = WR_LIST_Y + r * WR_TROW
        lx, lw, vx, vw = ((16, 168, 186, 66), (276, 180, 456, 76))[col]
        tooltip = B.key("wr_f_%s_tt" % name, tip)
        inner += M.text("wr_f_%s_l" % name, lx, y + 2, lw, B.key("wr_f_%s_l" % name, label), M.FONT_LABEL, height=22, tooltip=tooltip)
        inner += M.text("wr_f_" + name, vx, y + 1, vw, B.key("wr_f_" + name, value), M.FONT_VALUE, "right", 22, tooltip=tooltip)
    body += steel_card("campaign", "The campaign", inner, "since the record began")

    def slot_heads(prefix, labels):
        return "".join(M.text("%s_%d" % (prefix, n), 8 + sx, 4, sw, B.key("%s_%d" % (prefix, n), label), M.FONT_LABEL, "centre", 22,
                              tooltip=B.key("%s_%d_tt" % (prefix, n), tip)) for n, ((sx, sw), (label, tip)) in enumerate(zip(WR_SLOTS, labels)))

    dead_tips = [("Our dead", "Casualties: your dead by the hand of this war's enemies."),
                 ("Their dead", "Casualties: the enemies' dead by your hand.")]
    # ---- the wars of today
    inner = slot_heads("wr_now_heads", [("Days", "How long the war has lasted.")] + dead_tips + [
        ("Surr.", "How close the war's first enemy that still fights is to capitulating.")])
    inner += war_listing("wr_now_list", "wr_now_grid", 8, WR_LIST_Y, WR_NOW_ROWS * WR_ROW)
    inner += M.text("wr_now_none", 16, WR_LIST_Y + 12, 480, B.key("wr_now_none", "At peace."), M.FONT_LABEL)
    triggers += block("wr_now_none_visible", "check_variable = { mod1440_wv_g^num < 1 }\n")
    body += steel_card("today", "Wars of today", inner)

    # ---- the finished wars
    old_h = WR_CARDS["done"][1]
    inner = slot_heads("wr_old_heads", [("Began", "The year the war began.")] + dead_tips + [
        ("End", "How it ended for its first enemy: the tooltip says it in words.")])
    inner += war_listing("wr_old_list", "wr_old_grid", 8, WR_LIST_Y, WR_OLD_ROWS * WR_ROW)
    inner += M.text("wr_old_none", 16, WR_LIST_Y + 12, 480, B.key("wr_old_none", "None since the record began."), M.FONT_LABEL)
    inner += M.text("wr_old_note", 12, old_h - 54, WR_COL_W - 24, B.key(
        "wr_old_note", "Green: they gave up. Blue: peace. Red: we gave up. %s: not kept." % DASH), M.FONT_LABEL, height=22,
        tooltip=B.key("wr_old_note_tt", "%s: this war ended before the record kept its dead." % DASH))
    triggers += block("wr_old_none_visible", "check_variable = { mod1440_wp_g^num < 1 }\n")
    body += steel_card("done", "Finished wars", inner)

    # ---- a war of today: its plate, the first enemy's flag and name, "+N" for the others, its figures
    hit = "GFX_1440p_SG_hit_%dx%d" % (WR_PLATE_W, WR_PLATE_H)

    def war_row(p, pre, first_slot, last_slot):
        """The widgets of a plate of the list <pre> (wv or wp), whose row widgets are named <p>_row_*."""
        out = M.icon(p + "_row_pick", 4, 4, PICK % (258, 33))
        out += M.icon(p + "_row_flag", 8, 8, FLAG_SMALL)
        props = flown(p + "_row_flag", "?mod1440_%s_c^i" % pre)
        out += M.text(p + "_row_enemy", 56, 9, 162, B.key(p + "_row_enemy", "§Y[?mod1440_%s_c^i.GetName]§!" % pre), M.FONT_LABEL, height=22, fixed=True)
        out += M.text(p + "_row_more", 222, 9, 36, B.key(p + "_row_more", "+[?mod1440_%s_n^i|0]" % pre), M.FONT_LABEL, "right", 22,
                      tooltip=B.key("wr_row_more_tt", "More enemies in this war: its file lists them."))
        trig = block(p + "_row_more_visible", "check_variable = { mod1440_%s_n^i > 0 }\n" % pre)
        trig += block(p + "_row_pick_visible", "check_variable = { mod1440_%s_pk^i = 1 }\n" % pre)
        sx, sw = WR_SLOTS[0]
        out += M.text(p + "_row_" + first_slot[0], sx + 2, 8, sw - 4, B.key(p + "_row_" + first_slot[0], first_slot[1]), M.FONT_VALUE, "centre", 22)
        if first_slot[2]:
            trig += block(p + "_row_%s_visible" % first_slot[0], first_slot[2])
        known = "check_variable = { mod1440_%s_known^i > 0 }\n" % pre
        for (sx, sw), part in zip(WR_SLOTS[1:3], ("kus", "kthem")):
            out += M.text("%s_row_%s" % (p, part), sx + 2, 8, sw - 4, B.key("%s_row_%s" % (p, part), "[?mod1440_%s_%s^i|1]K" % (pre, part)), M.FONT_VALUE, "centre", 22)
            out += M.text("%s_row_%s_none" % (p, part), sx + 2, 8, sw - 4, B.key("wr_dash", DASH), M.FONT_VALUE, "centre", 22,
                          tooltip=B.key("wr_dash_tt", "Not kept: this war ended before the record kept its dead."))
            trig += block("%s_row_%s_visible" % (p, part), known) + block("%s_row_%s_none_visible" % (p, part), "NOT = { %s }\n" % known.strip())
        return out, props, trig, last_slot

    entry = icon_frame("wr_row_plate", 0, 0, WR_PLATE, 2)
    piece, props, trig, _ = war_row("wr", "wv", ("days", "[?mod1440_wv_days^i|0]", None), None)
    sx, sw = WR_SLOTS[3]
    piece += M.text("wr_row_surr", sx + 2, 8, sw - 4, B.key("wr_row_surr", "[?mod1440_wv_surr^i|0]%"), M.FONT_VALUE, "centre", 22)
    entry += piece + M.button("wr_row", 0, 0, hit, tooltip=B.key("wr_row_tt", "Open the file of this war"))
    properties += props
    triggers += trig
    effects += block("wr_row_click", setv("mod1440_wr_sel_g", "mod1440_wv_g^i") + setv("mod1440_wr_sel_e", 0)
                     + "mod1440_wr_picks = yes\nmod1440_wr_card = yes\n")
    gui_rows = row("mod1440_records_war_row", WR_PLATE_W, WR_ROW, entry)

    # ---- a finished war: the list runs over the frames of the plates (v), the rest is read by the row's index
    entry = M.icon("wo_row_plate", 0, 0, WR_PLATE)
    properties += block("wo_row_plate", "frame = v\n")
    piece, props, trig, _ = war_row("wo", "wp", ("year", "[?mod1440_wp_year^i|0]", "check_variable = { mod1440_wp_year^i > 0 }\n"), None)
    sx, sw = WR_SLOTS[3]
    icons, icon_triggers = outcome_icons("wo_row_end", sx + sw // 2, WR_PLATE_H // 2, "mod1440_wp_oc^i", "")
    entry += piece + icons + M.button("wo_row", 0, 0, hit, tooltip=B.key("wr_row_tt", "Open the file of this war"))
    properties += props
    triggers += trig + icon_triggers
    effects += block("wo_row_click", setv("mod1440_wr_sel_g", "mod1440_wp_g^i") + setv("mod1440_wr_sel_e", 0)
                     + "mod1440_wr_picks = yes\nmod1440_wr_card = yes\n")
    gui_rows += row("mod1440_records_past_war_row", WR_PLATE_W, WR_ROW, entry)

    # ---- the file of the chosen war, on the war overview's frame
    has = is_one("mod1440_wr_c_has") + "\n"
    now = has + "check_variable = { mod1440_wr_c_open = 1 }\n"
    past = has + "check_variable = { mod1440_wr_c_open = 0 }\n"
    known = "check_variable = { mod1440_wr_c_old = 0 }\n"
    one = has + "check_variable = { mod1440_wr_c_count = 1 }\n"
    several = has + "check_variable = { mod1440_wr_c_count > 1 }\n"
    first = "mod1440_wr_c_enemy"
    fw = WR_FILE_W
    mid = fw // 2
    shows = []                                              # what shows for any chosen war
    inner = M.icon("wr_file_bg", 0, 0, "GFX_1440p_SG_war_file")
    inner += M.text("wr_c_none", 60, 220, fw - 120, B.key("wr_c_none", "Click a war in a table to open its file."), M.FONT_LABEL, "centre")
    triggers += block("wr_c_none_visible", "NOT = { %s }\n" % has.strip())
    # the top plate: the war's name (its first enemy), our flag on the left rays and theirs on the right
    inner += M.text("wr_c_title", mid - 235, 18, 470, B.key("wr_c_title", "The war with [?%s.GetName]" % first), M.FONT_CARD, "centre", 30, fixed=True)
    inner += flag("wr_c_flag_us", 80, 8) + flag("wr_c_flag_them", fw - 80 - 82, 8)
    properties += flown("wr_c_flag_us", "ROOT") + flown("wr_c_flag_them", "?" + first)
    shows += ["wr_c_title", "wr_c_flag_us", "wr_c_flag_them"]
    # band A: the two names, "+12" for the other enemies, and between them when it began and ended
    inner += M.text("wr_c_us", 30, 72, 260, B.key("wr_c_us", "[ROOT.GetName]"), M.FONT_CARD, height=30, fixed=True)
    inner += M.text("wr_c_them", fw - 30 - 260, 72, 260, B.key("wr_c_them", "[?%s.GetName]" % first), M.FONT_CARD, "right", 30, fixed=True)
    inner += M.text("wr_c_them_n", fw - 30 - 260, 72, 260, B.key("wr_c_them_n", "[?%s.GetName] +[?mod1440_wr_c_n|0]" % first), M.FONT_CARD, "right", 30, fixed=True)
    shows.append("wr_c_us")
    triggers += block("wr_c_them_visible", one) + block("wr_c_them_n_visible", several)
    since, until = "[?mod1440_wr_c_since.%s]" % LONG, "[?mod1440_wr_c_until.%s]" % LONG
    for name, words, when in (
            ("now", "%s  -  today  -  [?mod1440_wr_c_days|0] days" % since, now + known),
            ("now_old", "%s  -  today  -  [?mod1440_wr_c_days|0] days on record" % BEGAN, now + "check_variable = { mod1440_wr_c_old = 1 }\n"),
            ("past", "%s  -  %s  -  [?mod1440_wr_c_days|0] days" % (since, until), past + known),
            ("past_old", "%s  -  %s" % (BEGAN, until), past + "check_variable = { mod1440_wr_c_old = 1 }\n")):
        inner += M.text("wr_c_when_" + name, mid - 270, 78, 540, B.key("wr_c_when_" + name, words), M.FONT_LABEL, "centre", 22)
        triggers += block("wr_c_when_%s_visible" % name, when)
    # band B: the war day by day, a mark for each of the newest lines of the diary about it. The game's short date
    # carries the hour (X35), so the file's dates are written without it.
    short = "GetDateStringNoHour"
    inner += M.text("wr_c_track_l", 30, WF_TRACK_Y + 3, 120, B.key("wr_c_track_l", "Day by day"), M.FONT_LABEL, height=22)
    inner += M.icon("wr_c_track_frame", WF_TRACK_X - 6, WF_TRACK_Y - 6, "GFX_warscore_progressbar_frame")
    inner += M.icon("wr_c_track", WF_TRACK_X, WF_TRACK_Y, STRIPE % (WF_TRACK_W, 26))
    inner += M.text("wr_c_track_from", WF_TRACK_X - 14 - 100, WF_TRACK_Y + 3, 100, B.key("wr_c_track_from", "[?mod1440_wr_c_day0d.%s]" % short),
                    M.FONT_LABEL, "right", 22)
    inner += M.text("wr_c_track_to", WF_TRACK_X + WF_TRACK_W + 14, WF_TRACK_Y + 3, 120, B.key("wr_c_track_to", "[?mod1440_wr_c_endd.%s]" % short),
                    M.FONT_LABEL, height=22)
    shows += ["wr_c_track_l", "wr_c_track_frame", "wr_c_track", "wr_c_track_from", "wr_c_track_to"]
    for k in range(WR_MARKS):
        tip = B.key("wr_c_mark_%d_tt" % k, "[?mod1440_wr_ln_date^%d.%s]: [?mod1440_wr_ln_kind^%d.GetTokenLocalizedKey]" % (k, LONG, k))
        more = has + "check_variable = { mod1440_wr_ln_n > %d }\n" % k
        for suffix, sprite, test in (("w", "GFX_army_experience", "check_variable = { mod1440_wr_ln_fam^%d = 1 }\n" % k),
                                     ("t", "GFX_victory_points", "NOT = { check_variable = { mod1440_wr_ln_fam^%d = 1 } }\n" % k)):
            widget = "wr_c_mark_%d_%s" % (k, suffix)
            inner += M.icon(widget, WF_TRACK_X + 2, WF_TRACK_Y + 3, sprite).replace(" }\n", ' pdx_tooltip = "%s" }\n' % tip)
            properties += block(widget, "x = mod1440_wr_mx^%d\n" % k)
            triggers += block(widget + "_visible", more + test)

    # the two panels' heads
    inner += M.text("wr_c_side_us", 32, WF_SIDE_Y, 300, B.key("wr_c_side_us", "Our side"), M.FONT_CARD, height=30)
    inner += M.text("wr_c_side_them", 562, WF_SIDE_Y, 300, B.key("wr_c_side_them", "Their side"), M.FONT_CARD, height=30)
    inner += M.text("wr_c_side_n", 852, WF_SIDE_Y + 5, 200, B.key("wr_c_side_n", "[?mod1440_wr_c_count|0] enemies"), M.FONT_LABEL, "right", 22,
                    tooltip=B.key("wr_c_side_n_tt", "The enemies who fought this war on one side: the table below lists them."))
    shows += ["wr_c_side_us", "wr_c_side_them"]
    triggers += block("wr_c_side_n_visible", several)

    # ---- the heads of government of both sides, at the start and at the end (decision 1): two portraits, or one
    # when it was the same person; where the game can name no portrait, the country's flag on a dark inset with the
    # ideology's icon
    def ideology_row(name, x, y, w, align, group_var, when):
        out, trig = "", ""
        for g, (word, group) in enumerate(IDEOLOGIES, start=1):
            widget = "%s_g%d" % (name, g)
            if align == "left":
                out += scaled(widget + "_i", x, y + 1, "GFX_ideology_%s_group" % group, IDEOLOGY_SMALL)
                out += M.text(widget, x + 28, y, w - 28, "%s_noun" % group, M.FONT_LABEL, height=22, fixed=True)
            else:
                out += scaled(widget + "_i", x + w - 22, y + 1, "GFX_ideology_%s_group" % group, IDEOLOGY_SMALL)
                out += M.text(widget, x, y, w - 28, "%s_noun" % group, M.FONT_LABEL, "right", 22, fixed=True)
            trig += shown_if([widget, widget + "_i"], when + "check_variable = { %s = %d }\n" % (group_var, g))
        return out, trig

    def face_box(name, x, s, n, country, when):
        """A portrait 125x168, or the fallback in its place."""
        var = "mod1440_wr_c_%sp%s" % (s, n)
        fb = "check_variable = { mod1440_wr_c_%sfb%s = 1 }\n" % (s, n)
        out = portrait(name, x, WF_PY, WR_FACE)
        props = shown(name, var)
        trig = block(name + "_visible", when + "NOT = { %s }\n" % fb.strip())
        out += scaled(name + "_fb", x, WF_PY, INSET % (125, 168), 1.0, B.key("wr_c_noface_tt", "No portrait the game can name"))
        out += flag(name + "_fb_flag", x + 21, WF_PY + 40)
        props += flown(name + "_fb_flag", country)
        trig += shown_if([name + "_fb", name + "_fb_flag"], when + fb)
        for g, (word, group) in enumerate(IDEOLOGIES, start=1):
            out += scaled("%s_fb_g%d" % (name, g), x + 40, WF_PY + 104, "GFX_ideology_%s_group" % group, IDEOLOGY_LARGE)
            trig += block("%s_fb_g%d_visible" % (name, g), when + fb + "check_variable = { mod1440_wr_c_%sg%s = %d }\n" % (s, n, g))
        return out, props, trig

    for s, country in (("u", "ROOT"), ("t", "?mod1440_wr_c_te")):
        x0, x1 = WF_FACES[s]
        two_at, twin_at, align = WF_TEXT[s]
        twin = "check_variable = { mod1440_wr_c_%stw = 1 }\n" % s
        two = "check_variable = { mod1440_wr_c_%stw = 0 }\n" % s
        live = "check_variable = { mod1440_wr_c_%s = 1 }\n" % ("open" if s == "u" else "topen")
        dead = "check_variable = { mod1440_wr_c_%s = 0 }\n" % ("open" if s == "u" else "topen")
        # the faces: ours, the start at the left and the end beside it; theirs, the end at the right and the start beside it
        if s == "u":
            boxes = [("wr_c_face_u0", x0, "0", has), ("wr_c_face_u1", x1, "1", has + two)]
        else:
            boxes = [("wr_c_face_t0", x0, "0", has + two), ("wr_c_face_t1", x1, "1", has)]
        for name, x, n, when in boxes:
            piece, props, trig = face_box(name, x, s, n, country, when)
            inner += piece
            properties += props
            triggers += trig
        # the text: the country, then who led it when
        for mode, (tx, tw), cond in (("two", two_at, two), ("twin", twin_at, twin)):
            p = "wr_c_%s_%s" % (s, mode)
            when = has + cond
            ry = [WF_TY + r * WR_TROW for r in range(7)]
            name_of = "§Y[ROOT.GetName]§!" if s == "u" else "§Y[?mod1440_wr_c_te.GetName]§!"
            inner += M.text(p + "_c", tx, ry[0], tw, B.key("wr_c_%s_c" % s, name_of), M.FONT_LABEL, align, 22, fixed=True)
            triggers += block(p + "_c_visible", when)
            starts = [("start", "At the start", "")] if mode == "two" else [("live", "At the start and today", live), ("dead", "Throughout the war", dead)]
            for key, words, extra in starts:
                inner += M.text("%s_w_%s" % (p, key), tx, ry[1], tw, B.key("wr_c_w_" + key, words), M.FONT_LABEL, align, 22)
                triggers += block("%s_w_%s_visible" % (p, key), when + extra)
            ends = [("0", 2)] + ([("1", 5)] if mode == "two" else [])
            for n, r in ends:
                nr = "check_variable = { mod1440_wr_c_%snr%s = 1 }\n" % (s, n)
                inner += M.text("%s_l%s" % (p, n), tx, ry[r], tw, B.key("wr_c_%sl%s" % (s, n), "§Y[?mod1440_wr_c_%sl%s.GetName]§!" % (s, n)),
                                M.FONT_LABEL, align, 22, fixed=True)
                inner += M.text("%s_l%s_nr" % (p, n), tx, ry[r], tw, B.key("wr_c_nr", "§gNot recorded§!"), M.FONT_LABEL, align, 22,
                                tooltip=B.key("wr_c_nr_tt", "This war began before the record kept its heads of government."))
                triggers += block("%s_l%s_visible" % (p, n), when + "NOT = { %s }\n" % nr.strip()) + block("%s_l%s_nr_visible" % (p, n), when + nr)
                piece, trig = ideology_row("%s_i%s" % (p, n), tx, ry[r + 1], tw, align, "mod1440_wr_c_%sg%s" % (s, n), when)
                inner += piece
                triggers += trig
            if mode == "two":
                for key, words, extra in (("today", "Today", live), ("end", "At the end", dead)):
                    inner += M.text("%s_w_%s" % (p, key), tx, ry[4], tw, B.key("wr_c_w_" + key, words), M.FONT_LABEL, align, 22)
                    triggers += block("%s_w_%s_visible" % (p, key), when + extra)

    # ---- in this war: four figures on each side, always full
    def strip(name, x, y, words, tooltip=None):
        return (M.icon(name, x, y, layout.head_sprite(WF_SW, 26))
                + M.text(name + "_t", x + 8, y + 2, 400, B.key(name + "_t", words), M.FONT_LABEL, height=22, tooltip=tooltip))

    for s in ("us", "them"):
        sx = WF_SX[0 if s == "us" else 1]
        inner += strip("wr_c_fig_%s" % s, sx, WF_FY, "In this war")
        shows += ["wr_c_fig_%s" % s, "wr_c_fig_%s_t" % s]
        for r in (1, 3):
            inner += M.icon("wr_c_fig_%s_band_%d" % (s, r), sx, WF_FY + 26 + r * WR_TROW, STRIPE % (WF_SW, WR_TROW))
            shows.append("wr_c_fig_%s_band_%d" % (s, r))
    # the player's words, not the script's (gate B): who caused the dead, when they are counted, what is left out
    when_counted = ", counted each day while it runs and once more at its end; the dead no enemy caused (attrition, weather) are not in it."
    dead_tip = {"us": "The dead this war's enemies caused us" + when_counted, "them": "The dead we caused this war's enemies" + when_counted}
    figures = [
        ("us", 0, "kus", "Casualties, by their hand", "[?mod1440_wr_c_kus|1]K", has + "check_variable = { mod1440_wr_c_kunk = 0 }\n", dead_tip["us"]),
        ("us", 1, "taken", "States taken", "[?mod1440_wr_c_taken|0]", has, "States you took from this war's enemies."),
        ("us", 2, "vpt", "Victory points taken", "[?mod1440_wr_c_vpt|0]", has, "Victory points you took from this war's enemies."),
        ("us", 3, "capt", "Capitals taken", "[?mod1440_wr_c_capt|0]", has, "The 'Capital taken' lines of this war in the War Diary."),
        ("them", 0, "kthem", "Casualties, by our hand", "[?mod1440_wr_c_kthem|1]K", has + "check_variable = { mod1440_wr_c_kunk = 0 }\n", dead_tip["them"]),
        ("them", 1, "lost", "States taken from us", "[?mod1440_wr_c_lost|0]", has, "States this war's enemies took from you."),
        ("them", 2, "vpl", "Victory points taken from us", "[?mod1440_wr_c_vpl|0]", has, "Victory points this war's enemies took from you."),
        ("them", 3, "surr", "Surrender", "[?mod1440_wr_c_surr|0]%", one + "check_variable = { mod1440_wr_c_open = 1 }\n",
         "How close the enemy is to capitulating: the war overview's bar."),
        ("them", 3, "end", "How it ended", "[?mod1440_wr_c_outcome.GetTokenLocalizedKey]", one + "check_variable = { mod1440_wr_c_open = 0 }\n",
         "How the war ended, as the War Diary wrote it on its last day."),
        ("them", 3, "gave", "Enemies who gave up", "[?mod1440_wr_c_gave|0] of [?mod1440_wr_c_count|0]", several,
         "The enemies of this war who capitulated, were annexed or made a subject, or are no more."),
    ]
    for s, r, name, label, value, when, tip in figures:
        sx = WF_SX[0 if s == "us" else 1]
        y = WF_FY + 26 + r * WR_TROW
        tooltip = B.key("wr_c_%s_tt" % name, tip)
        inner += M.text("wr_c_%s_l" % name, sx + 10, y + 2, 320, B.key("wr_c_%s_l" % name, label), M.FONT_LABEL, height=22, tooltip=tooltip)
        inner += M.text("wr_c_" + name, sx + 342, y + 1, 150, B.key("wr_c_" + name, value), M.FONT_VALUE, "right", 22, tooltip=tooltip, fixed=True)
        label_when = when if name in ("surr", "end", "gave") else has
        triggers += block("wr_c_%s_l_visible" % name, label_when) + block("wr_c_%s_visible" % name, when)
        if name in ("kus", "kthem"):
            inner += M.text("wr_c_%s_none" % name, sx + 342, y + 1, 150, B.key("wr_dash", DASH), M.FONT_VALUE, "right", 22,
                            tooltip=B.key("wr_dash_tt", "Not kept: this war ended before the record kept its dead."))
            triggers += block("wr_c_%s_none_visible" % name, has + "check_variable = { mod1440_wr_c_kunk = 1 }\n")

    # ---- our commanders in this war: who took its states and points, counted per war on each officer
    sx = WF_SX[0]
    inner += strip("wr_k_head", sx, WF_LY, "Our commanders in this war", B.key(
        "wr_k_head_tt", "The general who had the most divisions in the place when it changed hands; each officer keeps what he took in each war."))
    shows += ["wr_k_head", "wr_k_head_t"]
    for x, part, words in WF_TALLY:
        inner += M.text("wr_k_h_" + part, x, WF_LY + 2, 62, B.key("wr_k_h_" + part, words), M.FONT_LABEL, "centre", 22)
        shows.append("wr_k_h_" + part)
    inner += M.text("wr_k_none", sx + 8, WF_LY + 40, 480, B.key("wr_k_none", "None of your generals has taken a place in this war yet."),
                    M.FONT_LABEL, height=22)
    triggers += block("wr_k_none_visible", has + "check_variable = { mod1440_wr_k_n < 1 }\n")
    game_faces = ""
    properties += block("wr_k_gface", GAME_FACE)
    for k in range(WR_COMMANDERS):
        ry = WF_LY + 26 + k * 48
        more = has + "check_variable = { mod1440_wr_k_n > %d }\n" % k
        names = []
        if k % 2:
            inner += M.icon("wr_k_%d_stripe" % k, sx, ry, STRIPE % (WF_SW, 48))
            names.append("wr_k_%d_stripe" % k)
        # E7: the table's portrait for one who is no unit leader any more; the game's face of one who is, in a list of
        # one row over mod1440_wr_k_<k>_ul (filled with the tally)
        inner += portrait("wr_k_%d_face" % k, sx + 8, ry + 1, WR_SMALL_FACE)
        properties += shown("wr_k_%d_face" % k, "mod1440_wr_k_%d_p" % k)
        triggers += block("wr_k_%d_face_visible" % k, more + "check_variable = { mod1440_wr_k_%d_ul^num < 1 }\n" % k)
        inner += face_grid("wr_k_%d_gface_grid" % k, sx + 8, ry + 1, WR_SMALL_FACE)
        game_faces += face_list("wr_k_%d_gface_grid" % k, "mod1440_wr_k_%d_ul" % k, "wr_k_gface")
        inner += M.text("wr_k_%d" % k, sx + 52, ry + 2, 230, B.key("wr_k_%d" % k, "§Y[?mod1440_wr_k_%d.GetName]§!" % k), M.FONT_LABEL, height=22, fixed=True)
        names += ["wr_k_%d" % k]
        for x, part, words in WF_TALLY:
            inner += M.text("wr_k_%d_%s" % (k, part), x, ry + 12, 62, B.key("wr_k_%d_%s" % (k, part), "[?mod1440_wr_k_%d_%s|0]" % (k, part)),
                            M.FONT_VALUE, "centre", 22)
            names.append("wr_k_%d_%s" % (k, part))
        for rank, words in ((1, "Field Marshal"), (2, "General"), (3, "Admiral")):
            widget = "wr_k_%d_rank_%d" % (k, rank)
            inner += M.text(widget, sx + 52, ry + 24, 230, B.key("wr_k_rank_%d" % rank, words), M.FONT_LABEL, height=22)
            triggers += block(widget + "_visible", more + "check_variable = { mod1440_wr_k_%d_rank = %d }\n" % (k, rank))
        triggers += shown_if(names, more)

    # ---- the War Diary: the war's newest lines in one run, the left column under the commanders, then the right
    # column, under the enemies table (several enemies) or in its place (one)
    def diary_lines(prefix, first, count, x, y, when):
        out, trig = "", ""
        for n in range(count):
            k = first + n
            ly = y + n * WR_TROW
            more = when + "check_variable = { mod1440_wr_ln_n > %d }\n" % k
            names = []
            w = "%s_%d" % (prefix, k)
            if n % 2:
                out += M.icon(w + "_bg", x, ly, STRIPE % (WF_SW, WR_TROW))
                names.append(w + "_bg")
            out += M.text(w + "_d", x + 8, ly + 2, 86, B.key("wr_ln_%d_d" % k, "[?mod1440_wr_ln_date^%d.%s]" % (k, short)), M.FONT_LABEL, height=22)
            out += M.text(w + "_w", x + 90, ly + 1, 26, B.key("wr_ln_icon_w", "£army_experience"), M.FONT_LABEL, height=22)
            out += M.text(w + "_t", x + 90, ly + 1, 26, B.key("wr_ln_icon_t", "£victory_points"), M.FONT_LABEL, height=22)
            trig += block(w + "_w_visible", more + "check_variable = { mod1440_wr_ln_fam^%d = 1 }\n" % k)
            trig += block(w + "_t_visible", more + "NOT = { check_variable = { mod1440_wr_ln_fam^%d = 1 } }\n" % k)
            out += M.text(w, x + 116, ly + 2, 232, B.key("wr_ln_%d" % k, "[?mod1440_wr_ln_kind^%d.GetTokenLocalizedKey]" % k), M.FONT_LABEL, height=22, fixed=True)
            # the place is a button that moves the camera
            out += M.button(w + "_go", x + 354, ly, layout.head_sprite(144, WR_TROW), tooltip=B.key("wd_row_go_tt", "Show this place on the map"))
            out += plain(w + "_s", x + 362, ly + 2, 128, B.key("wr_ln_%d_s" % k, "§Y[?mod1440_wr_ln_a^%d.GetName]§!" % k), height=22)
            out += plain(w + "_p", x + 362, ly + 2, 128, B.key("wr_ln_%d_p" % k, "§Y[?mod1440_wr_ln_a^%d.GetTokenLocalizedKey]§!" % k), height=22)
            trig += block(w + "_go_visible", more + "check_variable = { mod1440_wr_ln_sa^%d > 1 }\n" % k)
            trig += block(w + "_s_visible", more + "check_variable = { mod1440_wr_ln_sa^%d = 2 }\n" % k)
            trig += block(w + "_p_visible", more + "check_variable = { mod1440_wr_ln_sa^%d = 3 }\n" % k)
            # a line about a country and no place (war declared, capitulated): the country, which the war has several of
            out += M.text(w + "_b", x + 362, ly + 2, 128, B.key("wr_ln_%d_b" % k, "§Y[?mod1440_wr_ln_b^%d.GetName]§!" % k), M.FONT_LABEL, height=22, fixed=True)
            trig += block(w + "_b_visible", more + "check_variable = { mod1440_wr_ln_sa^%d < 2 }\n" % k)
            go_effects.append(block(w + "_go_click", tmp("wd_go", "mod1440_wr_ln_a^%d" % k)
                                    + iff("check_variable = { mod1440_wr_ln_sa^%d = 3 }" % k, tmp("wd_go", "mod1440_wr_ln_p^%d" % k))
                                    + block("var:wd_go", block("ROOT", "goto_state = PREV\nmod1440_rec_close = yes\n"))))
            names += [w + "_d", w]
            trig += shown_if(names, more)
        return out, trig

    go_effects = []
    sx0, sx1 = WF_SX
    inner += strip("wr_ln_head", sx0, WF_DIARY_Y, "In the War Diary", B.key("wr_ln_head_tt", "The war's newest lines; a place is a button that shows it on the map."))
    inner += M.button("wr_ln_all", sx0 + WF_SW - 136, WF_DIARY_Y + 1, "GFX_1440p_SG_hit_130x24",
                      tooltip=B.key("wr_ln_all_tt", "The War Diary with every line about the enemy chosen in this file"))
    inner += plain("wr_ln_all_t", sx0 + WF_SW - 208, WF_DIARY_Y + 2, 200, B.key("wr_ln_all_t", "All its lines"), M.FONT_LABEL, "right", 22)
    shows += ["wr_ln_head", "wr_ln_head_t", "wr_ln_all", "wr_ln_all_t"]
    effects += block("wr_ln_all_click", setv("mod1440_wd_filter", WD_COUNTRY_FILTER) + setv("mod1440_wd_country", "mod1440_wr_c_te")
                     + "clear_array = mod1440_wd_back\n" + setv("mod1440_wd_from", 0) + setv("mod1440_rec_page", 0) + "mod1440_rec_show = yes\n")
    inner += M.text("wr_ln_none", sx0 + 8, WF_DIARY_Y + 30, 480, B.key("wr_ln_none", "Nothing yet."), M.FONT_LABEL, height=22)
    triggers += block("wr_ln_none_visible", has + "check_variable = { mod1440_wr_ln_n < 1 }\n")
    piece, trig = diary_lines("wr_ln", 0, WR_LEFT_LINES, sx0, WF_DIARY_Y + 26, has)
    inner += piece
    triggers += trig
    # one enemy: the diary continues at the top of the right column
    inner += strip("wr_l1_head", sx1, WF_LY, "In the War Diary, continued")
    triggers += shown_if(["wr_l1_head", "wr_l1_head_t"], one + "check_variable = { mod1440_wr_ln_n > %d }\n" % WR_LEFT_LINES)
    piece, trig = diary_lines("wr_l1", WR_LEFT_LINES, WR_LINES - WR_LEFT_LINES, sx1, WF_LY + 26, one)
    inner += piece
    triggers += trig
    # several: the enemies table, then the diary under it
    heads_y = WF_LY + 2
    inner += M.icon("wr_en_head", sx1, WF_LY, layout.head_sprite(WF_SW, 26))
    shows_several = ["wr_en_head"]
    for name, x, w, align, words, tip in (
            ("enemy", 50, 120, "left", "Enemy", "Click an enemy for its heads of government."),
            ("joined", 174, 80, "left", "Joined", "The day it entered the war."),
            ("end", 250, 56, "centre", "End", "How it ended (the icon's tooltip says it), or how close it is to capitulating."),
            ("theirs", 296, 76, "right", "Their dead", "Casualties: its dead by your hand."),
            ("ours", 374, 64, "right", "Our dead", "Casualties: your dead by its hand."),
            ("states", 442, 58, "centre", "States", "States taken from it : lost to it.")):
        inner += M.text("wr_en_h_" + name, sx1 + x, heads_y, w, B.key("wr_en_h_" + name, words), M.FONT_LABEL, align, 22,
                        tooltip=B.key("wr_en_h_%s_tt" % name, tip))
        shows_several.append("wr_en_h_" + name)
    inner += war_listing("wr_en_list", "wr_en_grid", sx1, WF_LY + 26, WR_ENEMY_ROWS * WR_ENEMY_ROW, WF_SW, WF_SW + 16, WR_ENEMY_ROW)
    shows_several.append("wr_en_list")
    inner += strip("wr_l2_head", sx1, WF_RIGHT_Y, "In the War Diary, continued")
    triggers += shown_if(shows_several, several)
    triggers += shown_if(["wr_l2_head", "wr_l2_head_t"], several + "check_variable = { mod1440_wr_ln_n > %d }\n" % WR_LEFT_LINES)
    piece, trig = diary_lines("wr_l2", WR_LEFT_LINES, WR_RIGHT_SEVERAL, sx1, WF_RIGHT_Y + 26, several)
    inner += piece
    triggers += trig
    effects += "".join(go_effects)
    triggers += shown_if(shows, has)
    body += M.box("wr_file", WR_FILE_X, REC_BODY_Y, fw, REC_BODY_H, inner)

    # ---- a row of the enemies table: flag, name, when it joined, how it ended, both sides' dead, states
    hit = "GFX_1440p_SG_hit_%dx%d" % (WF_SW, WR_ENEMY_ROW)
    entry = M.icon("wr_en_stripe", 0, 0, STRIPE % (WF_SW, WR_ENEMY_ROW))
    entry += M.icon("wr_en_pick", 0, 0, PICK % (WF_SW, WR_ENEMY_ROW))
    triggers += block("wr_en_stripe_visible", "check_variable = { mod1440_we_odd^i = 1 }\ncheck_variable = { mod1440_we_pk^i = 0 }\n")
    triggers += block("wr_en_pick_visible", "check_variable = { mod1440_we_pk^i = 1 }\n")
    entry += M.icon("wr_en_flag", 4, 3, FLAG_SMALL)
    properties += flown("wr_en_flag", "?mod1440_we_c^i")
    entry += M.text("wr_en_name", 50, 5, 120, B.key("wr_en_name", "§Y[?mod1440_we_c^i.GetName]§!"), M.FONT_LABEL, height=22, fixed=True)
    entry += M.text("wr_en_joined", 174, 5, 80, B.key("wr_en_joined", "[?mod1440_we_since^i.%s]" % short), M.FONT_LABEL, height=22)
    entry += M.text("wr_en_surr", 250, 5, 56, B.key("wr_en_surr", "[?mod1440_we_surr^i|0]%"), M.FONT_LABEL, "centre", 22)
    triggers += block("wr_en_surr_visible", "check_variable = { mod1440_we_open^i = 1 }\n")
    icons, icon_triggers = outcome_icons("wr_en_end", 278, WR_ENEMY_ROW // 2, "mod1440_we_oc^i", "check_variable = { mod1440_we_open^i = 0 }\n")
    entry += icons
    triggers += icon_triggers
    for name, x, w, part in (("theirs", 302, 68, "kthem"), ("ours", 374, 64, "kus")):
        entry += M.text("wr_en_" + name, x, 4, w, B.key("wr_en_" + name, "[?mod1440_we_%s^i|1]K" % part), M.FONT_VALUE, "right", 22)
        entry += M.text("wr_en_%s_none" % name, x, 4, w, B.key("wr_dash", DASH), M.FONT_VALUE, "right", 22,
                        tooltip=B.key("wr_dash_tt", "Not kept: this war ended before the record kept its dead."))
        triggers += block("wr_en_%s_visible" % name, "check_variable = { mod1440_we_kus^i > -1 }\n")
        triggers += block("wr_en_%s_none_visible" % name, "check_variable = { mod1440_we_kus^i < 0 }\n")
    entry += M.text("wr_en_states", 442, 5, 58, B.key("wr_en_states", "[?mod1440_we_st^i|0] : [?mod1440_we_sl^i|0]"), M.FONT_LABEL, "centre", 22)
    entry += M.button("wr_en_row", 0, 0, hit, tooltip=B.key("wr_en_row_tt", "Show this enemy's heads of government"))
    effects += block("wr_en_row_click", setv("mod1440_wr_sel_e", "mod1440_we_id^i") + "mod1440_wr_them = yes\n")
    gui_rows += row("mod1440_records_enemy_row", WF_SW, WR_ENEMY_ROW, entry)

    lists = block("wr_now_grid", 'array = mod1440_wv_g\nentry_container = "mod1440_records_war_row"\n')
    lists += block("wr_old_grid", 'array = mod1440_wp_fr\nentry_container = "mod1440_records_past_war_row"\n')
    lists += block("wr_en_grid", 'array = mod1440_we_c\nentry_container = "mod1440_records_enemy_row"\n')
    lists += game_faces
    gui, script = page_gui("wr", 3, body, lists=lists, effects=effects, triggers=triggers, properties=properties)
    gui += gui_rows + game_face("wr_k_gface", WR_SMALL_FACE)
    return gui, script, wars_script(portrait_version)


def wars_script(portrait_version):
    outcomes = dict((name, token("wr_out_" + name, words)) for name, words in OUTCOMES)
    unknown = "token:" + UNKNOWN
    find = tmp("wr_j", -1) + block("for_each_loop", "array = mod1440_wr_enemy\nvalue = wr_v\nindex = wr_i\n"
                                   + iff("check_variable = { wr_v = wr_c }", tmp("wr_j", "wr_i")))

    def kread(victim, opponent, *prev):
        """Script that reads the dead of <victim> by the hand of <opponent> (in thousands, to 0.1) into kr, searching up
        from the sum of <prev> (yesterday's reading)."""
        out = setv("mod1440_wr_kv", victim) + setv("mod1440_wr_ko", opponent) + tmp("kr_prev", prev[0] if prev else 0)
        out += "".join("add_to_temp_variable = { kr_prev = %s }\n" % p for p in prev[1:])
        return out + "mod1440_wr_kread = yes\n"

    def mark(variable):
        return tmp("ch_v", variable) + "mod1440_ch_mark = yes\n"

    def role(country, out):
        """out: 1 when the country in scope has the offensive war against <country> (it declared, or joined the side that did)."""
        return tmp(out, 0) + iff("has_offensive_war_with = var:%s" % country, tmp(out, 1))

    # ---- a new row: the war it joins, the readings of its first day, the heads of government
    start = {"enemy": "wr_c", "since": "global.date", "day0": "global.num_days", "cas0": 0, "taken": 0, "lost": 0, "days": 0,
             "cas": 0, "capd": 0, "old": "wr_old", "surr": 0, "vpt": 0, "vpl": 0, "id": "mod1440_wr_next", "ecas0": 0, "ecas": 0,
             "grp": "wr_g", "how": "wr_how", "kday": "global.num_days", "kus0": "wr_k0", "kthem0": "wr_t0", "kus": 0, "kthem": 0,
             "lu0": "wr_lu", "pu0": "wr_pu", "gu0": "wr_gu", "lt0": "wr_lt", "pt0": "wr_pt", "gt0": "wr_gt", "lt1": "wr_lt", "pt1": "wr_pt", "gt1": "wr_gt"}
    grouping = (tmp("wr_g", "mod1440_wr_next") + role("wr_c", "wr_r") + tmp("wr_b", 0)
                + block("for_each_loop", "array = mod1440_wr_enemy\nvalue = wr_v\nindex = wr_i\nbreak = wr_b\n" + role("wr_v", "wr_r2")
                        + iff("check_variable = { wr_r2 = wr_r } var:wr_c = { has_war_together_with = var:wr_v }",
                              tmp("wr_g", "mod1440_wr_grp^wr_i") + tmp("wr_b", 1))))
    # the readings of the first day: 0 for a war that ran when the record began (its whole length counts), unless the
    # pair fought a war before, whose dead the game may still count
    baseline = (tmp("wr_k0", 0) + tmp("wr_t0", 0) + iff(
        "var:wr_c = { exists = yes } OR = { check_variable = { wr_old = 0 } is_in_array = { array = mod1440_wo_enemy value = wr_c } }",
        kread("THIS", "wr_c") + tmp("wr_k0", "kr") + kread("wr_c", "THIS") + tmp("wr_t0", "kr")))
    leaders = ("mod1440_wr_hog = yes\n" + tmp("wr_lu", "hg_l") + tmp("wr_pu", "hg_p") + tmp("wr_gu", "hg_g")
               + tmp("wr_lt", 0) + tmp("wr_pt", unknown) + tmp("wr_gt", 0)
               + block("var:wr_c", iff("exists = yes", "mod1440_wr_hog = yes\n" + tmp("wr_lt", "hg_l") + tmp("wr_pt", "hg_p") + tmp("wr_gt", "hg_g")))
               + mark("wr_lu") + mark("wr_lt"))

    # ---- a row that ends
    end = {"enemy": "wr_c", "since": "mod1440_wr_since^wr_j", "until": "global.date", "days": "wr_d", "cas": 0,
           "taken": "mod1440_wr_taken^wr_j", "lost": "mod1440_wr_lost^wr_j", "outcome": "wr_out", "old": "mod1440_wr_old^wr_j",
           "vpt": "mod1440_wr_vpt^wr_j", "vpl": "mod1440_wr_vpl^wr_j", "id": "mod1440_wr_id^wr_j", "day0": "mod1440_wr_day0^wr_j",
           "ecas": "mod1440_wr_ecas^wr_j", "oc": "wr_oc", "fr": "wr_fr",
           "kus": "wr_ku", "kthem": "wr_kt", "lu1": "wr_lu", "pu1": "wr_pu", "gu1": "wr_gu"}
    for part in WO_NEW_3:
        end.setdefault(part, "mod1440_wr_%s^wr_j" % part)

    def keep_higher(base, target, kept):
        """After a reading in kr: the reading minus the row's first one, into <kept> when higher."""
        return (tmp("kr_v", "kr") + "subtract_from_temp_variable = { kr_v = %s }\n" % base + tmp("kr_o", kept)
                + iff("check_variable = { kr_v > kr_o }", setv(target, "kr_v") if target else tmp(kept, "kr_v")))

    last_reading = (tmp("wr_ku", "mod1440_wr_kus^wr_j") + tmp("wr_kt", "mod1440_wr_kthem^wr_j")
                    + iff("var:wr_c = { exists = yes }", (
                        kread("THIS", "wr_c", "mod1440_wr_kus^wr_j", "mod1440_wr_kus0^wr_j") + keep_higher("mod1440_wr_kus0^wr_j", None, "wr_ku")
                        + kread("wr_c", "THIS", "mod1440_wr_kthem^wr_j", "mod1440_wr_kthem0^wr_j") + keep_higher("mod1440_wr_kthem0^wr_j", None, "wr_kt"))))

    # ---- what a save of an earlier build lacks (wr_grow)
    # a game saved before a row counted victory points: the rows that are there get a 0 each
    grow = "".join(iff("check_variable = { mod1440_%s_%s^num < mod1440_%s_enemy^num }" % (table, WR_NEW[0], table), block(
        "for_loop_effect", "start = 0\nend = %d\nvalue = gr_n\n" % WO_KEEP + "".join(
            iff("check_variable = { mod1440_%s_%s^num < mod1440_%s_enemy^num }" % (table, part, table), "add_to_array = { mod1440_%s_%s = 0 }\n" % (table, part))
            for part in WR_NEW))) for table in ("wr", "wo"))
    # ... and one saved before 2026-10-16 rows without a number, the enemy's first casualties, the first day of a
    # finished war and how it ended as a number: each row that is there gets its own number, today's casualties
    # of the enemy, "not known" (-1) for the first day, and its outcome read from the text of before
    gr_new = {
        "wr": {"id": "add_to_variable = { mod1440_wr_next = 1 }\n" + "add_to_array = { mod1440_wr_id = mod1440_wr_next }\n",
               "ecas0": tmp("gr_c", "mod1440_wr_enemy^gr_i") + tmp("gr_e", 0) + block("var:gr_c", tmp("gr_e", "casualties"))
               + "add_to_array = { mod1440_wr_ecas0 = gr_e }\n",
               "ecas": "add_to_array = { mod1440_wr_ecas = 0 }\n"},
        "wo": {"id": "add_to_variable = { mod1440_wr_next = 1 }\n" + "add_to_array = { mod1440_wo_id = mod1440_wr_next }\n",
               "day0": "add_to_array = { mod1440_wo_day0 = -1 }\n", "ecas": "add_to_array = { mod1440_wo_ecas = 0 }\n",
               "oc": (tmp("gr_o", "mod1440_wo_outcome^gr_i") + tmp("gr_oc", 1)
                      + "".join(tmp("gr_t", outcomes[name]) + iff("check_variable = { gr_o = gr_t }", tmp("gr_oc", n))
                                for n, (name, words) in enumerate(OUTCOMES[:5], start=1) if n > 1)
                      + "add_to_array = { mod1440_wo_oc = gr_oc }\n"),
               "fr": (tmp("gr_fr", 1) + iff("check_variable = { mod1440_wo_oc^gr_i = 1 }", tmp("gr_fr", 3))
                      + "add_to_array = { mod1440_wo_fr = gr_fr }\n")},
    }
    for table, parts in WR_NEW_2.items():
        first = parts[0]
        body = tmp("gr_i", "mod1440_%s_%s^num" % (table, first)) + "".join(
            iff("check_variable = { mod1440_%s_%s^num < mod1440_%s_enemy^num }" % (table, part, table), gr_new[table][part]) for part in parts)
        grow += iff("check_variable = { mod1440_%s_%s^num < mod1440_%s_enemy^num }" % (table, first, table),
                    block("for_loop_effect", "start = 0\nend = %d\nvalue = gr_n\n" % WO_KEEP + iff(
                        "check_variable = { mod1440_%s_%s^num < mod1440_%s_enemy^num }" % (table, first, table), body)))

    # ... and one saved before E4 round 2 (2026-10-29): rows per enemy without a war, casualties or leaders.
    def ruler_at(date, out):
        """Our head of government on the date <date> (a date variable), from the Government page's heads since the
        record began (mod1440_gv_rul, newest first, from the day each came): <out>_l, <out>_p, <out>_g; the oldest
        head for a date before the record, today's when the page kept none."""
        return ("mod1440_wr_hog = yes\n" + tmp(out + "_l", "hg_l") + tmp(out + "_p", "hg_p") + tmp(out + "_g", "hg_g")
                + tmp("gr_s", date) + tmp("gr_hit", 0)
                + block("for_each_loop", "array = mod1440_gv_rul\nvalue = gr_v\nindex = gr_k\nbreak = gr_hit\n" + tmp("gr_f", "mod1440_gv_rul_from^gr_k")
                        + iff("NOT = { check_variable = { gr_f > gr_s } }", (
                            tmp(out + "_l", "gr_v") + tmp(out + "_p", "mod1440_gv_rul_p^gr_k") + tmp(out + "_g", "mod1440_gv_rul_g^gr_k") + tmp("gr_hit", 1))))
                + iff("check_variable = { gr_hit = 0 } check_variable = { mod1440_gv_rul^num > 0 }", (
                    tmp("gr_k", "mod1440_gv_rul^num") + "subtract_from_temp_variable = { gr_k = 1 }\n"
                    + tmp(out + "_l", "mod1440_gv_rul^gr_k") + tmp(out + "_p", "mod1440_gv_rul_p^gr_k") + tmp(out + "_g", "mod1440_gv_rul_g^gr_k")))
                + iff("check_variable = { %s_p = 0 }" % out, tmp(out + "_p", unknown)))

    # today's rows: the war by the rule of a new row, over the rows migrated before; the dead from today's reading (the
    # whole war when the pair never fought before); ours at the start from the Government page, theirs not recorded
    wr_body = (
        tmp("gr_i", "mod1440_wr_grp^num") + tmp("gr_c", "mod1440_wr_enemy^gr_i")
        + tmp("gr_g", "mod1440_wr_id^gr_i") + role("gr_c", "gr_r") + tmp("gr_b", 0)
        + block("for_loop_effect", "start = 0\nend = gr_i\nvalue = gr_k\n" + iff("check_variable = { gr_b = 0 }", (
            tmp("gr_v", "mod1440_wr_enemy^gr_k") + role("gr_v", "gr_r2")
            + iff("check_variable = { gr_r2 = gr_r } var:gr_c = { has_war_together_with = var:gr_v }", tmp("gr_g", "mod1440_wr_grp^gr_k") + tmp("gr_b", 1)))))
        + tmp("gr_k0", 0) + tmp("gr_t0", 0) + tmp("gr_kd", "mod1440_wr_day0^gr_i")
        + iff("is_in_array = { array = mod1440_wo_enemy value = gr_c } var:gr_c = { exists = yes }", (
            kread("THIS", "gr_c") + tmp("gr_k0", "kr") + kread("gr_c", "THIS") + tmp("gr_t0", "kr") + tmp("gr_kd", "global.num_days")))
        + ruler_at("mod1440_wr_since^gr_i", "gr_u")
        + tmp("gr_lt", 0) + tmp("gr_pt", unknown) + tmp("gr_gt", 0)
        + block("var:gr_c", iff("exists = yes", "mod1440_wr_hog = yes\n" + tmp("gr_lt", "hg_l") + tmp("gr_pt", "hg_p") + tmp("gr_gt", "hg_g")))
        + mark("gr_u_l") + mark("gr_lt")
        + "".join("add_to_array = { mod1440_wr_%s = %s }\n" % (part, value) for part, value in zip(WR_NEW_3, (
            "gr_g", 0, "gr_kd", "gr_k0", "gr_t0", 0, 0, "gr_u_l", "gr_u_p", "gr_u_g", 0, unknown, 0, "gr_lt", "gr_pt", "gr_gt"))))
    # finished rows: rows that ended on the same day are one war; the dead not kept (-1), unless the enemy was fought
    # once, is not at war with the country now and the game still counts its dead (a reading above 0); ours at both
    # ends from the Government page, theirs not recorded
    wo_body = (
        tmp("gr_i", "mod1440_wo_grp^num") + tmp("gr_c", "mod1440_wo_enemy^gr_i") + tmp("gr_u", "mod1440_wo_until^gr_i")
        + tmp("gr_g", "mod1440_wo_id^gr_i") + tmp("gr_b", 0)
        + block("for_loop_effect", "start = 0\nend = gr_i\nvalue = gr_k\n" + iff("check_variable = { gr_b = 0 }", (
            tmp("gr_v", "mod1440_wo_until^gr_k") + iff("check_variable = { gr_v = gr_u }", tmp("gr_g", "mod1440_wo_grp^gr_k") + tmp("gr_b", 1)))))
        + tmp("gr_ku", -1) + tmp("gr_kt", -1) + tmp("gr_seen", 0)
        + "".join(block("for_each_loop", "array = mod1440_%s_enemy\nvalue = gr_v\n" % t + iff("check_variable = { gr_v = gr_c }", "add_to_temp_variable = { gr_seen = 1 }\n"))
                  for t in ("wo", "wr"))
        + iff("check_variable = { gr_seen = 1 } var:gr_c = { exists = yes } NOT = { has_war_with = var:gr_c }", (
            kread("THIS", "gr_c") + iff("check_variable = { kr > 0 }", tmp("gr_ku", "kr") + kread("gr_c", "THIS") + tmp("gr_kt", "kr"))))
        + ruler_at("mod1440_wo_since^gr_i", "gr_a") + ruler_at("mod1440_wo_until^gr_i", "gr_z")
        + mark("gr_a_l") + mark("gr_z_l")
        + "".join("add_to_array = { mod1440_wo_%s = %s }\n" % (part, value) for part, value in zip(WO_NEW_3, (
            "gr_g", 0, -1, "gr_ku", "gr_kt", "gr_a_l", "gr_a_p", "gr_a_g", "gr_z_l", "gr_z_p", "gr_z_g", 0, unknown, 0, 0, unknown, 0))))
    for table, body in (("wr", wr_body), ("wo", wo_body)):
        missing = "check_variable = { mod1440_%s_grp^num < mod1440_%s_enemy^num }" % (table, table)
        grow += iff(missing, block("for_loop_effect", "start = 0\nend = %d\nvalue = gr_n\n" % WO_KEEP + iff(missing, body))
                    + 'log = "MOD1440 records: the rows of %s were given their wars, casualties and leaders (E4 round 2)"\n' % table)
    # E4 fix round 1: a row whose enemy is the country itself is dropped, once per save (mod1440_wr_fix1), after every part
    # is there; the parts stay as they are, a row leaves all of them as at a peace. An officer's tally of its number is
    # left alone: no war shows it any more.
    drop = tmp("gr_me", "THIS")
    for table, parts in (("wr", WR_PARTS), ("wo", WO_PARTS)):
        drop += tmp("gr_go", 1) + block("while_loop_effect", "limit = { check_variable = { gr_go = 1 } }\n" + (
            tmp("gr_go", 0) + tmp("gr_x", -1) + tmp("gr_b", 0)
            + block("for_each_loop", "array = mod1440_%s_enemy\nvalue = gr_v\nindex = gr_k\nbreak = gr_b\n" % table
                    + iff("check_variable = { gr_v = gr_me }", tmp("gr_x", "gr_k") + tmp("gr_b", 1)))
            + iff("check_variable = { gr_x > -1 }", (
                "".join("remove_from_array = { array = mod1440_%s_%s index = gr_x }\n" % (table, part) for part in parts)
                + tmp("gr_go", 1) + 'log = "MOD1440 records: a row of %s against the country itself was dropped (E4 fix round 1)"\n' % table))))
    grow += iff("NOT = { check_variable = { mod1440_wr_fix1 = 1 } }", setv("mod1440_wr_fix1", 1) + drop + "mod1440_wr_count_wars = yes\n")

    # ---- the portraits kept on the rows, looked up again from the kept leaders when the numbers of the text keys
    # have moved or the table of portraits has changed (SCR-076)
    def relook(table, idx, pairs, theirs):
        out = ""
        for l, p in pairs:
            look = block("var:rl_l", "mod1440_p_leader = yes\n")
            if theirs:
                look = block("var:rl_e", iff("exists = yes", look))
            out += (tmp("rl_l", "mod1440_%s_%s^%s" % (table, l, idx)) + tmp("p_tok", unknown)
                    + iff("NOT = { check_variable = { rl_l = 0 } }", look) + setv("mod1440_%s_%s^%s" % (table, p, idx), "p_tok"))
        return out

    faces_again = iff(stale("mod1440_wr_p_ver", portrait_version), "".join(
        block("for_loop_effect", "start = 0\nend = mod1440_%s_grp^num\nvalue = rl_i\n" % table + tmp("rl_e", "mod1440_%s_enemy^rl_i" % table)
              + relook(table, "rl_i", ours, False) + relook(table, "rl_i", theirs, True))
        for table, ours, theirs in (("wr", [("lu0", "pu0")], [("lt0", "pt0"), ("lt1", "pt1")]),
                                    ("wo", [("lu0", "pu0"), ("lu1", "pu1")], [("lt0", "pt0"), ("lt1", "pt1")])))
        + stamped("mod1440_wr_p_ver", portrait_version))

    # ---- the two lists, one plate per war
    def find_in(array, value, out):
        return tmp(out, -1) + tmp("ls_b", 0) + block("for_each_loop", "array = %s\nvalue = ls_x\nindex = ls_k\nbreak = ls_b\n" % array
                                                     + iff("check_variable = { ls_x = %s }" % value, tmp(out, "ls_k") + tmp("ls_b", 1)))

    def new_war(pre, parts, values):
        return "".join("add_to_array = { mod1440_%s_%s = %s }\n" % (pre, part, values.get(part, 0)) for part in parts) + (
            tmp("ls_j", "mod1440_%s_g^num" % pre) + "subtract_from_temp_variable = { ls_j = 1 }\n")

    def add_up(pre, table, idx, first_extra=""):
        """Row <idx> of <table> counts for war ls_j of the list <pre>: one more enemy, its dead when kept, the first enemy
        (the row with the lowest number) and the first day."""
        return ("add_to_variable = { mod1440_%s_n^ls_j = 1 }\n" % pre
                + tmp("ls_u", "mod1440_%s_kus^%s" % (table, idx)) + tmp("ls_t", "mod1440_%s_kthem^%s" % (table, idx))
                + iff("check_variable = { ls_u > -1 }", (
                    "add_to_variable = { mod1440_%s_kus^ls_j = ls_u }\n" % pre + "add_to_variable = { mod1440_%s_kthem^ls_j = ls_t }\n" % pre
                    + "add_to_variable = { mod1440_%s_known^ls_j = 1 }\n" % pre + "add_to_temp_variable = { ls_all = ls_t }\n"))
                + tmp("ls_id", "mod1440_%s_id^%s" % (table, idx)) + tmp("ls_f", "mod1440_%s_first^ls_j" % pre)
                + iff("check_variable = { ls_id < ls_f }", setv("mod1440_%s_first^ls_j" % pre, "ls_id")
                      + setv("mod1440_%s_c^ls_j" % pre, "mod1440_%s_enemy^%s" % (table, idx)) + first_extra)
                + tmp("ls_d", "mod1440_%s_day0^%s" % (table, idx)) + tmp("ls_e", "mod1440_%s_d0^ls_j" % pre)
                + iff("check_variable = { ls_d > -1 } OR = { check_variable = { ls_e < 0 } check_variable = { ls_d < ls_e } }",
                      setv("mod1440_%s_d0^ls_j" % pre, "ls_d")))

    wp_first = setv("mod1440_wp_oc^ls_j", "mod1440_wo_oc^ls_i") + setv("mod1440_wp_fr^ls_j", "mod1440_wo_fr^ls_i")
    lists = (
        "".join("clear_array = mod1440_wv_%s\n" % part for part in WV_PARTS) + "".join("clear_array = mod1440_wp_%s\n" % part for part in WP_PARTS)
        + tmp("ls_all", 0)
        + block("for_each_loop", "array = mod1440_wr_enemy\nvalue = ls_v\nindex = ls_i\n" + (
            tmp("ls_g", "mod1440_wr_grp^ls_i") + find_in("mod1440_wv_g", "ls_g", "ls_j")
            + iff("check_variable = { ls_j < 0 }", new_war("wv", WV_PARTS, {
                "g": "ls_g", "c": "ls_v", "first": "mod1440_wr_id^ls_i", "n": -1, "d0": "mod1440_wr_day0^ls_i", "surr": "mod1440_wr_surr^ls_i"}))
            + add_up("wv", "wr", "ls_i")))
        + block("for_loop_effect", "start = 0\nend = mod1440_wo_enemy^num\nvalue = ls_i\n" + (
            tmp("ls_g", "mod1440_wo_grp^ls_i") + find_in("mod1440_wv_g", "ls_g", "ls_j")
            + iff("check_variable = { ls_j > -1 }", add_up("wv", "wo", "ls_i"))
            + els(find_in("mod1440_wp_g", "ls_g", "ls_j")
                  + iff("check_variable = { ls_j < 0 }", new_war("wp", WP_PARTS, {
                      "g": "ls_g", "c": "mod1440_wo_enemy^ls_i", "first": "mod1440_wo_id^ls_i", "n": -1, "d0": "mod1440_wo_day0^ls_i",
                      "oc": "mod1440_wo_oc^ls_i", "fr": "mod1440_wo_fr^ls_i"}))
                  + add_up("wp", "wo", "ls_i", wp_first))))
        # the days of a war of today; the year a finished war began (a year is 365 days, day 0 the first of year 0)
        + block("for_loop_effect", "start = 0\nend = mod1440_wv_g^num\nvalue = ls_j\n" + (
            tmp("ls_d", "global.num_days") + "subtract_from_temp_variable = { ls_d = mod1440_wv_d0^ls_j }\n" + setv("mod1440_wv_days^ls_j", "ls_d")))
        + block("for_loop_effect", "start = 0\nend = mod1440_wp_g^num\nvalue = ls_j\n" + (
            tmp("ls_d", "mod1440_wp_d0^ls_j") + iff("check_variable = { ls_d > -1 }", (
                "divide_temp_variable = { ls_d = 365 }\nsubtract_from_temp_variable = { ls_d = 0.499 }\nround_temp_variable = ls_d\n"
                + setv("mod1440_wp_year^ls_j", "ls_d")))))
        + setv("mod1440_wr_kthem_all", "ls_all")
        + "mod1440_wr_picks = yes\n")
    picks = "".join(block("for_loop_effect", "start = 0\nend = mod1440_%s_g^num\nvalue = pk_j\n" % pre + (
        tmp("pk_g", "mod1440_%s_g^pk_j" % pre) + setv("mod1440_%s_pk^pk_j" % pre, 0)
        + iff("check_variable = { pk_g = mod1440_wr_sel_g }", setv("mod1440_%s_pk^pk_j" % pre, 1)))) for pre in ("wv", "wp"))

    # ---- the file of the chosen war: its rows in the order they joined, the war's figures, both sides' heads
    def take_row(table, x):
        src = {"c": "enemy", "id": "id", "since": "since", "day0": "day0", "kus": "kus", "kthem": "kthem", "st": "taken", "sl": "lost",
               "vpt": "vpt", "vpl": "vpl", "old": "old"}
        values = dict((part, "mod1440_%s_%s^%s" % (table, name, x)) for part, name in src.items())
        if table == "wr":
            values.update({"open": 1, "until": "global.date", "end": "global.num_days", "oc": 0, "surr": "mod1440_wr_surr^%s" % x,
                           "capd": "mod1440_wr_capd^%s" % x})
        else:
            values.update({"open": 0, "until": "mod1440_wo_until^%s" % x, "end": "cd_end", "oc": "mod1440_wo_oc^%s" % x, "surr": 0, "capd": 0})
        values.update({"idx": x, "odd": "cd_odd", "pk": 0})
        pre = "" if table == "wr" else (tmp("cd_end", -1) + tmp("cd_d", "mod1440_wo_day0^%s" % x) + iff(
            "check_variable = { cd_d > -1 }", tmp("cd_end", "cd_d") + "add_to_temp_variable = { cd_end = mod1440_wo_days^%s }\n" % x))
        return pre + "".join("add_to_array = { mod1440_we_%s = %s }\n" % (part, values[part]) for part in WE_PARTS)

    gather = (
        "".join("clear_array = mod1440_we_%s\n" % part for part in WE_PARTS)
        + "clear_array = mod1440_wr_t_id\nclear_array = mod1440_wr_t_open\nclear_array = mod1440_wr_t_idx\n"
        + "".join(block("for_loop_effect", "start = 0\nend = mod1440_%s_enemy^num\nvalue = cd_i\n" % table + iff(
            "check_variable = { mod1440_%s_grp^cd_i = mod1440_wr_sel_g }" % table, (
                "add_to_array = { mod1440_wr_t_id = mod1440_%s_id^cd_i }\n" % table + "add_to_array = { mod1440_wr_t_open = %d }\n" % opened
                + "add_to_array = { mod1440_wr_t_idx = cd_i }\n"))) for table, opened in (("wr", 1), ("wo", 0)))
        + tmp("cd_n", "mod1440_wr_t_id^num") + tmp("cd_odd", 0)
        + block("for_loop_effect", "start = 0\nend = cd_n\nvalue = cd_k\n" + (
            block("find_lowest_in_array", "array = mod1440_wr_t_id\nvalue = cd_lo\nindex = cd_at\n")
            + tmp("cd_o", "mod1440_wr_t_open^cd_at") + tmp("cd_x", "mod1440_wr_t_idx^cd_at") + setv("mod1440_wr_t_id^cd_at", 2000000)
            + iff("check_variable = { cd_o = 1 }", take_row("wr", "cd_x")) + els(take_row("wo", "cd_x"))
            + iff("check_variable = { cd_odd = 0 }", tmp("cd_odd", 1)) + els(tmp("cd_odd", 0)))))

    def sum_into(variable, part, test=None):
        body = "add_to_variable = { %s = mod1440_we_%s^cd_k }\n" % (variable, part)
        return iff(test, body) if test else body

    figures = (
        setv("mod1440_wr_c_count", "cd_n") + setv("mod1440_wr_c_n", "cd_n") + "subtract_from_variable = { mod1440_wr_c_n = 1 }\n"
        + setv("mod1440_wr_c_enemy", "mod1440_we_c^0") + setv("mod1440_wr_c_since", "mod1440_we_since^0") + setv("mod1440_wr_c_old", "mod1440_we_old^0")
        + setv("mod1440_wr_c_id", "mod1440_we_id^0")
        + "".join(setv("mod1440_wr_c_" + v, 0) for v in ("open", "kus", "kthem", "taken", "lost", "vpt", "vpl", "gave", "kunk"))
        + setv("mod1440_wr_c_day0", -1) + setv("mod1440_wr_c_endday", -1) + setv("mod1440_wr_c_until", "mod1440_we_until^0")
        + tmp("cd_last", 0) + tmp("cd_known", 0)
        + block("for_loop_effect", "start = 0\nend = cd_n\nvalue = cd_k\n" + (
            iff("check_variable = { mod1440_we_open^cd_k = 1 }", setv("mod1440_wr_c_open", 1))
            + tmp("cd_d", "mod1440_we_day0^cd_k") + tmp("cd_e", "mod1440_wr_c_day0")
            + iff("check_variable = { cd_d > -1 } OR = { check_variable = { cd_e < 0 } check_variable = { cd_d < cd_e } }", setv("mod1440_wr_c_day0", "cd_d"))
            + tmp("cd_d", "mod1440_we_end^cd_k")
            + iff("check_variable = { cd_d > mod1440_wr_c_endday }", setv("mod1440_wr_c_endday", "cd_d") + setv("mod1440_wr_c_until", "mod1440_we_until^cd_k")
                  + tmp("cd_last", "cd_k"))
            + iff("check_variable = { mod1440_we_kus^cd_k > -1 }", sum_into("mod1440_wr_c_kus", "kus") + sum_into("mod1440_wr_c_kthem", "kthem")
                  + "add_to_temp_variable = { cd_known = 1 }\n")
            + sum_into("mod1440_wr_c_taken", "st") + sum_into("mod1440_wr_c_lost", "sl") + sum_into("mod1440_wr_c_vpt", "vpt") + sum_into("mod1440_wr_c_vpl", "vpl")
            + tmp("cd_oc", "mod1440_we_oc^cd_k")
            + iff("OR = { AND = { check_variable = { mod1440_we_open^cd_k = 0 } check_variable = { cd_oc > 1 } check_variable = { cd_oc < 6 } } "
                  "AND = { check_variable = { mod1440_we_open^cd_k = 1 } check_variable = { mod1440_we_capd^cd_k > 0 } } }",
                  "add_to_variable = { mod1440_wr_c_gave = 1 }\n")))
        + iff("check_variable = { cd_known = 0 }", setv("mod1440_wr_c_kunk", 1))
        + iff(is_one("mod1440_wr_c_open"), setv("mod1440_wr_c_endday", "global.num_days") + setv("mod1440_wr_c_until", "global.date"))
        + setv("mod1440_wr_c_days", "mod1440_wr_c_endday") + iff("check_variable = { mod1440_wr_c_day0 > -1 }", "subtract_from_variable = { mod1440_wr_c_days = mod1440_wr_c_day0 }\n")
        + els(setv("mod1440_wr_c_days", 0))
        # a war of one enemy: its surrender (today) or how it ended
        + setv("mod1440_wr_c_surr", "mod1440_we_surr^0") + setv("mod1440_wr_c_outcome", BLANK)
        + iff("check_variable = { mod1440_we_open^0 = 0 }", tmp("cd_x", "mod1440_we_idx^0") + setv("mod1440_wr_c_outcome", "mod1440_wo_outcome^cd_x"))
        # ours: at the war's start from its first row, at its end from the row that ended last, or today's
        + tmp("cd_x", "mod1440_we_idx^0")
        + iff("check_variable = { mod1440_we_open^0 = 1 }", "".join(setv("mod1440_wr_c_u%s0" % k, "mod1440_wr_%su0^cd_x" % p) for k, p in (("l", "l"), ("p", "p"), ("g", "g"))))
        + els("".join(setv("mod1440_wr_c_u%s0" % k, "mod1440_wo_%su0^cd_x" % p) for k, p in (("l", "l"), ("p", "p"), ("g", "g"))))
        + iff(is_one("mod1440_wr_c_open"), "mod1440_wr_hog = yes\n" + setv("mod1440_wr_c_ul1", "hg_l") + setv("mod1440_wr_c_up1", "hg_p") + setv("mod1440_wr_c_ug1", "hg_g"))
        + els(tmp("cd_x", "mod1440_we_idx^cd_last") + "".join(setv("mod1440_wr_c_u%s1" % k, "mod1440_wo_%su1^cd_x" % k) for k in "lpg"))
        + "mod1440_wr_faces_u = yes\n")

    def faces_of(s):
        """Whether side <s> had the same head at both ends, and which portraits the game cannot name."""
        out = tmp("fc_unk", unknown)
        for n in "01":
            p, l = "mod1440_wr_c_%sp%s" % (s, n), "mod1440_wr_c_%sl%s" % (s, n)
            out += iff("check_variable = { %s = 0 }" % p, setv(p, unknown))
            out += setv("mod1440_wr_c_%sfb%s" % (s, n), 0) + iff("check_variable = { %s = fc_unk }" % p, setv("mod1440_wr_c_%sfb%s" % (s, n), 1))
            out += setv("mod1440_wr_c_%snr%s" % (s, n), 0) + iff("check_variable = { %s = 0 }" % l, setv("mod1440_wr_c_%snr%s" % (s, n), 1))
        out += setv("mod1440_wr_c_%stw" % s, 0) + tmp("fc_a", "mod1440_wr_c_%sl0" % s) + tmp("fc_b", "mod1440_wr_c_%sl1" % s)
        # E4 fix round 1: the same person at both ends, or nobody recorded at either (a migrated war): one box
        out += iff("check_variable = { fc_a = fc_b }", setv("mod1440_wr_c_%stw" % s, 1))
        return out

    # their side: the enemy chosen in the table (the war's first by default)
    them = (
        tmp("th_k", -1) + tmp("th_b", 0)
        + block("for_each_loop", "array = mod1440_we_id\nvalue = th_v\nindex = th_i\nbreak = th_b\n" + iff(
            "check_variable = { th_v = mod1440_wr_sel_e }", tmp("th_k", "th_i") + tmp("th_b", 1)))
        + iff("check_variable = { th_k < 0 } check_variable = { mod1440_we_id^num > 0 }", tmp("th_k", 0) + setv("mod1440_wr_sel_e", "mod1440_we_id^0"))
        + iff("check_variable = { th_k > -1 }", (
            block("for_loop_effect", "start = 0\nend = mod1440_we_pk^num\nvalue = th_i\n" + setv("mod1440_we_pk^th_i", 0))
            + setv("mod1440_we_pk^th_k", 1)
            + setv("mod1440_wr_c_te", "mod1440_we_c^th_k") + setv("mod1440_wr_c_topen", "mod1440_we_open^th_k") + tmp("th_x", "mod1440_we_idx^th_k")
            + iff("check_variable = { mod1440_wr_c_topen = 1 }", "".join(setv("mod1440_wr_c_t%s%s" % (k, n), "mod1440_wr_%st%s^th_x" % (k, n)) for k in "lpg" for n in "01"))
            # theirs at the end: the head kept on the row's last day (lt1), today's while the row is open
            + els("".join(setv("mod1440_wr_c_t%s%s" % (k, n), "mod1440_wo_%st%s^th_x" % (k, n)) for k in "lpg" for n in "01"))))
        + faces_of("t"))

    # the lines of the War Diary about this war: a line about one of its enemies written between its first and last day
    def of_this_war(log):
        return ("check_variable = { mod1440_wr_ln_date^num < %d } check_variable = { mod1440_%s_sb^mg_m = 1 } "
                "check_variable = { mod1440_%s_day^mg_m > cd_lo } check_variable = { mod1440_%s_day^mg_m < cd_hi }" % (WR_LINES, log, log, log))

    ln_parts = ("date", "day", "kind", "fam", "a", "sa", "p", "b")

    def war_line(log):
        return (tmp("cd_b", "mod1440_%s_b^mg_m" % log) + iff("is_in_array = { array = mod1440_we_c value = cd_b }", (
            "".join("add_to_array = { mod1440_wr_ln_%s = mod1440_%s_%s^mg_m }\n" % (part, log, part) for part in ("date", "day", "kind", "fam", "p", "b"))
            + iff("check_variable = { mod1440_%s_sa^mg_m > 1 }" % log,
                  "add_to_array = { mod1440_wr_ln_a = mod1440_%s_a^mg_m }\nadd_to_array = { mod1440_wr_ln_sa = mod1440_%s_sa^mg_m }\n" % (log, log))
            + els("add_to_array = { mod1440_wr_ln_a = 0 }\nadd_to_array = { mod1440_wr_ln_sa = 0 }\n"))))

    # the capitals taken in this war: its "Capital taken" lines, which stand in the main log
    capitals = (tmp("cd_cap", 0) + tmp("cd_ck", "token:mod1440_ev_capital_taken")
                + block("for_loop_effect", "start = 0\nend = mod1440_ev_date^num\nvalue = cd_m\n" + iff(
                    "check_variable = { mod1440_ev_kind^cd_m = cd_ck } check_variable = { mod1440_ev_sb^cd_m = 1 } "
                    "check_variable = { mod1440_ev_day^cd_m > cd_lo } check_variable = { mod1440_ev_day^cd_m < cd_hi }",
                    tmp("cd_b", "mod1440_ev_b^cd_m") + iff("is_in_array = { array = mod1440_we_c value = cd_b }", "add_to_temp_variable = { cd_cap = 1 }\n")))
                + setv("mod1440_wr_c_capt", "cd_cap"))

    # the marks of the track: where each line's day stands between the war's first and last day
    span = WF_TRACK_W - 4 - WF_MARK
    marks = (
        "clear_array = mod1440_wr_mx\n"
        + tmp("mx_0", "mod1440_wr_c_day0") + tmp("mx_1", "mod1440_wr_c_endday")
        + iff("check_variable = { mx_0 < 0 } check_variable = { mod1440_wr_ln_n > 0 }", (
            tmp("mx_last", "mod1440_wr_ln_n") + "subtract_from_temp_variable = { mx_last = 1 }\n"
            + tmp("mx_0", "mod1440_wr_ln_day^mx_last") + tmp("mx_1", "mod1440_wr_ln_day^0")))
        + tmp("mx_span", "mx_1") + "subtract_from_temp_variable = { mx_span = mx_0 }\n" + "clamp_temp_variable = { var = mx_span min = 1 }\n"
        + block("for_loop_effect", "start = 0\nend = %d\nvalue = mx_k\n" % WR_MARKS + (
            tmp("mx_x", 0) + iff("check_variable = { mx_k < mod1440_wr_ln_n }", (
                tmp("mx_x", "mod1440_wr_ln_day^mx_k") + "subtract_from_temp_variable = { mx_x = mx_0 }\n"
                + "clamp_temp_variable = { var = mx_x min = 0 max = mx_span }\n"
                + "multiply_temp_variable = { mx_x = %d }\ndivide_temp_variable = { mx_x = mx_span }\nround_temp_variable = mx_x\n" % span))
            + "add_to_temp_variable = { mx_x = %d }\n" % (WF_TRACK_X + 2) + "add_to_array = { mod1440_wr_mx = mx_x }\n")))

    # our commanders in this war: every officer the record knows who keeps a count for one of its rows, the best five
    tally = (
        "".join("clear_array = mod1440_wr_kt_%s\n" % part for part in ("c", "st", "vp", "cap", "score"))
        + "clear_temp_array = kt_ids\n" + block("for_each_loop", "array = mod1440_we_id\nvalue = kt_v\nadd_to_temp_array = { kt_ids = kt_v }\n")
        + block("for_each_scope_loop", "array = mod1440_of_known\n" + (
            tmp("kt_st", 0) + tmp("kt_vp", 0) + tmp("kt_cap", 0) + tmp("kt_any", 0)
            + block("for_each_loop", "array = mod1440_ow_id\nvalue = kt_v\nindex = kt_i\n" + iff("is_in_array = { array = kt_ids value = kt_v }", (
                "add_to_temp_variable = { kt_st = mod1440_ow_st^kt_i }\nadd_to_temp_variable = { kt_vp = mod1440_ow_vp^kt_i }\n"
                "add_to_temp_variable = { kt_cap = mod1440_ow_cap^kt_i }\n" + tmp("kt_any", 1))))
            + iff("check_variable = { kt_any = 1 }", "mod1440_of_me = yes\n" + iff("NOT = { check_variable = { of_me = 0 } }", (
                "add_to_array = { PREV.mod1440_wr_kt_c = of_me }\n"
                + "".join("add_to_array = { PREV.mod1440_wr_kt_%s = kt_%s }\n" % (part, part) for part in ("st", "vp", "cap"))
                + tmp("kt_s", "kt_st") + "multiply_temp_variable = { kt_s = 1000 }\n" + "add_to_temp_variable = { kt_s = kt_vp }\n"
                + "add_to_array = { PREV.mod1440_wr_kt_score = kt_s }\n")))))
        + setv("mod1440_wr_k_n", 0))
    for k in range(WR_COMMANDERS):
        slot = "mod1440_wr_k_%d" % k
        tally += setv(slot, "country_leader") + setv(slot + "_p", unknown) + "".join(setv("%s_%s" % (slot, part), 0) for part in ("st", "vp", "cap", "rank"))
        tally += iff("check_variable = { mod1440_wr_kt_score^num > %d }" % k, (
            block("find_highest_in_array", "array = mod1440_wr_kt_score\nvalue = kt_hi\nindex = kt_at\n")
            + setv(slot, "mod1440_wr_kt_c^kt_at") + "".join(setv("%s_%s" % (slot, part), "mod1440_wr_kt_%s^kt_at" % part) for part in ("st", "vp", "cap"))
            + setv("mod1440_wr_kt_score^kt_at", -1) + "add_to_variable = { mod1440_wr_k_n = 1 }\n"
            + tmp("kt_ul", 0)
            + block("var:" + slot, (
                # E7: a unit leader's face is the game's; the table for one who is no longer
                iff("is_unit_leader = yes", tmp("kt_ul", 1))
                + els(officer_table(portrait_version) + setv("PREV.%s_p" % slot, "mod1440_p"))
                + setv("PREV.%s_rank" % slot, 2)
                + iff("is_field_marshal = yes", setv("PREV.%s_rank" % slot, 1)) + iff("is_navy_leader = yes", setv("PREV.%s_rank" % slot, 3))))
            + iff("check_variable = { kt_ul = 1 }", "add_to_array = { %s_ul = %s }\n" % (slot, slot))))

    card = (
        "mod1440_wr_grow = yes\nmod1440_ev_grow = yes\n" + faces_again + setv("mod1440_wr_c_has", 0)
        # E7: no commander's face until the tally names him
        + "".join("clear_array = mod1440_wr_k_%d_ul\n" % k for k in range(WR_COMMANDERS))
        # with no war chosen the hidden flags and names still ask for a country: the own one
        + "".join(iff("check_variable = { %s = 0 }" % v, setv(v, "THIS")) for v in ("mod1440_wr_c_enemy", "mod1440_wr_c_te"))
        + gather
        + iff("check_variable = { cd_n > 0 }", (
            setv("mod1440_wr_c_has", 1) + figures + "mod1440_wr_them = yes\n"
            + tmp("cd_lo", "mod1440_wr_c_day0") + "subtract_from_temp_variable = { cd_lo = 1 }\n"
            + iff("check_variable = { mod1440_wr_c_day0 < 0 }", tmp("cd_lo", -10))
            + tmp("cd_hi", "mod1440_wr_c_endday") + "add_to_temp_variable = { cd_hi = 1 }\n"
            + "".join("clear_array = mod1440_wr_ln_%s\n" % part for part in ln_parts)
            + merged(of_this_war, war_line)
            + setv("mod1440_wr_ln_n", "mod1440_wr_ln_date^num")
            + capitals
            # the dates at the two ends of the track
            + setv("mod1440_wr_c_day0d", "mod1440_wr_c_since") + setv("mod1440_wr_c_endd", "mod1440_wr_c_until")
            + marks + tally))
        # a hidden line's text still asks for its element (fix round 1 of E1): the lines are always there
        + pad([("mod1440_wr_ln_date", 0), ("mod1440_wr_ln_day", 0), ("mod1440_wr_ln_kind", BLANK), ("mod1440_wr_ln_fam", 0),
               ("mod1440_wr_ln_a", 0), ("mod1440_wr_ln_sa", 0), ("mod1440_wr_ln_p", 0), ("mod1440_wr_ln_b", "THIS")], WR_LINES))

    # ---- the daily round of today's rows
    keep_row = (lambda part, base: keep_higher("mod1440_wr_%s^wr_i" % base, "mod1440_wr_%s^wr_i" % part, "mod1440_wr_%s^wr_i" % part))
    daily_row = (
        tmp("wr_d", "global.num_days") + "subtract_from_temp_variable = { wr_d = mod1440_wr_day0^wr_i }\n" + setv("mod1440_wr_days^wr_i", "wr_d")
        + tmp("wr_s", 0) + block("var:wr_v", tmp("wr_s", "surrender_progress")) + "multiply_temp_variable = { wr_s = 100 }\n"
        + setv("mod1440_wr_surr^wr_i", "wr_s")
        + iff("check_variable = { mod1440_wr_capd^wr_i = 0 } var:wr_v = { has_capitulated = yes }",
              setv("mod1440_wr_capd^wr_i", 1) + line("capitulated", b="wr_v"))
        + iff("var:wr_v = { exists = yes }", (
            kread("THIS", "wr_v", "mod1440_wr_kus^wr_i", "mod1440_wr_kus0^wr_i") + keep_row("kus", "kus0")
            + kread("wr_v", "THIS", "mod1440_wr_kthem^wr_i", "mod1440_wr_kthem0^wr_i") + keep_row("kthem", "kthem0")
            # their head of government: kept again when another one rules
            + tmp("wr_cl", 0) + block("var:wr_v", tmp("wr_cl", "country_leader")) + tmp("wr_ol", "mod1440_wr_lt1^wr_i")
            + iff("NOT = { check_variable = { wr_cl = wr_ol } }", (
                block("var:wr_v", "mod1440_wr_hog = yes\n") + setv("mod1440_wr_lt1^wr_i", "hg_l") + setv("mod1440_wr_pt1^wr_i", "hg_p")
                + setv("mod1440_wr_gt1^wr_i", "hg_g") + mark("hg_l"))))))

    # the search of mod1440_wr_kread: up from yesterday's reading in steps that double, then halving down to 0.1
    kt = WR_KT
    kread_body = (
        setv("mod1440_wr_kn", "kr_prev") + tmp("kr_lo", 0) + tmp("kr_hi", "kr_prev")
        + iff("NOT = { %s }" % kt, iff("check_variable = { kr_prev > 0 }", setv("mod1440_wr_kn", 0) + iff("NOT = { %s }" % kt, tmp("kr_hi", 0))))
        + els(tmp("kr_lo", "kr_prev") + tmp("kr_st", 0.1) + tmp("kr_up", 1)
              + block("while_loop_effect", "limit = { check_variable = { kr_up = 1 } check_variable = { kr_st < 1000000 } }\n" + (
                  tmp("kr_t", "kr_lo") + "add_to_temp_variable = { kr_t = kr_st }\n" + setv("mod1440_wr_kn", "kr_t")
                  + iff(kt, tmp("kr_lo", "kr_t") + "multiply_temp_variable = { kr_st = 2 }\n")
                  + els(tmp("kr_hi", "kr_t") + tmp("kr_up", 0)))))
        + tmp("kr_d", "kr_hi") + "subtract_from_temp_variable = { kr_d = kr_lo }\n"
        + block("while_loop_effect", "limit = { check_variable = { kr_d > 0.15 } }\n" + (
            tmp("kr_t", "kr_lo") + "add_to_temp_variable = { kr_t = kr_hi }\n" + "multiply_temp_variable = { kr_t = 5 }\n"
            + "round_temp_variable = kr_t\n" + "divide_temp_variable = { kr_t = 10 }\n" + setv("mod1440_wr_kn", "kr_t")
            + iff(kt, tmp("kr_lo", "kr_t")) + els(tmp("kr_hi", "kr_t"))
            + tmp("kr_d", "kr_hi") + "subtract_from_temp_variable = { kr_d = kr_lo }\n"))
        + tmp("kr", "kr_lo"))

    hog = (tmp("hg_l", "country_leader")
           + iff("OR = { %s NOT = { check_variable = { mod1440_ld_p_of = country_leader } } }" % stale("mod1440_ld_p_ver", portrait_version), (
               tmp("p_ld", "country_leader") + tmp("p_tok", unknown) + block("var:p_ld", "mod1440_p_leader = yes\n")
               + setv("mod1440_ld_p", "p_tok") + stamped("mod1440_ld_p_ver", portrait_version) + setv("mod1440_ld_p_of", "country_leader")))
           + tmp("hg_p", "mod1440_ld_p") + iff("check_variable = { hg_p = 0 }", tmp("hg_p", unknown))
           + tmp("hg_g", 0) + "".join(iff("has_government = %s" % g, tmp("hg_g", n)) for n, (word, g) in enumerate(IDEOLOGIES, start=1)))

    return (
        "# Wars: a row for the enemy in wr_c, from today (wr_old = 1: the war ran when the record began; wr_how: 1 we\n"
        "# declared, 2 they declared, 3 it joined, 0 not known). It joins the war of an open row whose enemy fights on its\n"
        "# side, against whom the country has the same role; it keeps the readings of the first day and both heads of\n"
        "# government.\n"
        # E4 fix round 1: never the country itself (wr_me), whatever a hook or a comparison hands over
        + block("mod1440_wr_open", "mod1440_wr_grow = yes\n" + tmp("wr_me", "THIS") + iff(
            "check_variable = { wr_c = wr_me }", 'log = "MOD1440 records: no war row for [This.GetTag] against itself"\n')
            + iff("NOT = { is_in_array = { array = mod1440_wr_enemy value = wr_c } } NOT = { check_variable = { wr_c = wr_me } }",
                  "add_to_variable = { mod1440_wr_next = 1 }\n" + grouping + baseline + leaders
                  + "".join("add_to_array = { mod1440_wr_%s = %s }\n" % (part, start[part]) for part in WR_PARTS))
            + "mod1440_wr_count_wars = yes\n")
        + block("mod1440_wr_grow", grow)
        + "\n# Wars: how many wars the country fights today (its open rows by their war), for the tab (E4 fix round 1).\n"
        + block("mod1440_wr_count_wars", "clear_temp_array = wn_g\n" + block(
            "for_each_loop", "array = mod1440_wr_grp\nvalue = wn_v\n" + iff(
                "NOT = { is_in_array = { array = wn_g value = wn_v } }", "add_to_temp_array = { wn_g = wn_v }\n"))
            + setv("mod1440_wr_wars", "wn_g^num"))
        + "\n# Wars: in the scope of a country, its head of government (hg_l, his place), his portrait as a text key (hg_p,\n"
        "# looked up when another one rules or the table changed, kept on the country) and his ideology group (hg_g: 1\n"
        "# fascism, 2 democratic, 3 communism, 4 neutrality, 0 another).\n"
        + block("mod1440_wr_hog", hog)
        + "\n# Wars: the dead of the country mod1440_wr_kv by the hand of mod1440_wr_ko, in thousands to 0.1, into kr; kr_prev is\n"
        "# yesterday's reading. casualties_inflicted_by answers yes or no, so the number is searched (meta_trigger, SCR-054).\n"
        + block("mod1440_wr_kread", kread_body)
        + "\n# Wars: the war with wr_c is over: its row moves to the finished wars with the end date, its length, its dead\n"
        "# frozen (one more reading, the higher of it and yesterday's), how it ended and our head of government of the day.\n"
        + block("mod1440_wr_close", "mod1440_wr_grow = yes\n" + find + iff("check_variable = { wr_j > -1 }", (
            tmp("wr_out", outcomes["peace"]) + tmp("wr_oc", 1)
            + iff("check_variable = { mod1440_wr_capd^wr_j = 1 }", tmp("wr_out", outcomes["capitulated"]) + tmp("wr_oc", 2))
            + iff("is_in_array = { array = subjects value = wr_c }", tmp("wr_out", outcomes["subject"]) + tmp("wr_oc", 3))
            + iff("var:wr_c = { exists = no }", tmp("wr_out", outcomes["gone"]) + tmp("wr_oc", 5))
            + iff("check_variable = { mod1440_wr_capd^wr_j = 2 }", tmp("wr_out", outcomes["annexed"]) + tmp("wr_oc", 4))
            + iff("has_capitulated = yes", tmp("wr_out", outcomes["we_capitulated"]) + tmp("wr_oc", 6))
            + iff("var:wr_c = { exists = yes } is_subject_of = var:wr_c", tmp("wr_out", outcomes["we_subject"]) + tmp("wr_oc", 7))
            + tmp("wr_fr", 1) + iff("check_variable = { wr_oc = 1 }", tmp("wr_fr", 3)) + iff("check_variable = { wr_oc > 5 }", tmp("wr_fr", 2))
            + tmp("wr_d", "global.num_days") + "subtract_from_temp_variable = { wr_d = mod1440_wr_day0^wr_j }\n"
            + last_reading
            + "mod1440_wr_hog = yes\n" + tmp("wr_lu", "hg_l") + tmp("wr_pu", "hg_p") + tmp("wr_gu", "hg_g") + mark("wr_lu")
            + "".join("add_to_array = { array = mod1440_wo_%s value = %s index = 0 }\n" % (part, end[part]) for part in WO_PARTS)
            + "".join("remove_from_array = { array = mod1440_wr_%s index = wr_j }\n" % part for part in WR_PARTS)
            + "mod1440_wr_count_wars = yes\n"
            + iff("check_variable = { mod1440_wo_enemy^num > %d }" % WO_KEEP, (
                tmp("wr_last", "mod1440_wo_enemy^num") + "subtract_from_temp_variable = { wr_last = 1 }\n"
                + "".join("remove_from_array = { array = mod1440_wo_%s index = wr_last }\n" % part for part in WO_PARTS))))))
        + "\n# Wars: one more state taken from (wr_f = 1) or lost to (wr_f = 2) the enemy in wr_c, or one more victory\n"
        "# point taken (3) or lost (4). What was taken counts also for the general on the spot (of_best, of_who), in\n"
        "# this war: arrays on the officer (mod1440_ow_*), one element per row by the row's number; tr_cap 1 a capital.\n"
        + block("mod1440_wr_count", "mod1440_wr_grow = yes\n" + find + iff("check_variable = { wr_j > -1 }", "".join(
            iff("check_variable = { wr_f = %d }" % n, "add_to_variable = { mod1440_wr_%s^wr_j = 1 }\n" % part)
            for n, part in enumerate(("taken", "lost", "vpt", "vpl"), start=1))
            + iff("OR = { check_variable = { wr_f = 1 } check_variable = { wr_f = 3 } } check_variable = { of_best > 0 }", (
                tmp("ow_war", "mod1440_wr_id^wr_j") + block("var:of_who", (
                    tmp("ow_j", -1) + block("for_each_loop", "array = mod1440_ow_id\nvalue = ow_v\nindex = ow_i\n" + iff("check_variable = { ow_v = ow_war }", tmp("ow_j", "ow_i")))
                    + iff("check_variable = { ow_j < 0 }", "add_to_array = { mod1440_ow_id = ow_war }\n" + "".join(
                        "add_to_array = { mod1440_ow_%s = 0 }\n" % part for part in ("st", "vp", "cap")) + tmp("ow_j", "mod1440_ow_id^num")
                        + "subtract_from_temp_variable = { ow_j = 1 }\n")
                    + iff("check_variable = { wr_f = 1 }", "add_to_variable = { mod1440_ow_st^ow_j = 1 }\n"
                          + iff("check_variable = { tr_cap = 1 }", "add_to_variable = { mod1440_ow_cap^ow_j = 1 }\n"))
                    + iff("check_variable = { wr_f = 3 }", "add_to_variable = { mod1440_ow_vp^ow_j = 1 }\n")))))))
        + block("mod1440_wr_annexed", find + iff("check_variable = { wr_j > -1 }", setv("mod1440_wr_capd^wr_j", 2)))
        + "\n# Wars: the numbers of today's rows: days, each enemy's surrender progress, both sides' dead (never falling), the\n"
        "# enemy's head of government when another one rules; a line in the War Diary when an enemy or the country itself\n"
        "# has capitulated. The portraits kept on the rows are looked up again when the text keys' numbers moved.\n"
        + block("mod1440_wr_daily", (
            "mod1440_wr_grow = yes\n" + faces_again
            + block("for_each_loop", "array = mod1440_wr_enemy\nvalue = wr_v\nindex = wr_i\n" + daily_row)
            + "mod1440_wr_count_wars = yes\n"
            + iff("has_capitulated = yes NOT = { %s }" % is_one("mod1440_ev_capd"), setv("mod1440_ev_capd", 1) + line("we_capitulated"))
            + iff("has_capitulated = no", setv("mod1440_ev_capd", 0))))
        + "\n# Wars: the two lists of the page, one plate per war (mod1440_wv_* of today, mod1440_wp_* finished, newest first):\n"
        "# its first enemy, how many more, its days or the year it began, both sides' dead summed over its rows. A walk over\n"
        "# the rows when the page shows (rule 5).\n"
        + block("mod1440_wr_lists", lists)
        + block("mod1440_wr_picks", picks)
        + "\n# Wars: what the page needs when it is on show. With no war chosen, or one that is no more, the file opens on the\n"
        "# first war there is.\n"
        + block("mod1440_wr_show", (
            "mod1440_wr_grow = yes\nmod1440_wr_lists = yes\n"
            + find_in("mod1440_wv_g", "mod1440_wr_sel_g", "sh_a") + find_in("mod1440_wp_g", "mod1440_wr_sel_g", "sh_b")
            + iff("check_variable = { sh_a < 0 } check_variable = { sh_b < 0 }", (
                setv("mod1440_wr_sel_e", 0)
                + iff("check_variable = { mod1440_wv_g^num > 0 }", setv("mod1440_wr_sel_g", "mod1440_wv_g^0"))
                + iff("check_variable = { mod1440_wp_g^num > 0 }", setv("mod1440_wr_sel_g", "mod1440_wp_g^0"), "else_if")
                + "mod1440_wr_picks = yes\n"))
            + "mod1440_wr_card = yes\n"))
        + "\n# Wars: the file of the chosen war (mod1440_wr_sel_g): its rows in the order they joined (mod1440_we_*, the enemies\n"
        "# table), the war's figures, our heads of government, the War Diary's lines about its enemies within its dates,\n"
        "# the marks of the track and the commanders' tally over its rows.\n"
        + block("mod1440_wr_card", card)
        + block("mod1440_wr_faces_u", faces_of("u"))
        + "\n# Wars: their side of the file: the heads of government of the enemy chosen in the table (mod1440_wr_sel_e).\n"
        + block("mod1440_wr_them", them))


# ---------------------------------------------------------------- victory points

# Script learns of a state that changes hands from a hook, of a single province from nothing: so the mod looks,
# once a day while the country is at war, at who holds each victory point (the global array
# province_controllers) and compares with its copy of the day before. A point that passed between the country
# and an enemy becomes a line of the territory log, with the general who had the most divisions in its state.

def victory_points():
    """Returns the text of common/scripted_effects/mod1440_victory_points.txt and the version of the game's table.

    A mod can bring states of its own: Road to 56 has 1143 for the game's 1081 and other numbers for many, so a
    point of the game's table is in another state there, or no point at all. tools/victory_points_mods_table.py
    holds the points of such a map, and script picks the table by the number of states the loaded game has."""
    from victory_points_table import VICTORY_POINTS
    try:
        from victory_points_mods_table import MAPS
    except ImportError:
        MAPS = []
    tables = [("the game's history/states", 0, VICTORY_POINTS)] + [("the states of " + name, states, rows) for name, states, rows in MAPS]
    versions = [table_version(rows) for _name, _states, rows in tables]
    assert len(set(versions)) == len(versions), "two tables of victory points with the same version"
    version = versions[0]
    parts = ""
    for m, (source, states, rows) in enumerate(tables):
        scan, sync = "", ""
        for n, (province, state, value) in enumerate(rows):
            name = token("vp_%d" % province, "$VICTORY_POINTS_%d$" % province)
            now = "global.province_controllers^%d" % province
            scan += tmp("vp_now", now) + iff("NOT = { check_variable = { mod1440_vp_ctl^%d = vp_now } }" % n, (
                tmp("vp_old", "mod1440_vp_ctl^%d" % n) + setv("mod1440_vp_ctl^%d" % n, "vp_now") + tmp("vp_k", name) + tmp("vp_v", value)
                + block(str(state), tmp("vp_s", "THIS")) + "mod1440_vp_changed = yes\n"))
            sync += "add_to_array = { mod1440_vp_ctl = %s }\n" % now
        parts += ("\n# The %d points of %s: the copy, and the daily comparison.\n" % (len(rows), source)
                  + block("mod1440_vp_sync_%d" % m, "clear_array = mod1440_vp_ctl\n" + sync + setv("mod1440_vp_ver", versions[m]))
                  + block("mod1440_vp_scan_%d" % m, iff("NOT = { check_variable = { mod1440_vp_ver = %d } }" % versions[m],
                                                        "mod1440_vp_sync_%d = yes\n" % m) + els(scan)))

    def pick(effect):
        """The effect of the map that is loaded: of the game's own unless the number of states is another map's."""
        out = "mod1440_vp_map = yes\n"
        for m in range(1, len(tables)):
            out += iff("check_variable = { vp_map = %d }" % m, "%s_%d = yes\n" % (effect, m), "if" if m == 1 else "else_if")
        return out + (els("%s_0 = yes\n" % effect) if len(tables) > 1 else "%s_0 = yes\n" % effect)

    which = tmp("vp_map", 0)
    if len(tables) > 1:
        which += tmp("vp_states", 0) + block("every_state", "add_to_temp_variable = { vp_states = 1 }\n")
        which += "".join(iff("check_variable = { vp_states = %d }" % states, tmp("vp_map", m))
                         for m, (_source, states, _rows) in enumerate(tables) if m)
    enemy = "OR = { is_in_array = { array = enemies value = %s } is_in_array = { array = mod1440_ev_enemies value = %s } }"
    # a point that changes hands because its country gave up or is gone was not fought for: no line
    fought = "var:%s = { exists = yes has_capitulated = no }"

    def changed(kind, other, flag_value, counter):
        return (tmp("tr_s", "vp_s") + "mod1440_of_best = yes\n"
                + iff("check_variable = { vp_v > %d }" % (VP_MAJOR - 1), line(kind, a="vp_k", b=other, point=True, c="of_who", sc="of_best", p="vp_s", both=True))
                + els(line(kind, a="vp_k", b=other, point=True, c="of_who", sc="of_best", p="vp_s", log="tr"))
                + tmp("wr_c", other) + tmp("wr_f", flag_value) + "mod1440_wr_count = yes\n"
                + iff("check_variable = { of_best > 0 }", block("var:of_who", "add_to_variable = { %s = 1 }\n" % counter))
                # a great city taken: the honour of the divisions in its state, when that switch is on (frame())
                + (iff("check_variable = { vp_v > %d }" % (VP_MAJOR - 1), "mod1440_hn_city = yes\n") if kind == "vp_taken" else ""))

    out = ("# Generated by tools/build_managers.py from tools/victory_points_table.py (the game's history/states)\n"
           "# and tools/victory_points_mods_table.py (the states of a mod).\n\n"
           "# Victory points: which table is the loaded game's. vp_map: 0 the game's own, and the map of a mod when the\n"
           "# game has as many states as that map.\n"
           + block("mod1440_vp_map", which)
           + "\n# Victory points: the copy of who holds each point today, without a line: the first run, the first day of a\n"
           "# war, and after the list of points has changed (another build of the mod, another map).\n"
           + block("mod1440_vp_sync", pick("mod1440_vp_sync"))
           + "\n# Victory points: once a day for a player's country at war. Each point whose holder is another than\n"
           "# yesterday goes to mod1440_vp_changed with vp_old and vp_now (the holders), vp_k (its name), vp_v (its\n"
           "# value) and vp_s (its state).\n"
           + block("mod1440_vp_scan", pick("mod1440_vp_scan"))
           + parts
           + "\n# Victory points: one has changed hands. A line when the country in scope took it from an enemy or lost it to\n"
           "# one, the count of that war, and the count of the general on the spot.\n"
           + block("mod1440_vp_changed", (
               tmp("vp_me", "THIS")
               + iff("check_variable = { vp_now = vp_me } %s %s" % (enemy % ("vp_old", "vp_old"), fought % "vp_old"),
                     changed("vp_taken", "vp_old", 3, "mod1440_of_vps"))
               + iff("check_variable = { vp_old = vp_me } %s" % (enemy % ("vp_now", "vp_now")),
                     changed("vp_lost", "vp_now", 4, "mod1440_of_vpl"), "else_if"))))
    return out, version


# ---------------------------------------------------------------- text keys a save keeps (fix round 1)

# A variable holds a text key (token:<key>) as the key's number in the game's table of names, and a save keeps that
# number. The table is filled as the game loads: the mod's names in the order of
# common/synchronized_dynamic_tokens/mod1440_tokens.txt (sorted), after every name loaded before. Another build of the
# mod, another set of mods or another game version moves the numbers, and a number kept from before then names
# another key: the user's save of 2026-10-16 showed "GFX_portrait_..." in the place of "State taken" and other
# people's portraits on the officers. So:
# - what the save keeps for good (the kind of each line of the logs, the name of a victory point on a line, how a war
#   ended) is listed in a dictionary kept on the country with the numbers of the day it was made (mod1440_tk_*);
#   when a number of the dictionary is no longer what the key has today, every kept key is looked up in the old
#   dictionary and written again with today's number;
# - what the mod looks up again when it likes (portraits, traits, an advisor's role, medal strips and names) carries
#   the stamp global.mod1440_tk_ep, which goes up by one each time the numbers moved: a stamp of before is stale.
TK_OLD_LINE = "tk_old_line"                     # a line of a save older than the dictionary whose kind is lost
TK_SAMPLE = 16                                  # every this many entries of the dictionary is looked at each day


def kept_tokens():
    """[(group, [(code, key)])]: k the kinds of line, the blank and the ends of a war, v the names of victory points.
    A code says what the entry is whatever its place: a kind's number (KINDS only grows at its end), a province."""
    kinds = [(n, "mod1440_ev_" + name) for n, (name, family, words) in enumerate(KINDS)]
    kinds += [(90, BLANK.split(":", 1)[1])] + [(100 + n, "mod1440_wr_out_" + name) for n, (name, words) in enumerate(OUTCOMES)]
    from victory_points_table import VICTORY_POINTS
    try:
        from victory_points_mods_table import MAPS
    except ImportError:
        MAPS = []
    provinces = sorted(set(row[0] for row in VICTORY_POINTS) | set(row[0] for _name, _states, rows in MAPS for row in rows))
    return [("k", kinds), ("v", [(p, "mod1440_vp_%d" % p) for p in provinces])]


def kept_tokens_script(portrait_version):
    """The script of the dictionary (see above), for common/scripted_effects/mod1440_records.txt."""
    groups = kept_tokens()
    version = table_version(groups)
    token(TK_OLD_LINE, "A line of an earlier version of the mod")
    old_line = "token:mod1440_" + TK_OLD_LINE
    logs = ("ev", "tr", "kp")
    none = -1                                   # what mod1440_tk_map_<g> gives for a number the old dictionary lacks
    out = ("# The Records: the text keys a save keeps (tools/build_records.py, kept_tokens()). %s.\n"
           % ", ".join("%s: %d keys" % (g, len(rows)) for g, rows in groups))
    # today's numbers of every key, with their codes, into the temporary arrays tk_<g>n and tk_<g>c
    for g, rows in groups:
        out += block("mod1440_tk_now_" + g, "clear_temp_array = tk_%sn\nclear_temp_array = tk_%sc\n" % (g, g) + "".join(
            "add_to_temp_array = { tk_%sn = token:%s }\nadd_to_temp_array = { tk_%sc = %d }\n" % (g, key, g, code) for code, key in rows))
    # the number tk_v of group g, from the old dictionary to today's: tk_r, or -1 when the old one did not know it.
    # The code at the same place first (the list unchanged), else the code looked for.
    for g, rows in groups:
        found = (tmp("tk_c", "mod1440_tk_%sc^tk_j" % g) + tmp("tk_b2", 0)
                 + iff("check_variable = { tk_j < tk_%sc^num }" % g, (
                     tmp("tk_o2", "tk_%sc^tk_j" % g)
                     + iff("check_variable = { tk_o2 = tk_c }", tmp("tk_r", "tk_%sn^tk_j" % g) + tmp("tk_b2", 1))))
                 + iff("check_variable = { tk_b2 = 0 }", block("for_each_loop", (
                     "array = tk_%sc\nvalue = tk_o2\nindex = tk_j2\nbreak = tk_b2\n" % g
                     + iff("check_variable = { tk_o2 = tk_c }", tmp("tk_r", "tk_%sn^tk_j2" % g) + tmp("tk_b2", 1)))))
                 + tmp("tk_brk", 1))
        out += block("mod1440_tk_map_" + g, tmp("tk_r", none) + tmp("tk_brk", 0) + block("for_each_loop", (
            "array = mod1440_tk_%s\nvalue = tk_o\nindex = tk_j\nbreak = tk_brk\n" % g + iff("check_variable = { tk_o = tk_v }", found))))

    def each_line(log, part, body, test=None):
        """body for every line tk_i of a log (whose test holds), with the line's <part> in tk_v."""
        inside = tmp("tk_v", "mod1440_%s_%s^tk_i" % (log, part)) + body
        return block("for_loop_effect", "start = 0\nend = mod1440_%s_date^num\nvalue = tk_i\n" % log + (iff(test, inside) if test else inside))

    def is_point(log):
        return "check_variable = { mod1440_%s_sa^tk_i = 3 }" % log

    def to_state(log):
        """A line about a point whose name is lost names the point's state instead."""
        return setv("mod1440_%s_sa^tk_i" % log, 2) + setv("mod1440_%s_a^tk_i" % log, "mod1440_%s_p^tk_i" % log)

    def remap(log):
        kind = each_line(log, "kind", "mod1440_tk_map_k = yes\n" + iff("check_variable = { tk_r = %d }" % none, tmp("tk_r", old_line))
                         + setv("mod1440_%s_kind^tk_i" % log, "tk_r"))
        point = each_line(log, "a", "mod1440_tk_map_v = yes\n" + iff("check_variable = { tk_r = %d }" % none, to_state(log))
                          + els(setv("mod1440_%s_a^tk_i" % log, "tk_r")), is_point(log))
        return kind + point

    # A save of before the dictionary: every build numbered the kinds in the order of their sorted names, one after
    # the other. The base that makes the family of every line agree with its kind is looked for; when exactly one
    # does, it gives each line its kind. Otherwise a kind that is not one of today's becomes "a line of an earlier
    # version".
    by_name = sorted((key, n) for n, key in groups[0][1] if n < len(KINDS))
    count = len(by_name)
    fams = "".join("add_to_temp_array = { tk_sf = %d }\nadd_to_temp_array = { tk_ss = token:%s }\n" % (KINDS[n][1], key) for key, n in by_name)

    def all_kinds(body):
        return "".join(block("for_each_loop", "array = mod1440_%s_kind\nvalue = tk_v\nindex = tk_i\n" % log + body(log)) for log in logs)

    def agrees(log):
        return iff("check_variable = { tk_ok = 1 }", tmp("tk_stop", 0) + block("for_each_loop", (
            "array = mod1440_%s_kind\nvalue = tk_v\nindex = tk_i\nbreak = tk_stop\n" % log
            + tmp("tk_e", "tk_v") + "subtract_from_temp_variable = { tk_e = tk_base }\n"
            + iff("OR = { check_variable = { tk_e < 0 } check_variable = { tk_e > %d } }" % (count - 1), tmp("tk_ok", 0) + tmp("tk_stop", 1))
            + els(tmp("tk_f", "tk_sf^tk_e") + iff("NOT = { check_variable = { mod1440_%s_fam^tk_i = tk_f } }" % log, tmp("tk_ok", 0) + tmp("tk_stop", 1))))))

    unknown_kind = "NOT = { is_in_array = { array = tk_kn value = tk_v } }"
    guess = (
        "clear_temp_array = tk_sf\nclear_temp_array = tk_ss\n" + fams + tmp("tk_bad", 0) + tmp("tk_min", 2000000)
        + all_kinds(lambda log: iff(unknown_kind, "add_to_temp_variable = { tk_bad = 1 }\n") + iff("check_variable = { tk_v < tk_min }", tmp("tk_min", "tk_v")))
        + iff("check_variable = { tk_bad > 0 }", (
            tmp("tk_hits", 0) + tmp("tk_found", 0)
            + block("for_loop_effect", "start = 0\nend = %d\nvalue = tk_cand\n" % count + (
                tmp("tk_base", "tk_min") + "subtract_from_temp_variable = { tk_base = tk_cand }\n" + tmp("tk_ok", 1)
                + "".join(agrees(log) for log in logs)
                + iff("check_variable = { tk_ok = 1 }", "add_to_temp_variable = { tk_hits = 1 }\n" + tmp("tk_found", "tk_base"))))
            + iff("check_variable = { tk_hits = 1 }", all_kinds(lambda log: (
                tmp("tk_e", "tk_v") + "subtract_from_temp_variable = { tk_e = tk_found }\n" + setv("mod1440_%s_kind^tk_i" % log, "tk_ss^tk_e"))))
            + els(all_kinds(lambda log: iff(unknown_kind, setv("mod1440_%s_kind^tk_i" % log, old_line))))))
        # its points: a name that is not one of today's is lost
        + "".join(each_line(log, "a", iff("NOT = { is_in_array = { array = tk_vn value = tk_v } }", to_state(log)), is_point(log)) for log in logs))

    samples = ""
    for g, rows in groups:
        picks = sorted(set(list(range(0, len(rows), TK_SAMPLE)) + [len(rows) - 1])) if g == "v" else range(len(rows))
        samples += "".join(tmp("tk_t", "token:" + rows[j][1]) + iff("NOT = { check_variable = { mod1440_tk_%s^%d = tk_t } }" % (g, j), tmp("tk_bad", 1))
                           for j in picks)
    store = "".join(
        "clear_array = mod1440_tk_%s\nclear_array = mod1440_tk_%sc\n" % (g, g)
        + block("for_each_loop", "array = tk_%sn\nvalue = tk_o\nadd_to_array = { mod1440_tk_%s = tk_o }\n" % (g, g))
        + block("for_each_loop", "array = tk_%sc\nvalue = tk_o\nadd_to_array = { mod1440_tk_%sc = tk_o }\n" % (g, g)) for g, rows in groups)
    outcomes = block("for_loop_effect", "start = 0\nend = mod1440_wo_outcome^num\nvalue = tk_i\n" + tmp("tk_v", "mod1440_wo_outcome^tk_i")
                     + "mod1440_tk_map_k = yes\n" + iff("NOT = { check_variable = { tk_r = %d } }" % none, setv("mod1440_wo_outcome^tk_i", "tk_r")))
    # the kind of the newest line, which the tooltip of the top bar button names (E1 review)
    outcomes += (tmp("tk_v", "mod1440_rec_last_k") + "mod1440_tk_map_k = yes\n"
                 + iff("NOT = { check_variable = { tk_r = %d } }" % none, setv("mod1440_rec_last_k", "tk_r")) + els(setv("mod1440_rec_last_k", BLANK)))
    out += (
        "\n# The Records: for the country in scope, whether the numbers of the kept keys are still today's (the version of\n"
        "# the list, then every key of the kinds and every %dth name of a point). If not, mod1440_tk_fix.\n" % TK_SAMPLE
        + block("mod1440_tk_check", tmp("tk_bad", 0) + iff("NOT = { check_variable = { mod1440_tk_ver = %d } }" % version, tmp("tk_bad", 1))
                + els(samples) + iff("check_variable = { tk_bad = 1 }", "mod1440_tk_fix = yes\n"))
        + "\n# The Records: writes every key the logs of the country in scope keep again with today's number, by the old\n"
        "# dictionary or, for a save older than it, by the order of the names; keeps today's dictionary; and makes\n"
        "# every portrait, trait, role and medal looked up before stale (global.mod1440_tk_ep).\n"
        + block("mod1440_tk_fix", (
            "".join("mod1440_tk_now_%s = yes\n" % g for g, rows in groups)
            + iff("check_variable = { mod1440_tk_k^num > 0 }", "".join(remap(log) for log in logs) + outcomes)
            + els(guess)
            + store + setv("mod1440_tk_ver", version)
            + "add_to_variable = { global.mod1440_tk_ep = 1 }\n"
            # the portrait on the card of a state taken (frame()): kept on the state, looked up again now
            + block("every_state", "limit = { check_variable = { mod1440_sr_has_by = 1 } }\n" + tmp("tk_who", "mod1440_sr_by")
                    + tmp("tk_p", "token:" + UNKNOWN) + block("PREV", block("var:tk_who", (
                        officer_table(portrait_version) + tmp("tk_p", "mod1440_p"))))
                    + setv("mod1440_sr_by_p", "tk_p"))
            + 'log = "MOD1440 records: the numbers of the kept text keys had moved; the logs of [This.GetTag] were written again"\n')))
    return out


def stale(stamp, version=None):
    """A trigger: what the stamp <stamp> marks was looked up before the numbers of the text keys last moved, or (with
    <version>) in another table. The stamp's own variable is <stamp>_ep, the table's <stamp>."""
    epoch = "NOT = { check_variable = { %s_ep = global.mod1440_tk_ep } }" % stamp
    if version is None:
        return epoch
    return "OR = { NOT = { check_variable = { %s = %d } } %s }" % (stamp, version, epoch)


def stamped(stamp, version=None):
    """Script that sets the stamp of stale()."""
    return (setv(stamp, version) if version is not None else "") + setv(stamp + "_ep", "global.mod1440_tk_ep")


def portrait_stale(version):
    """The officer in scope needs mod1440_p_officer (the stamp mod1440_p_ver)."""
    return stale("mod1440_p_ver", version)


def officer_table(version):
    """Script in an officer's scope: his table portrait (mod1440_p), looked up once per table and epoch. E7 fix round 1:
    the chain (is_character on every name) is asked only of a unit leader. A retired officer's kept scope is no valid
    character, and each test logged 'is_character: Scope is not a valid character' (E7 check 2, Oswald Lutz); he keeps
    the portrait cached while he served (the daily round, mark), or the unknown leader once that is stale."""
    old = portrait_stale(version)
    return (iff("is_unit_leader = yes %s" % old, "mod1440_p_officer = yes\n")
            + iff(old, setv("mod1440_p", "token:" + UNKNOWN) + stamped("mod1440_p_ver", version)))


# ---------------------------------------------------------------- the frame: button, state card, hooks, daily run

HONOUR_DLC = 'has_dlc = "By Blood Alone"'


def open_war(country, old=0):
    # E4 round 2: how the war began, kept on its row (3: the daily comparison found it, so it joined a war; 0 not known)
    return tmp("wr_c", country) + tmp("wr_old", old) + tmp("wr_how", 0 if old else 3) + "mod1440_wr_open = yes\n"


def frame(portrait_version):
    """The top bar button, the card in the state view, and the script that ties the pages together."""
    # ---- the top bar button: the diary's icon, and a badge with the lines written since the window was last closed
    # d7-top-bar: at the right end of the top bar beside the clock, 150x28 inside the band's flat interior (y 3 to
    # 31), where it was 168x36 at 1300,4 and ran over the band's lower edge (user, 2026-10-16)
    # E1 review: the count in red when a new line is of War and peace; the tooltip says how many and names the
    # newest line (mod1440_rec_last_*, written by mod1440_ev_add)
    handle = M.button("rec_toggle", 0, 0, "GFX_1440p_SG_button_150x28", shortcut="shift+j", tooltip=B.key("rec_toggle_tt", (
        "The War Diary, your wars, your officers and your government (Shift+J)\\n\\n"
        "§Y[?mod1440_rec_new|0]§! new lines since you last closed the Records, §R[?mod1440_rec_new_war|0] of war and peace§!.\\n"
        "Newest: [?mod1440_rec_last_k.GetTokenLocalizedKey] §Y[?mod1440_rec_last_n.GetName]§!, [?mod1440_rec_last_d.%s]" % LONG)))
    handle += plain("rec_toggle_l", 12, 5, 98, B.key("rec_toggle", "£army_experience  Records"), height=22)
    handle += M.icon("rec_badge_bg", 114, 2, M.tile_sprite(30, 24))
    handle += plain("rec_badge", 114, 5, 30, B.key("rec_badge", "§Y[?mod1440_rec_new|0]§!"), M.FONT_SMALL, "centre", 20)
    handle += plain("rec_badge_war", 114, 5, 30, B.key("rec_badge_war", "§R[?mod1440_rec_new|0]§!"), M.FONT_SMALL, "centre", 20)
    gui = M.box("mod1440_records_handle", 2002, 3, 150, 28, handle)
    new = M.more_than_zero("mod1440_rec_new")
    script = M.scripted_gui("mod1440_records_handle", "mod1440_records_handle", "top_bar", effects=block(
        "rec_toggle_click", "mod1440_ev_init = yes\n" + iff(is_one("mod1440_rec_open"), "mod1440_rec_close = yes\n")
        + els(setv("mod1440_rec_open", 1) + "mod1440_rec_show = yes\n")),
        triggers=shown_if(["rec_badge_bg"], new) + block("rec_badge_visible", new + "NOT = { %s }\n" % M.more_than_zero("mod1440_rec_new_war").strip())
        + block("rec_badge_war_visible", new + M.more_than_zero("mod1440_rec_new_war")))

    # ---- the state card (E1 part C, E6): who took the state and when, by whose troops, the citation, its lines
    # 2026-10-27 (user): the card can be hidden. Landlord's windows stand at 462,8 to 564,138 of the state view,
    # under the card's left part (tools/check_playset.py guis), so a close button in the head strip hides the card
    # and a small Record button, placed right of Landlord's at 570, brings it back. The choice is kept per country
    # (mod1440_sc_hidden on ROOT, 1 = hidden; a save of an earlier build reads 0 and shows the card as before).
    # No ESCAPE on the close button: ESCAPE closes the state view itself, and would hide the card for good.
    card_w, card_h = 540, 142
    close_w, close_h = layout.CLOSE_SIZE
    close_x = 6 + (card_w - 12) - close_w - 4           # its right edge 4 inside the head strip's (Design Language, Fixed places)
    inner = M.icon("sc_head", 6, 6, layout.head_sprite(card_w - 12, 30))
    inner += M.text("sc_title", 14, 10, 290, B.key("sc_title", "£victory_points  The record of §Y[THIS.GetName]§!"), M.FONT_LABEL, height=22, fixed=True)
    lines_w = 184
    inner += M.text("sc_lines", close_x - 8 - lines_w, 12, lines_w, B.key("sc_lines", "[?mod1440_sr_lines|0] lines in the War Diary"), M.FONT_SMALL, "right", 20)
    inner += M.text("sc_lines_1", close_x - 8 - lines_w, 12, lines_w, B.key("sc_lines_1", "1 line in the War Diary"), M.FONT_SMALL, "right", 20)
    inner += M.button("sc_hide", close_x, 5, layout.CLOSE_BUTTON, tooltip=B.key(
        "sc_hide_tt", "Hide this card. The Record button that takes its place brings it back; the choice is kept for your country."))
    inner += M.icon("sc_flag", 14, 44, FLAG_SMALL)
    inner += M.text("sc_taken", 62, 48, card_w - 76, B.key(
        "sc_taken", "Taken from §Y[?mod1440_sr_from.GetName]§! on [?mod1440_sr_date.%s], held [?mod1440_sr_held|0] days" % LONG), M.FONT_LABEL, height=22, fixed=True)
    # E1 review: a state that came by treaty (mod1440_sr_how 2) says so, and that no troops are named
    inner += M.text("sc_received", 62, 48, card_w - 76, B.key(
        "sc_received", "Received from §Y[?mod1440_sr_from.GetName]§! by treaty on [?mod1440_sr_date.%s], held [?mod1440_sr_held|0] days" % LONG),
        M.FONT_LABEL, height=22, fixed=True)
    inner += M.text("sc_treaty", 62, 78, card_w - 76, B.key("sc_treaty", "§gIt came by treaty or annexation, not in battle: no troops are named.§!"),
                    M.FONT_SMALL, height=20)
    inner += M.text("sc_untaken", 14, 48, card_w - 28, B.key("sc_untaken", "Yours since before the record began."), M.FONT_LABEL, height=22)
    inner += M.button("sc_cite", 12, 108, "GFX_sort_button_202x29", B.key("sc_cite", "Cite the divisions here"), tooltip=B.key(
        "sc_cite_tt", "Every division of yours that stands in this state gets a line in its own history: Cited by the high command. "
                      "You can then award a medal for it in the division's history, at the game's price. A division takes one line a day."))
    inner += M.text("sc_cited", 224, 114, 200, B.key("sc_cited", "§G[?mod1440_sr_cited|0] cited today§!  -  [?mod1440_sr_cites|0] times in all"), M.FONT_SMALL, height=20)
    inner += M.text("sc_cites", 224, 114, 200, B.key("sc_cites", "Cited [?mod1440_sr_cites|0] times before"), M.FONT_SMALL, height=20)
    inner += M.button("sc_its_lines", card_w - 112, 108, "GFX_sort_button_100x29", B.key("sc_its_lines", "Its lines"),
                      tooltip=B.key("sc_its_lines_tt", "Opens the War Diary on the lines about this state."))
    gui += M.box("mod1440_state_card", 470, 0, card_w, card_h, inner, M.CARD_BG)
    # the general whose troops took it, in a window of its own: one that is not drawn never asks for a character
    # (a text that names one through an empty variable logs an error, Engine Facts X73)
    # E7: over the table's portrait the game's face, a list of one row over the state's mod1440_sr_by_ul, which holds him
    # while he is a unit leader (asked at the capture and again in the daily round over the player's states taken). The
    # card is drawn long after the capture and nothing is worked out when it shows, so the table's portrait stays under it.
    by = portrait("sc_by_face", 8, 0, WD_FACE) + face_grid("sc_by_gface_grid", 8, 0, WD_FACE)
    by += M.text("sc_by", 48, 6, card_w - 76, B.key("sc_by", "by the troops of §Y[?mod1440_sr_by.GetName]§!"), M.FONT_LABEL, height=22, fixed=True)
    gui += M.box("mod1440_state_card_by", 470 + 6, 74, card_w - 12, 32, by)
    gui += game_face("sc_by_gface", WD_FACE)
    # the handle while the card is hidden: right of Landlord's windows, on the line of the card's head strip
    handle = M.button("sc_show", 0, 0, "GFX_sort_button_100x29", B.key("sc_show", "£victory_points Record"), tooltip=B.key(
        "sc_show_tt", "Show the record of this state: when it was taken and by whose troops, the citation of your divisions, its lines in the War Diary."))
    gui += M.box("mod1440_state_card_handle", 570, 6, 100, 29, handle)
    cite = (tmp("hn_n", 0)
            + block("every_state_division", "limit = { OWNER = { tag = ROOT } }\n" + block(
                "add_history_entry", 'key = mod1440_hn_cited\nsubject = "Citation"\nallow = yes\n') + "add_to_temp_variable = { hn_n = 1 }\n")
            + setv("mod1440_sr_cited", "hn_n") + setv("mod1440_sr_cited_day", "global.num_days")
            + iff("check_variable = { hn_n > 0 }", "add_to_variable = { mod1440_sr_cites = 1 }\n" + fill("cited", a="THIS", state=True, n="hn_n")
                  + block("ROOT", "mod1440_tr_add = yes\nadd_to_variable = { mod1440_hn_count = hn_n }\nadd_to_variable = { mod1440_hn_cite_n = hn_n }\n"
                          + setv("mod1440_hn_last_s", "PREV") + setv("mod1440_hn_last_d", "global.date") + setv("mod1440_hn_has_last", 1))))
    its_lines = block("ROOT", (setv("mod1440_wd_filter", WD_STATE_FILTER) + setv("mod1440_wd_state", "PREV") + setv("mod1440_rec_page", 0)
                               + "clear_array = mod1440_wd_back\n" + setv("mod1440_wd_from", 0) + "mod1440_ev_init = yes\n"
                               + setv("mod1440_rec_open", 1) + "mod1440_rec_show = yes\n"))
    mine = "is_controlled_by = ROOT\n"
    hidden = block("ROOT", is_one("mod1440_sc_hidden") + "\n")
    shown_card = mine + block("ROOT", "NOT = { %s }\n" % is_one("mod1440_sc_hidden"))
    taken = "check_variable = { mod1440_sr_day > 0 }\n"
    state_script = block("mod1440_state_card", (
        'context_type = selected_state_context\nwindow_name = "mod1440_state_card"\nparent_window_token = selected_state_view\n\n'
        + block("visible", shown_card) + "\n" + block("properties", flown("sc_flag", "?mod1440_sr_from")) + "\n"
        + block("effects", block("sc_cite_click", cite) + block("sc_its_lines_click", its_lines)
                + block("sc_hide_click", block("ROOT", setv("mod1440_sc_hidden", 1)))) + "\n"
        + block("triggers", (
            block("sc_lines_visible", "check_variable = { mod1440_sr_lines > 1 }\n")
            + block("sc_lines_1_visible", "check_variable = { mod1440_sr_lines = 1 }\n")
            + shown_if(["sc_flag"], taken)
            + block("sc_taken_visible", taken + "NOT = { check_variable = { mod1440_sr_how = 2 } }\n")
            + shown_if(["sc_received", "sc_treaty"], taken + "check_variable = { mod1440_sr_how = 2 }\n")
            + block("sc_untaken_visible", "check_variable = { mod1440_sr_day < 1 }\n")
            + block("sc_cite_visible", HONOUR_DLC + "\n")
            + block("sc_its_lines_visible", M.more_than_zero("mod1440_sr_lines"))
            + block("sc_cited_visible", "check_variable = { mod1440_sr_cited_day = global.num_days }\ncheck_variable = { mod1440_sr_cited > 0 }\n")
            + block("sc_cites_visible", "NOT = { check_variable = { mod1440_sr_cited_day = global.num_days } }\n" + M.more_than_zero("mod1440_sr_cites"))))
        + "\n" + block("ai_enabled", "always = no\n")))
    state_script += block("mod1440_state_card_by", (
        'context_type = selected_state_context\nwindow_name = "mod1440_state_card_by"\nparent_window_token = selected_state_view\n\n'
        + block("visible", shown_card + taken + is_one("mod1440_sr_has_by") + "\n") + "\n"
        + block("dynamic_lists", face_list("sc_by_gface_grid", "mod1440_sr_by_ul", "sc_by_gface")) + "\n"
        + block("properties", shown("sc_by_face", "mod1440_sr_by_p") + block("sc_by_gface", GAME_FACE)) + "\n"
        + block("triggers", block("sc_by_gface_visible", SERVES + "\n")) + "\n"
        + block("ai_enabled", "always = no\n")))
    state_script += block("mod1440_state_card_handle", (
        'context_type = selected_state_context\nwindow_name = "mod1440_state_card_handle"\nparent_window_token = selected_state_view\n\n'
        + block("visible", mine + hidden) + "\n"
        + block("effects", block("sc_show_click", block("ROOT", setv("mod1440_sc_hidden", 0)))) + "\n"
        + block("ai_enabled", "always = no\n")))
    token("hn_capture", "Took part in the capture of $PROVINCE$")
    token("hn_cited", "Cited by the high command at $PROVINCE$")
    token("hn_sea", "Landed from the sea in $PROVINCE$")
    token("hn_air", "Dropped from the air over $PROVINCE$")
    token("hn_city", "Fought for $PROVINCE$, where a great city fell")

    # ---- script
    tabs = ""       # each page writes its own tab in front (head())
    # the file of a war shows the portrait of the country's own head of government, which the Government page looks up
    lists = ["mod1440_wd_list = yes\n", "mod1440_of_list = yes\n", "mod1440_gv_daily = yes\n",
             "mod1440_gv_daily = yes\nmod1440_wr_daily = yes\nmod1440_wr_show = yes\n"]
    switches = "".join(setv("mod1440_hn_f_" + name, 1) + iff(is_one(variable), setv("mod1440_hn_f_" + name, 2)) for name, variable, words in HONOURS)
    show = "mod1440_rec_odd = yes\n" + tabs + switches
    show += setv("mod1440_rec_days", "global.num_days") + "subtract_from_variable = { mod1440_rec_days = mod1440_ev_since_day }\n"
    show += "".join(iff("check_variable = { mod1440_rec_page = %d }" % n, lists[n]) for n in range(len(PAGES)))

    # an icon asks for its sprite also before anybody is chosen: until then it is told the unknown leader; a text
    # that names a state through a variable gets the capital until it names another
    faces = "".join(iff("check_variable = { %s = 0 }" % v, setv(v, "token:" + UNKNOWN)) for v in ("mod1440_of_c_p", "mod1440_wr_c_p", "mod1440_gv_p")
                    # E4 round 2: the kept heads of government of a war's file and its commanders
                    + tuple("mod1440_wr_c_%sp%s" % (s, n) for s in "ut" for n in "01") + tuple("mod1440_wr_k_%d_p" % k for k in range(WR_COMMANDERS)))
    faces += "".join(iff("check_variable = { %s = 0 }" % v, setv(v, "capital")) for v in ("mod1440_wd_state", "mod1440_hn_last_s"))
    # ... and one that names a country, the country itself (the head of a country's lines, E1 review)
    faces += iff("check_variable = { mod1440_wd_country = 0 }", setv("mod1440_wd_country", "THIS"))
    copy_members = "clear_array = mod1440_gv_fac\n" + block(
        "for_each_loop", "array = faction_members\nvalue = ev_c\nadd_to_array = { mod1440_gv_fac = ev_c }\n")
    in_faction = tmp("ev_in", 0) + iff("is_in_faction = yes", tmp("ev_in", 1))

    def credit(counter):
        return iff("check_variable = { of_best > 0 }", block("var:of_who", "add_to_variable = { %s = 1 }\n" % counter))

    def honour(key, subject, owner="ROOT"):
        """The line in the history of every division of the player that stands in the state in scope."""
        return (tmp("hn_n", 0) + block("every_state_division", "limit = { OWNER = { tag = %s } }\n" % owner + block(
            "add_history_entry", 'key = mod1440_hn_%s\nsubject = "%s"\nallow = no\n' % (key, subject)) + "add_to_temp_variable = { hn_n = 1 }\n"))

    # the casualty steps (E1 review): casualties_k against the next step, once a day; the first run of a record
    # takes the steps already passed without a line (mod1440_ev_cas_i: the index of the next step)
    casualty_step = tmp("ev_ck", "casualties_k") + iff("NOT = { check_variable = { mod1440_ev_cas_v = 1 } }", (
        setv("mod1440_ev_cas_v", 1) + setv("mod1440_ev_cas_i", 0)
        + "".join(iff("check_variable = { ev_ck > %d }" % (step - 1), setv("mod1440_ev_cas_i", k + 1)) for k, step in enumerate(CASUALTY_STEPS))))
    casualty_step += "".join(iff("check_variable = { mod1440_ev_cas_i = %d } check_variable = { ev_ck > %d }" % (k, step - 1), (
        setv("mod1440_ev_cas_i", k + 1) + line("casualties", n=step)), "if" if k == 0 else "else_if") for k, step in enumerate(CASUALTY_STEPS))
    counted = "add_to_variable = { mod1440_hn_count = hn_n }\nadd_to_variable = { mod1440_hn_auto_n = hn_n }\n"
    capital = iff("check_variable = { tr_cap = 1 } %s %s" % (is_one("mod1440_hn_auto"), HONOUR_DLC), block("var:tr_s", honour("capture", "Capital")) + counted)

    def changed(kind, capital_kind):
        """The line for a state that changed hands: a capital into both logs, any other into the territory log."""
        return (iff("check_variable = { tr_cap = 1 }", line(capital_kind, a="tr_s", b="tr_c", state=True, c="of_who", sc="of_best", both=True))
                + els(line(kind, a="tr_s", b="tr_c", state=True, c="of_who", sc="of_best", log="tr")))

    # who took the state: the general on the spot and his portrait, for the state card
    by_whom = (tmp("sr_p", "token:" + UNKNOWN)
               + iff("check_variable = { of_best > 0 }", block("var:of_who", (
                   officer_table(portrait_version) + tmp("sr_p", "mod1440_p"))))
               + block("var:tr_s", setv("mod1440_sr_has_by", 0) + "clear_array = mod1440_sr_by_ul\n" + iff("check_variable = { of_best > 0 }", (
                   setv("mod1440_sr_by", "of_who") + setv("mod1440_sr_by_p", "sr_p") + setv("mod1440_sr_has_by", 1)
                   # E7: the general on the spot, kept for the game's face on the card (a unit leader: he was found among them)
                   + "add_to_array = { mod1440_sr_by_ul = of_who }\n"))))

    script_effects = (
        "# The Records: what the window shows. Sets the buttons' frames and makes the list of the open page.\n"
        + block("mod1440_rec_show", "mod1440_ev_grow = yes\n" + faces + show + "add_to_variable = { mod1440_rec_dirty = 1 }\n")
        + "\n# The Records: the window closes; the lines written so far count as seen (the badge of the top bar button).\n"
        + block("mod1440_rec_close", setv("mod1440_rec_open", 0) + setv("mod1440_rec_new", 0) + setv("mod1440_rec_new_war", 0)
                # the lines up to here are seen: a line with a higher number stands on the lighter band (E1 review)
                + setv("mod1440_rec_seen", "mod1440_ln_next"))
        + "\n# The Records: the first run for the country in scope. Takes the copies the daily comparison needs, opens a\n"
        "# row for each war that already runs and writes the first line.\n"
        # The card of a state names the country it was taken from. A state nobody took holds none, and the game
        # logs "invalid scope for var" each time such a state is selected, also while the line is hidden (Engine
        # Facts X73). So every state gets a country once, for all players: the line shows only where
        # mod1440_sr_day says the state was taken.
        + block("mod1440_ev_init", iff("NOT = { check_variable = { global.mod1440_sr_named = 1 } }", (
            block("every_state", iff("NOT = { has_variable = mod1440_sr_from }", setv("mod1440_sr_from", "PREV")))
            + setv("global.mod1440_sr_named", 1))) + iff("NOT = { %s }" % is_one("mod1440_ev_begun"), (
            setv("mod1440_ev_begun", 1) + setv("mod1440_hn_auto", 1)
            + setv("mod1440_ev_since", "global.date") + setv("mod1440_ev_since_day", "global.num_days") + "mod1440_rec_odd = yes\n"
            + line("begins")
            + block("for_each_loop", "array = enemies\nvalue = ev_c\nadd_to_array = { mod1440_ev_enemies = ev_c }\n" + open_war("ev_c", 1))
            + block("for_each_loop", "array = subjects\nvalue = ev_c\nadd_to_array = { mod1440_ev_subjects = ev_c }\n")
            + in_faction + setv("mod1440_ev_fac", "ev_in") + copy_members
            + "mod1440_gv_daily = yes\nmod1440_of_seen = yes\n")))
        + "\n# The Records: once a day for a player's country. The victory points first, while yesterday's enemies are\n"
        "# still known. Then what no hook tells, found by comparing with yesterday: the end of a war, a new or lost\n"
        "# subject, the faction, the offices. Then the numbers of the wars, and how long each state taken is held.\n"
        + block("mod1440_rec_daily", (
            "mod1440_ev_init = yes\nmod1440_ev_grow = yes\n"
            # at peace nothing is looked at; the copy is taken again on the first day of the next war
            + iff("has_war = yes", "mod1440_vp_scan = yes\n") + els(setv("mod1440_vp_ver", 0))
            + compare("enemies", "mod1440_ev_enemies", "ev_c",
                      line("war_with", b="ev_c") + open_war("ev_c"),
                      line("peace", b="ev_c") + tmp("wr_c", "ev_c") + "mod1440_wr_close = yes\n")
            + compare("subjects", "mod1440_ev_subjects", "ev_c", line("subject_new", b="ev_c"), line("subject_gone", b="ev_c"))
            + in_faction
            + iff("NOT = { check_variable = { mod1440_ev_fac = ev_in } }", (
                iff("check_variable = { ev_in = 1 }", line("faction_in", b="faction_leader")) + els(line("faction_out"))
                + setv("mod1440_ev_fac", "ev_in") + copy_members))
            # a new subject joins its overlord's faction the same day: "Made a subject" says it already (E1 review)
            + els(compare("faction_members", "mod1440_gv_fac", "ev_c",
                          iff("NOT = { is_in_array = { array = subjects value = ev_c } }", line("member_in", b="ev_c")), line("member_out", b="ev_c")))
            + "mod1440_wr_daily = yes\nmod1440_gv_daily = yes\nmod1440_of_seen = yes\nmod1440_of_gone = yes\n"
            + casualty_step
            + block("every_controlled_state", "limit = { check_variable = { mod1440_sr_day > 0 } }\n" + setv("mod1440_sr_held", "global.num_days")
                    + "subtract_from_variable = { mod1440_sr_held = mod1440_sr_day }\n"
                    # E7 gate B: the general of the card is asked again whether he is a unit leader; if not, the table's portrait
                    + iff(is_one("mod1440_sr_has_by"), unit_leader_into("mod1440_sr_by", "mod1440_sr_by_ul", "sr_ul")))
            + iff(is_one("mod1440_rec_open"), "mod1440_rec_show = yes\n")))
        + "\n# The Records: a war has begun between the country in scope and wr_c (a hook says who attacked).\n"
        # E4 round 2: wr_how, who declared (1 we, 2 they), kept on the war's row
        + block("mod1440_ev_war_on", line("war_on", b="wr_c") + tmp("wr_old", 0) + tmp("wr_how", 1) + "mod1440_wr_open = yes\n"
                + iff("NOT = { is_in_array = { array = mod1440_ev_enemies value = wr_c } }", "add_to_array = { mod1440_ev_enemies = wr_c }\n"))
        + block("mod1440_ev_war_by", line("war_by", b="wr_c") + tmp("wr_old", 0) + tmp("wr_how", 2) + "mod1440_wr_open = yes\n"
                + iff("NOT = { is_in_array = { array = mod1440_ev_enemies value = wr_c } }", "add_to_array = { mod1440_ev_enemies = wr_c }\n"))
        + "\n# The Records: the general of the country in scope with the most divisions in the state tr_s: of_who, and\n"
        "# of_best how many divisions that is (0: nobody stands there).\n"
        + block("mod1440_of_best", tmp("of_best", 0) + tmp("of_who", 0) + block("every_army_leader", (
            tmp("of_n", "num_units_in_state@var:tr_s")
            + iff("check_variable = { of_n > of_best }", "mod1440_of_me = yes\n" + iff(
                "NOT = { check_variable = { of_me = 0 } }", tmp("of_best", "of_n") + tmp("of_who", "of_me"))))))
        + "\n# The Records: the country in scope has taken the state tr_s from tr_c (tr_cap = 1: a capital). At war with\n"
        "# tr_c: a line with the general on the spot, the count of the war and his own, what the state card shows, and the\n"
        "# honour. Not at war (an annexation, a subject's state, a peace): a line of the territory log only, \"Received\n"
        "# from\", nothing counted for a war or an officer, and the card says it came by treaty (E1 review, 2026-10-22).\n"
        + block("mod1440_tr_taken", (
            block("var:tr_s", setv("mod1440_sr_date", "global.date") + setv("mod1440_sr_day", "global.num_days")
                  + setv("mod1440_sr_from", "tr_c") + setv("mod1440_sr_held", 0) + setv("mod1440_sr_how", 1))
            + iff("has_war_with = var:tr_c", (
                "mod1440_of_best = yes\n" + changed("state_taken", "capital_taken")
                + tmp("wr_c", "tr_c") + tmp("wr_f", 1) + "mod1440_wr_count = yes\n" + credit("mod1440_of_states")
                + by_whom + capital))
            + els(line("state_received", a="tr_s", b="tr_c", state=True, log="tr")
                  + block("var:tr_s", setv("mod1440_sr_how", 2) + setv("mod1440_sr_has_by", 0)))))
        + block("mod1440_tr_lost", iff("has_war_with = var:tr_c", (
            "mod1440_of_best = yes\n" + changed("state_lost", "capital_lost")
            + tmp("wr_c", "tr_c") + tmp("wr_f", 2) + "mod1440_wr_count = yes\n"))
            + els(line("state_handed", a="tr_s", b="tr_c", state=True, log="tr")))
        + "\n# The Records: a victory point worth %d or more taken (mod1440_vp_changed): the honour of the divisions of the\n"
        "# country in scope that stand in its state vp_s, when that switch is on.\n" % VP_MAJOR
        + block("mod1440_hn_city", iff("%s %s" % (is_one("mod1440_hn_vp"), HONOUR_DLC), block("var:vp_s", honour("city", "City")) + counted))
        + "\n# The Records: a landing from the sea (on_naval_invasion: the state in scope, ROOT the country that lands) and\n"
        "# from the air (on_units_paradropped_in_state: ROOT the state, FROM the country). The honour of the divisions of\n"
        "# the player that stand in the state when the hook fires.\n"
        + block("mod1440_hn_landing", honour("sea", "Landing") + block("ROOT", counted))
        + block("mod1440_hn_drop", honour("air", "Airborne", "FROM") + block("FROM", counted))
    )

    # ---- hooks (X43 for those seen firing; the others after the comments of the vanilla files)
    human = "is_ai = no"
    state = block("FROM.FROM", tmp("tr_s", "THIS") + tmp("tr_cap", 0) + iff("is_capital = yes", tmp("tr_cap", 1)))

    def simple(kind):
        return iff(human, line(kind))

    def ace(counter, kind, word):
        # E1 review (decision 2): a counter only, until phase E5 can keep the ace and name him on a line
        return iff(human, "add_to_variable = { mod1440_ac_%s = 1 }\n" % counter
                   + 'log = "MOD1440 listening: %s, ace [FROM.GetFullName] ([FROM.GetCallsign])"\n' % word)

    def listening(hook, scopes):
        return 'log = "MOD1440 listening: %s, %s"\n' % (hook, scopes)

    hooks = {
        # ROOT the attacker, FROM the defender
        "on_war_relation_added": (iff(human, tmp("wr_c", "FROM") + "mod1440_ev_war_on = yes\n")
                                  + iff("FROM = { is_ai = no }", block("FROM", tmp("wr_c", "PREV") + "mod1440_ev_war_by = yes\n"))),
        # ROOT the annexer, FROM the annexed. A civil war won writes its own line (on_civil_war_end, which says that
        # it fires on_annex too): the Annexed line is left out when that line came first on the same day
        "on_annex": iff(human, tmp("ev_an", "FROM") + iff(
            "NOT = { check_variable = { mod1440_ev_cw_day = global.num_days } check_variable = { mod1440_ev_cw_c = ev_an } }",
            line("annexed", b="FROM")) + tmp("wr_c", "FROM") + "mod1440_wr_annexed = yes\n"),
        # --- E1 review (2026-10-22): the hooks of the new kinds, with the scopes of the comments of the vanilla files
        # ROOT the winner, FROM the annexed: "fires just before FROM gets annexed ... It will also fire on_annex and
        # on_civil_war_end" (04_mtg_on_actions.txt:194), so the skip in on_annex above holds
        "on_civil_war_end_before_annexation": iff(human, setv("mod1440_ev_cw_day", "global.num_days") + setv("mod1440_ev_cw_c", "FROM")
                                + line("civil_war_won", b="FROM") + listening("on_civil_war_end_before_annexation", "[ROOT.GetName] over [FROM.GetName]")),
        # ROOT the sender, FROM the receiver (07_nsb_on_actions.txt)
        "on_send_volunteers": iff(human, line("volunteers_sent", b="FROM") + listening("on_send_volunteers", "[ROOT.GetName] to [FROM.GetName]")),
        # scopes not commented in the game's files: taken to be those of on_send_volunteers; the log line tells
        "on_recall_volunteers": iff(human, line("volunteers_back", b="FROM") + listening("on_recall_volunteers", "ROOT [ROOT.GetName], FROM [FROM.GetName]")),
        # ROOT the government in exile, FROM its host (09_aat_on_actions.txt)
        "on_government_exiled": (listening("on_government_exiled", "ROOT [ROOT.GetName], FROM [FROM.GetName]")
                                 + iff(human, line("exiled", b="FROM"))
                                 + iff("FROM = { is_ai = no }", block("FROM", line("exile_hosted", b="PREV")))),
        # ROOT the exile, FROM the old host (04_mtg_on_actions.txt)
        "on_exile_government_reinstated": iff(human, line("reinstated", b="FROM")),
        # the scope is the country whose cipher is broken, FROM the decrypter (05_lar_on_actions.txt): our own success only
        "on_fully_decrypted_cipher": iff("FROM = { is_ai = no }", block("FROM", line("cipher", b="PREV"))),
        # ROOT the country that was capitulated (00_on_actions.txt)
        "on_uncapitulation": iff(human, line("fought_on")),
        # ROOT the new controller, FROM the old one, FROM.FROM the state
        "on_state_control_changed": (iff(human, state + tmp("tr_c", "FROM") + "mod1440_tr_taken = yes\n")
                                     + iff("FROM = { is_ai = no }", state + block("FROM", tmp("tr_c", "PREV") + "mod1440_tr_lost = yes\n"))),
        # the scope is the state invaded, ROOT the country that lands: one line per state and day, and the honour of
        # the divisions that stand in the state when the hook fires
        "on_naval_invasion": iff("ROOT = { is_ai = no } NOT = { check_variable = { mod1440_sr_landing = global.num_days } }", (
            setv("mod1440_sr_landing", "global.num_days") + fill("landing", a="THIS", state=True) + block("ROOT", "mod1440_ev_add = yes\n")
            + iff("ROOT = { %s } %s" % (is_one("mod1440_hn_sea"), HONOUR_DLC), "mod1440_hn_landing = yes\n")
            + 'log = "MOD1440 listening: on_naval_invasion, state [THIS.GetName], by [ROOT.GetName], [?hn_n] divisions honoured"\n')),
        # ROOT the state dropped into, FROM the country
        "on_units_paradropped_in_state": iff("FROM = { is_ai = no }", (
            fill("airborne", a="THIS", state=True) + block("FROM", "mod1440_ev_add = yes\n")
            + iff("FROM = { %s } %s" % (is_one("mod1440_hn_air"), HONOUR_DLC), "mod1440_hn_drop = yes\n")
            + 'log = "MOD1440 listening: on_units_paradropped_in_state, state [THIS.GetName], by [FROM.GetName], [?hn_n] divisions honoured"\n')),
        # a change of party also changes the government: one line for the day (E1 review)
        "on_ruling_party_change": iff(human, setv("mod1440_ev_party_day", "global.num_days") + line("party")),
        "on_government_change": iff(human + " NOT = { check_variable = { mod1440_ev_party_day = global.num_days } }", line("government")),
        "on_new_term_election": simple("election"),
        # the country is the scope, FROM the ace. Whether an ace can be kept is not known (wiki/phases/E5-aces-roll.md):
        # the first hook tries and writes what it reads back to game.log.
        "on_ace_promoted": ace("new", "ace_new", "on_ace_promoted") + iff(human, (
            "add_to_array = { mod1440_ac_try = FROM }\n"
            'log = "MOD1440 listening: kept [?mod1440_ac_try^num] aces, the first reads [?mod1440_ac_try^0.GetFullName]"\n')),
        "on_ace_killed": ace("lost", "ace_lost", "on_ace_killed"),
        "on_ace_killed_on_accident": ace("lost", "ace_lost", "on_ace_killed_on_accident"),
        "on_ace_killed_by_ace": ace("lost", "ace_lost", "on_ace_killed_by_ace"),
        "on_ace_killed_other_ace": ace("down", "ace_down", "on_ace_killed_other_ace"),
        "on_non_ace_killed_other_ace": ace("down", "ace_down", "on_non_ace_killed_other_ace"),
        # ROOT the owner of the ship, FROM the country that sank it
        "on_pride_of_the_fleet_sunk": (iff(human, line("pride_lost", b="FROM"))
                                       + iff("FROM = { is_ai = no }", block("FROM", line("pride_sunk", b="PREV")))),
    }
    return gui, script + "\n" + state_script, script_effects, hooks


# ---------------------------------------------------------------- samples and scenes, for the renderer and the tests

# What a text of these pages shows at its widest, by what stands between its brackets.
SAMPLES = [
    # the frame, the diary, the wars and the state card of 2026-10-16
    (r"mod1440_rec_days", "1374"), (r"mod1440_rec_new", "3"), (r"mod1440_wr_enemy\^num|mod1440_wr_wars", "2"), (r"mod1440_of_known\^num", "26"),
    (r"mod1440_ev_date\^num|mod1440_tr_date\^num", "1000"), (r"mod1440_kp_date\^num", "300"), (r"mod1440_wd_first", "1"),
    (r"mod1440_wd_last", "200"), (r"mod1440_wd_total", "1000"), (r"mod1440_wd_hn", "2"), (r"mod1440_wd_g_\w+_t", "128"),
    (r"mod1440_wd_g_\w+_x", "12"), (r"GetDateStringShortMonth", "27 Sep, 1939"), (r"mod1440_wr_k_\d_(st|vp|cap)", "12"),
    (r"(ROOT\.)?mod1440_w[ro]_(taken|lost|vpt|vpl)\^i", "18"), (r"ROOT\.mod1440_wr_days|mod1440_wo_days", "1460"),
    (r"ROOT\.mod1440_wr_surr", "100"), (r"mod1440_wo_enemy\^i\.GetName|mod1440_wd_b\^i\.GetName", "The Czechoslovak Republic"),
    (r"mod1440_sr_held", "1460"), (r"mod1440_sr_lines", "128"), (r"mod1440_sr_cited|mod1440_sr_cites", "36"),
    (r"mod1440_hn_last_s", "Niederschlesien"), (r"mod1440_wr_c_ecas|mod1440_wr_c_cas", "1250000"), (r"mod1440_wr_c_ours", "100"),
    (r"mod1440_sr_by\.GetName", "Konstantin von Neurath"), (r"mod1440_wr_ln_b\^", "Czechoslovakia"), (r"mod1440_wr_c_title|wr_c_enemy\.GetName", "Czechoslovakia"),
    # e-officers-gov: the officer's file, the seats of the Government page
    (r"mod1440_of_c_tr\^|mod1440_of_tr\^", "Brilliant Strategist"), (r"mod1440_of_c_tr_(other|over)|mod1440_of_tr_plus", "2"),
    (r"mod1440_of_c_(atk|def|c3|c4|traits|max)\b", "9"), (r"mod1440_of_c_bat", "2400"), (r"mod1440_of_c_plan", "100%"),
    (r"mod1440_of_c_(fight|arm|k\d)\b", "240"), (r"_d_r\^|mod1440_gv_of_\d_r\b", "Reich Minister of Foreign Affairs"),
    (r"mod1440_gv_hc_n", "7"),
    (LONG, "30 September, 1944"), (r"GetDateStringNoHour", "1944.12.31"), (r"GetLastElection", " 1:00, 5 March, 1933"),
    (r"GetNameWithFlag", "The Czechoslovak Republic"),
    (r"mod1440_wd_kind|mod1440_of_ln_kind|mod1440_wr_ln_kind", "Our pride of the fleet was sunk by"), (r"outcome", "No longer exists"),
    (r"mod1440_gv_law", "Partial Mobilization"), (r"dec_key|md_key", "Knight's Cross (Swords & Diamonds)"),
    (r"GetRulingParty$", "NSDAP"), (r"Get\w+Party(Long)?$", "Nationalsozialistische Deutsche Arbeiterpartei"),
    (r"GetRulingIdeology", "fascist"), (r"GetFactionName", "Co-Prosperity Sphere"), (r"GetAgency", "Intelligence Agency"),
    (r"Capital\.GetName|mod1440_wd_a|mod1440_of_ln_a|mod1440_wr_ln_a", "Niederschlesien"), (r"^ROOT\.GetName$|mod1440_wr_c_enemy\.GetName", "Czechoslovakia"),
    (r"GetLeader$", "Konstantin von Neurath"), (r"Leader$|GetName", "Konstantin von Neurath"),
    (r"^\?casualties|mod1440_wr_cas|mod1440_wo_cas|mod1440_wr_c_cas", "1250000"), (r"party_popularity", "100%"), (r"_war_support", "12.5%"),
    (r"surrender_progress", "100%"), (r"days_until_next_election|mod1440_wr_days|mod1440_wd_days|mod1440_wr_c_days", "1460"), (r"\?v\b", "100"),
    (r"\^num|mod1440_wd_total", "500"), (r"_level|skill|num_traits|mod1440_of_c_skill", "9"), (r"num_units|num_ships|mod1440_of_c_cmd", "240"),
    (r"mod1440_wr_c_surr", "100"), (r"mod1440_", "128"), (r"", "128"),
]


def sample(inside):
    for pattern, value in SAMPLES:
        if re.search(pattern, inside):
            return value
    return ""


def officer_scene_hide(award=False):
    """What script hides in the officers scene: a German general's file (rank 2, status 1), three traits, two
    medals, five diary lines; with award=True the Award mode with four medals of the country instead."""
    from unit_medals_table import MEDALS
    hide = ["of_arrow_up", "of_arrow_down", "of_c_none", "of_c_face", "of_c_rank_1", "of_c_rank_3", "of_c_since", "of_c_prom", "of_c_lvl",
            "of_c_tr_none", "of_c_tr_over", "of_c_tr_other", "of_ln_none", "of_c_dec_none"]
    hide += ["of_c_status_" + s for s in ("off", "cap", "grp", "fleet", "idle")]
    hide += ["of_c_c3_i1", "of_c_c4_i1"]
    for name in ["ships"] + [short for short, kind, words in SHIP_KINDS]:
        hide += ["of_c_%s%s" % (name, part) for part in ("_bg", "_l", "")]
    for k in range(TRAIT_ICONS):
        hide.append("of_c_tr_%d_x" % k)
        if k >= 3:
            hide += ["of_c_tr_%d" % k, "of_c_tr_%d_n" % k]
    filing = ["of_award_on", "of_takeback", "of_f_dec_bg", "of_f_diary_bg", "of_f_diary_title", "of_ln_order"]
    filing += ["of_c_rack_%d" % k for k in range(2)] + ["of_c_dec_%d%s" % (k, part) for k in range(2) for part in ("", "_d")]
    lines = 5
    for k in range(CARD_LINES):
        parts = ["of_ln_%d_d" % k, "of_ln_%d" % k, "of_ln_%d_s" % k, "of_ln_%d_p" % k] + ["of_ln_%d_f%d" % (k, f) for f in FAMILY_ICON]
        if k % 2:
            parts.append("of_ln_%d_bg" % k)
        if k >= lines:
            hide += parts
            continue
        family = 4 if k < 2 else 2
        hide += ["of_ln_%d_f%d" % (k, f) for f in FAMILY_ICON if f != family] + ["of_ln_%d_p" % k]
        if k < 2:
            hide.append("of_ln_%d_s" % k)
        filing += [w for w in parts if w not in hide]
    hide += ["of_c_rack_%d" % k for k in range(2, RACK)] + ["of_c_dec_%d%s" % (k, part) for k in range(2, DEC_LINES) for part in ("", "_d")]
    medals = 4
    awarding = ["of_award_off", "of_f_award_bg", "of_md_hint"]
    for k in range(MEDAL_SLOTS):
        parts = ["of_md_%d_bg" % k, "of_md_%d" % k, "of_md_%d_name" % k, "of_award_%d" % k, "of_md_%d_held" % k]
        if k >= medals:
            hide += parts
        else:
            hide.append("of_md_%d_held" % k if k >= 2 else "of_award_%d" % k)
            awarding += [w for w in parts if w not in hide]
    return hide + (filing if award else awarding)


def government_scene_hide():
    """What script hides in the government scene (the sample state of E3 check 1)."""
    hide = ["gv_leader_since", "gv_next", "gv_faction_none", "gv_sub_none", "gv_hc_none"]
    hide += ["gv_group_%s" % g for i, g in IDEOLOGIES if g != "fascism"] + ["gv_p_%d_pick" % n for n in range(1, 4)]
    hide += ["gv_rul_0_g%d" % g for g in (2, 3, 4)] + ["gv_rul_0_t%s" % t for t in "abc"]
    for k in range(1, HEADS_SLOTS):
        hide += ["gv_rul_%d%s" % (k, part) for part in ("", "_face", "_bg")] + ["gv_rul_%d_g%d" % (k, g) for g in range(1, 5)]
        hide += ["gv_rul_%d_t%s" % (k, t) for t in "abcd"]
    seat = ("_face", "_big", "_name", "_role", "_since", "_since_old")

    def seats(prefix, filled, count):
        out = []
        for k in range(count):
            if k < filled:
                out += ["gv_%s_%d_big" % (prefix, k), "gv_%s_%d_since_old" % (prefix, k)]
            else:
                out += ["gv_%s_%d%s" % (prefix, k, part) for part in seat] + ["gv_%s_%d_bg" % (prefix, k)]
        return out

    hide += seats("adv", 2, CABINET_SLOTS) + seats("hc", 1, MEMBER_SLOTS)
    # E7: Fritsch (chief of the army) and Rundstedt (high command) are generals: the game draws their faces in the
    # place of the large portrait, and the table's small one is hidden
    hide += ["gv_of_0_face", "gv_hc_0_face"]
    hide += ["gv_adv_none_%d" % k for k in range(CABINET_SLOTS) if k != 2]
    hide += ["gv_of_0_none", "gv_of_0_vacant", "gv_of_0_big", "gv_of_0_since_old"]
    for k in range(1, len(OFFICES)):
        hide += ["gv_of_%d%s" % (k, part) for part in seat]
    return hide


def government_face_rows():
    """E7: the rows of the lists of the game's faces in the government scene: the chief of the army and the first
    member of the high command are generals (Fritsch, Rundstedt)."""
    rows = dict(("gv_of_%d_gface_grid" % k, 1 if k == 0 else 0) for k in range(len(OFFICES)))
    rows.update(("gv_hc_%d_gface_grid" % k, 1 if k == 0 else 0) for k in range(MEMBER_SLOTS))
    return rows


# The War Diary's scene (E1 review): a campaign like the design's (the United States in 1943) drawn row by row. Each
# row is (date or None, family, words, what: None / ("state", name, folded or 0) / ("vp", name) / ("officer", name) /
# ("person", name), country or None, officer on the spot or None, number widget and text or None, marked).
DIARY_CAMPAIGN = [
    ("12 June, 1943", 1, "Peace with", None, "Siam", None, None, False),
    (None, 1, "Made a subject:", None, "Philippines", None, None, False),
    (None, 2, "Handed over to", ("state", "Luzon", 6), "Philippines", None, None, False),
    ("7 June, 1943", 2, "Victory point taken", ("vp", "Kagoshima"), "State of Japan", "Walter Krueger", None, False),
    (None, 2, "State taken", ("state", "Minami Kyushu", 0), "State of Japan", "Walter Krueger", None, False),
    (None, 2, "Landing in", ("state", "Kyushu", 0), None, None, None, False),
    ("2 June, 1943", 4, "Gained a skill level", ("officer", "William Halsey, Jr."), None, None, ("", "5"), False),
    (None, 4, "Decorated", ("officer", "Douglas MacArthur"), None, None, None, False),
    (None, 1, "Broke the cipher of", None, "State of Japan", None, None, False),
    ("30 May, 1943", 1, "Our casualties passed", None, None, None, ("_k", "250 000"), False),
    (None, 2, "State taken", ("state", "Chugoku", 0), "State of Japan", "Dwight D. Eisenhower", None, False),
    (None, 2, "Victory point taken", ("vp", "Hiroshima"), "State of Japan", "Dwight D. Eisenhower", None, False),
    ("27 May, 1943", 2, "Capital taken", ("state", "Kanto", 0), "State of Japan", "Douglas MacArthur", None, True),
    (None, 2, "State taken", ("state", "Shikoku", 11), "State of Japan", None, None, False),
    ("23 May, 1943", 4, "Left the service", ("officer", "Leslie McNair"), None, None, None, False),
    (None, 1, "Volunteers sent to", None, "China", None, None, False),
    ("22 May, 1943", 1, "War declared by", None, "Hungary", None, None, False),
    (None, 1, "War declared by", None, "Romania", None, None, False),
    (None, 1, "War declared by", None, "Bulgaria", None, None, False),
    ("17 May, 1943", 1, "Annexed", None, "Cuba", None, None, False),
    (None, 2, "Received from", ("state", "Cuba", 0), "Cuba", None, None, False),
    (None, 1, "Joined our faction:", None, "Brazil", None, None, False),
    ("9 May, 1943", 4, "Promoted to field marshal", ("officer", "Walter Krueger"), None, None, None, True),
    (None, 3, "Appointed", ("person", "George C. Marshall"), None, None, None, False),
    ("2 May, 1943", 2, "Victory point taken", ("vp", "Nagasaki"), "State of Japan", "Walter Krueger", None, False),
    (None, 2, "State taken", ("state", "Kyushu", 0), "State of Japan", "Walter Krueger", None, False),
    (None, 2, "Landing in", ("state", "Kyushu", 0), None, None, None, True),
    (None, 1, "War declared on", None, "Siam", None, None, False),
]
DIARY_NEW_DAYS = 1                  # the first day of the campaign was written while the window was closed


def diary_rows(rows, new_days=DIARY_NEW_DAYS):
    """The scene's "only" and "samples" of the row window for <rows> (DIARY_CAMPAIGN's shape)."""
    only, samples = {}, {}

    def put(widget, n, text=None):
        only.setdefault(widget, []).append(n)
        if text is not None:
            samples.setdefault(widget, []).append(text)

    day, band = -1, 0
    for n, (date, family, words, what, country, officer, number, marked) in enumerate(rows):
        if date:
            day += 1
            band = 1 - band
            put("wd_row_date", n, date)
        put("wd_row_new" if day < new_days else ("wd_row_stripe" if band else None), n)
        put("wd_row_icon_%d" % family, n)
        put("wd_row_event", n, words)
        if number:
            put("wd_row_n" + number[0], n, "§Y%s§!" % number[1])
        kind = what[0] if what else None
        if kind in ("state", "vp"):
            folded = kind == "state" and what[2]
            put("wd_row_go_fold" if folded else "wd_row_go", n)
            put("wd_row_a" if kind == "state" else "wd_row_point", n, "§Y%s§!" % what[1])
            if folded:
                put("wd_row_fold", n, "+%d states" % what[2])
        elif kind == "officer":
            # E7: the face of one who serves is the game's, in the list of faces; the table's for one who has left
            put("wd_row_face" if words == "Left the service" else "wd_row_gface", n)
            put("wd_row_file", n)
            put("wd_row_who", n, "§Y%s§!" % what[1])
        elif kind == "person":
            put("wd_row_name", n, "§Y%s§!" % what[1])
        if country:
            suffix = "" if what else "_near"
            put("wd_row_flag" + suffix, n)
            put("wd_row_lines" + suffix, n)
            put("wd_row_b" + suffix, n, country)
        if officer:
            put("wd_row_gcface", n)
            put("wd_row_cfile", n)
            put("wd_row_c", n, "§Y%s§!" % officer)
        put("wd_row_marked" if marked else "wd_row_mark", n)
    only.pop(None, None)
    every = ["wd_row_stripe", "wd_row_new", "wd_row_date", "wd_row_event", "wd_row_n", "wd_row_n_k", "wd_row_n_m", "wd_row_go", "wd_row_go_fold",
             "wd_row_a", "wd_row_point", "wd_row_fold", "wd_row_face", "wd_row_file", "wd_row_who", "wd_row_name", "wd_row_flag", "wd_row_lines",
             "wd_row_b", "wd_row_flag_near", "wd_row_lines_near", "wd_row_b_near", "wd_row_cface", "wd_row_cfile", "wd_row_c", "wd_row_mark",
             "wd_row_marked"] + ["wd_row_icon_%d" % f for f in FAMILY_ICON]
    for widget in every + list(DIARY_FACES):
        only.setdefault(widget, [])
    return only, samples


# E7: the two lists of faces over the diary's rows: (their row window, their grid) by the icon in it
DIARY_FACES = {"wd_row_gface": ("mod1440_records_wd_row_gface_row", "wd_row_gface_grid"),
               "wd_row_gcface": ("mod1440_records_wd_row_gcface_row", "wd_row_gcface_grid")}


def diary_faces(only, count):
    """E7: what the scene's "only" of the diary's rows says of the lists of faces moves to their own row windows;
    returns (rows, listRows, only by row window) for <count> rows."""
    rows = dict((grid, count) for window, grid in DIARY_FACES.values())
    list_rows = dict((grid, window) for window, grid in DIARY_FACES.values())
    by_window = {"mod1440_records_diary_row": dict((w, v) for w, v in only.items() if w not in DIARY_FACES)}
    by_window.update((window, {icon: only.get(icon, [])}) for icon, (window, grid) in DIARY_FACES.items())
    return rows, list_rows, by_window


def diary_scene(place, crop, shot, back):
    """The scene of the War Diary (tools/scenes/war_diary.json)."""
    only, row_samples = diary_rows(DIARY_CAMPAIGN)
    # the pane with the figures of the design (the user's save of 2026-10-16, Ground split by the review's rule)
    figures = {"wars": 33, "peace": 22, "cap": 2, "annex": 2, "subj": 17, "atwar": 11, "comm": 1, "prom": 1, "lvl": 4, "dec": 3, "gone": 2,
               "govs": 0, "trr": 39, "trh": 47}
    page = dict(("wd_f_" + name, "§Y%d§!" % value) for name, value in figures.items())
    page.update({"wd_g_st_t": "§Y59§!", "wd_g_st_x": "§Y7§!", "wd_g_vp_t": "§Y25§!", "wd_g_vp_x": "§Y0§!", "wd_g_cap_t": "§Y2§!", "wd_g_cap_x": "§Y1§!",
                 "wd_hn_auto": "§Y3§!", "wd_hn_cite": "§Y1§!", "wd_hn_last": "Last citation: §YKyushu§!, 7 June, 1943",
                 "wd_count": "lines 1 - 311 of 318", "wd_country": "United States of America",
                 "wd_since": "Kept since 3 March, 1941  -  1084 days on record", "wd_tab_0_n": "155 lines", "wd_tab_3_n": "11 at war",
                 "wd_tab_1_n": "103", "wd_ch_n": "The lines you marked, kept for good: 4 of 300.",
                 "wd_kept_0": "Main log 155 of 1000 lines, territory 178 of 1000."})
    chronicle = [("27 May, 1943", 2, "Capital taken", "s", "Kanto"), ("9 May, 1943", 4, "Promoted to field marshal", "s", "Walter Krueger"),
                 ("2 May, 1943", 2, "Landing in", "s", "Kyushu"), ("8 December, 1941", 1, "War declared by", "b", "Empire of Japan")]
    pane_hide = ["wd_ch_none_0", "wd_ch_none_1"]
    for k, (date, family, words, which, name) in enumerate(chronicle):
        page["wd_ch_%d_d" % k] = "§g%s§!" % date
        page["wd_ch_%d" % k] = words
        page["wd_ch_%d_%s" % (k, which)] = "§Y%s§!" % name
        pane_hide += ["wd_ch_%d_f%d" % (k, f) for f in FAMILY_ICON if f != family]
        pane_hide += ["wd_ch_%d_%s" % (k, s) for s in ("s", "p", "b") if s != which]
    diary_page = ["wd_none", "wd_count_state", "wd_count_country", "wd_hn_none"] + pane_hide

    # a country's lines (filter 8): the State of Japan, back to the war's first day
    follow_rows = [r for r in DIARY_CAMPAIGN if r[4] == "State of Japan"]
    dated, seen = [], set()
    for date, family, words, what, country, officer, number, marked in follow_rows:
        day = next(d for d, rows in _days(DIARY_CAMPAIGN) if (date, family, words, what, country, officer, number, marked) in rows)
        dated.append((None if day in seen else day, family, words, what, country, officer, number, marked))
        seen.add(day)
    dated.append(("8 December, 1941", 1, "War declared by", None, "State of Japan", None, None, False))
    follow_only, follow_samples = diary_rows(dated, new_days=0)
    follow_rows, face_rows, follow_by = diary_faces(follow_only, len(dated))
    page_rows, face_rows, page_by = diary_faces(only, len(DIARY_CAMPAIGN))
    follow_page = ["wd_none", "wd_count", "wd_count_state", "wd_heads_3", "wd_heads_4", "wd_hn_none"] + pane_hide

    # nothing written yet of a filter: the list empty, the chronicle's two lines, no citation
    empty_page = (["wd_count", "wd_count_state", "wd_count_country", "wd_hn_last"]
                  + ["wd_ch_%d%s" % (k, part) for k in range(WD_CHRON_LINES) for part in ("", "_d", "_bg", "_s", "_p", "_b")]
                  + ["wd_ch_%d_f%d" % (k, f) for k in range(WD_CHRON_LINES) for f in FAMILY_ICON])
    states = [
        {"name": "follow", "rows": dict(follow_rows, wd_grid=len(dated)),
         "frames": {"mod1440_records_wd": {"wd_show_all": 1, "wd_hn_cap": 2, "wd_hn_sea": 2, "wd_hn_air": 2}},
         "hide": {"mod1440_records_wd": follow_page}, "only": follow_by,
         "samples": {"mod1440_records_diary_row": follow_samples,
                     "mod1440_records_wd": dict(page, wd_count_country="§YState of Japan§!: lines 1 - 57 of 57")},
         "_note": "A click on a country's name: its lines only (filter 8), its name where the Officer head was; no filter lit."},
        {"name": "empty", "rows": dict(diary_faces({}, 0)[0], wd_grid=0), "hide": {"mod1440_records_wd": empty_page},
         "samples": {"mod1440_records_wd": dict(page, wd_ch_n="The lines you marked, kept for good: 0 of 300.")},
         "_note": "A filter with nothing written yet; no line marked; no citation."},
    ]
    return {
        "phase": "E1", "file": "mod1440_records.gui", "screenshot": shot,
        "windows": [dict(place, name="mod1440_records_wd", rows=dict(page_rows, wd_grid=len(DIARY_CAMPAIGN)),
                         listRows=dict(face_rows, wd_grid="mod1440_records_diary_row"),
                         hide=diary_page, frames={"wd_show_all": 2, "wd_hn_cap": 2, "wd_hn_sea": 2, "wd_hn_air": 2},
                         _note="A window of its own over the map, opened from the Records button of the top bar. "
                                                "The list shows a campaign like the design's; flags and faces are the renderer's samples. E7: the "
                                                "faces of serving officers are two lists of their own over the rows (the game draws each one's face); "
                                                "the left officer (Leslie McNair) shows the table's portrait."),
                    {"name": "mod1440_records_wd_row_gface_row", "skip": True, "only": page_by["mod1440_records_wd_row_gface_row"]},
                    {"name": "mod1440_records_wd_row_gcface_row", "skip": True, "only": page_by["mod1440_records_wd_row_gcface_row"]},
                    {"name": "mod1440_records_diary_row", "skip": True, "only": page_by["mod1440_records_diary_row"],
                     "_note": "Each widget is drawn in the rows script shows it in: the day on its first row, the band of the day, the new "
                              "lines of the first day on the lighter band, runs of states folded, the numbers of a line."}],
        "samples": {"mod1440_records_diary_row": row_samples, "mod1440_records_wd": page},
        "states": states,
        "setup": [{"key": "shift+j", "wait": 1.5}, {"clickWidget": "mod1440_records_wd/wd_tab_0", "wait": 1.0}],
        "teardown": back,
        "expect": ["mod1440_records_wd/wd_close", "mod1440_records_wd/wd_older", "mod1440_records_wd/wd_ch_read"],
        "crop": crop,
        "manual": ["Lines that need a war: a state and a victory point taken with the general on the spot, capitulation, landings",
                   "A landing and an airborne drop with the honour switches on: the lines in the divisions' history",
                   "A peace conference that hands states over (whether has_war_with still holds then), a civil war won, a government in exile"],
        "checklist": DIARY_CHECKLIST,
    }


def _days(rows):
    out = []
    for row in rows:
        if row[0]:
            out.append((row[0], []))
        out[-1][1].append(row)
    return out


DIARY_CHECKLIST = [
    "The title strip and the tabs as before: Germany's flag, Records, German Reich, 'Kept since 1 January, 1936 - 0 days on record'; the War Diary's tab "
    "with the gold chevrons; each tab opens its page",
    "The list: no row of its own for a day; the date (hoi_16mbs) stands on a day's first line only, every line of a day on one band, the bands of "
    "two days apart; 'The record begins' on the lighter band of a new line until the window is closed once, then on the day's band",
    "Close and open the Records after a day with a line: the new lines on the lighter band (GFX_1440p_SG_pick); does it read as 'new' against the day bands?",
    "A line about a country (mod1440_chk_war: War declared on Poland): its flag (41x26) and name; click the name: the diary shows Poland's lines only, "
    "'Poland: lines 1 - N of N' in the head bar where Officer stood, the Country and Officer heads gone, no filter lit; All brings every line back",
    "A state taken in battle (mod1440_chk_war, then mod1440_chk_state2: Danzig): 'State taken', the plate moves the camera, Poland in the Country "
    "column, the general's face and name at the right; click his name: the Officers page opens on his file",
    "A state received by treaty (mod1440_chk_treaty): 'Received from' Austria in the diary (Territory filter too), no general named; the state card of "
    "Niederschlesien: 'Received from Austria by treaty on 1 January, 1936, held 0 days' and the grey line that no troops are named; "
    "'Handed over to' Austria for the state given first",
    "A run of states (mod1440_chk_treaty_run: four states received from Austria on one day): All shows one row 'Received from <state>' with "
    "'+3 states' at the plate's right end and its tooltip; Territory lists the four lines; 'lines 1 - N of M' counts the four",
    "An officer line (mod1440_chk_level: a general gains a skill level): 'Gained a skill level' with the level reached in yellow at the right end of the "
    "words (compare with the level in the general's own window); his face and name open his file",
    "mod1440_chk_retire (the fifth general retires), then mod1440_chk_daily: 'Left the service' with his face and name; The service: Left the "
    "service 1. A second mod1440_chk_daily writes no second line",
    "mod1440_chk_cipher and mod1440_chk_exile: 'Broke the cipher of' Poland and 'Hosting the exiled government of' Poland, each with its flag "
    "(volunteers, a civil war won and fighting on need a war the check cannot cause: under manual)",
    "The pane: The campaign as banded tables under three head bars (War and peace, Ground in battle with taken and lost and a bar, the By treaty row, "
    "The service); 'At war today' equals the number of enemies on the Wars page; Wars begun and Wars ended against the Wars page's rows",
    "The chronicle: mark three lines with their boxes: the pane lists the newest marked lines (date in grey, icon, words, name); 'Read the chronicle' "
    "opens the Marked filter; unmark them all: the two lines that say how to mark",
    "Battle honours: the four switches in two rows toggle; By themselves and Cited by you as a table row; the last citation under them",
    "Kept: two lines; the count in the head bar has the Kept text as its tooltip",
    "The page arrows past 200 rows (mod1440_chk_fill fills the logs): 200 lines a page with no day rows; 'lines 1 - 200 of M'; scroll the list to "
    "its end; mod1440_chk_list_time in game.log (the folds' cost against the last check)",
    "The top bar button: a War and peace line written while the window is closed turns the count red; its tooltip says 'N new lines since you "
    "last closed the Records, K of war and peace' and 'Newest: <words> <name>, <date>' (GetTokenLocalizedKey in a tooltip); Close clears both",
    "mod1440_chk_old3 (a save of before the review), then the Records opened: mod1440_chk_sizes3 reads every log's n as long as its dates; "
    "no line is on the lighter band; no 'Left the service' line for an officer gone before",
    "error.log: no line that names the mod, no 'invalid scope for var', no 'Could not find sprite type', no unknown trigger has_war_with",
]
# --- E7 --- the War Diary's faces through the game (image = portrait, SGUI-053)
DIARY_CHECKLIST += [
    "E7 with Road to 56: after mod1440_chk_e7_generals (Himmler, Bormann, Canaris get a command) and one day, the 'Commissioned' lines: "
    "each officer's face beside his name is his own, the same as in the game's commander picker (Himmler: Road to 56's texture file; "
    "Canaris: his civilian portrait, accepted by the user), not the unknown leader",
    "E7: a state taken with a general on the spot: Keitel given Army 1 (in Brandenburg), mod1440_chk_war, then mod1440_chk_e7_take (Army 1's "
    "divisions moved to Poznan, which Germany then takes; game.log 'MOD1440 e7 take: N German divisions'): the line 'State taken Poznan' "
    "names Keitel in the Officer column with his own face (Road to 56's texture file), the same as in his army's leader view. No general on "
    "the line: mod1440_chk_e7_take_again (Poland takes it back, Germany again)",
    "E7: the faces sit exactly on their lines (no offset, none on a line without an officer) while the list scrolls with the wheel and the "
    "scrollbar; a click on an officer's face or name still opens his file; mod1440_chk_e7_log lists one face per officer line",
    "E7: an officer who left the service (mod1440_chk_e7_retire after choosing him on the Officers page, then one day): his 'Left the service' "
    "line shows the table's portrait or the unknown leader, never an empty spot",
]
# --- end E7 ---


# --- E4 round 2 --- the Wars scene (tools/scenes/wars.json): a German campaign of 14 May 1942 like the design's
# figures. The file of a war is drawn in three states: the war of today with Poland and twelve other enemies (the
# United Kingdom chosen), the finished war with Yugoslavia alone, and the finished war with Czechoslovakia and two
# others (Yugoslavia chosen). war_file_hide() follows the visible triggers of wars() for a state.
WS_TODAY = [("Poland", 12, "986", "1204.6K", "2351.0K", "21%"), ("Soviet Union", 1, "326", "2210.4K", "4870.2K", "38%")]
# (name, others, began, ours, theirs, outcome, plate frame); None: not kept
WS_DONE = [("Switzerland", 0, "1941", "61.2K", "88.0K", 4, 1), ("Sweden", 0, "1940", "34.5K", "51.9K", 3, 1), ("Lithuania", 0, "1939", "2.1K", "3.4K", 1, 3),
           ("Czechoslovakia", 2, "1938", "186.4K", "404.9K", 4, 1), ("Luxembourg", 0, "1938", "0.0K", "0.4K", 4, 1), ("Austria", 0, "1938", "1.2K", "4.6K", 2, 1),
           ("Italy", 0, "1937", "96.3K", "41.0K", 6, 2), ("Denmark", 0, "1936", None, None, 1, 3)]
WS_CAMPAIGN = {"cas_all": "3601.4K", "cas_now": "3415.0K", "inflicted": "7626.1K", "longest": "32 mo.", "surrender": "4%", "convoys": "412",
               "pride_sunk": "2", "ws_cas": "8.4%", "ws_con": "1.2%", "ws_bomb": "3.1%", "pride_lost": "1", "ace_new": "14", "ace_lost": "3", "ace_down": "6"}
# a line of the War Diary in a file: (date, family, words, sa, place)
WS_LINES_POLAND = [
    ("1942.5.12", 2, "State taken from", 2, "Kent"), ("1942.5.9", 2, "Victory point taken from", 3, "Dover"),
    ("1942.5.4", 2, "State taken from", 2, "Sussex"), ("1942.4.27", 2, "Victory point taken from", 3, "Cyrenaica"),
    ("1942.4.18", 2, "State taken from", 2, "Peloponnese"), ("1942.4.11", 2, "State taken from", 2, "Crete"),
    ("1942.4.6", 2, "Victory point taken from", 3, "Tobruk"), ("1942.3.30", 2, "State taken from", 2, "Fezzan"),
    ("1942.3.21", 2, "Victory point taken from", 3, "Benghazi"), ("1942.3.14", 2, "State taken from", 2, "Malta"),
    ("1942.3.2", 2, "State taken from", 2, "Valletta"), ("1942.2.19", 2, "Victory point taken from", 3, "Gibraltar"),
    ("1942.2.8", 2, "State taken from", 2, "Cyprus"), ("1942.1.30", 2, "Victory point taken from", 3, "Nicosia"),
    ("1942.1.21", 2, "State taken from", 2, "Iraq"), ("1942.1.9", 2, "State taken from", 2, "Mosul"),
    ("1941.12.28", 2, "Victory point taken from", 3, "Kuwait"), ("1941.12.15", 2, "State taken from", 2, "Aden"),
    ("1941.12.2", 2, "Victory point taken from", 3, "Sinai"), ("1941.11.20", 2, "State taken from", 2, "Suez"),
    ("1941.5.2", 1, "Capitulated:", 0, "Yugoslavia"), ("1940.6.22", 1, "Capitulated:", 0, "France"), ("1939.10.6", 1, "Capitulated:", 0, "Poland")]
WS_LINES_YUGOSLAVIA = [
    ("1939.2.12", 2, "State taken from", 2, "Skopje"), ("1939.2.10", 2, "Victory point taken from", 3, "Vardar"),
    ("1939.2.7", 2, "State taken from", 2, "Kosovo"), ("1939.2.3", 2, "Victory point taken from", 3, "Pristina"),
    ("1939.1.30", 2, "State taken from", 2, "Montenegro"), ("1939.1.26", 2, "State taken from", 2, "Cetinje"),
    ("1939.1.21", 2, "Victory point taken from", 3, "Dalmatia"), ("1939.1.17", 2, "State taken from", 2, "Split"),
    ("1939.1.12", 2, "Victory point taken from", 3, "Herzegovina"), ("1939.1.8", 2, "State taken from", 2, "Mostar"),
    ("1939.1.3", 2, "State taken from", 2, "Sarajevo"), ("1938.12.29", 2, "Victory point taken from", 3, "Bosnia"),
    ("1938.12.23", 2, "State taken from", 2, "Banja Luka"), ("1938.12.18", 2, "Victory point taken from", 3, "Croatia"),
    ("1938.12.12", 2, "State taken from", 2, "Zagreb"), ("1938.12.7", 2, "State taken from", 2, "Slavonia"),
    ("1938.12.2", 2, "Victory point taken from", 3, "Osijek"), ("1938.11.26", 2, "State taken from", 2, "Nis"),
    ("1938.11.20", 2, "Victory point taken from", 3, "Morava"), ("1938.11.14", 2, "State taken from", 2, "Kragujevac"),
    ("1938.11.8", 2, "State taken from", 2, "Sumadija"), ("1938.11.2", 2, "Victory point taken from", 3, "Beograd"),
    ("1938.10.27", 2, "State taken from", 2, "Zemun"), ("1938.10.21", 2, "Victory point taken from", 3, "Banat"),
    ("1938.10.15", 2, "State taken from", 2, "Novi Sad"), ("1938.10.10", 2, "State taken from", 2, "Vojvodina"),
    ("1938.10.6", 2, "Victory point taken from", 3, "Subotica"), ("1938.10.5", 2, "State taken from", 2, "Slovenia"),
    ("1938.10.4", 2, "Victory point taken from", 3, "Ljubljana"), ("1938.10.4", 2, "State taken from", 2, "Maribor"),
    ("1938.10.4", 1, "War declared on", 0, "Yugoslavia")]
WS_LINES_CZECHOSLOVAKIA = [
    ("1939.2.11", 2, "State taken from", 2, "Vojvodina"), ("1939.2.8", 2, "Victory point taken from", 3, "Novi Sad"),
    ("1939.2.2", 2, "State taken from", 2, "Banat"), ("1939.1.28", 2, "Victory point taken from", 3, "Zemun"),
    ("1939.1.21", 2, "State taken from", 2, "Beograd"), ("1939.1.14", 2, "State taken from", 2, "Sumadija"),
    ("1939.1.9", 2, "Victory point taken from", 3, "Kragujevac"), ("1939.1.2", 2, "State taken from", 2, "Bosnia"),
    ("1938.12.27", 2, "Victory point taken from", 3, "Sarajevo"), ("1938.12.19", 2, "State taken from", 2, "Morava"),
    ("1938.12.12", 2, "State taken from", 2, "Nis"), ("1938.12.2", 2, "Victory point taken from", 3, "Bukovina"),
    ("1938.11.26", 2, "State taken from", 2, "Slovakia"), ("1938.11.18", 2, "Victory point taken from", 3, "Bratislava"),
    ("1938.11.9", 2, "State taken from", 2, "Moravia"), ("1938.11.1", 2, "State taken from", 2, "Brno"),
    ("1938.10.26", 2, "Victory point taken from", 3, "Bohemia"), ("1938.10.20", 2, "State taken from", 2, "Plzen"),
    ("1938.10.18", 1, "Capitulated:", 0, "Czechoslovakia"), ("1938.10.4", 1, "War declared by", 0, "Yugoslavia"),
    ("1938.10.3", 1, "War declared by", 0, "Romania"), ("1938.10.1", 1, "War declared on", 0, "Czechoslovakia")]
WS_COMMANDERS = {
    "page": [("Erich von Manstein", 1, 21, 30, 1), ("Heinz Guderian", 2, 14, 19, 0), ("Gerd von Rundstedt", 1, 11, 15, 1),
             ("Ewald von Kleist", 2, 9, 12, 0), ("Walter Model", 2, 5, 6, 0)],
    "file": [("Erich von Manstein", 1, 4, 6, 1), ("Ewald von Kleist", 2, 3, 4, 0), ("Heinz Guderian", 2, 2, 3, 0),
             ("Fedor von Bock", 1, 1, 2, 0), ("Walter Model", 2, 1, 1, 0)],
    "three": [("Erich von Manstein", 1, 5, 8, 1), ("Heinz Guderian", 2, 4, 6, 1), ("Gerd von Rundstedt", 1, 2, 3, 0), ("Ewald von Kleist", 2, 1, 1, 0)],
}
# the enemies table: (name, joined, end: outcome number or a surrender text, theirs, ours, states)
WS_ENEMIES = {
    "page": [("Poland", "1939.9.1", 2, "411.8K", "96.4K", "21 : 0"), ("United Kingdom", "1939.9.3", "21%", "602.3K", "388.1K", "6 : 3"),
             ("France", "1939.9.3", 2, "689.0K", "301.7K", "19 : 0"), ("British Raj", "1939.9.3", "4%", "88.2K", "60.4K", "0 : 0"),
             ("Australia", "1939.9.3", "2%", "41.6K", "32.0K", "0 : 0")],
    "three": [("Czechoslovakia", "1938.10.1", 4, "311.9K", "142.6K", "9 : 0"), ("Romania", "1938.10.3", 1, "40.7K", "28.1K", "0 : 1"),
              ("Yugoslavia", "1938.10.4", 3, "52.3K", "15.7K", "3 : 0")],
}
WS_PICKED = {"page": 1, "three": 2}


def war_file_hide(st):
    """The widgets of the file that script hides in state <st>: open, count, utw/ttw (one head at both ends), topen
    (the chosen enemy still fights), fb and g (by face u0 u1 t0 t1: no portrait, ideology group), nr, kunk, lines
    [(family, sa)], commanders [rank]."""
    hide = ["wr_c_none", "wr_now_none", "wr_old_none"]
    one = st["count"] == 1
    lines, ranks = st["lines"], st["commanders"]
    hide += ["wr_k_none"] if ranks else []
    hide += ["wr_ln_none"] if lines else []
    hide.append("wr_c_them_n" if one else "wr_c_them")
    hide += ["wr_c_side_n"] if one else []
    when = "now" if st["open"] else "past"
    hide += ["wr_c_when_" + w for w in ("now", "now_old", "past", "past_old") if w != when]
    for k in range(WR_MARKS):
        fam = lines[k][0] if k < len(lines) else None
        hide += ["wr_c_mark_%d_%s" % (k, suffix) for suffix in "wt" if fam is None or (suffix == "w") != (fam == 1)]
    groups = range(1, len(IDEOLOGIES) + 1)
    for s in "ut":
        twin = st[s + "tw"]
        live = st["open"] if s == "u" else st["topen"]
        boxes = [("u0", True), ("u1", not twin)] if s == "u" else [("t0", not twin), ("t1", True)]
        for face, shown_box in boxes:
            name = "wr_c_face_" + face
            fallback = [name + "_fb", name + "_fb_flag"] + ["%s_fb_g%d" % (name, g) for g in groups]
            if not shown_box:
                hide += [name] + fallback
            elif st["fb"].get(face):
                hide += [name] + ["%s_fb_g%d" % (name, g) for g in groups if g != st["g"][face]]
            else:
                hide += fallback
        for mode in ("two", "twin"):
            p = "wr_c_%s_%s" % (s, mode)
            ends = ("0", "1") if mode == "two" else ("0",)
            words = ["_w_start", "_w_today", "_w_end"] if mode == "two" else ["_w_live", "_w_dead"]
            every = [p + "_c"] + [p + w for w in words]
            for n in ends:
                every += ["%s_l%s" % (p, n), "%s_l%s_nr" % (p, n)] + ["%s_i%s_g%d%s" % (p, n, g, i) for g in groups for i in ("", "_i")]
            if (mode == "twin") != bool(twin):
                hide += every
                continue
            hide += [p + w for w in words if (w in ("_w_today", "_w_live") and not live) or (w in ("_w_end", "_w_dead") and live)]
            for n in ends:
                hide.append("%s_l%s%s" % (p, n, "" if st["nr"].get(s + n) else "_nr"))
                hide += ["%s_i%s_g%d%s" % (p, n, g, i) for g in groups for i in ("", "_i") if g != st["g"][s + n]]
    hide += ["wr_c_kus", "wr_c_kthem"] if st["kunk"] else ["wr_c_kus_none", "wr_c_kthem_none"]
    row4 = ("surr" if st["open"] else "end") if one else "gave"
    hide += ["wr_c_%s%s" % (x, part) for x in ("surr", "end", "gave") if x != row4 for part in ("", "_l")]
    for k in range(WR_COMMANDERS):
        # E7: the sample's commanders serve: the game draws their faces (war_face_rows()), the table's portraits are hidden
        hide.append("wr_k_%d_face" % k)
        names = (["wr_k_%d_stripe" % k] if k % 2 else []) + ["wr_k_%d" % k] + ["wr_k_%d_%s" % (k, p) for x, p, w in WF_TALLY]
        rank_names = ["wr_k_%d_rank_%d" % (k, r) for r in (1, 2, 3)]
        hide += names + rank_names if k >= len(ranks) else [w for r, w in enumerate(rank_names, start=1) if r != ranks[k]]

    def column(prefix, first, count, active):
        out = []
        for n in range(count):
            k = first + n
            w = "%s_%d" % (prefix, k)
            every = ([w + "_bg"] if n % 2 else []) + [w + "_d", w + "_w", w + "_t", w, w + "_go", w + "_s", w + "_p", w + "_b"]
            if not active or k >= len(lines):
                out += every
                continue
            fam, sa = lines[k]
            out.append(w + ("_t" if fam == 1 else "_w"))
            out += [w + "_go", w + "_s", w + "_p"] if sa < 2 else [w + ("_p" if sa == 2 else "_s"), w + "_b"]
        return out

    hide += column("wr_ln", 0, WR_LEFT_LINES, True)
    hide += column("wr_l1", WR_LEFT_LINES, WR_LINES - WR_LEFT_LINES, one)
    hide += column("wr_l2", WR_LEFT_LINES, WR_RIGHT_SEVERAL, not one)
    if not (one and len(lines) > WR_LEFT_LINES):
        hide += ["wr_l1_head", "wr_l1_head_t"]
    if one or len(lines) <= WR_LEFT_LINES:
        hide += ["wr_l2_head", "wr_l2_head_t"]
    if one:
        hide += ["wr_en_head", "wr_en_list"] + ["wr_en_h_" + n for n in ("enemy", "joined", "end", "theirs", "ours", "states")]
    return hide


def war_file_samples(st, lines, commanders, words):
    """The texts of the file in state <st>: <words> by widget, then the lines and the commanders."""
    out = dict(words)
    one = st["count"] == 1
    for k, (date, fam, kind, sa, place) in enumerate(lines):
        prefix = "wr_ln" if k < WR_LEFT_LINES else ("wr_l1" if one else "wr_l2")
        w = "%s_%d" % (prefix, k)
        out[w + "_d"] = date
        out[w] = kind
        if place:
            out[w + {0: "_b", 1: "_b", 2: "_s", 3: "_p"}[sa]] = "§Y%s§!" % place
    for k, (name, rank, st_, vp, cap) in enumerate(commanders):
        out["wr_k_%d" % k] = "§Y%s§!" % name
        out.update({"wr_k_%d_st" % k: str(st_), "wr_k_%d_vp" % k: str(vp), "wr_k_%d_cap" % k: str(cap)})
    return out


def war_face_rows(st):
    """E7: the rows of the five lists of the commanders' faces in state <st>: one per commander the file names."""
    return dict(("wr_k_%d_gface_grid" % k, 1 if k < len(st["commanders"]) else 0) for k in range(WR_COMMANDERS))


def war_marks(count):
    """The marks of the track spread over it as script places them (x by property), the newest at the right."""
    n = min(count, WR_MARKS)
    span = WF_TRACK_W - 4 - WF_MARK
    return dict(("wr_c_mark_%d_%s" % (k, suffix), [WF_TRACK_X + 2 + int(span * (n - 1 - k) / max(1, n - 1.0)), WF_TRACK_Y + 3])
                for k in range(n) for suffix in "wt")


def war_list_scene():
    """The two lists: rows, only and samples of their row windows, and the plates' frames."""
    now_rows = {"wr_row_enemy": ["§Y%s§!" % r[0] for r in WS_TODAY], "wr_row_more": ["+%d" % r[1] for r in WS_TODAY if r[1]],
                "wr_row_days": [r[2] for r in WS_TODAY], "wr_row_kus": [r[3] for r in WS_TODAY], "wr_row_kthem": [r[4] for r in WS_TODAY],
                "wr_row_surr": [r[5] for r in WS_TODAY]}
    now_only = {"wr_row_pick": [0], "wr_row_more": [n for n, r in enumerate(WS_TODAY) if r[1]], "wr_row_kus_none": [], "wr_row_kthem_none": []}
    kept = [n for n, r in enumerate(WS_DONE) if r[3] is not None]
    done_rows = {"wo_row_enemy": ["§Y%s§!" % r[0] for r in WS_DONE], "wo_row_more": ["+%d" % r[1] for r in WS_DONE if r[1]],
                 "wo_row_year": [r[2] for r in WS_DONE], "wo_row_kus": [WS_DONE[n][3] for n in kept], "wo_row_kthem": [WS_DONE[n][4] for n in kept]}
    done_only = {"wo_row_pick": [], "wo_row_more": [n for n, r in enumerate(WS_DONE) if r[1]],
                 "wo_row_kus": kept, "wo_row_kthem": kept,
                 "wo_row_kus_none": [n for n, r in enumerate(WS_DONE) if r[3] is None],
                 "wo_row_kthem_none": [n for n, r in enumerate(WS_DONE) if r[3] is None]}
    done_only.update(("wo_row_end_%d" % oc, [n for n, r in enumerate(WS_DONE) if r[5] == oc]) for oc in OUTCOME_ICON)
    return now_rows, now_only, done_rows, done_only, [r[6] for r in WS_DONE]


def enemy_rows_scene(which):
    rows = WS_ENEMIES[which]
    picked = WS_PICKED[which]
    only = {"wr_en_pick": [picked], "wr_en_stripe": [n for n in range(len(rows)) if n % 2 and n != picked],
            "wr_en_surr": [n for n, r in enumerate(rows) if isinstance(r[2], str)],
            "wr_en_theirs_none": [], "wr_en_ours_none": []}
    only.update(("wr_en_end_%d" % oc, [n for n, r in enumerate(rows) if r[2] == oc]) for oc in OUTCOME_ICON)
    samples = {"wr_en_name": ["§Y%s§!" % r[0] for r in rows], "wr_en_joined": [r[1] for r in rows],
               "wr_en_surr": [r[2] for r in rows if isinstance(r[2], str)], "wr_en_theirs": [r[3] for r in rows],
               "wr_en_ours": [r[4] for r in rows], "wr_en_states": [r[5] for r in rows]}
    return only, samples


def wars_scene(place, crop, shot, back, setup):
    groups = {"fascism": 1, "democratic": 2, "communism": 3, "neutrality": 4}
    page = {"open": True, "count": 13, "utw": True, "ttw": False, "topen": True, "fb": {}, "nr": {}, "kunk": False,
            "g": {"u0": 1, "u1": 1, "t0": 2, "t1": 2}, "lines": [(l[1], l[3]) for l in WS_LINES_POLAND],
            "commanders": [c[1] for c in WS_COMMANDERS["page"]]}
    yug = {"open": False, "count": 1, "utw": True, "ttw": False, "topen": False, "fb": {"t1": 1}, "nr": {}, "kunk": False,
           "g": {"u0": 1, "u1": 1, "t0": 4, "t1": 4}, "lines": [(l[1], l[3]) for l in WS_LINES_YUGOSLAVIA],
           "commanders": [c[1] for c in WS_COMMANDERS["file"]]}
    three = dict(yug, count=3, lines=[(l[1], l[3]) for l in WS_LINES_CZECHOSLOVAKIA], commanders=[c[1] for c in WS_COMMANDERS["three"]])
    # E4 fix round 1: a finished war of a save migrated from the build before: their heads not recorded, the dead not kept
    unrecorded = dict(yug, ttw=True, fb={"t1": 1}, nr={"t0": 1}, kunk=True, g={"u0": 1, "u1": 1, "t0": 0, "t1": 0})
    campaign = dict(("wr_f_" + name, value) for name, value in WS_CAMPAIGN.items())
    page_words = dict(campaign, **{
        "wr_c_title": "The war with Poland", "wr_c_us": "German Reich", "wr_c_them_n": "Poland +12",
        "wr_c_when_now": "1 September, 1939  -  today  -  986 days", "wr_c_track_from": "1939.9.1", "wr_c_track_to": "1942.5.14",
        "wr_c_side_n": "13 enemies", "wr_c_u_twin_c": "§YGerman Reich§!", "wr_c_u_twin_l0": "§YAdolf Hitler§!",
        "wr_c_t_two_c": "§YUnited Kingdom§!", "wr_c_t_two_l0": "§YNeville Chamberlain§!", "wr_c_t_two_l1": "§YWinston Churchill§!",
        "wr_c_kus": "1204.6K", "wr_c_taken": "63", "wr_c_vpt": "88", "wr_c_capt": "7",
        "wr_c_kthem": "2351.0K", "wr_c_lost": "3", "wr_c_vpl": "5", "wr_c_gave": "7 of 13"})
    yug_words = dict(campaign, **{
        "wr_c_title": "The war with Yugoslavia", "wr_c_us": "German Reich", "wr_c_them": "Yugoslavia",
        "wr_c_when_past": "4 October, 1938  -  12 February, 1939  -  131 days", "wr_c_track_from": "1938.10.4", "wr_c_track_to": "1939.2.12",
        "wr_c_u_twin_c": "§YGerman Reich§!", "wr_c_u_twin_l0": "§YAdolf Hitler§!",
        "wr_c_t_two_c": "§YYugoslavia§!", "wr_c_t_two_l0": "§YPrince Paul§!", "wr_c_t_two_l1": "§YDragisa Cvetkovic§!",
        "wr_c_kus": "118.3K", "wr_c_taken": "11", "wr_c_vpt": "16", "wr_c_capt": "1",
        "wr_c_kthem": "352.6K", "wr_c_lost": "0", "wr_c_vpl": "1", "wr_c_end": "Made a subject"})
    three_words = dict(yug_words, **{
        "wr_c_title": "The war with Czechoslovakia", "wr_c_them_n": "Czechoslovakia +2", "wr_c_side_n": "3 enemies",
        "wr_c_when_past": "1 October, 1938  -  12 February, 1939  -  134 days", "wr_c_track_from": "1938.10.1",
        "wr_c_kus": "186.4K", "wr_c_taken": "12", "wr_c_vpt": "18", "wr_c_capt": "1",
        "wr_c_kthem": "404.9K", "wr_c_lost": "1", "wr_c_vpl": "2", "wr_c_gave": "2 of 3"})
    unrecorded_words = dict(yug_words, **{
        "wr_c_title": "The war with Austria", "wr_c_them": "Austria", "wr_c_when_past": "4 October, 1938  -  12 February, 1939  -  131 days",
        "wr_c_t_twin_c": "§YAustria§!", "wr_c_end": "Capitulated"})
    now_rows, now_only, done_rows, done_only, frames = war_list_scene()
    page_only, page_enemies = enemy_rows_scene("page")
    three_only, three_enemies = enemy_rows_scene("three")
    window = "mod1440_records_wr"
    lists = {"wr_now_grid": len(WS_TODAY), "wr_old_grid": len(WS_DONE)}
    list_rows = {"wr_now_grid": "mod1440_records_war_row", "wr_old_grid": "mod1440_records_past_war_row", "wr_en_grid": "mod1440_records_enemy_row"}
    states = [
        {"name": "file", "rows": dict(lists, wr_en_grid=0, **war_face_rows(yug)), "hide": {window: war_file_hide(yug)}, "place": {window: war_marks(len(yug["lines"]))},
         "samples": {window: war_file_samples(yug, WS_LINES_YUGOSLAVIA, WS_COMMANDERS["file"], yug_words)},
         "_note": "The finished war with Yugoslavia alone (1938-39): Hitler throughout, Prince Paul at the start and a leader with no portrait the game "
                  "can name at the end (the flag box); How it ended in the figures; no enemies table, the War Diary runs on into the right column."},
        {"name": "three", "rows": dict(lists, wr_en_grid=len(WS_ENEMIES["three"]), **war_face_rows(three)), "hide": {window: war_file_hide(three)},
         "place": {window: war_marks(len(three["lines"]))},
         "only": {"mod1440_records_enemy_row": three_only},
         "samples": {window: war_file_samples(three, WS_LINES_CZECHOSLOVAKIA, WS_COMMANDERS["three"], three_words),
                     "mod1440_records_enemy_row": three_enemies},
         "_note": "The finished war with Czechoslovakia and two other enemies, Yugoslavia chosen in the enemies table."},
        {"name": "unrecorded", "rows": dict(lists, wr_en_grid=0, **war_face_rows(unrecorded)), "hide": {window: war_file_hide(unrecorded)},
         "place": {window: war_marks(len(unrecorded["lines"]))},
         "samples": {window: war_file_samples(unrecorded, WS_LINES_YUGOSLAVIA, WS_COMMANDERS["file"], unrecorded_words)},
         "_note": "E4 fix round 1: a finished war of a migrated save: neither of their heads recorded, so one flag box, 'Throughout the war', "
                  "'Not recorded'; the dead not kept (the dash)."},
    ]
    return {
        "phase": "E4", "file": "mod1440_records.gui", "screenshot": shot,
        "windows": [dict(place, name=window, rows=dict(lists, wr_en_grid=len(WS_ENEMIES["page"]), **war_face_rows(page)),
                         listRows=dict(list_rows, **dict(("wr_k_%d_gface_grid" % k, "mod1440_records_wr_k_gface_row") for k in range(WR_COMMANDERS))),
                         hide=war_file_hide(page), place=war_marks(len(page["lines"])),
                         _note="A German campaign of 14 May 1942: the war of today with Poland and twelve other enemies, the United Kingdom chosen in "
                               "the enemies table. Flags and portraits are the renderer's placeholders (script names them); the marks of the track "
                               "stand where script puts them (x by property)."),
                    {"name": "mod1440_records_war_row", "skip": True, "only": now_only},
                    {"name": "mod1440_records_past_war_row", "skip": True, "only": done_only, "frames": {"wo_row_plate": frames}},
                    {"name": "mod1440_records_enemy_row", "skip": True, "only": page_only},
                    {"name": "mod1440_records_wr_k_gface_row", "skip": True}],
        "samples": {window: war_file_samples(page, WS_LINES_POLAND, WS_COMMANDERS["page"], page_words),
                    "mod1440_records_war_row": now_rows, "mod1440_records_past_war_row": done_rows, "mod1440_records_enemy_row": page_enemies},
        "states": states,
        "setup": setup,
        "teardown": [{"clickWidget": "mod1440_records_wr/wr_tab_0", "wait": 0.8}] + back,
        "expect": ["mod1440_records_wr/wr_close"],
        "crop": crop,
        "manual": ["A war that runs for weeks with fighting: the dead of both sides against the war overview's casualties",
                   "A real alliance war (the Allies): several enemies joining over days, one of them capitulating while the war goes on",
                   "An existing save of the build before E4 round 2 with finished and running wars: the migration (rows grouped, dead not kept, "
                   "leaders from the Government page)",
                   "Commanders who took states and points in a war: they need fighting, or mod1440_chk_state2 with a general in the state"],
        "checklist": WARS_CHECKLIST,
    }


WARS_CHECKLIST_E7 = [
    "E7 with Road to 56: in the file of the war with Poland after mod1440_chk_e7_take (and a day), the faces under "
    "'Our commanders in this war' are each general's own, the same as in his army's leader view (34x46); mod1440_chk_e7_log: 'war k 1 ...'",
    "E7: a file with fewer than five commanders shows no face on the empty lines; a war with none shows only 'None of your generals ...'",
]
WARS_CHECKLIST = WARS_CHECKLIST_E7 + [
    "The page in the steel look: three steel cards in the left column (The campaign 548x220, Wars of today 548x188, Finished wars 548x670), "
    "6 apart, each with a head band of 27 holding its title and the column heads (Days / Our dead / Their dead / Surr.; Began / Our dead / Their dead / End); "
    "the window's ground, title strip and tabs unchanged; the Wars tab's tooltip 'One row per war, its enemies joined'",
    "The campaign table: 14 figures in two columns, bands on rows 2, 4, 6. Compare 'Casualties, all wars' with National Figures' 'Casualties, all "
    "wars'; 'in wars of today' with the war overview's casualties of your side; Our surrender with the war overview's bar; 'Casualties we inflicted' "
    "with the sum of Their dead over both lists",
    "Declare war on Poland (effect mod1440_chk_war), run 3 days: one red plate under Wars of today with Poland's flag and name, Days 3, Our dead and "
    "Their dead in K with one decimal, Surr. as the war overview's capitulation bar of Poland; 'At peace.' gone",
    "Grouping (has_war_together_with): effect mod1440_chk_ally_join (the United Kingdom and France join Poland's side), run 1 day: still ONE plate, "
    "'Poland +2'; effect mod1440_chk_wr_log: game.log 'MOD1440 wr: row' gives POL, ENG and FRA the same grp and role 1. Then mod1440_chk_war2 "
    "(Czechoslovakia, a war of its own): a second plate, its own grp",
    "The file of the war: 'The war with Poland', both flags, 'German Reich' and 'Poland +2' in hoi_24header, '1 January, 1936 - today - N days'; "
    "the track and its marks; Their side '3 enemies'; the enemies table, 3 rows (flag, name, Joined, surrender %, Their dead, Our dead, States), Poland "
    "on the lighter band; click the United Kingdom: its row lights and Their side shows its head of government (Chamberlain)",
    "Casualties (casualties_inflicted_by, faults 1 and 3): after some days of fighting, mod1440_chk_wr_log: each row's kus/kthem and 'now' "
    "readings in thousands; compare a one-enemy war's Our dead and Their dead with the war overview's casualties of each participant (the "
    "difference: the dead no enemy caused) and write both numbers down; the plate, the file's 'Casualties, by their hand / by our hand' and the "
    "enemies table's columns agree with the sums",
    "meta_trigger with numbers from variables: after Reloading Database and a daily round, error.log has no line about meta_trigger, "
    "casualties_inflicted_by, a '[N]' or '[O]' placeholder or a parse error; mod1440_chk_kread_time: the time of 100 full readings between two game.log lines",
    "The peace (mod1440_chk_peace: white peace with Poland), run 1 day: Poland's row leaves the war of today if the war goes on, or the war moves to "
    "Finished wars on a blue plate with the peace icon; Our dead and Their dead keep the values of the day before, NOT 0 (fault 1); "
    "mod1440_chk_wr_log after the peace: the 'now' reading tells whether casualties_inflicted_by keeps its value after a peace or falls to 0 (write it down)",
    "A second war with Poland after the peace (mod1440_chk_war again, 2 days): a plate of its own; its dead count from its first day (the reading of "
    "that day is its base, kus0 in the log); the first war's file keeps its numbers, and its War Diary lines stop at its last day (designer's fault 3)",
    "Kept heads of government (fault 2): during a war, mod1440_chk_leader_change (Poland's head of government retired), run 1 day: Poland's row "
    "keeps the head of the first day (lt0) and the new one (lt1) in mod1440_chk_wr_log; its file shows 'At the start' and 'Today', two portraits. "
    "After the peace, mod1440_chk_leader_change_us (ours retired): the finished war still shows our head of that time, 'Throughout the war', one portrait",
    "An annexed enemy (mod1440_chk_war2, mod1440_chk_annex, 1 day): a green plate with the annex icon; its file still shows Czechoslovakia's head "
    "of government at the start and the end with his portrait (no 'This country is no more')",
    "The flag box: a head of government the game has no portrait for shows the country's flag (82x52) on the dark inset with the ideology icon "
    "under it, tooltip 'No portrait the game can name'",
    "A finished war of one enemy: no enemies table; the War Diary runs from the left column (10 lines) into the right one (up to 21 lines, "
    "'In the War Diary, continued'); 'How it ended' in the fourth figure row with the outcome's words",
    "'All its lines' in the War Diary strip: the War Diary opens filtered to the chosen enemy ('<country>: lines 1 - N of N')",
    "A place in the file's War Diary is a button: the camera moves to it and the Records close",
    "Migration of an existing save: effect mod1440_chk_old4 (the rows as the build before left them), open the Records: game.log 'the rows of wr "
    "... wo were given their wars, casualties and leaders'; mod1440_chk_sizes4 logs every new part as long as the rows; the old finished wars show "
    "the dash in both dead slots (tooltip 'Not kept'), an enemy fought once and not at war now may show the game's value instead; rows that ended "
    "on the same day are one plate; our heads of government come from the Government page, theirs 'Not recorded' at the start",
    "The lists scroll with the wheel: Finished wars past 12 plates, the enemies table past 5 rows",
    "error.log: no line that names the mod, no 'invalid scope for var', no 'Could not find sprite type' (GFX_1440p_WR_*, "
    "GFX_1440p_SG_inset_125x168), no unknown trigger or effect has_war_together_with, has_offensive_war_with, casualties_inflicted_by, is_subject_of",
]
# --- end E4 round 2 ---


def scenes():
    from unit_medals_table import MEDALS
    others = sorted(set(m[1] for m in MEDALS) - {"ger"})
    place = {"at": [REC_X, REC_Y], "freeWindow": True}
    crop = [REC_X - 10, REC_Y - 10, REC_W + 20, REC_H + 20]
    shot = "reference/vanilla/theatre_bar.jpg"
    back = [{"key": "shift+j", "wait": 0.8}]

    def tab(n):
        return [{"key": "shift+j", "wait": 1.5}, {"clickWidget": "mod1440_records_wd/wd_tab_%d" % n, "scene": "war_diary", "wait": 1.2}]

    def subjects(prefix, count):
        return ["%s_%d_p" % (prefix, k) for k in range(count)]

    officer_hide = officer_scene_hide()

    return {
        "war_diary": diary_scene(place, crop, shot, back),
        "officers": {
            "phase": "E2", "file": "mod1440_records.gui", "screenshot": shot,
            "windows": [dict(place, name="mod1440_records_of", rows={"of_grid": 21, "of_c_gface_grid": 1},
                             listRows={"of_grid": "mod1440_records_officer_row", "of_c_gface_grid": "mod1440_records_of_c_gface_row"},
                             hide=officer_hide, _note="The file shows a German general with three traits, two medals and five lines of the War Diary; script hides the twins of his rank, status and command, the admiral's plates and the Award mode. A portrait is the renderer's unknown leader: in the game each serving officer's row and his file draw his own face (E7, image = portrait), the table's portrait only for one who has left; a trait icon is a sample until script names the trait."),
                        {"name": "mod1440_records_of_c_gface_row", "skip": True},
                        {"name": "mod1440_records_officer_row", "skip": True,
                         "hide": ["of_row_pick", "of_row_name_sel", "of_row_face_table", "of_cell_c3_navy", "of_cell_c4_navy", "of_cell_cmd_navy", "of_row_tr_3", "of_row_tr_4",
                                  "of_row_tr_5", "of_row_tr_more", "of_row_md_2"]
                         + ["of_row_st_" + suffix for suffix, words, condition in officer_status() if suffix != "gen_cmd"]}],
            "setup": tab(1),
            "teardown": [{"clickWidget": "mod1440_records_of/of_tab_0", "wait": 0.8}] + back,
            "expect": ["mod1440_records_of/of_close", "mod1440_records_of/of_sort_skill"],
            "crop": crop,
            "manual": ["Battles won and lost, states and victory points taken: they need fighting", "A general the game made up: he shows the unknown leader",
                       "A captured general, an army group, an admiral's ship kinds: they need a war or a fleet"],
            "checklist": [
                "Each row shows its officer's portrait, his rank and status under the name, and his traits as the game's icons (compare three officers with the game's own general window)",
                "The column heads show the game's attack, defence, planning and logistics icons; a click on each sorts, a second click turns the order",
                "A click anywhere on an officer's portrait or name opens his file and marks his row, the name in yellow",
                "The file: portrait, rank and status, the five level plates with their icons, Divisions/Battalions/Fighting/Armoured/Planning against the game's army view",
                "Traits: icon and name of each, and \"N of M he can take\"; note what num_max_traits gives",
                "Planning: is it shown as a percentage (0 to 100%)?",
                "Award... shows the country's medals over the decorations and diary cards; Award one; the plate says awarded with the date; Back to his file shows the medal on the rack at full size and in his row at half size",
                "Take back last; choosing another officer ends the Award mode",
                "An admiral (Raeder): manoeuvring and coordination icons, Ships and the four ship kinds",
                "error.log: no line about has_trait, a sprite GFX_trait_ or GFX_1440p_medal_, or an array index",
                # --- E7 ---
                "E7 with Road to 56: every row's face is the officer's own, as the game's Officer Corps lists and commander picker show him: "
                "Wilhelm Keitel and Franz Halder (texture files of Road to 56, the unknown leader before E7), Rundstedt, Manstein; the admirals "
                "Raeder, Doenitz and Otto Ciliax (texture file) as in the Officer Corps' Admirals list",
                "E7: after mod1440_chk_e7_generals (one day, or a click on All): Heinrich Himmler (texture file), Martin Bormann and Wilhelm Canaris "
                "(his civilian portrait, as the commander picker) as rows with their own faces",
                "E7: click Keitel: his file shows his own face at full size (156x210); click Himmler: the same in his file",
                "E7: choose an officer, effect mod1440_chk_e7_retire, one day, filter Former: his row and his file show the table's portrait "
                "(or the unknown leader for one the table lacks), not the game's unknown man; mod1440_chk_e7_log: 'file 0'. game.log at the "
                "effect: 'MOD1440 e7 retired <name>: is_unit_leader no' (not known before; 'yes' is a finding: the pages would draw him as the unknown man)",
                "E7 gate B: the faces hold on a day after the start without opening the Officers page first: close the Records on the War "
                "Diary tab on day 1 (they reopen on the page they were closed on), run one day, open them, then select Poznan on the map: the "
                "officers' faces in the diary and on Poznan's state card are the game's (decided by is_unit_leader, not by the day last seen)",
                "E7: the faces scale as before (34x46 in the rows) and stay on their rows while the list scrolls; error.log: no line naming "
                "'portrait', mod1440_of_c_ul or is_unit_leader"],
        },
        "government": {
            "phase": "E3", "file": "mod1440_records.gui", "screenshot": shot,
            "windows": [dict(place, name="mod1440_records_gv", rows=dict({"gv_fac_grid": 1, "gv_sub_grid": 1}, **government_face_rows()),
                             listRows=dict({"gv_fac_grid": "mod1440_records_fac_row", "gv_sub_grid": "mod1440_records_sub_row"},
                                           **dict((grid, "mod1440_records_gv_gface_row") for grid in government_face_rows())),
                             hide=government_scene_hide(),
                             _note="The sample state of E3 check 1: Todt and Neurath hired, Fritsch chief of the army, Rundstedt in the high command, Denmark a subject; script hides the empty seats, the twins of the dates and the other ideologies.")]
                       + [{"name": "mod1440_records_%s_row" % n, "skip": True} for n in ("fac", "sub", "gv_gface")],
            "setup": tab(2),
            "teardown": [{"clickWidget": "mod1440_records_gv/gv_tab_0", "wait": 0.8}] + back,
            "expect": ["mod1440_records_gv/gv_close"],
            "crop": crop,
            "manual": ["Operatives; an election; a new head of government (a row of the heads card with from and to)"],
            "checklist": [
                "The flag, the portrait at full size and the ideology icon of the head of government",
                "Parties: the ruling party's row is lit; the bars are as long as the shares",
                "Laws: each kind shows the law's own picture and name",
                "Hire an advisor (console: effect mod1440_chk_hire, tools/check_effects.py): the next day the Cabinet shows his own small portrait, his role and the date",
                "High command: Fritsch as chief of the army with his portrait and \"Oberkommando des Heeres\"; the vacant offices with the unknown portrait",
                "Faction members and subjects as flag tiles, four to a row (puppet Denmark: effect mod1440_chk_puppet)",
                "Heads of government: Hitler, \"before the record began - today\"",
                "error.log: no line about is_character, has_character or a sprite of an advisor",
                # --- E7 ---
                "E7 with Road to 56, after mod1440_chk_hire and one day: the chief of the army and a member of the high command who are generals "
                "(Fritsch if the DLC lets him be hired, Rundstedt) show their army portrait at 48x65 in the place of the advisor's small one, the "
                "same face as in the game's commander picker; mod1440_chk_e7_log: 'chiefs 1 ...' and 'members 1 ...'",
                "E7: a political advisor (Neurath, Todt) and a theorist keep the advisor's small portrait; the head of government and the heads "
                "of the record keep their portraits (or the flag box); no unknown man anywhere on the page"],
        },
        "wars": wars_scene(place, crop, shot, back, tab(3)),     # E4 round 2
    }


SCENES = {}


def build(managers):
    """Returns the files' pieces: (gui, scripted GUIs, scripted effects, hooks by name, further files by path)."""
    global M, B
    M, B = managers, managers.B
    portrait_script, portrait_version = portraits()
    point_script, point_version = victory_points()
    out_gui, out_script, out_effects = "", "", recording() + "\n" + kept_tokens_script(portrait_version)
    hooks = {}
    for part in (war_diary(portrait_version), officers(portrait_version), government(portrait_version), wars(portrait_version), frame(portrait_version)):
        out_gui += part[0]
        out_script += ("\n" if out_script else "") + part[1]
        out_effects += "\n" + part[2]
        if len(part) > 3:
            for name, body in part[3].items():
                hooks[name] = hooks.get(name, "") + body
    SCENES.clear()
    SCENES.update(scenes())
    return out_gui, out_script, out_effects, hooks, {
        "common/scripted_effects/mod1440_portraits.txt": portrait_script + advisor_portraits()[0],
        "common/scripted_effects/mod1440_victory_points.txt": point_script,
    }
