"""Reads the installed game and writes the tables of game content the Records window needs.

    python -I tools/make_game_tables.py            write tools/portraits_table.py, tools/victory_points_table.py and
                                                   tools/equipment_kinds_table.py
    python -I tools/make_game_tables.py --check    exit 1 when a table on disk differs from the game
    python -I tools/make_game_tables.py --mods     write tools/portraits_mods_table.py (the officers the mods of
                                                   the launcher's playset add) and
                                                   tools/victory_points_mods_table.py (the victory points of a
                                                   playset whose states are not the game's) and
                                                   tools/equipment_kinds_mods_table.py (its kinds of land equipment)

To be run again after a game update: tools/build_managers.py reads the tables, not the game.

    portraits_table.py        every character of common/characters with a portrait sprite: who can be a general,
                              an admiral or a head of government, and which sprite the game shows for each
    victory_points_table.py   every victory point of history/states: its province, state and value
    portraits_mods_table.py   the same as portraits_table.py for characters that mods add. Optional: the build
                              tool uses it when it is there. A name the loaded game does not know is not found
                              and logs nothing, so the lookup is harmless without those mods.
    victory_points_mods_table.py   the same as victory_points_table.py for a playset that brings states of its
                              own (Road to 56: 1143 states for the game's 1081, and other numbers for many).
                              Optional. Script counts the states of the loaded game and follows the points of
                              the map with that number, so the game's own table stays in use without those mods.
    equipment_kinds_table.py  the kinds of land equipment of Army Readiness: every archetype a land sub-unit needs,
                              with the sprite of its picture and that picture's size
    equipment_kinds_mods_table.py   the same for the playset, chosen in script by its number of states as the
                              victory points are. Optional.
    traits_table.py           every trait of a unit leader (common/unit_leader): who can have it and its icon
                              GFX_trait_<trait>, for the trait icons of the Officers page (e-officers-gov)
    traits_mods_table.py      (--mods) the traits the playset adds, and the game's traits it drops
    laws_table.py             the picture of every law (common/ideas, law = yes) for the Government page
    portraits_table.py also holds ADVISORS: the small portrait of each advisor and the first trait of each of his
    roles, by seat; portraits_mods_table.py the same for the characters of the playset.

Script cannot ask the game for a character's portrait or for the name of a province. It can ask whether a
character is a certain one (is_character) and who controls a province (province_controllers), so the mod
carries these two lists (wiki/Engine-Facts.md, X58 to X60).
"""
import glob
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guiparse  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNIT_ROLES = ("corps_commander", "field_marshal", "navy_leader")


def blocks(text):
    """The 'name = { ... }' blocks at the top level of a text."""
    out, i = [], 0
    for m in re.finditer(r"([A-Za-z_0-9.\-']+)\s*=\s*\{", text):
        if m.start() < i:
            continue
        depth, j = 1, m.end()
        while depth and j < len(text):
            depth += {"{": 1, "}": -1}.get(text[j], 0)
            j += 1
        out.append((m.group(1), text[m.end():j - 1]))
        i = j
    return out


def without_comments(text):
    return re.sub(r"#[^\n]*", "", text)


def portraits(game, by_effect=False, paths=None):
    """(character, file tag, army sprite, navy sprite, civilian sprite, roles) for every character with a sprite.
    by_effect: a character whose file gives him no role at all is taken as an officer too. That is how mods add
    generals: the character is defined bare, and an event gives him his command (add_corps_commander_role).
    paths: these files instead of the folder's (tools/check_playset.py reads a playset file by file)."""
    rows = []
    for path in paths if paths is not None else sorted(glob.glob(os.path.join(game, "common", "characters", "*.txt"))):
        tag = os.path.splitext(os.path.basename(path))[0]
        text = without_comments(io.open(path, encoding="utf-8-sig", errors="replace").read())
        for top, body in blocks(text):
            if top != "characters":
                continue
            for name, character in blocks(body):
                found = {}
                for kind in ("army", "navy", "civilian"):
                    m = re.search(r"\b%s\s*=\s*\{[^{}]*?\blarge\s*=\s*\"?(GFX_[A-Za-z0-9_\-]+)\"?" % kind, character)
                    if m:
                        found[kind] = m.group(1)
                roles = [role for role in UNIT_ROLES + ("country_leader",) if re.search(r"\b%s\s*=\s*\{" % role, character)]
                if by_effect and not roles and not re.search(r"\b(advisor|scientist)\s*=\s*\{", character):
                    roles = ["navy_leader"] if ("navy" in found and "army" not in found) else ["corps_commander"]
                # D2 fix round 3: a character of the game with an army or navy portrait and no command in his file
                # (an advisor such as Martin Bormann) can be given one by effect; the officers' lookup takes him too
                if not by_effect and not roles and ("army" in found or "navy" in found):
                    roles = ["officer_by_effect"]
                if found and roles:
                    rows.append((name, tag, found.get("army", ""), found.get("navy", ""), found.get("civilian", ""), " ".join(roles)))
    return rows


