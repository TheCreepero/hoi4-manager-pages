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

# E2 round 2 (2026-10-30; scratch/phases/E2/layout.json, design.json; the user took every recommendation): the page in
# the steel look. The left column is a card of filters (seven: Order of battle is number 6, and the Army names switch
# apart behind a rule) and the list's card (rows of 48, 20 in sight, the column heads in its head band); the right
# column is the chosen officer's file in five steel cards: who he is (his army as its second subject, Reports to,
# Stands in), Command (a general's or an admiral's) or the Chain of command (a field marshal leading an army group),
# Traits (each trait with a tooltip of its effects, tools/trait_effects_table.py), the Service record (a banded table
# over the rack of his medals) and his lines of the War Diary. The chain card is 62 taller than Command: the three
# cards under it move down by a y property on each of their widgets (a nested container takes none, SGUI-013), and the
# diary keeps 5 lines. The steel cards are bitmaps cut from the steel bar (tools/stretch_background.py, GFX_1440p_OF_*).
#
# The chain of command is worked out once a day (mod1440_of_chain): a general who leads an army with troops is
# linked to the field marshal leading an army group who has at least as many divisions in the state where most of
# the general's stand (Army Readiness's mod1440_al_loc), and at least as many divisions in all; of several, the one
# with most divisions there, marked as likely (decision 6). OF_CHAIN = False builds the page without it (no filter
# Order of battle, no Reports to, a marshal's file shows Command): the fallback if the game check finds no link.
#
# A column is (name, value of the officer, width, head text or None, head icon or None, what the tooltip says).
# An admiral has no planning and logistics: his third and fourth levels are manoeuvring and coordination, and his
# command is ships.
OF_CHAIN = True
OF_COLUMNS = [
    ("skill", "skill_level", 52, "Skill", None, "Skill level."),
    ("atk", "attack_level", 44, None, "GFX_trait_attack", "Attack."),
    ("def", "defense_level", 44, None, "GFX_trait_defense", "Defence."),
    ("c3", "planning_level", 44, None, "GFX_trait_planning", "Planning; for an admiral manoeuvring."),
    ("c4", "logistics_level", 44, None, "GFX_trait_logistics", "Logistics; for an admiral coordination."),
    ("traits", "num_traits", 168, "Traits", None, "His traits, as the game's icons: who he is first, the skills he learnt last. "
     "The pointer on one shows what it does."),
    ("cmd", "num_units", 56, "Div", None, "Divisions under his command today; for an admiral ships. A field marshal's in grey: "
     "they are counted again under his generals."),
    ("won", "mod1440_of_won", 50, "Won", None, "Battles won since the record began."),
    ("lost", "mod1440_of_lost", 50, "Lost", None, "Battles lost since the record began."),
    ("dec", "mod1440_of_dec^num", 96, "Medals", None, "Decorations you have awarded."),
]
OF_NAVY = {"c3": "maneuvering_level", "c4": "coordination_level", "cmd": "num_ships"}
OF_NAVY_ICON = {"c3": "GFX_trait_maneuvering", "c4": "GFX_trait_coordination"}
OF_NUMBERS = ("skill", "atk", "def", "c3", "c4", "cmd", "won", "lost")      # the columns that show a number
OF_FACE_W, OF_FACE = 40, 0.22               # the column of the portrait in a row, and how small it is drawn (34x46)
OF_NAME = 272                               # the name and under it the rank and his command
OF_ROW_W = OF_FACE_W + OF_NAME + sum(c[2] for c in OF_COLUMNS)     # 960
OF_ROW, OF_ROWS = 48, 20                    # rows in sight (21 before: the filters' card takes one)
OF_HIT = "GFX_1440p_SG_hit_288x48"          # the row's button: the portrait and the name, with nothing drawn; the mark after it
OF_COL_X, OF_COL_W = REC_BODY_X, 1006       # the left column: the filters' card and the list's card
OF_LIST_TOP = REC_BODY_Y + 46 + 6           # 168: the list's card, under the filters' card
OF_ROW_X, OF_ROW_Y = 22, OF_LIST_TOP + 42   # the first row
OF_HEAD_Y = OF_LIST_TOP + 8                 # the column heads in the head band
OF_FILTER_X, OF_FILTER_STEP = 22, 124
OF_INDENT = 20                              # Order of battle: a general under his field marshal
OF_MARK_X = 290                             # the green mark of a trait that can be chosen, after the name
OF_FILTERS = [
    (0, "all", "All", "Every officer serving today."),
    (1, "army", "Army", "Generals and field marshals."),
    (2, "navy", "Navy", "Admirals."),
    (3, "cmd", "With a command", "Officers who lead troops or ships today."),
    (4, "dec", "Decorated", "Officers you have decorated."),
    (5, "former", "Former", "Officers the record knows who serve no longer."),
    (6, "oob", "Order of battle", "The chain of command: each army group's field marshal with his generals under him, then the "
     "armies that answer to the High Command, then the fleets.\\nThe links, made once a day: "
     "[?mod1440_of_chain_how.GetTokenLocalizedKey]."),
]
OF_FILE_X, OF_FILE_W = 1026, 640            # the file: REC_BODY_X + 1006 + 6
OF_DY = 62                                  # how much lower Traits, Service record and the diary stand under the chain card
OF_STEEL = "GFX_1440p_OF_%s"                # the page's steel cards: (width, height, head band)
OF_CARDS = {"filters": (1006, 46, 38), "list": (1006, 1038, 38), "who": (640, 250, 0), "cmd": (640, 206, 38),
            "chain": (640, 268, 38), "traits": (640, 126, 27), "rec": (640, 240, 38), "diary": (640, 244, 27),
            "diary_m": (640, 182, 27), "award": (640, 490, 38), "award_m": (640, 428, 38)}
# the file's cards, from the top of the page's body: who 0, Command or the chain 256, then (a marshal's 62 lower)
OF_TOP = {"who": 0, "cmd": 256, "traits": 468, "rec": 600, "diary": 846}
OF_PAIR = 24                                # a row of the file's banded tables
OF_CHAIN_ROWS = 5                           # generals the chain card names; "+N more" and Order of battle for the rest
CARD_SPRITE = "GFX_1440p_SG_card_%dx%d"
TRAIT_ICONS = 6         # trait icons in a row, and traits named in a file
TRAIT_STEP = 24         # from one trait icon of a row to the next (an icon is 23x33)
TRAIT_SAMPLE = ["GFX_trait_old_guard", "GFX_trait_brilliant_strategist", "GFX_trait_trait_cautious",
                "GFX_trait_infantry_officer", "GFX_trait_war_hero", "GFX_trait_career_officer"]     # what the renderer draws
TRAIT_PAD = "token:unknown"                 # GFX_trait_unknown, the game's own picture of a trait it cannot show
TRAIT_NO_EFFECTS = "mod1440_tre_none"       # another mod's trait: its effects are in the game's own tooltip (decision 5)
ROW_MEDALS = 3          # medals at half size in a row
MEDAL_SLOTS = 12        # decorations a country can award at most (Chile has twelve medals)
RACK = 9                # medals on the rack of a file, at 0.6
RACK_TEXT = 4           # the newest medal's name and date stand after the rack while it holds this many or fewer
CARD_LINES = 8          # diary lines a file shows; under the chain card 5
CHAIN_LINES = 5
DEC_ARRAYS = ["dec", "dec_key", "dec_date", "dec_set", "dec_frame"]     # an officer's decorations, on the officer
SHIP_KINDS = [("k1", "carrier", "Carriers"), ("k2", "capital", "Capital ships"), ("k3", "screen", "Screens"),
              ("k4", "submarine", "Submarines")]
# the left half of the service record: (name, label, value, tooltip)
OF_FIGURES = [
    ("won", "Battles won", "[?mod1440_of_c_won|0]", "Counted since the record began."),
    ("lost", "Battles lost", "[?mod1440_of_c_lost|0]", "Counted since the record began."),
    ("states", "States taken", "[?mod1440_of_c_states|0]", "States you took while he had the most divisions in them."),
    ("vps", "Points taken", "[?mod1440_of_c_vps|0]", "Victory points you took from an enemy while he had the most divisions in their state."),
    ("vpl", "Points lost", "[?mod1440_of_c_vpl|0]", "Victory points an enemy took while he had the most divisions in their state."),
]
# the right half: a field marshal's rows, and a general's or an admiral's (Promoted to field marshal left out)
OF_DATES = {"since": "Commissioned", "prom": "Promoted to field marshal", "lvl": "Last skill level"}
OF_RIGHT = {"m": ["since", "prom", "lvl", "div", "dec"], "o": ["since", "lvl", "div", "dec"]}
# the status of an officer, by what the game says of him: (name, the words in a row, a trigger in his scope)
FORMER = "check_variable = { mod1440_of_seen_day < global.num_days }"
# E2b: the tooltip of the switch on both pages (tools/build_managers.py's Army Readiness reads it)
PATCH_TIP = ("Tick when your hoi4.exe carries the Modding Manager's patch (Set-HoiArmyNameProperty.ps1): it gives the names of "
             "armies and army groups here and on Army Readiness, and the exact chain of command. Every game update undoes the "
             "patch: the chain of command then falls back to its guess by itself, and the names would read Himself until you "
             "untick this.")
ARMY_NAME = "[THIS.GetHerselfHimselfCap]"
# E2b fix round 1: a free slot in the officer's trait tree, in his scope: fewer traits chosen than slots (the Traits head's pair)
FREE_SLOT = "check_variable = { num_assigned_traits < num_max_traits }"   # his army's name on the patched hoi4.exe (SCR-078), behind Army names
NAMES_ON = "check_variable = { ROOT.mod1440_ar_names = 1 }"


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


def trait_effects():
    """E2 round 2: the lines of each of the game's traits by language (tools/trait_effects_table.py, made by
    tools/make_game_tables.py); empty when the table has not been made."""
    try:
        from trait_effects_table import EFFECTS
    except ImportError:
        EFFECTS = {}
    return EFFECTS


def trait_effect_files():
    """E2 round 2: localisation/<language>/mod1440_traits_l_<language>.yml (E2 fix round 1: the game reads only a file
    whose name ends in _l_<language>.yml, LOC-001), the text keys mod1440_tre_<trait> that the
    trait cache holds beside each trait (mod1440_of_tr_e), in the game's languages: the trait's kind, its effects with
    the game's own names, its description. Another mod's trait holds mod1440_tre_none."""
    effects = trait_effects()
    leaders = leader_effects()          # E3 round 2: the country_leader traits, the game's and the playset's (decision 4)
    out = {}
    for language in M.LANGUAGES:
        table = effects.get(language) or effects.get("english") or {}
        entries = ' %s:0 "%s"\n' % (TRAIT_NO_EFFECTS, "\u00a7gAnother mod's trait: its effects are in the game's own tooltip.\u00a7!")
        entries += "".join(' mod1440_tre_%s:0 "%s"\n' % (name, "\\n".join(lines)) for name, lines in sorted(table.items()))
        plain_name = re.compile(r"^[A-Za-z0-9_]+$")
        entries += "".join(' mod1440_trl_%s:0 "%s"\n' % (name, "\\n".join(lines))
                           for name, lines in sorted((leaders.get(language) or leaders.get("english") or {}).items()) if plain_name.match(name))
        # E3 fix round 2: a role's name on one line where the game's breaks its line (mod1440_trn_<trait>)
        names = leader_names()
        entries += "".join(' mod1440_trn_%s:0 "%s"\n' % (name, words)
                           for name, words in sorted((names.get(language) or names.get("english") or {}).items()) if plain_name.match(name))
        out["localisation/%s/mod1440_traits_l_%s.yml" % (language, language)] = "\ufeffl_%s:\n" % language + entries
    return out


