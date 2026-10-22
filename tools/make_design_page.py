"""The design page of a phase, made from its handoff files (wiki/Workflow.md, "Handoff files"):

    python -I tools/make_design_page.py A10            # scratch/phases/A10/design.html
    python -I tools/make_design_page.py A10 --open     # and open it in the browser

Reads scratch/phases/<id>/design.json, decisions-final.json, build/build.json, checks/check-*.json and audit.json
(tools/ux_audit.py), whichever exist, and writes design.html beside them, with one composite image per figure group (vanilla, current, proposed
and build stacked at the same scale, labelled, WebP) embedded, so the page stays small and the orchestrator reads
one image per group. The composites are also written to scratch/phases/<id>/figures/<group>.webp. The orchestrator
publishes the page with the Artifact tool at every gate; the same file, so the link stays.

design.json may name its figure groups (optional): "groups": [{"name": "main", "title": "The whole view", "note": "1:1, ..."}].
"""
import argparse
import base64
import glob
import html
import io
import json
import os
import re
import sys
import webbrowser

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from layout import HEURISTICS  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIND_ORDER = ["vanilla", "current", "proposed", "alternative", "build"]
KIND_LABEL = {"vanilla": "Vanilla", "current": "Current build", "proposed": "Proposed", "alternative": "Alternative", "build": "Built"}
KIND_COLOUR = {"vanilla": (70, 76, 74), "current": (92, 84, 60), "proposed": (15, 92, 128), "alternative": (90, 70, 120), "build": (43, 116, 64)}

CSS = """
:root{--bg:#eef0ef;--panel:#ffffff;--fg:#1b211f;--muted:#5a6560;--line:#d3d8d5;--accent:#9a5b12;--rec:#0f5c80;--ok:#2b7440;--tag:#e3e7e5;--plot:#0c0f0e;
--sans:"IBM Plex Sans",system-ui,sans-serif;--mono:"IBM Plex Mono",ui-monospace,monospace}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#121615;--panel:#1a201e;--fg:#e4e9e6;--muted:#97a39d;--line:#2f3835;--accent:#e2a24a;--rec:#6db6e0;--ok:#72c98a;--tag:#26302c;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#121615;--panel:#1a201e;--fg:#e4e9e6;--muted:#97a39d;--line:#2f3835;--accent:#e2a24a;--rec:#6db6e0;--ok:#72c98a;--tag:#26302c;color-scheme:dark}
body{background:var(--bg);color:var(--fg);font:15px/1.55 var(--sans);margin:0;padding-block:28px 64px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
main{max-width:1180px;margin:0 auto;display:flex;flex-direction:column;gap:28px}
h1{font:600 28px/1.2 var(--sans);margin:0 0 6px;text-wrap:balance}
h2{font:600 19px/1.3 var(--sans);margin:0 0 10px;text-wrap:balance}
h3{font:600 16px/1.3 var(--sans);margin:22px 0 4px}
h4{font:600 15px/1.3 var(--sans);margin:14px 0 2px}
p{margin:0 0 10px;max-width:75ch}
.sub{color:var(--muted)}
section{background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:20px;min-width:0}
table{border-collapse:collapse;width:100%;font-size:14px;font-variant-numeric:tabular-nums}
th,td{text-align:left;vertical-align:top;padding:8px 10px;border-bottom:1px solid var(--line)}
th{font:600 12px/1.2 var(--mono);letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.tw{overflow-x:auto}
.facts{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:12px;margin-top:6px}
.facts div{border:1px solid var(--line);border-radius:4px;padding:12px 14px;min-width:0}
.facts b{display:block;margin-bottom:4px}
.dec{border-top:1px solid var(--line);padding:16px 0;display:grid;grid-template-columns:2.2em 1fr;gap:4px 12px}
.dec:first-of-type{border-top:0}
.dec .n{font:600 22px/1 var(--mono);color:var(--accent)}
.dec h3{margin:0 0 6px}
.dec ul{margin:0 0 8px}
.rec{color:var(--ok);font-weight:600}
.chosen{color:var(--rec);font-weight:600}
.fig{margin:14px 0 0}
figcaption{font-size:13.5px;color:var(--muted);margin-bottom:6px}
.tag{font:600 11px/1 var(--mono);letter-spacing:.06em;text-transform:uppercase;padding:4px 6px;border-radius:3px;margin-right:8px;background:var(--tag);color:var(--fg)}
.scroll{overflow-x:auto;border:1px solid var(--line);border-radius:4px;background:var(--plot)}
.scroll img{display:block;width:100%;height:auto}
body.one .scroll img{width:auto;max-width:none}
button{font:inherit;font-size:13px;padding:6px 12px;border:1px solid var(--line);background:var(--tag);color:var(--fg);border-radius:4px;cursor:pointer}
button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
ul{margin:0;padding-left:1.2em}li{margin-bottom:5px;max-width:80ch}
code{font:13px var(--mono);background:var(--tag);padding:1px 4px;border-radius:3px}
.bar{position:sticky;top:env(safe-area-inset-top,0px);z-index:5;display:flex;justify-content:flex-end}
.state{display:inline-block;padding:3px 8px;border-radius:3px;background:var(--tag);font-size:13px}
"""