def playset(user):
    """(name, folder) of the mods of the launcher's playset, this mod left out. While a game check runs the
    harness has its own playset in place and keeps the user's in scratch/harness/dlc_load.backup.json."""
    path = os.path.join(ROOT, "scratch", "harness", "dlc_load.backup.json")
    if not os.path.isfile(path):
        path = os.path.join(user, "dlc_load.json")
    mods = []
    for rel in json.load(io.open(path, encoding="utf-8-sig")).get("enabled_mods", []):
        file = os.path.join(user, rel)
        if not os.path.isfile(file):
            continue
        text = io.open(file, encoding="utf-8-sig", errors="replace").read()
        name = re.search(r'^\s*name\s*=\s*"([^"]*)"', text, re.M)
        folder = re.search(r'^\s*path\s*=\s*"([^"]*)"', text, re.M)
        if not folder or not os.path.isdir(folder.group(1)):
            continue
        if os.path.isfile(os.path.join(folder.group(1), "tools", "make_game_tables.py")) or "hoi4-manager-pages" in rel:
            continue
        mods.append((name.group(1) if name else rel, folder.group(1)))
    return mods


def mod_portraits(game, user):
    """The characters the mods of the playset add to the game's own, and the names of the mods that add any."""
    from portraits_table import PORTRAITS
    known = set(row[0] for row in PORTRAITS)
    tags = country_tags(game)
    rows, used = [], []
    for name, folder in playset(user):
        added = 0
        for row in portraits(folder, by_effect=True):
            if row[0] in known:
                continue        # the game's own character: its sprite name is the game's, whatever picture a mod puts there
            known.add(row[0])
            # the file of a country: named after its tag (USA), or with the tag as a part of its name (AUGA_USA)
            source = row[1]
            if source not in tags:
                parts = [part for part in re.split(r"[^A-Za-z0-9]+", source) if part in tags]
                source = parts[0] if parts else "mod_" + re.sub(r"[^A-Za-z0-9]+", "_", source)
            rows.append((row[0], source) + row[2:])
            added += 1
        if added:
            used.append("%s: %d" % (name, added))
    return rows, used


def country_tags(game):
    """The tags of common/country_tags: a file of characters named after one holds that country's people."""
    tags = set()
    for path in glob.glob(os.path.join(game, "common", "country_tags", "*.txt")):
        text = without_comments(io.open(path, encoding="utf-8-sig", errors="replace").read())
        tags.update(re.findall(r"^\s*([A-Z][A-Z0-9]{2})\s*=", text, re.M))
    return tags


def victory_points(game, state_files=None, text_files=None, count=None):
    """(province, state, value) for every victory point that has a name. state_files, text_files: these files
    instead of the game's folders (a playset). count: a list that gets the number of states."""
    rows, states = [], 0
    for path in state_files if state_files is not None else sorted(glob.glob(os.path.join(game, "history", "states", "*.txt"))):
        text = without_comments(io.open(path, encoding="utf-8-sig", errors="replace").read())
        state = re.search(r"\bid\s*=\s*(\d+)", text)
        if not state:
            continue
        states += 1
        for m in re.finditer(r"victory_points\s*=\s*\{\s*(\d+)\s+([\d.]+)\s*\}", text):
            rows.append((int(m.group(1)), int(state.group(1)), int(float(m.group(2)))))
    names = set()
    for path in text_files if text_files is not None else glob.glob(os.path.join(game, "localisation", "english", "*.yml")):
        text = io.open(path, encoding="utf-8-sig", errors="replace").read()
        names.update(int(k) for k in re.findall(r"^\s*VICTORY_POINTS_(\d+):", text, re.M))
    seen, out = set(), []
    for province, state, value in sorted(rows):
        if province in names and province not in seen:     # a point without a name could not be written down
            seen.add(province)
            out.append((province, state, value))
    if count is not None:
        count.append(states)
    return out


