"""The generated sections of a phase's notes, written from its handoff files (wiki/Workflow.md, "Handoff files"):

    python -I tools/phase_notes.py A10            # writes wiki/phases/A10-*.md (the file whose name starts with the id)
    python -I tools/phase_notes.py A10 --check    # exit 1 when the notes are out of date

Four sections are generated, each between markers the tool owns:

    ## Proposal     from scratch/phases/<id>/design.json
    ## Build        from scratch/phases/<id>/build/build.json
    ## Game checks  the table rows, from scratch/phases/<id>/checks/check-<n>.json
    ## Fix rounds   from scratch/phases/<id>/fixes.json

    <!-- generated: proposal (tools/phase_notes.py; edit the handoff file, not this) -->
    ...
    <!-- end generated: proposal -->

Text outside the markers is the hand-written record (Scope, Roles and handoffs, Inventory, Decisions, Close, and
anything added under a generated section after its markers) and stays as it is. A section without markers gets
them right after its heading; a missing section is added before "## Close" (or at the end). The agents write
the JSON files only; the orchestrator runs this tool at every gate. The handoff files are not in the repository,
so the notes are the durable copy.
"""
import argparse
import glob
import io
import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECTIONS = ["proposal", "build", "game checks", "fix rounds"]
HEADINGS = {"proposal": "## Proposal", "build": "## Build", "game checks": "## Game checks", "fix rounds": "## Fix rounds"}


def read_json(path):
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def cell(text):
    return str(text or "").replace("|", "\\|").replace("\n", " ").strip()


def lines_of(items, fmt):
    return "\n".join("- " + fmt(x).replace("\n", " ") for x in items) if items else "- none"


# ---------------------------------------------------------------- the sections
def proposal_text(design):
    if not design:
        return None
    out = []
    out.append("%s. Verdict: %s; effort: %s." % ((design.get("summary") or "").strip().rstrip("."), design.get("verdict", ""), (design.get("effort") or "").strip().rstrip(".")))
    if design.get("current"):
        out.append("")
        out.append("What vanilla does badly: " + design["current"].strip())
    for part in design.get("proposal", []):
        out.append("")
        out.append("**%s.** %s" % (part.get("heading", "").strip().rstrip("."), (part.get("body") or "").strip()))
    table = design.get("table") or {}
    if table.get("rows"):
        cols = table.get("columns", [])
        out.append("")
        out.append("| " + " | ".join(cell(c) for c in cols) + " |")
        out.append("|" + "---|" * len(cols))
        for row in table["rows"]:
            out.append("| " + " | ".join(cell(c) for c in row) + " |")
    if design.get("additions"):
        out.append("")
        out.append("Additions, each with the row of \"What a redesign can add\" or the register id that allows it:")
        out.append("")
        out.append(lines_of(design["additions"], lambda a: "%s (%s)" % (a.get("what", ""), a.get("how", ""))))
    if design.get("openInGame"):
        out.append("")
        out.append("Open until the game shows it:")
        out.append("")
        out.append(lines_of(design["openInGame"], str))
    if design.get("figures"):
        groups = []
        for f in design["figures"]:
            if f["group"] not in groups:
                groups.append(f["group"])
        out.append("")
        out.append("Figure groups of the design page: " + ", ".join(groups) + ".")
    return "\n".join(out)


def build_text(build):
    if not build:
        return None
    out = ["Status: built and checked by render and tests; not seen in game (by %s)." % build.get("agent", "the builder"), ""]
    out.append("**What was built.** " + (build.get("summary") or "").strip())
    if build.get("deviations"):
        out += ["", "**Deviations.**", "", lines_of(build["deviations"], lambda d: "%s: %s" % (d.get("what", ""), d.get("why", "")))]
    if build.get("fallbacks"):
        out += ["", "**Fallbacks.**", "", lines_of(build["fallbacks"], lambda f: "If %s: %s" % (f.get("if", ""), f.get("then", "")))]
    if build.get("notSeenInGame"):
        out += ["", "**Not seen in game.**", "", lines_of(build["notSeenInGame"], str)]
    if build.get("sharedFiles"):
        out += ["", "Shared files touched: " + ", ".join("`%s`" % f for f in build["sharedFiles"]) + "."]
    if build.get("gameCheck"):
        out += ["", "**Game check.** `%s`" % build["gameCheck"]]
    if build.get("checklist"):
        out += ["", "Checklist for the game checker:", ""]
        out += ["%d. %s" % (i, str(item).replace("\n", " ")) for i, item in enumerate(build["checklist"], 1)]
    if build.get("tests"):
        out += ["", "**Tests.** " + build["tests"]]
    if build.get("newFacts"):
        out += ["", "Candidate engine facts (for the orchestrator at the close):", "", lines_of(build["newFacts"], str)]
    return "\n".join(out)


