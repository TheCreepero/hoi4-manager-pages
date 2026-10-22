"""Dev only: where the mods of the launcher's playset meet this mod, read from their files without the game.

    python -I tools/check_playset.py                    the whole report
    python -I tools/check_playset.py windows content    some parts: playset windows sprites fonts hotkeys guis content
    python -I tools/check_playset.py --window <name>    a reworked window as each mod has it, against the game's
    python -I tools/check_playset.py --out <file>       the report into a file as well

The playset is the one the launcher has active (dlc_load.json; while a game check runs, the copy the harness
keeps in scratch/harness). What the report can tell:

    windows   a mod that defines a window of this mod's name (a copy of a page, or the 1440p UI mod before the
              split of 2026-10-21). The game takes the definition of the file that comes last by name.
    sprites   a sprite this mod's pages name that a mod defines again, or whose picture a mod replaces: with
              another size or number of frames the layout no longer fits it.
    fonts     the same for the fonts.
    hotkeys   a key this mod adds that a mod adds too.
    guis      the scripted GUIs of the mods on the tabs the manager pages stand on, with place and size.
    content   what the pages name from the game's content (equipment, buildings, resources, laws, medals,
              victory points, characters) against what the playset has.

What it cannot tell is how the screens look and what the log says: that is the game check with the playset
(wiki/Game-Recipes.md, "With the user's playset").
"""
import csv
import io
import json
import os
import pickle
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guiparse  # noqa: E402
from make_game_tables import blocks, without_comments, portraits  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARTS = ["playset", "windows", "sprites", "fonts", "hotkeys", "guis", "content"]
OUT = []


def say(text=""):
    OUT.append(text)
    print(text)


def head(title):
    say()
    say("=" * 8 + " " + title)


def few(names, most=12):
    names = [str(n) for n in names]
    return ", ".join(names[:most]) + (" ... (%d more)" % (len(names) - most) if len(names) > most else "")


# ---------------------------------------------------------------- the playset as the game loads it


class Layer:
    def __init__(self, name, folder, replace=(), mine=False, supported=""):
        self.name, self.folder, self.mine, self.supported = name, folder, mine, supported
        self.replace = [p.replace("\\", "/").strip("/").lower() for p in replace]

    def __repr__(self):
        return self.name


def playset(user):
    """The mods of the launcher's playset in load order, this mod among them."""
    path = os.path.join(ROOT, "scratch", "harness", "dlc_load.backup.json")
    if not os.path.isfile(path):
        path = os.path.join(user, "dlc_load.json")
    layers, unread = [], []
    for rel in json.load(io.open(path, encoding="utf-8-sig")).get("enabled_mods", []):
        file = os.path.join(user, rel)
        if not os.path.isfile(file):
            unread.append(rel + " (no launcher file)")
            continue
        text = io.open(file, encoding="utf-8-sig", errors="replace").read()
        name = re.search(r'^\s*name\s*=\s*"([^"]*)"', text, re.M)
        folder = re.search(r'^\s*path\s*=\s*"([^"]*)"', text, re.M)
        folder = folder.group(1) if folder else ""
        if folder and not os.path.isabs(folder):
            folder = os.path.join(user, folder)
        if not folder or not os.path.isdir(folder):
            unread.append(rel + " (no folder: an archive, or not downloaded)")
            continue
        supported = re.search(r'^\s*supported_version\s*=\s*"([^"]*)"', text, re.M)
        mine = os.path.normcase(os.path.abspath(folder)) == os.path.normcase(os.path.abspath(ROOT))   # this repository, and no sibling mod of the Manager
        layers.append(Layer(name.group(1) if name else rel, folder, re.findall(r'^\s*replace_path\s*=\s*"([^"]*)"', text, re.M),
                            mine, supported.group(1) if supported else ""))
    return layers, unread, path


