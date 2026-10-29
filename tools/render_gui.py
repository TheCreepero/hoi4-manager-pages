"""Draw a HOI4 window, or a whole screen, from the mod's .gui files before any game launch.

    python -I tools/render_gui.py army_division_view                 one top-level window (mod file first, then vanilla)
    python -I tools/render_gui.py army_division_list_view --bounds   with every named widget outlined and labelled
    python -I tools/render_gui.py --scene army_selection             every window of tools/scenes/army_selection.json
    python -I tools/render_gui.py --scene army_selection --over      ... composed over the scene's vanilla screenshot
    python -I tools/render_gui.py <window> --expand divisions        with that dropdown opened
    python -I tools/render_gui.py <window> --report                  print the absolute rectangle of every named widget
    python -I tools/render_gui.py --batch jobs.json                  many calls in one process (the Pester suites)

Output goes to scratch/previews/: <name>.png at 1:1 and <name>@2x.png, or <scene>_scene.png and <scene>_crop.png.
Texts come from the scene's samples, else from the English localisation of a literal text key, else nothing
(the widget name in --bounds mode). Grids and lists are filled with the rows named in tools/gui-links.json.

What the renderer knows about the engine is listed in wiki/Engine-Facts.md; what it cannot know is printed
after every render: widgets the engine positions in code are drawn where the file puts them.
"""

import argparse
import json
import os
import pickle
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import guiparse as gp  # noqa: E402

from PIL import Image, ImageDraw  # noqa: E402

REPO_ROOT = gp.REPO_ROOT
PREVIEW_DIR = os.path.join(REPO_ROOT, "scratch", "previews")
SCREEN = (2560, 1440)

CONTAINERS = {"containerwindowtype", "windowtype", "expandedwindow", "positiontype_container"}
TEXTS = {"instanttextboxtype", "textboxtype", "editboxtype"}
BUTTONS = {"buttontype", "guibuttontype", "checkboxtype", "expandbutton"}
ICONS = {"icontype"}
LISTS = {"smoothlistboxtype", "listboxtype"}
GRIDS = {"gridboxtype"}
SCROLLBARS = {"extendedscrollbartype", "scrollbartype"}
SKIP = {"background", "positiontype", "overlappingelementsboxtype", "slider", "track", "decreasebutton", "increasebutton"}

BOUNDS_COLORS = {
    "container": (80, 200, 255, 255),
    "text": (255, 220, 80, 255),
    "button": (255, 120, 120, 255),
    "icon": (180, 255, 120, 255),
    "list": (255, 140, 255, 255),
    "grid": (255, 140, 255, 255),
    "other": (200, 200, 200, 255),
}


class Rect:
    __slots__ = ("x", "y", "w", "h")

    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h

    @property
    def right(self):
        return self.x + self.w

    @property
    def bottom(self):
        return self.y + self.h

    def box(self):
        return (int(round(self.x)), int(round(self.y)), int(round(self.x + self.w)), int(round(self.y + self.h)))

    def intersect(self, other):
        if other is None:
            return self
        x1, y1 = max(self.x, other.x), max(self.y, other.y)
        x2, y2 = min(self.right, other.right), min(self.bottom, other.bottom)
        return Rect(x1, y1, max(0, x2 - x1), max(0, y2 - y1))

    def __repr__(self):
        return "(%d,%d %dx%d)" % (self.x, self.y, self.w, self.h)


# ---------------------------------------------------------------- window index


class WindowIndex:
    """Top-level window name -> .gui file. Mod files first (they win), then every vanilla file."""

    def __init__(self, game_dir, mod_dir, vanilla_only=False):
        self.game_dir = game_dir
        self.mod_dir = mod_dir
        self.mod = {}
        self.vanilla = {}
        self._roots = {}
        if not vanilla_only:   # --vanilla: lay the screen out as the game does without the mod
            for path in self._gui_files(os.path.join(mod_dir, "interface")):
                for w in gp.top_level_windows(self._root(path)):
                    self.mod.setdefault(w.name, path)
        if game_dir:
            self.vanilla = self._vanilla_index()

    @staticmethod
    def _gui_files(folder):
        out = []
        for dirpath, _dirs, files in os.walk(folder):
            for f in files:
                if f.lower().endswith(".gui"):
                    out.append(os.path.join(dirpath, f))
        return sorted(out)

    def _root(self, path):
        if path not in self._roots:
            self._roots[path] = gp.parse_file(path)
        return self._roots[path]

    def _vanilla_index(self):
        files = self._gui_files(os.path.join(self.game_dir, "interface"))
        stamp = [(p, os.path.getmtime(p), os.path.getsize(p)) for p in files]
        cache_dir = os.path.join(self.mod_dir, "scratch", "cache")
        os.makedirs(cache_dir, exist_ok=True)
        cache_path = os.path.join(cache_dir, "windows.pickle")
        try:
            with open(cache_path, "rb") as handle:
                cached = pickle.load(handle)
            if cached.get("stamp") == stamp:
                return cached["index"]
        except Exception:
            pass
        index = {}
        for path in files:
            try:
                root = gp.parse_file(path)
            except Exception:
                continue
            for w in gp.top_level_windows(root):
                index.setdefault(w.name, path)
        with open(cache_path, "wb") as handle:
            pickle.dump({"stamp": stamp, "index": index}, handle)
        return index

    def find(self, name, prefer_file=None):
        """(node, path, source_lines) for a window, or (None, None, None)."""
        candidates = []
        if prefer_file:
            candidates.append(prefer_file)
        if name in self.mod:
            candidates.append(self.mod[name])
        if name in self.vanilla:
            candidates.append(self.vanilla[name])
        for path in candidates:
            if not path or not os.path.isfile(path):
                continue
            root = self._root(path)
            for w in gp.top_level_windows(root):
                if w.name == name:
                    lines = gp.read_text(path).replace("\r\n", "\n").split("\n")
                    return w, path, lines
        return None, None, None

    def variables(self, path):
        """@name -> value defined in a .gui file: at file level, or inside a window (naviesview.gui
        defines @nv_tb_btn_y inside its toolbar, and that definition travels with the window)."""
        out = {}
        for block in self._root(path).walk():
            for child in block.children or []:
                if child.children is None and child.key.startswith("@") and child.value is not None:
                    out.setdefault(child.key, child.value)
        return out


# ---------------------------------------------------------------- renderer


_window_indexes = {}


def window_index(game_dir, mod_dir, vanilla_only):
    """One WindowIndex per process and mode: the batch mode runs many renders, and the index only grows."""
    key = (game_dir, mod_dir, bool(vanilla_only))
    if key not in _window_indexes:
        _window_indexes[key] = WindowIndex(game_dir, mod_dir, vanilla_only=vanilla_only)
    return _window_indexes[key]