def trait_cache():
    """The script that keeps an officer's traits on him (mod1440_of_traits), and the version of the table.

    mod1440_of_tr     the traits the table names, as text keys: those with an icon first; padded to six
    mod1440_of_tr_e   E2 round 2: beside each, the text key of its effects (mod1440_tre_<trait>, or mod1440_tre_none)
    mod1440_of_tr_i   how many of them have an icon, mod1440_of_tr_k how many the table named
    mod1440_of_tr_n   num_traits when the array was made: the daily round makes it again when that changes
    mod1440_of_tr_plus  traits beyond the icons a row shows (more than six, no icon, or another mod's)"""
    rows = trait_table()
    described = set((trait_effects().get("english") or {}).keys())
    # E2 round 2: the effects belong to the version, so every officer's cache is made again once with mod1440_of_tr_e
    version = table_version((rows, sorted(described), "tr_e"))

    def tests(kind, with_icon):
        """The tests for one kind of officer, in groups of 16: a group runs while traits are still missing."""
        chosen = [name for name, who, sprite in rows if who in (kind, "both") and bool(sprite) == with_icon]
        out = ""
        for start in range(0, len(chosen), 16):
            body = "".join(iff("has_trait = %s" % name, "add_to_array = { mod1440_of_tr = token:%s }\n" % name
                               + "add_to_array = { mod1440_of_tr_e = token:%s }\n" % ("mod1440_tre_" + name if name in described else TRAIT_NO_EFFECTS))
                           for name in chosen[start:start + 16])
            out += iff("check_variable = { mod1440_of_tr^num < num_traits }", body)
        return out

    body = ("clear_array = mod1440_of_tr\nclear_array = mod1440_of_tr_e\n"
            + iff("is_navy_leader = yes", tests("navy", True)) + els(tests("army", True))
            + setv("mod1440_of_tr_i", "mod1440_of_tr^num")
            + iff("is_navy_leader = yes", tests("navy", False)) + els(tests("army", False))
            + setv("mod1440_of_tr_k", "mod1440_of_tr^num") + setv("mod1440_of_tr_n", "num_traits") + stamped("mod1440_of_tr_v", version)
            # the row shows six icons at most, and +N for every other trait
            + tmp("tr_shown", "mod1440_of_tr_i") + "clamp_temp_variable = { var = tr_shown max = %d }\n" % TRAIT_ICONS
            + setv("mod1440_of_tr_plus", "num_traits") + "subtract_from_variable = { mod1440_of_tr_plus = tr_shown }\n"
            + "clamp_variable = { var = mod1440_of_tr_plus min = 0 }\n"
            + pad([("mod1440_of_tr", TRAIT_PAD), ("mod1440_of_tr_e", "token:" + TRAIT_NO_EFFECTS)], TRAIT_ICONS))
    army = sum(1 for row in rows if row[1] in ("army", "both"))
    navy = sum(1 for row in rows if row[1] in ("navy", "both"))
    text = ("# Officers: the traits of the officer in scope, kept on him (tools/traits_table.py and traits_mods_table.py:\n"
            "# %d traits; a general is asked about %d, an admiral about %d), each with the text key of its effects\n"
            "# (tools/trait_effects_table.py, %d of them). Run when num_traits has changed.\n" % (len(rows), army, navy, len(described))
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


def officer_status():
    """The words under an officer's name in a row: (widget suffix, words, trigger in his scope, test of a sample row).
    One is true. E2 round 2: the army he commands (its name with Army names on, SCR-078), an army group's armies."""
    out = []
    serving = "NOT = { %s }" % FORMER
    free = serving + " NOT = { is_general_captured = yes }"
    group = "is_leading_army_group = yes"
    army = "NOT = { %s } check_variable = { num_units > 0 }" % group
    for rank, word, trigger in (("fm", "Field Marshal", "is_field_marshal = yes NOT = { is_navy_leader = yes }"),
                                ("gen", "General", "is_corps_commander = yes NOT = { is_field_marshal = yes } NOT = { is_navy_leader = yes }"),
                                ("adm", "Admiral", "is_navy_leader = yes")):
        lead = "\u00a7g%s  \u00b7  " % word
        if rank == "adm":
            states = [("off", lead + "\u00a7!\u00a7Rno longer serving\u00a7!", FORMER, ("off",)),
                      ("cmd", lead + "Fleet of [?num_ships|0] ships\u00a7!", "%s check_variable = { num_ships > 0 }" % serving, ("fleet",)),
                      ("idle", lead + "unassigned\u00a7!", "%s NOT = { check_variable = { num_ships > 0 } }" % serving, ("idle",))]
        else:
            states = [("off", lead + "\u00a7!\u00a7Rno longer serving\u00a7!", FORMER, ("off",)),
                      ("cap", lead + "\u00a7!\u00a7Rcaptured\u00a7!", "%s is_general_captured = yes" % serving, ("cap",)),
                      ("army", lead + "\u00a7!" + ARMY_NAME, "%s %s %s" % (free, army, NAMES_ON), ("army", True)),
                      ("armyd", lead + "army of [?num_units|0] divisions\u00a7!", "%s %s NOT = { %s }" % (free, army, NAMES_ON), ("army", False)),
                      ("idle", lead + "unassigned\u00a7!", "%s NOT = { %s } NOT = { check_variable = { num_units > 0 } }" % (free, group), ("idle",))]
            if rank == "fm":
                links = "check_variable = { mod1440_of_subs^num > 0 }"
                # E2 fix round 1: with Army names on, the army group's own name: the patched property reads the orders group a
                # marshal leads, and an army group is one (group+0x39 set, its name at +0x160 like an army's; build.json newFacts)
                states[2:2] = [("grpn", lead + "\u00a7!" + ARMY_NAME, "%s %s %s" % (free, group, NAMES_ON), ("grp", "name")),
                               ("grp", lead + "Army group of [?mod1440_of_subs^num|0] armies\u00a7!",
                                "%s %s %s NOT = { %s }" % (free, group, links, NAMES_ON), ("grp", True)),
                               ("grpd", lead + "Army group of [?num_units|0] divisions\u00a7!",
                                "%s %s NOT = { %s } NOT = { %s }" % (free, group, links, NAMES_ON), ("grp", False))]
        for state, words, condition, test in states:
            out.append(("%s_%s" % (rank, state), words, "%s %s" % (trigger, condition), (rank,) + test))
    return out


def status_shown(test, r):
    """Whether the status line <test> (officer_status()) is the one of the sample row r."""
    rank, state = test[0], test[1]
    if r["rank"] != rank or r["status"] != state:
        return False
    if state == "army":
        return test[2] == r["names"]
    if state == "grp":
        if test[2] == "name":
            return r["names"]
        return not r["names"] and test[2] == (r.get("subs", 0) > 0)
    return True


def officers(portrait_version):
    from unit_medals_table import MEDALS
    sets = sorted(set(m[1] for m in MEDALS))
    trait_script, trait_version = trait_cache()
    body, effects, properties = head("of", 1, "Every general and admiral, with what the mod has written down about him. Click one for his record.")
    triggers = ""
    row_triggers = ""
    sub_triggers = ""
    # E2 round 2: what the renderer's scene needs: each widget of the file with the test of a sample state that says
    # whether script shows it, and the same for the rows (tools/scenes/officers.json, officer_scene())
    shows, row_shows, sub_shows = {}, {}, {}

    def show(name, trigger, test):
        """A widget of the file shown when <trigger> holds; <test>(st) says it of a sample state."""
        nonlocal triggers
        triggers += block(name + "_visible", trigger if trigger.endswith("\n") else trigger + "\n")
        shows[name] = test

    def row_show(name, trigger, test):
        nonlocal row_triggers
        row_triggers += block(name + "_visible", trigger if trigger.endswith("\n") else trigger + "\n")
        row_shows[name] = test

    filters = [f for f in OF_FILTERS if OF_CHAIN or f[0] != 6]
    names_on = is_one("mod1440_ar_names")

    # ---- the filters: a steel card that is all head band; the chosen one shows the button's second frame
    body += M.icon("of_f_filters_bg", OF_COL_X, REC_BODY_Y, OF_STEEL % "filters")
    for n, (value, name, label, tip) in enumerate(filters):
        body += M.button("of_show_%s" % name, OF_FILTER_X + n * OF_FILTER_STEP, REC_BODY_Y + 5, "GFX_sort_button_120x29",
                         B.key("of_show_%s" % name, label), tooltip=B.key("of_show_%s_tt" % name, tip))
        effects += block("of_show_%s_click" % name, setv("mod1440_of_show", value) + "mod1440_of_list = yes\n")
        properties += block("of_show_%s" % name, "frame = mod1440_of_frame_%d\n" % value)
    # the Army names switch (decision 2): Army Readiness's own switch, a setting and not a filter (gate A round 1):
    # behind a rule, the pages' gold checkbox and its words; either page turns it
    # E2b (2026-10-30): the switch says what it stands for, a patched game (scratch/phases/E2b/design.json); the same variable
    names_tip = B.key("of_names_tt", PATCH_TIP)
    # E2b: rule, box and words 4 px further left than E2 drew them: "Patched game" is 83 px in hoi_16mbs and the box ends at the card's inner edge (1012)
    body += M.icon("of_names_rule", 891, REC_BODY_Y + 7, "GFX_1440p_SG_rule_2x30")
    body += checkbox("of_names", 900, REC_BODY_Y + 11, 1, names_tip)
    properties += block("of_names", "frame = mod1440_ar_names_fr\n")
    body += M.button("of_names_hit", 924, REC_BODY_Y + 8, "GFX_1440p_SG_hit_84x28", tooltip=names_tip)
    body += plain("of_names_l", 927, REC_BODY_Y + 12, OF_COL_X + OF_COL_W - 8 - 927, B.key("of_names_l", "Patched game"), M.FONT_SMALL, height=20)
    toggle = (iff(names_on, setv("mod1440_ar_names", 0) + setv("mod1440_ar_names_fr", 1))
              + els(setv("mod1440_ar_names", 1) + setv("mod1440_ar_names_fr", 2)) + "mod1440_of_how = yes\n"
              + "add_to_variable = { mod1440_rec_dirty = 1 }\n")
    effects += block("of_names_click", toggle) + block("of_names_hit_click", toggle)

    # ---- the list: a steel card whose head band holds the column heads. A click sorts, a second click turns the order.
    body += M.icon("of_f_list_bg", OF_COL_X, OF_LIST_TOP, OF_STEEL % "list")
    body += M.button("of_sort_name", OF_ROW_X + OF_FACE_W, OF_LIST_TOP + 4, "GFX_1440p_SG_hit_160x30",
                     tooltip=B.key("of_sort_name_tt", "Back to the order of the game."))
    body += plain("of_sort_name_l", OF_ROW_X + 46, OF_HEAD_Y, 150, B.key("of_sort_name", "Officer"))
    effects += block("of_sort_name_click", setv("mod1440_of_sort_by", 0) + "mod1440_of_list = yes\n")
    body += M.text("of_count", OF_ROW_X + 200, OF_HEAD_Y + 2, 104, B.key("of_count", "\u00a7g[?mod1440_of_rows^num|0] listed\u00a7!"), M.FONT_SMALL, "right", 20)
    x = OF_ROW_X + OF_FACE_W + OF_NAME
    rx = OF_FACE_W + OF_NAME
    middle = 12                             # the line of a number in a row
    entry = M.icon("of_row_stripe", 0, 0, STRIPE % (OF_ROW_W, OF_ROW))
    entry += M.icon("of_row_pick", 0, 0, PICK % (OF_ROW_W, OF_ROW))
    row_show("of_row_stripe", is_one("mod1440_of_odd") + " NOT = { %s }" % is_one("mod1440_of_picked"), lambda r: r["odd"] and not r["picked"])
    row_show("of_row_pick", is_one("mod1440_of_picked"), lambda r: r["picked"])
    # E7: the row's scope is the officer: while he is a unit leader (mod1440_of_ul, UL_MARK) the game draws his face; one
    # who has left the service shows the table's portrait. E2 round 2: under Order of battle a general under his field
    # marshal stands 20 further right (mod1440_of_ind, set where the list is made), on twins of the face and the lines.
    indent = is_one("mod1440_of_ind")
    for suffix, dx, cond, test in (("", 0, "NOT = { %s }" % indent, lambda r: not r["ind"]), ("_in", OF_INDENT, indent, lambda r: r["ind"])):
        entry += portrait("of_row_face" + suffix, 3 + dx, 1, OF_FACE)
        properties += block("of_row_face" + suffix, GAME_FACE)
        row_show("of_row_face" + suffix, SERVES + " " + cond, lambda r, t=test: r["serves"] and t(r))
    entry += portrait("of_row_face_table", 3, 1, OF_FACE)
    properties += shown("of_row_face_table", "mod1440_p")
    row_show("of_row_face_table", "NOT = { %s }" % SERVES, lambda r: not r["serves"])
    # the whole of the portrait and the name is the button, and nothing of it is drawn
    entry += M.button("of_row", 0, 0, OF_HIT, tooltip=B.key("of_row_tt", "Show this officer's record"))
    for suffix, dx, cond, test in (("", 0, "NOT = { %s }" % indent, lambda r: not r["ind"]), ("_in", OF_INDENT, indent, lambda r: r["ind"])):
        entry += fixed(plain("of_row_name" + suffix, OF_FACE_W + 6 + dx, 3, 236 - dx, B.key("of_row_name", "[THIS.GetName]"), height=22))
        entry += fixed(plain("of_row_name_sel" + suffix, OF_FACE_W + 6 + dx, 3, 236 - dx, B.key("of_row_name_sel", "\u00a7Y[THIS.GetName]\u00a7!"), height=22))
        row_show("of_row_name" + suffix, "NOT = { %s } %s" % (is_one("mod1440_of_picked"), cond), lambda r, t=test: not r["picked"] and t(r))
        row_show("of_row_name_sel" + suffix, "%s %s" % (is_one("mod1440_of_picked"), cond), lambda r, t=test: r["picked"] and t(r))
    for suffix, words, condition, test in officer_status():
        widget = "of_row_st_" + suffix
        entry += fixed(plain(widget, OF_FACE_W + 6, 26, 262, B.key(widget, words), M.FONT_SMALL, height=20))
        if test[1] == "army":
            # a general (or a field marshal) whose army serves in an army group: indented under Order of battle
            entry += fixed(plain(widget + "_in", OF_FACE_W + 6 + OF_INDENT, 26, 262 - OF_INDENT, B.key(widget, words), M.FONT_SMALL, height=20))
            row_show(widget, condition + " NOT = { %s }" % indent, lambda r, t=test: status_shown(t, r) and not r["ind"])
            row_show(widget + "_in", condition + " " + indent, lambda r, t=test: status_shown(t, r) and r["ind"])
        else:
            row_show(widget, condition, lambda r, t=test: status_shown(t, r))
    # the green mark after the name: a free slot in his trait tree (E2b fix round 1: can_select_trait takes a trait, not yes,
    # and tested nothing; the pair of the Traits head's "N of M chosen" does, and is no loop)
    entry += M.icon("of_row_mark", OF_MARK_X, 8, "GFX_army_experience")
    entry = entry[:-3] + ' pdx_tooltip = "%s" }\n' % B.key("of_row_mark_tt", "A free slot in his trait tree: a trait can be chosen there.")
    row_show("of_row_mark", "NOT = { %s } %s" % (FORMER, FREE_SLOT), lambda r: r.get("can", False))
    keys = ""
    head_hits = ""
    for number, (name, value, width, label, picture, tip) in enumerate(OF_COLUMNS, start=1):
        tooltip = B.key("of_sort_%s_tt" % name, tip + "\\nClick to sort, click again to turn the order.")
        head_hits += M.button("of_sort_%s" % name, x, OF_LIST_TOP + 4, "GFX_1440p_SG_hit_%dx30" % width, tooltip=tooltip)
        if label:
            body += plain("of_sort_%s_l" % name, x, OF_HEAD_Y, width, B.key("of_sort_%s" % name, label), M.FONT_LABEL, "centre", 22)
        else:
            body += through("of_sort_%s_icon" % name, x + (width - 27) // 2, OF_LIST_TOP + 6, picture)
        effects += block("of_sort_%s_click" % name, (
            iff("check_variable = { mod1440_of_sort_by = %d }" % number, flip("mod1440_of_up"))
            + els(setv("mod1440_of_sort_by", number) + setv("mod1440_of_up", 0))
            + setv("mod1440_of_arrow_x", x + width - M.ARROW_DX) + "mod1440_of_list = yes\n"))
        key = tmp("of_key", value)
        if name in OF_NAVY:
            key += iff("is_navy_leader = yes", tmp("of_key", OF_NAVY[name]))
        keys += iff("check_variable = { ROOT.mod1440_of_sort_by = %d }" % number, key, "if" if number == 1 else "else_if")
        if name in OF_NUMBERS:
            cell = "[?%s|0]" % value
            entry += M.text("of_cell_%s" % name, rx + 2, middle, width - 4, B.key("of_cell_%s" % name, cell), M.FONT_VALUE, "centre", 24)
            if name == "cmd":
                # divisions; a field marshal's of his army group in grey (counted again under his generals); ships
                entry += M.text("of_cell_cmd_group", rx + 2, middle, width - 4, B.key("of_cell_cmd_group", "\u00a7g[?num_units|0]\u00a7!"),
                                M.FONT_VALUE, "centre", 24)
                entry += M.text("of_cell_cmd_navy", rx + 2, middle, width - 4, B.key("of_cell_cmd_navy", "[?num_ships|0]"), M.FONT_VALUE, "centre", 24)
                row_show("of_cell_cmd", "NOT = { is_navy_leader = yes } NOT = { is_leading_army_group = yes } check_variable = { num_units > 0 }",
                         lambda r: r["rank"] != "adm" and r["status"] == "army")
                row_show("of_cell_cmd_group", "NOT = { is_navy_leader = yes } is_leading_army_group = yes", lambda r: r["status"] == "grp")
                row_show("of_cell_cmd_navy", "is_navy_leader = yes check_variable = { num_ships > 0 }", lambda r: r["status"] == "fleet")
            elif name in OF_NAVY:
                entry += M.text("of_cell_%s_navy" % name, rx + 2, middle, width - 4, B.key("of_cell_%s_navy" % name, "[?%s|0]" % OF_NAVY[name]),
                                M.FONT_VALUE, "centre", 24)
                row_show("of_cell_%s" % name, "NOT = { is_navy_leader = yes }", lambda r: r["rank"] != "adm")
                row_show("of_cell_%s_navy" % name, "is_navy_leader = yes", lambda r: r["rank"] == "adm")
            elif name in ("won", "lost"):
                row_show("of_cell_%s" % name, M.more_than_zero(value), lambda r, n=name: r.get(n, 0) > 0)
        elif name == "traits":
            # his traits as the game's icons, from the array kept on him; each with the tooltip of its effects (E2
            # round 2); +N for those no icon stands for
            for t in range(TRAIT_ICONS):
                widget = "of_row_tr_%d" % t
                tip_key = B.key(widget + "_tt", "\u00a7Y[?mod1440_of_tr^%d.GetTokenLocalizedKey]\u00a7!\\n[?mod1440_of_tr_e^%d.GetTokenLocalizedKey]" % (t, t))
                entry += M.icon(widget, rx + 4 + t * TRAIT_STEP, 7, TRAIT_SAMPLE[t])[:-3] + ' pdx_tooltip = "%s" }\n' % tip_key
                properties += block(widget, 'image = "GFX_trait_[?mod1440_of_tr^%d.GetTokenKey]"\n' % t)
                row_show(widget, "check_variable = { mod1440_of_tr_i > %d }" % t, lambda r, t=t: r["tr"] > t)
            entry += M.text("of_row_tr_more", rx + 4 + TRAIT_ICONS * TRAIT_STEP, 14, width - 8 - TRAIT_ICONS * TRAIT_STEP,
                            B.key("of_row_tr_more", "+[?mod1440_of_tr_plus|0]"), M.FONT_SMALL, height=20)
            row_show("of_row_tr_more", M.more_than_zero("mod1440_of_tr_plus"), lambda r: r.get("plus", 0) > 0)
        elif name == "dec":
            # up to three of his medals at half size: the strip of its set and its frame, kept for the row
            for k in range(ROW_MEDALS):
                widget = "of_row_md_%d" % k
                entry += scaled(widget, rx + 4 + k * 28, 3, MEDAL_STRIP % "ger", 0.5)
                properties += block(widget, 'image = "[?mod1440_of_rm^%d.GetTokenKey]"\nframe = mod1440_of_rf^%d\n' % (k, k))
                row_show(widget, "check_variable = { mod1440_of_dec^num > %d }" % k, lambda r, k=k: r.get("dec", 0) > k)
        x += width
        rx += width
    body += head_hits
    first = OF_ROW_X + OF_FACE_W + OF_NAME + OF_COLUMNS[0][2] - M.ARROW_DX
    body += scaled("of_arrow_down", first, OF_LIST_TOP + 2, "GFX_arrow_down_small", M.ARROW)
    body += scaled("of_arrow_up", first, OF_LIST_TOP + 2, "GFX_arrow_up_small", M.ARROW)
    properties += block("of_arrow_down", "x = mod1440_of_arrow_x\n") + block("of_arrow_up", "x = mod1440_of_arrow_x\n")
    show("of_arrow_down", M.more_than_zero("mod1440_of_sort_by") + "NOT = { %s }\n" % is_one("mod1440_of_up"), lambda st: False)
    show("of_arrow_up", M.more_than_zero("mod1440_of_sort_by") + is_one("mod1440_of_up") + "\n", lambda st: False)
    body += war_listing("of_list", "of_grid", OF_ROW_X, OF_ROW_Y, OF_ROWS * OF_ROW, width=OF_ROW_W, outer=OF_ROW_W + 30, step=OF_ROW)
    # the row's scope is the officer: the mark of the one chosen before is taken off, his put on; Award ends
    effects += block("of_row_click", (
        "mod1440_of_me = yes\n"
        + block("ROOT", iff(is_one("mod1440_of_has_sel"), block("var:mod1440_of_sel", setv("mod1440_of_picked", 0)))
                + setv("mod1440_of_sel", "of_me") + setv("mod1440_of_has_sel", 1) + setv("mod1440_of_awarding", 0))
        + setv("mod1440_of_picked", 1) + block("ROOT", "mod1440_of_card = yes\n")))

    # ---- the file of the chosen officer, in a box at OF_FILE_X; positions are the box's
    has = is_one("mod1440_of_has_sel") + "\n"
    award = is_one("mod1440_of_awarding")
    filing = has + "NOT = { %s }\n" % award           # his file, not the Award mode
    awarding = has + award + "\n"
    chain = is_one("mod1440_of_c_chain")
    not_chain = "NOT = { %s }\n" % chain
    W = OF_FILE_W
    rank = lambda n: "check_variable = { mod1440_of_c_rank = %d }\n" % n
    mode = lambda n: "check_variable = { mod1440_of_c_mode = %d }\n" % n
    navy = rank(3)
    army = "NOT = { %s }\n" % navy.strip()
    serving = "check_variable = { mod1440_of_c_status < 3 }\n"
    inner = ""
    lower = ""                  # the widgets of Traits, Service record and the diary: a y property each (OF_DY)
    lprops = {}                 # their properties

    def lprop(name, line):
        lprops[name] = lprops.get(name, "") + line

    # who he is: the portrait, name, rank and status; his army as the card's second subject; his levels; Reports to; Stands in
    inner += M.icon("of_f_who_bg", 0, OF_TOP["who"], OF_STEEL % "who")
    # E7: a unit leader's face is a list of one row (mod1440_of_c_ul, filled by mod1440_of_card); the table's portrait
    # shows for one who is no unit leader any more
    inner += portrait("of_c_face", 8, 8)
    properties += shown("of_c_face", "mod1440_of_c_p")
    inner += face_grid("of_c_gface_grid", 8, 8, 1.0)
    properties += block("of_c_gface", GAME_FACE)
    show("of_c_face", has + "check_variable = { mod1440_of_c_ul^num < 1 }\n", lambda st: st["has"] and not st["ul"])
    inner += M.text("of_c_name", 172, 10, 460, B.key("of_c_name", "[?mod1440_of_sel.GetName]"), M.FONT_CARD, height=30, fixed=True)
    inner += M.text("of_c_none", 16, 18, W - 32, B.key("of_c_none", "Click an officer in the table to open his file."), M.FONT_LABEL)
    show("of_c_name", has, lambda st: st["has"])
    show("of_c_none", "NOT = { %s }\n" % has.strip(), lambda st: not st["has"])
    for r, word in ((1, "Field Marshal"), (2, "General"), (3, "Admiral")):
        for s, words, cond in (("on", "serving", "check_variable = { mod1440_of_c_status < 3 }\n"),
                               ("cap", "\u00a7Rcaptured\u00a7!", "check_variable = { mod1440_of_c_status = 3 }\n"),
                               ("off", "\u00a7Rno longer serving\u00a7!", "check_variable = { mod1440_of_c_status = 4 }\n")):
            widget = "of_c_rs_%d_%s" % (r, s)
            inner += M.text(widget, 172, 44, 460, B.key(widget, "\u00a7Y%s\u00a7!   \u00a7g\u00b7  \u00a7!%s" % (word, words)), M.FONT_LABEL, height=22)
            show(widget, has + rank(r) + cond,
                 lambda st, r=r, s=s: st["has"] and st["rank"] == r and {"on": st["status"] < 3, "cap": st["status"] == 3, "off": st["status"] == 4}[s])
    # the army: the lighter plate of a chosen row as a rim round a near-black field; its name in the name font in white
    # (gate A round 1). Names on: a list of one row whose scope is the officer reads the army's name [SCR-078].
    army_tip = B.key("of_f_army_tt", "His command. With Army names on, the army's name as the game shows it (it needs the local "
                     "patch of hoi4.exe; without it the name would read Himself).")
    inner += M.icon("of_f_army_rim", 172, 70, PICK % (460, 62))
    inner += M.icon("of_f_army_field", 176, 74, INSET % (452, 54))[:-3] + ' pdx_tooltip = "%s" }\n' % army_tip
    show("of_f_army_rim", has, lambda st: st["has"])
    show("of_f_army_field", has, lambda st: st["has"])
    inner += ('gridboxtype = {\n\tname = "of_c_army_grid"\n\tposition = { x = 188 y = 88 }\n\tsize = { width = 290 height = 30 }\n'
              '\tslotsize = { width = 1 height = 1 }\n\tadd_horizontal = no\n\tformat = "UPPER_LEFT"\n}\n')
    army_entry = M.text("of_c_army_name", 0, 0, 290, B.key("of_c_army_name", ARMY_NAME), M.FONT_CARD, height=30, fixed=True)
    # E2 fix round 1: also a field marshal's army group (its name through the same patched property); one who leads neither
    # would read the pronoun
    army_row_trigger = block("of_c_army_name_visible", "%s\nOR = { is_leading_army = yes is_leading_army_group = yes }\n" % NAMES_ON)
    for widget, words, cond, test in (
            ("of_c_army_n", "Army of [?mod1440_of_c_cmd|0] divisions", mode(1) + "NOT = { %s }\n" % names_on, lambda st: st["mode"] == 1 and not st["names"]),
            ("of_c_army_grp", "Army group of [?mod1440_of_c_subs_n|0] armies", mode(2) + M.more_than_zero("mod1440_of_c_subs_n")
             + "NOT = { %s }\n" % names_on, lambda st: st["mode"] == 2 and st["subs"] > 0 and not st["names"]),
            ("of_c_army_grpd", "Army group", mode(2) + "NOT = { %s }\n" % M.more_than_zero("mod1440_of_c_subs_n").strip()
             + "NOT = { %s }\n" % names_on, lambda st: st["mode"] == 2 and not st["subs"] and not st["names"]),
            ("of_c_army_fleet", "Fleet", mode(3), lambda st: st["mode"] == 3),
            ("of_c_army_none", "\u00a7gNo command\u00a7!", mode(0), lambda st: st["mode"] == 0)):
        inner += M.text(widget, 188, 88, 290, B.key(widget, words), M.FONT_CARD, height=30, fixed=True)
        show(widget, has + cond, lambda st, t=test: st["has"] and t(st))
    inner += M.text("of_c_army_div", 486, 80, 138, B.key("of_c_army_div", "[?mod1440_of_c_cmd|0] divisions"), M.FONT_VALUE, "right", 24)
    inner += M.text("of_c_army_bat", 486, 108, 138, B.key("of_c_army_bat", "[?mod1440_of_c_bat|0] battalions"), M.FONT_LABEL, "right", 22)
    inner += M.text("of_c_army_ships", 486, 80, 138, B.key("of_c_army_ships", "[?mod1440_of_c_cmd|0] ships"), M.FONT_VALUE, "right", 24)
    show("of_c_army_div", has + "OR = { %s %s }\n" % (mode(1).strip(), mode(2).strip()), lambda st: st["has"] and st["mode"] in (1, 2))
    show("of_c_army_bat", has + "OR = { %s %s }\n" % (mode(1).strip(), mode(2).strip()), lambda st: st["has"] and st["mode"] in (1, 2))
    show("of_c_army_ships", has + mode(3), lambda st: st["has"] and st["mode"] == 3)
    # the levels: one banded row of 32, Skill and the four levels with the game's icons
    inner += M.icon("of_f_levels", 172, 140, STRIPE % (460, 32))
    show("of_f_levels", has, lambda st: st["has"])
    cell = 460 // 5
    inner += M.text("of_c_skill_l", 180, 144, 60, B.key("of_c_skill_l", "Skill"), M.FONT_LABEL, height=22)
    inner += M.text("of_c_skill", 172, 143, cell - 8, B.key("of_c_skill", "[?mod1440_of_c_skill|0]"), M.FONT_VALUE, "right", 24)
    show("of_c_skill_l", has, lambda st: st["has"])
    show("of_c_skill", has, lambda st: st["has"])
    for n, column in enumerate(("atk", "def", "c3", "c4"), start=1):
        cx = 172 + n * cell
        sprite = [c[4] for c in OF_COLUMNS if c[0] == column][0]
        tip = [c[5] for c in OF_COLUMNS if c[0] == column][0]
        icons = [(sprite, army, lambda st: st["rank"] != 3), (OF_NAVY_ICON[column], navy, lambda st: st["rank"] == 3)] \
            if column in OF_NAVY_ICON else [(sprite, "", lambda st: True)]
        for i, (picture, condition, test) in enumerate(icons):
            inner += M.icon("of_c_%s_i%d" % (column, i), cx + 8, 142, picture)
            show("of_c_%s_i%d" % (column, i), has + condition, lambda st, t=test: st["has"] and t(st))
        inner += M.text("of_c_%s" % column, cx, 143, cell - 8, B.key("of_c_%s" % column, "[?mod1440_of_c_%s|0]" % column), M.FONT_VALUE, "right", 24,
                        tooltip=B.key("of_c_%s_tt" % column, tip))
        show("of_c_%s" % column, has, lambda st: st["has"])
    # Reports to: the field marshal whose army group his army serves in (a click opens his file), or the High Command
    commanding = has + serving + "OR = { %s %s }\n" % (mode(1).strip(), mode(2).strip())
    if OF_CHAIN:
        linked = M.more_than_zero("mod1440_of_c_fm_n")
        inner += M.text("of_c_rep_l", 172, 180, 92, B.key("of_c_rep_l", "Reports to"), M.FONT_SMALL, height=20)
        inner += M.text("of_c_rep", 268, 178, 364, B.key("of_c_rep", "\u00a7Y[?mod1440_of_c_fm.GetName]\u00a7!  \u00a7g\u00b7  army group of "
                                                         "[?mod1440_of_c_fm_k|0] armies\u00a7!"), M.FONT_LABEL, height=22, fixed=True)
        # E2 fix round 1: with Army names on, the army group's name after the marshal's (the patched property of the character
        # the variable holds, as GetName is); the count of its armies moves into the tooltip (a long marshal's and group's
        # name fill the line); a marshal's own line keeps the count of his armies the name field no longer says
        inner += M.text("of_c_rep_n", 268, 178, 364, B.key("of_c_rep_n", "\u00a7Y[?mod1440_of_c_fm.GetName]\u00a7!  \u00a7g\u00b7  \u00a7!"
                                                             "[?mod1440_of_c_fm.GetHerselfHimselfCap]"),
                        M.FONT_LABEL, height=22, fixed=True)
        inner += M.text("of_c_rep_hc", 268, 178, 364, B.key("of_c_rep_hc", "\u00a7gHigh Command\u00a7!"), M.FONT_LABEL, height=22)
        inner += M.text("of_c_rep_hc_grp", 268, 178, 364, B.key("of_c_rep_hc_grp", "\u00a7gHigh Command  \u00b7  his army group of "
                                                                   "[?mod1440_of_c_subs_n|0] armies\u00a7!"), M.FONT_LABEL, height=22)
        inner += M.button("of_c_rep_go", 268, 177, "GFX_1440p_SG_hit_364x24", tooltip=B.key(
            "of_c_rep_go_tt", "His field marshal, [?mod1440_of_chain_how.GetTokenLocalizedKey]. His army group has "
            "[?mod1440_of_c_fm_k|0] armies. Click for the marshal's file."))
        inner += M.button("of_c_rep_likely", 268, 177, "GFX_1440p_SG_hit_364x24", tooltip=B.key(
            "of_c_rep_likely_tt", "Likely his field marshal, [?mod1440_of_chain_how.GetTokenLocalizedKey]: more than one army group "
            "has divisions in the state where most of his stand, and this one has the most there; it has [?mod1440_of_c_fm_k|0] armies. "
            "Click for the marshal's file."))
        show("of_c_rep_l", commanding, lambda st: st["has"] and st["status"] < 3 and st["mode"] in (1, 2))
        show("of_c_rep", commanding + linked + "NOT = { %s }\n" % names_on,
             lambda st: st["has"] and st["status"] < 3 and st["mode"] in (1, 2) and st["fm"] > 0 and not st["names"])
        show("of_c_rep_n", commanding + linked + names_on + "\n",
             lambda st: st["has"] and st["status"] < 3 and st["mode"] in (1, 2) and st["fm"] > 0 and st["names"])
        show("of_c_rep_go", commanding + "check_variable = { mod1440_of_c_fm_n = 1 }\n", lambda st: False)
        show("of_c_rep_likely", commanding + "check_variable = { mod1440_of_c_fm_n > 1 }\n", lambda st: False)
        named_group = mode(2).strip() + " " + M.more_than_zero("mod1440_of_c_subs_n").strip() + " " + names_on
        show("of_c_rep_hc", commanding + "NOT = { %s }\nNOT = { %s }\n" % (linked.strip(), named_group),
             lambda st: st["has"] and st["status"] < 3 and st["mode"] in (1, 2) and not st["fm"] and not (st["mode"] == 2 and st["subs"] and st["names"]))
        show("of_c_rep_hc_grp", commanding + "NOT = { %s }\n%s\n" % (linked.strip(), named_group),
             lambda st: st["has"] and st["status"] < 3 and st["mode"] == 2 and not st["fm"] and st["subs"] and st["names"])
        effects += block("of_c_rep_go_click", open_file("mod1440_of_c_fm")) + block("of_c_rep_likely_click", open_file("mod1440_of_c_fm"))
    # Stands in: the state where most of his divisions stand (Army Readiness's count), and his HQ; the go-to button
    located = M.more_than_zero("mod1440_of_c_lcnt")
    hq = is_one("mod1440_of_c_has_hq")
    inner += M.text("of_c_loc_l", 172, 206, 92, B.key("of_c_loc_l", "Stands in"), M.FONT_SMALL, height=20)
    inner += M.text("of_c_loc", 268, 204, 324, B.key("of_c_loc", "\u00a7Y[?mod1440_of_c_loc.GetName]\u00a7!  \u00a7g\u00b7  HQ in [?mod1440_of_c_hq.GetName]\u00a7!"),
                    M.FONT_LABEL, height=22, fixed=True)
    inner += M.text("of_c_loc_nohq", 268, 204, 324, B.key("of_c_loc_nohq", "\u00a7Y[?mod1440_of_c_loc.GetName]\u00a7!  \u00a7g\u00b7  HQ not deployed\u00a7!"),
                    M.FONT_LABEL, height=22, fixed=True)
    inner += M.text("of_c_loc_sea", 268, 204, 324, B.key("of_c_loc_sea", "\u00a7gat sea, or not counted yet\u00a7!"), M.FONT_LABEL, height=22)
    inner += M.button("of_c_go", W - 40, 200, "GFX_countryaction_gotolocation_big", tooltip=B.key("of_c_go_tt", "Show where most of his divisions stand"))
    show("of_c_loc_l", commanding, lambda st: st["has"] and st["status"] < 3 and st["mode"] in (1, 2))
    show("of_c_loc", commanding + located + hq + "\n", lambda st: st["has"] and st["status"] < 3 and st["mode"] in (1, 2) and st["loc"] and st["hq"])
    show("of_c_loc_nohq", commanding + located + "NOT = { %s }\n" % hq, lambda st: st["has"] and st["status"] < 3 and st["mode"] in (1, 2) and st["loc"] and not st["hq"])
    show("of_c_loc_sea", commanding + "NOT = { %s }\n" % located.strip(), lambda st: st["has"] and st["status"] < 3 and st["mode"] in (1, 2) and not st["loc"])
    show("of_c_go", commanding + located, lambda st: st["has"] and st["status"] < 3 and st["mode"] in (1, 2) and st["loc"])
    go = tmp("of_go", "mod1440_of_c_loc") + block("var:of_go", block("ROOT", "goto_state = PREV\n"))
    effects += block("of_c_go_click", go)

    # Command: a general's or an admiral's (and a marshal's while the chain is not built); Show on map and Equipment in the head
    top = OF_TOP["cmd"]
    commands = has + not_chain
    inner += M.icon("of_f_cmd_bg", 0, top, OF_STEEL % "cmd")
    inner += M.text("of_f_cmd_title", 12, top + 7, 300, B.key("of_f_cmd_title", "Command"), M.FONT_LABEL, height=22)
    show("of_f_cmd_bg", commands, lambda st: st["has"] and not st["chain"])
    show("of_f_cmd_title", commands, lambda st: st["has"] and not st["chain"])
    inner += M.button("of_c_map", W - 8 - 120 - 6 - 120, top + 5, "GFX_sort_button_120x29", B.key("of_c_map", "Show on map"),
                      tooltip=B.key("of_c_map_tt", "The camera to the state where most of his divisions stand."))
    inner += M.button("of_c_eq", W - 8 - 120, top + 5, "GFX_sort_button_120x29", B.key("of_c_eq", "Equipment"),
                      tooltip=B.key("of_c_eq_tt", "Closes the Records and opens Army Readiness with his army chosen: what its divisions hold and need."))
    show("of_c_map", commands + serving + located, lambda st: st["has"] and not st["chain"] and st["status"] < 3 and st["loc"] and st["mode"] in (1, 2))
    show("of_c_eq", commands + serving + "OR = { %s %s }\n" % (mode(1).strip(), mode(2).strip()),
         lambda st: st["has"] and not st["chain"] and st["status"] < 3 and st["mode"] in (1, 2))
    effects += block("of_c_map_click", go)
    # Equipment (decision 3): Army Readiness's chosen army is written (a named deviation of the contracts), the Records close
    effects += block("of_c_eq_click", iff(is_one("mod1440_of_has_sel"), (
        setv("mod1440_ar_sel", "mod1440_of_sel") + setv("mod1440_ar_has_sel", 1) + "mod1440_rec_close = yes\n"
        + setv("mod1440_ar_open", 1) + setv("mod1440_ar_small", 0) + setv("mod1440_nf_shown", 0) + "mod1440_ar_count = yes\n")))
    for n in (1, 3, 5):
        inner += M.icon("of_f_cmd_band_%d" % n, 8, top + 42 + n * OF_PAIR, STRIPE % (624, OF_PAIR))
        show("of_f_cmd_band_%d" % n, commands, lambda st: st["has"] and not st["chain"])
    plan_none = "check_variable = { mod1440_of_c_bp < 1 }"
    land = [
        ("div", "Divisions", "[?mod1440_of_c_cmd|0]", None, "inf", "Infantry", "[?mod1440_of_c_inf|0]", None),
        ("bat", "Battalions", "[?mod1440_of_c_bat|0]", None, "arm", "Armoured", "[?mod1440_of_c_arm|0]", "Divisions whose main kind is armour."),
        ("fight", "In battle", "[?mod1440_of_c_fight|0]", "[?mod1440_of_c_att|0] attacking, [?mod1440_of_c_dfd|0] defending.",
         "mot", "Motorised", "[?mod1440_of_c_mot|0]", None),
        ("plan", "Planning", "[?mod1440_of_c_plan|%0]", "What his divisions have planned, on average. It builds only while a battle plan is drawn.",
         "mech", "Mechanised", "[?mod1440_of_c_mech|0]", None),
        ("ent", "Entrenchment", "[?mod1440_of_c_ent|%0]", "How dug in his divisions are, on average.",
         "oth", "Other kinds", "[?mod1440_of_c_oth|0]", "Cavalry, artillery, rocket and special divisions."),
        ("bp", "Battle plans", "[?mod1440_of_c_bp|0]", None, "eq", "Equipped", "[?mod1440_of_c_eq|0]%",
         "What his divisions hold of what they need, as Army Readiness counted it at the start of the day."),
    ]
    sea = [("ships", "Ships", "[?mod1440_of_c_cmd|0]", None, "k1", "Carriers", "[?mod1440_of_c_k1|0]", None),
           ("k2", "Capital ships", "[?mod1440_of_c_k2|0]", None, "k3", "Screens", "[?mod1440_of_c_k3|0]", None),
           ("k4", "Submarines", "[?mod1440_of_c_k4|0]", None, None, None, None, None)]
    for kind, rows, condition, test in (("l", land, army, lambda st: st["rank"] != 3), ("s", sea, navy, lambda st: st["rank"] == 3)):
        for k, (n1, l1, v1, t1, n2, l2, v2, t2) in enumerate(rows):
            y = top + 42 + k * OF_PAIR
            for name, label, value, tip, lx, vx, vw in ((n1, l1, v1, t1, 16, 176, 120), (n2, l2, v2, t2, 336, 502, 126)):
                if not name:
                    continue
                widget = "of_c_p_%s_%s" % (kind, name)
                tooltip = B.key(widget + "_tt", tip) if tip else None
                inner += M.text(widget + "_l", lx, y, 150, B.key(widget + "_l", label), M.FONT_LABEL, height=22, tooltip=tooltip)
                inner += M.text(widget, vx, y - 1, vw, B.key(widget, value), M.FONT_VALUE, "right", 24, tooltip=tooltip)
                when = commands + condition
                show(widget + "_l", when, lambda st, t=test: st["has"] and not st["chain"] and t(st))
                if name == "plan":
                    inner += M.text(widget + "_none", vx, y, vw, B.key(widget + "_none", "no battle plan"), M.FONT_LABEL, "right", 22, tooltip=tooltip)
                    show(widget, when + "NOT = { %s }\n" % plan_none, lambda st, t=test: st["has"] and not st["chain"] and t(st) and not st["plan_none"])
                    show(widget + "_none", when + plan_none + "\n", lambda st, t=test: st["has"] and not st["chain"] and t(st) and st["plan_none"])
                elif name == "eq":
                    inner += M.text(widget + "_none", vx, y - 1, vw, B.key("of_c_dash", "\u00a7g-\u00a7!"), M.FONT_VALUE, "right", 24, tooltip=tooltip)
                    counted = is_one("mod1440_of_c_has_eq")
                    show(widget, when + counted + "\n", lambda st, t=test: st["has"] and not st["chain"] and t(st) and st["eq"])
                    show(widget + "_none", when + "NOT = { %s }\n" % counted, lambda st, t=test: st["has"] and not st["chain"] and t(st) and not st["eq"])
                else:
                    show(widget, when, lambda st, t=test: st["has"] and not st["chain"] and t(st))

    # the Chain of command: a field marshal leading an army group, his armies' battles while under him, his generals
    if OF_CHAIN:
        held = has + chain + "\n"
        inner += M.icon("of_f_chain_bg", 0, top, OF_STEEL % "chain")
        inner += M.text("of_f_chain_title", 12, top + 7, 260, B.key("of_f_chain_title", "Chain of command"), M.FONT_LABEL, height=22)
        inner += M.text("of_c_ch_more", 280, top + 10, 220, B.key("of_c_ch_more", "\u00a7g+[?mod1440_of_c_subs_more|0] more: Order of battle\u00a7!"),
                        M.FONT_SMALL, "right", 20)
        inner += M.button("of_c_map2", W - 8 - 120, top + 5, "GFX_sort_button_120x29", B.key("of_c_map", "Show on map"),
                          tooltip=B.key("of_c_map_tt", "The camera to the state where most of his divisions stand."))
        show("of_f_chain_bg", held, lambda st: st["has"] and st["chain"])
        show("of_f_chain_title", held, lambda st: st["has"] and st["chain"])
        show("of_c_ch_more", held + M.more_than_zero("mod1440_of_c_subs_more"), lambda st: st["has"] and st["chain"] and st["subs"] > OF_CHAIN_ROWS)
        show("of_c_map2", held + located, lambda st: st["has"] and st["chain"] and st["loc"])
        effects += block("of_c_map2_click", go)
        for label, cx, cw, fmt in (("General", 48, 200, "left"), ("Army", 256, 166, "left"), ("Div", 426, 50, "centre"),
                                   ("Won", 480, 46, "centre"), ("Lost", 530, 46, "centre"), ("Skill", 580, 44, "centre")):
            widget = "of_c_ch_h_" + label.lower()
            inner += M.text(widget, cx, top + 42, cw, B.key(widget, "\u00a7g%s\u00a7!" % label), M.FONT_SMALL, fmt, 20)
            show(widget, held, lambda st: st["has"] and st["chain"])
        ty = top + 64
        total_tip = B.key("of_c_ch_total_tt", "His army group's divisions today, and the battles his generals' armies won and lost while "
                          "they served under him, counted from the day this build of the mod first ran.")
        inner += M.icon("of_c_ch_total_bg", 8, ty, PICK % (624, 26))
        inner += M.text("of_c_ch_total", 48, ty + 1, 200, B.key("of_c_ch_total", "Under his command"), M.FONT_LABEL, height=22, tooltip=total_tip)
        inner += M.text("of_c_ch_since", 256, ty + 3, 166, B.key("of_c_ch_since", "\u00a7gsince [?mod1440_of_chain_since.%s]\u00a7!" % LONG), M.FONT_SMALL, height=20)
        for name, value, cx, cw in (("div", "[?mod1440_of_c_cmd|0]", 426, 50), ("won", "[?mod1440_of_c_gwon|0]", 480, 46),
                                    ("lost", "[?mod1440_of_c_glost|0]", 530, 46)):
            inner += M.text("of_c_ch_" + name, cx, ty, cw, B.key("of_c_ch_" + name, value), M.FONT_VALUE, "centre", 24, tooltip=total_tip)
        for widget in ("of_c_ch_total_bg", "of_c_ch_total", "of_c_ch_since", "of_c_ch_div", "of_c_ch_won", "of_c_ch_lost"):
            show(widget, held, lambda st: st["has"] and st["chain"])
        by = ty + 28
        for n in (1, 3):
            inner += M.icon("of_c_ch_band_%d" % n, 8, by + n * 32, STRIPE % (624, 32))
            show("of_c_ch_band_%d" % n, held, lambda st: st["has"] and st["chain"])
        inner += M.text("of_c_ch_none", 48, by + 6, 560, B.key("of_c_ch_none", "\u00a7gNo general is linked to him today; the link is made once a day.\u00a7!"),
                        M.FONT_SMALL, height=20, tooltip=B.key("of_c_ch_none_tt", "A general is linked from the state where most of his "
                                                               "army's divisions stand, once a day."))
        show("of_c_ch_none", held + "check_variable = { mod1440_of_c_subs_n < 1 }\n", lambda st: st["has"] and st["chain"] and not st["subs"])
        inner += ('gridboxtype = {\n\tname = "of_c_subs_grid"\n\tposition = { x = 8 y = %d }\n\tsize = { width = 624 height = %d }\n'
                  '\tslotsize = { width = 1 height = 1 }\n\tadd_horizontal = no\n\tformat = "UPPER_LEFT"\n}\n' % (by, OF_CHAIN_ROWS * 32))
    # a row of the chain card: the row's scope is the general
    sub = scaled("of_sub_face", 8, 1, UNKNOWN, 0.15)
    properties += block("of_sub_face", GAME_FACE)
    sub += M.button("of_sub_hit", 0, 0, "GFX_1440p_SG_hit_240x32", tooltip=B.key("of_sub_hit_tt", "Click for his file."))
    sub += fixed(plain("of_sub_name", 40, 4, 200, B.key("of_sub_name", "\u00a7Y[THIS.GetName]\u00a7!"), height=22))
    sub += M.text("of_sub_army", 248, 4, 166, B.key("of_sub_army", ARMY_NAME), M.FONT_LABEL, height=22, fixed=True)
    sub += M.text("of_sub_army_n", 248, 4, 166, B.key("of_sub_army_n", "army of [?num_units|0] divisions"), M.FONT_LABEL, height=22, fixed=True)
    sub_triggers += block("of_sub_army_visible", NAMES_ON + "\n") + block("of_sub_army_n_visible", "NOT = { %s }\n" % NAMES_ON)
    sub_shows["of_sub_army"] = lambda r: r["names"]
    sub_shows["of_sub_army_n"] = lambda r: not r["names"]
    for name, value, cx, cw in (("div", "[?num_units|0]", 418, 50), ("won", "[?mod1440_of_won|0]", 472, 46),
                                ("lost", "[?mod1440_of_lost|0]", 522, 46), ("skill", "[?skill_level|0]", 572, 44)):
        sub += M.text("of_sub_" + name, cx, 3, cw, B.key("of_sub_" + name, value), M.FONT_VALUE, "centre", 24)
    sub += M.icon("of_sub_mark", 604, 9, "GFX_army_experience")[:-3] + ' pdx_tooltip = "%s" }\n' % B.key("of_row_mark_tt", "A free slot in his trait tree: a trait can be chosen there.")
    sub_triggers += block("of_sub_mark_visible", FREE_SLOT + "\n")
    sub_shows["of_sub_mark"] = lambda r: r.get("can", False)
    effects += block("of_sub_hit_click", "mod1440_of_me = yes\n" + block("ROOT", open_file("of_me")))

    # Traits: up to six with icon and name, each with the tooltip of its effects; the chosen of the slots
    top = OF_TOP["traits"]
    lower += M.icon("of_f_tr_bg", 0, top, OF_STEEL % "traits")
    lower += M.text("of_f_tr_title", 12, top + 4, 70, B.key("of_f_traits_title", "Traits"), M.FONT_LABEL, height=22)
    show("of_f_tr_bg", has, lambda st: st["has"])
    show("of_f_tr_title", has, lambda st: st["has"])
    lower += M.text("of_c_tr_over", 80, top + 5, 66, B.key("of_c_tr_over", "+[?mod1440_of_c_tr_over|0] more"), M.FONT_SMALL, height=20)
    lower += M.text("of_c_tr_other", 146, top + 5, 106, B.key("of_c_tr_other", "+[?mod1440_of_c_tr_other|0] of other mods"), M.FONT_SMALL, height=20,
                    tooltip=B.key("of_c_tr_other_tt", "Traits the mod's table of traits does not name: another mod's."))
    show("of_c_tr_over", has + M.more_than_zero("mod1440_of_c_tr_over"), lambda st: st["has"] and st["tr_over"] > 0)
    show("of_c_tr_other", has + M.more_than_zero("mod1440_of_c_tr_other"), lambda st: st["has"] and st["tr_other"] > 0)
    can = is_one("mod1440_of_c_can")
    lower += M.icon("of_c_tr_can_i", 254, top + 8, "GFX_army_experience")
    lower += M.text("of_c_tr_can", 272, top + 4, 160, B.key("of_c_tr_can", "a trait can be chosen"), M.FONT_LABEL, height=22,
                    tooltip=B.key("of_c_tr_can_tt", "A free slot in his trait tree (fewer traits chosen than slots): a trait can be chosen there, in the game's "
                                  "own window of the general or admiral."))
    show("of_c_tr_can_i", has + serving + can + "\n", lambda st: st["has"] and st["can"])
    show("of_c_tr_can", has + serving + can + "\n", lambda st: st["has"] and st["can"])
    lower += M.text("of_c_tr_count", 440, top + 4, 184, B.key("of_c_tr_count", "[?mod1440_of_c_tr_as|0] of [?mod1440_of_c_max|0] chosen"),
                    M.FONT_LABEL, "right", 22, tooltip=B.key("of_c_tr_count_tt", "Traits chosen in his trait tree (num_assigned_traits), of the slots "
                                                             "his rank and skill give him (num_max_traits)."))
    show("of_c_tr_count", has, lambda st: st["has"])
    lower += M.text("of_c_tr_none", 16, top + 38, W - 32, B.key("of_c_tr_none", "No trait the mod's table names."), M.FONT_SMALL, height=22)
    show("of_c_tr_none", has + "check_variable = { mod1440_of_c_tr_k < 1 }\n", lambda st: st["has"] and st["tr_k"] < 1)
    for k in range(TRAIT_ICONS):
        tx, ty = 12 + (k % 3) * 208, top + 34 + (k // 3) * 40
        widget = "of_c_tr_%d" % k
        tip_key = B.key(widget + "_tt", "\u00a7Y[?mod1440_of_c_tr^%d.GetTokenLocalizedKey]\u00a7!\\n[?mod1440_of_c_tr_e^%d.GetTokenLocalizedKey]" % (k, k))
        lower += M.icon(widget, tx, ty, TRAIT_SAMPLE[k])[:-3] + ' pdx_tooltip = "%s" }\n' % tip_key
        lprop(widget, 'image = "GFX_trait_[?mod1440_of_c_tr^%d.GetTokenKey]"\n' % k)
        lower += M.icon(widget + "_x", tx, ty, "GFX_trait_unknown")[:-3] + ' pdx_tooltip = "%s" }\n' % tip_key
        lower += M.text(widget + "_n", tx + 29, ty + 5, 172, B.key(widget + "_n", "[?mod1440_of_c_tr^%d.GetTokenLocalizedKey]" % k), M.FONT_LABEL,
                        height=22, fixed=True, tooltip=tip_key)
        show(widget, has + "check_variable = { mod1440_of_c_tr_i > %d }\n" % k, lambda st, k=k: st["has"] and st["tr_i"] > k)
        show(widget + "_x", has + "check_variable = { mod1440_of_c_tr_i < %d }\ncheck_variable = { mod1440_of_c_tr_k > %d }\n" % (k + 1, k),
             lambda st, k=k: st["has"] and st["tr_i"] <= k < st["tr_k"])
        show(widget + "_n", has + "check_variable = { mod1440_of_c_tr_k > %d }\n" % k, lambda st, k=k: st["has"] and st["tr_k"] > k)

    # the Service record: a banded table (the figures, the dates, From a division, Decorations) over the rack of his
    # medals; Award... and Take back last in its head
    top = OF_TOP["rec"]
    lower += M.icon("of_f_rec_bg", 0, top, OF_STEEL % "rec")
    lower += M.text("of_f_rec_title", 12, top + 7, 240, B.key("of_f_rec_title", "Service record"), M.FONT_LABEL, height=22)
    show("of_f_rec_bg", filing, lambda st: st["has"] and not st["award"])
    show("of_f_rec_title", filing, lambda st: st["has"] and not st["award"])
    lower += M.button("of_award_on", W - 8 - 120 - 6 - 120, top + 5, "GFX_sort_button_120x29", B.key("of_award_on", "Award..."),
                      tooltip=B.key("of_award_on_tt", "Your country's medals: award him one."))
    lower += M.button("of_takeback", W - 8 - 120, top + 5, "GFX_sort_button_120x29", B.key("of_takeback", "Take back last"),
                      tooltip=B.key("of_takeback_tt", "Takes the decoration awarded last from this officer."))
    lower += M.button("of_award_off", W - 8 - 120, top + 5, "GFX_sort_button_120x29", B.key("of_award_off", "Back to his file"))
    show("of_award_on", filing, lambda st: st["has"] and not st["award"])
    show("of_award_off", awarding, lambda st: st["has"] and st["award"])
    show("of_takeback", filing + M.more_than_zero("mod1440_of_c_dec_n"), lambda st: st["has"] and not st["award"] and st["dec"] > 0)
    effects += block("of_takeback_click", "mod1440_md_takeback = yes\n")
    effects += block("of_award_on_click", setv("mod1440_of_awarding", 1) + "add_to_variable = { mod1440_rec_dirty = 1 }\n")
    effects += block("of_award_off_click", setv("mod1440_of_awarding", 0) + "add_to_variable = { mod1440_rec_dirty = 1 }\n")
    for n in (1, 3):
        lower += M.icon("of_f_rec_band_%d" % n, 8, top + 42 + n * OF_PAIR, STRIPE % (624, OF_PAIR))
        show("of_f_rec_band_%d" % n, filing, lambda st: st["has"] and not st["award"])
    for k, (name, label, value, tip) in enumerate(OF_FIGURES):
        y = top + 42 + k * OF_PAIR
        tooltip = B.key("of_c_%s_tt" % name, tip)
        lower += M.text("of_c_%s_l" % name, 16, y, 110, B.key("of_c_%s_l" % name, label), M.FONT_LABEL, height=22, tooltip=tooltip)
        lower += M.text("of_c_%s" % name, 126, y - 1, 70, B.key("of_c_%s" % name, value), M.FONT_VALUE, "right", 24, tooltip=tooltip)
        show("of_c_%s_l" % name, filing, lambda st: st["has"] and not st["award"])
        show("of_c_%s" % name, filing, lambda st: st["has"] and not st["award"])
    for variant, rows in OF_RIGHT.items():
        which = rank(1) if variant == "m" else "NOT = { %s }\n" % rank(1).strip()
        is_m = (lambda st: st["rank"] == 1) if variant == "m" else (lambda st: st["rank"] != 1)
        for k, name in enumerate(rows):
            y = top + 42 + k * OF_PAIR
            widget = "of_c_%s_%s" % (variant, name)
            when = filing + which
            test = lambda st, m=is_m: st["has"] and not st["award"] and m(st)
            label = OF_DATES.get(name) or {"div": "From a division", "dec": "Decorations"}[name]
            lower += M.text(widget + "_l", 240, y, 190, B.key("of_c_%s_l" % name, label), M.FONT_LABEL, height=22)
            show(widget + "_l", when, test)
            if name in OF_DATES:
                dated = is_one("mod1440_of_c_has_%s" % name)
                lower += M.text(widget, 430, y, 200, B.key("of_c_%s" % name, "[?mod1440_of_c_%s.%s]" % (name, LONG)), M.FONT_LABEL, "right", 22)
                lower += M.text(widget + "_old", 430, y, 200, B.key("of_c_%s_old" % name, "before the record began" if name == "since" else "-"),
                                M.FONT_LABEL, "right", 22)
                show(widget, when + dated + "\n", lambda st, t=test, n=name: t(st) and n in st["dates"])
                show(widget + "_old", when + "NOT = { %s }\n" % dated, lambda st, t=test, n=name: t(st) and n not in st["dates"])
            elif name == "div":
                tip = B.key("of_c_div_tt", "Whether he was promoted to his command from a division's (or a ship's) command.")
                lower += M.text(widget, 430, y, 200, B.key("of_c_div_yes", "yes"), M.FONT_LABEL, "right", 22, tooltip=tip)
                lower += M.text(widget + "_no", 430, y, 200, B.key("of_c_div_no", "no"), M.FONT_LABEL, "right", 22, tooltip=tip)
                show(widget, when + is_one("mod1440_of_c_fromdiv") + "\n", lambda st, t=test: t(st) and st["fromdiv"])
                show(widget + "_no", when + "NOT = { %s }\n" % is_one("mod1440_of_c_fromdiv"), lambda st, t=test: t(st) and not st["fromdiv"])
            else:
                lower += M.text(widget, 430, y - 1, 200, B.key("of_c_decs", "[?mod1440_of_c_dec_n|0]"), M.FONT_VALUE, "right", 24)
                show(widget, when, test)
    my = top + 42 + 5 * OF_PAIR + 8
    for k in range(RACK):
        tip = B.key("of_c_rack_%d_tt" % k, "[?mod1440_of_c_dec_key^%d.GetTokenLocalizedKey]\\n[?mod1440_of_c_dec_date^%d.%s]" % (k, k, LONG))
        widget = "of_c_rack_%d" % k
        lower += scaled(widget, 16 + k * 46, my, MEDAL_STRIP % "ger", 0.6, tip)
        lprop(widget, 'image = "[?mod1440_of_c_dec_strip^%d.GetTokenKey]"\nframe = mod1440_of_c_dec_frame^%d\n' % (k, k))
        show(widget, filing + "check_variable = { mod1440_of_c_dec_n > %d }\n" % k, lambda st, k=k: st["has"] and not st["award"] and st["dec"] > k)
    lower += M.text("of_c_dec_last", 16 + 46 + 8, my + 14, 400, B.key("of_c_dec_last", "\u00a7g[?mod1440_of_c_dec_lk.GetTokenLocalizedKey], "
                                                                     "[?mod1440_of_c_dec_ld.%s]\u00a7!" % LONG), M.FONT_SMALL, height=20)
    lprop("of_c_dec_last", "x = mod1440_of_c_dec_tx\n")
    show("of_c_dec_last", filing + M.more_than_zero("mod1440_of_c_dec_n") + "check_variable = { mod1440_of_c_dec_n < %d }\n" % (RACK_TEXT + 1),
         lambda st: st["has"] and not st["award"] and 0 < st["dec"] <= RACK_TEXT)
    lower += M.text("of_c_dec_none", 16, my + 14, W - 32, B.key("of_c_dec_none", "\u00a7gNone yet. Award... shows the medals of your country.\u00a7!"),
                    M.FONT_SMALL, height=20)
    show("of_c_dec_none", filing + "check_variable = { mod1440_of_c_dec_n < 1 }\n", lambda st: st["has"] and not st["award"] and st["dec"] < 1)

    # the Award mode: the country's medals over the service record and the diary
    lower += M.icon("of_f_award_bg", 0, top, OF_STEEL % "award")
    lower += M.icon("of_f_award_m_bg", 0, top, OF_STEEL % "award_m")
    lower += M.text("of_f_award_title", 12, top + 7, 300, B.key("of_f_award_title", "Award a decoration"), M.FONT_LABEL, height=22)
    show("of_f_award_bg", awarding + not_chain, lambda st: st["has"] and st["award"] and not st["chain"])
    show("of_f_award_m_bg", awarding + chain + "\n", lambda st: st["has"] and st["award"] and st["chain"])
    show("of_f_award_title", awarding, lambda st: st["has"] and st["award"])
    lower += M.text("of_md_hint", 16, top + 42, W - 32, B.key(
        "of_md_hint", "Your country's medals as the game has them: a record only, no bonus, no cost."), M.FONT_SMALL, height=20)
    show("of_md_hint", awarding, lambda st: st["has"] and st["award"])
    for k in range(MEDAL_SLOTS):
        px, py = 8 + (k % 2) * 316, top + 66 + (k // 2) * 60
        more = awarding + "check_variable = { mod1440_md_count > %d }\n" % k
        held = "check_variable = { mod1440_md_has^%d = 1 }\n" % k
        lower += M.icon("of_md_%d_bg" % k, px, py, M.tile_sprite(306, 56))
        lower += scaled("of_md_%d" % k, px + 8, py + 3, MEDAL_STRIP % "ger", 0.6)
        lprop("of_md_%d" % k, 'image = "[?mod1440_md_strip^%d.GetTokenKey]"\nframe = mod1440_md_frame^%d\n' % (k, k))
        lower += M.text("of_md_%d_name" % k, px + 52, py + 4, 246, B.key("of_md_%d_name" % k, "[?mod1440_md_key^%d.GetTokenLocalizedKey]" % k),
                        M.FONT_LABEL, height=22, fixed=True)
        lower += M.button("of_award_%d" % k, px + 52, py + 26, "GFX_sort_button_100x29", B.key("of_award", "Award"))
        lower += M.text("of_md_%d_held" % k, px + 52, py + 30, 240, B.key("of_md_%d_held" % k, "\u00a7Gawarded\u00a7! [?mod1440_md_date^%d.%s]" % (k, LONG)),
                        M.FONT_SMALL, height=20)
        test = lambda st, k=k: st["has"] and st["award"] and st["medals"] > k
        for widget in ("of_md_%d_bg" % k, "of_md_%d" % k, "of_md_%d_name" % k):
            show(widget, more, test)
        show("of_award_%d" % k, more + "NOT = { %s }\n" % held.strip(), lambda st, k=k, t=test: t(st) and k not in st["held"])
        show("of_md_%d_held" % k, more + held, lambda st, k=k, t=test: t(st) and k in st["held"])
        effects += block("of_award_%d_click" % k, tmp("md_k", k) + "mod1440_md_award = yes\n")

    # what the War Diary has about him: his own lines, and the states and victory points he was at (5 under a chain card)
    top = OF_TOP["diary"]
    lower += M.icon("of_f_diary_bg", 0, top, OF_STEEL % "diary")
    lower += M.icon("of_f_diary_m_bg", 0, top, OF_STEEL % "diary_m")
    lower += M.text("of_f_diary_title", 12, top + 4, 300, B.key("of_f_diary_title", "In the War Diary"), M.FONT_LABEL, height=22)
    lower += M.text("of_ln_order", W - 16 - 150, top + 5, 150, B.key("of_ln_order", "\u00a7gnewest first\u00a7!"), M.FONT_SMALL, "right", 20)
    lower += M.text("of_ln_none", 16, top + 33, 500, B.key("of_ln_none", "Nothing yet."), M.FONT_LABEL, height=22)
    show("of_f_diary_bg", filing + not_chain, lambda st: st["has"] and not st["award"] and not st["chain"])
    show("of_f_diary_m_bg", filing + chain + "\n", lambda st: st["has"] and not st["award"] and st["chain"])
    for widget in ("of_f_diary_title", "of_ln_order"):
        show(widget, filing, lambda st: st["has"] and not st["award"])
    show("of_ln_none", filing + "check_variable = { mod1440_of_ln_n < 1 }\n", lambda st: st["has"] and not st["award"] and not st["lines"])
    for k in range(CARD_LINES):
        more = filing + "check_variable = { mod1440_of_ln_n > %d }\n" % k + (not_chain if k >= CHAIN_LINES else "")

        def line_test(st, k=k):
            return st["has"] and not st["award"] and k < len(st["lines"]) and (k < CHAIN_LINES or not st["chain"])
        ly = top + 31 + k * OF_PAIR
        if k % 2:
            lower += M.icon("of_ln_%d_bg" % k, 8, ly, STRIPE % (624, OF_PAIR))
            show("of_ln_%d_bg" % k, more, line_test)
        lower += M.text("of_ln_%d_d" % k, 16, ly, 136, B.key("of_ln_%d_d" % k, "[?mod1440_of_ln_date^%d.%s]" % (k, LONG)), M.FONT_LABEL, height=22)
        show("of_ln_%d_d" % k, more, line_test)
        for family, text_icon in sorted(FAMILY_ICON.items()):
            widget = "of_ln_%d_f%d" % (k, family)
            lower += M.text(widget, 158, ly, 24, B.key("wd_icon_%d" % family, "\u00a3" + text_icon), M.FONT_SMALL, height=22)
            show(widget, more + "check_variable = { mod1440_of_ln_fam^%d = %d }\n" % (k, family),
                 lambda st, k=k, f=family, t=line_test: t(st) and st["lines"][k][0] == f)
        lower += M.text("of_ln_%d" % k, 184, ly, 206, B.key("of_ln_%d" % k, "[?mod1440_of_ln_kind^%d.GetTokenLocalizedKey]" % k), M.FONT_LABEL,
                        height=22, fixed=True)
        show("of_ln_%d" % k, more, line_test)
        lower += M.text("of_ln_%d_s" % k, 396, ly, 228, B.key("of_ln_%d_s" % k, "\u00a7Y[?mod1440_of_ln_a^%d.GetName]\u00a7!" % k), M.FONT_LABEL,
                        height=22, fixed=True)
        lower += M.text("of_ln_%d_p" % k, 396, ly, 228, B.key("of_ln_%d_p" % k, "\u00a7Y[?mod1440_of_ln_a^%d.GetTokenLocalizedKey]\u00a7!" % k),
                        M.FONT_LABEL, height=22, fixed=True)
        show("of_ln_%d_s" % k, more + "check_variable = { mod1440_of_ln_sa^%d = 2 }\n" % k, lambda st, k=k, t=line_test: t(st) and st["lines"][k][1] == 2)
        show("of_ln_%d_p" % k, more + "check_variable = { mod1440_of_ln_sa^%d = 3 }\n" % k, lambda st, k=k, t=line_test: t(st) and st["lines"][k][1] == 3)

    # the y property of every widget of the three lower cards: its place in a general's file, OF_DY lower under the chain card
    low_at = {}
    for m in re.finditer(r'name = "(\w+)" position = \{ x = (-?\d+) y = (-?\d+) \}', lower):
        low_at[m.group(1)] = (int(m.group(2)), int(m.group(3)))
        lprop(m.group(1), "y = mod1440_of_y_%s\n" % m.group(3))
    properties += "".join(block(name, lines) for name, lines in lprops.items())
    lows = sorted(set(y for x, y in low_at.values()))
    place_y = ("".join(setv("mod1440_of_y_%d" % y, y) for y in lows)
               + iff(is_one("mod1440_of_c_chain"), "".join("add_to_variable = { mod1440_of_y_%d = %d }\n" % (y, OF_DY) for y in lows)))
    body += M.box("of_card", OF_FILE_X, REC_BODY_Y, OF_FILE_W, REC_BODY_H, inner + lower)

    gui, script = page_gui("of", 1, body, dirty="mod1440_rec_dirty",
                           lists=block("of_grid", 'array = mod1440_of_rows\nchange_scope = yes\nentry_container = "mod1440_records_officer_row"\n')
                           + face_list("of_c_gface_grid", "mod1440_of_c_ul", "of_c_gface")
                           + block("of_c_army_grid", 'array = mod1440_of_c_ul\nchange_scope = yes\nentry_container = "mod1440_records_of_c_army_row"\n')
                           + (block("of_c_subs_grid", 'array = mod1440_of_c_subs\nchange_scope = yes\nentry_container = "mod1440_records_of_sub_row"\n')
                              if OF_CHAIN else ""),
                           effects=effects, triggers=triggers + row_triggers + army_row_trigger + sub_triggers, properties=properties)
    gui += row("mod1440_records_officer_row", OF_ROW_W, OF_ROW, entry)
    gui += game_face("of_c_gface", 1.0)
    gui += row("mod1440_records_of_c_army_row", 290, 30, army_entry)
    gui += row("mod1440_records_of_sub_row", 624, 32, sub)
    OF_SCENE.clear()
    OF_SCENE.update({"shows": shows, "row_shows": row_shows, "sub_shows": sub_shows, "low_at": low_at})

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
    keep = UL_MARK + officer_table(portrait_version) + tmp("of_keep", 1) + setv("mod1440_of_ind", 0)
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
    keep += iff("check_variable = { ROOT.mod1440_of_show = 6 }", tmp("of_keep", 0))      # E2 round 2: Order of battle, made apart
    frames = "".join(setv("mod1440_of_frame_%d" % v, 1) for v, _, _, _ in filters)
    frames += "".join(iff("check_variable = { mod1440_of_show = %d }" % v, setv("mod1440_of_frame_%d" % v, 2)) for v, _, _, _ in filters)

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
    # E2 round 2: the army card's subject (0 none, 1 an army, 2 an army group, 3 a fleet), the Command table, where his
    # troops stand (Army Readiness's count of the day: mod1440_al_loc, _lcnt, _hq, _eq), the chain of command
    copy_command = (
        setv("PREV.mod1440_of_c_mode", 0)
        + iff("NOT = { %s } check_variable = { num_units > 0 } NOT = { is_navy_leader = yes }" % FORMER, (
            setv("PREV.mod1440_of_c_mode", 1) + iff("is_leading_army_group = yes", setv("PREV.mod1440_of_c_mode", 2))))
        + iff("NOT = { %s } is_navy_leader = yes check_variable = { num_ships > 0 }" % FORMER, setv("PREV.mod1440_of_c_mode", 3))
        + "".join(setv("PREV.mod1440_of_c_%s" % short, variable) for short, variable in (
            ("inf", "num_infantry"), ("mot", "num_motorized"), ("mech", "num_mechanized"), ("att", "num_units_offensive_combats"),
            ("dfd", "num_units_defensive_combats"), ("ent", "avg_unit_entrenchment_ratio"), ("bp", "num_battle_plans"),
            ("tr_as", "num_assigned_traits")))
        + setv("PREV.mod1440_of_c_oth", "num_units")
        + "".join("subtract_from_variable = { PREV.mod1440_of_c_oth = %s }\n" % v for v in ("num_infantry", "num_armored", "num_motorized", "num_mechanized"))
        + setv("PREV.mod1440_of_c_has_eq", 0) + setv("PREV.mod1440_of_c_lcnt", 0) + setv("PREV.mod1440_of_c_has_hq", 0)
        + iff("check_variable = { num_units > 0 } NOT = { is_navy_leader = yes }", (
            iff("has_variable = mod1440_al_eq", setv("PREV.mod1440_of_c_eq", "mod1440_al_eq") + setv("PREV.mod1440_of_c_has_eq", 1))
            + iff("check_variable = { mod1440_al_lcnt > 0 }", setv("PREV.mod1440_of_c_loc", "mod1440_al_loc") + setv("PREV.mod1440_of_c_lcnt", "mod1440_al_lcnt"))
            # the HQ as Army Readiness asks it (D2 fix round 2: state_deployed, SCR-069)
            + iff("check_variable = { mod1440_al_hq > 0 }", setv("PREV.mod1440_of_c_hq", "mod1440_al_hq") + setv("PREV.mod1440_of_c_has_hq", 1))))
        + setv("PREV.mod1440_of_c_can", 0) + iff(FREE_SLOT, setv("PREV.mod1440_of_c_can", 1))
        + setv("PREV.mod1440_of_c_fromdiv", 0) + iff("is_promoted_from_unit = yes", setv("PREV.mod1440_of_c_fromdiv", 1))
        + setv("PREV.mod1440_of_c_chain", 0) + setv("PREV.mod1440_of_c_fm_n", 0) + setv("PREV.mod1440_of_c_subs_n", 0)
        + setv("PREV.mod1440_of_c_gwon", "mod1440_of_gwon") + setv("PREV.mod1440_of_c_glost", "mod1440_of_glost"))
    if OF_CHAIN:
        copy_command += (
            iff("NOT = { %s } is_leading_army_group = yes" % FORMER, (
                setv("PREV.mod1440_of_c_chain", 1) + setv("PREV.mod1440_of_c_subs_n", "mod1440_of_subs^num")
                + block("for_each_loop", "array = mod1440_of_subs\nvalue = of_v\nindex = of_i\n" + iff(
                    "check_variable = { of_i < %d }" % OF_CHAIN_ROWS, "add_to_array = { PREV.mod1440_of_c_subs = of_v }\n"))))
            + iff("NOT = { %s } NOT = { is_leading_army_group = yes } check_variable = { num_units > 0 } check_variable = { mod1440_of_fm_n > 0 }" % FORMER, (
                setv("PREV.mod1440_of_c_fm", "mod1440_of_fm") + setv("PREV.mod1440_of_c_fm_n", "mod1440_of_fm_n")
                + tmp("of_f", "mod1440_of_fm") + tmp("of_k", 0) + block("var:of_f", tmp("of_k", "mod1440_of_subs^num"))
                + setv("PREV.mod1440_of_c_fm_k", "of_k"))))
    copy_traits = (
        iff(stale_traits, "mod1440_of_traits = yes\n")
        + setv("PREV.mod1440_of_c_traits", "num_traits") + setv("PREV.mod1440_of_c_max", "num_max_traits")
        + setv("PREV.mod1440_of_c_tr_i", "mod1440_of_tr_i") + setv("PREV.mod1440_of_c_tr_k", "mod1440_of_tr_k")
        + setv("PREV.mod1440_of_c_tr_other", "num_traits") + "subtract_from_variable = { PREV.mod1440_of_c_tr_other = mod1440_of_tr_k }\n"
        + setv("PREV.mod1440_of_c_tr_over", "mod1440_of_tr_k") + "subtract_from_variable = { PREV.mod1440_of_c_tr_over = %d }\n" % TRAIT_ICONS
        + block("for_each_loop", "array = mod1440_of_tr\nvalue = of_v\nadd_to_array = { PREV.mod1440_of_c_tr = of_v }\n")
        + block("for_each_loop", "array = mod1440_of_tr_e\nvalue = of_v\nadd_to_array = { PREV.mod1440_of_c_tr_e = of_v }\n"))
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

    # E2 round 2: the list is made in mod1440_of_part, put into the chosen order (mod1440_of_order), and appended to the
    # rows; Order of battle does it once for the army groups, once for each marshal's generals (indented), once for the
    # armies under the High Command and once for the fleets
    def append(ind):
        return block("for_each_scope_loop", "array = mod1440_of_part\n" + setv("mod1440_of_ind", ind) + "mod1440_of_me = yes\n"
                     + iff(has_me, "add_to_array = { ROOT.mod1440_of_rows = of_me }\n"))

    def gather(scope, limit):
        return ("clear_array = mod1440_of_part\n"
                + block(scope, "limit = { %s }\nmod1440_of_me = yes\n" % limit + iff(has_me, "add_to_array = { PREV.mod1440_of_part = of_me }\n")))
    order = iff("check_variable = { mod1440_of_sort_by > 0 }", (
        "clear_array = mod1440_of_keys\n"
        + block("for_each_scope_loop", "array = mod1440_of_part\n" + tmp("of_key", 0) + keys
                + iff(is_one("ROOT.mod1440_of_up"), "multiply_temp_variable = { of_key = -1 }\n")
                + "add_to_array = { ROOT.mod1440_of_keys = of_key }\n")
        + "clear_array = mod1440_of_sorted\n"
        + block("for_loop_effect", "start = 0\nend = mod1440_of_part^num\nvalue = of_step\n"
                + block("find_highest_in_array", "array = mod1440_of_keys\nvalue = of_high\nindex = of_at\n")
                + "add_to_array = { mod1440_of_sorted = mod1440_of_part^of_at }\n" + setv("mod1440_of_keys^of_at", -2000000))
        + "clear_array = mod1440_of_part\n"
        + block("for_each_loop", "array = mod1440_of_sorted\nvalue = of_copy\nadd_to_array = { mod1440_of_part = of_copy }\n")))
    oob = (
        "mod1440_of_chain = yes\n"
        + gather("every_army_leader", "is_leading_army_group = yes") + "mod1440_of_order = yes\n"
        + "clear_array = mod1440_of_oob_fm\n"
        + block("for_each_loop", "array = mod1440_of_part\nvalue = ob_v\nadd_to_array = { mod1440_of_oob_fm = ob_v }\n")
        + block("for_each_scope_loop", (
            "array = mod1440_of_oob_fm\n" + setv("mod1440_of_ind", 0) + "mod1440_of_me = yes\n"
            + iff(has_me, "add_to_array = { ROOT.mod1440_of_rows = of_me }\n")
            + block("ROOT", "clear_array = mod1440_of_part\n")
            + block("for_each_loop", "array = mod1440_of_subs\nvalue = ob_s\nadd_to_array = { ROOT.mod1440_of_part = ob_s }\n")
            + block("ROOT", "mod1440_of_order = yes\n" + append(1))))
        + gather("every_army_leader", "NOT = { is_leading_army_group = yes } check_variable = { num_units > 0 } "
                 "NOT = { check_variable = { mod1440_of_fm_n > 0 } }") + "mod1440_of_order = yes\n" + append(0)
        + gather("every_navy_leader", "check_variable = { num_ships > 0 }") + "mod1440_of_order = yes\n" + append(0))
    # The chain of command, once a day after Army Readiness's count (mod1440_al_loc on each general with troops): see
    # the head of this section. Cost: the marshals leading an army group times the generals leading an army.
    # E2 fix round 2 (2026-10-30): the state test alone linked an army that serves in no army group (Cranz's I. SS-Standarten,
    # 3 divisions in Gdynia's state) to a marshal whose armies also stood there. Now each match is a candidate pair (general,
    # marshal, key), and the pairs are taken strongest first: the key is the share of the marshal's divisions in the general's
    # state that the general holds (x 1000), then the larger army. A marshal's num_units is the sum of his armies' divisions,
    # so each marshal keeps what remains of it (mod1440_of_cap); a general is linked only if his num_units fits, else his next
    # candidate, else the High Command. mod1440_of_fm_n keeps how many marshals matched him (2 or more: likely, decision 6).
    pair = ("add_to_array = { PREV.mod1440_of_ch_pg = ch_g }\nadd_to_array = { PREV.mod1440_of_ch_pm = of_me }\n"
            + tmp("ch_k", "ch_n") + "multiply_temp_variable = { ch_k = 1000 }\ndivide_temp_variable = { ch_k = ch_m }\n"
            + "add_to_temp_variable = { ch_k = ch_u }\nadd_to_array = { PREV.mod1440_of_ch_pk = ch_k }\n")
    take = (tmp("ch_g", "mod1440_of_ch_pg^ch_at") + tmp("ch_fm", "mod1440_of_ch_pm^ch_at") + setv("mod1440_of_ch_pk^ch_at", -1)
            + block("var:ch_g", iff("check_variable = { mod1440_of_fm_n = 0 }", (
                tmp("ch_u", "num_units") + tmp("ch_ok", 0)
                + block("var:ch_fm", iff("check_variable = { var = mod1440_of_cap value = ch_u compare = greater_than_or_equals }", (
                    "subtract_from_variable = { mod1440_of_cap = ch_u }\nadd_to_array = { mod1440_of_subs = ch_g }\n" + tmp("ch_ok", 1))))
                + iff("check_variable = { ch_ok = 1 }", setv("mod1440_of_fm", "ch_fm") + setv("mod1440_of_fm_n", "mod1440_of_fm_c"))))))
    guess_script = (
        "clear_array = mod1440_of_ch_pg\nclear_array = mod1440_of_ch_pm\nclear_array = mod1440_of_ch_pk\n"
        + block("every_army_leader", (
            "limit = { NOT = { is_leading_army_group = yes } check_variable = { num_units > 0 } check_variable = { mod1440_al_lcnt > 0 } }\n"
            + "mod1440_of_me = yes\n"
            + iff(has_me, (
                tmp("ch_g", "of_me") + tmp("ch_s", "mod1440_al_loc") + tmp("ch_n", "mod1440_al_lcnt") + tmp("ch_u", "num_units")
                + tmp("ch_hits", 0)
                + block("PREV", block("every_army_leader", (
                    "limit = { is_leading_army_group = yes }\n"
                    + tmp("ch_m", "num_units_in_state@var:ch_s") + tmp("ch_mu", "num_units")
                    + iff("check_variable = { var = ch_m value = ch_n compare = greater_than_or_equals } "
                          "check_variable = { var = ch_mu value = ch_u compare = greater_than_or_equals }", (
                              "add_to_temp_variable = { ch_hits = 1 }\nmod1440_of_me = yes\n" + iff(has_me, pair))))))
                + setv("mod1440_of_fm_c", "ch_hits")))))
        # the pairs, strongest first: each is looked at once
        + block("for_loop_effect", "start = 0\nend = mod1440_of_ch_pk^num\nvalue = ch_step\n"
                + block("find_highest_in_array", "array = mod1440_of_ch_pk\nvalue = ch_hi\nindex = ch_at\n")
                + iff("check_variable = { ch_hi > 0 }", take)))
    # E2b (2026-10-30, SCR-086): on a game with the Modding Manager's field marshal patch, has_orders_group is the id of the army
    # group a leader serves in (his own for a field marshal; 0 for none) as id x 0.00001; unpatched it is 1 or 0. The day's
    # values tell which (mod1440_of_exact), whatever the switch says (decision 2A). Exact: a general with an army takes the
    # marshal leading an army group whose value equals his; one at most can, so mod1440_of_fm_n is 1 and nothing is likely; 0
    # is the High Command. The values are copied into temporary variables and compared with check_variable's var/value form,
    # as the guess compares its counts.
    exact_script = (
        block("every_army_leader", (
            "limit = { NOT = { is_leading_army_group = yes } check_variable = { num_units > 0 } }\n"
            + tmp("ch_o", "has_orders_group") + "mod1440_of_me = yes\n"
            + iff("NOT = { check_variable = { ch_o = 0 } } %s" % has_me, (
                tmp("ch_g", "of_me") + tmp("ch_fm", 0)
                + block("PREV", block("every_army_leader", (
                    "limit = { is_leading_army_group = yes }\n" + tmp("ch_mo", "has_orders_group")
                    + iff("check_variable = { var = ch_mo value = ch_o compare = equals }", "mod1440_of_me = yes\n"
                          + iff(has_me, tmp("ch_fm", "of_me"))))))
                + iff("NOT = { check_variable = { ch_fm = 0 } }", (
                    setv("mod1440_of_fm", "ch_fm") + setv("mod1440_of_fm_n", 1) + setv("mod1440_of_fm_c", 1)
                    + block("var:ch_fm", "add_to_array = { mod1440_of_subs = ch_g }\n"))))))))
    chain_script = (
        iff("NOT = { has_variable = mod1440_of_chain_since }", setv("mod1440_of_chain_since", "global.date"))
        + block("every_army_leader", "clear_array = mod1440_of_subs\n" + setv("mod1440_of_fm_n", 0) + setv("mod1440_of_fm_c", 0)
                + setv("mod1440_of_cap", "num_units"))
        # a patched game: some army leader's value is neither 0 nor 1
        + tmp("ch_x", 0) + block("every_army_leader", iff("NOT = { check_variable = { has_orders_group = 0 } } "
                                                          "NOT = { check_variable = { has_orders_group = 1 } }", tmp("ch_x", 1)))
        + setv("mod1440_of_exact", "ch_x") + "mod1440_of_how = yes\n"
        + iff(is_one("mod1440_of_exact"), "mod1440_of_chain_exact = yes\n") + els("mod1440_of_chain_guess = yes\n"))
    lists_script = (
        "mod1440_of_seen = yes\nclear_array = mod1440_of_rows\nclear_array = mod1440_of_part\n"
        + block("for_each_scope_loop", "array = mod1440_of_known\n" + keep
                + iff("check_variable = { of_keep = 1 }", "mod1440_of_me = yes\n" + iff(
                    has_me, "add_to_array = { ROOT.mod1440_of_part = of_me }\n")))
        + (iff("check_variable = { mod1440_of_show = 6 }", "mod1440_of_oob = yes\n") + els("mod1440_of_order = yes\n" + append(0))
           if OF_CHAIN else "mod1440_of_order = yes\n" + append(0))
        + tmp("of_par", 0) + block("for_each_scope_loop", "array = mod1440_of_rows\n" + setv("mod1440_of_odd", "of_par")
                                   + iff("check_variable = { of_par = 0 }", tmp("of_par", 1)) + els(tmp("of_par", 0)))
        + frames + "mod1440_md_list = yes\nmod1440_of_card = yes\n")
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
        + "\n# Officers (E2 round 2): the chain of command for the country in scope, once a day after Army Readiness's count:\n"
        "# each general who leads an army with troops keeps the field marshal whose army group he is taken to serve in\n"
        "# (mod1440_of_fm; mod1440_of_fm_n how many army groups matched, 0 none, 2 or more: likely), and the marshal\n"
        "# keeps his generals (mod1440_of_subs).\n"
        + block("mod1440_of_chain", chain_script if OF_CHAIN else "")
        + "\n# Officers (E2b): the chain of command on a patched game (SCR-086), and the guess of E2 on any other.\n"
        + block("mod1440_of_chain_exact", exact_script if OF_CHAIN else "")
        + block("mod1440_of_chain_guess", guess_script if OF_CHAIN else "")
        + "\n# Officers (E2b): the words the tooltips of Reports to and Order of battle say of the links (mod1440_of_chain_how).\n"
        + block("mod1440_of_how", (
            iff(is_one("mod1440_of_exact"), setv("mod1440_of_chain_how", token("chain_exact", "from the game")))
            + block("else_if", "limit = { %s }\n" % is_one("mod1440_ar_names")
                    + setv("mod1440_of_chain_how", token("chain_unpatched", "guessed from where his troops stand: the game is not patched")))
            + els(setv("mod1440_of_chain_how", token("chain_guess", "guessed from where his troops stand")))))
        + "\n# Officers (E2 round 2): the battles of a general in scope counted for his field marshal too (decision 4).\n"
        + block("mod1440_of_g_won", iff("check_variable = { mod1440_of_fm_n > 0 }", block("var:mod1440_of_fm", "add_to_variable = { mod1440_of_gwon = 1 }\n")))
        + block("mod1440_of_g_lost", iff("check_variable = { mod1440_of_fm_n > 0 }", block("var:mod1440_of_fm", "add_to_variable = { mod1440_of_glost = 1 }\n")))
        + "\n# Officers (E2 round 2): mod1440_of_part in the order of the chosen column (mod1440_of_sort_by, _up).\n"
        + block("mod1440_of_order", order)
        + "\n# Officers (E2 round 2): the rows of Order of battle (filter 6).\n"
        + block("mod1440_of_oob", oob if OF_CHAIN else "")
        + "\n# Officers: makes the list of the page again: who the filter wants, in the order of the chosen column,\n"
        "# every second row marked for its stripe.\n"
        + block("mod1440_of_list", lists_script)
        + "\n# Officers: copies the chosen officer's values, traits, record, decorations and diary lines to the country,\n"
        "# where his file reads them. His own values are read in his scope (X33).\n"
        + block("mod1440_of_card", "clear_array = mod1440_of_c_ul\nclear_array = mod1440_of_c_subs\n" + iff(is_one("mod1440_of_has_sel"), (
            "mod1440_ev_grow = yes\n" + "".join("clear_array = mod1440_of_c_%s\n" % part for part in DEC_ARRAYS[1:] + ["dec_strip", "tr", "tr_e"])
            + tmp("of_ul", 0)
            + block("var:mod1440_of_sel", (
                copy_levels + copy_command + copy_traits
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
            + "clamp_variable = { var = mod1440_of_c_oth min = 0 }\n"
            + setv("mod1440_of_c_subs_more", "mod1440_of_c_subs_n") + "subtract_from_variable = { mod1440_of_c_subs_more = %d }\n" % OF_CHAIN_ROWS
            + setv("mod1440_of_c_dec_n", "mod1440_of_c_dec_key^num")
            # the newest decoration's name and date after the rack (E2 round 2)
            + iff("check_variable = { mod1440_of_c_dec_n > 0 }", (
                tmp("of_dl", "mod1440_of_c_dec_n") + "subtract_from_temp_variable = { of_dl = 1 }\n"
                + setv("mod1440_of_c_dec_lk", "mod1440_of_c_dec_key^of_dl") + setv("mod1440_of_c_dec_ld", "mod1440_of_c_dec_date^of_dl")
                + setv("mod1440_of_c_dec_tx", "mod1440_of_c_dec_n") + "multiply_variable = { mod1440_of_c_dec_tx = 46 }\n"
                + "add_to_variable = { mod1440_of_c_dec_tx = 24 }\n"))
            + medal_tokens(sets, "mod1440_of_c_dec_set", "mod1440_of_c_dec_strip", RACK)
            + pad([("mod1440_of_c_dec_key", BLANK), ("mod1440_of_c_dec_date", 0), ("mod1440_of_c_dec_set", -1), ("mod1440_of_c_dec_frame", 1)], RACK)
            + pad([("mod1440_of_c_dec_strip", "token:" + MEDAL_STRIP % sets[0])], RACK)
            + pad([("mod1440_of_c_tr", TRAIT_PAD), ("mod1440_of_c_tr_e", "token:" + TRAIT_NO_EFFECTS)], TRAIT_ICONS)
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
            # where the three lower cards stand: OF_DY lower under the chain card (mod1440_of_c_chain, set above)
            + place_y
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

    # E2 round 2: a general's battle also counts for the field marshal his army serves under (decision 4)
    hooks = {
        "on_unit_leader_created": dated("since", "commissioned"),
        "on_army_leader_promoted": dated("prom", "promoted"),
        "on_unit_leader_level_up": dated("lvl", "level", n="skill_level"),     # part n: the level reached
        "on_army_leader_won_combat": iff(human, "add_to_variable = { mod1440_of_won = 1 }\n" + ("mod1440_of_g_won = yes\n" if OF_CHAIN else "")),
        "on_army_leader_lost_combat": iff(human, "add_to_variable = { mod1440_of_lost = 1 }\n" + ("mod1440_of_g_lost = yes\n" if OF_CHAIN else "")),
        "on_navy_leader_won_combat": iff(human, "add_to_variable = { mod1440_of_won = 1 }\n"),
        "on_navy_leader_lost_combat": iff(human, "add_to_variable = { mod1440_of_lost = 1 }\n"),
    }
    return gui, script, script_effects, hooks


OF_SCENE = {}           # E2 round 2: the tests of each widget's sample state, filled by officers() for officer_scene()


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
            # E3: the heads of government of each month of the record of party support, the heads panel's copy and the
            # government's lines of the War Diary (people, kept by place; the last two are made again each day)
            + in_array("mod1440_gv_pp_h") + in_array("mod1440_gv_rp") + in_array("mod1440_gv_dl_a", "check_variable = { mod1440_gv_dl_sa^rm_i = 1 }")
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

# --- E3 round 2 --- The redesign of 2026-10-30 (scratch/phases/E3/layout.json, design.json; the user took every
# recommendation, decisions-final.json). The page in the steel look: on top who rules (the head of government with his
# traits and the laws) beside Party support, a poll tracker of the four parties over up to ten years with a results bar and
# a table sorted by support; under it who serves (the cabinet and the high command as banded tables, every person's effects
# in a tooltip), the realm, the government's own lines of the War Diary and the Intelligence card. The heads of government
# move into a panel over Party support, opened by a button in the Head of government card.
#
# The cards: (x, y, w, h, head band) in the window; each is a bitmap cut from the steel bar (GFX_1440p_GV_<name>,
# tools/stretch_background.py). The heads panel stands on the card of Party support.
GV_CARDS = {"hog": (14, 116, 540, 446, 38), "parties": (560, 116, 1106, 446, 38), "cabinet": (14, 568, 540, 280, 27),
            "realm": (14, 854, 540, 352, 27), "high": (560, 568, 540, 376, 27), "diary": (560, 950, 540, 256, 38),
            "intel": (1106, 568, 560, 638, 38)}
GV_STEEL = "GFX_1440p_GV_%s"
GV_ROW, GV_SEAT = 24, 48                            # a row of a table; a row with a person's portrait and two lines
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
LAW_SCALE = 0.35                                    # a law's picture (64x64) in a row of 24: 22x22
SMALL_UNKNOWN = "GFX_idea_unknown"                  # an advisor whose portrait the table does not know
GV_SMALL = 0.7                                      # an advisor's small portrait (65x67) in a row of 48: 46x47
GV_FACE = 0.22                                      # a large portrait (156x210) in a row of 48: 34x46
FACE_NONE = "GFX_1440p_SG_face_none_46x47"          # decision 2: the game's unknown leader outline on the dark inset
FACE_NONE_TT = "No picture: his portrait is a file of another mod, which only the game's own windows draw."
BEGAN = "before the record"
GV_FIGURES = [("elections", "Elections", ("election",), "Elections held since the record began."),
              ("changes", "Changes of rule", ("party", "government"), "Changes of the ruling party or of the government."),
              ("heads", "New heads", ("leader",), "Heads of government who took office."),
              ("appointed", "Appointments", ("appointed",), "Advisors, chiefs and members of the high command who took office."),
              ("party", "Changes of the ruling party", ("party",), "The ruling party changed.")]       # E3 round 2
CABINET_SLOTS = 5       # political advisors (the game gives three; Road to 56 gives Germany a fifth)
MEMBER_SLOTS = 3        # members of the high command (three in the game)
HEADS_SLOTS = 4         # heads of government in the padded copy mod1440_gv_rd (the save keeps its meaning)
HEADS_ROWS = 7          # rows of the heads panel
HEADS_KEEP = 100        # heads of government the record keeps
SLOT_PARTS = ["", "_since", "_old", "_p", "_r", "_b"]       # holder, since, held when the record began, portrait, role, large
SLOT_NEW = ["_e", "_fb"]                            # E3 round 2: the text key of his role's effects; 1: no picture (the fallback)
FLAG_TILE = (124, 96)   # a country of the faction or a subject: a plate of 122x90 in a slot of this size
# The heads of government: the record's arrays (newest first) and the new ones of round 2: the day he came and went
# (num_days, -1 not known), stability and war support in percent on his first and last day (-1 not recorded), the
# elections held in his term.
RUL = ["", "_from", "_old", "_to", "_end", "_p", "_g"]
RUL_NEW = ["_fd", "_td", "_s0", "_s1", "_w0", "_w1", "_e"]
RP = RUL + RUL_NEW + ["_days", "_fb"]               # the panel's padded copy mod1440_gv_rp*
# The record of party support: one value a month per party, aligned with National Figures' mod1440_h_date; the ruling
# group (1 to 4, 0 not known) and the head of government of each month.
PP_PARTS = ["_0", "_1", "_2", "_3", "_g", "_h"]
GV_EL_KEEP = 40         # elections kept (dates and days)
# The chart: the plot in the window (x, y, w, h), 2.8 px a percent; the ranges (months, slot, dot, caption)
GV_PLOT = (1010, 172, 600, 280)
GV_PX = 2.8
GV_RANGES = [(24, 25, 8, "2 years"), (60, 10, 6, "5 years"), (120, 5, 5, "10 years")]
GV_YEARS = 10
GV_SPANS = 6            # heads of government named on the band under the years
GV_SPAN_NAME = 130      # a span this wide or wider carries the name
GV_TICKS = 10           # election ticks
GV_LABEL_X = 1614       # the shares at the lines' ends
GV_LABEL_GAP = 18
GV_BAND_Y, GV_BAND_H = 482, 22
GV_CHART_VER = 3        # mod1440_gv_chart_v: the chart is drawn again once when this build is new
# The parties' colours (decision 5): the game's (common/ideologies) for the swatches and the results bar; lifted for
# the chart's dots and end swatches only, so that each reaches 3:1 on the plot (decision 5B)
PARTY_COLOURS = {"fascism": (150, 75, 0), "democratic": (0, 0, 255), "communism": (255, 0, 0), "neutrality": (124, 124, 124)}
DOT_COLOURS = {"fascism": (160, 85, 15), "democratic": (70, 90, 255), "communism": (255, 0, 0), "neutrality": (124, 124, 124)}
GV_TRAITS = 4           # traits of the head of government (the arrays of a save of the first build; nothing shows them)
# E3 fix round 1 (2026-10-31): no head of government's traits. has_country_leader_with_trait with a trait the loaded game
# does not define is refused at load ('Invalid trait', error.log) and keeps a null object; evaluated, it crashed the game
# (ACCESS_VIOLATION in FUN_140bffc50, the user's crash of 31 October, 1.19.4.1 with Road to 56). A mod cannot know the
# loaded game's traits, so no trigger of this page names a trait (tests/ScriptedGuis.Tests.ps1).
GV_NO_TRAITS = True
GV_DIARY = 8            # the government's newest lines of the War Diary
GV_KNOW = 3             # countries under What we know of
# The agency's upgrades (common/intelligence_agency_upgrades): 21 in five branches, eleven to a row (deviation: the
# design drew 17 in rows of nine; the game has 21)
GV_UPGRADES = [("upgrade_economy_civilian", "GFX_agency_economy_department"), ("upgrade_army_department", "GFX_agency_army_department"),
               ("upgrade_naval_department", "GFX_agency_naval_department"), ("upgrade_airforce_department", "GFX_agency_airforce_department"),
               ("upgrade_passive_defense", "GFX_agency_defense_department"), ("upgrade_anti_partisan", "GFX_agency_anti_partisan"),
               ("upgrade_blueprint_stealing", "GFX_agency_steal_blueprints"), ("upgrade_portable_radios", "GFX_agency_portable_radios"),
               ("upgrade_invisible_ink", "GFX_agency_invisible_ink"), ("upgrade_plastic_explosives", "GFX_agency_plastic_explosives"),
               ("upgrade_suicide_pills", "GFX_agency_suicide_pills"), ("upgrade_training_centers", "GFX_agency_localized_training_center"),
               ("upgrade_commando_training", "GFX_agency_commando_training"),
               ("upgrade_interrogation_techniques", "GFX_agency_interrogation_techniques"),
               ("upgrade_diplo_training", "GFX_agency_diplomatic_training"), ("upgrade_psycho_warfare", "GFX_agency_psychological_warfare"),
               ("upgrade_form_department", "GFX_agency_form_department"), ("upgrade_decryption_boost", "GFX_agency_decryption_boost_1"),
               ("upgrade_decryption_boost_2", "GFX_agency_decryption_boost_2"), ("upgrade_crypto_strength", "GFX_agency_cryptology_1"),
               ("upgrade_crypto_strength_2", "GFX_agency_cryptology_2")]
GV_UP_ROW, GV_UP_STEP, GV_UP_SIZE = 11, 49, 44
GV_UP_SCALE = 0.647                                  # a picture of 68x68 at 44x44
# An operative's mission: (the game's name of it, the frame of GFX_operative_mission_icons_small as the game's texts number
# them, the text key of its title). Fix round 1: the names are the game's own (common/script_enums.txt,
# script_enum_operative_mission_type, and the operative_leader_mission triggers of the game's files); quiet_intel_network,
# a text key's word, was refused at load ('Not a valid value', error.log of 2026-10-31): the game calls it quiet_network.
MISSIONS = [("build_intel_network", 1, "BUILD_INTEL_NETWORK"), ("quiet_network", 2, "QUIET_INTEL_NETWORK"),
            ("counter_intelligence", 3, "COUNTER_INTELLIGENCE"), ("root_out_resistance", 4, "ROOT_OUT_RESISTANCE"),
            ("boost_ideology", 5, "BOOST_IDEOLOGY"), ("control_trade", 6, "CONTROL_TRADE"), ("diplomatic_pressure", 7, "DIPLOMATIC_PRESSURE"),
            ("propaganda", 8, "PROPAGANDA")]
GV_OP_ROWS = 4
OP_ROW_W = 528
# --- end E3 round 2 ---


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


# --- E3 round 2 --- the effects of the country_leader traits (tools/make_game_tables.py: trait_effects_table.py's
# LEADER_EFFECTS, and leader_traits_mods_table.py for the playset's, decision 4), text keys mod1440_trl_<trait>
def leader_effects():
    """{language: {trait: lines}}: the game's leader traits, and the playset's the game lacks."""
    try:
        from trait_effects_table import LEADER_EFFECTS
    except ImportError:
        LEADER_EFFECTS = {}
    try:
        from leader_traits_mods_table import LEADER_EFFECTS as others
    except ImportError:
        others = {}
    out = {}
    for language in set(LEADER_EFFECTS) | set(others):
        table = dict(others.get(language) or {})
        table.update(LEADER_EFFECTS.get(language) or {})
        out[language] = table
    return out


def leader_described():
    return set((leader_effects().get("english") or {}).keys())


def leader_names():
    """E3 fix round 2: {language: {trait: its name on one line}} for the roles whose own name breaks its line ('Army Drill'
    over '(Expert)': a row's role is one line, and the break cut the rest off); the game's and the playset's."""
    try:
        from trait_effects_table import LEADER_NAMES
    except ImportError:
        LEADER_NAMES = {}
    try:
        from leader_traits_mods_table import LEADER_NAMES as others
    except ImportError:
        others = {}
    out = {}
    for language in set(LEADER_NAMES) | set(others):
        table = dict(others.get(language) or {})
        table.update(LEADER_NAMES.get(language) or {})
        out[language] = table
    return out


def role_key(trait, one_line):
    """The text key a role is written with: its one-line name (mod1440_trn_<trait>), or the trait's own."""
    return "mod1440_trn_" + trait if trait in one_line else trait


def effect_key(trait, described):
    """The text key of a leader trait's effects, or the one of a trait the tables do not describe."""
    plain_name = re.compile(r"^[A-Za-z0-9_]+$")
    return "mod1440_trl_" + trait if trait in described and plain_name.match(trait) else TRAIT_NO_EFFECTS


def head_traits():
    """The traits a head of government can have: the game's and the playset's (LEADER_TRAITS of both tables)."""
    try:
        from trait_effects_table import LEADER_TRAITS
    except ImportError:
        LEADER_TRAITS = []
    try:
        from leader_traits_mods_table import LEADER_TRAITS as others
    except ImportError:
        others = []
    plain_name = re.compile(r"^[A-Za-z0-9_]+$")
    return sorted(name for name in set(LEADER_TRAITS) | set(others) if plain_name.match(name))
# --- end E3 round 2 ---


def advisor_portraits():
    """The script that finds an advisor's small portrait and the role he holds in a slot: one effect per slot,
    mod1440_p_adv_<slot>, in the advisor's scope with PREV his country. It leaves p_tok (the sprite), p_role
    (the text key of the role's trait), p_big (1: the sprite is a large portrait) and, E3 round 2, p_eff (the text key
    of the role's effects, mod1440_trl_<trait>) and p_fb (1: no sprite the page can name, decision 2's fallback).
    Returns the script and the version of the table."""
    from portraits_table import TAGS
    rows = advisor_table()
    described = leader_described()
    one_line = set((leader_names().get("english") or {}).keys())
    version = table_version((rows, sorted(described), "E3", sorted(one_line)))
    out = ("\n# Advisors (tools/portraits_table.py, ADVISORS): the small portrait, the role and the role's effects of the advisor\n"
           "# in scope, PREV his country, for each kind of seat. %d roles.\n" % len(rows))
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
                               (tmp("p_tok", "token:" + sprite) + tmp("p_fb", 0) if sprite else "")
                               + (tmp("p_role", "token:" + role_key(trait, one_line)) + tmp("p_eff", "token:" + effect_key(trait, described)) if trait else "")
                               + (tmp("p_big", 1) if large else "") + tmp("p_found", 1), "if" if n == 0 else "else_if")
                           for n, (name, sprite, trait, large) in enumerate(by_file[source]))
            effects += block("mod1440_p_adv_%s_%s" % (slot, source), body)
            call = "mod1440_p_adv_%s_%s = yes\n" % (slot, source)
            if source in TAGS:
                own += iff("PREV = { original_tag = %s }" % source, call, "else_if" if own else "if")
            others += iff("check_variable = { p_found = 0 }", call)
        out += block("mod1440_p_adv_%s" % slot, tmp("p_tok", "token:" + SMALL_UNKNOWN) + tmp("p_role", BLANK) + tmp("p_big", 0) + tmp("p_found", 0)
                     + tmp("p_eff", "token:" + TRAIT_NO_EFFECTS) + tmp("p_fb", 1)
                     + own + iff("check_variable = { p_found = 0 }", others))
    return out + "\n" + effects, version


def gv_is_person(value):
    """A trigger: the number <value> (an element of the game's political_advisor or high_command array) holds a
    character, as a variable holds one (X67): a unit leader by his number (-21474.83648 and up) or a character by his
    place (5368.70912 and up). The game's political_advisor array can hold an element that scopes to a country (the
    "German Reich" seat of the user's capture, 2026-10-30): it is left out and never looked up, so no is_character asks a
    country (the error.log line of E7, 'Open (found 2026-10-30)')."""
    return "OR = { check_variable = { %s > 5368 } check_variable = { %s < -21000 } }" % (value, value)


def gv_person_test(value, flag):
    """Script for the country in scope (its number in the temporary gv_me): <flag> 1 when the element <value> is a character.
    E3 fix round 2: the number test alone let the 'German Reich' seat through (the user's save, 31 October: its number is in
    the range of a place, X67, and the place leads to nobody, so its scope stays the country). The element is entered and must
    leave the country's scope (the mod1440_chk_gv_phantom pattern); entering a place nobody stands on logs nothing (X67). Asked
    in the daily round only, never in a drawn trigger; the seat's copy keeps only who passes."""
    return (tmp(flag, 0) + iff(gv_is_person(value), (
        tmp("gv_pt", "gv_me") + block("var:" + value, tmp("gv_pt", "THIS"))
        + iff("NOT = { check_variable = { gv_pt = gv_me } }", tmp(flag, 1)))))


def government(portrait_version):
    adv_version = table_version((advisor_table(), sorted(leader_described()), "E3", sorted((leader_names().get("english") or {}).keys())))
    from laws_table import LAW_PICTURES
    pictures = dict(LAW_PICTURES)
    body, effects, properties = head("gv", 2, "Who rules and who serves. A date is the day the mod first saw the name in office.")
    vis = {}                # widget -> its conditions, ANDed in its _visible trigger
    lists, rows_gui = "", ""
    panel = is_one("mod1440_gv_heads") + "\n"
    chart_open = "NOT = { %s }\n" % is_one("mod1440_gv_heads")

    def when(names, cond):
        for name in ([names] if isinstance(names, str) else names):
            vis.setdefault(name, [])
            if cond not in vis[name]:
                vis[name].append(cond)

    def card(name, inner, key=None):
        x, y, w, h, band = GV_CARDS[name]
        return M.box("gv_" + name, x, y, w, h, M.icon("gv_%s_bg" % name, 0, 0, GV_STEEL % (key or name)) + inner)

    def rel(name, x, y):
        return x - GV_CARDS[name][0], y - GV_CARDS[name][1]

    def txt(name, x, y, w, words, font=None, fmt="left", h=22, tip=None, fixed=False, key=None):
        return M.text(name, x, y, w, B.key(key or name, words), font or M.FONT_LABEL, fmt, h,
                      tooltip=B.key((key or name) + "_tt", tip) if tip else None, fixed=fixed)

    def strip(name, x, y, w, words, right=None, right_w=260):
        out = M.icon(name, x, y, layout.head_sprite(w, 26)) + txt(name + "_t", x + 8, y + 2, 300, words)
        if right:
            out += txt(name + "_r", x + w - 8 - right_w, y + 2, right_w, right, fmt="right")
        return out

    def bands(name, x, y, w, row, rows):
        return "".join(M.icon("%s_%d" % (name, n), x, y + (n - 1) * row, STRIPE % (w, row)) for n in range(2, rows + 1, 2))

    def head_text(name, words, w=316, right=None, right_w=200, widget=None):
        """The caption in a card's head band, and a figure at its right end."""
        band = GV_CARDS[name][4]
        y = 4 if band == 27 else 8
        widget = widget or "gv_%s" % name
        out = txt(widget + "_title", 12, y, w, words, fixed=True)
        if right:
            out += txt(widget + "_right", GV_CARDS[name][2] - 12 - right_w, y, right_w, right, fmt="right")
        return out

    def since(name, x, y, w, date, old, fmt="right", word="since ", cond=""):
        """A date, or the words for one held when the record began."""
        out = txt(name, x, y, w, "%s[?%s.%s]" % (word, date, LONG), fmt=fmt)
        out += M.text(name + "_old", x, y, w, B.key("gv_began_" + word.strip(), BEGAN if word == "since " else word + BEGAN), M.FONT_LABEL, fmt, 22)
        when(name, cond + "check_variable = { %s = 0 }\n" % old)
        when(name + "_old", cond + "check_variable = { %s = 1 }\n" % old)
        return out

    def group_icons(name, x, y, scale, var, cond=""):
        out = ""
        for g, (word, group) in enumerate(IDEOLOGIES, start=1):
            out += scaled("%s_g%d" % (name, g), x, y, "GFX_ideology_%s_group" % group, scale)
            when("%s_g%d" % (name, g), cond + "check_variable = { %s = %d }\n" % (var, g))
        return out

    # ================================================================ Head of government
    c = "hog"
    inner = head_text(c, "Head of government")
    inner += M.button("gv_heads_btn", 392, 5, "GFX_sort_button_140x29", B.key("gv_heads_btn", "Heads of government"), tooltip=B.key(
        "gv_heads_btn_tt", "Every head of government since the record began, with his term, stability and war support, in the place of "
        "Party support. Click again, or Party support, to go back."))
    properties += block("gv_heads_btn", "frame = mod1440_gv_heads_f\n")
    effects += block("gv_heads_btn_click", flip("mod1440_gv_heads") + "mod1440_gv_panel = yes\n")
    inner += txt("gv_leader", 12, 44, 420, "[ROOT.GetLeader]", M.FONT_CARD, h=30, fixed=True)
    inner += flag("gv_flag", 450, 44)
    properties += flown("gv_flag", "ROOT")
    inner += txt("gv_party", 12, 76, 420, "§Y[ROOT.GetRulingParty]§!, [ROOT.GetRulingIdeology]", fixed=True)
    # the portrait at full size; a head the game can name no portrait for: the flag on the dark inset with his group's icon (E4)
    inner += portrait("gv_face", 8, 106)
    properties += shown("gv_face", "mod1440_gv_p")
    when("gv_face", "check_variable = { mod1440_gv_pfb = 0 }\n")
    inner += scaled("gv_face_fb", 8, 106, INSET % (156, 210), 1.0, B.key("gv_face_fb_tt", "No portrait the game can name"))
    inner += flag("gv_face_fb_flag", 8 + 37, 106 + 40)
    properties += flown("gv_face_fb_flag", "ROOT")
    when(["gv_face_fb", "gv_face_fb_flag"], "check_variable = { mod1440_gv_pfb = 1 }\n")
    for g, (word, group) in enumerate(IDEOLOGIES, start=1):
        inner += scaled("gv_face_fb_g%d" % g, 8 + 56, 106 + 104, "GFX_ideology_%s_group" % group, IDEOLOGY_LARGE)
        when("gv_face_fb_g%d" % g, "check_variable = { mod1440_gv_pfb = 1 }\nhas_government = %s\n" % group)
    # his party and dates as a banded table; E3 fix round 1: in the place of the traits (removed, see GV_NO_TRAITS) three
    # rows of today's figures, so that the table runs down beside the portrait
    bx, by = rel(c, 186, 222)
    inner += bands("gv_hog_band", bx, by, 360, GV_ROW, 8)
    rows = [("party_long", "Party", None), ("office", "In office", None), ("rec", "On record", None),
            ("election", "Last election", None), ("next", "Next election", None),
            ("support", "Party support", None), ("stab", "Stability", None), ("ws", "War support", None)]
    for n, (name, label, _x) in enumerate(rows):
        y = by + n * GV_ROW
        inner += txt("gv_%s_l" % name, bx + 8, y + 2, 110, label)
    inner += txt("gv_party_long", bx + 122, by + 2, 230, "[ROOT.GetRulingPartyLong]", fixed=True, tip="[ROOT.GetRulingPartyLong]")
    inner += since("gv_leader_since", bx + 122, by + GV_ROW + 2, 230, "mod1440_gv_leader_since", "mod1440_gv_leader_old", "left")
    inner += txt("gv_rec", bx + 122, by + 2 * GV_ROW + 2, 230, "[?mod1440_gv_leader_rec|0] days", tip="Days the record has kept him in office.")
    when("gv_rec", "check_variable = { mod1440_gv_leader_rec > -1 }\n")
    inner += txt("gv_election", bx + 122, by + 3 * GV_ROW + 2, 230, "[ROOT.GetLastElection]", fixed=True)
    inner += txt("gv_next", bx + 122, by + 4 * GV_ROW + 2, 230, "in [?days_until_next_election|0] days")
    inner += txt("gv_next_none", bx + 122, by + 4 * GV_ROW + 2, 230, "none")
    when("gv_next", "check_variable = { days_until_next_election > -1 }\n")
    when("gv_next_none", "check_variable = { days_until_next_election < 0 }\n")
    inner += txt("gv_support", bx + 122, by + 5 * GV_ROW + 2, 230, "[?party_popularity@ruling_party|%1]",
                 tip="The ruling party's support today, as the politics panel's pie shows it.")
    inner += txt("gv_stab", bx + 122, by + 6 * GV_ROW + 2, 230, "[?stability|%0]", tip="Stability today, as the top bar shows it.")
    inner += txt("gv_ws", bx + 122, by + 7 * GV_ROW + 2, 230, "[?has_war_support|%0]", tip="War support today, as the top bar shows it.")
    # the laws in force: the kind, the law's own picture, its name
    lx, ly = rel(c, 22, 456)
    inner += strip("gv_law_head", lx, ly, 524, "Laws in force")
    inner += bands("gv_law_band", lx, ly + 26, 524, GV_ROW, 3)
    for n, (label, ideas) in enumerate(LAWS):
        y = ly + 26 + n * GV_ROW
        inner += txt("gv_law_%d_l" % n, lx + 8, y + 2, 120, "§g%s§!" % label)
        inner += scaled("gv_law_%d_pic" % n, lx + 132, y + 1, LAW_UNKNOWN, LAW_SCALE)
        properties += block("gv_law_%d_pic" % n, 'image = "[?mod1440_gv_law_%d_gfx.GetTokenKey]"\n' % n)
        inner += txt("gv_law_%d" % n, lx + 162, y + 2, 354, "§Y[?mod1440_gv_law_%d.GetTokenLocalizedKey]§!" % n, fixed=True)
    body += card(c, inner)

    # ================================================================ Party support, and the heads panel on its card
    c = "parties"
    px0, py0 = rel(c, GV_PLOT[0], GV_PLOT[1])          # the plot in the card: 450, 56
    chart = ""                                          # the widgets of Party support (hidden while the panel is open)
    chart += head_text(c, "Party support", 600)
    for k, (span, step, dot, caption) in enumerate(GV_RANGES):
        name = "gv_range_%d" % span
        chart += M.button(name, 790 + k * 104, 5, "GFX_sort_button_100x29", B.key(name, caption), tooltip=B.key(name + "_tt", (
            "The last %s on the chart, a dot a month. Until you pick a range, the chart takes the shortest that holds every month "
            "written down." % caption)))
        effects += block(name + "_click", setv("mod1440_gv_range", span) + "mod1440_gv_chart = yes\n")
        properties += block(name, "frame = mod1440_gv_rf_%d\n" % span)
    # today's result: one bar split in the parties' colours, the largest share first (four layers of four colours, laid
    # over each other by the cumulative share; the layer of the last rank under the others)
    tx, ty = rel(c, 568, 162)
    chart += M.icon("gv_today_bg", tx, ty, INSET % (384, 24))
    for r in reversed(range(4)):
        for p, (word, group) in enumerate(IDEOLOGIES):
            name = "gv_today_%d_%d" % (r, p)
            chart += M.icon(name, tx + 8, ty + 4, "GFX_1440p_GV_share_%s" % group).replace(
                " }\n", ' pdx_tooltip = "%s" }\n' % B.key("gv_today_%d_tt" % p, "[ROOT.Get%sParty]: [?party_popularity@%s|%%1]" % (word, group)))
            properties += block(name, "frame = mod1440_gv_cum_%d\n" % p)
            when(name, "check_variable = { mod1440_gv_rank_%d = %d }\n" % (p, r))
    # the table of the four parties, sorted by support: each row's widgets move to their rank (y by property)
    hx, hy = rel(c, 568, 192)
    chart += M.icon("gv_pt_head", hx, hy, layout.head_sprite(384, 26))
    chart += txt("gv_pt_h0", hx + 52, hy + 2, 200, "Party")
    chart += txt("gv_pt_h1", hx + 264, hy + 2, 50, "Now", fmt="right", tip="The party's support today, as the politics panel shows it.")
    chart += txt("gv_pt_h2", hx + 320, hy + 2, 56, "Year", fmt="right", tip="The change in support over the last twelve months written down.")
    chart += bands("gv_pt_band", hx, hy + 26, 384, GV_SEAT, 4)
    base = hy + 26                                      # 102: the first row
    chart += M.icon("gv_pt_pick", hx, base, PICK % (384, GV_SEAT))
    properties += block("gv_pt_pick", "y = mod1440_gv_py_pick\n")
    for p, (word, group) in enumerate(IDEOLOGIES):
        parts = [("sw", 4, M.icon("gv_pt_%d_sw" % p, hx, base + 4, "GFX_1440p_GV_swatch_%s" % group)),
                 ("ic", 7, scaled("gv_pt_%d_ic" % p, hx + 12, base + 7, "GFX_ideology_%s_group" % group, 0.5)),
                 ("name", 2, txt("gv_pt_%d_name" % p, hx + 52, base + 2, 206, "[ROOT.Get%sParty]" % word, fixed=True)),
                 ("who", 24, txt("gv_pt_%d_who" % p, hx + 52, base + 24, 206, "§Y[ROOT.Get%sLeader]§!" % word, fixed=True)),
                 ("now", 12, txt("gv_pt_%d_now" % p, hx + 264, base + 12, 50, "[?party_popularity@%s|%%0]" % group, M.FONT_VALUE, "right")),
                 ("nows", 12, txt("gv_pt_%d_nows" % p, hx + 264, base + 12, 50, "[?party_popularity@%s|%%1]" % group, M.FONT_VALUE, "right")),
                 ("dy", 13, txt("gv_pt_%d_dy" % p, hx + 320, base + 13, 56, "[?mod1440_gv_dy_%d|=1]" % p, fmt="right")),
                 ("dyn", 13, M.text("gv_pt_%d_dyn" % p, hx + 320, base + 13, 56, B.key("gv_dash", DASH), M.FONT_LABEL, "right", 22))]
        for part, off, widget in parts:
            chart += widget
            properties += block("gv_pt_%d_%s" % (p, part), "y = mod1440_gv_py_%d_%d\n" % (p, off))
        when("gv_pt_%d_now" % p, "check_variable = { party_popularity@%s > 0.0099 }\n" % group)
        when("gv_pt_%d_nows" % p, "check_variable = { party_popularity@%s < 0.01 }\n" % group)
        when("gv_pt_%d_dy" % p, "check_variable = { mod1440_gv_hy_%d = 1 }\n" % p)
        when("gv_pt_%d_dyn" % p, "check_variable = { mod1440_gv_hy_%d = 0 }\n" % p)
    # since the record began: four figures
    fx, fy = rel(c, 568, 418)
    chart += strip("gv_since_head", fx, fy, 384, "Since the record began")
    chart += bands("gv_since_band", fx, fy + 26, 384, GV_ROW, 4)
    for n, (name, label, value, tip) in enumerate((
            ("el", "Elections held", "[?mod1440_gv_n_elections|0]", "Elections the War Diary wrote since the record began."),
            ("ch", "Changes of the ruling party", "[?mod1440_gv_n_party|0]", "Times the ruling party changed since the record began."),
            ("hi", "Ruling party at its highest", "[?mod1440_gv_hi|1]%, [?mod1440_gv_hi_d.GetDateStringNoHour]",
             "The ruling party's highest month of National Figures' record (series 30), and when."),
            ("mo", "Months recorded", "[?mod1440_gv_pp_n|0], [?mod1440_gv_pp_full|0] in full",
             "Months of the record of party support; in full: with all four parties (from this build on)."))):
        y = fy + 26 + n * GV_ROW
        chart += txt("gv_since_%s_l" % name, fx + 8, y + 2, 210, label, tip=tip)
        chart += txt("gv_since_%s" % name, fx + 220, y + 1, 156, value, M.FONT_VALUE, "right", key="gv_since_%s_v" % name)
    # the chart in its inset: quarter bands, the scale, the plot of dots (one grid per party and range, and the ruling
    # party's on top), the years, the band of who governed, the election ticks, the shares at the lines' ends, the legend
    ix, iy = rel(c, 960, 160)
    chart += M.icon("gv_chart_bg", ix, iy, INSET % (698, 394))
    chart += "".join(M.icon("gv_quarter_%d" % k, px0, py0 + k * 70, STRIPE % (GV_PLOT[2], 70)) for k in (1, 3))
    for k, words in enumerate(("100%", "75", "50", "25", "0")):
        chart += M.text("gv_scale_%d" % k, ix + 4, py0 + k * 70 - 9, 40, B.key("gv_scale_%d" % k, words), M.FONT_LABEL, "right", 22)
    chart += M.icon("gv_foot", px0, py0 + GV_PLOT[3], "GFX_1440p_SG_line_600x2")
    plot = ""
    for span, step, dot, caption in GV_RANGES:
        for p in [str(n) for n in range(4)] + ["r"]:
            grid = "gv_dots_%s_%d" % (p, span)
            plot += ('gridboxtype = {\n\tname = "%s"\n\tposition = { x = 0 y = 0 }\n\tsize = { width = %d height = %d }\n'
                     '\tslotsize = { width = %d height = %d }\n\tadd_horizontal = yes\n\tmax_slots_horizontal = %d\n\tformat = "UPPER_LEFT"\n}\n'
                     % (grid, GV_PLOT[2], GV_PLOT[3] + 10, step, GV_PLOT[3] + 10, span))
            row_name = "mod1440_records_gv_dot_%s_%d" % (p, span)
            lists += block(grid, 'array = mod1440_gv_pd_%s_%d\nentry_container = "%s"\n' % (p, span, row_name))
            at = (step - dot) // 2
            if p == "r":
                # the ruling party's dots, drawn last: one icon per colour, shown by the month's ruling group
                cells = ""
                for g, (word, group) in enumerate(IDEOLOGIES, start=1):
                    widget = "gv_dotr%d_%d" % (g, span)
                    cells += through(widget, at, 0, "GFX_1440p_GV_dot_%s_%d" % (group, dot))
                    properties += block(widget, "y = v\n")
                    when(widget, "check_variable = { v > -1 }\ncheck_variable = { mod1440_gv_pg_%d^i = %d }\n" % (span, g))
            else:
                group = IDEOLOGIES[int(p)][1]
                widget = "gv_dot%s_%d" % (p, span)
                cells = through(widget, at, 0, "GFX_1440p_GV_dot_%s_%d" % (group, dot))
                properties += block(widget, "y = v\n")
                when(widget, "check_variable = { v > -1 }\n")
            rows_gui += row(row_name, step, GV_PLOT[3] + 10, cells)
    chart += M.box("gv_plot", px0, py0, GV_PLOT[2], GV_PLOT[3] + 10, plot)
    # who governed: a cell a month in the colour of the ruling group
    _bx, band_y = rel(c, GV_PLOT[0], GV_BAND_Y)
    cells_box = ""
    for span, step, dot, caption in GV_RANGES:
        grid = "gv_band_%d" % span
        cells_box += ('gridboxtype = {\n\tname = "%s"\n\tposition = { x = 0 y = 0 }\n\tsize = { width = %d height = %d }\n'
                      '\tslotsize = { width = %d height = %d }\n\tadd_horizontal = yes\n\tmax_slots_horizontal = %d\n\tformat = "UPPER_LEFT"\n}\n'
                      % (grid, GV_PLOT[2], GV_BAND_H, step, GV_BAND_H, span))
        row_name = "mod1440_records_gv_band_%d" % span
        lists += block(grid, 'array = mod1440_gv_pb_%d\nentry_container = "%s"\n' % (span, row_name))
        cells = ""
        for g, (word, group) in enumerate(IDEOLOGIES, start=1):
            widget = "gv_cell%d_%d" % (g, span)
            cells += through(widget, 0, 0, "GFX_1440p_GV_band_%s_%d" % (group, step))
            when(widget, "check_variable = { v = %d }\n" % g)
        rows_gui += row(row_name, step, GV_BAND_H, cells)
    chart += M.box("gv_band", px0, band_y, GV_PLOT[2], GV_BAND_H, cells_box)
    # the years under the plot, moved by script (x by property, X4); a mark at the foot of each
    _yx, years_y = rel(c, 0, 456)
    for k in range(GV_YEARS):
        chart += M.icon("gv_ymark_%d" % k, px0, py0 + GV_PLOT[3], "GFX_1440p_GV_tick_2x6")
        chart += M.text("gv_year_%d" % k, px0, years_y, 40, B.key("gv_year_%d" % k, "[?mod1440_gv_yl_%d|0]" % k), M.FONT_LABEL, "centre", 22)
        properties += block("gv_ymark_%d" % k, "x = mod1440_gv_tx_%d\n" % k) + block("gv_year_%d" % k, "x = mod1440_gv_yx_%d\n" % k)
        when(["gv_ymark_%d" % k, "gv_year_%d" % k], "check_variable = { mod1440_gv_yl_%d > 0 }\n" % k)
    # his name on his span where it fits, his name and dates in its tooltip
    for s in range(GV_SPANS):
        name = "gv_span_%d" % s
        chart += txt(name, px0 + 6, band_y, GV_SPAN_NAME - 10, "[?mod1440_gv_bn_%d.GetName]" % s, fixed=True,
                     tip="§Y[?mod1440_gv_bn_%d.GetName]§!\\n[?mod1440_gv_bf_%d.%s] to [?mod1440_gv_bt_%d.%s]" % (s, s, LONG, s, LONG))
        properties += block(name, "x = mod1440_gv_bx_%d\n" % s)
        when(name, "check_variable = { mod1440_gv_bn_n > %d }\ncheck_variable = { mod1440_gv_bw_%d > %d }\n" % (s, s, GV_SPAN_NAME - 1))
    for t in range(GV_TICKS):
        name = "gv_tick_%d" % t
        chart += M.icon(name, px0, band_y - 4, "GFX_1440p_GV_tick_2x30").replace(
            " }\n", ' pdx_tooltip = "%s" }\n' % B.key("gv_tick_%d_tt" % t, "An election: [?mod1440_gv_td_%d.%s]" % (t, LONG)))
        properties += block(name, "x = mod1440_gv_tk_%d\n" % t)
        when(name, "check_variable = { mod1440_gv_tk_n > %d }\n" % t)
    # the share at each line's end, pushed apart where two meet (y by property)
    lx = GV_LABEL_X - GV_CARDS[c][0]
    for p, (word, group) in enumerate(IDEOLOGIES):
        chart += M.icon("gv_end_%d_sw" % p, lx, py0, "GFX_1440p_GV_dot_%s_6" % group)
        chart += txt("gv_end_%d" % p, lx + 9, py0, 38, "[?mod1440_gv_lv_%d|0]%%" % p)
        chart += M.text("gv_end_%d_lt" % p, lx + 9, py0, 38, B.key("gv_end_lt", "<1%"), M.FONT_LABEL, "left", 22)
        # at the line's end (x) and at its own height, pushed apart (y), as the design's figures draw them
        properties += block("gv_end_%d_sw" % p, "x = mod1440_gv_lx_s\ny = mod1440_gv_ly_%d_s\n" % p)
        properties += (block("gv_end_%d" % p, "x = mod1440_gv_lx_t\ny = mod1440_gv_ly_%d_t\n" % p)
                       + block("gv_end_%d_lt" % p, "x = mod1440_gv_lx_t\ny = mod1440_gv_ly_%d_t\n" % p))
        has = "check_variable = { mod1440_gv_lv_%d > -1 }\n" % p
        when("gv_end_%d_sw" % p, has)
        when("gv_end_%d" % p, has + "check_variable = { mod1440_gv_lv_%d > 0.99 }\n" % p)
        when("gv_end_%d_lt" % p, has + "check_variable = { mod1440_gv_lv_%d < 1 }\n" % p)
    gx, gy = rel(c, 968, 520)
    chart += txt("gv_legend", gx, gy, 682, "§gA dot: the first of a month.  Under the years: who governed;  | an election.§!", fixed=True)
    chart += txt("gv_legend_bf", gx, gy, 682, "§gBefore [?mod1440_gv_full_d.%s] the record kept the ruling party only (National Figures, series 30).§!" % LONG,
                 fixed=True, tip="The months before this build of the mod: the ruling party's support from National Figures' record, the "
                                 "other parties not recorded. All four are recorded from then on.")
    when("gv_legend", "check_variable = { mod1440_gv_bf = 0 }\n")
    when("gv_legend_bf", "check_variable = { mod1440_gv_bf = 1 }\n")
    chart += txt("gv_chart_none", px0 + 20, py0 + 100, 560, "Nothing is written down yet. The first dots come on the first of next month.")
    when("gv_chart_none", "check_variable = { mod1440_gv_pp_n < 1 }\n")
    GS_NAMES["chart"] = re.findall(r'(?:iconType|instantTextboxType|buttonType) = \{ name = "([^"]+)"', chart)
    for name in GS_NAMES["chart"]:
        when(name, chart_open)
    inner = chart

    # ---- the heads panel: the record's heads of government, seven to a page, newest first
    heads = head_text(c, "Heads of government since the record began", 600, widget="gv_hd")
    heads += M.button("gv_heads_back", 958, 5, "GFX_sort_button_140x29", B.key("gv_heads_back", "Party support"),
                      tooltip=B.key("gv_heads_back_tt", "Back to the chart of party support"))
    effects += block("gv_heads_back_click", setv("mod1440_gv_heads", 0) + "mod1440_gv_panel = yes\n")
    for name, words, delta, tip in (("gv_heads_newer", "Newer", -HEADS_ROWS, "The seven heads before these"),
                                    ("gv_heads_older", "Older", HEADS_ROWS, "The seven heads after these")):
        heads += M.button(name, 750 if delta < 0 else 854, 5, "GFX_sort_button_100x29", B.key(name, words), tooltip=B.key(name + "_tt", tip))
        effects += block(name + "_click", "add_to_variable = { mod1440_gv_hp = %d }\n" % delta
                         + "clamp_variable = { var = mod1440_gv_hp min = 0 max = %d }\n" % (HEADS_KEEP - HEADS_ROWS) + "mod1440_gv_heads_copy = yes\n")
    when("gv_heads_newer", "check_variable = { mod1440_gv_hp > 0 }\n")
    when("gv_heads_older", "check_variable = { mod1440_gv_rul^num > mod1440_gv_hp_end }\n")
    hx, hy = rel(c, 568, 160)
    heads += M.icon("gv_hd_head", hx, hy, layout.head_sprite(1090, 26))
    for name, x, w, fmt, words in (("who", 56, 240, "left", "Head of government"), ("office", 334, 300, "left", "In office"),
                                   ("stab", 640, 130, "centre", "Stability"), ("ws", 780, 130, "centre", "War support"),
                                   ("el", 920, 90, "centre", "Elections")):
        heads += txt("gv_hd_h_" + name, hx + x - 8, hy + 2, w, words, fmt=fmt)
    heads += bands("gv_hd_band", hx, hy + 26, 1090, GV_SEAT, HEADS_ROWS)
    heads += M.icon("gv_hd_pick", hx, hy + 26, PICK % (1090, GV_SEAT))
    when("gv_hd_pick", "check_variable = { mod1440_gv_hp = 0 }\ncheck_variable = { mod1440_gv_rul^num > 0 }\n")
    for k in range(HEADS_ROWS):
        y = hy + 26 + k * GV_SEAT
        more = "check_variable = { mod1440_gv_rp_n > %d }\n" % k
        p = "gv_hd_%d" % k
        heads += portrait(p + "_face", hx + 6, y + 1, GV_FACE)
        properties += shown(p + "_face", "mod1440_gv_rp_p^%d" % k)
        when(p + "_face", more + "check_variable = { mod1440_gv_rp_fb^%d = 0 }\n" % k)
        heads += scaled(p + "_fb", hx + 6, y + 1, INSET % (34, 46), 1.0, B.key("gv_hd_fb_tt", "No portrait the game can name"))
        when(p + "_fb", more + "check_variable = { mod1440_gv_rp_fb^%d = 1 }\n" % k)
        heads += group_icons(p + "_fbg", hx + 12, y + 12, IDEOLOGY_SMALL, "mod1440_gv_rp_g^%d" % k, more + "check_variable = { mod1440_gv_rp_fb^%d = 1 }\n" % k)
        heads += txt(p, hx + 48, y + 2, 230, "§Y[?mod1440_gv_rp^%d.GetName]§!" % k, fixed=True)
        when(p, more)
        for g, (word, group) in enumerate(IDEOLOGIES, start=1):
            widget = "%s_pt%d" % (p, g)
            heads += txt(widget, hx + 48, y + 24, 230, "[ROOT.Get%sParty], %s" % (word, word), fixed=True, key="gv_hd_pt%d_%d" % (k, g))
            when(widget, more + "check_variable = { mod1440_gv_rp_g^%d = %d }\n" % (k, g))
        heads += group_icons(p + "_gi", hx + 282, y + 7, 0.5, "mod1440_gv_rp_g^%d" % k, more)
        for name, words, condition in (
                ("a", "[?mod1440_gv_rp_from^%d.%s] – [?mod1440_gv_rp_to^%d.%s]" % (k, LONG, k, LONG), "check_variable = { mod1440_gv_rp_old^%d = 0 } check_variable = { mod1440_gv_rp_end^%d = 1 }"),
                ("b", "%s – [?mod1440_gv_rp_to^%d.%s]" % (BEGAN, k, LONG), "check_variable = { mod1440_gv_rp_old^%d = 1 } check_variable = { mod1440_gv_rp_end^%d = 1 }"),
                ("c", "since [?mod1440_gv_rp_from^%d.%s]" % (k, LONG), "check_variable = { mod1440_gv_rp_old^%d = 0 } check_variable = { mod1440_gv_rp_end^%d = 0 }"),
                ("d", "%s – today" % BEGAN, "check_variable = { mod1440_gv_rp_old^%d = 1 } check_variable = { mod1440_gv_rp_end^%d = 0 }")):
            widget = "%s_t%s" % (p, name)
            heads += txt(widget, hx + 326, y + 2, 300, words, fixed=True)
            when(widget, more + (condition % (k, k)) + "\n")
        heads += txt(p + "_days", hx + 326, y + 24, 300, "§g[?mod1440_gv_rp_days^%d|0] days§!" % k)
        heads += txt(p + "_rec", hx + 326, y + 24, 300, "§g[?mod1440_gv_rp_days^%d|0] days on record§!" % k)
        known = "check_variable = { mod1440_gv_rp_days^%d > -1 }\n" % k
        when(p + "_days", more + known + "check_variable = { mod1440_gv_rp_old^%d = 0 }\n" % k)
        when(p + "_rec", more + known + "check_variable = { mod1440_gv_rp_old^%d = 1 }\n" % k)
        for name, x, a, b in (("stab", 632, "s0", "s1"), ("ws", 772, "w0", "w1")):
            heads += txt("%s_%s" % (p, name), hx + x, y + 12, 130, "[?mod1440_gv_rp_%s^%d|0]%% to [?mod1440_gv_rp_%s^%d|0]%%" % (a, k, b, k), fmt="centre")
            heads += M.text("%s_%s_nr" % (p, name), hx + x, y + 12, 130, B.key("gv_hd_nr", "not recorded"), M.FONT_LABEL, "centre", 22)
            when("%s_%s" % (p, name), more + "check_variable = { mod1440_gv_rp_%s^%d > -1 }\n" % (a, k))
            when("%s_%s_nr" % (p, name), more + "check_variable = { mod1440_gv_rp_%s^%d < 0 }\n" % (a, k))
        heads += txt(p + "_el", hx + 912, y + 11, 90, "[?mod1440_gv_rp_e^%d|0]" % k, M.FONT_VALUE, "centre")
        when(p + "_el", more)
    heads += txt("gv_hd_note", 16, 414, 1074, "§gNewest first, 7 to a page; the record keeps 100. Stability and war support: on the first and "
                                              "on the last day in office (recorded from this build on).§!", fixed=True)
    GS_NAMES["panel"] = re.findall(r'(?:iconType|instantTextboxType|buttonType) = \{ name = "([^"]+)"', heads)
    for name in GS_NAMES["panel"]:
        when(name, panel)
    inner += heads
    body += card(c, inner)

    # ================================================================ Cabinet and High command
    def seat(prefix, k, x, y, holder, role, began, sprite, big, fb, eff, has, kind, game=None, office=None):
        """A row of a person: his portrait (the table's small one, a large one smaller, the game's face while he is a
        unit leader, or decision 2's fallback), name and role, his office in grey and since when; the effects of his role
        in the tooltip of his name and role. holder etc. are variables; has a trigger."""
        nonlocal lists, rows_gui
        p = "gv_%s_%d" % (prefix, k)
        out = ""
        table = ""
        if game:
            out += face_grid(p + "_gface_grid", x + 2, y + 1, GV_FACE)
            lists += face_list(p + "_gface_grid", game, "gv_gface")
            table = "check_variable = { %s^num < 1 }\n" % game
        out += scaled(p + "_face", x, y + 1, SMALL_UNKNOWN, GV_SMALL if not game else 0.52)
        out += scaled(p + "_big", x + (6 if not game else 2), y + 1, UNKNOWN, GV_FACE)
        properties_add = block(p + "_face", 'image = "[?%s.GetTokenKey]"\n' % sprite) + block(p + "_big", 'image = "[?%s.GetTokenKey]"\n' % sprite)
        out += scaled(p + "_none", x, y + 1, FACE_NONE, 1.0 if not game else 0.72, B.key("gv_face_none_tt", FACE_NONE_TT))
        when(p + "_face", has + "check_variable = { %s = 0 }\ncheck_variable = { %s = 0 }\n" % (big, fb) + table)
        when(p + "_big", has + "check_variable = { %s = 1 }\ncheck_variable = { %s = 0 }\n" % (big, fb) + table)
        when(p + "_none", has + "check_variable = { %s = 1 }\n" % fb + table)
        nx = x + (54 if not game else 44)
        tip = "§Y[?%s.GetName]§!\\n§g%s: [?%s.GetTokenLocalizedKey]§!\\n\\n[?%s.GetTokenLocalizedKey]" % (holder, kind, role, eff)
        tip_key = B.key(p + "_tt", tip)
        out += M.text(p + "_name", nx, y + 2, 248 if not game else 230, B.key(p + "_name", "§Y[?%s.GetName]§!" % holder), M.FONT_LABEL, "left", 22,
                      tooltip=tip_key, fixed=True)
        out += M.text(p + "_role", nx, y + 24, 248 if not game else 230, B.key(p + "_role", "[?%s.GetTokenLocalizedKey]" % role), M.FONT_LABEL,
                      "left", 22, tooltip=tip_key, fixed=True)
        when([p + "_name", p + "_role"], has)
        right = GV_CARDS["cabinet"][2] - 14 - 174
        if office:
            out += txt(p + "_office", 330, y + 2, 196, "§g%s§!" % office, fmt="right", key="gv_office_" + re.sub(r"\W+", "_", office.lower()))
            when(p + "_office", "always = yes\n")
            out += since(p + "_since", 330, y + 24, 196, began[0], began[1], cond=has)
        else:
            out += since(p + "_since", right, y + 13, 174, began[0], began[1], cond=has)
        return out, properties_add

    c = "cabinet"
    inner = head_text(c, "Cabinet", 316, "[?mod1440_gv_adv^num|0] in office")
    inner += bands("gv_cab_band", 8, 32, 524, GV_SEAT, CABINET_SLOTS)
    for k in range(CABINET_SLOTS):
        parts = dict((part, "mod1440_gv_adv_d%s^%d" % (part, k)) for part in SLOT_PARTS + SLOT_NEW)
        has = "check_variable = { mod1440_gv_adv^num > %d }\n" % k
        piece, prop = seat("adv", k, 10, 32 + k * GV_SEAT, parts[""], parts["_r"], (parts["_since"], parts["_old"]), parts["_p"], parts["_b"],
                           parts["_fb"], parts["_e"], has, "Political advisor")
        inner += piece
        properties += prop
    inner += txt("gv_adv_none", 16, 46, 500, "§gNo political advisor is hired.§!")
    when("gv_adv_none", "check_variable = { mod1440_gv_adv^num < 1 }\n")
    body += card(c, inner)

    c = "high"
    inner = head_text(c, "High command", 316, "[?mod1440_gv_hc_n|0] in office")
    inner += bands("gv_hc_band", 8, 32, 524, GV_SEAT, len(OFFICES) + MEMBER_SLOTS)
    for k, (variable, trigger, label) in enumerate(OFFICES):
        holder = "mod1440_gv_of_%d" % k
        has = is_one(holder + "_has") + "\n"
        y = 32 + k * GV_SEAT
        piece, prop = seat("of", k, 12, y, holder, holder + "_r", (holder + "_since", holder + "_old"), holder + "_p", holder + "_b",
                           holder + "_fb", holder + "_e", has, label, game="mod1440_gv_of_%d_ul" % k, office=label)
        inner += piece
        properties += prop
        # a vacant office: the politics panel's own empty slot and "vacant"
        inner += scaled("gv_of_%d_slot" % k, 14, y + 8, "GFX_idea_slot_" + variable, 0.5)
        inner += txt("gv_of_%d_vacant" % k, 56, y + 13, 200, "§gvacant§!", key="gv_vacant")
        when(["gv_of_%d_slot" % k, "gv_of_%d_vacant" % k], "NOT = { %s }\n" % has.strip())
    for m in range(MEMBER_SLOTS):
        k = len(OFFICES) + m
        parts = dict((part, "mod1440_gv_hc_d%s^%d" % (part, m)) for part in SLOT_PARTS + SLOT_NEW)
        has = "check_variable = { mod1440_gv_hc^num > %d }\n" % m
        piece, prop = seat("hc", m, 12, 32 + k * GV_SEAT, parts[""], parts["_r"], (parts["_since"], parts["_old"]), parts["_p"], parts["_b"],
                           parts["_fb"], parts["_e"], has, "High command", game="mod1440_gv_hc_%d_ul" % m, office="High command")
        inner += piece
        properties += prop
        when("gv_hc_%d_office" % m, has)
    body += card(c, inner)
    # E7: the row of the game's face of a chief or a member who is a unit leader (34x46)
    properties += block("gv_gface", GAME_FACE)
    rows_gui += game_face("gv_gface", GV_FACE)

    # ================================================================ In the War Diary: the government's newest lines
    c = "diary"
    inner = head_text(c, "In the War Diary", 300)
    inner += M.button("gv_diary_all", 392, 5, "GFX_sort_button_140x29", B.key("gv_diary_all", "All its lines"),
                      tooltip=B.key("gv_diary_all_tt", "The War Diary with the Government filter: every line about parties, elections, heads of "
                                                       "government and advisors"))
    effects += block("gv_diary_all_click", setv("mod1440_wd_filter", 3) + "clear_array = mod1440_wd_back\n" + setv("mod1440_wd_from", 0)
                     + setv("mod1440_rec_page", 0) + "mod1440_rec_show = yes\n")
    inner += bands("gv_dl_band", 8, 44, 524, GV_ROW, GV_DIARY)
    inner += txt("gv_dl_none", 16, 50, 500, "§gNo line of the government's yet.§!")
    when("gv_dl_none", "check_variable = { mod1440_gv_dl_n < 1 }\n")
    for k in range(GV_DIARY):
        y = 44 + k * GV_ROW
        more = "check_variable = { mod1440_gv_dl_n > %d }\n" % k
        p = "gv_dl_%d" % k
        inner += txt(p + "_d", 16, y + 2, 112, "[?mod1440_gv_dl_date^%d.GetDateStringNoHour]" % k)
        inner += M.text(p + "_i", 130, y + 1, 26, B.key("gv_dl_icon", "£pol_power"), M.FONT_LABEL, "left", 22)
        inner += txt(p, 156, y + 2, 148, "[?mod1440_gv_dl_kind^%d.GetTokenLocalizedKey]" % k, fixed=True)
        inner += txt(p + "_a", 306, y + 2, 218, "§Y[?mod1440_gv_dl_a^%d.GetName]§!" % k, fixed=True)
        inner += txt(p + "_b", 306, y + 2, 218, "§Y[?mod1440_gv_dl_b^%d.GetName]§!" % k, fixed=True)
        when([p + "_d", p + "_i", p], more)
        when(p + "_a", more + "check_variable = { mod1440_gv_dl_sa^%d = 1 }\n" % k)
        when(p + "_b", more + "NOT = { check_variable = { mod1440_gv_dl_sa^%d = 1 } }\ncheck_variable = { mod1440_gv_dl_sb^%d = 1 }\n" % (k, k))
    body += card(c, inner)

    # ================================================================ Faction and subjects
    def countries(name, array, x, y):
        nonlocal lists, rows_gui
        lists += block("gv_%s_grid" % name, 'array = %s\nchange_scope = yes\nentry_container = "mod1440_records_%s_row"\n' % (array, name))
        tile_w, tile_h = FLAG_TILE
        entry = M.icon("gv_%s_row_bg" % name, 0, 0, INSET % (tile_w - 2, tile_h - 6))
        # E3 fix round 2: the flag and the name inside the inset's border of 8 (the user's capture: the flag on the frame's top
        # edge and a long name over its sides); a name is one line, cut in its fixed box (W28)
        entry += flag("gv_%s_row_flag" % name, (tile_w - 2 - 82) // 2, 9)
        entry += M.text("gv_%s_row_name" % name, 8, 64, tile_w - 18, B.key("gv_country_tile", "[THIS.GetName]"), M.FONT_SMALL, "centre", 20, fixed=True)
        rows_gui += row("mod1440_records_%s_row" % name, tile_w, tile_h, entry)
        grid = ('gridboxtype = {\n\tname = "gv_%s_grid"\n\tposition = { x = 0 y = 0 }\n\tsize = { width = %d height = 100%%%% }\n'
                '\tslotsize = { width = %d height = %d }\n\tmax_slots_horizontal = 4\n\tadd_horizontal = yes\n\tformat = "UPPER_LEFT"\n}\n'
                % (name, 4 * tile_w, tile_w, tile_h))
        return ('containerWindowType = {\n\tname = "gv_%s_list"\n\tposition = { x = %d y = %d }\n\tsize = { width = %d height = %d }\n'
                '\tverticalScrollbar = "right_vertical_slider"\n\tscroll_wheel_factor = %d\n\tsmooth_scrolling = yes\n%s%s}\n'
                % (name, x, y, 4 * tile_w + 26, tile_h, tile_h, LIST_BG, M.indent(grid)))

    properties += "".join(block("gv_%s_row_flag" % name, 'image = "[THIS.GetFlag]"\n') for name in ("fac", "sub"))
    c = "realm"
    inner = head_text(c, "Faction and subjects", 276)
    # E3 fix round 2: one member, one subject in the singular
    for m, words_m, cond_m in (("m1", "1 member", "check_variable = { mod1440_gv_fac^num = 1 }"),
                               ("mn", "[?mod1440_gv_fac^num|0] members", "NOT = { check_variable = { mod1440_gv_fac^num = 1 } }")):
        for k, words_s, cond_s in (("s1", "1 subject", "check_variable = { mod1440_ev_subjects^num = 1 }"),
                                   ("sn", "[?mod1440_ev_subjects^num|0] subjects", "NOT = { check_variable = { mod1440_ev_subjects^num = 1 } }")):
            widget = "gv_realm_right_%s%s" % (m, k)
            inner += txt(widget, 540 - 12 - 240, 4, 240, "%s, %s" % (words_m, words_s), fmt="right")
            when(widget, "%s\n%s\n" % (cond_m, cond_s))
    inner += txt("gv_faction", 12, 32, 516, "[ROOT.GetFactionName]", M.FONT_CARD, h=30, fixed=True)
    inner += txt("gv_faction_none", 12, 38, 516, "In no faction.")
    inner += txt("gv_faction_lead", 12, 64, 516, "led by §Y[?faction_leader.GetName]§!", fixed=True)
    when(["gv_faction", "gv_faction_lead"], "is_in_faction = yes\n")
    when("gv_faction_none", "is_in_faction = no\n")
    inner += countries("fac", "mod1440_gv_fac", 8, 94)
    inner += strip("gv_sub_head", 8, 196, 524, "Subjects", "overlord: §Y[?overlord.GetName]§!")
    inner += txt("gv_sub_head_r0", 532 - 8 - 260, 198, 260, "overlord: none", fmt="right")
    when("gv_sub_head_r", "is_subject = yes\n")
    when("gv_sub_head_r0", "is_subject = no\n")
    inner += txt("gv_sub_none", 16, 236, 400, "§gNo subjects.§!")
    when("gv_sub_none", "check_variable = { mod1440_ev_subjects^num < 1 }\n")
    inner += countries("sub", "mod1440_ev_subjects", 8, 228)
    body += card(c, inner)

    # ================================================================ Intelligence
    c = "intel"
    agency = "has_intelligence_agency = yes\n"
    inner = txt("gv_ag_name", 12, 8, 316, "Intelligence agency: §Y[ROOT.GetAgency]§!", fixed=True)
    inner += txt("gv_ag_none", 12, 8, 316, "No intelligence agency yet")
    when("gv_ag_name", agency)
    when("gv_ag_none", "has_intelligence_agency = no\n")
    inner += since("gv_ag_since", 328, 8, 220, "mod1440_gv_ag_since", "mod1440_gv_ag_old", word="founded ", cond=agency)
    inner += strip("gv_up_head", 8, 44, 544, "Upgrades", "[?mod1440_gv_ag_done|0] of %d at their highest level" % len(GV_UPGRADES), 300)
    for n, (upgrade, sprite) in enumerate(GV_UPGRADES):
        x, y = 14 + (n % GV_UP_ROW) * GV_UP_STEP, 76 + (n // GV_UP_ROW) * 48
        inner += scaled("gv_up_%d" % n, x, y, sprite, GV_UP_SCALE, upgrade)
        inner += scaled("gv_up_%d_dim" % n, x, y, "GFX_1440p_SG_dim_44", 1.0, upgrade)
        when("gv_up_%d_dim" % n, "NOT = { has_done_agency_upgrade = %s }\n" % upgrade)
    # operatives: a list over the game's array, the face drawn by the game (an operative is a unit leader, SGUI-053)
    inner += M.icon("gv_op_head", 8, 174, layout.head_sprite(544, 26))
    inner += txt("gv_op_h0", 54, 176, 200, "Operatives  [?num_of_operatives|0] of [?num_operative_slots|0]")
    inner += txt("gv_op_h1", 222, 176, 140, "Mission")
    inner += txt("gv_op_h2", 372, 176, 170, "Where")
    inner += bands("gv_op_band", 8, 200, 544, GV_SEAT, GV_OP_ROWS)
    inner += war_listing("gv_op_list", "gv_op_grid", 8, 200, GV_OP_ROWS * GV_SEAT, OP_ROW_W, 544, GV_SEAT)
    inner += txt("gv_op_none", 16, 214, 500, "§gNo operative is recruited.§!")
    when("gv_op_none", "check_variable = { num_of_operatives < 1 }\n")
    lists += block("gv_op_grid", 'array = operatives\nchange_scope = yes\nentry_container = "mod1440_records_gv_op_row"\n')
    entry = scaled("gv_op_face", 4, 1, UNKNOWN, GV_FACE)
    properties += block("gv_op_face", GAME_FACE)
    # E3 fix round 2: no code name. GetCodeName is a property of the UnitLeader object (loc_objects_documentation.md), and a
    # row's scope is the Character, which has none: the user's rows read empty quotes. The name stands in the row's middle.
    entry += M.text("gv_op_name", 46, 13, 160, B.key("gv_op_name", "§Y[THIS.GetName]§!"), M.FONT_LABEL, "left", 22, fixed=True)
    for mission, frame_n, title in MISSIONS:
        entry += icon_frame("gv_op_m_%s" % mission, 214, 14, "GFX_operative_mission_icons_small", frame_n)
        entry += M.text("gv_op_t_%s" % mission, 238, 13, 118, "OPERATIVE_MISSION_%s_TITLE" % title, M.FONT_LABEL, "left", 22, fixed=True)
        when(["gv_op_m_%s" % mission, "gv_op_t_%s" % mission], "operative_leader_mission = %s\n" % mission)
    entry += M.text("gv_op_t_none", 238, 13, 118, "OPERATIVE_MISSION_NO_MISSION_TITLE", M.FONT_LABEL, "left", 22, fixed=True)
    when("gv_op_t_none", "operative_leader_mission = no_mission\n")
    entry += M.icon("gv_op_flag", 364, 11, FLAG_SMALL)
    properties += flown("gv_op_flag", "?operation_country")
    entry += M.text("gv_op_where", 410, 2, 118, B.key("gv_op_where", "§Y[?operation_state.GetName]§!"), M.FONT_LABEL, "left", 22, fixed=True)
    entry += M.text("gv_op_net", 410, 24, 118, B.key("gv_op_net", "§gnetwork [?mod1440_gv_net|0]%§!"), M.FONT_LABEL, "left", 22,
                    tooltip=B.key("gv_op_net_tt", "Your intelligence network's national coverage of this country, as the daily round read it."))
    entry += M.text("gv_op_home", 410, 24, 118, B.key("gv_op_home", "§gat home§!"), M.FONT_LABEL, "left", 22)
    entry += M.text("gv_op_idle", 410, 13, 118, B.key("gv_op_idle", "§gnot assigned§!"), M.FONT_LABEL, "left", 22)
    # E3 fix round 2: an operative on a mission in a country (counter-intelligence at home) has no state: the state's name
    # fell back to the row's scope, his own name. Then the country's name stands there.
    entry += M.text("gv_op_country", 410, 2, 118, B.key("gv_op_country", "§Y[?operation_country.GetName]§!"), M.FONT_LABEL, "left", 22, fixed=True)
    assigned = "check_variable = { operation_country > 0 }\n"
    when("gv_op_flag", assigned)
    when("gv_op_where", assigned + "check_variable = { operation_state > 0 }\n")
    when("gv_op_country", assigned + "NOT = { check_variable = { operation_state > 0 } }\n")
    when("gv_op_net", assigned + "check_variable = { mod1440_gv_home = 0 }\n")
    when("gv_op_home", assigned + "check_variable = { mod1440_gv_home = 1 }\n")
    when("gv_op_idle", "NOT = { %s }\n" % assigned.strip())
    rows_gui += row("mod1440_records_gv_op_row", OP_ROW_W, GV_SEAT, entry)
    # cryptology
    inner += strip("gv_cr_head", 8, 400, 544, "Cryptology", "department active")
    inner += txt("gv_cr_head_r0", 552 - 8 - 260, 402, 260, "no department", fmt="right")
    when("gv_cr_head_r", "is_cryptology_department_active = yes\n")
    when("gv_cr_head_r0", "is_cryptology_department_active = no\n")
    inner += bands("gv_cr_band", 8, 426, 544, GV_ROW, 4)
    for n, (name, label, value, tip) in enumerate((
            ("enc", "Our cipher strength", "[?encryption_strength|0]", "Your cipher strength in the game's own units, as the cryptology view shows it: 12000, and 4250 for each level of cryptology (NDefines CRYPTO_BASE_CRYPTO_LEVEL, CRYPTO_CRYPTO_LEVEL_PER_CRYPTO_UPGRADE)."),
            ("def", "Cryptology defence level", "[?cryptology_defense_level|0]", "Your cryptology defence level, as the agency view shows it."),
            ("dec", "Decrypting", "§Y[?mod1440_gv_dc.GetName]§!  [?mod1440_gv_dc_p|0]%", "The cipher you are breaking and how far (the cryptology tab's bar)."),
            ("brk", "Ciphers broken since the record began", "[?mod1440_ct^%d|0]" % NUMBER["cipher"], "The 'Broke the cipher of' lines of the War Diary."))):
        y = 426 + n * GV_ROW
        inner += txt("gv_cr_%s_l" % name, 16, y + 2, 280, label, tip=tip)
        inner += txt("gv_cr_%s" % name, 300, y + 2, 244, value, fmt="right", key="gv_cr_%s_v" % name)
    inner += txt("gv_cr_dec_none", 300, 426 + 2 * GV_ROW + 2, 244, "§gnothing§!", fmt="right")
    when("gv_cr_dec", "check_variable = { mod1440_gv_dc_has = 1 }\n")
    when("gv_cr_dec_none", "check_variable = { mod1440_gv_dc_has = 0 }\n")
    # what we know of: the enemies at war first, then the majors
    inner += M.icon("gv_kn_head", 8, 528, layout.head_sprite(544, 26))
    inner += txt("gv_kn_h", 16, 530, 200, "What we know of", tip="Your intel on each country, as the intelligence ledger shows it: enemies at war first, then the major powers.")
    for n, words in enumerate(("Civilian", "Army", "Navy", "Air")):
        inner += txt("gv_kn_h%d" % n, 268 + n * 68, 530, 68, words, fmt="centre")
    inner += bands("gv_kn_band", 8, 554, 544, GV_ROW, GV_KNOW)
    for k in range(GV_KNOW):
        y = 554 + k * GV_ROW
        more = "check_variable = { mod1440_gv_kn_n > %d }\n" % k
        inner += txt("gv_kn_%d" % k, 16, y + 2, 240, "§Y[?mod1440_gv_kn^%d.GetName]§!" % k, fixed=True)
        names = ["gv_kn_%d" % k]
        for n, part in enumerate(("c", "a", "n", "i")):
            inner += txt("gv_kn_%d_%s" % (k, part), 268 + n * 68, y + 1, 68, "[?mod1440_gv_kn_%s^%d|0]%%" % (part, k), M.FONT_VALUE, "centre")
            names.append("gv_kn_%d_%s" % (k, part))
        when(names, more)
    body += card(c, inner)

    triggers = "".join(block(name + "_visible", "".join(conds)) for name, conds in vis.items())
    gui, script = page_gui("gv", 2, body, lists=lists, effects=effects, triggers=triggers, properties=properties)
    gui += rows_gui
    return gui, script, government_script(adv_version, portrait_version, pictures), government_hooks()


def gv_slot(var, count, body, start=0):
    """Script: body(n) for the n that the temporary variable <var> holds, n from start to count - 1 (a chain)."""
    return "".join(iff("check_variable = { %s = %d }" % (var, n), body(n), "if" if n == start else "else_if") for n in range(start, count))


def government_script(adv_version, portrait_version, pictures):
    """E3 round 2: the daily round of the Government page, the monthly record of party support and its chart, the panel
    of the heads of government, the government's lines of the War Diary and the agency's figures."""
    begun = is_one("mod1440_gv_begun")
    unknown_small = "token:" + SMALL_UNKNOWN
    no_effects = "token:" + TRAIT_NO_EFFECTS
    all_parts = SLOT_PARTS + SLOT_NEW

    def office_array(game, copy, slot):
        """The daily comparison of one array of seats with its copy. A new holder gets today's date, a line in the
        War Diary, and his portrait, role and its effects looked up once; a holder kept keeps them. An element that is
        no character is left out (gv_is_person)."""
        news = ["mod1440_gv_new" + part for part in all_parts]
        lookup = (block("var:gv_c", "mod1440_p_adv_%s = yes\n" % slot) + tmp("gv_p", "p_tok") + tmp("gv_r", "p_role") + tmp("gv_b", "p_big")
                  + tmp("gv_e", "p_eff") + tmp("gv_fb", "p_fb"))
        return (
            "".join("clear_array = %s\n" % n for n in news)
            + tmp("gv_me", "THIS")
            + block("for_each_loop", "array = %s\nvalue = gv_c\n" % game + gv_person_test("gv_c", "gv_isp") + iff("check_variable = { gv_isp = 1 }", (
                tmp("gv_since", "global.date") + tmp("gv_old", 1) + iff(begun, tmp("gv_old", 0)) + tmp("gv_found", 0)
                + tmp("gv_e", no_effects) + tmp("gv_fb", 0)
                + block("for_each_loop", "array = %s\nvalue = gv_o\nindex = gv_j\n" % copy + iff(
                    "check_variable = { gv_o = gv_c }", tmp("gv_found", 1) + tmp("gv_since", "%s_since^gv_j" % copy) + tmp("gv_old", "%s_old^gv_j" % copy)
                    + tmp("gv_p", "%s_p^gv_j" % copy) + tmp("gv_r", "%s_r^gv_j" % copy) + tmp("gv_b", "%s_b^gv_j" % copy)
                    + tmp("gv_e", "%s_e^gv_j" % copy) + tmp("gv_fb", "%s_fb^gv_j" % copy)))
                + iff("check_variable = { gv_found = 0 } " + begun, line("appointed", a="gv_c"))
                # a copy of a game saved before the portraits (or, E3 round 2, the effects) were kept: looked up now
                + iff("OR = { check_variable = { gv_found = 0 } check_variable = { gv_stale = 1 } }", lookup)
                + "".join("add_to_array = { %s = %s }\n" % (n, v) for n, v in zip(news, ("gv_c", "gv_since", "gv_old", "gv_p", "gv_r", "gv_b", "gv_e", "gv_fb"))))))
            + block("for_each_loop", "array = %s\nvalue = gv_o\n" % copy + iff(
                "NOT = { is_in_array = { array = %s value = gv_o } } %s" % (game, begun), line("dismissed", a="gv_o")))
            + "".join("clear_array = %s%s\n" % (copy, part) + block(
                "for_each_loop", "array = mod1440_gv_new%s\nvalue = gv_o\nadd_to_array = { %s%s = gv_o }\n" % (part, copy, part))
                for part in all_parts))

    def shown_seats(prefix, count):
        """The copy the seats of the page read: the first <count> holders, padded so that a hidden seat reads
        an element that is there."""
        source, target = "mod1440_gv_" + prefix, "mod1440_gv_%s_d" % prefix
        pads = {"": 0, "_since": 0, "_old": 0, "_p": unknown_small, "_r": BLANK, "_b": 0, "_e": no_effects, "_fb": 0}
        return ("".join("clear_array = %s%s\n" % (target, part) for part in all_parts)
                + block("for_each_loop", "array = %s\nvalue = gv_v\nindex = gv_i\n" % source + iff(
                    "check_variable = { gv_i < %d }" % count,
                    "".join("add_to_array = { %s%s = %s%s^gv_i }\n" % (target, part, source, part) for part in all_parts)))
                + pad([(target + part, pads[part]) for part in all_parts], count))

    offices = ""
    for k, (variable, trigger, label) in enumerate(OFFICES):
        holder = "mod1440_gv_of_%d" % k
        lookup = (tmp("gv_c", holder) + block("var:gv_c", "mod1440_p_adv_%s = yes\n" % variable)
                  + setv(holder + "_p", "p_tok") + setv(holder + "_r", "p_role") + setv(holder + "_b", "p_big")
                  + setv(holder + "_e", "p_eff") + setv(holder + "_fb", "p_fb"))
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
    # the leader's portrait: looked up when another leader rules, and when the game's list of characters has changed;
    # E3 round 2: whether the game can name one (else the flag on the dark inset, E4's fallback)
    face = (leader_portrait("THIS", "mod1440_gv_p", portrait_version) + tmp("gv_unk", "token:" + UNKNOWN) + setv("mod1440_gv_pfb", 0)
            + iff("check_variable = { mod1440_gv_p = gv_unk }", setv("mod1440_gv_pfb", 1)))
    rulers_again = block("for_each_loop", "array = mod1440_gv_rul\nvalue = gv_v\nindex = gv_i\n" + iff(
        "check_variable = { gv_i < mod1440_gv_rul_p^num } NOT = { check_variable = { gv_v = 0 } }",
        tmp("p_tok", "token:" + UNKNOWN) + block("var:gv_v", "mod1440_p_leader = yes\n") + setv("mod1440_gv_rul_p^gv_i", "p_tok")))
    group = tmp("gv_g", 0) + "".join(iff("has_government = %s" % g, tmp("gv_g", n)) for n, (ideology, g) in enumerate(IDEOLOGIES, start=1))
    stab = tmp("gv_st", "stability") + "multiply_temp_variable = { gv_st = 100 }\n" + tmp("gv_ws", "has_war_support") + "multiply_temp_variable = { gv_ws = 100 }\n"
    # the heads of government since the record began: a row when another one rules, newest first (E3 round 2: the days he
    # came and went, stability and war support on his first and last day, the elections in his term)
    new_head = (
        iff("check_variable = { mod1440_gv_rul^num > 0 }", setv("mod1440_gv_rul_to^0", "global.date") + setv("mod1440_gv_rul_end^0", 1)
            + setv("mod1440_gv_rul_td^0", "global.num_days"))
        + group + tmp("gv_cl", "country_leader") + stab
        + "".join("add_to_array = { array = mod1440_gv_rul%s value = %s index = 0 }\n" % (part, value) for part, value in zip(
            RUL + RUL_NEW, ("gv_cl", "mod1440_gv_leader_since", "mod1440_gv_leader_old", 0, 0, "mod1440_gv_p", "gv_g",
                            "global.num_days", -1, "gv_st", "gv_st", "gv_ws", "gv_ws", 0)))
        + iff("check_variable = { mod1440_gv_rul^num > %d }" % HEADS_KEEP, tmp("gv_last", "mod1440_gv_rul^num") + "subtract_from_temp_variable = { gv_last = 1 }\n"
              + "".join("remove_from_array = { array = mod1440_gv_rul%s index = gv_last }\n" % part for part in RUL + RUL_NEW)))
    heads_shown = ("".join("clear_array = mod1440_gv_rd%s\n" % part for part in RUL)
                   + block("for_each_loop", "array = mod1440_gv_rul\nvalue = gv_v\nindex = gv_i\n" + iff(
                       "check_variable = { gv_i < %d }" % HEADS_SLOTS,
                       "".join("add_to_array = { mod1440_gv_rd%s = mod1440_gv_rul%s^gv_i }\n" % (part, part) for part in RUL)))
                   + pad([("mod1440_gv_rd", 0), ("mod1440_gv_rd_from", 0), ("mod1440_gv_rd_old", 0), ("mod1440_gv_rd_to", 0),
                          ("mod1440_gv_rd_end", 0), ("mod1440_gv_rd_p", "token:" + UNKNOWN), ("mod1440_gv_rd_g", 0)], HEADS_SLOTS))
    sums = ""
    for name, label, kinds, tip in GV_FIGURES:
        sums += count(*kinds) + setv("mod1440_gv_n_" + name, "ct_sum")

    # ---- the migration of a save of the build before round 2 (once): the new parts of the heads, the elections from the
    # log's election lines, the elections of each head's term (dates compared as numbers, as the Wars page does)
    rul_pads = {"_fd": -1, "_td": -1, "_s0": -1, "_s1": -1, "_w0": -1, "_w1": -1, "_e": 0}
    migrate = ""
    for part in RUL_NEW:
        value = rul_pads[part]
        body = tmp("gv_mv", value)
        if part == "_fd":
            body += iff("check_variable = { mod1440_gv_rul_old^gv_mi = 1 }", tmp("gv_mv", "mod1440_ev_since_day"))
        migrate += block("for_loop_effect", "start = 0\nend = mod1440_gv_rul^num\nvalue = gv_mi\n" + iff(
            "check_variable = { mod1440_gv_rul%s^num < mod1440_gv_rul^num }" % part, tmp("gv_mi", "mod1440_gv_rul%s^num" % part) + body
            + "add_to_array = { mod1440_gv_rul%s = gv_mv }\n" % part))
    migrate += (tmp("gv_tk", "token:mod1440_ev_election") + "clear_array = mod1440_gv_el\nclear_array = mod1440_gv_el_d\n"
                + block("for_each_loop", "array = mod1440_ev_kind\nvalue = gv_mk\nindex = gv_mi\n" + iff(
                    "check_variable = { gv_mk = gv_tk }", "add_to_array = { mod1440_gv_el = mod1440_ev_date^gv_mi }\nadd_to_array = { mod1440_gv_el_d = mod1440_ev_day^gv_mi }\n"))
                + block("while_loop_effect", "limit = { check_variable = { mod1440_gv_el^num > %d } }\n" % GV_EL_KEEP
                        + "remove_from_array = { array = mod1440_gv_el index = 0 }\nremove_from_array = { array = mod1440_gv_el_d index = 0 }\n")
                + block("for_each_loop", "array = mod1440_gv_el\nvalue = gv_md\n" + tmp("gv_mb", 0) + block(
                    "for_each_loop", "array = mod1440_gv_rul\nindex = gv_mk\nvalue = gv_mv\nbreak = gv_mb\n" + iff(
                        "OR = { check_variable = { mod1440_gv_rul_old^gv_mk = 1 } NOT = { check_variable = { mod1440_gv_rul_from^gv_mk > gv_md } } }",
                        "add_to_variable = { mod1440_gv_rul_e^gv_mk = 1 }\n" + tmp("gv_mb", 1)))))
    migration = iff("NOT = { check_variable = { mod1440_gv_v3 = 1 } }", setv("mod1440_gv_v3", 1) + migrate
                    + 'log = "MOD1440 government: the heads of government of [This.GetTag] got their days, stability and war support (not recorded), '
                      '[?mod1440_gv_el^num] elections from the log"\n')

    # ---- the heads panel's copy: seven rows from the page offset mod1440_gv_hp, with the days in office and the fallback
    pads = {"": 0, "_from": 0, "_old": 0, "_to": 0, "_end": 0, "_p": "token:" + UNKNOWN, "_g": 0, "_fd": -1, "_td": -1, "_s0": -1, "_s1": -1,
            "_w0": -1, "_w1": -1, "_e": 0, "_days": -1, "_fb": 0}
    heads_copy = (
        "".join("clear_array = mod1440_gv_rp%s\n" % part for part in RP)
        + tmp("gv_unk", "token:" + UNKNOWN) + tmp("gv_hn", 0)
        + block("for_loop_effect", "start = 0\nend = %d\nvalue = gv_hk\n" % HEADS_ROWS + tmp("gv_hi", "mod1440_gv_hp") + "add_to_temp_variable = { gv_hi = gv_hk }\n"
                + iff("check_variable = { gv_hi < mod1440_gv_rul^num }", (
                    "".join("add_to_array = { mod1440_gv_rp%s = mod1440_gv_rul%s^gv_hi }\n" % (part, part) for part in RUL + RUL_NEW)
                    + tmp("gv_hd", -1) + tmp("gv_hf", "mod1440_gv_rul_fd^gv_hi")
                    + iff("check_variable = { gv_hf > -1 }", (
                        iff("check_variable = { mod1440_gv_rul_end^gv_hi = 0 }", tmp("gv_hd", "global.num_days") + "subtract_from_temp_variable = { gv_hd = gv_hf }\n")
                        + iff("check_variable = { mod1440_gv_rul_td^gv_hi > -1 }", tmp("gv_hd", "mod1440_gv_rul_td^gv_hi")
                              + "subtract_from_temp_variable = { gv_hd = gv_hf }\n", "else_if")))
                    + "add_to_array = { mod1440_gv_rp_days = gv_hd }\n"
                    + tmp("gv_hb", 0) + iff("check_variable = { mod1440_gv_rul_p^gv_hi = gv_unk }", tmp("gv_hb", 1))
                    + "add_to_array = { mod1440_gv_rp_fb = gv_hb }\n" + "add_to_temp_variable = { gv_hn = 1 }\n")))
        + setv("mod1440_gv_rp_n", "gv_hn") + setv("mod1440_gv_hp_end", "mod1440_gv_hp") + "add_to_variable = { mod1440_gv_hp_end = %d }\n" % HEADS_ROWS
        + pad([("mod1440_gv_rp" + part, pads[part]) for part in RP], HEADS_ROWS))

    # ---- the head of government's traits: none (GV_NO_TRAITS, fix round 1). The arrays mod1440_gv_tr and _tr_e a save of
    # the first build holds stay as they are, unread.

    # ---- the parties of today: their ranks by support, the results bar's layers and the table's rows (y by property)
    base = GV_CARDS["parties"][1]
    first_row = 218 - base                              # 102: the table's first row in the card
    parties = "".join(tmp("gv_v%d" % p, "party_popularity_100@" + g) for p, (w, g) in enumerate(IDEOLOGIES))
    for p in range(4):
        parties += tmp("gv_r%d" % p, 0)
        for q in range(4):
            if q == p:
                continue
            parties += iff("check_variable = { gv_v%d > gv_v%d }" % (q, p), "add_to_temp_variable = { gv_r%d = 1 }\n" % p)
            if q < p:
                parties += iff("check_variable = { gv_v%d = gv_v%d }" % (q, p), "add_to_temp_variable = { gv_r%d = 1 }\n" % p, "else_if")
        parties += setv("mod1440_gv_rank_%d" % p, "gv_r%d" % p)
    for p in range(4):
        parties += tmp("gv_cu", 0) + "".join(iff("NOT = { check_variable = { gv_r%d > gv_r%d } }" % (q, p), "add_to_temp_variable = { gv_cu = gv_v%d }\n" % q)
                                             for q in range(4))
        parties += "clamp_temp_variable = { var = gv_cu min = 0 max = 100 }\n" + setv("mod1440_gv_cum_%d" % p, "gv_cu")
        parties += tmp("gv_y", "gv_r%d" % p) + "multiply_temp_variable = { gv_y = %d }\nadd_to_temp_variable = { gv_y = %d }\n" % (GV_SEAT, first_row)
        for off in (4, 7, 2, 24, 12, 13):
            parties += setv("mod1440_gv_py_%d_%d" % (p, off), "gv_y") + "add_to_variable = { mod1440_gv_py_%d_%d = %d }\n" % (p, off, off)
    parties += setv("mod1440_gv_py_pick", first_row) + "".join(
        iff("has_government = %s" % g, setv("mod1440_gv_py_pick", "gv_r%d" % p) + "multiply_variable = { mod1440_gv_py_pick = %d }\n" % GV_SEAT
            + "add_to_variable = { mod1440_gv_py_pick = %d }\n" % first_row) for p, (w, g) in enumerate(IDEOLOGIES))

    # ---- the record of party support, aligned with National Figures' months (mod1440_h_date)
    def back_fill(target):
        """Script: the arrays of the record trimmed or filled at their front to <target> months. A month before the
        record kept all four: the ruling party's support from series 30 (decision 7), by the ruling group and head of the
        head of government in office then (dates compared as numbers); the others -1."""
        dates = "mod1440_h_date"
        find_head = (tmp("gv_bg", "gv_g") + tmp("gv_bh", "country_leader") + tmp("gv_bd", "%s^gv_bj" % dates)
                     + block("for_loop_effect", "start = mod1440_gv_rul^num\nend = 0\ncompare = greater_than\nadd = -1\nvalue = gv_bk\n"
                             + tmp("gv_bi", "gv_bk") + "subtract_from_temp_variable = { gv_bi = 1 }\n"
                             + iff("OR = { check_variable = { mod1440_gv_rul_old^gv_bi = 1 } NOT = { check_variable = { mod1440_gv_rul_from^gv_bi > gv_bd } } }",
                                   tmp("gv_bg", "mod1440_gv_rul_g^gv_bi") + tmp("gv_bh", "mod1440_gv_rul^gv_bi"))))
        # series 30 of a save whose padding National Figures has not written yet stands shorter: read by its own index
        value = (tmp("gv_bv", -1) + tmp("gv_b30", "gv_bj") + "subtract_from_temp_variable = { gv_b30 = mod1440_h_date^num }\n"
                 + "add_to_temp_variable = { gv_b30 = mod1440_h_30^num }\n"
                 + iff("check_variable = { gv_b30 > -1 }", tmp("gv_bv", "mod1440_h_30^gv_b30")))
        insert = "".join(tmp("gv_b%d" % p, -1) + iff("check_variable = { gv_bg = %d }" % (p + 1), tmp("gv_b%d" % p, "gv_bv")) for p in range(4))
        insert += "".join("add_to_array = { array = mod1440_gv_pp_%d value = gv_b%d index = 0 }\n" % (p, p) for p in range(4))
        insert += "add_to_array = { array = mod1440_gv_pp_g value = gv_bg index = 0 }\nadd_to_array = { array = mod1440_gv_pp_h value = gv_bh index = 0 }\n"
        return (group + tmp("gv_bt", target)
                + block("while_loop_effect", "limit = { check_variable = { mod1440_gv_pp_0^num > gv_bt } }\n"
                        + "".join("remove_from_array = { array = mod1440_gv_pp%s index = 0 }\n" % part for part in PP_PARTS))
                # the parts written in step: a part shorter than the first is filled up to it at its front
                + "".join(block("while_loop_effect", "limit = { check_variable = { mod1440_gv_pp%s^num < mod1440_gv_pp_0^num } }\n" % part
                                + "add_to_array = { array = mod1440_gv_pp%s value = %s index = 0 }\n" % (part, -1 if part != "_h" else "country_leader"))
                          for part in PP_PARTS[1:])
                + iff("check_variable = { mod1440_gv_pp_0^num < gv_bt }", (
                    tmp("gv_bm", "gv_bt") + "subtract_from_temp_variable = { gv_bm = mod1440_gv_pp_0^num }\n"
                    + block("for_loop_effect", "start = gv_bm\nend = 0\ncompare = greater_than\nadd = -1\nvalue = gv_bk\n"
                            + tmp("gv_bj", "gv_bk") + "subtract_from_temp_variable = { gv_bj = 1 }\n"
                            + value
                            + find_head + insert))))

    record = (
        "\n# Government (E3 round 2): the record of party support, written by National Figures' monthly round after its series\n"
        "# (mod1440_h_record): today's support of the four parties, the ruling group and the head of government, aligned with\n"
        "# mod1440_h_date (%d months). A save of an earlier build fills the months before at the front (back_fill).\n" % M.H_KEEP
        + block("mod1440_gv_pp_record", (
            tmp("gv_rt", "mod1440_h_date^num") + "subtract_from_temp_variable = { gv_rt = 1 }\n"
            + back_fill("gv_rt")
            + "".join("add_to_array = { mod1440_gv_pp_%d = party_popularity_100@%s }\n" % (p, g) for p, (w, g) in enumerate(IDEOLOGIES))
            + group + "add_to_array = { mod1440_gv_pp_g = gv_g }\nadd_to_array = { mod1440_gv_pp_h = country_leader }\n"
            + iff("is_ai = no", "mod1440_gv_chart = yes\n")))
        + "\n# Government: the record of party support filled at its front to National Figures' months (a save of an earlier\n"
        "# build, the first day it is played with this one).\n"
        + block("mod1440_gv_pp_fill", tmp("gv_rt", "mod1440_h_date^num") + back_fill("gv_rt")))

    # ---- the chart: the months of the range as y pixels of dots, the ruling party's apart and drawn last, the band
    pd_arrays = ["mod1440_gv_pd_%s_%d" % (p, span) for span, s, d, c in GV_RANGES for p in ("0", "1", "2", "3", "r")]
    other_arrays = ["mod1440_gv_pg_%d" % span for span, s, d, c in GV_RANGES] + ["mod1440_gv_pb_%d" % span for span, s, d, c in GV_RANGES]
    clear_chart = "".join("clear_array = %s\n" % a for a in pd_arrays + other_arrays)
    px0 = GV_PLOT[0] - GV_CARDS["parties"][0]
    py0 = GV_PLOT[1] - GV_CARDS["parties"][1]
    foot = py0 + GV_PLOT[3]

    def months(span, step, dot):
        top = GV_PLOT[3] - dot // 2                 # the dot of 0%: its top this far down the plot
        body = (tmp("gv_j", "gv_from") + "add_to_temp_variable = { gv_j = gv_k }\n" + tmp("gv_g", "mod1440_gv_pp_g^gv_j") + tmp("gv_yr", -1))
        for p in range(4):
            body += (tmp("gv_y", -1) + tmp("gv_v", "mod1440_gv_pp_%d^gv_j" % p)
                     + iff("check_variable = { gv_v > -1 }", tmp("gv_y", "gv_v") + "multiply_temp_variable = { gv_y = %s }\n" % GV_PX
                           + "multiply_temp_variable = { gv_y = -1 }\nadd_to_temp_variable = { gv_y = %d }\n" % top
                           + iff("check_variable = { gv_g = %d }" % (p + 1), tmp("gv_yr", "gv_y") + tmp("gv_y", -1)))
                     + "add_to_array = { mod1440_gv_pd_%d_%d = gv_y }\n" % (p, span))
        body += "add_to_array = { mod1440_gv_pd_r_%d = gv_yr }\nadd_to_array = { mod1440_gv_pg_%d = gv_g }\nadd_to_array = { mod1440_gv_pb_%d = gv_g }\n" % (span, span, span)
        return block("for_loop_effect", "start = 0\nend = gv_cnt\nvalue = gv_k\n" + body)

    spans = "".join(iff("check_variable = { gv_span = %d }" % span, tmp("gv_step", step) + setv("mod1440_gv_rf_%d" % span, 2) + months(span, step, dot)
                        # the shares stand after the last month's dot
                        + setv("mod1440_gv_lx_s", "gv_cnt") + "multiply_variable = { mod1440_gv_lx_s = %d }\n" % step
                        + "add_to_variable = { mod1440_gv_lx_s = %d }\n" % (px0 + step // 2 + dot // 2 + 6 - step)
                        + setv("mod1440_gv_lx_t", "mod1440_gv_lx_s") + "add_to_variable = { mod1440_gv_lx_t = 9 }\n",
                        "if" if k == 0 else "else_if") for k, (span, step, dot, caption) in enumerate(GV_RANGES))
    # the years: a mark under the first month of each new year
    years = ("".join(setv("mod1440_gv_yl_%d" % k, 0) for k in range(GV_YEARS)) + tmp("gv_before", 0) + tmp("gv_slot", 0)
             + tmp("gv_yoff", "mod1440_h_date^num") + "subtract_from_temp_variable = { gv_yoff = mod1440_h_year^num }\n"
             + block("for_loop_effect", "start = 0\nend = gv_cnt\nvalue = gv_k\n" + (
                 tmp("gv_yi", "gv_from") + "add_to_temp_variable = { gv_yi = gv_k }\nsubtract_from_temp_variable = { gv_yi = gv_yoff }\n"
                 + tmp("gv_yv", 0) + iff("check_variable = { gv_yi > -1 }", tmp("gv_yv", "mod1440_h_year^gv_yi"))
                 + iff("check_variable = { gv_k > 0 } check_variable = { gv_yv > 0 } NOT = { check_variable = { gv_yv = gv_before } } check_variable = { gv_slot < %d }" % GV_YEARS, (
                     tmp("gv_x", "gv_k") + "multiply_temp_variable = { gv_x = gv_step }\nadd_to_temp_variable = { gv_x = %d }\n" % px0
                     + gv_slot("gv_slot", GV_YEARS, lambda n: setv("mod1440_gv_yl_%d" % n, "gv_yv") + setv("mod1440_gv_tx_%d" % n, "gv_x")
                               + setv("mod1440_gv_yx_%d" % n, "gv_x") + "subtract_from_variable = { mod1440_gv_yx_%d = 20 }\n" % n)
                     + "add_to_temp_variable = { gv_slot = 1 }\n"))
                 + tmp("gv_before", "gv_yv"))))
    # who governed: a span per head of government, his name where it fits
    close_span = iff("check_variable = { gv_open = 1 }", tmp("gv_open", 0) + gv_slot("gv_sn", GV_SPANS + 1, lambda n: (
        setv("mod1440_gv_bw_%d" % (n - 1), "gv_k") + "subtract_from_variable = { mod1440_gv_bw_%d = gv_bs }\n" % (n - 1)
        + "multiply_variable = { mod1440_gv_bw_%d = gv_step }\n" % (n - 1) + setv("mod1440_gv_bt_%d" % (n - 1), "gv_bl")), 1))
    heads_band = (tmp("gv_sn", 0) + tmp("gv_ph", -1) + tmp("gv_bs", 0) + tmp("gv_bl", "global.date") + tmp("gv_open", 0)
                  + block("for_loop_effect", "start = 0\nend = gv_cnt\nvalue = gv_k\n" + (
                      tmp("gv_j", "gv_from") + "add_to_temp_variable = { gv_j = gv_k }\n" + tmp("gv_hv", "mod1440_gv_pp_h^gv_j")
                      + iff("OR = { check_variable = { gv_k = 0 } NOT = { check_variable = { gv_hv = gv_ph } } }", (
                          close_span
                          + iff("check_variable = { gv_sn < %d }" % GV_SPANS, (
                              tmp("gv_x", "gv_k") + "multiply_temp_variable = { gv_x = gv_step }\nadd_to_temp_variable = { gv_x = %d }\n" % (px0 + 6)
                              + gv_slot("gv_sn", GV_SPANS, lambda n: setv("mod1440_gv_bn_%d" % n, "gv_hv") + setv("mod1440_gv_bx_%d" % n, "gv_x")
                                        + setv("mod1440_gv_bf_%d" % n, "mod1440_h_date^gv_j"))
                              + tmp("gv_bs", "gv_k") + tmp("gv_open", 1) + "add_to_temp_variable = { gv_sn = 1 }\n"))
                          + tmp("gv_ph", "gv_hv")))
                      + tmp("gv_bl", "mod1440_h_date^gv_j")))
                  + tmp("gv_k", "gv_cnt") + close_span + setv("mod1440_gv_bn_n", "gv_sn"))
    # an election a tick at the boundary of its month (both lists by date, a pointer each)
    tick = lambda at: iff("check_variable = { gv_tn < %d }" % GV_TICKS, (
        tmp("gv_x", at) + "multiply_temp_variable = { gv_x = gv_step }\nadd_to_temp_variable = { gv_x = %d }\n" % (px0 - 1)
        + gv_slot("gv_tn", GV_TICKS, lambda n: setv("mod1440_gv_tk_%d" % n, "gv_x") + setv("mod1440_gv_td_%d" % n, "mod1440_gv_el^gv_e"))
        + "add_to_temp_variable = { gv_tn = 1 }\n"))
    ticks = (tmp("gv_e", 0) + tmp("gv_tn", 0) + tmp("gv_en", "mod1440_gv_el^num") + tmp("gv_d0", "mod1440_h_date^gv_from") + tmp("gv_wb", 0)
             + block("while_loop_effect", "limit = { check_variable = { gv_e < gv_en } }\nbreak = gv_wb\n"
                     + iff("check_variable = { mod1440_gv_el^gv_e < gv_d0 }", "add_to_temp_variable = { gv_e = 1 }\n") + els(tmp("gv_wb", 1)))
             + block("for_loop_effect", "start = 1\nend = gv_cnt\nvalue = gv_k\n" + (
                 tmp("gv_j", "gv_from") + "add_to_temp_variable = { gv_j = gv_k }\n" + tmp("gv_dj", "mod1440_h_date^gv_j") + tmp("gv_wb", 0)
                 + block("while_loop_effect", "limit = { check_variable = { gv_e < gv_en } }\nbreak = gv_wb\n"
                         + iff("check_variable = { mod1440_gv_el^gv_e < gv_dj }", tick("gv_k") + "add_to_temp_variable = { gv_e = 1 }\n") + els(tmp("gv_wb", 1)))))
             + block("while_loop_effect", "limit = { check_variable = { gv_e < gv_en } }\n" + tick("gv_cnt") + "add_to_temp_variable = { gv_e = 1 }\n")
             + setv("mod1440_gv_tk_n", "gv_tn"))
    # the share at each line's end, the lowest first, each at least 18 px above the one under it
    ends = tmp("gv_last", "gv_n") + "subtract_from_temp_variable = { gv_last = 1 }\n"
    for p in range(4):
        ends += (setv("mod1440_gv_lv_%d" % p, -1) + tmp("gv_c%d" % p, 0) + tmp("gv_pl%d" % p, 0)
                 + iff("check_variable = { gv_n > 0 }", setv("mod1440_gv_lv_%d" % p, "mod1440_gv_pp_%d^gv_last" % p))
                 + iff("check_variable = { mod1440_gv_lv_%d > -1 }" % p, tmp("gv_c%d" % p, "mod1440_gv_lv_%d" % p)
                       + "multiply_temp_variable = { gv_c%d = %s }\nmultiply_temp_variable = { gv_c%d = -1 }\nadd_to_temp_variable = { gv_c%d = %d }\n"
                       % (p, GV_PX, p, p, foot)))
    ends += tmp("gv_low", foot + 4)
    for r in range(4):
        ends += tmp("gv_best", -1000) + tmp("gv_bi", -1)
        for p in range(4):
            ends += iff("check_variable = { gv_pl%d = 0 } check_variable = { mod1440_gv_lv_%d > -1 } check_variable = { gv_c%d > gv_best }" % (p, p, p),
                        tmp("gv_best", "gv_c%d" % p) + tmp("gv_bi", p))
        ends += iff("check_variable = { gv_bi > -1 }", (
            iff("check_variable = { gv_best > gv_low }", tmp("gv_best", "gv_low"))
            + gv_slot("gv_bi", 4, lambda p: tmp("gv_c%d" % p, "gv_best") + tmp("gv_pl%d" % p, 1))
            + tmp("gv_low", "gv_best") + "subtract_from_temp_variable = { gv_low = %d }\n" % GV_LABEL_GAP))
    for p in range(4):
        ends += (setv("mod1440_gv_ly_%d_s" % p, "gv_c%d" % p) + "subtract_from_variable = { mod1440_gv_ly_%d_s = 3 }\n" % p
                 + setv("mod1440_gv_ly_%d_t" % p, "gv_c%d" % p) + "subtract_from_variable = { mod1440_gv_ly_%d_t = 11 }\n" % p)
    # the change in a year, the ruling party at its highest, the months recorded and how many in full
    figures = ""
    for p in range(4):
        figures += (setv("mod1440_gv_hy_%d" % p, 0) + iff("check_variable = { gv_n > 12 }", (
            tmp("gv_a", "mod1440_gv_pp_%d^gv_last" % p) + tmp("gv_i13", "gv_n") + "subtract_from_temp_variable = { gv_i13 = 13 }\n"
            + tmp("gv_b", "mod1440_gv_pp_%d^gv_i13" % p)
            + iff("check_variable = { gv_a > -1 } check_variable = { gv_b > -1 }", setv("mod1440_gv_dy_%d" % p, "gv_a")
                  + "subtract_from_variable = { mod1440_gv_dy_%d = gv_b }\n" % p + setv("mod1440_gv_hy_%d" % p, 1)))))
    figures += (setv("mod1440_gv_hi", 0) + setv("mod1440_gv_hi_d", "global.date") + iff("check_variable = { mod1440_h_30^num > 0 }", (
        tmp("gv_hi", 0) + tmp("gv_hat", 0) + block("find_highest_in_array", "array = mod1440_h_30\nvalue = gv_hi\nindex = gv_hat\n")
        + setv("mod1440_gv_hi", "gv_hi") + setv("mod1440_gv_hi_d", "mod1440_h_date^gv_hat"))))
    figures += (tmp("gv_full", 0) + tmp("gv_ff", -1)
                + block("for_loop_effect", "start = 0\nend = gv_n\nvalue = gv_k\n" + iff(
                    " ".join("check_variable = { mod1440_gv_pp_%d^gv_k > -1 }" % p for p in range(4)),
                    "add_to_temp_variable = { gv_full = 1 }\n" + iff("check_variable = { gv_ff < 0 }", tmp("gv_ff", "gv_k"))))
                + setv("mod1440_gv_pp_full", "gv_full") + setv("mod1440_gv_full_d", "global.date")
                + iff("check_variable = { gv_ff > -1 }", setv("mod1440_gv_full_d", "mod1440_h_date^gv_ff"))
                + setv("mod1440_gv_bf", 0) + iff("OR = { check_variable = { gv_ff > gv_from } check_variable = { gv_ff < 0 } } check_variable = { gv_n > 0 }",
                                                  setv("mod1440_gv_bf", 1)))
    chart = (
        "\n# Government: the chart of party support for the range chosen (or the shortest that holds every month): the y of\n"
        "# each party's dot in each month (-1: none), the ruling party's apart (drawn last), the band of who governed, the\n"
        "# years, the election ticks and the shares at the lines' ends. Run on a range click, on the first of the month and\n"
        "# when the panel of the heads closes (rule 5); while the panel is open the arrays stay empty.\n"
        + block("mod1440_gv_chart", (
            clear_chart + "".join(setv("mod1440_gv_rf_%d" % span, 1) for span, s, d, c in GV_RANGES)
            + tmp("gv_n", "mod1440_gv_pp_0^num") + setv("mod1440_gv_pp_n", "gv_n") + setv("mod1440_gv_chart_v", GV_CHART_VER)
            + iff("NOT = { %s }" % is_one("mod1440_gv_heads"), (
                tmp("gv_span", "mod1440_gv_range")
                + iff("check_variable = { gv_span = 0 }", tmp("gv_span", GV_RANGES[0][0])
                      + "".join(iff("check_variable = { gv_n > %d }" % GV_RANGES[k - 1][0], tmp("gv_span", GV_RANGES[k][0])) for k in range(1, len(GV_RANGES))))
                + tmp("gv_from", "gv_n") + "subtract_from_temp_variable = { gv_from = gv_span }\n"
                + iff("check_variable = { gv_from < 0 }", tmp("gv_from", 0))
                + tmp("gv_cnt", "gv_n") + "subtract_from_temp_variable = { gv_cnt = gv_from }\n"
                + tmp("gv_step", GV_RANGES[0][1]) + spans + years + heads_band + ticks + ends + figures)))))

    panel = (
        "\n# Government: the heads panel opened or closed (mod1440_gv_heads): its button's frame, its copy, the chart.\n"
        + block("mod1440_gv_panel", setv("mod1440_gv_heads_f", 1) + iff(is_one("mod1440_gv_heads"), setv("mod1440_gv_heads_f", 2) + "mod1440_gv_heads_copy = yes\n")
                + "mod1440_gv_chart = yes\n")
        + block("mod1440_gv_heads_copy", heads_copy)
        + "\n# Government: an election (on_new_term_election): its date and day, kept %d, and one more in the term of today's head.\n" % GV_EL_KEEP
        + block("mod1440_gv_election", "add_to_array = { mod1440_gv_el = global.date }\nadd_to_array = { mod1440_gv_el_d = global.num_days }\n"
                + iff("check_variable = { mod1440_gv_el^num > %d }" % GV_EL_KEEP,
                      "remove_from_array = { array = mod1440_gv_el index = 0 }\nremove_from_array = { array = mod1440_gv_el_d index = 0 }\n")
                + iff("check_variable = { mod1440_gv_rul_e^num > 0 }", "add_to_variable = { mod1440_gv_rul_e^0 = 1 }\n")))

    # ---- the government's lines of the War Diary: the newest eight of family 3, made again when the log has grown or the
    # numbers of the text keys moved
    diary_parts = [("date", "date"), ("kind", "kind"), ("a", "a"), ("sa", "sa"), ("b", "b"), ("sb", "sb")]
    diary = iff("OR = { NOT = { check_variable = { mod1440_gv_dl_seen = mod1440_ln_next } } %s NOT = { check_variable = { mod1440_gv_dl_v = 2 } } }" % stale("mod1440_gv_dl"), (
        "".join("clear_array = mod1440_gv_dl_%s\n" % name for name, part in diary_parts) + tmp("gv_df", 0) + tmp("gv_db", 0)
        + tmp("gv_ds", "mod1440_ev_date^num") + "subtract_from_temp_variable = { gv_ds = 1 }\n"
        + tmp("gv_me", "THIS")
        + block("for_loop_effect", "start = gv_ds\nend = 0\ncompare = greater_than_or_equals\nadd = -1\nvalue = gv_di\nbreak = gv_db\n" + iff(
            "check_variable = { mod1440_ev_fam^gv_di = 3 }",
            # E3 fix round 2: a line about a person whose subject is no character (the 'Appointed German Reich' line an earlier
            # build wrote for the phantom seat) is left off the card; the log keeps it
            tmp("gv_dok", 1) + iff("check_variable = { mod1440_ev_sa^gv_di = 1 }", tmp("gv_da", "mod1440_ev_a^gv_di") + gv_person_test("gv_da", "gv_dok"))
            + iff("check_variable = { gv_dok = 1 }",
                  "".join("add_to_array = { mod1440_gv_dl_%s = mod1440_ev_%s^gv_di }\n" % (name, part) for name, part in diary_parts)
                  + "add_to_temp_variable = { gv_df = 1 }\n" + iff("check_variable = { gv_df > %d }" % (GV_DIARY - 1), tmp("gv_db", 1)))))
        + setv("mod1440_gv_dl_n", "gv_df")
        + pad([("mod1440_gv_dl_date", "global.date"), ("mod1440_gv_dl_kind", BLANK), ("mod1440_gv_dl_a", 0), ("mod1440_gv_dl_sa", 0),
               ("mod1440_gv_dl_b", "THIS"), ("mod1440_gv_dl_sb", 0)], GV_DIARY)
        + setv("mod1440_gv_dl_seen", "mod1440_ln_next") + setv("mod1440_gv_dl_v", 2) + stamped("mod1440_gv_dl")))

    # ---- the agency: when it was founded, its upgrades at their highest level, each operative's network, the cipher
    # being broken, what we know of three countries (the @<country> forms with a country held in a variable: see the
    # game check; fallback in build.json)
    # E3 fix round 2: the first run of the agency's record (mod1440_gv_ag_v) takes an agency that is there already as founded
    # before the record; and a save that ran the first build of round 2, which wrote that day as the founding (the user's
    # 'founded 24 August, 1940'), gets 'before the record' when no month of the record of party support before it is kept in
    # full (that record and the agency's began with the same build)
    agency_first = iff("NOT = { check_variable = { mod1440_gv_ag_v = 1 } }", (
        iff("%s check_variable = { mod1440_gv_ag_old = 0 }" % is_one("mod1440_gv_ag_has"), (
            tmp("gv_aff", -1) + tmp("gv_ab", 0)
            + block("for_loop_effect", "start = 0\nend = mod1440_gv_pp_0^num\nvalue = gv_ak\nbreak = gv_ab\n" + iff(
                " ".join("check_variable = { mod1440_gv_pp_%d^gv_ak > -1 }" % p for p in range(4)), tmp("gv_aff", "gv_ak") + tmp("gv_ab", 1)))
            + tmp("gv_ad", "global.date") + iff("check_variable = { gv_aff > -1 }", tmp("gv_ad", "mod1440_h_date^gv_aff"))
            + iff("OR = { check_variable = { gv_aff < 0 } check_variable = { gv_ad > mod1440_gv_ag_since } }", setv("mod1440_gv_ag_old", 1))))
        + iff("has_intelligence_agency = yes NOT = { %s }" % is_one("mod1440_gv_ag_has"),
              setv("mod1440_gv_ag_has", 1) + setv("mod1440_gv_ag_since", "global.date") + setv("mod1440_gv_ag_old", 1))
        + setv("mod1440_gv_ag_v", 1)))
    intel = agency_first + (iff("has_intelligence_agency = yes NOT = { %s }" % is_one("mod1440_gv_ag_has"), (
        setv("mod1440_gv_ag_has", 1) + setv("mod1440_gv_ag_since", "global.date") + setv("mod1440_gv_ag_old", 1) + iff(begun, setv("mod1440_gv_ag_old", 0))))
        + tmp("gv_ud", 0) + "".join(iff("has_done_agency_upgrade = %s" % upgrade, "add_to_temp_variable = { gv_ud = 1 }\n") for upgrade, sprite in GV_UPGRADES)
        + setv("mod1440_gv_ag_done", "gv_ud")
        + block("every_operative", (
            tmp("gv_oc", "operation_country") + setv("mod1440_gv_home", 0) + setv("mod1440_gv_net", 0)
            + iff("check_variable = { gv_oc > 0 }", (
                block("PREV", tmp("gv_me", "THIS") + tmp("gv_nc", "network_national_coverage@var:gv_oc"))
                + iff("check_variable = { gv_oc = gv_me }", setv("mod1440_gv_home", 1))
                + els(setv("mod1440_gv_net", "gv_nc") + "multiply_variable = { mod1440_gv_net = 100 }\n")))))
        + setv("mod1440_gv_dc_has", 0)
        + iff("is_cryptology_department_active = yes", (
            tmp("gv_dct", 0)
            + block("every_country", "limit = { OR = { is_major = yes has_war_with = ROOT } ROOT = { is_decrypting = PREV } }\n" + tmp("gv_dct", "THIS"))
            + iff("NOT = { check_variable = { gv_dct = 0 } }", setv("mod1440_gv_dc", "gv_dct") + setv("mod1440_gv_dc_has", 1)
                  + tmp("gv_dp", "decryption_progress@var:gv_dct") + setv("mod1440_gv_dc_p", "gv_dp") + "multiply_variable = { mod1440_gv_dc_p = 100 }\n")))
        + "clear_temp_array = gv_kt\n" + tmp("gv_kb", 0)
        + block("for_each_loop", "array = enemies\nvalue = gv_kc\nbreak = gv_kb\n" + iff(
            "check_variable = { gv_kt^num < %d }" % GV_KNOW, "add_to_temp_array = { gv_kt = gv_kc }\n") + els(tmp("gv_kb", 1)))
        + block("every_country", "limit = { is_major = yes NOT = { tag = ROOT } }\n" + tmp("gv_kc", "THIS") + iff(
            "check_variable = { gv_kt^num < %d } NOT = { is_in_array = { array = gv_kt value = gv_kc } }" % GV_KNOW, "add_to_temp_array = { gv_kt = gv_kc }\n"))
        + "".join("clear_array = mod1440_gv_kn%s\n" % part for part in ("", "_c", "_a", "_n", "_i"))
        + block("for_each_loop", "array = gv_kt\nvalue = gv_kc\n" + "add_to_array = { mod1440_gv_kn = gv_kc }\n" + "".join(
            # E3 fix round 2: the value is already in percent points, the sum of the intel sources, which can pass 100 (the
            # user's United Kingdom read 108.14, shown as 10814%); the intelligence ledger shows it clamped to 100%
            tmp("gv_kv", "%s_intel@var:gv_kc" % kind) + "clamp_temp_variable = { var = gv_kv min = 0 max = 100 }\nadd_to_array = { mod1440_gv_kn_%s = gv_kv }\n" % part
            for part, kind in (("c", "civilian"), ("a", "army"), ("n", "navy"), ("i", "air"))))
        + setv("mod1440_gv_kn_n", "mod1440_gv_kn^num")
        + pad([("mod1440_gv_kn", "THIS"), ("mod1440_gv_kn_c", 0), ("mod1440_gv_kn_a", 0), ("mod1440_gv_kn_n", 0), ("mod1440_gv_kn_i", 0)], GV_KNOW))

    return (
        "\n# Government: compares who holds each office with yesterday's copy. A new name gets today's date, a line\n"
        "# in the War Diary, and his portrait, role and its effects; a name that is gone a line. The first run only takes the\n"
        "# copy. Then the heads of government since the record began, the laws in force and their pictures, the parties of\n"
        "# today, the leader's portrait and traits, the seats the page shows, the government's lines of the War Diary, the\n"
        "# agency, and the figures of the record. E3 round 2: an element of the advisor arrays that is no character is left out.\n"
        + block("mod1440_gv_daily", (
            migration
            + tmp("gv_stale", 0) + iff(stale("mod1440_gv_adv_ver", adv_version), tmp("gv_stale", 1) + rulers_again)
            + iff("NOT = { check_variable = { mod1440_gv_leader = country_leader } }", (
                setv("mod1440_gv_leader", "country_leader") + setv("mod1440_gv_leader_since", "global.date") + setv("mod1440_gv_leader_old", 1)
                + iff(begun, setv("mod1440_gv_leader_old", 0) + line("leader", a="country_leader"))))
            + face
            + iff("OR = { check_variable = { mod1440_gv_rul^num < 1 } NOT = { check_variable = { mod1440_gv_rul^0 = country_leader } } }", new_head)
            # today's head: stability and war support of his last day so far, the days the record has kept him
            + iff("check_variable = { mod1440_gv_rul^num > 0 }", stab + setv("mod1440_gv_rul_s1^0", "gv_st") + setv("mod1440_gv_rul_w1^0", "gv_ws")
                  + setv("mod1440_gv_leader_rec", -1) + iff("check_variable = { mod1440_gv_rul_fd^0 > -1 }", setv("mod1440_gv_leader_rec", "global.num_days")
                                                            + "subtract_from_variable = { mod1440_gv_leader_rec = mod1440_gv_rul_fd^0 }\n"))
            + tmp("gv_hc_n", 0) + offices
            + office_array("political_advisor", "mod1440_gv_adv", "political_advisor") + office_array("high_command", "mod1440_gv_hc", "high_command")
            + "add_to_temp_variable = { gv_hc_n = mod1440_gv_hc^num }\n" + setv("mod1440_gv_hc_n", "gv_hc_n")
            + shown_seats("adv", CABINET_SLOTS) + shown_seats("hc", MEMBER_SLOTS) + heads_shown + "mod1440_gv_heads_copy = yes\n"
            # E7: the chiefs and the members of the high command who are unit leaders: the game draws their faces
            + "".join("clear_array = mod1440_gv_of_%d_ul\n" % k + iff(is_one("mod1440_gv_of_%d_has" % k), unit_leader_into(
                "mod1440_gv_of_%d" % k, "mod1440_gv_of_%d_ul" % k, "gv_ul")) for k in range(len(OFFICES)))
            + "".join("clear_array = mod1440_gv_hc_%d_ul\n" % k + iff("check_variable = { mod1440_gv_hc^num > %d }" % k, unit_leader_into(
                "mod1440_gv_hc_d^%d" % k, "mod1440_gv_hc_%d_ul" % k, "gv_ul")) for k in range(MEMBER_SLOTS))
            + laws + support + parties + diary + intel
            + pad([("mod1440_ct", 0)], len(KINDS) + 8) + sums + setv("mod1440_gv_begun", 1)
            + stamped("mod1440_gv_adv_ver", adv_version)
            # the record of party support of a save of an earlier build, and the chart once for this build
            + iff("check_variable = { mod1440_gv_pp_0^num < mod1440_h_date^num }", "mod1440_gv_pp_fill = yes\n" + setv("mod1440_gv_chart_v", 0))
            + iff("NOT = { check_variable = { mod1440_gv_chart_v = %d } }" % GV_CHART_VER, setv("mod1440_gv_heads_f", 1) + "mod1440_gv_chart = yes\n")
            + "mod1440_gv_marks = yes\n"))
        + record + chart + panel)


def government_hooks():
    """E3 round 2: the election's date for the chart and the heads panel, beside E1's line (frame(), unchanged)."""
    return {"on_new_term_election": iff("is_ai = no", "mod1440_gv_election = yes\n")}


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
            # E2 round 2: the chain of command after the officers' round, on Army Readiness's count of the day (mod1440_al_loc)
            + "mod1440_wr_daily = yes\nmod1440_gv_daily = yes\nmod1440_of_seen = yes\nmod1440_of_chain = yes\nmod1440_of_gone = yes\n"
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


# --- E2 round 2 --- the Officers scene (tools/scenes/officers.json): Germany on 6 April 1939 as the design drew it
# (scratch/phases/E2/work/make_layout.py). Whether script shows a widget is worked out from the tests officers() keeps
# beside each trigger (OF_SCENE), for the file's sample state and for each sample row.
# key: name, rank (fm, gen, adm), army (None: unassigned), skill, levels, traits, divisions, won, lost, medals, armies (fm)
OS_PEOPLE = {
    "witzleben": ("Erwin von Witzleben", "fm", "Heeresgruppe C", 4, (5, 3, 2, 4), ["brilliant_strategist", "old_guard", "politically_connected", "offensive_doctrine", "organizer"], 25, 2, 0, 1, 2),
    "model": ("Walter Model", "fm", "OKH - Westen", 3, (5, 3, 3, 2), ["brilliant_strategist", "career_officer", "trait_cautious", "offensive_doctrine", "aggressive_assaulter", "organizer"], 28, 0, 0, 0, 3),
    "leeb": ("Wilhelm Ritter von Leeb", "fm", "Heeresgruppe Nord", 3, (4, 3, 1, 2), ["old_guard", "trait_cautious", "defensive_doctrine"], 20, 0, 0, 0, 2),
    "bock": ("Fedor von Bock", "gen", "Army 1", 4, (4, 3, 4, 3), ["old_guard", "career_officer", "infantry_officer", "hill_fighter"], 14, 1, 0, 0, 0),
    "rundstedt": ("Gerd von Rundstedt", "gen", "Army 2", 3, (3, 2, 3, 2), ["old_guard", "trait_cautious", "urban_assault_specialist"], 7, 3, 1, 1, 0),
    "kluge": ("Günther von Kluge", "gen", "Army 3", 3, (3, 2, 2, 3), ["career_officer", "trait_cautious"], 7, 0, 0, 0, 0),
    "blaskowitz": ("Johannes Blaskowitz", "gen", "Army 4", 3, (3, 3, 3, 2), ["infantry_officer", "career_officer", "politically_connected", "hill_fighter", "trait_cautious"], 14, 0, 0, 0, 0),
    "kuchler": ("Georg von Küchler", "gen", "Army 5", 4, (3, 3, 4, 5), ["old_guard", "trait_engineer"], 11, 0, 0, 0, 0),
    "kleist": ("Ewald von Kleist", "gen", "Panzergruppe Kleist", 2, (2, 1, 2, 2), ["armor_officer", "panzer_leader"], 10, 2, 0, 0, 0),
    "guderian": ("Heinz Guderian", "gen", "Army 7", 4, (5, 2, 3, 3), ["armor_officer", "panzer_leader", "trait_reckless", "media_personality"], 10, 0, 0, 0, 0),
    "manstein": ("Erich von Manstein", "gen", "Army 8", 4, (3, 4, 4, 4), ["brilliant_strategist", "infantry_officer", "hill_fighter", "media_personality"], 2, 2, 0, 2, 0),
    "list": ("Wilhelm List", "gen", "Army 9", 2, (2, 3, 1, 3), ["infantry_officer", "hill_fighter", "trait_cautious"], 2, 0, 0, 0, 0),
    "rommel": ("Erwin Rommel", "gen", "Army 10", 3, (4, 1, 2, 3), ["infantry_officer", "trait_reckless"], 3, 0, 0, 0, 0),
    # E2 fix round 2: the user's case of 27 June 1939, an army in no army group whose divisions share a state with one's
    "cranz": ("Friedrich-Carl Cranz", "gen", "I. SS-Standarten", 2, (2, 2, 1, 2), ["career_officer"], 3, 0, 0, 0, 0),
    "hoth": ("Hermann Hoth", "gen", None, 3, (3, 3, 3, 2), ["armor_officer"], 0, 0, 0, 0, 0),
    "paulus": ("Friedrich Paulus", "gen", None, 2, (1, 2, 4, 3), ["career_officer"], 0, 0, 0, 0, 0),
    "weichs": ("Maximilian von Weichs", "gen", None, 3, (2, 3, 3, 3), ["old_guard"], 0, 0, 0, 0, 0),
    "reinhardt": ("Georg-Hans Reinhardt", "gen", None, 2, (3, 1, 2, 2), ["armor_officer"], 0, 0, 0, 0, 0),
    "student": ("Kurt Student", "gen", None, 3, (3, 2, 3, 2), ["commando"], 0, 0, 0, 0, 0),
    "kesselring": ("Albert Kesselring", "gen", None, 3, (2, 4, 3, 3), ["career_officer"], 0, 0, 0, 0, 0),
    "jodl": ("Alfred Jodl", "gen", None, 2, (1, 2, 3, 3), ["career_officer"], 0, 0, 0, 0, 0),
    "raeder": ("Erich Raeder", "adm", "Fleet", 4, (4, 3, 4, 3), ["old_guard_navy", "superior_tactician"], 41, 0, 0, 0, 0),
    "donitz": ("Karl Dönitz", "adm", "Fleet", 3, (3, 2, 4, 3), ["seawolf"], 30, 0, 0, 0, 0),
    "lutjens": ("Günther Lütjens", "adm", "Fleet", 3, (3, 3, 3, 2), ["gunnery_expert"], 12, 0, 0, 0, 0),
}
OS_CAN = {"rundstedt", "guderian", "kluge"}         # a free slot in the trait tree: the green mark
OS_PAGE = ["witzleben", "model", "leeb", "bock", "rundstedt", "kluge", "blaskowitz", "kuchler", "kleist", "guderian", "manstein", "list",
           "rommel", "hoth", "paulus", "weichs", "reinhardt", "student", "kesselring", "jodl"]
OS_OOB = [("model", 0), ("bock", 1), ("rundstedt", 1), ("kluge", 1), ("witzleben", 0), ("blaskowitz", 1), ("kuchler", 1), ("leeb", 0),
          ("kleist", 1), ("guderian", 1), ("manstein", 0), ("list", 0), ("rommel", 0), ("cranz", 0), ("raeder", 0), ("donitz", 0), ("lutjens", 0)]
OS_WORDS = {"fm": "Field Marshal", "gen": "General", "adm": "Admiral"}
OS_TRAIT_NAMES = {"old_guard": "Old Guard", "trait_cautious": "Cautious", "urban_assault_specialist": "Urban Assault Specialist",
                  "brilliant_strategist": "Brilliant Strategist", "career_officer": "Career Officer", "offensive_doctrine": "Offensive Doctrine",
                  "aggressive_assaulter": "Aggressive Assaulter", "organizer": "Organizer", "armor_officer": "Armor Officer",
                  "panzer_leader": "Panzer Leader"}
# the diary of a file: (date, family, words, subject, what the subject is: 0 none, 2 a state or country, 3 a text key)
OS_LINES = {
    "rundstedt": [("12 March, 1939", 4, "Decorated", "Knight's Cross", 3), ("14 October, 1938", 2, "Victory point taken", "Brno", 3),
                  ("14 October, 1938", 2, "State taken", "Jihomoravsko", 2), ("9 October, 1938", 2, "Victory point taken", "Olomouc", 3),
                  ("9 October, 1938", 2, "State taken", "Severní Morava", 2), ("2 October, 1938", 2, "Victory point taken", "Opava", 3),
                  ("28 September, 1938", 4, "Gained a skill level", "", 0), ("1 October, 1938", 1, "War declared on", "Czechoslovakia", 2)],
    "model": [("31 October, 1936", 2, "Victory point taken", "Amsterdam", 3), ("31 October, 1936", 2, "Capital taken", "Holland", 2),
              ("22 September, 1936", 2, "Victory point taken", "Maastricht", 3), ("19 September, 1936", 2, "Victory point taken", "The Hague", 3),
              ("10 September, 1936", 2, "State taken", "Noord-Brabant", 2), ("12 August, 1936", 4, "Promoted to field marshal", "", 0)],
    "kleist": [("10 October, 1938", 2, "State taken", "Plzensko", 2), ("8 October, 1938", 1, "Divisions cited in", "Karlovy Vary", 2)],
}


def os_row(key, i, picked, ind, names):
    """A sample row: what the row's tests read (officer_status(), OF_SCENE['row_shows'])."""
    name, rank, army, skill, levels, traits, div, won, lost, medals, armies = OS_PEOPLE[key]
    status = "idle" if army is None else {"fm": "grp", "gen": "army", "adm": "fleet"}[rank]
    return {"key": key, "rank": rank, "status": status, "names": names, "ind": bool(ind), "picked": key == picked, "odd": i % 2 == 1,
            "serves": True, "tr": min(len(traits), TRAIT_ICONS), "plus": max(0, len(traits) - TRAIT_ICONS), "dec": medals,
            "won": won, "lost": lost, "can": key in OS_CAN, "subs": armies}


def os_line2(r):
    name, rank, army, skill, levels, traits, div, won, lost, medals, armies = OS_PEOPLE[r["key"]]
    lead = "§g%s  ·  " % OS_WORDS[rank]
    if r["status"] == "idle":
        return lead + "unassigned§!"
    if r["status"] == "grp":
        return lead + "§!" + army if r["names"] else lead + "Army group of %d armies§!" % armies
    if r["status"] == "fleet":
        return lead + "Fleet of %d ships§!" % div
    return lead + "§!" + army if r["names"] else lead + "army of %d divisions§!" % div


def os_rows(keys, picked, names):
    """The list's rows: how many, which instance of each widget script shows, and their texts in drawing order."""
    rows = [os_row(key, i, picked, ind, names) for i, (key, ind) in enumerate(keys)]
    only = dict((name, [i for i, r in enumerate(rows) if test(r)]) for name, test in OF_SCENE["row_shows"].items())
    samples = {}

    def add(widget, text):
        samples.setdefault(widget, []).append(text)
    for r in rows:
        p = OS_PEOPLE[r["key"]]
        suffix = "_in" if r["ind"] else ""
        add(("of_row_name_sel" if r["picked"] else "of_row_name") + suffix, "§Y%s§!" % p[0] if r["picked"] else p[0])
        for status, words, condition, test in officer_status():
            if status_shown(test, r):
                add("of_row_st_" + status + (suffix if test[1] == "army" else ""), os_line2(r))
        add("of_cell_skill", str(p[3]))
        add("of_cell_atk", str(p[4][0]))
        add("of_cell_def", str(p[4][1]))
        add("of_cell_c3_navy" if r["rank"] == "adm" else "of_cell_c3", str(p[4][2]))
        add("of_cell_c4_navy" if r["rank"] == "adm" else "of_cell_c4", str(p[4][3]))
        if r["status"] in ("army", "grp", "fleet"):
            add({"army": "of_cell_cmd", "grp": "of_cell_cmd_group", "fleet": "of_cell_cmd_navy"}[r["status"]],
                "§g%d§!" % p[6] if r["status"] == "grp" else str(p[6]))
        for col, value in (("won", p[7]), ("lost", p[8])):
            if value:
                add("of_cell_" + col, str(value))
        if r["plus"]:
            add("of_row_tr_more", "+%d" % r["plus"])
    images = {"of_row_tr_%d" % t: ["GFX_trait_" + OS_PEOPLE[r["key"]][5][t] for r in rows if r["tr"] > t] for t in range(TRAIT_ICONS)}
    return len(rows), only, samples, images


def os_file(key, st):
    """The texts of the file of <key> in the sample state <st>."""
    name, rank, army, skill, levels, traits, div, won, lost, medals, armies = OS_PEOPLE[key]
    out = {"of_c_name": name, "of_c_skill": str(skill), "of_c_atk": str(levels[0]), "of_c_def": str(levels[1]),
           "of_c_c3": str(levels[2]), "of_c_c4": str(levels[3]), "of_c_tr_count": st["count"],
           "of_c_won": str(won), "of_c_lost": str(lost), "of_c_states": st["states"], "of_c_vps": st["vps"], "of_c_vpl": "0",
           "of_c_m_dec": str(medals), "of_c_o_dec": str(medals), "of_c_m_since": st.get("since", ""), "of_c_m_prom": st.get("prom", ""),
           "of_c_o_lvl": st.get("lvl", ""), "of_c_m_lvl": st.get("lvl", "")}
    for k, trait in enumerate(traits[:TRAIT_ICONS]):
        out["of_c_tr_%d_n" % k] = OS_TRAIT_NAMES.get(trait, trait)
    out.update(st.get("words", {}))
    for k, (date, fam, words, subject, sa) in enumerate(OS_LINES.get(key, [])):
        out["of_ln_%d_d" % k] = date
        out["of_ln_%d" % k] = words
        if sa:
            out["of_ln_%d_%s" % (k, "s" if sa == 2 else "p")] = "§Y%s§!" % subject
    return out


def os_state(key, **more):
    name, rank, army, skill, levels, traits, div, won, lost, medals, armies = OS_PEOPLE[key]
    st = {"has": True, "award": False, "rank": {"fm": 1, "gen": 2, "adm": 3}[rank], "status": 1 if army else 0,
          "mode": 0 if army is None else {"fm": 2, "gen": 1, "adm": 3}[rank], "chain": rank == "fm" and OF_CHAIN, "names": True,
          "loc": army is not None and rank != "adm", "hq": True, "fm": 0, "subs": armies, "plan_none": True, "eq": True,
          "tr_i": min(len(traits), TRAIT_ICONS), "tr_k": len(traits), "tr_other": 0, "tr_over": max(0, len(traits) - TRAIT_ICONS),
          "can": key in OS_CAN, "dec": medals, "dates": set(), "fromdiv": False, "medals": 0, "held": set(), "ul": True,
          "lines": [(fam, sa) for date, fam, words, subject, sa in OS_LINES.get(key, [])], "count": "0 of 1 chosen", "states": "0", "vps": "0"}
    if st["rank"] == 1:
        st["status"] = 2
    st.update(more)
    return st


def os_scene_state(state_name, key, rows, picked, names, filter_value, st, note):
    """One state of the scene: the file of <key> in <st>, the list of <rows> with <picked> chosen."""
    window = "mod1440_records_of"
    count, only, row_samples, images = os_rows(rows, picked, names)
    hide = [name for name, test in OF_SCENE["shows"].items() if not test(st)]
    place = {}
    if st["chain"]:
        place = dict((name, [x, y + OF_DY]) for name, (x, y) in OF_SCENE["low_at"].items())
    subs = st.get("sub_rows", [])
    sub_rows = [{"names": names, "can": k in OS_CAN} for k in subs]
    sub_only = dict((name, [i for i, r in enumerate(sub_rows) if test(r)]) for name, test in OF_SCENE["sub_shows"].items())
    sub_samples = {"of_sub_name": ["§Y%s§!" % OS_PEOPLE[k][0] for k in subs],
                   "of_sub_army": [OS_PEOPLE[k][2] for k in subs if names],
                   "of_sub_army_n": ["army of %d divisions" % OS_PEOPLE[k][6] for k in subs if not names],
                   "of_sub_div": [str(OS_PEOPLE[k][6]) for k in subs], "of_sub_won": [str(OS_PEOPLE[k][7]) for k in subs],
                   "of_sub_lost": [str(OS_PEOPLE[k][8]) for k in subs], "of_sub_skill": [str(OS_PEOPLE[k][3]) for k in subs]}
    frames = {"of_show_" + [f[1] for f in OF_FILTERS if f[0] == filter_value][0]: 2, "of_names": 2 if names else 1}
    rack = dict(("of_c_rack_%d" % k, 2) for k in range(st["dec"]))
    traits = OS_PEOPLE[key][5]
    file_images = dict(("of_c_tr_%d" % k, "GFX_trait_" + trait) for k, trait in enumerate(traits[:TRAIT_ICONS]))
    file_images.update(("of_row_tr_%d" % t, v) for t, v in [(t, images["of_row_tr_%d" % t]) for t in range(TRAIT_ICONS)])
    return {
        "name": state_name, "_note": note,
        "rows": {"of_grid": count, "of_c_gface_grid": 1, "of_c_army_grid": 1 if st["mode"] in (1, 2) and names else 0, "of_c_subs_grid": len(subs)},
        "hide": {window: hide}, "place": {window: place}, "frames": {window: dict(frames, **rack)},
        "only": {"mod1440_records_officer_row": only, "mod1440_records_of_sub_row": sub_only},
        "images": {window: dict((k, v) for k, v in file_images.items() if k.startswith("of_c_")),
                   "mod1440_records_officer_row": dict((k, v) for k, v in file_images.items() if k.startswith("of_row_"))},
        "samples": {window: dict(os_file(key, st), of_count="§g%d listed§!" % (23 if filter_value != 6 else len(rows))),
                    "mod1440_records_officer_row": row_samples, "mod1440_records_of_sub_row": sub_samples,
                    "mod1440_records_of_c_army_row": {"of_c_army_name": OS_PEOPLE[key][2] or ""}},
    }


def officer_scene(place, crop, shot, back, setup):
    page_rows = [(k, 0) for k in OS_PAGE]
    rundstedt = os_state("rundstedt", fm=1, can=True, dec=1, dates={"lvl"}, states="2", vps="3", words={
        "of_c_army_div": "7 divisions", "of_c_army_bat": "98 battalions",
        "of_c_rep": "§YWalter Model§!  §g·  army group of 3 armies§!", "of_c_rep_n": "§YWalter Model§!  §g·  §!OKH - Westen", "of_c_loc": "§YWestfalen§!  §g·  HQ in Rheinland§!",
        "of_c_p_l_div": "7", "of_c_p_l_bat": "98", "of_c_p_l_fight": "0", "of_c_p_l_ent": "4%", "of_c_p_l_bp": "0",
        "of_c_p_l_inf": "6", "of_c_p_l_arm": "0", "of_c_p_l_mot": "1", "of_c_p_l_mech": "0", "of_c_p_l_oth": "0", "of_c_p_l_eq": "92%",
        "of_c_o_lvl": "28 September, 1938", "of_c_dec_last": "§gKnight's Cross, 12 March, 1939§!"})
    names_off = dict(rundstedt, names=False, words=dict(rundstedt["words"], of_c_army_n="Army of 7 divisions"))
    model = os_state("model", count="2 of 2 chosen", dates={"since", "prom"}, states="3", vps="9", sub_rows=["bock", "rundstedt", "kluge"], words={
        "of_c_army_grp": "Army group of 3 armies", "of_c_army_div": "28 divisions", "of_c_army_bat": "392 battalions",
        "of_c_rep_hc": "§gHigh Command§!", "of_c_rep_hc_grp": "§gHigh Command  ·  his army group of 3 armies§!", "of_c_loc": "§YWestfalen§!  §g·  HQ in Hannover§!",
        "of_c_ch_since": "§gsince 6 April, 1939§!", "of_c_ch_div": "28", "of_c_ch_won": "4", "of_c_ch_lost": "1",
        "of_c_m_since": "8 July, 1936", "of_c_m_prom": "12 August, 1936"})
    kleist = os_state("kleist", fm=1, plan_none=False, states="1", vps="1", words={
        "of_c_army_div": "10 divisions", "of_c_army_bat": "118 battalions",
        "of_c_rep": "§YWilhelm Ritter von Leeb§!  §g·  army group of 2 armies§!",
        "of_c_rep_n": "§YWilhelm Ritter von Leeb§!  §g·  §!Heeresgruppe Nord",
        "of_c_loc": "§YSchlesien§!  §g·  HQ in Niederschlesien§!",
        "of_c_p_l_div": "10", "of_c_p_l_bat": "118", "of_c_p_l_fight": "0", "of_c_p_l_plan": "34%", "of_c_p_l_ent": "0%", "of_c_p_l_bp": "1",
        "of_c_p_l_inf": "2", "of_c_p_l_arm": "4", "of_c_p_l_mot": "3", "of_c_p_l_mech": "1", "of_c_p_l_oth": "0", "of_c_p_l_eq": "87%"})
    # E2 fix round 2: an army under the High Command (the capacity check left Cranz out of Model's army group)
    cranz = os_state("cranz", hq=False, words={
        "of_c_army_div": "3 divisions", "of_c_army_bat": "27 battalions", "of_c_rep_hc": "\u00a7gHigh Command\u00a7!",
        "of_c_loc_nohq": "\u00a7YPomorze\u00a7!  \u00a7g\u00b7  HQ not deployed\u00a7!",
        "of_c_p_l_div": "3", "of_c_p_l_bat": "27", "of_c_p_l_fight": "0", "of_c_p_l_ent": "12%", "of_c_p_l_bp": "0",
        "of_c_p_l_inf": "3", "of_c_p_l_arm": "0", "of_c_p_l_mot": "0", "of_c_p_l_mech": "0", "of_c_p_l_oth": "0", "of_c_p_l_eq": "96%"})
    states = [
        os_scene_state("page", "rundstedt", page_rows, "rundstedt", True, 1, rundstedt,
                       "Filter Army, Gerd von Rundstedt chosen: a general with an army (Army 2) in Walter Model's army group; Army names on."),
        os_scene_state("traits", "rundstedt", page_rows, "rundstedt", True, 1, rundstedt,
                       "The same as page; the trait tooltip is drawn over the render by scratch/phases/E2/build/figures.py (the renderer draws no tooltip)."),
        os_scene_state("marshal", "model", OS_OOB, "model", True, 6, model,
                       "Filter Order of battle: three army groups with their generals indented, the armies under the High Command, the fleets; "
                       "Walter Model chosen: the Chain of command card, the three cards under it 62 lower, 5 diary lines."),
        os_scene_state("unlinked", "cranz", OS_OOB, "cranz", True, 6, cranz,
                       "E2 fix round 2: filter Order of battle, Friedrich-Carl Cranz chosen: his army I. SS-Standarten serves in no army group; "
                       "his 3 divisions share Pomorze with Model's armies, whose 28 divisions Leeb's and Blaskowitz's armies fill, so he stands "
                       "with the armies under the High Command and his file says Reports to High Command."),
        os_scene_state("units", "kleist", page_rows, "kleist", True, 1, kleist,
                       "Ewald von Kleist chosen: a panzer army under Leeb with a battle plan (planning 34%), the Command table."),
        os_scene_state("names_off", "rundstedt", page_rows, "rundstedt", False, 1, names_off,
                       "Army names off (an unpatched hoi4.exe): each army by its divisions, in the rows and the file."),
    ]
    default = states[0]
    window = "mod1440_records_of"
    return {
        "phase": "E2", "file": "mod1440_records.gui", "screenshot": shot,
        "windows": [dict(place, name=window, rows=default["rows"],
                         listRows={"of_grid": "mod1440_records_officer_row", "of_c_gface_grid": "mod1440_records_of_c_gface_row",
                                   "of_c_army_grid": "mod1440_records_of_c_army_row", "of_c_subs_grid": "mod1440_records_of_sub_row"},
                         hide=default["hide"][window], frames=default["frames"][window], images=default["images"][window],
                         _note="E2 round 2: the page state (scene states page, traits, marshal, units, names_off: render_gui.py --state). Portraits "
                               "are the renderer's unknown leader: in the game each serving officer's row, his file and the chain card draw his own "
                               "face (E7, image = portrait)."),
                    {"name": "mod1440_records_of_c_gface_row", "skip": True},
                    {"name": "mod1440_records_of_c_army_row", "skip": True},
                    {"name": "mod1440_records_of_sub_row", "skip": True, "only": default["only"]["mod1440_records_of_sub_row"]},
                    {"name": "mod1440_records_officer_row", "skip": True, "only": default["only"]["mod1440_records_officer_row"],
                     "images": default["images"]["mod1440_records_officer_row"]}],
        "samples": default["samples"],
        "states": states,
        "setup": setup,
        "teardown": [{"clickWidget": "mod1440_records_of/of_tab_0", "wait": 0.8}] + back,
        "expect": ["mod1440_records_of/of_close", "mod1440_records_of/of_sort_skill", "mod1440_records_of/of_show_oob", "mod1440_records_of/of_names"],
        "crop": crop,
        "manual": ["Battles won and lost, states and victory points taken: they need fighting; a marshal's battles under him need a general's battle",
                   "A general the game made up: he shows the unknown leader",
                   "A captured general, an admiral's ship kinds: they need a war or a fleet",
                   "Two army groups with divisions in one state: the likely link (decision 6)"],
        "checklist": OFFICERS_CHECKLIST,
    }


OFFICERS_CHECKLIST = [
    "1. The page in the steel look: the filters' card (14,116 1006x46) with seven buttons All ... Order of battle and, behind a rule, the gold "
    "checkbox 'Army names'; the list's card (14,168 1006x1038) with the column heads in its head band (Officer, 'N listed', Skill, the four "
    "level icons, Traits, Div, Won, Lost, Medals); 20 rows of 48 in sight, the list scrolls to its end with the wheel; the file in five steel "
    "cards at x 1026, 640 wide; the title strip and tabs unchanged",
    "2. Army name (1.19.4.1, patched): with Army names ticked, a general's row reads 'General  .  <army name>' and his file's dark field shows "
    "the army's name in white; compare three generals with the army names in the game's army bar (hover the army's badge). Untick: 'army of N "
    "divisions' in the rows, 'Army of N divisions' in the file; Army Readiness's Army names button shows the same setting (one switch). Note "
    "what a field marshal leading an army group reads (his rows say 'Army group of N armies' and never ask the property)",
    "3. Chain of command: effect mod1440_chk_e2_oob (tools/check_effects.py) and read game.log: for each general with troops, his state and "
    "count, and for each field marshal leading an army group 'num_units_in_state' in that state. Write down whether a marshal's "
    "num_units_in_state counts his generals' divisions (state method) and, from the same effect, whether is_leading_army_in_province with "
    "include_field_marshal = yes is true for the general's provinces (province method) and whether 'province = var:' is accepted",
    "4. Without an army group at the start: form one (select two armies, create an army group, assign a field marshal), run one day: filter "
    "Order of battle lists the marshal with his generals indented under him, then the armies under the High Command, then the fleets; compare "
    "with the game's theatre boxes (army group letter, armies by number); move a general to another army group, one day: he moves too",
    "5. The marshal's file: the Chain of command card (Under his command: divisions = his num_units, Won/Lost of his armies since the build "
    "ran, 'since <date>'), up to five generals with face, name (click: his file), army, Div, Won, Lost, Skill, the green mark; Traits, "
    "Service record and the diary stand 62 lower and the diary shows 5 lines. Click a general's name: his file, 'Reports to <marshal>  .  "
    "army group of N armies' (click: the marshal's file)",
    "6. A battle counted for a marshal: effect mod1440_chk_e2_battle (a won and a lost battle of a general linked to a marshal through the "
    "hooks' own effects), then mod1440_chk_e2_log: the marshal's gwon and glost are 1 each and his chain card's line shows them. With "
    "fighting: whether a field marshal gets on_army_leader_won_combat himself when one of his generals fights (his own Won rises too: write "
    "it down; Witzleben read Won 2 in the user's game)",
    "7. Traits: 'N of M chosen' against the trait tree (num_assigned_traits against the chosen traits, num_max_traits against the slots: Model "
    "2, Rundstedt 1); the green mark in the row and 'a trait can be chosen' in the file against the game's own marker on the general (a leader "
    "with free experience and a slot); mod1440_chk_e2_log prints both numbers and whether he has a free slot for every leader",
    "8. Trait tooltips: hover a trait icon in a row and an icon and a name in the file: the trait's name in yellow, its kind, its effects with "
    "the game's own names in green or red, and its description; compare Cautious and Old Guard with the game's own trait tooltip in the "
    "general's window; newlines and colours must render (no '\\n' or section signs shown). Another mod's trait: 'its effects are in the game's "
    "own tooltip'",
    "9. Command card of a general: Divisions, Battalions, In battle (tooltip attacking/defending), Planning ('no battle plan' while he has "
    "none; draw a battle plan, wait two days: the percentage against the army badge's planning bar), Entrenchment, Battle plans, Infantry, "
    "Armoured (against the division badges of his army: a panzer division counts), Motorised, Mechanised, Other kinds, Equipped (against Army "
    "Readiness's Equipped of the same army)",
    "10. Stands in: the state where most of his divisions stand and 'HQ in <state>' (or 'HQ not deployed') as Army Readiness's row says; the "
    "go-to button and Show on map move the camera there",
    "11. Equipment: the Records close and Army Readiness opens with that general's army chosen (its row lit, the equipment list of the army)",
    "12. Service record: the banded table (Battles won ... Points lost; Commissioned, Promoted to field marshal for a marshal only, Last skill "
    "level, From a division, Decorations); Award... shows the country's medals over the service record and the diary (two columns of plates, "
    "rows of 60); award one: the rack shows it at 0.6 with its name and date after it and in the tooltip; Take back last",
    "13. An admiral (Raeder): manoeuvring and coordination icons in the level row, 'Fleet' and 'N ships' in the field, Ships and the four ship "
    "kinds in the Command table; no Reports to, no Stands in, no Equipment",
    "14. error.log: no line that names the mod, no 'invalid scope for var' (mod1440_of_fm, mod1440_of_c_fm, mod1440_of_c_loc, mod1440_of_c_hq), "
    "no unknown trigger is_promoted_from_unit, no 'Not a valid value', no 'Could not find sprite type' (GFX_1440p_OF_*, GFX_1440p_SG_rule_2x30, the "
    "new hit, stripe and pick sprites), no missing localisation mod1440_tre_*",
    # --- E7 ---
    "E7: every row's face and the file's face are the officer's own as the game's Officer Corps shows him; the chain card's faces at 23x31",
]
# --- end E2 round 2 ---


# --- E3 round 2 --- the Government page's scene: the user's campaign on the day the build comes (Germany, 24 November 1939,
# party support back-filled from National Figures' series 30), a new game on 1 May 1943 after a change of the ruling party at
# ten years (state "later"), and the heads panel open over it (state "panel"), as the design's figures draw them
# (scratch/phases/E3/work/make_layout.py: the same made-up support).
GS_KEYS = [(0, 40, 35, 10, 15), (8, 52, 22, 6, 20), (16, 63, 6, 2, 29), (28, 70, 0.4, 0.3, 29.3), (46, 72.4, 0.3, 0.2, 27.1),
           (66, 76, 0.4, 0.3, 23.3), (78, 54, 1, 1, 44), (80, 44, 3, 1, 52), (88, 38, 9, 3, 50)]
GS_GROUPS = [group for word, group in IDEOLOGIES]


def gs_series(n, keys, seed=11):
    """Made-up party support from January 1936, month by month, summing to 100 (the design's figures)."""
    import random
    rng = random.Random(seed)
    out = dict((g, []) for g in GS_GROUPS)
    for i in range(n):
        for (m0, *a), (m1, *b) in zip(keys, keys[1:]):
            if m0 <= i <= m1:
                t = (i - m0) / float(m1 - m0 or 1)
                t = t * t * (3 - 2 * t)
                vals = [x + (y - x) * t for x, y in zip(a, b)]
                break
        vals = [max(0.0, v + rng.uniform(-1.2, 1.2) * (v > 3)) for v in vals]
        s = sum(vals)
        for g, v in zip(GS_GROUPS, vals):
            out[g].append(round(100 * v / s, 1))
    return out


def gs_states():
    page = gs_series(47, GS_KEYS[:5])
    page["fascism"][-1], page["neutrality"][-1], page["democratic"][-1], page["communism"][-1] = 72.4, 27.1, 0.3, 0.2
    later = gs_series(89, GS_KEYS)
    return {
        "page": {"n": 47, "span": 60, "series": page, "full_from": 46, "ruling": ["fascism"] * 47, "heads": [(0, 47, "Adolf Hitler")],
                 "elections": [], "start_year": 1936},
        "later": {"n": 89, "span": 120, "series": later, "full_from": 0, "ruling": ["fascism"] * 80 + ["neutrality"] * 9,
                  "heads": [(0, 79, "Adolf Hitler"), (79, 80, "Ludwig Beck"), (80, 89, "Kurt von Hammerstein-Equord")], "elections": [87],
                  "start_year": 1936},
    }


def gs_chart(st):
    """The chart of state st as script draws it: rows, only, place and hide of the dots, the band, the years, the spans,
    the ticks and the shares at the lines' ends (the card's coordinates, mod1440_gv_chart)."""
    span, n = st["span"], st["n"]
    step, dot = dict((s, (p, d)) for s, p, d, c in GV_RANGES)[span]
    first = max(0, n - span)
    shown = n - first
    px0, py0 = GV_PLOT[0] - GV_CARDS["parties"][0], GV_PLOT[1] - GV_CARDS["parties"][1]
    top = GV_PLOT[3] - dot // 2
    at = (step - dot) // 2
    rows, only, place, hide, windows = {}, {}, {}, [], []
    for s, p_, d_, c_ in GV_RANGES:
        for p in ["0", "1", "2", "3", "r"]:
            rows["gv_dots_%s_%d" % (p, s)] = shown if s == span else 0
        rows["gv_band_%d" % s] = shown if s == span else 0
    for p, g in enumerate(GS_GROUPS):
        row = "mod1440_records_gv_dot_%d_%d" % (p, span)
        drawn, pos = [], []
        for k in range(shown):
            i = first + k
            if i < st["full_from"] and g != st["ruling"][i]:
                continue
            if g == st["ruling"][i]:
                continue
            drawn.append(k)
            pos.append([at, round(top - st["series"][g][i] * GV_PX)])
        only[row] = {"gv_dot%d_%d" % (p, span): drawn}
        place[row] = {"gv_dot%d_%d" % (p, span): pos}
    row = "mod1440_records_gv_dot_r_%d" % span
    only[row], place[row] = {}, {}
    for gi, g in enumerate(GS_GROUPS, start=1):
        widget = "gv_dotr%d_%d" % (gi, span)
        ks = [k for k in range(shown) if st["ruling"][first + k] == g]
        only[row][widget] = ks
        place[row][widget] = [[at, round(top - st["series"][g][first + k] * GV_PX)] for k in ks]
    row = "mod1440_records_gv_band_%d" % span
    only[row] = dict(("gv_cell%d_%d" % (gi, span), [k for k in range(shown) if st["ruling"][first + k] == g]) for gi, g in enumerate(GS_GROUPS, start=1))
    windows += [{"name": "mod1440_records_gv_dot_%s_%d" % (p, s), "skip": True} for s, a, b, c in GV_RANGES for p in ("0", "1", "2", "3", "r")]
    windows += [{"name": "mod1440_records_gv_band_%d" % s, "skip": True} for s, a, b, c in GV_RANGES]
    card_place, samples = {}, {}
    # the years
    slot = 0
    for k in range(1, shown):
        i = first + k
        if i % 12 == 0 and slot < GV_YEARS:
            card_place["gv_year_%d" % slot] = [px0 + k * step - 20, 456 - GV_CARDS["parties"][1]]
            card_place["gv_ymark_%d" % slot] = [px0 + k * step, py0 + GV_PLOT[3]]
            samples["gv_year_%d" % slot] = str(st["start_year"] + i // 12)
            slot += 1
    hide += ["gv_year_%d" % k for k in range(slot, GV_YEARS)] + ["gv_ymark_%d" % k for k in range(slot, GV_YEARS)]
    # who governed: his name where the span is wide enough
    s = 0
    for start, end, name in st["heads"]:
        a, b = max(start, first) - first, min(end, n) - first
        if b <= 0:
            continue
        card_place["gv_span_%d" % s] = [px0 + 6 + a * step, GV_BAND_Y - GV_CARDS["parties"][1]]
        if (b - a) * step < GV_SPAN_NAME:
            hide.append("gv_span_%d" % s)
        else:
            samples["gv_span_%d" % s] = name
        s += 1
    hide += ["gv_span_%d" % k for k in range(s, GV_SPANS)]
    # the elections
    t = 0
    for e in st["elections"]:
        if e > first:
            card_place["gv_tick_%d" % t] = [px0 - 1 + (e - first) * step, GV_BAND_Y - GV_CARDS["parties"][1] - 4]
            t += 1
    hide += ["gv_tick_%d" % k for k in range(t, GV_TICKS)]
    # the shares at the lines' ends, pushed apart
    foot = py0 + GV_PLOT[3]
    last = dict((g, st["series"][g][n - 1]) for g in GS_GROUPS)
    centre = dict((g, foot - v * GV_PX) for g, v in last.items())
    low = foot + 4
    for g in sorted(GS_GROUPS, key=lambda g: -centre[g]):
        y = min(centre[g], low)
        centre[g] = y
        low = y - GV_LABEL_GAP
    lx = px0 + shown * step + step // 2 + dot // 2 + 6 - step
    for p, g in enumerate(GS_GROUPS):
        card_place["gv_end_%d_sw" % p] = [lx, round(centre[g] - 3)]
        card_place["gv_end_%d" % p] = [lx + 9, round(centre[g] - 11)]
        card_place["gv_end_%d_lt" % p] = [lx + 9, round(centre[g] - 11)]
        samples["gv_end_%d" % p] = "%d%%" % last[g]
        hide.append("gv_end_%d" % p if last[g] < 1 else "gv_end_%d_lt" % p)
    return rows, only, place, hide, card_place, samples, windows


def gs_parties(st):
    """The table and the results bar: the rows moved to their ranks, the bar's layers, today's shares and the change in a year."""
    n = st["n"]
    now = dict((g, st["series"][g][n - 1]) for g in GS_GROUPS)
    order = sorted(GS_GROUPS, key=lambda g: (-now[g], GS_GROUPS.index(g)))
    rank = dict((g, r) for r, g in enumerate(order))
    first_row = 218 - GV_CARDS["parties"][1]
    hx = 568 - GV_CARDS["parties"][0]
    place, hide, fills, samples = {}, [], {}, {}
    xs = {"sw": hx, "ic": hx + 12, "name": hx + 52, "who": hx + 52, "now": hx + 264, "nows": hx + 264, "dy": hx + 320, "dyn": hx + 320}
    offs = {"sw": 4, "ic": 7, "name": 2, "who": 24, "now": 12, "nows": 12, "dy": 13, "dyn": 13}
    names = {"fascism": ("Nationalsozialistische Deutsche Arbeiterpartei", "Adolf Hitler"),
             "democratic": ("Deutsche Zentrumspartei - Sozialdemokratische Partei Deutschlands", "Konrad Adenauer"),
             "communism": ("Kommunistische Partei Deutschlands - Kommunistische Partei Opposition", "Wilhelm Pieck"),
             "neutrality": ("Deutschnationale Volkspartei", "Kurt von Hammerstein-Equord")}
    for p, g in enumerate(GS_GROUPS):
        y = first_row + GV_SEAT * rank[g]
        for part, x in xs.items():
            place["gv_pt_%d_%s" % (p, part)] = [x, y + offs[part]]
        samples["gv_pt_%d_name" % p] = names[g][0]
        samples["gv_pt_%d_who" % p] = "§Y%s§!" % names[g][1]
        samples["gv_pt_%d_now" % p] = "%d%%" % round(now[g])
        samples["gv_pt_%d_nows" % p] = "%.1f%%" % now[g]
        hide.append("gv_pt_%d_%s" % (p, "nows" if now[g] >= 1 else "now"))
        back = st["series"][g][n - 13] if n > 12 and (n - 13) >= st["full_from"] else None
        if back is None:
            hide.append("gv_pt_%d_dy" % p)
        else:
            samples["gv_pt_%d_dy" % p] = "%+.1f" % (now[g] - back)
            hide.append("gv_pt_%d_dyn" % p)
        cum = sum(now[h] for h in GS_GROUPS if rank[h] <= rank[g])
        for r in range(4):
            name = "gv_today_%d_%d" % (r, p)
            if r != rank[g]:
                hide.append(name)
            else:
                fills[name] = [min(1.0, cum / 100.0)]
    place["gv_pt_pick"] = [hx, first_row + GV_SEAT * rank[st["ruling"][-1]]]
    return place, hide, fills, samples


GS_CABINET = [("Martin Heidegger", "Post-Metaphysical Philosopher", "6 July, 1936", None),
              ("Ludwig Mueller", "Reichsbischof", "5 February, 1936", None),
              ("Walther Funk", "Reich Minister of Economy", "15 April, 1936", "GFX_idea_walther_funk"),
              ("Fritz Todt", "Reich Engineer", "2 March, 1937", "GFX_portrait_GER_fritz_todt_small"),
              ("Konstantin von Neurath", "Reich Minister of Foreign Affairs", "1 January, 1936", "GFX_portrait_GER_konstantin_von_neurath_small")]
GS_HIGH = [("Wilhelm Keitel", "Army Drill (Expert)", "4 March, 1936", UNKNOWN),
           ("Erich Raeder", "Decisive Battle (Expert)", "8 August, 1936", "GFX_portrait_GER_erich_raeder"),
           ("Albert Kesselring", "Air Reformer (Expert)", "12 May, 1936", "GFX_portrait_GER_albert_kesselring"),
           ("Heinz Guderian", "Blitzkrieg Theorist", "9 December, 1938", "GFX_portrait_GER_heinz_guderian"),
           ("Hugo Sperrle", "Close Air Support (Expert)", "20 October, 1939", UNKNOWN),
           ("Ferdinand Schörner", "Infantry (Expert)", "8 July, 1937", UNKNOWN),
           ("Erwin Rommel", "Armor (Genius)", "9 April, 1939", "GFX_portrait_GER_erwin_rommel")]
GS_DIARY = [("1939.10.20", "Appointed", "Hugo Sperrle"), ("1939.4.9", "Appointed", "Erwin Rommel"), ("1938.12.9", "Appointed", "Heinz Guderian"),
            ("1937.7.8", "Appointed", "Ferdinand Schörner"), ("1937.3.2", "Appointed", "Fritz Todt"), ("1937.3.2", "Left office", "Hjalmar Schacht"),
            ("1936.8.8", "Appointed", "Erich Raeder"), ("1936.7.6", "Appointed", "Martin Heidegger")]
GS_UPGRADES_DONE = {0, 1, 6, 7, 11, 16}
GS_OPERATIVES = [("Erwin Lahousen", "Wotan", "build_intel_network", "Kent", "ENG", "network 41%"),
                 ("Nikolaus Ritter", "Dr. Rantzau", "build_intel_network", "Ile de France", "FRA", "network 64%"),
                 ("Hermann Giskes", "Falke", "counter_intelligence", "German Reich", "GER", None),
                 ("Paul Thümmel", "Holm", "propaganda", "Muntenia", "ROM", "network 18%")]
GS_KNOW = [("United Kingdom", "34%", "22%", "18%", "25%"), ("France", "41%", "36%", "12%", "28%"), ("Soviet Union", "9%", "6%", "3%", "4%")]
GS_HEADS = [("Kurt von Hammerstein-Equord", 4, "c", "since 3 September, 1942", "240 days", "38% to 61%", "71% to 44%", "1", True),
            ("Ludwig Beck", 4, "a", "12 August, 1942 – 3 September, 1942", "22 days", "29% to 38%", "78% to 71%", "0", True),
            ("Adolf Hitler", 1, "b", "before the record – 12 August, 1942", "2415 days on record", None, None, "0", False)]


def gs_panel_names():
    """Every widget of the heads panel and of Party support's chart, as government() names them (from the written page)."""
    return GS_NAMES


GS_NAMES = {"panel": [], "chart": []}


def government_scene_hide(state="page"):
    """What script hides in the government scene's state: page (24 November 1939), later (1 May 1943), panel."""
    st = gs_states()["later" if state in ("later", "panel") else "page"]
    hide = []
    later = state != "page"
    # the head of government
    hide += ["gv_face_fb", "gv_face_fb_flag"] + ["gv_face_fb_g%d" % g for g in range(1, 5)] if not later else ["gv_face"] + [
        "gv_face_fb_g%d" % g for g in (1, 2, 3)]
    hide += ["gv_leader_since"] if not later else ["gv_leader_since_old"]
    hide += ["gv_next"] if not later else ["gv_next_none"]
    if state == "panel":
        hide += GS_NAMES["chart"]
    else:
        hide += GS_NAMES["panel"]
        _rows, _only, _place, chart_hide, _cp, _s, _w = gs_chart(st)
        hide += chart_hide
        hide += ["gv_legend_bf" if later else "gv_legend", "gv_chart_none"]
        _p, party_hide, _f, _s2 = gs_parties(st)
        hide += party_hide
    if state == "panel":
        hide += ["gv_heads_newer", "gv_heads_older"]
        for k in range(HEADS_ROWS):
            p = "gv_hd_%d" % k
            every = [p, p + "_face", p + "_fb", p + "_days", p + "_rec", p + "_el"] + ["%s_t%s" % (p, t) for t in "abcd"]
            every += ["%s_pt%d" % (p, g) for g in range(1, 5)] + ["%s_gi_g%d" % (p, g) for g in range(1, 5)] + ["%s_fbg_g%d" % (p, g) for g in range(1, 5)]
            every += ["%s_%s%s" % (p, name, s) for name in ("stab", "ws") for s in ("", "_nr")]
            if k >= len(GS_HEADS):
                hide += every
                continue
            name, g, t, words, days, stab, ws, el, fb = GS_HEADS[k]
            keep = {p, p + "_el", "%s_t%s" % (p, t), "%s_pt%d" % (p, g), "%s_gi_g%d" % (p, g)}
            keep |= {p + "_fb", "%s_fbg_g%d" % (p, g)} if fb else {p + "_face"}
            keep.add(p + ("_rec" if t == "b" else "_days"))
            keep |= {"%s_stab_nr" % p, "%s_ws_nr" % p} if stab is None else {"%s_stab" % p, "%s_ws" % p}
            hide += [w for w in every if w not in keep]
    # the cabinet: Heidegger and Mueller without a picture (decision 2), Funk, Todt and Neurath by their small portraits
    for k, (name, role, since, sprite) in enumerate(GS_CABINET):
        hide += ["gv_adv_%d_big" % k, "gv_adv_%d_since_old" % k] + (["gv_adv_%d_face" % k] if sprite is None else ["gv_adv_%d_none" % k])
    hide.append("gv_adv_none")
    # the high command: every chief and member a general or an admiral, so the game draws their faces
    for k in range(len(OFFICES)):
        hide += ["gv_of_%d_%s" % (k, part) for part in ("face", "big", "none", "since_old", "slot", "vacant")]
    for m in range(MEMBER_SLOTS):
        hide += ["gv_hc_%d_%s" % (m, part) for part in ("face", "big", "none", "since_old")]
    # the diary: every line names a person
    hide += ["gv_dl_none"] + ["gv_dl_%d_b" % k for k in range(GV_DIARY)]
    # the realm: in the Axis, two subjects, no overlord
    hide += ["gv_faction_none", "gv_sub_none", "gv_sub_head_r", "gv_realm_right_m1s1", "gv_realm_right_m1sn", "gv_realm_right_mns1"]
    # the agency: founded during the record; six upgrades at their highest level; the department active, decrypting
    hide += ["gv_ag_none", "gv_ag_since_old", "gv_op_none", "gv_cr_head_r0", "gv_cr_dec_none"]
    hide += ["gv_up_%d_dim" % n for n in GS_UPGRADES_DONE]
    return hide


def government_face_rows():
    """E7: the rows of the lists of the game's faces: every chief and member of the sample is a unit leader."""
    rows = dict(("gv_of_%d_gface_grid" % k, 1) for k in range(len(OFFICES)))
    rows.update(("gv_hc_%d_gface_grid" % k, 1) for k in range(MEMBER_SLOTS))
    return rows


def government_samples(state="page"):
    """The texts of the page in a state, by widget."""
    later = state != "page"
    st = gs_states()["later" if later else "page"]
    out = {"gv_leader": "Adolf Hitler" if not later else "Kurt von Hammerstein-Equord",
           "gv_party": "§YNSDAP§!, Nazism" if not later else "§YDNVP§!, Conservatism",
           "gv_party_long": "Nationalsozialistische Deutsche Arbeiterpartei" if not later else "Deutschnationale Volkspartei",
           "gv_leader_since": "since 3 September, 1942", "gv_rec": "1422 days" if not later else "240 days",
           "gv_election": "1:00, 5 March, 1933" if not later else "1:00, 7 March, 1943", "gv_next": "in 1407 days",
           "gv_support": "72.4%" if not later else "50.0%", "gv_stab": "71%" if not later else "61%", "gv_ws": "62%" if not later else "44%"}
    laws = [("War Economy", "Limited Exports", "Limited Conscription"), ("Partial Mobilisation", "Export Focus", "Limited Conscription")][later]
    for n, words in enumerate(laws):
        out["gv_law_%d" % n] = "§Y%s§!" % words
    if state != "panel":
        _rows, _only, _place, _hide, _cp, samples, _w = gs_chart(st)
        out.update(samples)
        _p, _h, _f, samples = gs_parties(st)
        out.update(samples)
        out.update({"gv_since_el": "0" if not later else "1", "gv_since_ch": "0" if not later else "1",
                    "gv_since_hi": "74.1%, 1939.6.1" if not later else "77.0%, 1941.6.1", "gv_since_mo": "47, 1 in full" if not later else "89, 89 in full",
                    "gv_legend_bf": "§gBefore 1 November, 1939 the record kept the ruling party only (National Figures, series 30).§!"})
    else:
        for k, (name, g, t, words, days, stab, ws, el, fb) in enumerate(GS_HEADS):
            p = "gv_hd_%d" % k
            out[p] = "§Y%s§!" % name
            out["%s_pt%d" % (p, g)] = ["NSDAP, Fascist", "DNVP, Conservatism"][g == 4]
            out["%s_t%s" % (p, t)] = words
            out[p + ("_rec" if t == "b" else "_days")] = "§g%s§!" % days
            if stab:
                out[p + "_stab"], out[p + "_ws"] = stab, ws
            out[p + "_el"] = el
    for k, (name, role, since, sprite) in enumerate(GS_CABINET):
        out.update({"gv_adv_%d_name" % k: "§Y%s§!" % name, "gv_adv_%d_role" % k: role, "gv_adv_%d_since" % k: "since " + since})
    out["gv_cabinet_right"] = "5 in office"
    # the heads panel's party lines and the band's names: as the game writes them for a head (short party name), whose
    # rows the panel draws only where the record has one
    for k in range(HEADS_ROWS):
        for g, (word, group) in enumerate(IDEOLOGIES, start=1):
            out.setdefault("gv_hd_%d_pt%d" % (k, g), "DNVP, %s" % word)
    for s in range(GV_SPANS):
        out.setdefault("gv_span_%d" % s, "Adolf Hitler")
    for k, (name, role, since, sprite) in enumerate(GS_HIGH):
        p = "gv_of_%d" % k if k < len(OFFICES) else "gv_hc_%d" % (k - len(OFFICES))
        out.update({p + "_name": "§Y%s§!" % name, p + "_role": role, p + "_since": "since " + since})
    out["gv_high_right"] = "7 in office"
    for k, (date, words, who) in enumerate(GS_DIARY):
        out.update({"gv_dl_%d_d" % k: date, "gv_dl_%d" % k: words, "gv_dl_%d_a" % k: "§Y%s§!" % who})
    out.update({"gv_realm_right_mnsn": "3 members, 2 subjects", "gv_faction": "Axis", "gv_faction_lead": "led by §YThe German Reich§!",
                "gv_ag_name": "Intelligence agency: §YAbwehr§!", "gv_ag_since": "founded 12 March, 1937",
                "gv_up_head_r": "%d of %d at their highest level" % (len(GS_UPGRADES_DONE), len(GV_UPGRADES)),
                "gv_op_h0": "Operatives  4 of 5", "gv_cr_enc": "50250", "gv_cr_def": "9", "gv_cr_dec": "§YUnited Kingdom§!  64%", "gv_cr_brk": "1"})
    for k, (name, c, a, nv, ai) in enumerate(GS_KNOW):
        out.update({"gv_kn_%d" % k: "§Y%s§!" % name, "gv_kn_%d_c" % k: c, "gv_kn_%d_a" % k: a, "gv_kn_%d_n" % k: nv, "gv_kn_%d_i" % k: ai})
    return out


def government_scene(place, crop, shot, back, setup):
    window = "mod1440_records_gv"
    face_rows = government_face_rows()
    states = {}
    for state in ("page", "later", "panel"):
        st = gs_states()["later" if state != "page" else "page"]
        rows = dict({"gv_fac_grid": 3, "gv_sub_grid": 2, "gv_op_grid": len(GS_OPERATIVES)}, **face_rows)
        only, row_place, card_place, fills, windows = {}, {}, {}, {}, []
        if state != "panel":
            chart_rows, only, row_place, _h, card_place, _s, windows = gs_chart(st)
            rows.update(chart_rows)
            party_place, _h2, fills, _s2 = gs_parties(st)
            card_place.update(party_place)
        else:
            rows.update(("gv_dots_%s_%d" % (p, s), 0) for s, a, b, c in GV_RANGES for p in ("0", "1", "2", "3", "r"))
            rows.update(("gv_band_%d" % s, 0) for s, a, b, c in GV_RANGES)
            windows = [{"name": "mod1440_records_gv_dot_%s_%d" % (p, s), "skip": True} for s, a, b, c in GV_RANGES for p in ("0", "1", "2", "3", "r")]
            windows += [{"name": "mod1440_records_gv_band_%d" % s, "skip": True} for s, a, b, c in GV_RANGES]
        frames = {"gv_heads_btn": 2 if state == "panel" else 1}
        frames.update(("gv_range_%d" % s, 2 if s == st["span"] else 1) for s, a, b, c in GV_RANGES)
        images = {"gv_face": "GFX_portrait_GER_adolf_hitler"}
        for k, (name, role, since, sprite) in enumerate(GS_CABINET):
            if sprite:
                images["gv_adv_%d_face" % k] = sprite
        for n, sprite in enumerate([("GFX_idea_war_economy", "GFX_idea_limited_exports", "GFX_idea_limited_conscription"),
                                    ("GFX_idea_partial_economic_mobilisation", "GFX_idea_export_focus", "GFX_idea_limited_conscription")][state != "page"]):
            images["gv_law_%d_pic" % n] = sprite
        op_only = {"gv_op_home": [2], "gv_op_net": [0, 1, 3], "gv_op_idle": [], "gv_op_where": [0, 1, 3], "gv_op_country": [2]}
        for mission, frame_n, title in MISSIONS:
            ks = [k for k, o in enumerate(GS_OPERATIVES) if o[2] == mission]
            op_only["gv_op_m_" + mission] = ks
            op_only["gv_op_t_" + mission] = ks
        op_only["gv_op_t_none"] = []
        states[state] = {"rows": rows, "only": dict(only, mod1440_records_gv_op_row=op_only), "place": dict(row_place, **{window: card_place}),
                         "hide": {window: government_scene_hide(state)}, "fills": {window: fills}, "frames": {window: frames},
                         "images": {window: images,
                                    "mod1440_records_gv_gface_row": {"gv_gface": [sprite for name, role, since, sprite in GS_HIGH]},
                                    "mod1440_records_gv_op_row": {"gv_op_face": ["GFX_portrait_unknown"] * 4}},
                         "samples": {window: government_samples(state),
                                     "mod1440_records_gv_op_row": {
                                         "gv_op_name": ["§Y%s§!" % o[0] for o in GS_OPERATIVES], "gv_op_country": ["§Y%s§!" % o[3] for o in GS_OPERATIVES if not o[5]],
                                         "gv_op_where": ["§Y%s§!" % o[3] for o in GS_OPERATIVES if o[5]],
                                         "gv_op_net": ["§g%s§!" % o[5] for o in GS_OPERATIVES if o[5]]},
                                     "mod1440_records_fac_row": {"gv_fac_row_name": ["German Reich", "German East Indies", "Gau Luxemburg"]},
                                     "mod1440_records_sub_row": {"gv_sub_row_name": ["Gau Luxemburg", "German East Indies"]}}}
        if state == "page":
            states[state]["windows"] = windows
    default = states["page"]
    rows_windows = [{"name": "mod1440_records_%s_row" % n, "skip": True} for n in ("fac", "sub", "gv_op")]
    rows_windows.append({"name": "mod1440_records_gv_gface_row", "skip": True, "images": default["images"]["mod1440_records_gv_gface_row"]})
    return {
        "phase": "E3", "file": "mod1440_records.gui", "screenshot": shot,
        "windows": [dict(place, name=window, rows=default["rows"],
                         listRows=dict({"gv_fac_grid": "mod1440_records_fac_row", "gv_sub_grid": "mod1440_records_sub_row", "gv_op_grid": "mod1440_records_gv_op_row"},
                                       **dict(dict((grid, "mod1440_records_gv_gface_row") for grid in face_rows),
                                              **dict(("gv_dots_%s_%d" % (p, s), "mod1440_records_gv_dot_%s_%d" % (p, s)) for s, a, b, c in GV_RANGES
                                                     for p in ("0", "1", "2", "3", "r")),
                                              **dict(("gv_band_%d" % s, "mod1440_records_gv_band_%d" % s) for s, a, b, c in GV_RANGES))),
                         hide=default["hide"][window], place=default["place"][window], fills=default["fills"][window],
                         frames=default["frames"][window], images=default["images"][window],
                         _note="Germany on 24 November 1939, the day the build comes to the user's save: party support back-filled from "
                               "National Figures' series 30 (the months before November 1939 hold the ruling party only), Heidegger and "
                               "Mueller without a picture (decision 2), every chief and member a general or an admiral, six upgrades done.")]
                   + [dict(w, **{k: v for k, v in (("only", default["only"].get(w["name"])), ("place", default["place"].get(w["name"]))) if v})
                      for w in default["windows"]]
                   + [dict(w, only=default["only"]["mod1440_records_gv_op_row"]) if w["name"] == "mod1440_records_gv_op_row" else w for w in rows_windows],
        "samples": default["samples"],
        "states": [dict(dict((k, v) for k, v in states[name].items() if k != "windows"), name=name, _note=note) for name, note in (
            ("later", "A new game on 1 May 1943 at ten years: the conservatives took power in August 1942 (Beck, then Hammerstein-Equord); "
                      "an election in March 1943 (the tick); the head of government without a portrait (E4's flag box)."),
            ("panel", "The same day with the heads panel open over Party support: three terms, Hitler's not recorded before the build."))],
        "setup": setup,
        "teardown": [{"clickWidget": "mod1440_records_gv/gv_tab_0", "wait": 0.8}] + back,
        "expect": ["mod1440_records_gv/gv_close", "mod1440_records_gv/gv_heads_btn"],
        "crop": crop,
        # the long names of the parties are cut in their fixed boxes (W28; design.json H10: the full name in the politics panel)
        "knownCuts": [{"widget": "%s/%s" % (window, widget), "text": text} for widget, text in (
            ("gv_party_long", "Nationalsozialistische Deutsche Arbeiterpartei"), ("gv_pt_0_name", "Nationalsozialistische Deutsche Arbeiterpartei"),
            ("gv_pt_1_name", "Deutsche Zentrumspartei - Sozialdemokratische Partei Deutschlands"),
            ("gv_pt_2_name", "Kommunistische Partei Deutschlands - Kommunistische Partei Opposition"))]
        # ... and the game's titles of the operatives' missions in theirs (the design's "Build Intel Net...")
        + [{"widget": "mod1440_records_gv_op_row/gv_op_t_%s" % mission, "text": words} for mission, words in (
            ("build_intel_network", "Build Intel Network"), ("quiet_network", "Quiet Intel Network"),
            ("counter_intelligence", "Counter Intelligence"), ("root_out_resistance", "Root Out Resistance"),
            ("diplomatic_pressure", "Diplomatic Pressure"), ("control_trade", "Control Trade"), ("boost_ideology", "Boost Ideology"))]
        # ... and a long country name under its flag, one line inside the tile's border (fix round 2)
        + [{"widget": "mod1440_records_%s_row/gv_%s_row_name" % (n, n), "text": "German East Indies"} for n in ("fac", "sub")],
        "manual": ["Several years of play with a change of ruling party and an election (the chart's band and tick, the heads panel's terms); "
                   "the user's own save of 24 November 1939 for the back-fill"],
        "checklist": GOVERNMENT_CHECKLIST,
    }


GOVERNMENT_CHECKLIST = [
    "The page in the steel look: seven steel cards (Head of government 540x446 and Party support 1106x446 on top, Cabinet 540x280, "
    "Faction and subjects 540x352, High command 540x376, In the War Diary 540x256, Intelligence 560x638), 6 apart; the window's ground, "
    "title strip and tabs unchanged",
    "Head of government: name in hoi_24header, the flag, party and ideology, the portrait at full size (a head with no portrait the game "
    "can name: the flag on the dark inset with the group's icon); the banded table of eight rows: Party / In office / On record / Last "
    "election / Next election against the politics panel, Party support against its pie, Stability and War support against the top bar. "
    "Fix round 1: no Traits strip (the head of government's traits are not shown)",
    "Fix round 1, the crash: open the Records on the user's save of 24 August 1940 (Road to 56) and click every tab and the Heads of "
    "government button: no crash; error.log has no 'Invalid trait ... mod1440_records.txt' and no 'Not a valid value ... mod1440_records.txt' "
    "line (the operatives' mission quiet_network is accepted)",
    "Laws in force: each kind with the law's own picture at 22x22 and its name, as the politics panel's law slots",
    "Party support, the table: the four parties sorted by support, the ruling party on the lighter plate, Now as the politics panel's pie "
    "(hover it), Year a dash until twelve months are recorded; the results bar above it in the parties' colours, largest first, its "
    "lengths as the shares (hover each colour)",
    "The chart, 5 years on the user's save of 24 November 1939 (or a save of the build before, one day played with this build): the "
    "ruling party's dots back to January 1936 from National Figures' series 30 (compare the dots' heights with National Figures' graph of "
    "'Ruling party popularity'), the other three only from the first month with this build; the legend 'Before ... the record kept the "
    "ruling party only'",
    "Effect mod1440_chk_gv_months (tools/check_effects.py): made-up months of party support over six years with a change of ruling party "
    "and an election; open the page: dots in the parties' colours (democratic blue 70,90,255, fascist brown 160,85,15 on the chart), the "
    "ruling party's dots on top, the shares at the lines' ends pushed apart, the years under the plot, the band in the ruling group's "
    "colour with the head's name where it fits (hover: name and dates), a white tick at the election; click 2 years, 5 years, 10 years: "
    "each redraws at once (the dots move by their y property in list rows: are they at their heights?), the chosen button gold; no "
    "stutter while the page is open (fifteen grids of up to 120 dots)",
    "Heads of government (the button in the Head of government card, frame 2 while open): the panel over Party support, newest first, "
    "today's head on the lighter plate, In office with days, Stability and War support 'from to' (compare today's head's second number "
    "with the top bar's stability and war support), 'not recorded' for terms before the build, Elections per term; Party support (or the "
    "button again) goes back to the chart; effect mod1440_chk_gv_leader: a new row the next day",
    "Cabinet: five seats of 48, each with portrait, name in yellow, role and 'since'; Heidegger and Mueller (Road to 56) with the unknown "
    "leader outline on the dark inset, its tooltip 'No picture...'; hover a name: the role and its effects with the game's names and values "
    "(compare with the advisor's own tooltip in the politics panel; Heidegger: Research Speed +5.00%, Daily Fascism Support +0.03, "
    "Construction Speed +2.50%)",
    "The German Reich seat is gone: '5 in office' on the user's save (persons only); effect mod1440_chk_gv_phantom logs every element of "
    "political_advisor ('MOD1440 gv phantom: ...'): write down what the country element is (its number, name, whether it is ROOT); "
    "error.log has no 'is_character: Invalid Scope' line in mod1440_p_adv_political_advisor_GER after a day",
    "Hire and dismiss (mod1440_chk_gv_hire, a day, then mod1440_chk_gv_fire, a day): the seat fills with his portrait, role and date, the "
    "War Diary card gets 'Appointed' and 'Left office' lines at its top",
    "High command: seven rows of 48, the four offices then the members; the game's face of each general or admiral (34x46); a vacant office "
    "shows the politics panel's own empty slot picture and 'vacant'; hover: the chief's trait and its effects",
    "In the War Diary: the government's eight newest lines (date, icon, words, person); All its lines opens the War Diary on the Government filter",
    "Faction and subjects: the faction's name, led by, member flags (four to a row, scrolls), Subjects with the overlord or 'none' "
    "(mod1440_chk_puppet: Denmark as a tile)",
    "Intelligence (mod1440_chk_gv_agency: an agency, two upgrades, an operative): the agency's name and 'founded <date>'; the 21 upgrade "
    "pictures, lit at their highest level and dimmed otherwise (compare with the agency's upgrade window; has_done_agency_upgrade of an "
    "upgrade with levels is true only at the highest); 'N of 21 at their highest level'",
    "Operatives: a row per operative with the game's face (image = portrait in a list row with change_scope over the game's operatives "
    "array: is it his face, as in the agency's operatives view?), name, code name, the mission's own icon and title, the flag and state of "
    "his operation and 'network N%' (compare with the map's intel network coverage of that country); 'at home' for counter-intelligence "
    "at home; 'not assigned' without a mission",
    "Cryptology: 'department active' or 'no department'; Our cipher strength and Cryptology defence level against the agency view "
    "(agency_crypto_defense_level, agency_decrypt_strength); Decrypting: the country and its progress against the cryptology tab's bar; "
    "Ciphers broken: the War Diary's cipher lines",
    "What we know of: the enemies at war first, then the majors; Civilian, Army, Navy and Air against the intelligence ledger's values for "
    "each (write down whether they read as percent)",
    "The @<country> forms with a country held in a variable (network_national_coverage@var:, decryption_progress@var:, *_intel@var:): "
    "error.log has no line about them after a daily round, and the numbers are not 0 where the game shows some (else the fallback of build.json)",
    "error.log: no line that names the mod, no 'Could not find sprite type' (GFX_1440p_GV_*, GFX_1440p_SG_face_none_46x47, "
    "GFX_1440p_SG_dim_44, GFX_idea_slot_*), no unknown trigger or effect has_done_agency_upgrade (or an 'Invalid' line naming an "
    "upgrade, an idea or a mission), is_cryptology_department_active, is_decrypting, operative_leader_mission, is_major, every_operative, is_subject",
]
# --- end E3 round 2 ---


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

    return {
        "war_diary": diary_scene(place, crop, shot, back),
        "officers": officer_scene(place, crop, shot, back, tab(1)),     # E2 round 2
        "government": government_scene(place, crop, shot, back, tab(2)),     # E3 round 2
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
    return out_gui, out_script, out_effects, hooks, dict({
        "common/scripted_effects/mod1440_portraits.txt": portrait_script + advisor_portraits()[0],
        "common/scripted_effects/mod1440_victory_points.txt": point_script,
    }, **trait_effect_files())     # E2 round 2: the effects of the traits, in the game's languages