class View:
    """The files of a folder as the game sees them: the same path in a later mod takes the place of the
    earlier file, and a mod's replace_path empties the folder first (the folder itself, not what is under it)."""

    def __init__(self, game, mods):
        self.game = Layer("the game", game)
        self.mods = [m for m in mods if not m.mine]
        self.layers = [self.game] + self.mods

    def files(self, rel_dir, suffix, recurse=False):
        rel_dir = rel_dir.replace("\\", "/").strip("/")
        out = {}
        for layer in self.layers:
            if rel_dir.lower() in layer.replace:
                out = dict((k, v) for k, v in out.items() if os.path.dirname(k) != rel_dir.lower())
            base = os.path.join(layer.folder, rel_dir)
            if not os.path.isdir(base):
                continue
            for dirpath, dirs, names in os.walk(base):
                if not recurse:
                    dirs[:] = []
                for name in names:
                    if name.lower().endswith(suffix):
                        full = os.path.join(dirpath, name)
                        rel = os.path.relpath(full, layer.folder).replace("\\", "/")
                        out[rel.lower()] = (layer, full, rel)
        return out

    def find(self, rel):
        """The layer whose copy of one file the game loads, and the path."""
        for layer in reversed(self.layers):
            full = os.path.join(layer.folder, rel)
            if os.path.isfile(full):
                return layer, full
        return None, None

    def ids(self, rel_dir, top, suffix=".txt"):
        """id -> (text of its block, layer) for the blocks inside 'top = { }' of every file of a folder."""
        out = {}
        for _key, (layer, full, _rel) in sorted(self.files(rel_dir, suffix).items()):
            text = without_comments(guiparse.read_text(full))
            for name, body in blocks(text):
                if name != top:
                    continue
                for ident, inner in blocks(body):
                    out[ident] = (inner, layer)
        return out


def cached(name, stamp, make):
    folder = os.path.join(ROOT, "scratch", "cache")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, name)
    try:
        with open(path, "rb") as handle:
            data = pickle.load(handle)
        if data.get("stamp") == stamp:
            return data["value"]
    except Exception:
        pass
    value = make()
    with open(path, "wb") as handle:
        pickle.dump({"stamp": stamp, "value": value}, handle)
    return value


def my_gui_files():
    folder = os.path.join(ROOT, "interface")
    return [os.path.join(folder, f) for f in sorted(os.listdir(folder)) if f.lower().endswith(".gui")]


# ---------------------------------------------------------------- windows


def shape(node):
    """named widget path -> what the widget says about itself: its values and its blocks without a name."""

    def own(n):
        parts = []
        for c in n.children:
            if c.children is None:
                parts.append("%s=%s" % ((c.key or "").lower(), c.value))
            elif not c.name:
                parts.append("%s{%s}" % ((c.key or "").lower(), own(c)))
        return " ".join(sorted(parts))

    out, stack = {}, [(node, "")]
    while stack:
        current, prefix = stack.pop()
        name = current.name
        if name:
            prefix = (prefix + "/" + name if prefix else name).lower()
            out[prefix] = own(current)
        for child in current.children or []:
            if child.children is not None:
                stack.append((child, prefix))
    return out


