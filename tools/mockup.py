"""Helpers for design mock-ups: draw the game's sprites and fonts, the plates of the card style, and pieces of a
reference capture onto a canvas. A mock-up script imports this module and composes a proposal before any .gui
file exists (wiki/Design-Rules.md, "Recipe for a screen phase", step 2).

The short way is a layout file (wiki/Workflow.md, "Handoff files"): the same file whose numbers the builder writes
into the generator, so the mock-up and the build share every number.

    python -I tools/mockup.py scratch/phases/A10/layout.json --out scratch/phases/A10/proposed-main.png [--crop 690,280,2240,1040]

or from a script that adds what the code draws (chart lines, pictures) on top:

    import sys; sys.path.insert(0, "tools")
    from mockup import Mockup
    m = Mockup.from_layout("scratch/phases/A10/layout.json")   # the capture, the windows and every item drawn
    m.text("hoi_18mbs", 1200, 400, "17.0")                      # more, in screen pixels
    m.save("scratch/phases/A10/proposed-main.png", crop=(690, 280, 2240, 1040))

The primitives are there for a hand-written mock-up too:

    m = Mockup("reference/vanilla/production.jpg", panel="reference/vanilla/production-panel.png")
    m.sprite("GFX_tiled_plain_bg", 0, 80, 1044, 1360)        # any sprite, at its size or a given one
    m.card(6, 56, 568, 68); m.head_bar(14, 138, 552, 30); m.bands(14, 168, 552, 32, 6); m.title_strip(3, 3, 574, 44)
    m.steel(6, 56, 568, 120, head=27); m.steel(2, 2, 816, 46, title=True)   # the steel look
    m.text("hoi_36header", 45, 86, "Production")              # a game font; colour codes and text icons work
    m.text("hoi_18mbs", 194, 175, "Fighters", w=192, align="center")
    m.paste(m.cut((16, 76, 512, 112)), 12, 140)               # a piece of the panel capture, at 1:1
    m.save("scratch/mockups/production.png", crop=(0, 60, 1100, 1440))

Pieces cut from a capture keep what the code draws there (pictures, portraits, values); sprites and
fonts come from the game files through the renderer, so a mock-up looks like the game at 1:1.
"""
import argparse
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guiparse  # noqa: E402
import layout as layoutmod  # noqa: E402
from render_gui import Rect, Renderer  # noqa: E402
from stretch_background import STEEL_BAR, steel_piece, tile_nine  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Mockup:
    def __init__(self, frame, panel=None, game_dir=None, size=None):
        """`frame`: the image to draw on, usually a reference capture of the whole screen (None with `size` for an
        empty canvas). `panel`: an optional second image to cut pieces from (a lossless panel capture)."""
        self.renderer = Renderer(guiparse.find_game_dir(game_dir), options={"vanilla": False})
        if frame:
            self.canvas = Image.open(os.path.join(REPO_ROOT, frame)).convert("RGBA")
        else:
            self.canvas = Image.new("RGBA", size or (2560, 1440), (12, 14, 16, 255))
        self.source = Image.open(os.path.join(REPO_ROOT, panel)).convert("RGBA") if panel else self.canvas.copy()
        self._textures = {}

    # ------------------------------------------------------------------ the game's sprites and fonts
    def sprite(self, name, x, y, width=None, height=None, frame=1, fill=0.7):
        """Draw a sprite at (x, y); a tiled sprite takes the given size, a progress bar fills `fill`."""
        return self.renderer.draw_sprite(self.canvas, self.renderer.sprite(name), Rect(x, y, width, height), frame=frame, fill=fill)

    def texture(self, name):
        """The sprite's texture as an image (a portrait, a hull picture), to resize or paste."""
        return self.renderer.texture(self.renderer.sprite(name))

    def texture_file(self, rel):
        """A texture of the game by its path under the game folder (gfx/interface/tiles/black_bg_tile.dds)."""
        if rel not in self._textures:
            path = os.path.join(self.renderer.game_dir, rel.replace("/", os.sep))
            if not os.path.isfile(path):
                path = os.path.join(REPO_ROOT, rel.replace("/", os.sep))
            self._textures[rel] = Image.open(path).convert("RGBA")
        return self._textures[rel]

    def text(self, font, x, y, text, w=None, align="left"):
        """A line of text in a game font; with `w` and `align` ("center", "right") it is placed inside a box."""
        if w is not None and align not in ("left", None):
            tw = self.text_width(font, text)
            x += (w - tw) // 2 if align in ("center", "centre") else w - tw
        self.renderer.draw_text_line(self.canvas, self.renderer.font(font), x, y, text, None)

    def text_width(self, font, text):
        return self.renderer.text_width(self.renderer.font(font), text)

    def line_height(self, font):
        return self.renderer.font(font).line_height

    # ------------------------------------------------------------------ the plates of the card style
    def tile(self, texture, border, w, h):
        """A texture laid out at w x h the way a corneredTileSpriteType with tilingCenter = yes lays it out."""
        return tile_nine(self.texture_file(texture), border, w, h)

    def plate(self, kind, x, y, w, h):
        texture, border = layoutmod.PLATES[kind]
        self.paste(self.tile(texture, border, w, h), x, y)

    def steel(self, x, y, w, h, head=0, title=False):
        """A piece of the steel look: a card with `head` rows of head band, or the title strip."""
        item = {"kind": "steel_title" if title else "steel", "w": w, "h": h, "head": head}
        self.paste(self.steel_image(item), x, y)

    def steel_image(self, item):
        head, gain, bottom = layoutmod.steel_params(item)
        return steel_piece(self.texture_file(STEEL_BAR), item["kind"], item["w"], item["h"], head, gain, bottom)

    def title_strip(self, x, y, w, h):
        self.plate("title", x, y, w, h)

    def card(self, x, y, w, h):
        self.plate("card", x, y, w, h)

    def head_bar(self, x, y, w, h=30):
        self.plate("head", x, y, w, h)

    def bands(self, x, y, w, row, rows, every=2, first=None):
        """The bands of a table: a dark plate on every `every`-th row (the even rows by default)."""
        first = every if first is None else first
        for n in range(first, rows + 1, every):
            self.plate("bands", x, y + row * (n - 1), w, row)

    def fixed_box(self, font, x, y, w, h, text, align="left"):
        """A text in a fixed box: cut where the box ends, as the game cuts a fixedsize text (W28)."""
        cut = self.renderer.truncate(self.renderer.font(font), text, w)
        self.text(font, x, y, cut, w, align)

    # ------------------------------------------------------------------ pieces
    def cut(self, box):
        """A piece (left, top, right, bottom) of the source capture."""
        return self.source.crop(box)

    def paste(self, image, x, y):
        self.canvas.alpha_composite(image.convert("RGBA"), (int(x), int(y)))

    def save(self, path, crop=None, scale=1):
        path = os.path.join(REPO_ROOT, path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        image = self.canvas.crop(crop) if crop else self.canvas
        if scale != 1:
            image = image.resize((image.width * scale, image.height * scale), Image.LANCZOS)
        image.convert("RGB").save(path, optimize=True)
        return path

    # ------------------------------------------------------------------ a layout file
    @classmethod
    def from_layout(cls, path, game_dir=None, windows=None):
        """A mock-up with the layout's capture as the canvas and every window drawn."""
        lay = layoutmod.load(os.path.join(REPO_ROOT, path) if not os.path.isabs(path) else path)
        m = cls(lay.get("frame"), panel=lay.get("panel"), game_dir=game_dir, size=tuple(lay.get("size", (2560, 1440))))
        m.layout = lay
        m.draw_layout(lay, windows)
        return m

    def draw_layout(self, lay, windows=None):
        """Draw the windows of a layout (all, or the paths named) with their items, in order."""
        for window in lay["windows"]:
            if windows and window["path"] not in windows:
                continue
            self.draw_window(lay, window)
        return self

    def draw_window(self, lay, window):
        ox, oy = layoutmod.window_screen_origin(window)
        if window.get("background") and window.get("size"):
            self.sprite(window["background"], ox, oy, window["size"][0], window["size"][1])
        for item in layoutmod.items(window):
            self.draw_item(lay, item, ox, oy)

    def draw_item(self, lay, item, ox, oy):
        kind = item["kind"]
        x, y = ox + item.get("x", 0), oy + item.get("y", 0)
        if kind in ("title", "card", "head", "inset"):
            self.plate(kind, x, y, item["w"], item["h"])
        elif kind in layoutmod.STEEL_KINDS:
            self.paste(self.steel_image(item), x, y)
        elif kind == "bands":
            for _n, by in layoutmod.band_rows(item):
                self.plate("bands", x, oy + by, item["w"], item["row"])
        elif kind == "plate":
            tex = layoutmod.plate_texture(item)
            if tex is None:
                self.sprite(item["sprite"], x, y, item.get("w"), item.get("h"), frame=item.get("frame", 1))
            else:
                self.paste(self.tile(tex[0], tex[1], item["w"], item["h"]), x, y)
        elif kind == "caption":
            if item.get("text"):
                self.text(item.get("font", "hoi_18mbs"), x, y, item["text"], item.get("w"), item.get("format", "left"))
        elif kind == "text":
            self.text(item["font"], x, y, item.get("text", ""), item.get("w"), item.get("align", item.get("format", "left")))
        elif kind == "sprite":
            self.sprite(item["name"], x, y, item.get("w"), item.get("h"), frame=item.get("frame", 1), fill=item.get("fill", 0.7))
        elif kind == "paste":
            self.paste(self.cut(tuple(item["box"])), x, y)
        elif kind == "move":
            # what the vanilla widget would show at its new place, when the item says so
            if item.get("sprite") and item.get("draw", True) and "sample" not in item:
                self.sprite(item["sprite"], x, y, item.get("w"), item.get("h"), frame=item.get("frame", 1), fill=item.get("fill", 0.7))
            if item.get("sample"):
                font = item.get("font", "hoi_18mbs")
                if item.get("fixed") and item.get("w"):
                    self.fixed_box(font, x, y, item["w"], item.get("h", 24), item["sample"], item.get("format", "left"))
                else:
                    self.text(font, x, y, item["sample"], item.get("w"), item.get("format", "left"))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Draw a layout file as a mock-up.")
    parser.add_argument("layout", help="scratch/phases/<id>/layout.json")
    parser.add_argument("--out", required=True, help="the PNG to write (under the repository)")
    parser.add_argument("--crop", help="left,top,right,bottom in screen pixels")
    parser.add_argument("--scale", type=int, default=1)
    parser.add_argument("--window", action="append", help="draw only this window path (repeatable)")
    parser.add_argument("--game-dir")
    args = parser.parse_args(argv)
    m = Mockup.from_layout(args.layout, game_dir=args.game_dir, windows=args.window)
    crop = tuple(int(v) for v in args.crop.split(",")) if args.crop else None
    print(m.save(args.out, crop=crop, scale=args.scale))


if __name__ == "__main__":
    main()
