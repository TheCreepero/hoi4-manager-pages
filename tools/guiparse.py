"""Clausewitz GUI parsing for the Python tools: the same tokenizer as tools/GuiParsing.ps1.

    python -I tools/guiparse.py --dump <file.gui>      widget paths, one per line (parity with Get-GuiWidgetPaths)
    python -I tools/guiparse.py --windows <file.gui>   top-level windows with their line ranges
    python -I tools/guiparse.py --game-dir             the Hearts of Iron IV install folder the tools use

Also the shared loaders for the renderer: the game folder, the sprite index of every .gfx file, the
bitmap fonts (BMFont .fnt files with a .dds/.tga page) and the English localisation.
"""

import bisect
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_images = {}
_memo = {}


def load_image(path, mod_dir=REPO_ROOT):
    """An image file as RGBA, decoded once per process and kept as a PNG under scratch/cache/textures.

    Pillow decodes the game's DDS files in pure Python, which was most of a render's time; a PNG of the
    decoded pixels reads back in a fraction of it, and is the same pixels.
    """
    import hashlib
    from PIL import Image

    if path in _images:
        return _images[path]
    stat = os.stat(path)
    key = hashlib.md5(("%s|%d|%d" % (os.path.normcase(os.path.abspath(path)), stat.st_mtime_ns, stat.st_size)).encode("utf-8")).hexdigest()
    cache_dir = os.path.join(mod_dir, "scratch", "cache", "textures")
    cached = os.path.join(cache_dir, key + ".png")
    img = None
    if os.path.isfile(cached):
        try:
            img = Image.open(cached).convert("RGBA")
        except Exception:
            img = None
    if img is None:
        img = Image.open(path).convert("RGBA")
        try:   # a read-only or missing scratch folder must not stop a render
            os.makedirs(cache_dir, exist_ok=True)
            img.save(cached + ".tmp", format="PNG")
            os.replace(cached + ".tmp", cached)
        except Exception:
            pass
    _images[path] = img
    return img


def memoized(loader):
    """One result per process for a loader called with the same arguments (the batch mode of render_gui.py)."""
    import functools

    @functools.wraps(loader)
    def wrapper(*args, **kwargs):
        key = (loader.__name__, args, tuple(sorted(kwargs.items())))
        if key not in _memo:
            _memo[key] = loader(*args, **kwargs)
        return _memo[key]
    return wrapper


TOKEN_RE = re.compile(r'#[^\r\n]*|"[^"]*"|[{}=]|[^\s{}=#"]+')


class Node:
    """A block (children is a list) or a key = value leaf (children is None)."""

    __slots__ = ("key", "value", "children", "line", "end_line")

    def __init__(self, key, value, children, line):
        self.key = key
        self.value = value
        self.children = children
        self.line = line
        self.end_line = line

    def is_block(self):
        return self.children is not None

    def get(self, key, default=None):
        """First leaf value with this key, case-insensitive (Get-GuiValue)."""
        if self.children is None:
            return default
        key = key.lower()
        for child in self.children:
            if child.children is None and child.key.lower() == key:
                return child.value
        return default

    def block(self, key):
        """First child block with this key, case-insensitive (Get-GuiBlock)."""
        if self.children is None:
            return None
        key = key.lower()
        for child in self.children:
            if child.children is not None and child.key.lower() == key:
                return child
        return None

    def blocks(self, key=None):
        if self.children is None:
            return []
        if key is None:
            return [c for c in self.children if c.children is not None]
        key = key.lower()
        return [c for c in self.children if c.children is not None and c.key.lower() == key]

    def leaves(self, key):
        """Every leaf value with this key, in order (a button can have several shortcut lines)."""
        if self.children is None:
            return []
        key = key.lower()
        return [c.value for c in self.children if c.children is None and c.key.lower() == key]

    @property
    def name(self):
        return self.get("name")

    def walk(self):
        """Every block at or below this node, parents before children (Get-GuiNodes)."""
        stack = [self]
        while stack:
            current = stack.pop()
            yield current
            for child in reversed(current.children or []):
                if child.children is not None:
                    stack.append(child)


def read_text(path):
    """Read a Clausewitz file: UTF-8 with or without BOM, falling back to Latin-1 (Read-GuiText)."""
    with open(path, "rb") as handle:
        data = handle.read()
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin-1")


