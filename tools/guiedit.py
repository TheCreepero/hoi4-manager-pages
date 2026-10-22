"""Set values of widgets in a .gui file by widget path, leaving every other byte of the file alone.

A layout change touches dozens of positions, sizes and fonts. Editing them through this module names
each widget by its path, so a wrong assumption stops the script instead of changing the wrong widget,
and the file keeps its comments, order and line endings.

    import guiedit
    gui = guiedit.GuiFile("interface/zz_1440p_unit_details.gui")
    w = gui.window("army_division_stats_view")
    w.at("btn_close").set("position", x=1336, y=2)          # numbers inside a { } value
    w.at("info/base_stats/stats_grid").set("slotsize", width=233, height=28)
    w.at("experience").put("font", '"hoi_20b"')              # a plain value; added when missing
    w.at("").set("size", width=1370, height=612)             # "" is the window itself
    gui.save()

A path lists widget names from the window down, separated by "/". Add "#n" to a name for the n-th
widget of that name among the children searched (0 is the first). A step matches a direct child
first and then looks deeper, so "stats_grid" finds the only widget of that name, while
"combat_stats/stats_grid" picks one of several.

Keys are matched without regard to case, as the game does. After editing, review the result with
tools/Compare-Baseline.ps1.
"""

import bisect
import io
import re


class GuiEditError(Exception):
    pass


def _strip_comments(text):
    """The text with every comment blanked out, same length, so offsets stay valid."""
    out = []
    for line in text.split("\n"):
        in_string = False
        cut = None
        for i, ch in enumerate(line):
            if ch == '"':
                in_string = not in_string
            elif ch == "#" and not in_string:
                cut = i
                break
        out.append(line if cut is None else line[:cut] + " " * (len(line) - cut))
    return "\n".join(out)


class GuiFile:
    def __init__(self, path):
        self.path = path
        self.text = io.open(path, encoding="utf-8", newline="").read()

    def save(self):
        io.open(self.path, "w", encoding="utf-8", newline="").write(self.text)

    # ------------------------------------------------------------------ structure

    def _code(self):
        # the comment-free text, kept while the text does not change (a layout touches hundreds of widgets)
        cached = getattr(self, "_code_cache", None)
        if cached is None or cached[0] is not self.text:
            cached = (self.text, _strip_comments(self.text))
            self._code_cache = cached
        return cached[1]

    def _braces(self):
        """Every "{" of the comment-free text with its matching "}" (offset after it), indexed once per text version."""
        cached = getattr(self, "_brace_cache", None)
        if cached is None or cached[0] is not self.text:
            code = self._code()
            match = {}
            stack = []
            for m in re.finditer(r"[{}]", code):
                if m.group() == "{":
                    stack.append(m.start())
                elif stack:
                    match[stack.pop()] = m.start() + 1
            if stack:
                raise GuiEditError("unbalanced braces in " + self.path)
            cached = (self.text, sorted(match), match)
            self._brace_cache = cached
        return cached[1], cached[2]

    def _children(self, start, end):
        """(name, key, open, close) of each block directly inside the block text[start:end]
        (start is the offset of its "{", end the offset after its "}")."""
        code = self._code()
        opens, match = self._braces()
        found = []
        i = bisect.bisect_right(opens, start)
        while i < len(opens) and opens[i] < end - 1:
            open_at = opens[i]
            close = match[open_at]
            head = re.search(r"([A-Za-z_][\w]*)\s*=\s*$", code[max(start, open_at - 80):open_at])
            key = head.group(1) if head else ""
            name = self._own_value(code, open_at, close, "name")
            found.append((name, key, open_at, close))
            i = bisect.bisect_left(opens, close)
        return found

    def _match(self, code, open_at):
        try:
            return self._braces()[1][open_at]
        except KeyError:
            raise GuiEditError("no block opens at offset %d" % open_at)

    def _own_spans(self, code, start, end):
        """Pieces of text[start:end] that belong to the block itself, not to a child block."""
        opens, match = self._braces()
        spans = []
        at = start + 1
        i = bisect.bisect_right(opens, start)
        while i < len(opens) and opens[i] < end - 1:
            spans.append((at, opens[i]))
            at = match[opens[i]]
            i = bisect.bisect_left(opens, at)
        spans.append((at, end - 1))
        return spans

    def _own_value(self, code, start, end, key):
        for a, b in self._own_spans(code, start, end):
            m = re.search(r"(?i)(?<![\w])" + re.escape(key) + r"\s*=\s*\"?([^\s\"{}]+)\"?", code[a:b])
            if m:
                return m.group(1)
        return None

    def _find(self, start, end, name, nth):
        """The nth block named `name` under text[start:end]: direct children first, then deeper."""
        level = self._children(start, end)
        while level:
            hits = [c for c in level if c[0] == name]
            if len(hits) > nth:
                return hits[nth][2], hits[nth][3]
            nth -= len(hits)
            deeper = []
            for _name, _key, a, b in level:
                deeper += self._children(a, b)
            level = deeper
        return None

    def window(self, name):
        code = self._code()
        root = re.search(r"guiTypes\s*=\s*\{", code)
        if not root:
            raise GuiEditError("no guiTypes block in " + self.path)
        open_at = root.end() - 1
        for child, _key, a, _b in self._children(open_at, self._match(code, open_at)):
            if child == name:
                return Widget(self, name, [])
        raise GuiEditError("window %r is not in %s" % (name, self.path))

    def _span(self, window, steps):
        code = self._code()
        root = re.search(r"guiTypes\s*=\s*\{", code)
        open_at = root.end() - 1
        span = None
        for child, _key, a, b in self._children(open_at, self._match(code, open_at)):
            if child == window:
                span = (a, b)
                break
        if span is None:
            raise GuiEditError("window %r is not in %s" % (window, self.path))
        for step in steps:
            name, _, index = step.partition("#")
            found = self._find(span[0], span[1], name, int(index or 0))
            if found is None:
                raise GuiEditError("no widget %r under %s/%s" % (step, window, "/".join(steps[:steps.index(step)])))
            span = found
        return span