def mod_victory_points(game):
    """The victory points of the launcher's playset when its states are not the game's: (the mods the states
    come from, the number of states, the rows), or None. The playset is read as the game loads it: a mod's
    replace_path empties the game's folder (tools/check_playset.py, View)."""
    from check_playset import View, playset as layers_of      # that tool imports this one
    layers, _unread, _source = layers_of(guiparse.user_dir())
    view = View(game, layers)
    files = view.files("history/states", ".txt")
    mods = sorted(set(layer.name for layer, _full, _rel in files.values() if layer is not view.game))
    if not mods:
        return None
    texts = []
    for layer in view.layers:
        for dirpath, _dirs, names in os.walk(os.path.join(layer.folder, "localisation")):
            texts += [os.path.join(dirpath, name) for name in names if name.lower().endswith("l_english.yml")]
    count, own = [], []
    rows = victory_points(game, [full for _key, (_layer, full, _rel) in sorted(files.items())], texts, count)
    victory_points(game, count=own)
    if count[0] == own[0]:
        print("the playset has states of its own, and as many as the game (%d): script could not tell the two maps apart" % own[0])
        return None
    return " + ".join(mods), count[0], rows


# ---------------------------------------------------------------- d2-readiness: the kinds of land equipment

# The kinds the Army Readiness page counts: every equipment archetype a land sub-unit asks for (a sub-unit with a
# "group", which ships and planes have not). These stand first, in the order of the logistics tab; the others
# follow by name. The page sorts its rows by the count, so this order only breaks ties.
KIND_ORDER = [
    "infantry_equipment", "support_equipment", "artillery_equipment", "anti_tank_equipment", "anti_air_equipment",
    "rocket_artillery_equipment", "motorized_equipment", "mechanized_equipment", "armored_car_equipment",
    "motorized_rocket_equipment", "light_tank_chassis", "medium_tank_chassis", "heavy_tank_chassis",
    "modern_tank_chassis", "amphibious_tank_chassis", "amphibious_mechanized_equipment",
]
# A kind whose own picture is another kind's: the game draws mechanized equipment as the motorized truck. Its
# row shows a halftrack in the look of the archetype pictures, a sprite of this mod (interface/mod1440_ui.gfx,
# made by tools/stretch_background.py); the technology picture it was before stood out among them.
KIND_SPRITE = {"mechanized_equipment": "GFX_1440p_archetype_mechanized_equipment_medium"}
KIND_FALLBACK = "GFX_archetype_support_equipment_medium"     # a kind without a picture of its own
KIND_TANK = "GFX_archetype_light_tank_equipment_medium"         # the same for a tank