def game_windows(game):
    """name -> node of the game's own definition of every window this mod reworks (baseline/manifest.csv).
    This mod reworks no vanilla window and keeps no baseline/ folder: then both are empty."""
    sources = {}
    manifest = os.path.join(ROOT, "baseline", "manifest.csv")
    if not os.path.isfile(manifest):
        return {}, sources
    with io.open(manifest, encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            sources.setdefault(row["Source"], set()).add(row["Window"].lower())
    out = {}
    for rel, names in sources.items():
        for window in guiparse.top_level_windows(guiparse.parse_file(os.path.join(game, rel))):
            if window.name.lower() in names:
                out[window.name.lower()] = window
    return out, sources


def mod_guis(view):
    """(layer, relative path, parsed file) of every .gui file a mod of the playset brings."""
    out = []
    for _key, (layer, full, rel) in sorted(view.files("interface", ".gui", recurse=True).items()):
        if layer is view.game:
            continue
        try:
            out.append((layer, rel, guiparse.parse_file(full)))
        except Exception as exc:
            say("  cannot read %s of %s: %s" % (rel, layer, exc))
    return out


def part_windows(view, guis, detail=None):
    mine = {}
    for path in my_gui_files():
        for window in guiparse.top_level_windows(guiparse.parse_file(path)):
            mine[window.name.lower()] = os.path.basename(path)
    vanilla, sources = game_windows(view.game.folder)
    if detail is None:
        head("windows: %d of this mod, %d of them reworked from the game's" % (len(mine), len(vanilla)))
    found = 0
    for layer, rel, root in guis:
        hits = [w for w in guiparse.top_level_windows(root) if w.name.lower() in mine]
        if not hits:
            continue
        found += 1
        base = os.path.basename(rel).lower()
        same, differ, wins = [], [], []
        for window in hits:
            name = window.name.lower()
            if base > mine[name].lower():
                wins.append(window.name)
            if name not in vanilla:
                differ.append("%s (a window of this mod's own name)" % window.name)
                continue
            a, b = shape(vanilla[name]), shape(window)
            added = sorted(k for k in b if k not in a)
            dropped = sorted(k for k in a if k not in b)
            changed = sorted(k for k in a if k in b and a[k] != b[k])
            if not added and not dropped and not changed:
                same.append(window.name)
                continue
            differ.append("%s (+%d -%d ~%d)" % (window.name, len(added), len(dropped), len(changed)))
            if detail and detail.lower() == name:
                say()
                say("%s in %s of [%s]" % (window.name, rel, layer))
                for k in added:
                    say("  + %s    %s" % (k, b[k][:150]))
                for k in dropped:
                    say("  - %s" % k)
                for k in changed:
                    say("  ~ %s" % k)
                    old, new = set(a[k].split(" ")), set(b[k].split(" "))
                    say("      game: %s" % " ".join(sorted(old - new))[:220])
                    say("      mod:  %s" % " ".join(sorted(new - old))[:220])
        if detail is not None:
            continue
        whole = " (takes the place of the game's file)" if rel.lower() in [s.lower() for s in sources] else ""
        say()
        say("[%s] %s%s" % (layer, rel, whole))
        if differ:
            say("    its changes are lost under this mod: " + ", ".join(differ))
        if same:
            say("    as in the game: %d (%s)" % (len(same), few(same, 6)))
        if wins:
            say("    !! COMES AFTER this mod's file by name, so the game takes the mod's: " + ", ".join(wins))
    if detail is None and not found:
        say("no mod of the playset defines a window of this mod")
    if detail is None:
        say()
        say("  +n -n ~n: named widgets the mod adds, drops and changes against the game's window; --window <name> lists them")


# ---------------------------------------------------------------- sprites and fonts


def picture_size(path):
    try:
        with open(path, "rb") as handle:
            data = handle.read(32)
        if data[:4] == b"DDS ":
            return (int.from_bytes(data[16:20], "little"), int.from_bytes(data[12:16], "little"))
        from PIL import Image
        with Image.open(path) as image:
            return image.size
    except Exception:
        return None


def part_sprites(view):
    used = set()
    for path in my_gui_files():
        used.update(re.findall(r'"(GFX_[A-Za-z0-9_\-]+)"', guiparse.read_text(path)))
    known = guiparse.load_sprites(view.game.folder)
    own = set(name for name, sprite in known.items() if sprite.file.startswith(ROOT))
    head("sprites: %d named by this mod's screens, %d of them its own" % (len(used), len(used & own)))
    again, same = [], 0
    defined, dropped_by = set(own), {}
    for key, (layer, full, rel) in sorted(view.files("interface", ".gfx", recurse=True).items()):
        text = guiparse.read_text(full)
        names = set(re.findall(r'name\s*=\s*"?(GFX_[A-Za-z0-9_\-]+)"?', text))
        defined |= names
        if layer is view.game:
            continue
        # a mod's file under the game's own path: what the game's copy defines and this one does not is gone
        theirs = os.path.join(view.game.folder, rel)
        if os.path.isfile(theirs):
            for name in set(re.findall(r'name\s*=\s*"?(GFX_[A-Za-z0-9_\-]+)"?', guiparse.read_text(theirs))) - names:
                dropped_by[name] = "[%s] %s" % (layer, rel)
        if not names & (used | own):
            continue
        for sprite in guiparse.sprite_declarations(guiparse.parse(text), full):
            if sprite.name in own:
                again.append("!! [%s] %s defines this mod's own sprite %s" % (layer, rel, sprite.name))
            elif sprite.name in used and sprite.name in known:
                was = known[sprite.name]
                notes = []
                if sprite.frames != was.frames:
                    notes.append("frames %s, the game's %s" % (sprite.frames, was.frames))
                if (sprite.texture or "").lower() != (was.texture or "").lower():
                    old = picture_size(os.path.join(view.game.folder, was.texture or ""))
                    _layer, path = view.find(sprite.texture or "")
                    new = picture_size(path) if path else None
                    if old != new:
                        notes.append("picture %s %s, the game's %s %s" % (sprite.texture, new, was.texture, old))
                    else:
                        notes.append("another picture of the same size")
                if sprite.border != was.border:
                    notes.append("border %s, the game's %s" % (sprite.border, was.border))
                if sprite.kind.lower() != was.kind.lower():
                    notes.append("kind %s, the game's %s" % (sprite.kind, was.kind))
                if [n for n in notes if not n.startswith("another picture")]:
                    again.append("[%s] %s: %s: %s" % (layer, rel, sprite.name, "; ".join(notes)))
                else:
                    same += 1
    for line in again:
        say(line)
    say("%d definitions of the same shape as the game's (another picture at most)" % same)
    # a picture replaced under the game's own path, without a new definition
    resized, repainted = [], {}
    for name in sorted(used - own):
        sprite = known.get(name)
        if not sprite or not sprite.texture:
            continue
        layer, path = view.find(sprite.texture)
        if layer is None or layer is view.game:
            continue
        old, new = picture_size(os.path.join(view.game.folder, sprite.texture)), picture_size(path)
        if old != new:
            resized.append("!! [%s] %s for %s: %s, the game's %s" % (layer, sprite.texture, name, new, old))
        else:
            repainted.setdefault(layer.name, []).append(name)
    for line in resized:
        say(line)
    for mod, names in sorted(repainted.items()):
        say("[%s] paints %d of the game's pictures anew, same size: %s" % (mod, len(names), few(names, 8)))
    missing = sorted(name for name in used if name not in known)
    if missing:
        say("named but defined nowhere in the game or this mod: " + few(missing))
    gone = sorted(name for name in used if name in known and name not in defined)
    for name in gone:
        say("!! %s is named by this mod and not defined in the playset: dropped by %s. The game logs \"Could not find sprite type\""
            % (name, dropped_by.get(name, "a mod")))
        for path in my_gui_files():
            n = guiparse.read_text(path).count('"%s"' % name)
            if n:
                say("       %d times in %s" % (n, os.path.basename(path)))
    if not gone:
        say("every sprite this mod names is still defined in the playset")


def part_fonts(view):
    used = set()
    for path in my_gui_files():
        used.update(re.findall(r'\bfont\s*=\s*"?([A-Za-z0-9_]+)"?', guiparse.read_text(path)))
    declared = guiparse.font_declarations(view.game.folder)
    head("fonts: %d named by this mod's screens" % len(used))
    found = False
    for _key, (layer, full, rel) in sorted(view.files("interface", ".gfx", recurse=True).items()):
        if layer is view.game:
            continue
        text = without_comments(guiparse.read_text(full))
        names = set(re.findall(r'bitmapfont\s*=\s*\{\s*name\s*=\s*"?([A-Za-z0-9_]+)"?', text)) & used
        if names:
            found = True
            say("[%s] %s defines again: %s" % (layer, rel, few(sorted(names))))
    for name in sorted(used):
        if name not in declared:
            continue
        for ext in (".fnt", ".dds", ".tga"):
            layer, _path = view.find(declared[name][0] + ext)
            if layer is not None and layer is not view.game:
                found = True
                say("[%s] replaces %s%s of the font %s" % (layer, declared[name][0], ext, name))
    if not found:
        say("no mod of the playset touches them")


# ---------------------------------------------------------------- hotkeys


def shortcuts(root):
    """(key, window, widget) for every shortcut line of a parsed .gui file."""
    out = []
    for window in guiparse.top_level_windows(root):
        for node in window.walk():
            for key in node.leaves("shortcut"):
                out.append((key.lower(), window.name, node.name or "?"))
    return out


def game_shortcuts(game):
    folder = os.path.join(game, "interface")
    files = [os.path.join(folder, f) for f in sorted(os.listdir(folder)) if f.lower().endswith(".gui")]
    stamp = [(p, os.path.getmtime(p), os.path.getsize(p)) for p in files]

    def make():
        out = []
        for path in files:
            if "shortcut" in guiparse.read_text(path):
                out += shortcuts(guiparse.parse_file(path))
        return out

    return cached("game_shortcuts.pickle", stamp, make)


def part_hotkeys(view, guis):
    game = game_shortcuts(view.game.folder)
    in_game = set((key, widget.lower()) for key, _window, widget in game)
    mine = []
    for path in my_gui_files():
        for key, window, widget in shortcuts(guiparse.parse_file(path)):
            if (key, widget.lower()) not in in_game:
                mine.append((key, window, widget, os.path.basename(path)))
    theirs = []
    for layer, rel, root in guis:
        for key, window, widget in shortcuts(root):
            if (key, widget.lower()) not in in_game:
                theirs.append((key, window, widget, layer.name, rel))
    head("hotkeys: %d added by this mod, %d added by the mods of the playset" % (len(mine), len(theirs)))
    my_keys = set(key for key, _w, _n, _f in mine)
    clash = [t for t in theirs if t[0] in my_keys]
    for key in sorted(set(t[0] for t in clash)):
        say("%s" % key)
        for _k, window, widget, file in [m for m in mine if m[0] == key]:
            say("    this mod: %s/%s (%s)" % (window, widget, file))
        for _k, window, widget, mod, rel in [t for t in clash if t[0] == key]:
            say("    [%s] %s/%s (%s)" % (mod, window, widget, rel))
    if not clash:
        say("no key is added by both")
    say("a key counts as added when the game has no widget of that name with that key; the same key on two screens")
    say("only matters when both can be up at once")
    by_mod = {}
    for key, window, widget, mod, _rel in theirs:
        by_mod.setdefault(mod, []).append("%s (%s)" % (key, widget))
    for mod, keys in sorted(by_mod.items()):
        say("[%s] adds %d: %s" % (mod, len(keys), few(sorted(set(keys)), 10)))


# ---------------------------------------------------------------- scripted GUIs


def scripted_guis(folder):
    out = []
    base = os.path.join(folder, "common", "scripted_guis")
    if not os.path.isdir(base):
        return out
    for name in sorted(os.listdir(base)):
        if not name.lower().endswith(".txt"):
            continue
        try:
            root = guiparse.parse_file(os.path.join(base, name))
        except Exception:
            continue
        for top in root.blocks("scripted_gui"):
            for gui in top.blocks():
                out.append((gui.key, gui.get("window_name") or "", gui.get("parent_window_token") or "",
                            gui.get("parent_window_name") or "", gui.get("context_type") or "", name))
    return out


def place(node):
    if node is None:
        return "window not found"
    pos, size = node.block("position"), node.block("size")
    text = "at %s,%s" % (pos.get("x"), pos.get("y")) if pos else "at 0,0"
    if size:
        text += " size %sx%s" % (size.get("width") or size.get("x"), size.get("height") or size.get("y"))
    if node.get("orientation"):
        text += " from " + node.get("orientation")
    return text


def part_guis(view, guis):
    mine = scripted_guis(ROOT)
    tokens = set(g[2] for g in mine if g[2])
    my_windows = {}
    for path in my_gui_files():
        for window in guiparse.top_level_windows(guiparse.parse_file(path)):
            my_windows[window.name.lower()] = window
    their_windows = {}
    for _layer, _rel, root in guis:
        for window in guiparse.top_level_windows(root):
            their_windows[window.name.lower()] = window
    head("scripted GUIs on the tabs of this mod's pages: " + ", ".join(sorted(tokens)))
    for token in sorted(tokens):
        say(token)
        for name, window, tok, _parent, _context, _file in mine:
            if tok == token:
                say("    this mod: %s, %s" % (name, place(my_windows.get(window.lower()))))
        for layer in view.mods:
            for name, window, tok, parent, _context, file in scripted_guis(layer.folder):
                if tok == token or (parent and parent.lower() in my_windows):
                    say("    [%s] %s (%s), %s" % (layer, name, file, place(their_windows.get(window.lower()))))
    say()
    say("scripted GUIs per mod: " + ", ".join("%s %d" % (layer, n) for layer, n in
                                             ((layer, len(scripted_guis(layer.folder))) for layer in view.mods) if n))


# ---------------------------------------------------------------- content the pages name


def compare(title, named, have, game_has, note=""):
    """named: what the mod's pages name; have: id -> layer in the playset; game_has: the ids of the game alone."""
    gone = [n for n in named if n not in have]
    new = sorted(n for n in have if n not in game_has and n not in named)
    say("%s: the pages name %d; the playset has %d, the game alone %d" % (title, len(named), len(have), len(game_has)))
    if gone:
        say("    !! named by a page, not in the playset: " + few(gone))
    if new:
        by_mod = {}
        for n in new:
            by_mod.setdefault(have[n].name, []).append(n)
        for mod, names in sorted(by_mod.items()):
            say("    not named by a page, from [%s]: %s" % (mod, few(names, 14)))
    if note and (gone or new):
        say("    " + note)


def part_content(view):
    import build_managers as M
    import build_records as R
    from unit_medals_table import MEDALS
    from victory_points_table import VICTORY_POINTS
    from portraits_table import PORTRAITS
    try:
        from portraits_mods_table import PORTRAITS as MOD_PORTRAITS
    except ImportError:
        MOD_PORTRAITS = []
    try:
        from victory_points_mods_table import MAPS
    except ImportError:
        MAPS = []
    game = View(view.game.folder, [])
    head("content the pages name")

    def layers(table):
        return dict((k, v[1]) for k, v in table.items())

    # equipment: the kinds Army Readiness counts in a game with the playset's number of states (d2-readiness), against
    # the archetypes the land sub-units of the playset need (tools/make_game_tables.py, equipment_kinds)
    from make_game_tables import equipment_kinds, state_count
    states = state_count(view)
    tables = [rows for count, rows in M.AR_TABLES if count == states] or [M.AR_TABLES[0][1]]
    counted = [row[0] for row in tables[0]]
    needed = [row[0] for row in equipment_kinds(view)]
    say("equipment (kinds of Army Readiness): the playset's land sub-units need %d kinds; the page counts %d for %d states (%s)"
        % (len(needed), len(counted), states, "the playset's table" if tables[0] is not M.AR_TABLES[0][1] else "the game's table"))
    missing = [k for k in needed if k not in counted]
    if missing:
        say("    !! needed in the playset, not counted (run tools/make_game_tables.py --mods): " + few(missing, 14))
    gone = [k for k in counted if k not in needed]
    if gone:
        say("    counted, needed by no sub-unit of the playset (a row only while some are in stock): " + few(gone, 14))

    # buildings and resources of the States table
    named = []
    for column in M.STATE_COLUMNS:
        m = re.match(r"building_level@(\w+)", column[1])
        if m:
            named.append(m.group(1))
    named += ["infrastructure", "industrial_complex", "arms_factory"]
    compare("buildings (States)", named, layers(view.ids("common/buildings", "buildings")),
            set(game.ids("common/buildings", "buildings")))
    compare("resources (States, National Figures)", M.RESOURCES, layers(view.ids("common/resources", "resources")),
            set(game.ids("common/resources", "resources")))
    compare("ideology groups (Government)", [group for _, group in R.IDEOLOGIES], layers(view.ids("common/ideologies", "ideologies")),
            set(game.ids("common/ideologies", "ideologies")))

    # laws of the Government page: the ideas of three categories
    def ideas(v, category):
        out = {}
        for _key, (layer, full, _rel) in sorted(v.files("common/ideas", ".txt").items()):
            text = without_comments(guiparse.read_text(full))
            for top, body in blocks(text):
                if top != "ideas":
                    continue
                for cat, inner in blocks(body):
                    if cat == category:
                        for ident, _b in blocks(inner):
                            out[ident] = layer
        return out

    for label, category in (("Economy", "economy"), ("Trade", "trade_laws"), ("Conscription", "mobilization_laws")):
        named = dict(R.LAWS)[label]
        compare("laws: %s (Government)" % label, named, ideas(view, category), set(ideas(game, category)),
                "a law no page names reads \"another law\"")

    # advisor slots
    def slots(v):
        out = {}
        for _key, (layer, full, _rel) in sorted(v.files("common/idea_tags", ".txt").items()):
            for slot in re.findall(r"\b(?:character_slot|slot)\s*=\s*(\w+)", without_comments(guiparse.read_text(full))):
                out[slot] = layer
        return out

    named = [o[0] for o in R.OFFICES] + ["political_advisor", "high_command"]
    compare("offices (Government)", named, slots(view), set(slots(game)))

    # unit medals
    compare("unit medals (Officers)", [m[0] for m in MEDALS], layers(view.ids("common/unit_medals", "unit_medals")),
            set(game.ids("common/unit_medals", "unit_medals")), "a medal that is gone would be offered without a name")

    # victory points
    def points(v):
        out, states = {}, 0
        for _key, (layer, full, _rel) in sorted(v.files("history/states", ".txt").items()):
            text = without_comments(guiparse.read_text(full))
            state = re.search(r"\bid\s*=\s*(\d+)", text)
            if not state:
                continue
            states += 1
            for m in re.finditer(r"victory_points\s*=\s*\{\s*(\d+)\s+([\d.]+)\s*\}", text):
                out[int(m.group(1))] = (int(state.group(1)), int(float(m.group(2))), layer)
        return out, states

    # script takes the table of the map that has as many states as the loaded game (tools/build_records.py)
    now, states = points(view)
    rows, source = VICTORY_POINTS, "the game's table"
    for name, count, points_of_map in MAPS:
        if count == states:
            rows, source = points_of_map, "the table of " + name
    table = dict((p, (s, v)) for p, s, v in rows)
    say("victory points: the playset has %d states, so script follows %s" % (states, source))
    gone = sorted(p for p in table if p not in now)
    moved = sorted(p for p in table if p in now and now[p][0] != table[p][0])
    valued = sorted(p for p in table if p in now and now[p][1] != table[p][1])
    new = sorted(p for p in now if p not in table)
    say("victory points (War Diary): the table has %d; the playset has %d" % (len(table), len(now)))
    say("    in the table, no victory point in the playset: %d %s" % (len(gone), few(gone, 10)))
    say("    in another state in the playset: %d %s" % (len(moved), few(moved, 10)))
    say("    another value in the playset: %d %s" % (len(valued), few(valued, 10)))
    by_mod = {}
    for p in new:
        by_mod.setdefault(now[p][2].name, []).append(p)
    say("    in the playset, not in the table (no line when one changes hands; a point without a name cannot be in it): %d" % len(new))
    for mod, ps in sorted(by_mod.items()):
        say("        [%s] %d: %s" % (mod, len(ps), few(ps, 10)))

    # characters
    paths = [full for _key, (_layer, full, _rel) in sorted(view.files("common/characters", ".txt").items())]
    owner = dict((full, layer) for _key, (layer, full, _rel) in view.files("common/characters", ".txt").items())
    rows = {}
    for path in paths:
        for row in portraits(None, by_effect=True, paths=[path]):
            rows[row[0]] = (row, owner[path])
    known = dict((row[0], row) for row in list(PORTRAITS) + list(MOD_PORTRAITS))
    officer = ("corps_commander", "field_marshal", "navy_leader", "country_leader")
    missing, repainted = {}, {}
    for name, (row, layer) in rows.items():
        if not any(role in row[5] for role in officer):
            continue
        if name not in known:
            missing.setdefault(layer.name, []).append(name)
        elif tuple(known[name][2:5]) != tuple(row[2:5]):
            repainted.setdefault(layer.name, []).append(name)
    say("characters (portraits in the Records): the tables have %d; the playset has %d with a portrait and a role"
        % (len(known), len(rows)))
    for mod, names in sorted(missing.items()):
        say("    no row in the tables (shown without a portrait), from [%s]: %d: %s" % (mod, len(names), few(sorted(names), 6)))
    for mod, names in sorted(repainted.items()):
        say("    another portrait in the playset than in the tables, from [%s]: %d: %s" % (mod, len(names), few(sorted(names), 6)))
    if not missing and not repainted:
        say("    every officer and head of government of the playset has the row the playset gives him")
    replaced = [layer.name for layer in view.mods if "common/characters" in layer.replace]
    if replaced:
        say("    replace_path on common/characters: " + ", ".join(replaced))


# ---------------------------------------------------------------- main


def main(argv):
    game = guiparse.find_game_dir()
    if not game:
        print("game folder not found")
        return 2
    detail = out_file = None
    wanted = []
    args = list(argv)
    while args:
        arg = args.pop(0)
        if arg == "--window":
            detail = args.pop(0)
        elif arg == "--out":
            out_file = args.pop(0)
        elif arg in PARTS:
            wanted.append(arg)
        else:
            print(__doc__)
            return 2
    wanted = wanted or PARTS
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    layers, unread, source = playset(guiparse.user_dir())
    view = View(game, layers)
    if detail:
        part_windows(view, mod_guis(view), detail)
        return 0
    if "playset" in wanted:
        head("playset: %d mods beside this one (%s)" % (len(view.mods), source))
        for n, layer in enumerate(layers):
            notes = ["for " + layer.supported] if layer.supported else []
            if layer.replace:
                notes.append("replace_path " + " ".join(layer.replace))
            say("%3d  %s%s%s" % (n + 1, layer.name, "   <- this mod" if layer.mine else "", "   (" + "; ".join(notes) + ")" if notes else ""))
        for line in unread:
            say("  !! not read: " + line)
        if not any(layer.mine for layer in layers):
            say("  !! this mod is not in the playset")
        elif not layers[-1].mine:
            say("  !! this mod is not the last of the playset")
    guis = mod_guis(view) if set(wanted) & set(["windows", "hotkeys", "guis"]) else []
    if "windows" in wanted:
        part_windows(view, guis)
    if "sprites" in wanted:
        part_sprites(view)
    if "fonts" in wanted:
        part_fonts(view)
    if "hotkeys" in wanted:
        part_hotkeys(view, guis)
    if "guis" in wanted:
        part_guis(view, guis)
    if "content" in wanted:
        part_content(view)
    if out_file:
        io.open(out_file, "w", encoding="utf-8", newline="\n").write("\n".join(OUT) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