e = html.escape


def rich(text):
    """The handoff files' text: paragraphs on a blank line, **bold** and `code` the only markup."""
    if not text:
        return ""
    out = []
    for para in re.split(r"\n\s*\n", text.strip()):
        p = e(para).replace("\n", " ")
        p = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", p)
        p = re.sub(r"`([^`]+)`", r"<code>\1</code>", p)
        out.append("<p>%s</p>" % p)
    return "".join(out)


def inline(text):
    p = e(text or "")
    p = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", p)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", p)


def read_json(path):
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


# ---------------------------------------------------------------- the composite figures
def label_font(size=18):
    for name in ("segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def composite(figures, folder, out_path):
    """The figures of one group stacked in one image: a label bar over each, all at the width of the widest."""
    tiles = []
    for fig in figures:
        path = os.path.join(folder, fig["file"])
        if not os.path.isfile(path):
            raise FileNotFoundError("figure %s of the group %s is missing" % (fig["file"], fig.get("group")))
        tiles.append((fig, Image.open(path).convert("RGB")))
    width = max(img.width for _f, img in tiles)
    bar, gap = 34, 10
    height = sum(img.height + bar for _f, img in tiles) + gap * (len(tiles) - 1)
    out = Image.new("RGB", (width, height), (12, 15, 14))
    draw = ImageDraw.Draw(out)
    font = label_font(18)
    y = 0
    for fig, img in tiles:
        kind = fig.get("kind", "proposed")
        draw.rectangle((0, y, width, y + bar), fill=KIND_COLOUR.get(kind, (60, 60, 60)))
        text = KIND_LABEL.get(kind, kind.capitalize())
        if fig.get("caption"):
            text += "  -  " + fig["caption"]
        draw.text((10, y + 7), text[:220], fill=(240, 242, 240), font=font)
        out.paste(img, (0, y + bar))
        y += bar + img.height + gap
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    out.save(out_path, "WEBP", quality=85, method=4)
    return out_path


def data_uri(path):
    with open(path, "rb") as handle:
        return "data:image/webp;base64," + base64.b64encode(handle.read()).decode()


# ---------------------------------------------------------------- the page
def group_order(design):
    seen = []
    for fig in design.get("figures", []):
        if fig["group"] not in seen:
            seen.append(fig["group"])
    return seen


def figure_rows(design, build):
    """{group: [figures in kind order]}: the design's, then the build's (as kind "build")."""
    rows = {g: [] for g in group_order(design)}
    for fig in design.get("figures", []):
        rows[fig["group"]].append(dict(fig, folder="design"))
    for fig in (build or {}).get("figures", []):
        rows.setdefault(fig["group"], []).append(dict(fig, kind="build", folder="build"))
    for g in rows:
        rows[g].sort(key=lambda f: (KIND_ORDER.index(f.get("kind", "proposed")) if f.get("kind") in KIND_ORDER else 9))
    return rows


def section(title, body, sub=None):
    head = "<h2>%s</h2>" % e(title)
    if sub:
        head += '<p class="sub">%s</p>' % inline(sub)
    return "<section>%s%s</section>" % (head, body)


def table_html(columns, rows):
    head = "".join("<th>%s</th>" % e(c) for c in columns)
    body = "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % c for c in row) for row in rows)
    return '<div class="tw"><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (head, body)


def review_section(design):
    """The player tasks (vanilla against the proposal) and the answers to the review questions of design.json."""
    body = ""
    tasks = design.get("tasks") or []
    if tasks:
        def cell(side):
            side = side or {}
            return "%s / %s" % (side.get("clicks", ""), side.get("looks", ""))
        body += "<h3>Player tasks</h3>" + table_html(["Task", "Vanilla: clicks / places", "Proposed: clicks / places", "Note"],
                                                       [[inline(t.get("task", "")), e(cell(t.get("vanilla"))), e(cell(t.get("proposed"))), inline(t.get("note", ""))] for t in tasks])
    answers = {h.get("id"): h for h in design.get("heuristics") or []}
    if answers:
        rows = []
        for hid, title, question in HEURISTICS:
            a = answers.get(hid, {})
            verdict = a.get("verdict", "not answered")
            mark = '<span class="rec">%s</span>' % e(verdict) if verdict == "pass" else '<span class="chosen">%s</span>' % e(verdict)
            rows.append(["<b>%s</b> %s" % (e(hid), e(title)), e(question), mark, inline(a.get("note", ""))])
        body += "<h3>Review questions</h3>" + table_html(["Question", "Asks", "Answer", "Note"], rows)
    if not body:
        return ""
    return section("Tasks and review", body, "What a player does on this screen, counted in clicks and in places the eye must go, vanilla against the proposal; and the designer's answers to the review questions of the Design Language page. An issue there is fixed or is one of the decisions below.")


def audit_section(phase_dir):
    """What tools/ux_audit.py measured: the linter, the contrast, the fonts, small buttons, the squinted figures."""
    audit = read_json(os.path.join(phase_dir, "audit.json"))
    if not audit:
        return ""
    body = ""
    lint = audit.get("lint")
    if lint:
        c = lint["counts"]
        body += "<p>Linter (%s look): %d error(s), %d warning(s), %d excepted.</p>" % (e(audit.get("style", "")), c["error"], c["warn"], c["excepted"])
        if lint["findings"]:
            body += table_html(["Level", "Rule", "Where", "Finding", "Reason"],
                               [[e(f["level"]), e(f["rule"]), e("%s %s" % (f["window"], f["item"])), e(f["message"]), e(f.get("why") or "")] for f in lint["findings"]])
    contrast = audit.get("contrast")
    if contrast is not None:
        low = [c for c in contrast if not c["ok"]]
        body += "<h3>Contrast</h3><p>%d of %d texts under the floor (4.5:1, or 3:1 for large text). The game's text shadows read better than the ratio says.</p>" % (len(low), len(contrast))
        if low:
            body += table_html(["Ratio", "Needed", "Where", "Font", "Text"],
                               [["%.2f" % c["ratio"], "%.1f" % c["needed"], e("%s %s" % (c["window"], c["item"])), e(c["font"]), e(c["text"])] for c in low])
    if audit.get("fonts"):
        body += "<h3>Fonts</h3><p>%s</p>" % ", ".join("<code>%s</code> x%d" % (e(f), n) for f, n in audit["fonts"].items())
    if audit.get("targets"):
        body += "<h3>Small buttons</h3><ul>%s</ul>" % "".join("<li>%s %s: %dx%d</li>" % (e(t["window"]), e(t["item"]), t["size"][0], t["size"][1]) for t in audit["targets"])
    for rel in audit.get("squint", []):
        path = os.path.join(phase_dir, *rel.split("/"))
        if os.path.isfile(path):
            group = os.path.basename(rel)[:-len("-squint.webp")]
            body += ('<figure class="fig"><figcaption><span class="tag">%s</span>Squinted: blurred and grey, what still stands out is what the eye finds first</figcaption>'
                     '<div class="scroll"><img src="%s" alt="%s squinted"></div></figure>' % (e(group), data_uri(path), e(group)))
    return section("Measured", body, "Made by tools/ux_audit.py from the layout file and the figures.")


def make_page(phase_dir, full=False):
    design = read_json(os.path.join(phase_dir, "design.json"))
    if not design:
        raise FileNotFoundError("no design.json in " + phase_dir)
    final = read_json(os.path.join(phase_dir, "decisions-final.json")) or []
    build = read_json(os.path.join(phase_dir, "build", "build.json"))
    checks = [read_json(p) for p in sorted(glob.glob(os.path.join(phase_dir, "checks", "check-*.json")))]
    checks = [c for c in checks if c]
    pid = design.get("id", os.path.basename(phase_dir))
    title = design.get("title", pid)

    if checks:
        launches = sum(len(c.get("launches", [])) for c in checks)
        defects = sum(len(c.get("defects", [])) for c in checks[-1:])
        state = "Checked in the game: %d launch(es), %d open defect(s) after the last round." % (launches, defects)
    elif build:
        state = "Built and rendered; not seen in the game yet."
    else:
        state = "Nothing is built yet."

    parts = ['<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
             "<title>%s</title>" % e(title), '<meta name="claude:viewport-fit-sides" content="cover">',
             '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@500;600&family=IBM+Plex+Sans:wght@400;600&display=swap">',
             "<style>%s</style></head><body><main>" % CSS]
    parts.append('<header><h1>%s</h1><p class="sub">Phase %s of HOI4 Manager Pages, %s. Verdict: %s, effort %s. <span class="state">%s</span></p></header>'
                 % (e(title), e(pid), e(design.get("kind", "screen")), e(design.get("verdict", "")), e(design.get("effort", "")), e(state)))

    # what changes and why
    body = rich(design.get("summary"))
    if design.get("current"):
        body += "<h3>What vanilla does badly</h3>" + rich(design["current"])
    for part in design.get("proposal", []):
        body += "<h4>%s</h4>%s" % (inline(part.get("heading", "")), rich(part.get("body", "")))
    table = design.get("table")
    if table and table.get("rows"):
        cols = table.get("columns", [])
        body += '<div class="tw"><table><thead><tr>%s</tr></thead><tbody>' % "".join("<th>%s</th>" % e(c) for c in cols)
        for row in table["rows"]:
            body += "<tr>%s</tr>" % "".join("<td>%s</td>" % inline(str(c)) for c in row)
        body += "</tbody></table></div>"
    parts.append(section("What changes and why", body))

    if design.get("knowledge"):
        facts = "".join('<div><b>%s</b>%s</div>' % (e(", ".join(k.get("ids", []))) or "Fact", inline(k.get("fact", ""))) for k in design["knowledge"])
        parts.append(section("What the engine allows", '<div class="facts">%s</div>' % facts,
                             "Register facts and executable reads the design rests on; the ids resolve in the knowledge register."))
    if design.get("additions"):
        items = "".join("<li>%s <span class=\"sub\">(%s)</span></li>" % (inline(a.get("what", "")), inline(a.get("how", ""))) for a in design["additions"])
        parts.append(section("What the redesign adds", "<ul>%s</ul>" % items, "Each with the rule or the register fact that allows it."))

    # figures
    rows = figure_rows(design, build)
    titles = {g.get("name"): g for g in design.get("groups", [])}
    figs = ['<div class="bar"><button id="zoom" type="button" aria-pressed="false">Show at 1:1</button></div>']
    for group, fl in rows.items():
        meta = titles.get(group, {})
        figs.append("<h3>%s</h3>" % e(meta.get("title", group.capitalize())))
        if meta.get("note"):
            figs.append('<p class="sub">%s</p>' % inline(meta["note"]))
        for fig in fl:
            fig["path"] = os.path.join(phase_dir, "build" if fig["folder"] == "build" else "", fig["file"])
        out = os.path.join(phase_dir, "figures", "%s.webp" % group)
        composite([dict(f, file=os.path.relpath(f["path"], phase_dir)) for f in fl], phase_dir, out)
        caption = "; ".join("%s: %s" % (KIND_LABEL.get(f.get("kind"), f.get("kind")), f["file"]) for f in fl)
        figs.append('<figure class="fig"><figcaption><span class="tag">%s</span>%s</figcaption><div class="scroll"><img src="%s" alt="%s"></div></figure>'
                    % (e(group), e(caption), data_uri(out), e(group)))
    parts.append(section("Vanilla beside the proposal", "".join(figs),
                         "Each group stacks the vanilla capture, the current build where one exists, the proposal and, after the build, the render of the mod's files, all cut at the same box and the same scale. The button shows them at 1:1."))

    review = review_section(design)
    if review:
        parts.append(review)
    measured = audit_section(phase_dir)
    if measured:
        parts.append(measured)

    if build:
        body = rich(build.get("summary"))
        if build.get("deviations"):
            body += "<h3>Where the build differs from the design</h3><ul>%s</ul>" % "".join(
                "<li>%s: %s</li>" % (inline(d.get("what", "")), inline(d.get("why", ""))) for d in build["deviations"])
        if build.get("fallbacks"):
            body += "<h3>Fallbacks</h3><ul>%s</ul>" % "".join(
                "<li>If %s: %s</li>" % (inline(f.get("if", "")), inline(f.get("then", ""))) for f in build["fallbacks"])
        if build.get("tests"):
            body += '<p class="sub">%s</p>' % inline(build["tests"])
        parts.append(section("As built", body))

    answered = {x.get("question"): x for x in final}
    decs = []
    for i, q in enumerate(design.get("decisions", []), 1):
        opts = "".join("<li>%s</li>" % inline(o) for o in q.get("options", []))
        ans = answered.get(q.get("question"))
        chosen = '<p class="chosen">Chosen: %s</p>' % inline(ans["chosen"]) if ans else ""
        decs.append('<div class="dec"><div class="n">%d</div><div><h3>%s</h3><ul>%s</ul><p><span class="rec">Recommended:</span> %s</p>%s</div></div>'
                    % (i, inline(q.get("question", "")), opts, inline(q.get("recommendation", "")), chosen))
    if decs:
        head = "Answered; the choice stands under each question." if final else "Each has a recommendation; answering \"as recommended\" is enough."
        parts.append(section("Decisions for you", "".join(decs), head))

    body = ""
    if design.get("openInGame"):
        body += "<ul>%s</ul>" % "".join("<li>%s</li>" % inline(x) for x in design["openInGame"])
    if build and build.get("notSeenInGame"):
        body += "<h3>Not seen in game after the build</h3><ul>%s</ul>" % "".join("<li>%s</li>" % inline(x) for x in build["notSeenInGame"])
    if design.get("risks"):
        body += "<h3>Risks</h3><ul>%s</ul>" % "".join("<li>%s</li>" % inline(x) for x in design["risks"])
    if body:
        parts.append(section("What only the game can show", body))

    if checks:
        trs = []
        for c in checks:
            trs.append("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%d</td><td>%d</td><td>%s</td></tr>" % (
                e(str(c.get("round", ""))), e(c.get("date", "")), e(c.get("build", "")), e(c.get("playset", "")),
                len(c.get("launches", [])), len(c.get("defects", [])), e(c.get("autosave", ""))))
        body = '<div class="tw"><table><thead><tr><th>Round</th><th>Date</th><th>Build</th><th>Playset</th><th>Launches</th><th>Defects</th><th>Autosave</th></tr></thead><tbody>%s</tbody></table></div>' % "".join(trs)
        last = checks[-1]
        if last.get("defects"):
            body += "<h3>Defects of the last round</h3><ul>%s</ul>" % "".join(
                "<li>%s (%s)</li>" % (inline(d.get("what", "")), inline(d.get("where", ""))) for d in last["defects"])
        if last.get("forTheUser"):
            body += "<h3>For you to settle</h3><ul>%s</ul>" % "".join("<li>%s</li>" % inline(x) for x in last["forTheUser"])
        parts.append(section("Game checks", body))

    parts.append("</main><script>(function(){var b=document.getElementById('zoom');if(!b)return;b.addEventListener('click',function(){"
                 "var on=document.body.classList.toggle('one');b.setAttribute('aria-pressed',on?'true':'false');b.textContent=on?'Fit to width':'Show at 1:1';});})();</script></body></html>")
    out = os.path.join(phase_dir, "design.html")
    with io.open(out, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(parts))
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description="Make the design page of a phase from its handoff files.")
    parser.add_argument("id", help="the phase id (A10), or a path to its handoff folder")
    parser.add_argument("--phases-dir", default=os.path.join("scratch", "phases"))
    parser.add_argument("--open", action="store_true")
    args = parser.parse_args(argv)
    folder = args.id if os.path.isdir(args.id) else os.path.join(REPO_ROOT, args.phases_dir, args.id)
    out = make_page(os.path.abspath(folder))
    print("%s (%d KB)" % (os.path.relpath(out, REPO_ROOT), os.path.getsize(out) // 1024))
    if args.open:
        webbrowser.open("file:///" + out.replace("\\", "/"))


if __name__ == "__main__":
    sys.exit(main())