def equipment_kinds(view):
    """(kind, sprite, width, height) for every archetype a land sub-unit of the view needs; the sprite is the
    game's medium archetype picture (GFX_archetype_<picture>_medium) as the view declares it, with the size of its
    texture. view: a tools/check_playset.py View (the game alone, or the playset)."""
    equipments = {}
    for _key, (_layer, full, _rel) in sorted(view.files("common/units/equipment", ".txt").items()):
        text = without_comments(io.open(full, encoding="utf-8-sig", errors="replace").read())
        for top, body in blocks(text):
            if top in ("equipments", "duplicate_archetypes"):
                for name, inner in blocks(body):
                    equipments[name] = (inner, top == "duplicate_archetypes")

    def archetype(name):
        """The archetype an equipment belongs to: itself, its 'archetype', or None."""
        inner, duplicate = equipments.get(name, ("", False))
        if duplicate or re.search(r"\bis_archetype\s*=\s*yes", inner):
            return name
        parent = re.search(r"\barchetype\s*=\s*(\w+)", inner)
        return parent.group(1) if parent and parent.group(1) in equipments else None

    def picture(name, depth=0):
        inner, duplicate = equipments.get(name, ("", False))
        found = re.search(r"\bpicture\s*=\s*(\w+)", inner)
        if found:
            return found.group(1)
        parent = re.search(r"\barchetype\s*=\s*(\w+)", inner)
        return picture(parent.group(1), depth + 1) if parent and depth < 4 else None

    kinds = set()
    for _key, (_layer, full, _rel) in sorted(view.files("common/units", ".txt").items()):
        text = without_comments(io.open(full, encoding="utf-8-sig", errors="replace").read())
        for top, body in blocks(text):
            if top != "sub_units":
                continue
            for _unit, inner in blocks(body):
                if not re.search(r"\bgroup\s*=", inner):
                    continue        # a ship, a plane or a railway gun
                for name, need in blocks(inner):
                    if name == "need":
                        for equipment in re.findall(r"([A-Za-z_0-9]+)\s*=", need):
                            kind = archetype(equipment)
                            if kind:
                                kinds.add(kind)

    sprites = {}
    for _key, (_layer, full, _rel) in sorted(view.files("interface", ".gfx", recurse=True).items()):
        try:
            root = guiparse.parse(guiparse.read_text(full))
        except Exception:
            continue
        for sprite in guiparse.sprite_declarations(root, full):
            sprites[sprite.name] = sprite.texture

    # the sprites of this mod that KIND_SPRITE names: their textures are in this repository
    own = {}
    mod_gfx = os.path.join(ROOT, "interface", "mod1440_ui.gfx")
    for sprite in guiparse.sprite_declarations(guiparse.parse(guiparse.read_text(mod_gfx)), mod_gfx):
        if sprite.name in KIND_SPRITE.values() and sprite.texture:
            sprites[sprite.name] = sprite.texture
            own[sprite.name] = os.path.join(ROOT, *sprite.texture.replace("\\", "/").split("/"))

    def size(sprite):
        _layer, path = (None, own[sprite]) if sprite in own else view.find(sprites[sprite] or "")
        if not path:
            return None
        with open(path, "rb") as handle:
            data = handle.read(32)
        if data[:4] == b"DDS ":
            return (int.from_bytes(data[16:20], "little"), int.from_bytes(data[12:16], "little"))
        from PIL import Image
        with Image.open(path) as image:
            return image.size

    rows = []
    for kind in [k for k in KIND_ORDER if k in kinds] + sorted(k for k in kinds if k not in KIND_ORDER):
        bare = re.sub(r"_(equipment|chassis)$", "", kind)
        shown = picture(kind)
        # a picture is the name of a sprite less "GFX_" and "_medium" (the game's), or the whole name (Better Mechanics)
        candidates = [KIND_SPRITE.get(kind), shown if shown and shown.startswith("GFX_") else None,
                      "GFX_archetype_%s_medium" % kind, "GFX_%s_medium" % shown if shown else None,
                      "GFX_archetype_%s_medium" % bare, "GFX_archetype_%s_equipment_medium" % bare,
                      KIND_TANK if "tank" in kind else KIND_FALLBACK]
        sprite = next(c for c in candidates if c and c in sprites and size(c))
        rows.append((kind, sprite) + tuple(size(sprite)))
    return rows


def state_count(view):
    """The number of states the view's history/states has: what script counts to tell the maps apart (X72)."""
    count = 0
    for _key, (_layer, full, _rel) in view.files("history/states", ".txt").items():
        if re.search(r"\bid\s*=\s*\d+", without_comments(io.open(full, encoding="utf-8-sig", errors="replace").read())):
            count += 1
    return count


def kinds_table(game):
    from check_playset import View      # that tool imports this one
    rows = equipment_kinds(View(game, []))
    return ('"""Made by tools/make_game_tables.py from the game %s: change the game, not this file.\n\n'
            "The kinds of land equipment of the Army Readiness page: every archetype a land sub-unit needs. A row is\n"
            "(kind, sprite of its picture, width, height of the picture).\n"
            '%d kinds."""\n\nKINDS = [\n%s]\n' % (version(game), len(rows), "".join("    %r,\n" % (row,) for row in rows)))