class Renderer:
    def __init__(self, game_dir, mod_dir=REPO_ROOT, scene=None, links=None, options=None):
        self.game_dir = game_dir
        self.mod_dir = mod_dir
        self.scene = scene or {}
        self.options = options or {}
        self.links = links or load_links(mod_dir)
        self.sprites = gp.load_sprites(game_dir, mod_dir)
        self.font_decls = gp.font_declarations(game_dir, mod_dir)
        self.loc = gp.load_localisation(game_dir, mod_dir)
        self.vanilla_only = bool(self.options.get("vanilla"))
        self.windows = window_index(game_dir, mod_dir, self.vanilla_only)
        self.located = []   # (window that defines the widget, widget name, Rect), in drawing order
        self.textures = {}
        self._window = None
        self._deferred = []
        self.warnings = []
        self.bounds = []
        self.report = []
        self.text_checks = []
        self.notes = set()
        self._source_lines = {}
        self.missing_sprites = set()
        self.variables = {}
        self.expand = set(self.options.get("expand") or [])
        # a named state of the scene: one of its captures, which may say what the screen shows then
        # ("hide" per window, "rows", "samples", "expand"); it is laid over the scene's own values
        self.state = {}
        wanted = self.options.get("state")
        if wanted:
            # "states" are states the renderer can draw but the harness cannot bring up (an HQ division)
            for capture in (self.scene.get("captures") or []) + (self.scene.get("states") or []):
                if capture.get("name") == wanted:
                    self.state = capture
            if not self.state:
                self.warn("the scene has no capture or state named %s; drawing its default state" % wanted)
        self.expand |= set(self.state.get("expand") or [])
        self._containers = []      # names of the containers being drawn, outermost first
        self._sample_index = {}    # (window, widget) -> how many instances took a text from a sample list
        # widgets the game code hides or moves: per window, from the scene ("hide", "place") and the CLI
        self.hidden = set()
        self.placements = {}
        state_hide = self.state.get("hide") or {}
        state_place = self.state.get("place") or {}     # d7-top-bar: a state may move widgets too (script's x)
        for w in self.scene.get("windows") or []:
            for n in (state_hide[w["name"]] if w["name"] in state_hide else (w.get("hide") or [])):
                self.hidden.add((w["name"], n))
            for n, at in list((w.get("place") or {}).items()) + list((state_place.get(w["name"]) or {}).items()):
                self.placements[(w["name"], n)] = (float(at[0]), float(at[1]))
        for n in self.options.get("hide") or []:
            self.hidden.add(("*", n))
        for n, at in (self.options.get("place") or {}).items():
            self.placements[("*", n)] = at
        # containers the code fills from left to right instead of top to bottom (composition counters)
        self.across = set()
        for w in self.scene.get("windows") or []:
            self.across |= set(w.get("rowsAcross") or [])
        self.clip_default = self.options.get("clip_default", "no") == "yes"
        self.frame_override = self.options.get("frame")
        # frames the code picks for single widgets (a selected row): "frames" per window in the scene, and
        # per window name in a state, which wins
        self.frames = {}
        state_frames = self.state.get("frames") or {}
        for w in self.scene.get("windows") or []:
            for n, f in (state_frames.get(w["name"]) or w.get("frames") or {}).items():
                # --- E4 round 2 --- a list gives one frame per instance, in drawing order (the plates of a list of rows)
                self.frames[(w["name"], n)] = [int(v) for v in f] if isinstance(f, list) else int(f)
        self._frame_index = {}
        # --- D2 round 2 --- widgets script shows in some rows of a list only (the band of every second row,
        # the chosen row): "only" per window, {widget: [instance numbers from 0, in drawing order]}; a state's
        # "only" of a window replaces the window's own
        self.only = {}
        self._only_index = {}
        state_only = self.state.get("only") or {}
        for w in self.scene.get("windows") or []:
            for n, rows in (state_only.get(w["name"]) if w["name"] in state_only else (w.get("only") or {})).items():
                self.only[(w["name"], n)] = set(int(r) for r in rows)
        # --- end D2 round 2 ---
        # --- D4 round 2 --- how far script fills a bar in each row (the columns of a graph, a sparkline): "fills"
        # per window, {widget: [0 to 1 per instance, in drawing order]}; an upright bar fills from its foot. A
        # state's "fills" of a window replaces the window's own.
        self.fills = {}
        self._fill_index = {}
        state_fills = self.state.get("fills") or {}
        for w in self.scene.get("windows") or []:
            for n, values in (state_fills.get(w["name"]) if w["name"] in state_fills else (w.get("fills") or {})).items():
                self.fills[(w["name"], n)] = [float(v) for v in values]
        # --- end D4 round 2 ---

    # ------------------------------------------------------------ helpers

    def warn(self, text):
        if text not in self.warnings:
            self.warnings.append(text)

    def value(self, raw):
        """A leaf value with @variables substituted."""
        if raw is None:
            return None
        if raw.startswith("@"):
            if raw in self.variables:
                return self.variables[raw]
            self.warn("variable %s is not defined in the override file (see gui-links.json 'variables')" % raw)
            return None
        return raw

    def num(self, node, block_key, key, parent_extent=None, default=0.0):
        block = node.block(block_key) if block_key else node
        if block is None:
            return default
        raw = self.value(block.get(key))
        if raw is None:
            return default
        pct = gp.percent(raw)
        if pct is not None:
            return abs(pct) * (parent_extent or 0)
        return gp.number(raw, default)

    def size_of(self, node, parent, default=None):
        """size = { width height } or { x y }, percentages against the parent."""
        block = node.block("size")
        if block is None:
            return default
        w = block.get("width")
        h = block.get("height")
        if w is None and h is None:
            w, h = block.get("x"), block.get("y")
        wv = self.num(block, None, "width", parent.w, None) if block.get("width") is not None else self.num(block, None, "x", parent.w, None)
        hv = self.num(block, None, "height", parent.h, None) if block.get("height") is not None else self.num(block, None, "y", parent.h, None)
        if wv is None and hv is None:
            return default
        # a negative size is the parent's less that much: the naval losses window is "height = -165",
        # the screen's height less 165
        if wv is not None and wv < 0:
            wv = max(0.0, parent.w + wv)
        if hv is not None and hv < 0:
            hv = max(0.0, parent.h + hv)
        return (wv or 0.0, hv or 0.0)

    def texture(self, sprite):
        """The sprite's first texture as an RGBA image, or None (warned once)."""
        if sprite.name in self.textures:
            return self.textures[sprite.name]
        img = None
        rel = sprite.texture
        if rel:
            stem, ext = os.path.splitext(rel)
            tried = []
            for base in (self.mod_dir, self.game_dir):
                if not base:
                    continue
                for candidate_ext in (ext, ".dds", ".tga", ".png"):
                    candidate = os.path.join(base, *(stem + candidate_ext).split("/"))
                    tried.append(candidate)
                    if os.path.isfile(candidate):
                        try:
                            img = gp.load_image(candidate, self.mod_dir)
                        except Exception as exc:
                            self.warn("texture %s of %s cannot be read: %s" % (candidate, sprite.name, exc))
                        break
                if img is not None:
                    break
            if img is None:
                self.warn("texture %s of sprite %s not found" % (rel, sprite.name))
        else:
            self.warn("sprite %s has no texturefile" % sprite.name)
        self.textures[sprite.name] = img
        return img

    def sprite(self, name):
        if not name:
            return None
        sprite = self.sprites.get(name)
        if sprite is None:
            self.missing_sprites.add(name)
            self.warn("sprite %s is not declared in any .gfx file" % name)
        return sprite

    def frame_image(self, sprite, frame=1):
        img = self.texture(sprite)
        if img is None:
            return None
        frames = max(1, sprite.frames)
        if frames == 1:
            return img
        fw = img.width // frames
        frame = max(1, min(frames, int(frame)))
        return img.crop(((frame - 1) * fw, 0, frame * fw, img.height))

    def sprite_size(self, sprite, frame=1):
        """Pixel size a sprite is drawn at when the widget gives no size."""
        if sprite is None:
            return (16.0, 16.0)
        if sprite.kind.lower() == "corneredtilespritetype" and sprite.size and sprite.size[0]:
            return (sprite.size[0], sprite.size[1])
        if sprite.kind.lower() == "progressbartype" and sprite.size and sprite.size[0]:
            return (sprite.size[0], sprite.size[1])
        img = self.frame_image(sprite, frame)
        if img is None:
            return (16.0, 16.0)
        return (float(img.width), float(img.height))

    def nine_slice(self, img, border, w, h, tiling_center):
        """Stretch or tile an image into w x h keeping its borders (corneredTileSpriteType)."""
        w, h = max(1, int(round(w))), max(1, int(round(h)))
        bx = int(min(border[0], img.width // 2))
        by = int(min(border[1], img.height // 2))
        out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        src_cols = [(0, bx), (bx, img.width - bx), (img.width - bx, img.width)]
        src_rows = [(0, by), (by, img.height - by), (img.height - by, img.height)]
        dst_cols = [(0, bx), (bx, w - bx), (w - bx, w)]
        dst_rows = [(0, by), (by, h - by), (h - by, h)]
        for ri, (sy1, sy2) in enumerate(src_rows):
            for ci, (sx1, sx2) in enumerate(src_cols):
                sw, sh = sx2 - sx1, sy2 - sy1
                dx1, dx2 = dst_cols[ci]
                dy1, dy2 = dst_rows[ri]
                dw, dh = dx2 - dx1, dy2 - dy1
                if sw <= 0 or sh <= 0 or dw <= 0 or dh <= 0:
                    continue
                piece = img.crop((sx1, sy1, sx2, sy2))
                if (sw, sh) == (dw, dh):
                    out.alpha_composite(piece, (dx1, dy1))
                elif tiling_center and (ci == 1 or ri == 1):
                    for ty in range(dy1, dy2, sh):
                        for tx in range(dx1, dx2, sw):
                            tile = piece.crop((0, 0, min(sw, dx2 - tx), min(sh, dy2 - ty)))
                            out.alpha_composite(tile, (tx, ty))
                else:
                    out.alpha_composite(piece.resize((dw, dh), Image.BILINEAR), (dx1, dy1))
        return out

    def draw_sprite(self, canvas, sprite, rect, frame=1, scale=1.0, clip=None, rotation=0.0, fill=0.7, upright=False):
        """Draw a sprite into rect (rect.w/h may be None to use the sprite's own size). Returns the drawn Rect."""
        if sprite is None:
            return None
        kind = sprite.kind.lower()
        img = None
        if kind == "progressbartype":
            bg = None
            if len(sprite.textures) > 1:
                second = gp.Sprite.__new__(gp.Sprite)
                second.name, second.kind, second.texture, second.textures, second.frames = sprite.name + "#bg", "spriteType", sprite.textures[1], [sprite.textures[1]], 1
                second.size = second.border = None
                second.tiling_center = False
                second.file, second.line = sprite.file, sprite.line
                bg = self.texture(second)
            fg = self.frame_image(sprite, 1)
            size = (sprite.size if sprite.size and sprite.size[0] else (fg.size if fg else (28, 6)))
            w = rect.w if rect.w else size[0]
            h = rect.h if rect.h else size[1]
            img = Image.new("RGBA", (max(1, int(w)), max(1, int(h))), (0, 0, 0, 0))
            if bg is not None:
                img.alpha_composite(bg.resize(img.size, Image.BILINEAR))
            if fg is not None and upright and img.height > img.width:     # D4 round 2: a column fills from its foot
                tall = int(round(img.height * max(0.0, min(1.0, fill))))
                if tall > 0:
                    filled = fg.rotate(90, expand=True).resize(img.size, Image.BILINEAR).crop((0, img.height - tall, img.width, img.height))
                    img.alpha_composite(filled, (0, img.height - tall))
            elif fg is not None:
                filled = fg.resize(img.size, Image.BILINEAR).crop((0, 0, max(1, int(img.width * fill)), img.height))
                img.alpha_composite(filled)
        elif kind == "corneredtilespritetype":
            base = self.frame_image(sprite, frame)
            if base is None:
                return None
            w = rect.w if rect.w else (sprite.size[0] if sprite.size and sprite.size[0] else base.width)
            h = rect.h if rect.h else (sprite.size[1] if sprite.size and sprite.size[1] else base.height)
            border = sprite.border or (0, 0)
            img = self.nine_slice(base, border, w * scale, h * scale, sprite.tiling_center)
        else:
            base = self.frame_image(sprite, frame)
            if base is None:
                return None
            img = base
            if rect.w and rect.h and (int(rect.w) != base.width or int(rect.h) != base.height):
                img = base.resize((max(1, int(rect.w)), max(1, int(rect.h))), Image.BILINEAR)
            if scale and scale != 1.0:
                img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.BILINEAR)
        x, y = rect.x, rect.y
        if rotation and abs(abs(rotation) - 1.5708) < 0.05:
            # 90 degrees: the bar stands up from its anchor. The game draws an L x t bar left of the anchor's x,
            # its foot t below the anchor's y: x - t to x, y - (L - t) to y + t [GUL-013].
            img = img.rotate(90 if rotation > 0 else -90, expand=True)
            if rotation > 0:
                x = rect.x - img.width
                y = rect.y - img.height + img.width
        drawn = Rect(x, y, img.width, img.height)
        self.paste(canvas, img, drawn, clip)
        return drawn

    def paste(self, canvas, img, rect, clip):
        x, y = int(round(rect.x)), int(round(rect.y))
        if clip is not None:
            visible = Rect(x, y, img.width, img.height).intersect(clip)
            if visible.w <= 0 or visible.h <= 0:
                return
            if visible.w < img.width or visible.h < img.height:
                img = img.crop((int(visible.x - x), int(visible.y - y), int(visible.x - x + visible.w), int(visible.y - y + visible.h)))
                x, y = int(visible.x), int(visible.y)
        # alpha_composite needs the source inside the canvas
        cx1, cy1 = max(0, x), max(0, y)
        cx2, cy2 = min(canvas.width, x + img.width), min(canvas.height, y + img.height)
        if cx2 <= cx1 or cy2 <= cy1:
            return
        if (cx1, cy1, cx2, cy2) != (x, y, x + img.width, y + img.height):
            img = img.crop((cx1 - x, cy1 - y, cx2 - x, cy2 - y))
        canvas.alpha_composite(img, (cx1, cy1))

    def font(self, name):
        try:
            return gp.load_font(name, self.game_dir, self.mod_dir, self.font_decls)
        except FileNotFoundError:
            self.warn("font %s not found, using hoi_18" % name)
            return gp.load_font("hoi_18", self.game_dir, self.mod_dir, self.font_decls)

    def sample_text(self, window_name, widget_name, literal):
        for samples in (self.state.get("samples") or {}, self.scene.get("samples") or {}):
            for scope in (window_name, "*"):
                table = samples.get(scope) or {}
                if widget_name in table:
                    value = table[widget_name]
                    if isinstance(value, list):   # one text per instance, in drawing order (rows of a grid)
                        index = self._sample_index.get((window_name, widget_name), 0)
                        self._sample_index[(window_name, widget_name)] = index + 1
                        value = value[index % len(value)] if value else ""
                    # a text of the mod can hold a text key of the game between dollar signs
                    value = re.sub(r"[$]([A-Za-z0-9_]+)[$]", lambda m: self.loc.get(m.group(1), m.group(0)), str(value))
                    return value, "sample"
        if literal:
            if literal in self.loc:
                # a text can hold another text key between dollar signs; the colour codes and text icons stay
                value = re.sub(r"[$]([A-Za-z0-9_]+)[$]", lambda m: self.loc.get(m.group(1), m.group(0)), self.loc[literal])
                return (value if literal.startswith("MOD1440_") else gp.plain_text(value)), "loc"
            return gp.plain_text(literal), "literal"
        return None, None

    # ------------------------------------------------------------ layout

    def anchor(self, node, parent, size):
        """Absolute top-left of a widget from position, orientation and origo inside the parent rect."""
        placed = None
        for key in (self.list_keys(node.name) if node.name else [node.name]):
            # "parent/widget" first, for a window with several widgets of one name (the overview's item_grid)
            placed = self.placements.get((self._window, key)) or self.placements.get(("*", key))
            if placed is not None:
                break
        if placed is not None:
            return parent.x + placed[0], parent.y + placed[1]
        px = self.num(node, "position", "x", parent.w)
        py = self.num(node, "position", "y", parent.h)
        orientation = (self.value(node.get("orientation")) or "upper_left").lower()
        ox, oy = parent.x, parent.y
        if "right" in orientation:
            ox = parent.right
        elif orientation.startswith("center") and "left" not in orientation:
            ox = parent.x + parent.w / 2.0
        if orientation.startswith("lower") or orientation.endswith("down") or orientation.endswith("lower"):
            oy = parent.bottom
        elif orientation in ("center", "center_left", "center_right"):
            oy = parent.y + parent.h / 2.0
        x, y = ox + px, oy + py
        origo = (self.value(node.get("origo")) or "upper_left").lower()
        w, h = size
        if "right" in origo:
            x -= w
        elif origo.startswith("center") and "left" not in origo:
            x -= w / 2.0
        if origo.startswith("lower") or origo.endswith("down"):
            y -= h
        elif origo in ("center", "center_left", "center_right"):
            y -= h / 2.0
        if (self.value(node.get("centerPosition")) or "").lower() == "yes":
            x -= w / 2.0
            y -= h / 2.0
        return x, y

    # ------------------------------------------------------------ drawing

    def render_window(self, name, canvas, origin, prefer_file=None, depth=0, clip=None, instance_samples=None):
        """Draw a top-level window with its top-left at origin. Returns its Rect or None."""
        node, path, lines = self.windows.find(name, prefer_file)
        if node is None:
            self.warn("window %s is not defined in the mod or in vanilla" % name)
            return None
        if path and path not in self.variables:
            self.variables.update(self.windows.variables(path))
        parent = Rect(origin[0], origin[1], 0, 0)
        size = self.size_of(node, parent, default=(0.0, 0.0))
        rect = Rect(origin[0], origin[1], size[0], size[1])
        override = self.height_override(name)
        if override is not None:
            rect.h = float(override)
        elif lines and self.size_set_in_code(node, lines) and depth == 0:
            self.notes.add("%s: height %d is set in code; the game sizes it to its content up to this maximum (set 'height' in the scene or --height %s=N to see another)" % (name, rect.h, name))
        self._source_lines[name] = lines
        if depth == 0:
            self._sample_index = {}
            self._only_index = {}       # D2 round 2
            self._frame_index = {}      # E4 round 2
        outer = getattr(self, "_window", None)
        self._window = name
        self.draw_container(node, rect, canvas, name, depth, clip, window_rect=rect)
        if depth == 0:
            while self._deferred:
                child, child_rect, child_window, child_depth = self._deferred.pop(0)
                self._window = child_window
                self.draw_container(child, child_rect, canvas, child_window, child_depth, None)
        self._window = outer
        return rect

    def height_override(self, name):
        cli = (self.options.get("heights") or {}).get(name)
        if cli is not None:
            return cli
        for w in self.scene.get("windows") or []:
            if w.get("name") == name and w.get("height") is not None:
                return w["height"]
        return None

    @staticmethod
    def size_set_in_code(node, lines, also=None):
        """True when the comment on the size line says the size is set in code (and contains `also`)."""
        block = node.block("size")
        if block is None:
            return False
        for ln in range(block.line, min(block.end_line, block.line + 2) + 1):
            if 0 < ln <= len(lines):
                comment = lines[ln - 1].partition("#")[2]
                if re.search(r"set in code", comment, re.I) and (also is None or also.lower() in comment.lower()):
                    return True
        return False

    def record(self, kind, name, rect, node_type):
        self.bounds.append((kind, name, rect, node_type))
        self.report.append((name, node_type, rect))
        self.located.append((self._window, name, rect))

    def default_origin(self, name, prefer_file=None):
        """Where a top-level window lands on the screen when only the file places it: position, orientation, origo."""
        node, _path, _lines = self.windows.find(name, prefer_file)
        if node is None:
            return (0.0, 0.0)
        screen = Rect(0, 0, SCREEN[0], SCREEN[1])
        size = self.size_of(node, screen, default=(0.0, 0.0))
        outer = self._window
        self._window = name
        x, y = self.anchor(node, screen, size)
        self._window = outer
        return (x, y)

    def locate(self, spec):
        """The Rect of 'window/widget' or 'window/widget#n' (n-th drawn instance, from 0) after a layout, or None.

        The window is the top-level window that defines the widget: the row window for a widget of a row.
        'window' alone is the window's own rectangle; a bare 'widget' matches in any window.
        """
        path, _sep, index = spec.partition("#")
        index = int(index) if index else 0
        window, _sep, widget = path.rpartition("/")
        if not window:
            hits = [r for w, n, r in self.located if (w == path and n == path)]
            if not hits:
                hits = [r for w, n, r in self.located if n == path]
        else:
            hits = [r for w, n, r in self.located if w == window and n == widget]
        return hits[index] if index < len(hits) else None

    def draw_container(self, node, rect, canvas, window_name, depth, clip, window_rect=None):
        name = node.name or ""
        self.record("container", name, rect, node.key)
        clipping = self.value(node.get("clipping"))
        clips = (clipping or ("yes" if self.clip_default else "no")).lower() == "yes"
        if node.key.lower() in ("expandedwindow",):
            clips = True
        inner_clip = rect.intersect(clip) if clips else clip

        # a container can have several backgrounds (the History tab has a header panel, a strip and a
        # paper); each is drawn at its own position (wiki/Engine-Facts.md, S18), a tiled one at its own
        # size or the container's.
        for background in [b for b in node.blocks() if b.key.lower() == "background"]:
            # a second background the code shows in another state (the brown one of a decommissioned template)
            if background.name and ((window_name, background.name) in self.hidden or ("*", background.name) in self.hidden):
                continue
            sprite = self.sprite(self.value(background.get("quadTextureSprite")) or self.value(background.get("spriteType")))
            if sprite is None:
                continue
            bx = self.num(background, "position", "x", rect.w)
            by = self.num(background, "position", "y", rect.h)
            if sprite.kind.lower() == "corneredtilespritetype":
                own = self.size_of(background, rect, default=None)
                bw, bh = own if own is not None else (rect.w, rect.h)
                self.draw_sprite(canvas, sprite, Rect(rect.x + bx, rect.y + by, bw or rect.w, bh or rect.h), clip=inner_clip)
            else:
                self.draw_sprite(canvas, sprite, Rect(rect.x + bx, rect.y + by, None, None), clip=inner_clip)

        self._containers.append(name)
        for child in node.blocks():
            self.draw_child(child, rect, canvas, window_name, depth, inner_clip)
        self._containers.pop()

        # a container the code fills with rows (the division list's divisions_window) is drawn like a list
        rows = self.rows_for(window_name, name) if name else []
        if rows and node.key.lower() in CONTAINERS:
            self.fill_rows(rows, rect, canvas, window_name, name, depth, inner_clip, 0.0)

    def fill_rows(self, rows, rect, canvas, window_name, list_name, depth, inner_clip, spacing):
        count = self.row_count(window_name, list_name, default=None)
        across = list_name in self.across
        cx, cy = rect.x, rect.y
        i = 0
        while True:
            if count is not None and i >= count:
                break
            if count is None and (cx >= rect.right if across else cy >= rect.bottom):
                break
            row_rect = self.render_window(rows[i % len(rows)], canvas, (cx, cy), depth=depth + 1, clip=inner_clip)
            if row_rect is None or (row_rect.w if across else row_rect.h) <= 0:
                break
            if across:
                cx += row_rect.w + spacing
            else:
                cy += row_rect.h + spacing
            i += 1
            if i > 200:
                break

    def draw_child(self, child, parent, canvas, window_name, depth, clip):
        key = child.key.lower()
        cname = child.name or ""
        self._window = window_name
        if cname and ((window_name, cname) in self.hidden or ("*", cname) in self.hidden):
            return
        if cname and (window_name, cname) in self.only:        # D2 round 2: drawn in some instances only
            n = self._only_index.get((window_name, cname), 0)
            self._only_index[(window_name, cname)] = n + 1
            if n not in self.only[(window_name, cname)]:
                return
        if key in ("background", "positiontype", "slider", "track", "decreasebutton", "increasebutton", "backgroundbutton"):
            if key == "positiontype":
                px = self.num(child, "position", "x", parent.w)
                py = self.num(child, "position", "y", parent.h)
                self.bounds.append(("position", cname, Rect(parent.x + px, parent.y + py, 0, 0), child.key))
            return
        if key in ("size", "position", "margin", "slotsize", "show_position"):
            return
        if key in CONTAINERS or key == "dropdownboxtype" or key == "overlappingelementsboxtype":
            size = self.size_of(child, parent, default=None)
            if size is None:
                size = (parent.w, parent.h) if key != "dropdownboxtype" else (0.0, 0.0)
            x, y = self.anchor(child, parent, size)
            lines = self._source_lines.get(window_name)
            if key in CONTAINERS and lines and self.size_set_in_code(child, lines, "match the window"):
                # "Y set in code to match the window size": the child takes the rest of its parent
                size = (size[0] or parent.w, max(1.0, parent.bottom - y))
            rect = Rect(x, y, size[0], size[1])
            if key == "expandedwindow":
                if cname not in self.expand and (child.name or "") not in self.expand and not self.expand_parent(child):
                    return
                show = child.block("show_position")
                if show is not None:
                    rect = Rect(parent.x + gp.number(show.get("x"), 0), parent.y + gp.number(show.get("y"), 0), size[0], size[1])
                # an opened dropdown draws above everything else in its window (expandedOnTop)
                self._deferred.append((child, rect, window_name, depth + 1))
                return
            if key == "overlappingelementsboxtype":
                self.record("other", cname, rect, child.key)
                return
            if key == "dropdownboxtype":
                self.record("container", cname, rect, child.key)
                self._current_dropdown = cname
                for grand in child.blocks():
                    self.draw_child(grand, rect, canvas, window_name, depth + 1, clip)
                self._current_dropdown = None
                return
            self.draw_container(child, rect, canvas, window_name, depth + 1, clip)
            return
        if key in TEXTS:
            self.draw_text(child, parent, canvas, window_name, clip)
            return
        if key in BUTTONS or key in ICONS:
            self.draw_sprite_widget(child, parent, canvas, window_name, clip, key)
            return
        if key in LISTS:
            self.draw_list(child, parent, canvas, window_name, depth, clip)
            return
        if key in GRIDS:
            self.draw_grid(child, parent, canvas, window_name, depth, clip)
            return
        if key in SCROLLBARS:
            self.draw_scrollbar(child, parent, canvas, clip)
            return
        if child.name:
            size = self.size_of(child, parent, default=(0.0, 0.0))
            x, y = self.anchor(child, parent, size)
            self.record("other", cname, Rect(x, y, size[0], size[1]), child.key)

    def expand_parent(self, expanded_node):
        return getattr(self, "_current_dropdown", None) in self.expand

    def draw_sprite_widget(self, node, parent, canvas, window_name, clip, key):
        name = node.name or ""
        sprite_name = self.value(node.get("quadTextureSprite")) or self.value(node.get("spriteType"))
        sprite = self.sprite(sprite_name)
        frame = int(gp.number(self.value(node.get("frame")), 1) or 1)
        picked = self.frames.get((window_name, name))
        if isinstance(picked, list):    # E4 round 2: one frame per instance
            k = self._frame_index.get((window_name, name), 0)
            self._frame_index[(window_name, name)] = k + 1
            picked = picked[k % len(picked)] if picked else None
        if picked and sprite is not None and sprite.frames >= picked:
            frame = picked
        if self.frame_override and sprite is not None and sprite.frames >= self.frame_override:
            frame = self.frame_override
        scale = gp.number(self.value(node.get("scale")), 1.0) or 1.0
        explicit = self.size_of(node, parent, default=None)
        if explicit is not None and explicit[0] and explicit[1]:
            size = explicit
        else:
            size = self.sprite_size(sprite, frame)
            size = (size[0] * scale, size[1] * scale)
        x, y = self.anchor(node, parent, size)
        rect = Rect(x, y, size[0], size[1])
        rotation = gp.number(self.value(node.get("rotation")), 0.0) or 0.0
        if sprite is not None:
            target = Rect(x, y, size[0] if explicit else None, size[1] if explicit else None)
            if sprite.kind.lower() == "corneredtilespritetype" and not explicit:
                target = Rect(x, y, size[0], size[1])
            fill = {}
            if (window_name, name) in self.fills:      # D4 round 2: this row's fill of a bar script fills
                k = self._fill_index.get((window_name, name), 0)
                self._fill_index[(window_name, name)] = k + 1
                values = self.fills[(window_name, name)]
                fill = {"fill": values[k % len(values)] if values else 0.0, "upright": True}
            drawn = self.draw_sprite(canvas, sprite, target, frame=frame, scale=1.0 if explicit else scale, clip=clip, rotation=rotation, **fill)
            if drawn is not None:
                rect = drawn
        else:
            self.outline(canvas, rect, (255, 0, 255, 255), clip)
        kind = "icon" if key in ICONS else "button"
        self.record(kind, name, rect, node.key)
        text_key = self.value(node.get("buttonText"))
        if text_key:
            text, _src = self.sample_text(window_name, name, text_key)
            font = self.font(self.value(node.get("buttonFont")) or self.value(node.get("font")) or "hoi_18mbs")
            if text:
                tw = self.text_width(font, text)
                tx = rect.x + (rect.w - tw) / 2.0
                ty = rect.y + (rect.h - font.line_height) / 2.0
                self.draw_text_line(canvas, font, tx, ty, text, clip)

    # The colours of the game's text codes (the textcolors block of interface/core.gfx): a section sign and
    # a letter sets one, a section sign and "!" gives the font's own colour back.
    TEXT_COLOURS = {"W": (255, 255, 255), "T": (255, 255, 255), "Y": (255, 189, 0), "H": (255, 189, 0), "G": (0, 159, 3),
                    "R": (255, 50, 50), "g": (176, 176, 176), "L": (195, 176, 145), "C": (35, 206, 255), "O": (255, 112, 25),
                    "B": (0, 0, 255), "b": (0, 0, 0)}
    RICH = re.compile("§(.)|£([A-Za-z0-9_]+)(?:\\|(\\d+))?")

    def pieces(self, text):
        """A line as the game draws it: ("text", colour or None, string) and ("icon", image or None) pieces.
        A pound sign and a sprite name, with or without GFX_ and with "|frame" for a strip, is a text icon."""
        out, colour, at = [], None, 0
        for m in self.RICH.finditer(text):
            if m.start() > at:
                out.append(("text", colour, text[at:m.start()]))
            if m.group(1) is not None:
                colour = self.TEXT_COLOURS.get(m.group(1))
            else:
                name = m.group(2)
                sprite = self.sprites.get(name if name.startswith("GFX_") else "GFX_" + name) or self.sprites.get(name)
                out.append(("icon", self.frame_image(sprite, int(m.group(3) or 1)) if sprite is not None else None))
            at = m.end()
        if at < len(text):
            out.append(("text", colour, text[at:]))
        return out

    def text_width(self, font, text):
        """Width of a line with its colour codes taken out and its text icons at their own width."""
        if "§" not in text and "£" not in text:
            return font.width(text)
        total = 0
        for piece in self.pieces(text):
            if piece[0] == "text":
                total += font.width(piece[2])
            else:
                total += piece[1].width if piece[1] is not None else 24
        return total

    def draw_text_line(self, canvas, font, x, y, text, clip):
        layer = Image.new("RGBA", (max(1, int(self.text_width(font, text) + 4)), max(1, font.line_height + 8)), (0, 0, 0, 0))
        cursor = 0
        for piece in self.pieces(text):
            if piece[0] == "text":
                cursor += font.draw(layer, cursor, 4, piece[2], piece[1] + (255,) if piece[1] else None)
            elif piece[1] is not None:
                # an icon stands on the middle of the line
                layer.alpha_composite(piece[1], (int(cursor), max(0, int(4 + (font.line_height - piece[1].height) / 2.0))))
                cursor += piece[1].width
            else:
                cursor += 24
        self.paste(canvas, layer, Rect(x, y - 4, layer.width, layer.height), clip)

    def draw_text(self, node, parent, canvas, window_name, clip):
        name = node.name or ""
        font = self.font(self.value(node.get("font")) or "hoi_18mbs")
        max_w = gp.number(self.value(node.get("maxWidth")), None)
        max_h = gp.number(self.value(node.get("maxHeight")), None)
        explicit = self.size_of(node, parent, default=None)
        if explicit is not None:
            max_w = max_w or explicit[0]
            max_h = max_h or explicit[1]
        text, source = self.sample_text(window_name, name, self.value(node.get("text")))
        lines = []
        if text:
            lines = self.wrap(font, text, max_w)
        w = max_w if max_w else (self.text_width(font, text) if text else 60.0)
        line_count = max(1, len(lines))
        fits = int(max_h // font.line_height) if max_h else line_count
        fits = max(1, fits)
        truncated = False
        if text and len(lines) > fits:
            if fits == 1:
                lines = [self.truncate(font, text.replace("\n", " "), max_w)]
            else:
                lines = lines[:fits]
            truncated = True
        h = max_h if max_h else font.line_height * line_count
        x, y = self.anchor(node, parent, (w, h))
        rect = Rect(x, y, w, h)
        self.record("text", name, rect, node.key)
        if text:
            fmt = (self.value(node.get("format")) or "left").lower()
            for i, line in enumerate(lines):
                lw = self.text_width(font, line)
                lx = x
                if fmt in ("center", "centre", "up", "down") and max_w:
                    lx = x + (max_w - lw) / 2.0
                elif fmt in ("right", "upper_right", "lower_right") and max_w:
                    lx = x + max_w - lw
                self.draw_text_line(canvas, font, lx, y + i * font.line_height, line, clip)
            full = self.text_width(font, text.replace("\n", " "))
            # only texts someone chose are judged: scene samples and the mod's own captions. A vanilla
            # placeholder text ("Auto ($EQUIPMENT_CATEGORY$)") is replaced by the code at run time.
            judged = source == "sample" or name.startswith("mod1440_")
            if max_w and full > max_w and judged:
                verdict = "cut off" if truncated else "wrapped"
                # a text the design knowingly cuts off: listed in the scene, with the reason
                if truncated and any(c.get("widget") == "%s/%s" % (window_name, name) and c.get("text") == text for c in self.scene.get("knownCuts") or []):
                    verdict = "cut (known)"
                self.report_text(window_name, name, text, font, full, max_w, verdict)
            elif max_w and judged:
                self.report_text(window_name, name, text, font, full, max_w, "fits")

    def report_text(self, window_name, name, text, font, width, max_w, verdict):
        self.text_checks.append((window_name, name, text, os.path.basename(font.path).replace(".fnt", ""), int(width), int(max_w), verdict))

    def wrap(self, font, text, max_w):
        lines = []
        for paragraph in text.split("\n"):
            if not max_w:
                lines.append(paragraph)
                continue
            words = paragraph.split(" ")
            current = ""
            for word in words:
                trial = word if not current else current + " " + word
                if self.text_width(font, trial) <= max_w or not current:
                    current = trial
                else:
                    lines.append(current)
                    current = word
            lines.append(current)
        return lines

    def truncate(self, font, text, max_w):
        if not max_w or self.text_width(font, text) <= max_w:
            return text
        ellipsis = "..."
        while text and self.text_width(font, text + ellipsis) > max_w:
            text = text[:-1]
        return text.rstrip() + ellipsis

    def draw_list(self, node, parent, canvas, window_name, depth, clip):
        name = node.name or ""
        size = self.size_of(node, parent, default=(parent.w, parent.h))
        x, y = self.anchor(node, parent, size)
        rect = Rect(x, y, size[0], size[1] if size[1] else parent.h - (y - parent.y))
        self.record("list", name, rect, node.key)
        rows = self.rows_for(window_name, name)
        if not rows:
            return
        spacing = gp.number(self.value(node.get("spacing")), 0.0) or 0.0
        self.fill_rows(rows, rect, canvas, window_name, name, depth, rect.intersect(clip), spacing)
        scrollbar = self.value(node.get("scrollbartype"))
        if scrollbar:
            self.draw_named_scrollbar(scrollbar, rect, canvas, clip)

    def draw_grid(self, node, parent, canvas, window_name, depth, clip):
        name = node.name or ""
        size = self.size_of(node, parent, default=(parent.w, parent.h))
        x, y = self.anchor(node, parent, size)
        rect = Rect(x, y, size[0], size[1])
        self.record("grid", name, rect, node.key)
        slot = node.block("slotsize")
        sw = self.num(slot, None, "width", parent.w, 0.0) if slot else 0.0
        sh = self.num(slot, None, "height", parent.h, 0.0) if slot else 0.0
        entries = self.rows_for(window_name, name)
        if not entries or not sw or not sh:
            return
        cols = int(gp.number(self.value(node.get("max_slots_horizontal")), 0) or 0)
        if cols <= 0 and sw < 2 and (self.value(node.get("add_horizontal")) or "").lower() == "no":
            # a scripted list: a slot of 1x1 that does not run sideways is one column (wiki/Engine-Facts.md, X10)
            cols = 1
        if cols <= 0:
            cols = max(1, int(rect.w // sw)) if rect.w else 1
        count = self.row_count(window_name, name, default=None)
        if count is None:
            count = cols * (max(1, int(rect.h // sh)) if rect.h else 3)
        fmt = (self.value(node.get("format")) or "upper_left").lower()
        inner_clip = clip
        if sh < 2 and cols == 1:
            # a slot one pixel high: the code stacks the entries by their own height and honours each
            # entry window's own position (wiki/Engine-Facts.md, S27). The scene's listRows is then
            # the sequence of rows, which may mix several row windows (the deployment list).
            cy = rect.y
            for i in range(min(count, 200)):
                entry = entries[i % len(entries)]
                entry_node, _path, _lines = self.windows.find(entry)
                if entry_node is None:
                    break
                ox = self.num(entry_node, "position", "x")
                oy = self.num(entry_node, "position", "y")
                entry_rect = self.render_window(entry, canvas, (rect.x + ox, cy + oy), depth=depth + 1, clip=inner_clip)
                if entry_rect is None or entry_rect.h <= 0:
                    break
                cy += entry_rect.h
            return
        for i in range(count):
            col, row = i % cols, i // cols
            ex = rect.x + col * sw
            ey = rect.y + row * sh
            if "right" in fmt:
                ex = rect.right - (col + 1) * sw
            if "lower" in fmt or fmt == "up":
                ey = rect.bottom - (row + 1) * sh
            self.render_window(entries[i % len(entries)], canvas, (ex, ey), depth=depth + 1, clip=inner_clip)

    def list_keys(self, list_name):
        """The names a list goes by in a scene and in gui-links.json: "parent/list" first, then "list".

        The parent is the nearest named container around it. A window with several lists of one name
        (the three stat columns and the adjuster grid of a details window are all "stats_grid") needs
        the longer form.
        """
        parents = [n for n in self._containers if n]
        return (["%s/%s" % (parents[-1], list_name)] if parents else []) + [list_name]

    def rows_for(self, window_name, list_name):
        """Row windows for a list or grid: the scene's listRows first, then gui-links.json."""
        keys = self.list_keys(list_name)
        for key in keys:
            for w in self.scene.get("windows") or []:
                rows = (w.get("listRows") or {}).get(key)
                if rows:
                    return [rows] if isinstance(rows, str) else list(rows)
        out = []
        for pair in self.links.get("entryPairs", []):
            # a pair that names its window fills that window's grid only (two windows have a templates_grid)
            if pair.get("grid") in keys and pair.get("window") in (None, window_name):
                out.append(pair["entry"])
        for pair in self.links.get("listRows", []):
            if pair.get("list") in keys:
                out.append(pair["row"])
        # the first row window listed is the usual one; the others are shown once each after it
        return out

    def row_count(self, window_name, list_name, default):
        keys = self.list_keys(list_name)
        for table in (self.options.get("rows") or {}, self.state.get("rows") or {}):
            for key in keys:
                if table.get(key) is not None:
                    return int(table[key])
        for key in keys:
            for w in self.scene.get("windows") or []:
                rows = (w.get("rows") or {}).get(key)
                if rows is not None:
                    return int(rows)
        return default

    def draw_scrollbar(self, node, parent, canvas, clip):
        name = node.name or ""
        size = self.size_of(node, parent, default=(18.0, parent.h))
        x, y = self.anchor(node, parent, size)
        rect = Rect(x, y, size[0], parent.h)
        self.record("other", name, rect, node.key)
        self.draw_scrollbar_parts(node, rect, canvas, clip)

    def draw_named_scrollbar(self, name, list_rect, canvas, clip):
        node, _path, _lines = self.windows.find(name)
        if node is None:
            return
        size = self.size_of(node, list_rect, default=(18.0, list_rect.h))
        x, y = self.anchor(node, list_rect, (size[0], list_rect.h))
        rect = Rect(x, y, size[0], list_rect.h)
        self.draw_scrollbar_parts(node, rect, canvas, clip)

    def draw_scrollbar_parts(self, node, rect, canvas, clip):
        background = node.block("background")
        if background is not None:
            sprite = self.sprite(self.value(background.get("quadTextureSprite")) or self.value(background.get("spriteType")))
            if sprite is not None:
                self.draw_sprite(canvas, sprite, Rect(rect.x, rect.y, rect.w, rect.h), clip=clip)
        for part, anchor_bottom in (("track", False), ("decreaseButton", False), ("increaseButton", True), ("slider", False)):
            block = node.block(part)
            if block is None:
                continue
            sprite = self.sprite(self.value(block.get("quadTextureSprite")) or self.value(block.get("spriteType")))
            if sprite is None:
                continue
            px = self.num(block, "position", "x", rect.w)
            py = self.num(block, "position", "y", rect.h)
            if part == "track":
                self.draw_sprite(canvas, sprite, Rect(rect.x + px, rect.y + py, rect.w - 2 * px, rect.h - 2 * py), clip=clip)
            elif anchor_bottom:
                size = self.sprite_size(sprite)
                self.draw_sprite(canvas, sprite, Rect(rect.right + px, rect.bottom + py, None, None), clip=clip)
            else:
                self.draw_sprite(canvas, sprite, Rect(rect.x + px, rect.y + py, None, None), clip=clip)

    def outline(self, canvas, rect, color, clip, width=1):
        draw = ImageDraw.Draw(canvas)
        box = rect.box()
        if box[2] <= box[0] or box[3] <= box[1]:
            box = (box[0], box[1], box[0] + 1, box[1] + 1)
        draw.rectangle(box, outline=color, width=width)

    def draw_bounds(self, canvas):
        draw = ImageDraw.Draw(canvas)
        for kind, name, rect, node_type in self.bounds:
            if kind == "position":
                x, y = int(rect.x), int(rect.y)
                draw.line([(x - 4, y), (x + 4, y)], fill=(255, 255, 255, 255))
                draw.line([(x, y - 4), (x, y + 4)], fill=(255, 255, 255, 255))
                draw.text((x + 5, y - 4), name, fill=(255, 255, 255, 255))
                continue
            color = BOUNDS_COLORS.get(kind, BOUNDS_COLORS["other"])
            box = rect.box()
            if box[2] <= box[0]:
                box = (box[0], box[1], box[0] + 1, box[3])
            if box[3] <= box[1]:
                box = (box[0], box[1], box[2], box[1] + 1)
            draw.rectangle(box, outline=color, width=1)
            if name:
                draw.text((box[0] + 2, box[1] + 1), name, fill=color)


def load_links(mod_dir=REPO_ROOT):
    path = os.path.join(mod_dir, "tools", "gui-links.json")
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def load_scene(name, mod_dir=REPO_ROOT):
    path = name if os.path.isfile(name) else os.path.join(mod_dir, "tools", "scenes", name + ".json")
    with open(path, encoding="utf-8") as handle:
        scene = json.load(handle)
    scene["_path"] = path
    return scene


def save_scaled(img, path, scale):
    if scale != 1:
        img = img.resize((img.width * scale, img.height * scale), Image.NEAREST)
    img.save(path)
    return path


def render_single(renderer, name, args):
    """One window on a canvas that also shows what sticks out of it."""
    probe = Image.new("RGBA", SCREEN, (0, 0, 0, 0))
    renderer.text_checks = []
    rect = renderer.render_window(name, probe, (400, 400), prefer_file=args.file)
    if rect is None:
        return None
    # bounding box of everything drawn or recorded, relative to the window
    xs = [rect.x, rect.right]
    ys = [rect.y, rect.bottom]
    for _kind, _n, r, _t in renderer.bounds:
        if r.w > 4000 or r.h > 4000:
            continue
        xs += [r.x, r.right]
        ys += [r.y, r.bottom]
    x1, y1 = int(min(xs)) - 4, int(min(ys)) - 4
    x2, y2 = int(max(xs)) + 4, int(max(ys)) + 4
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(SCREEN[0], max(x2, x1 + 1)), min(SCREEN[1], max(y2, y1 + 1))
    canvas = Image.new("RGBA", (x2 - x1, y2 - y1), tuple(args.background))
    renderer.bounds = []
    renderer.report = []
    renderer.text_checks = []
    rect = renderer.render_window(name, canvas, (400 - x1, 400 - y1), prefer_file=args.file)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle(rect.box(), outline=(255, 255, 255, 90), width=1)
    if args.bounds:
        renderer.draw_bounds(canvas)
    os.makedirs(PREVIEW_DIR, exist_ok=True)
    out = args.out or os.path.join(PREVIEW_DIR, name + ("_bounds" if args.bounds else "") + ".png")
    canvas.save(out)
    out2 = save_scaled(canvas, out.replace(".png", "@2x.png"), 2) if args.scale == 2 else None
    offset = (400 - x1, 400 - y1)
    return rect, out, out2, offset


def layout_scene(renderer, scene, canvas):
    """Draw every window of a scene at its screen position. Returns [(name, Rect or None)]."""
    renderer.text_checks = []
    renderer.located = []
    prefer = None
    if scene.get("file") and not renderer.vanilla_only:
        prefer = os.path.join(REPO_ROOT, "interface", scene["file"])
    rects = []
    for w in scene.get("windows", []):
        if w.get("skip"):   # a row window, listed for its "hide" list only: another window draws it
            continue
        # d7-top-bar: a window script shows in some states only ("" is the scene's own state)
        if w.get("drawIn") is not None and (renderer.options.get("state") or "") not in w["drawIn"]:
            continue
        at = w.get("at")
        if renderer.vanilla_only and w.get("atVanilla") is not None:
            # a window the code places next to others sits elsewhere without the mod's sizes
            at = w["atVanilla"]
        if at is None:   # no measured position: where the file itself puts the window
            at = renderer.default_origin(w["name"], prefer)
        rect = renderer.render_window(w["name"], canvas, (at[0], at[1]), prefer_file=prefer)
        rects.append((w["name"], rect))
    return rects


def locate_specs(renderer, scene, specs):
    """Print one line per spec: LOCATE <spec> <x> <y> <w> <h> (centre and size on the screen) or LOCATE <spec> NOTFOUND."""
    layout_scene(renderer, scene, Image.new("RGBA", SCREEN, (0, 0, 0, 0)))
    ok = True
    for spec in specs:
        rect = renderer.locate(spec)
        if rect is None or rect.w <= 0 or rect.h <= 0:
            print("LOCATE\t%s\tNOTFOUND" % spec)
            ok = False
        else:
            print("LOCATE\t%s\t%d\t%d\t%d\t%d" % (spec, round(rect.x + rect.w / 2.0), round(rect.y + rect.h / 2.0), rect.w, rect.h))
    return ok


def verify_capture(renderer, scene, capture_path, specs, search=20, threshold=30.0):
    """Look for each widget in a game capture near where the layout puts it.

    The widget as the renderer draws it is compared with the capture at every offset up to `search` pixels;
    the best mean colour difference (0-255) wins. Prints VERIFY <spec> FOUND|MISSING <dx> <dy> <score>: the
    offset is how far the game draws the widget from the layout, which is also the renderer's error there.
    """
    from PIL import ImageChops, ImageStat

    canvas = Image.new("RGBA", SCREEN, (0, 0, 0, 0))
    layout_scene(renderer, scene, canvas)
    capture = Image.open(capture_path).convert("RGB")
    all_found = True
    for spec in specs:
        rect = renderer.locate(spec)
        if rect is None or rect.w < 4 or rect.h < 4:
            print("VERIFY\t%s\tMISSING\t0\t0\t-1\tnot in the layout" % spec)
            all_found = False
            continue
        box = (max(0, int(rect.x)), max(0, int(rect.y)), min(SCREEN[0], int(rect.x + rect.w)), min(SCREEN[1], int(rect.y + rect.h)))
        template = canvas.crop(box)
        mask = template.split()[3].point(lambda a: 255 if a > 200 else 0)
        if not mask.getbbox():
            print("VERIFY\t%s\tMISSING\t0\t0\t-1\tthe renderer draws nothing there" % spec)
            all_found = False
            continue
        template_rgb = template.convert("RGB")
        best = None
        for dy in range(-search, search + 1):
            for dx in range(-search, search + 1):
                shifted = (box[0] + dx, box[1] + dy, box[2] + dx, box[3] + dy)
                if shifted[0] < 0 or shifted[1] < 0 or shifted[2] > capture.width or shifted[3] > capture.height:
                    continue
                diff = ImageChops.difference(capture.crop(shifted), template_rgb)
                score = sum(ImageStat.Stat(diff, mask).mean) / 3.0
                if best is None or score < best[0]:
                    best = (score, dx, dy)
        found = best is not None and best[0] <= threshold
        all_found = all_found and found
        print("VERIFY\t%s\t%s\t%d\t%d\t%.1f" % (spec, "FOUND" if found else "MISSING", best[1] if best else 0, best[2] if best else 0, best[0] if best else -1))
    return all_found


def render_scene(renderer, scene, args):
    canvas = Image.new("RGBA", SCREEN, (0, 0, 0, 0))
    over = None
    if args.over:
        shot = args.over if isinstance(args.over, str) and os.path.isfile(args.over) else os.path.join(REPO_ROOT, scene.get("screenshot", ""))
        if os.path.isfile(shot):
            over = Image.open(shot).convert("RGBA").resize(SCREEN)
        else:
            renderer.warn("screenshot %s not found; rendering on a plain background" % shot)
    base = over if over is not None else Image.new("RGBA", SCREEN, tuple(args.background))
    rects = layout_scene(renderer, scene, canvas)
    if args.bounds:
        renderer.draw_bounds(canvas)
    base.alpha_composite(canvas)
    os.makedirs(PREVIEW_DIR, exist_ok=True)
    state = ("_" + args.state) if getattr(args, "state", None) else ""
    out = args.out or os.path.join(PREVIEW_DIR, scene["screen"] + state + "_scene" + ("_bounds" if args.bounds else "") + ".png")
    base.save(out)
    crop_out = None
    crop = scene.get("crop")
    if crop:
        x, y, w, h = crop
        crop_img = base.crop((x, y, x + w, y + h))
        crop_out = out.replace("_scene", "_crop")
        save_scaled(crop_img, crop_out, 2)
    return rects, out, crop_out


def print_report(renderer, offset=None):
    if renderer.text_checks:
        print("Texts (sample or caption against maxWidth):")
        for window, widget, text, font, width, max_w, verdict in renderer.text_checks:
            print("  %-8s %s/%s  %r  %d px in %s, maxWidth %d" % (verdict, window, widget, text, width, font, max_w))
    if renderer.notes:
        print("Notes:")
        for n in sorted(renderer.notes):
            print("  " + n)
    if renderer.warnings:
        print("Warnings:")
        for w in renderer.warnings:
            print("  " + w)
    print("Not modelled: widgets the engine positions or sizes in code are drawn where the file puts them; list and grid")
    print("contents are sample rows from gui-links.json; text wraps on maxWidth only. See wiki/Engine-Facts.md.")


def run_batch(path):
    """Run the calls listed in a JSON file ([{"id": ..., "args": [...]}, ...]) in this one process.

    The textures, fonts, sprite index and window index load once for all of them. Each call prints what it
    prints on its own, between "=== JOB <id> ===" and "=== END <id> exit <code> ===".
    """
    import contextlib
    import traceback

    with open(path, encoding="utf-8") as handle:
        jobs = json.load(handle)
    out = sys.stdout
    for job in jobs:
        job_id = str(job.get("id", ""))
        print("=== JOB %s ===" % job_id, file=out, flush=True)
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            try:
                code = main([str(a) for a in job.get("args", [])])
            except SystemExit as exc:
                code = exc.code if isinstance(exc.code, int) else 1
            except Exception:
                traceback.print_exc(file=out)
                code = 1
        out.flush()
        print("=== END %s exit %s ===" % (job_id, code), file=out, flush=True)
    return 0


def main(argv):
    # a sample text may hold a character the console code page lacks (the infinity sign of a series)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("window", nargs="?", help="top-level window to draw")
    ap.add_argument("--batch", metavar="JOBS.json", help="run every call listed in the file in this one process, and nothing else")
    ap.add_argument("--scene", help="scene name from tools/scenes/ (or a path)")
    ap.add_argument("--file", help="mod .gui file to take the window from (default: whichever mod file defines it, else vanilla)")
    ap.add_argument("--over", nargs="?", const=True, default=False, help="compose the scene over its screenshot (or the given PNG)")
    ap.add_argument("--bounds", action="store_true", help="outline and label every named widget")
    ap.add_argument("--report", action="store_true", help="print the absolute rectangle of every named widget")
    ap.add_argument("--expand", action="append", default=[], help="name of a dropdown (or its expandedWindow) to draw opened")
    ap.add_argument("--frame", type=int, help="draw every multi-frame sprite with this frame (2 = selected rows)")
    ap.add_argument("--rows", action="append", default=[], metavar="LIST=N", help="number of sample rows for a list or grid")
    ap.add_argument("--scale", type=int, default=2, choices=(1, 2), help="also write a 2x copy (default) or not")
    ap.add_argument("--height", action="append", default=[], metavar="WINDOW=N", help="draw a window whose height is set in code at this height")
    ap.add_argument("--hide", action="append", default=[], metavar="WIDGET", help="skip a widget the game code hides in this state")
    ap.add_argument("--place", action="append", default=[], metavar="WIDGET=X,Y", help="draw a widget the game code moves at this position inside its parent")
    ap.add_argument("--clip-default", choices=("yes", "no"), default="no", help="what a container without a clipping line does")
    ap.add_argument("--background", default="46,52,60,255", help="canvas colour r,g,b,a")
    ap.add_argument("--out", help="output path")
    ap.add_argument("--game-dir", help="Hearts of Iron IV install folder")
    ap.add_argument("--vanilla", action="store_true", help="lay out with the vanilla files only, as the game does without the mod")
    ap.add_argument("--locate", nargs="+", metavar="WINDOW/WIDGET[#N]", help="with --scene: print where these widgets sit on the screen, and draw nothing")
    ap.add_argument("--verify", metavar="CAPTURE.png", help="with --scene: look for the scene's 'expect' widgets (or --expect) in a game capture")
    ap.add_argument("--expect", nargs="+", metavar="WINDOW/WIDGET[#N]", help="widgets for --verify instead of the scene's own list")
    ap.add_argument("--state", metavar="CAPTURE", help="with --scene: draw the state of one of the scene's captures (another tab, an opened dropdown)")
    args = ap.parse_args(argv)
    if args.batch:
        return run_batch(args.batch)
    args.background = [int(v) for v in args.background.split(",")]

    game_dir = gp.find_game_dir(args.game_dir)
    if not game_dir:
        print("Hearts of Iron IV install not found. Pass --game-dir or set HOI4_GAME_DIR.", file=sys.stderr)
        return 2
    scene = load_scene(args.scene) if args.scene else {}
    rows = {}
    for item in args.rows:
        k, _sep, v = item.partition("=")
        rows[k] = int(v)
    heights = {}
    for item in args.height:
        k, _sep, v = item.partition("=")
        heights[k] = int(v)
    places = {}
    for item in args.place:
        k, _sep, v = item.partition("=")
        xs, _sep, ys = v.partition(",")
        places[k] = (float(xs), float(ys))
    options = {"expand": args.expand, "frame": args.frame, "rows": rows, "heights": heights, "hide": args.hide, "place": places, "clip_default": args.clip_default, "vanilla": args.vanilla, "state": args.state}
    renderer = Renderer(game_dir, scene=scene, options=options)

    if args.locate or args.verify:
        if not args.scene:
            print("--locate and --verify need --scene: the scene says where each window sits on the screen", file=sys.stderr)
            return 2
        if args.locate:
            return 0 if locate_specs(renderer, scene, args.locate) else 1
        specs = args.expect or scene.get("expect") or []
        if not specs:
            print("VERIFY\t-\tSKIPPED\t0\t0\t-1\tthe scene has no 'expect' list")
            return 0
        return 0 if verify_capture(renderer, scene, args.verify, specs) else 1

    if args.scene and not args.window:
        rects, out, crop_out = render_scene(renderer, scene, args)
        for name, rect in rects:
            print("%-40s %s" % (name, rect if rect else "NOT FOUND"))
        print("wrote", out)
        if crop_out:
            print("wrote", crop_out, "(crop at 2x)")
    elif args.window:
        result = render_single(renderer, args.window, args)
        if result is None:
            print("window %s not found" % args.window, file=sys.stderr)
            print_report(renderer)
            return 1
        rect, out, out2, offset = result
        print("%s  size %dx%d  canvas origin at (%d,%d) of the image" % (args.window, rect.w, rect.h, offset[0], offset[1]))
        print("wrote", out)
        if out2:
            print("wrote", out2)
    else:
        ap.print_help()
        return 1

    if args.report:
        print("Widgets (absolute, image pixels):")
        for name, node_type, rect in renderer.report:
            print("  %-45s %-22s %s" % (name, node_type, rect))
    print_report(renderer)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