def parse(text):
    """Parse Clausewitz script into a Node tree (ConvertFrom-GuiText)."""
    line_starts = [0]
    for m in re.finditer("\n", text):
        line_starts.append(m.end())

    root = Node("", None, [], 1)
    root.end_line = len(line_starts)
    stack = [root]
    pending_key = None
    pending_line = 0
    expect_value = False

    for m in TOKEN_RE.finditer(text):
        token = m.group(0)
        if token.startswith("#"):
            continue
        line = bisect.bisect_right(line_starts, m.start())
        current = stack[-1]
        if token == "{":
            key = ""
            key_line = line
            if expect_value:
                key = pending_key
                key_line = pending_line
            elif pending_key is not None:
                current.children.append(Node(pending_key, None, None, pending_line))
            node = Node(key, None, [], key_line)
            current.children.append(node)
            stack.append(node)
            pending_key = None
            expect_value = False
        elif token == "}":
            if pending_key is not None:
                current.children.append(Node(pending_key, None, None, pending_line))
            pending_key = None
            expect_value = False
            if len(stack) > 1:
                closed = stack.pop()
                closed.end_line = line
        elif token == "=":
            expect_value = True
        else:
            value = token
            if len(value) >= 2 and value.startswith('"'):
                value = value[1:-1]
            if expect_value:
                leaf = Node(pending_key, value, None, pending_line)
                leaf.end_line = line
                current.children.append(leaf)
                pending_key = None
                expect_value = False
            else:
                if pending_key is not None:
                    current.children.append(Node(pending_key, None, None, pending_line))
                pending_key = value
                pending_line = line
    return root


def parse_file(path):
    return parse(read_text(path))


def top_level_windows(root, section="guiTypes"):
    """Named blocks directly under guiTypes (Get-GuiTopLevelWindows)."""
    result = []
    for sec in root.children:
        if sec.children is None or sec.key.lower() != section.lower():
            continue
        for child in sec.children:
            if child.children is not None and child.name:
                result.append(child)
    return result


def widget_paths(node):
    """'parent/child|type' per named block, lower case (Get-GuiWidgetPaths), in the same order."""
    out = []
    stack = [(node, "")]
    while stack:
        current, prefix = stack.pop()
        name = current.name
        if name:
            prefix = prefix + "/" + name if prefix else name
            out.append(("%s|%s" % (prefix, current.key)).lower())
        for child in current.children or []:
            if child.children is not None:
                stack.append((child, prefix))
    return out


def number(value, default=None):
    """A numeric leaf value as float, or default. '100%' and '100%%' return the default."""
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def percent(value):
    """The percentage of a '100%'-style value as a fraction, or None."""
    if value is None:
        return None
    m = re.match(r"^(-?\d+(?:\.\d+)?)%+$", value.strip())
    return float(m.group(1)) / 100.0 if m else None


# ---------------------------------------------------------------- game folder


def find_game_dir(explicit=None):
    """The Hearts of Iron IV install folder: explicit, HOI4_GAME_DIR, then every Steam library."""
    candidates = [explicit, os.environ.get("HOI4_GAME_DIR")]
    steam_roots = [r"C:\Program Files (x86)\Steam"]
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
            steam_roots.insert(0, winreg.QueryValueEx(key, "SteamPath")[0].replace("/", "\\"))
    except (OSError, ImportError):
        pass
    for root in list(steam_roots):
        vdf = os.path.join(root, "steamapps", "libraryfolders.vdf")
        if os.path.isfile(vdf):
            with open(vdf, encoding="utf-8", errors="replace") as handle:
                steam_roots += [m.replace("\\\\", "\\") for m in re.findall(r'"path"\s+"([^"]+)"', handle.read())]
    candidates += [os.path.join(root, "steamapps", "common", "Hearts of Iron IV") for root in steam_roots]
    for candidate in candidates:
        if candidate and os.path.isdir(os.path.join(candidate, "interface")):
            return candidate
    return None


def user_dir():
    """Documents/Paradox Interactive/Hearts of Iron IV."""
    return os.path.join(os.path.expanduser("~"), "Documents", "Paradox Interactive", "Hearts of Iron IV")


# ---------------------------------------------------------------- sprites


class Sprite:
    __slots__ = ("name", "kind", "texture", "textures", "frames", "size", "border", "tiling_center", "file", "line")

    def __init__(self, node, source_file):
        self.name = node.name
        self.kind = node.key
        textures = []
        for child in node.children:
            if child.children is None and re.match(r"(?i)^texturefile\d?$", child.key) and child.value:
                textures.append(re.sub(r"[\\/]+", "/", child.value))
        self.textures = textures
        self.texture = textures[0] if textures else None
        self.frames = int(number(node.get("noOfFrames"), 1) or 1)
        size = node.block("size")
        self.size = (number(size.get("x")), number(size.get("y"))) if size else None
        border = node.block("borderSize")
        self.border = (number(border.get("x"), 0), number(border.get("y"), 0)) if border else None
        self.tiling_center = (node.get("tilingCenter") or "").lower() == "yes"
        self.file = source_file
        self.line = node.line