def mod_kinds(game):
    """The kinds of land equipment of the launcher's playset, when its states are not the game's: (the mods,
    the number of states, the rows), or None."""
    from check_playset import View, playset as layers_of
    layers, _unread, _source = layers_of(guiparse.user_dir())
    view = View(game, layers)
    states, own = state_count(view), state_count(View(game, []))
    if states == own:
        print("the playset has as many states as the game (%d): script could not tell its equipment from the game's" % own)
        return None
    rows = equipment_kinds(view)
    files = view.files("common/units", ".txt")
    mods = sorted(set(layer.name for layer, _full, _rel in files.values() if layer is not view.game))
    return " + ".join(mods), states, rows


def write_mod_kinds(game):
    """tools/equipment_kinds_mods_table.py: the kinds of land equipment of the playset, for the map with its
    number of states (part of --mods)."""
    found = mod_kinds(game)
    maps = [found] if found else []
    content = (
        '"""Made by tools/make_game_tables.py --mods from the mods of the launcher\'s playset: run it again when the\n'
        "playset changes. Delete this file for a build that knows the game's own equipment only.\n\n"
        "A map is (the mods its sub-units come from, the number of states of the playset, rows as in\n"
        "equipment_kinds_table.py). Script counts the states of the loaded game and counts the kinds of the map with\n"
        'that number; with any other number the game\'s own.\n%d maps."""\n\nMAPS = [\n%s]\n'
        % (len(maps), "".join("    (%r, %d, [\n%s    ]),\n" % (name, states, "".join("        %r,\n" % (row,) for row in rows))
                              for name, states, rows in maps)))
    io.open(os.path.join(ROOT, "tools", "equipment_kinds_mods_table.py"), "w", encoding="utf-8", newline="\n").write(content)
    print("wrote tools/equipment_kinds_mods_table.py: %s" % (", ".join(
        "%d kinds of land equipment for %d states" % (len(rows), states) for name, states, rows in maps) or "no map but the game's"))


# ---------------------------------------------------------------- d2-readiness end

# --- e-officers-gov: traits of unit leaders, advisors' small portraits and roles, the pictures of laws ---

# The kinds of trait in the order an officer's row shows them: who he is first, the skills he learnt last.
TRAIT_ORDER = ("personality_trait", "status_trait", "basic_trait", "assignable_trait", "assignable_terrain_trait",
               "basic_terrain_trait", "exile")
ARMY_TYPES = ("land", "corps_commander", "field_marshal", "all")
ADVISOR_SLOTS = ("political_advisor", "high_command", "army_chief", "navy_chief", "air_chief", "theorist")
SPRITE_NAME = re.compile(r"^GFX_[A-Za-z0-9_]+$")


def file_tag(source, tags):
    """As mod_portraits() names the file of a country: named after its tag (USA), or with the tag as a part of its name (AUGA_USA)."""
    if source in tags:
        return source
    parts = [part for part in re.split(r"[^A-Za-z0-9]+", source) if part in tags]
    return parts[0] if parts else "mod_" + re.sub(r"[^A-Za-z0-9]+", "_", source)


def game_view(game, layers=None):
    """The game's files as the loaded game sees them: the game alone, or with the layers of a playset."""
    from check_playset import View      # that tool imports this one
    return View(game, layers or [])


def sprite_names(view):
    """Every sprite name the .gfx files of interface/ declare, as the view loads them."""
    names = set()
    for _key, (_layer, full, _rel) in view.files("interface", ".gfx", recurse=True).items():
        names.update(re.findall(r"\bname\s*=\s*\"?(GFX_[A-Za-z0-9_\-.]+)", without_comments(guiparse.read_text(full))))
    return names