def checks_text(checks):
    if not checks:
        return None
    out = ["| # | Date | Build | By | Checked | Result | Screenshot | Taught |", "|---|---|---|---|---|---|---|---|"]
    n = 0
    for c in checks:
        items = c.get("checklist", [])
        passed = sum(1 for i in items if i.get("result") == "pass")
        failed = [i for i in items if i.get("result") == "fail"]
        unseen = [i for i in items if i.get("result") not in ("pass", "fail")]
        taught = "; ".join(c.get("newFacts", [])) or "-"
        for launch in c.get("launches", []) or [{"command": "(no launch recorded)", "captures": []}]:
            n += 1
            result = "round %s: %d of %d items pass" % (c.get("round", "?"), passed, len(items))
            if failed:
                result += "; fail: " + "; ".join("%s (%s)" % (i.get("item"), i.get("note", "")) for i in failed)
            if unseen:
                result += "; cannot see: " + ", ".join(str(i.get("item")) for i in unseen)
            if c.get("autosave") and c["autosave"] != "not touched":
                result += "; autosave " + c["autosave"]
            if launch.get("errorLog"):
                result += "; error.log: " + "; ".join(launch["errorLog"][:3])
            shots = ", ".join("`%s`" % p for p in launch.get("captures", [])) or "-"
            out.append("| %d | %s | %s | %s | %s (%s) | %s | %s | %s |" % (
                n, cell(c.get("date")), cell(c.get("build")), "game-checker", cell(launch.get("command")), cell(c.get("playset")),
                cell(result), shots, cell(taught)))
    last = checks[-1]
    if last.get("defects"):
        out += ["", "Defects of round %s:" % last.get("round", "?"), "",
                lines_of(last["defects"], lambda d: "%s, at %s (%s)" % (d.get("what", ""), d.get("where", ""), d.get("evidence", "")))]
    if last.get("forTheUser"):
        out += ["", "For the user to settle (a crop cannot):", "", lines_of(last["forTheUser"], str)]
    return "\n".join(out)


def fixes_text(fixes):
    if not fixes:
        return None
    out = []
    rounds = {}
    for f in fixes:
        rounds.setdefault(f.get("round", 1), []).append(f)
    for r in sorted(rounds):
        dates = sorted({f.get("date", "") for f in rounds[r] if f.get("date")})
        out.append("### Fix round %s (%s)" % (r, ", ".join(dates) or "undated"))
        out.append("")
        out.append(lines_of(rounds[r], lambda f: "%s. Cause: %s. Fix: %s. Re-test: %s.%s" % (
            f.get("issue", "").rstrip("."), f.get("cause", "").rstrip("."), f.get("fix", "").rstrip("."), f.get("retest", "").rstrip("."),
            (" (%s)" % f["by"]) if f.get("by") else "")))
        out.append("")
    return "\n".join(out).rstrip()


# ---------------------------------------------------------------- the file
def marker(name, end=False):
    return "<!-- end generated: %s -->" % name if end else "<!-- generated: %s (tools/phase_notes.py; edit the handoff file, not this) -->" % name


def put_section(text, name, body):
    """The notes text with the generated block of `name` replaced, inserted after its heading, or added."""
    block = "%s\n%s\n%s" % (marker(name), body, marker(name, True))
    pattern = re.compile(r"<!-- generated: %s \(.*?-->.*?<!-- end generated: %s -->" % (re.escape(name), re.escape(name)), re.S)
    if pattern.search(text):
        return pattern.sub(lambda m: block, text, count=1)
    heading = re.search(r"(?m)^%s\b[^\n]*\n" % re.escape(HEADINGS[name]), text)
    if heading:
        at = heading.end()
        return text[:at] + "\n" + block + "\n" + text[at:]
    close = re.search(r"(?m)^## Close\b", text)
    section = "%s\n\n%s\n\n" % (HEADINGS[name] + (" (generated)" if name == "build" else ""), block)
    if close:
        return text[:close.start()] + section + text[close.start():]
    return text.rstrip("\n") + "\n\n" + section


def notes_path(pid, phases_dir):
    hits = sorted(glob.glob(os.path.join(phases_dir, pid + "-*.md"))) + sorted(glob.glob(os.path.join(phases_dir, pid + ".md")))
    return hits[0] if hits else None


def render(pid, scratch_dir, notes_text):
    folder = os.path.join(scratch_dir, pid)
    bodies = {
        "proposal": proposal_text(read_json(os.path.join(folder, "design.json"))),
        "build": build_text(read_json(os.path.join(folder, "build", "build.json"))),
        "game checks": checks_text([c for c in (read_json(p) for p in sorted(glob.glob(os.path.join(folder, "checks", "check-*.json")))) if c]),
        "fix rounds": fixes_text(read_json(os.path.join(folder, "fixes.json"))),
    }
    text = notes_text
    for name in SECTIONS:
        if bodies[name] is not None:
            text = put_section(text, name, bodies[name])
    return text, [n for n in SECTIONS if bodies[n] is not None]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Write the generated sections of a phase's notes from its handoff files.")
    parser.add_argument("id")
    parser.add_argument("--notes", help="the notes file (default: wiki/phases/<id>-*.md)")
    parser.add_argument("--scratch", default=os.path.join(REPO_ROOT, "scratch", "phases"))
    parser.add_argument("--check", action="store_true", help="write nothing; exit 1 when the notes differ")
    args = parser.parse_args(argv)
    path = args.notes or notes_path(args.id, os.path.join(REPO_ROOT, "wiki", "phases"))
    if not path or not os.path.isfile(path):
        print("no notes file for %s under wiki/phases/ (copy wiki/Phase-Template.md first)" % args.id)
        return 2
    old = io.open(path, encoding="utf-8", newline="").read()
    newline = "\r\n" if "\r\n" in old else "\n"
    text, written = render(args.id, args.scratch, old.replace("\r\n", "\n"))
    text = text.replace("\n", newline)
    if not written:
        print("no handoff file under %s: nothing generated" % os.path.join(args.scratch, args.id))
        return 0
    if text == old:
        print("%s is up to date (%s)" % (os.path.relpath(path, REPO_ROOT), ", ".join(written)))
        return 0
    if args.check:
        print("%s is out of date: run tools/phase_notes.py %s" % (os.path.relpath(path, REPO_ROOT), args.id))
        return 1
    io.open(path, "w", encoding="utf-8", newline="").write(text)
    print("wrote %s (%s)" % (os.path.relpath(path, REPO_ROOT), ", ".join(written)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