def sprite_declarations(root, source_file):
    out = []
    for sec in root.children:
        if sec.children is None:
            continue
        # vanilla core.gfx declares 15 sprites inside its "bitmapfonts" section (the 375 px panel header
        # among them) and the game loads them, so a sprite block counts in any section
        anywhere = sec.key.lower() != "spritetypes"
        for child in sec.children:
            if child.children is not None and child.name:
                if anywhere and not child.key.lower().endswith(("spritetype", "progressbartype")):
                    continue
                out.append(Sprite(child, source_file))
    return out


def gfx_files(folder):
    out = []
    for dirpath, _dirs, files in os.walk(folder):
        for f in files:
            if f.lower().endswith(".gfx"):
                out.append(os.path.join(dirpath, f))
    return sorted(out)


@memoized
def load_sprites(game_dir, mod_dir=REPO_ROOT, verbose=False):
    """name -> Sprite over every vanilla .gfx file, then the mod's (the mod wins), with a cache under scratch/."""
    import pickle

    sources = []
    if game_dir:
        sources += gfx_files(os.path.join(game_dir, "interface"))
    sources += gfx_files(os.path.join(mod_dir, "interface"))
    stamp = [(p, os.path.getmtime(p), os.path.getsize(p)) for p in sources]
    cache_dir = os.path.join(mod_dir, "scratch", "cache")
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, "sprites.pickle")
    try:
        with open(cache_path, "rb") as handle:
            cached = pickle.load(handle)
        if cached.get("stamp") == stamp:
            return cached["sprites"]
    except Exception:
        pass
    sprites = {}
    for path in sources:
        try:
            root = parse(read_text(path))
        except Exception as exc:  # a broken vanilla file must not stop the index
            if verbose:
                print("skip", path, exc, file=sys.stderr)
            continue
        for sprite in sprite_declarations(root, path):
            sprites[sprite.name] = sprite
    with open(cache_path, "wb") as handle:
        pickle.dump({"stamp": stamp, "sprites": sprites}, handle)
    return sprites


# ---------------------------------------------------------------- fonts