def traits(view, sprites):
    """(trait, kind, sprite) for every trait of a unit leader: kind is army, navy or both (who can have it), sprite
    the game's icon GFX_trait_<trait> or "" when no .gfx declares one. The traits of operatives are left out."""
    rows = []
    for name, (body, _layer) in view.ids("common/unit_leader", "leader_traits").items():
        found = re.search(r"\btype\s*=\s*(\{[^}]*\}|\w+)", body)
        types = re.findall(r"\w+", found.group(1)) if found else ["all"]
        army = any(t in ARMY_TYPES for t in types)
        navy = any(t in ("navy", "all") for t in types)
        if not (army or navy):
            continue
        kind = "both" if (army and navy) else "army" if army else "navy"
        trait_type = re.search(r"\btrait_type\s*=\s*(\w+)", body)
        order = TRAIT_ORDER.index(trait_type.group(1)) if trait_type and trait_type.group(1) in TRAIT_ORDER else len(TRAIT_ORDER)
        sprite = "GFX_trait_" + name
        rows.append((order, name, kind, sprite if sprite in sprites else ""))
    return [row[1:] for row in sorted(rows, key=lambda row: row[0])]


def advisors(game, sprites, paths=None):
    """(character, file of common/characters, sprite, slot, trait, large) for every advisor role of a character:
    one row per role, the first trait of the role. The sprite is the 'small' of the character's portraits
    (civilian first) when a .gfx declares it; else the 'large' one, and large is 1; else ""."""
    rows = []
    for path in paths if paths is not None else sorted(glob.glob(os.path.join(game, "common", "characters", "*.txt"))):
        tag = os.path.splitext(os.path.basename(path))[0]
        text = without_comments(io.open(path, encoding="utf-8-sig", errors="replace").read())
        for top, body in blocks(text):
            if top != "characters":
                continue
            for name, character in blocks(body):
                small, large = "", 0
                for size in ("small", "large"):
                    for kind in ("civilian", "army", "navy"):
                        m = re.search(r"\b%s\s*=\s*\{[^{}]*?\b%s\s*=\s*\"?([^\s\"}]+)\"?" % (kind, size), character)
                        if m and SPRITE_NAME.match(m.group(1)) and m.group(1) in sprites:
                            small, large = m.group(1), int(size == "large")
                            break
                    if small:
                        break
                seen = set()
                for role, inner in blocks(character):
                    if role != "advisor":
                        continue
                    slot = re.search(r"\bslot\s*=\s*(\w+)", inner)
                    if not slot or slot.group(1) not in ADVISOR_SLOTS or slot.group(1) in seen:
                        continue
                    seen.add(slot.group(1))
                    listed = re.search(r"\btraits\s*=\s*\{([^}]*)\}", inner)
                    first = re.findall(r"[A-Za-z0-9_]+", listed.group(1)) if listed else []
                    rows.append((name, tag, small, slot.group(1), first[0] if first else "", large))
    return rows


def law_pictures(view, sprites):
    """(idea, sprite) for every idea of a law category (law = yes) of common/ideas: the sprite its picture names,
    GFX_idea_<idea> without one; "" when no .gfx declares it."""
    rows = []
    for _key, (_layer, full, _rel) in sorted(view.files("common/ideas", ".txt").items()):
        text = without_comments(guiparse.read_text(full))
        for top, body in blocks(text):
            if top != "ideas":
                continue
            for _category, ideas in blocks(body):
                if not re.search(r"^\s*law\s*=\s*yes", ideas, re.M):
                    continue
                for idea, inner in blocks(ideas):
                    picture = re.search(r"^\s*picture\s*=\s*\"?([A-Za-z0-9_]+)", inner, re.M)
                    sprite = picture.group(1) if picture else idea
                    sprite = sprite if sprite.startswith("GFX_") else "GFX_idea_" + sprite
                    rows.append((idea, sprite if sprite in sprites else ""))
    return sorted(set(rows))


def mod_traits(game, user):
    """The traits of the launcher's playset that the game lacks, the game's traits the playset drops, and the
    mods the traits come from. The playset is read as the game loads it (a mod's file replaces the game's)."""
    from check_playset import playset as layers_of
    layers, _unread, _source = layers_of(user)
    view = game_view(game, layers)
    own = set(row[0] for row in traits(game_view(game), sprite_names(game_view(game))))
    rows = traits(view, sprite_names(view))
    names = set(row[0] for row in rows)
    files = view.files("common/unit_leader", ".txt")
    mods = sorted(set(layer.name for layer, _full, _rel in files.values() if layer is not view.game))
    return [row for row in rows if row[0] not in own], sorted(own - names), mods