class Widget:
    def __init__(self, gui, window, steps):
        self.gui = gui
        self.window = window
        self.steps = steps

    def at(self, path):
        steps = [s for s in path.split("/") if s]
        return Widget(self.gui, self.window, self.steps + steps)

    def _label(self):
        return "/".join([self.window] + self.steps)

    def kind(self):
        """The widget's element type as the file writes it (instantTextboxType, iconType, containerWindowType)."""
        start, _end = self.gui._span(self.window, self.steps)
        code = self.gui._code()
        head = re.search(r"([A-Za-z_][\w]*)\s*=\s*$", code[max(0, start - 80):start])
        return head.group(1) if head else ""

    def has(self, key):
        """Whether the widget's own lines carry `key` (a plain or a { } value)."""
        start, end, spans = self._own()
        code = self.gui._code()
        for a, b in spans:
            if re.search(r"(?i)(?<![\w])" + re.escape(key) + r"\s*=", code[a:b]):
                return True
        return False

    def _own(self):
        start, end = self.gui._span(self.window, self.steps)
        return start, end, self.gui._own_spans(self.gui._code(), start, end)

    def get(self, key, component=None):
        """A plain value, or one number of a { } value; None when the key is missing."""
        start, end, spans = self._own()
        code = self.gui._code()
        if component is None:
            return self.gui._own_value(code, start, end, key)
        for a, b in spans:
            m = re.search(r"(?i)(?<![\w])" + re.escape(key) + r"\s*=\s*$", code[a:b])
            if m:
                close = self.gui._match(code, b)
                c = re.search(r"(?i)(?<![\w])" + re.escape(component) + r"\s*=\s*(-?[\d.]+%*)", code[b:close])
                return c.group(1) if c else None
        return None

    def set(self, key, **components):
        """Change numbers inside a block value such as position = { x=1 y=2 } or size = { width=3 height=4 }.
        Every component named must exist already."""
        start, end, spans = self._own()
        code = self.gui._code()
        for a, b in spans:
            m = re.search(r"(?i)(?<![\w])" + re.escape(key) + r"\s*=\s*$", code[a:b])
            if not m:
                continue
            close = self.gui._match(code, b)
            body = self.gui.text[b:close]
            for component, value in components.items():
                pattern = r"(?i)((?<![\w])" + re.escape(component) + r"\s*=\s*)(-?[\d.]+%*)"
                if not re.search(pattern, body):
                    raise GuiEditError("%s: %s has no %s" % (self._label(), key, component))
                body = re.sub(pattern, lambda mm: mm.group(1) + str(value), body, count=1)
            self.gui.text = self.gui.text[:b] + body + self.gui.text[close:]
            return self
        raise GuiEditError("%s has no %s = { }" % (self._label(), key))

    def put(self, key, value):
        """Set a plain value (key = value). The line is added after the name when the key is missing."""
        start, end, spans = self._own()
        code = self.gui._code()
        for a, b in spans:
            m = re.search(r"(?i)((?<![\w])" + re.escape(key) + r"\s*=\s*)(\"[^\"]*\"|[^\s{}]+)", code[a:b])
            if m:
                s, e = a + m.start(2), a + m.end(2)
                self.gui.text = self.gui.text[:s] + str(value) + self.gui.text[e:]
                return self
        return self.add("%s = %s" % (key, value))

    def add(self, line):
        """Add a line (or several, separated by a newline) right after the widget's name line."""
        start, end, spans = self._own()
        code = self.gui._code()
        newline = "\r\n" if "\r\n" in self.gui.text else "\n"
        for a, b in spans:
            m = re.search(r"(?i)(?<![\w])name\s*=\s*\"?[^\s\"{}]+\"?", code[a:b])
            if m:
                line_start = self.gui.text.rfind("\n", 0, a + m.start()) + 1
                indent = re.match(r"[ \t]*", self.gui.text[line_start:]).group(0)
                line_end = self.gui.text.find("\n", a + m.end())
                line_end = len(self.gui.text) if line_end < 0 else line_end + 1
                added = "".join(indent + part + newline for part in line.split("\n"))
                self.gui.text = self.gui.text[:line_end] + added + self.gui.text[line_end:]
                return self
        raise GuiEditError("%s has no name line to add after" % self._label())

    def remove(self, key):
        """Remove the line of a plain value, or of a block value written on one line (position = { x=1 y=2 })."""
        start, end, spans = self._own()
        code = self.gui._code()
        for a, b in spans:
            m = re.search(r"(?i)(?<![\w])" + re.escape(key) + r"\s*=\s*$", code[a:b])
            if m:
                close = self.gui._match(code, b)
                line_start = self.gui.text.rfind("\n", 0, a + m.start()) + 1
                line_end = self.gui.text.find("\n", close)
                line_end = len(self.gui.text) if line_end < 0 else line_end + 1
                if "\n" in self.gui.text[line_start:close]:
                    raise GuiEditError("%s: %s spans several lines; remove it by hand" % (self._label(), key))
                self.gui.text = self.gui.text[:line_start] + self.gui.text[line_end:]
                return self
        for a, b in spans:
            m = re.search(r"(?i)(?<![\w])" + re.escape(key) + r"\s*=\s*(\"[^\"]*\"|[^\s{}]+)", code[a:b])
            if m:
                line_start = self.gui.text.rfind("\n", 0, a + m.start()) + 1
                line_end = self.gui.text.find("\n", a + m.end())
                line_end = len(self.gui.text) if line_end < 0 else line_end + 1
                self.gui.text = self.gui.text[:line_start] + self.gui.text[line_end:]
                return self
        raise GuiEditError("%s has no %s to remove" % (self._label(), key))

    def shift(self, key="position", **deltas):
        """Add to numbers of a block value: shift("position", x=234) moves the widget right."""
        values = {}
        for component, delta in deltas.items():
            current = self.get(key, component)
            if current is None:
                raise GuiEditError("%s: %s has no %s" % (self._label(), key, component))
            number = float(current)
            total = number + delta
            values[component] = int(total) if float(total).is_integer() else total
        return self.set(key, **values)