class BitmapFont:
    """A BMFont text file plus its page image. Measures and draws text with the real glyphs."""

    def __init__(self, fnt_path, color=(255, 255, 255, 255)):
        self.path = fnt_path
        self.color = color      # the colour its bitmapfont block declares; white leaves the glyphs as painted
        self.chars = {}
        self.kerning = {}
        self.line_height = 0
        self.base = 0
        self.pages = {}
        self.page_images = {}
        with open(fnt_path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                parts = line.split()
                if not parts:
                    continue
                kind = parts[0]
                attrs = dict(p.split("=", 1) for p in parts[1:] if "=" in p)
                if kind == "common":
                    self.line_height = int(attrs.get("lineHeight", 0))
                    self.base = int(attrs.get("base", 0))
                elif kind == "page":
                    self.pages[int(attrs["id"])] = attrs["file"].strip('"')
                elif kind == "char":
                    keys = ("x", "y", "width", "height", "xoffset", "yoffset", "xadvance", "page")
                    self.chars[int(attrs["id"])] = {k: int(attrs[k]) for k in keys if k in attrs}
                elif kind == "kerning":
                    self.kerning[(int(attrs["first"]), int(attrs["second"]))] = int(attrs["amount"])

    def width(self, text):
        """Pixel width of a line of text: the sum of xadvance values (Design Rules, 'A text's width')."""
        total = 0
        prev = None
        for ch in text:
            glyph = self.chars.get(ord(ch)) or self.chars.get(ord("?"))
            if glyph is None:
                continue
            total += glyph["xadvance"] + self.kerning.get((prev, ord(ch)), 0)
            prev = ord(ch)
        return total

    def page_image(self, page_id):
        if page_id not in self.page_images:
            file_name = self.pages.get(page_id)
            candidates = []
            if file_name:
                candidates.append(os.path.join(os.path.dirname(self.path), file_name))
            stem = os.path.splitext(self.path)[0]
            candidates += [stem + ext for ext in (".dds", ".tga", ".png")]
            for candidate in candidates:
                if os.path.isfile(candidate):
                    self.page_images[page_id] = load_image(candidate)
                    break
            else:
                raise FileNotFoundError("no page image for " + self.path)
        return self.page_images[page_id]

    def draw(self, canvas, x, y, text, color=None):
        """Draw one line with its top-left corner at (x, y), in the font's declared colour unless one is given.
        Returns the width drawn."""
        from PIL import Image

        if color is None:
            color = self.color
        cursor = x
        prev = None
        for ch in text:
            glyph = self.chars.get(ord(ch)) or self.chars.get(ord("?"))
            if glyph is None:
                continue
            cursor += self.kerning.get((prev, ord(ch)), 0)
            if glyph["width"] and glyph["height"]:
                page = self.page_image(glyph.get("page", 0))
                box = (glyph["x"], glyph["y"], glyph["x"] + glyph["width"], glyph["y"] + glyph["height"])
                tile = page.crop(box)
                if color != (255, 255, 255, 255):
                    # tinted as the game does it: the glyph's own shading and outline stay under the colour
                    from PIL import ImageChops
                    alpha = tile.split()[3]
                    tile = ImageChops.multiply(tile, Image.new("RGBA", tile.size, color))
                    tile.putalpha(alpha)
                canvas.alpha_composite(tile, (int(cursor + glyph["xoffset"]), int(y + glyph["yoffset"])))
            cursor += glyph["xadvance"]
            prev = ord(ch)
        return cursor - x


@memoized
def font_declarations(game_dir, mod_dir=REPO_ROOT):
    """name -> (first fontfile path without extension, colour) from the bitmapfonts blocks of every .gfx."""
    out = {}
    sources = []
    if game_dir:
        sources += gfx_files(os.path.join(game_dir, "interface"))
    sources += gfx_files(os.path.join(mod_dir, "interface"))
    for path in sources:
        text = read_text(path)
        if "bitmapfont" not in text:
            continue
        root = parse(text)
        for sec in root.children:
            if sec.children is None or sec.key.lower() != "bitmapfonts":
                continue
            for font in sec.children:
                if font.children is None or font.key.lower() != "bitmapfont" or not font.name:
                    continue
                files = []
                block = font.block("fontfiles")
                if block:
                    files = [c.key for c in block.children if c.children is None]
                if not files and font.get("path"):
                    files = [font.get("path")]
                if files:
                    out[font.name] = (files[0].replace("\\", "/"), font.get("color") or "0xffffffff")
    return out


_font_cache = {}


def load_font(name, game_dir, mod_dir=REPO_ROOT, declarations=None):
    """A BitmapFont by its .gfx name (hoi_18mbs ...) or by a direct gfx/fonts path."""
    if name in _font_cache:
        return _font_cache[name]
    if declarations is None:
        declarations = font_declarations(game_dir, mod_dir)
    rel, declared = declarations.get(name, (None, None))
    if rel is None:
        rel = "gfx/fonts/" + name
    color = (255, 255, 255, 255)
    try:   # 0xAARRGGBB: the typewriter fonts are white glyphs declared black, and print black on paper
        argb = int(str(declared), 16)
        color = ((argb >> 16) & 255, (argb >> 8) & 255, argb & 255, 255)
    except (TypeError, ValueError):
        pass
    for base in (mod_dir, game_dir):
        if not base:
            continue
        fnt = os.path.join(base, *rel.split("/")) + ".fnt"
        if os.path.isfile(fnt):
            font = BitmapFont(fnt, color)
            _font_cache[name] = font
            return font
    raise FileNotFoundError("font %s (%s.fnt) not found" % (name, rel))


# ---------------------------------------------------------------- localisation


@memoized
def load_localisation(game_dir, mod_dir=REPO_ROOT, language="english"):
    """KEY -> text from localisation/<language>/*.yml, vanilla first then the mod (the mod wins)."""
    out = {}
    folders = []
    if game_dir:
        folders.append(os.path.join(game_dir, "localisation", language))
    folders.append(os.path.join(mod_dir, "localisation", language))
    folders.append(os.path.join(mod_dir, "localisation", "replace", language))
    line_re = re.compile(r'^\s*([A-Za-z0-9_.\-]+):\d*\s*"(.*)"\s*(?:#.*)?$')
    for folder in folders:
        if not os.path.isdir(folder):
            continue
        for dirpath, _dirs, files in os.walk(folder):
            for f in sorted(files):
                if not f.lower().endswith(".yml"):
                    continue
                with open(os.path.join(dirpath, f), encoding="utf-8-sig", errors="replace") as handle:
                    for line in handle:
                        m = line_re.match(line)
                        if m:
                            out[m.group(1)] = m.group(2)
    return out


def plain_text(text):
    """Localised text without colour codes, with $variables$ shown as their name."""
    text = re.sub("\u00a7[A-Za-z0-9!]", "", text)
    text = re.sub(r"\$([A-Za-z0-9_|]+)\$", lambda m: m.group(1).split("|")[0].lower(), text)
    return text.replace("\\n", "\n")


# ---------------------------------------------------------------- CLI


def main(argv):
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dump", metavar="FILE", help="print the widget paths of every top-level window")
    ap.add_argument("--windows", metavar="FILE", help="print the top-level windows with line ranges")
    ap.add_argument("--game-dir", action="store_true", help="print the game folder the tools use")
    args = ap.parse_args(argv)
    if args.game_dir:
        print(find_game_dir() or "")
        return 0
    path = args.dump or args.windows
    if not path:
        ap.print_help()
        return 1
    root = parse_file(path)
    for window in top_level_windows(root):
        if args.windows:
            print("%s\t%s\t%d\t%d" % (window.name, window.key, window.line, window.end_line))
        else:
            for p in widget_paths(window):
                print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