def mod_advisors(game, user):
    """The advisor roles of characters the mods of the playset add, rows as in advisors()."""
    from check_playset import playset as layers_of
    layers, _unread, _source = layers_of(user)
    sprites = sprite_names(game_view(game, layers))
    known = set(row[0] for row in advisors(game, sprite_names(game_view(game))))
    tags = country_tags(game)
    rows = []
    for _name, folder in playset(user):
        paths = sorted(glob.glob(os.path.join(folder, "common", "characters", "*.txt")))
        for row in advisors(game, sprites, paths):
            if row[0] not in known:
                rows.append((row[0], file_tag(row[1], tags)) + row[2:])
        known.update(row[0] for row in rows)
    return rows


def officer_tables(game, made, files):
    """Adds the advisors to portraits_table.py, and the tables of traits and of law pictures, to files."""
    view = game_view(game)
    sprites = sprite_names(view)
    roles = advisors(game, sprites)
    files["tools/portraits_table.py"] += (
        "\n# The advisor roles: (character, file of common/characters, sprite, slot, first trait of the role, large).\n"
        "# The sprite is the small portrait; the large one (large = 1) when no .gfx declares the small; \"\" when\n"
        "# neither is declared. %d roles.\n"
        "ADVISORS = [\n%s]\n" % (len(roles), "".join("    %r,\n" % (row,) for row in roles)))
    rows = traits(view, sprites)
    files["tools/traits_table.py"] = (
        '"""Made by tools/make_game_tables.py from the game %s: change the game, not this file.\n\n'
        "A row is (trait, who can have it: army, navy or both, its icon GFX_trait_<trait> or \"\" without one), in the\n"
        "order an officer's row shows his traits. The traits of operatives are left out.\n"
        '%d traits, %d without an icon."""\n\nTRAITS = [\n%s]\n'
        % (made, len(rows), sum(1 for row in rows if not row[2]), "".join("    %r,\n" % (row,) for row in rows)))
    laws = law_pictures(view, sprites)
    files["tools/laws_table.py"] = (
        '"""Made by tools/make_game_tables.py from the game %s: change the game, not this file.\n\n'
        "A row is (idea of a law, the sprite of its picture or \"\" when no .gfx declares it).\n"
        '%d laws."""\n\nLAW_PICTURES = [\n%s]\n' % (made, len(laws), "".join("    %r,\n" % (row,) for row in laws)))


def mod_advisors_text(game, user):
    rows = mod_advisors(game, user)
    print("advisor roles of the mods: %d" % len(rows))
    return ("\n# The advisor roles of the characters above and of the other characters the mods add, as in\n"
            "# portraits_table.py. %d roles.\nADVISORS = [\n%s]\n" % (len(rows), "".join("    %r,\n" % (row,) for row in rows)))


def write_mod_traits(game, user):
    rows, gone, mods = mod_traits(game, user)
    content = (
        '"""Made by tools/make_game_tables.py --mods from the mods of the launcher\'s playset: run it again when the\n'
        "playset changes. Delete this file for a build that knows the game's own traits only.\n\n"
        "TRAITS: the traits of unit leaders the playset has and the game lacks, rows as in traits_table.py.\n"
        "GONE: the game's traits the playset does not define.\n"
        '%d traits, %d gone."""\n\nMODS = %r\n\nTRAITS = [\n%s]\n\nGONE = %r\n'
        % (len(rows), len(gone), mods, "".join("    %r,\n" % (row,) for row in rows), gone))
    io.open(os.path.join(ROOT, "tools", "traits_mods_table.py"), "w", encoding="utf-8", newline="\n").write(content)
    print("wrote tools/traits_mods_table.py: %d traits of %s, %d of the game's gone" % (len(rows), ", ".join(mods) or "no mod", len(gone)))


def version(game):
    for line in io.open(os.path.join(game, "launcher-settings.json"), encoding="utf-8", errors="replace"):
        m = re.search(r'"rawVersion"\s*:\s*"([^"]+)"', line)
        if m:
            return m.group(1)
    return "unknown"


def main(argv):
    game = guiparse.find_game_dir()
    if not game or not os.path.isdir(game):
        print("game folder not found: the tables on disk stay as they are")
        return 2
    if "--mods" in argv:
        user = os.path.join(os.path.expanduser("~"), "Documents", "Paradox Interactive", "Hearts of Iron IV")
        rows, used = mod_portraits(game, user)
        content = (
            '"""Made by tools/make_game_tables.py --mods from the mods of the launcher\'s playset: run it again when the\n'
            "playset changes. Delete this file for a build that knows the game's own characters only.\n\n"
            "A row is as in portraits_table.py. A character whose file gives him no role is taken as an officer whose\n"
            "command comes by an effect. The game's own characters are left out, also where a mod changes them.\n"
            '%d characters."""\n\nMODS = [\n%s]\n\nPORTRAITS = [\n%s]\n'
            % (len(rows), "".join("    %r,\n" % line for line in used), "".join("    %r,\n" % (row,) for row in rows)))
        content += mod_advisors_text(game, user)        # e-officers-gov
        io.open(os.path.join(ROOT, "tools", "portraits_mods_table.py"), "w", encoding="utf-8", newline="\n").write(content)
        print("wrote tools/portraits_mods_table.py: %d characters of %d mods" % (len(rows), len(used)))
        write_mod_traits(game, user)                    # e-officers-gov
        found = mod_victory_points(game)
        maps = [found] if found else []
        content = (
            '"""Made by tools/make_game_tables.py --mods from the mods of the launcher\'s playset: run it again when the\n'
            "playset changes. Delete this file for a build that knows the game's own map only.\n\n"
            "A map is (the mods its states come from, its number of states, rows as in victory_points_table.py). Script\n"
            "counts the states of the loaded game and follows the points of the map with that number; with any other\n"
            'number it follows the game\'s own.\n%d maps."""\n\nMAPS = [\n%s]\n'
            % (len(maps), "".join("    (%r, %d, [\n%s    ]),\n" % (name, states, "".join("        %r,\n" % (row,) for row in points))
                                  for name, states, points in maps)))
        io.open(os.path.join(ROOT, "tools", "victory_points_mods_table.py"), "w", encoding="utf-8", newline="\n").write(content)
        print("wrote tools/victory_points_mods_table.py: %s" % (", ".join(
            "%d victory points in %d states of %s" % (len(points), states, name) for name, states, points in maps) or "no map but the game's"))
        write_mod_kinds(game)                           # d2-readiness
        return 0
    made = version(game)
    people = portraits(game)
    tags = sorted(country_tags(game) & set(row[1] for row in people))
    points = victory_points(game)
    files = {
        "tools/portraits_table.py": (
            '"""Made by tools/make_game_tables.py from the game %s: change the game, not this file.\n\n'
            "A row is (character, file of common/characters, army sprite, navy sprite, civilian sprite, roles).\n"
            "TAGS are the files that carry the name of a country: script asks a country for its tag before it goes\n"
            "through the people of that file.\n"
            '%d characters."""\n\nTAGS = %r\n\nPORTRAITS = [\n%s]\n'
            % (made, len(people), tags, "".join("    %r,\n" % (row,) for row in people))),
        "tools/victory_points_table.py": (
            '"""Made by tools/make_game_tables.py from the game %s: change the game, not this file.\n\n'
            "A row is (province, state, value). The name of a point is the game's text VICTORY_POINTS_<province>.\n"
            '%d victory points."""\n\nVICTORY_POINTS = [\n%s]\n'
            % (made, len(points), "".join("    %r,\n" % (row,) for row in points))),
        "tools/equipment_kinds_table.py": kinds_table(game),       # d2-readiness
    }
    officer_tables(game, made, files)                   # e-officers-gov
    stale = []
    for rel, content in files.items():
        path = os.path.join(ROOT, rel)
        current = io.open(path, encoding="utf-8", newline="").read() if os.path.isfile(path) else None
        if current is None or current.replace("\r\n", "\n") != content:   # a checkout may carry CRLF
            stale.append(rel)
            if "--check" not in argv:
                io.open(path, "w", encoding="utf-8", newline="\n").write(content)
                print("wrote", rel)
    print("%d characters with a portrait, %d victory points" % (len(people), len(points)))
    return 1 if ("--check" in argv and stale) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
