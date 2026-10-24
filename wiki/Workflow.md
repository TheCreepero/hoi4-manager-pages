# Workflow: who does what in a phase

(from the 1440p mod) Copied at the split of 2026-10-21; the steps that lay out an override file (`apply_layout.py`, `Compare-Baseline.ps1`) are the 1440p UI mod's and do not apply to a generated page. A phase is run by several agents with one human. This page says who does each step, what each hands to the next and where the user decides. The steps themselves stay in [Design Rules](Design-Rules.md), "Recipe for a screen phase"; this page only assigns them. Adopted by the user on 2026-10-16 after the redesign pass of the same day had run this way with briefs written for the occasion (`scratch/redesign/BRIEF.md`, `BUILD-BRIEF.md`, `FIX-BRIEF.md`, `CONTRACTS.md`, not in the repository).

In Claude Code the roles are the agent definitions under `.claude/agents/` and the runbook is the skill `/pages-phase <id> [<scene> ...]` (`.claude/skills/pages-phase/SKILL.md`, with an identical copy under `.agents/skills/pages-phase/` so that Antigravity loads it too). Another tool, or a person, follows the same roles in the same order by reading those files.

## Roles and models

| Role | Who | May | May not |
|---|---|---|---|
| **Orchestrator** | the interactive session (Claude Fable 5.1) | open the phase, write the contracts, brief and continue the agents, review every handoff, publish the design page, ask the user at the gates, read the captures itself, write the knowledge register, close the phase | build or design in the agents' place; start the game without the user's grant; commit |
| **Designer** | agent `designer` (Claude Opus 5.5) | read everything; run the read-only tools and the renderer; write under `scratch/phases/<id>/` | edit anything else in the repository; start the game; write the register; commit |
| **Builder** | agent `builder-script` (Claude Opus 5.5) for a scripted page (`tools/build_managers.py`, `tools/build_records.py`, script, localisation) and for a fix round whose cause is unknown; `builder-screen` (Claude Sonnet 5.5), the builder of a vanilla screen, stays in the 1440p UI mod | edit the mod's files, the scene, `tools/gui-links.json`, the tests' lists and its own phase notes; run the renderer and the tests | start the game; write the register; commit; change `wiki/Roadmap.md`, `README.md`, `descriptor.mod`, `AGENTS.md` |
| **Game checker** | agent `game-checker` (Claude Opus 5.5) | start the game through the harness once the user has granted the launches; read the captures and `error.log`; write `scratch/phases/<id>/checks/` and the rows of the "Game checks" table in the phase notes | edit any other file; fix anything; let more than ten days pass; save |
| **The user** | the human (called "the tester" in older phase notes) | approve the design, grant the launches, test in their own game, commit | |

A fix round goes back to the **same builder agent**, continued with the findings, not to a new one: it still holds the design and its own decisions. A builder is spawned anew only when the first one is gone.

## The stages

Recipe steps are those of [Design Rules](Design-Rules.md). Every handoff file lives in `scratch/phases/<id>/` (git-ignored); the durable record is `wiki/phases/<id>.md` and the published design page.

1. **Open** (orchestrator). Copy [Phase Template](Phase-Template.md) to `wiki/phases/<id>.md` and fill Scope. Create `scratch/phases/<id>/`. Write `contracts.md`: hotkeys already taken (`grep -rn 'shortcut = "' interface/ tools/build_managers.py tools/build_records.py`) and the new ones, shared rows and windows, shared files and who owns each, frames two pages share. Choose the builder by kind. One screen: work in the main tree. Several screens at once: one worktree per builder ([Contributing](Contributing.md), "Several screens at once").
2. **Design** (designer): recipe steps 1 and 2. Hands back `layout.json` (every number of the proposal, the one file the mock-ups and the build are made from), `design.json`, the mock-ups drawn from the layout with `tools/mockup.py` (plus a short script for what the code draws, if any), `audit.json` from `python -I tools/ux_audit.py <id>` (the linter, contrast, fonts, small buttons and the squinted figures; run after the figures exist), and a reply of at most 15 lines. Reads the bindings reports by window, never the decompiled code.
3. **Design review, gate A** (orchestrator). The design passes when:
   - every addition names the row of "What a redesign can add" or the register id that makes it possible, and the window bindings report backs every value shown;
   - every figure group has the vanilla capture, the current state and the proposal at the same scale and the same crop box;
   - the contracts are kept, or a deviation is written down;
   - what only the game can show is under `openInGame`, not promised;
   - `python -I tools/check_playset.py` has been read for the files the design touches, and a text another mod can lengthen has a box of fixed size;
   - `python -I tools/lint_layout.py scratch/phases/<id>/layout.json` leaves no error, and each excepted rule has a reason the orchestrator accepts ([Design Language](Design-Language.md), "How the rules are checked");
   - `tasks` holds three to five player tasks counted on vanilla and on the proposal, and the proposal is no worse on any of them, or the difference is a decision;
   - `heuristics` answers the ten review questions of [Design Language](Design-Language.md), and each `issue` is fixed or is a decision; the contrast table and the squinted figures of `audit.json` have been read.
   What fails goes back to the same designer. What passes becomes the design page: `python -I tools/make_design_page.py <id>` writes `scratch/phases/<id>/design.html` from the handoff files, with one composite image per figure group (vanilla, current, proposed and later the build, stacked at one scale; also written to `figures/<group>.webp`, the one file per group a review reads), published as an artifact when the tool can (link into the phase notes).
4. **User gate 1: the design.** The user marks the page up and answers the `decisions`. The orchestrator writes each answer, dated, under "Decisions" in the phase notes and into `decisions-final.json`. Nothing is built before this gate.
5. **Build** (builder): recipe steps 3 to 6, for a page through the generator (`tools/build_managers.py`, `tools/build_records.py`) with the numbers of `layout.json`. Hands back `build/build.json` (from which `tools/phase_notes.py` writes the notes' Build section), `build/build-<group>.png` for every figure group, and a reply of at most 20 lines. The gate inside: `build.ps1 -Check <scene>` green, every render looked at.
6. **Build review, gate B** (orchestrator). Read the diff of the generator and of the files it wrote: only intended changes. `python -I tools/lint_gui.py` passes, and a line the build adds to `tools/design_exceptions.json` has a reason the orchestrator accepts. Compare each build render with its mock-up. Read the deviations: each one has a reason the design or the rules back. Run `tools/ux_audit.py <id>` and `make_design_page.py` again so the page carries the build renders and their squinted figures (same artifact). What fails goes back to the same builder.
7. **User gate 2: the launches.** The orchestrator asks once for the phase, naming the scenes, how many launches, and that a check stays paused on 1 January 1936 or runs at most ten days with the autosave copied first. A vague grant has not got a launch through; the grant names the launches. The user's own screen and mouse are taken while the harness runs.
8. **Game check** (game checker): recipe step 7. `tools/Invoke-GameCheck.ps1 <scene> [...]` with this mod alone, then with a mod of the playset where [Game Recipes](Game-Recipes.md) asks for it (pages that read characters, leaders, states or equipment). Works through the scene's `checklist` item by item on the crops, diffs `error.log`, reads the clock. Hands back `checks/check-<n>.json` and a reply of at most 20 lines: defects first. Every failed or unseen item and every defect names its `evidence`, a cut of the capture made with `tools/crop_capture.py` into `checks/`, and the `box` it was cut from; each launch names one overview capture per scene. The rows of the "Game checks" table are generated from the file by `tools/phase_notes.py`.
9. **Capture review** (orchestrator). Reads the evidence cuts and one overview capture per scene itself (user, 2026-10-20; before that every crop): the checker's findings are a list to confirm, not a verdict. Decides which are defects, which are the renderer's known blind spots ([Contributing](Contributing.md), "What the renderer does not show") and which only the user can settle. Defects go to the same builder as a fix round; the checker re-runs only the scenes a fix touched. Each round adds entries to `fixes.json` (issue, cause, fix, what the re-test should look at), from which `tools/phase_notes.py` writes the "Fix round <n>" lines of the phase notes.
10. **Report, user gate 3.** When the checks are clean, the orchestrator reports to the user: what was built, the design page with the build renders beside the mock-ups, what the checks showed and with which mods loaded, and the numbered list of what only a human can settle: tooltips, click targets, states a 1936 start does not show, whether a width is too much. The user tests in their own game and playset, and commits.
11. **Close** (orchestrator): recipe step 8. The candidate facts of every handoff (`newFacts`) go to the knowledge register with `Add-HoiKnowledge.ps1`, or are dropped with a reason; then `Export-HoiKnowledge.ps1 -Repo hoi4-manager-pages`. The register is written by the orchestrator only.

The user's own in-game issues (a list and screenshots, as `screenshots/` and `FOUND_ISSUES.txt` on 2026-10-16) enter at stage 9 as findings.

The phase notes are kept current by `python -I tools/phase_notes.py <id>`, run by the orchestrator at every gate: it writes the Proposal, Build, Game checks and Fix rounds sections between markers from the handoff files; Scope, Roles and handoffs, Inventory, Decisions and Close are written by hand.

## The short path

A small phase (the verdict would be `refine` at effort S: a card pass, a chip, a hotkey, a width, a caption; user decision 2026-10-20) has no designer agent. The orchestrator writes `layout.json` and `design.json` itself, with one figure group drawn by `tools/mockup.py` and the choices under `decisions`, runs the linter and `tools/ux_audit.py`, answers only the review questions the change touches (H4 always) and the tasks it changes, makes the page and stops at user gate 1 like any phase. From stage 5 on the path is the same, with the same builder and checker. The path is chosen at stage 1 and written under "Roles and handoffs"; when the work turns out larger (a second figure group, a window that moves, a list that changes), the designer is spawned after all.

## Handoff files

All under `scratch/phases/<id>/`. JSON is UTF-8; strings are plain text with `\n\n` between paragraphs, `**bold**` and `` `code` `` the only markup. Every file a `figures` entry names must exist.

**`contracts.md`** (orchestrator, stage 1): hotkeys, shared rows and windows, shared files and their owners, frames shared by pages, what the agents do not change. The pattern is `scratch/redesign/CONTRACTS.md`.

**`design.json`** (designer, stage 2):

```json
{
  "id": "A3",
  "title": "Short name of the component",
  "kind": "screen | page",
  "scenes": ["division_details"],
  "files": ["interface/zz_1440p_unit_details.gui"],
  "verdict": "rework | refine | keep",
  "summary": "Two to four sentences: what the proposal does and why it is better.",
  "current": "What the vanilla screen, or the current build, does badly.",
  "knowledge": [{"fact": "What a register fact or an executable report opens or closes here", "ids": ["W34"]}],
  "proposal": [{"heading": "Part of the screen", "body": "What it becomes, with sizes."}],
  "table": {"columns": ["Part", "Vanilla", "Current", "Proposed"], "rows": [["Panel", "502x430", "", "..."]]},
  "additions": [{"what": "A caption / hotkey / card / scripted value", "how": "The row of 'What a redesign can add', or the register id"}],
  "tasks": [{"task": "What a player comes here for, in their words", "vanilla": {"clicks": 2, "looks": 3}, "proposed": {"clicks": 0, "looks": 1}, "note": "Where the answer stands now"}],
  "heuristics": [{"id": "H1", "verdict": "pass | issue | n/a", "note": "One sentence; for an issue, the fix or the decision"}],
  "figures": [
    {"file": "vanilla-main.png", "kind": "vanilla", "group": "main", "caption": "..."},
    {"file": "current-main.png", "kind": "current", "group": "main", "caption": "..."},
    {"file": "proposed-main.png", "kind": "proposed", "group": "main", "caption": "..."}
  ],
  "decisions": [{"question": "A choice that is the user's", "options": ["A", "B"], "recommendation": "A, because ..."}],
  "openInGame": ["What only a game check can settle"],
  "risks": ["Other mods, code-placed widgets, patched executable only, ..."],
  "effort": "S | M | L, and one sentence on what the build involves",
  "newFacts": ["Engine facts not in the register yet, with the evidence"]
}
```

`looks` counts the places the eye has to go (a card, a tooltip, another window each count one); the ten `heuristics` ids are the review questions of [Design Language](Design-Language.md). `design.json` may name its figure groups for the page: `"groups": [{"name": "main", "title": "The whole view", "note": "1:1, the same box on the screen"}]`. It is written directly with the Write tool, not through a generator script.

**`layout.json`** (designer, stage 2; the builder changes it only with a deviation): every number of the proposal in one file, read by `tools/mockup.py` for the mock-ups and written by the builder into the generator, so the two share every number. The worked examples are `tools/examples/steel-layout.json` (the steel look, the default) and `tools/examples/a10-layout.json` (a built screen in the card style); the pieces and the rules are in [Design Language](Design-Language.md), and `python -I tools/lint_layout.py <layout>` checks them.

```json
{
  "id": "A10", "prefix": "ar", "scene": "air_region", "file": "interface/zz_1440p_air_region.gui",
  "frame": "reference/mod/air_selection.jpg", "panel": null,
  "windows": [{
    "path": "strategicairview", "at": [712, 300], "position": [-568, -420], "size": [580, 718],
    "background": "GFX_tiled_window_1b_thin_border", "after": "strategic_air_bg",
    "items": [
      {"kind": "title", "name": "title", "x": 3, "y": 3, "w": 574, "h": 44},
      {"kind": "card", "name": "card_b", "x": 6, "y": 130, "w": 568, "h": 238},
      {"kind": "head", "name": "head_forces", "x": 14, "y": 138, "w": 552, "h": 30},
      {"kind": "bands", "name": "band_forces", "x": 14, "y": 168, "w": 552, "row": 32, "rows": 6},
      {"kind": "caption", "name": "cap_{n}", "repeat": {"var": "n", "range": [1, 6], "dy": 32}, "keys": ["AIR_RESERVES_TYPE_1", "..."], "texts": ["Fighters", "..."], "x": 194, "y": 175, "w": 192, "h": 24, "font": "hoi_18mbs", "format": "center"},
      {"kind": "move", "path": "region_name", "x": 16, "y": 10, "w": 370, "h": 32, "font": "hoi_30header", "fixed": true, "sample": "Western Poland"},
      {"kind": "move", "path": "wing_type_left_text_{n}", "repeat": {"var": "n", "range": [1, 4], "dy": 32}, "x": 30, "y": 174, "w": 120, "h": 24, "font": "hoi_20b", "format": "right", "samples": ["805", "0", "276", "3"]},
      {"kind": "plate", "name": "sky", "x": 28, "y": 426, "sprite": "GFX_1440p_AR_sky"},
      {"kind": "sprite", "name": "GFX_wing_types_own", "x": 156, "y": 172, "frame": 1},
      {"kind": "text", "font": "hoi_16mbs", "x": 20, "y": 393, "text": "Our Missions", "w": 140, "align": "center"}
    ]
  }]
}
```

A layout names its look with `style` (`steel`, the default, or `card`) and may waive a rule of the linter with `exceptions` (`[{"rule": "gap", "why": "..."}]`); an item may carry `role` (`title`, `name`, `figure`, `value`, `caption`, `button`: the linter checks its font against it) and `why` (the reason it breaks a rule). `steel` (with `head` 27 or 38) and `steel_title` are the steel pieces, bitmaps `tools/stretch_background.py` cuts from the game's steel bar (into `gfx/interface/mod1440/` for a page); `inset` is the near-black inset. `title`, `card`, `head`, `bands` and `plate` are plates of the mod (`mod1440_<prefix>_<name>` on `GFX_1440p_<PREFIX>_<name>`, declared in `interface/mod1440_ui.gfx`; a `plate` names an existing `sprite`, or a `texture` with its `border`); `caption` is a text of the mod on a localisation `key`; `move` puts a vanilla widget at its new place (`path` as `tools/guiedit.py` takes it; `w` and `h` set `maxWidth` and `maxHeight` on a text and `size` elsewhere; `font`, `format`, `fixed`, `sprite`, raw keys under `set`; `sample` goes into the scene and the mock-up); `text`, `sprite` and `paste` draw in the mock-up only. Numbers are window-relative; `at` is where the window stands on the screen; `after` names the child the plates are inserted after (the background by default; an item may carry its own); `repeat` expands `{n}` and `{i}` with `dx` and `dy` per step and one value per step from `keys`, `texts` or `samples`. What the layout cannot say (new textures, progress bars, lists, sprites the code sets) is the builder's own work, noted in `build.json`.

**`decisions-final.json`** (orchestrator, stage 4): one entry per question of `design.json`, `{"question": "...", "chosen": "...", "by": "user | agent recommendation", "note": "..."}`. Where `by` is "agent recommendation" the builder follows the recommendation.

**`build/build.json`** (builder, stage 5):

```json
{
  "id": "A3",
  "agent": "builder-screen",
  "worktree": "C:\\dev\\Hearts of Iron IV Modding Manager\\mods\\hoi4-1440p-ui-mod",
  "summary": "What was built, two to four sentences.",
  "figures": [{"file": "build-main.png", "group": "main", "caption": "..."}],
  "deviations": [{"what": "Where the build differs from the design", "why": "..."}],
  "fallbacks": [{"if": "What the game check might show", "then": "What to change"}],
  "notSeenInGame": ["..."],
  "gameCheck": "tools/Invoke-GameCheck.ps1 division_details",
  "checklist": ["Numbered items for the game checker"],
  "sharedFiles": ["interface/mod1440_ui.gfx"],
  "tests": "build.ps1 -Check division_details: 412 passed, 0 failed",
  "newFacts": ["Candidate engine facts with evidence"]
}
```

**`checks/check-<n>.json`** (game checker, stage 8), one per round:

```json
{
  "id": "A3",
  "round": 1,
  "date": "2026-10-17",
  "build": "80e628d+dirty",
  "playset": "this mod only | Reordered Pack (USA)",
  "launches": [{"command": "tools/Invoke-GameCheck.ps1 division_details", "captures": ["scratch/checks/division_details_crop.png"], "clock": "1 Jan 1936", "errorLog": ["lines the vanilla baseline does not have"]}],
  "checklist": [{"item": 1, "result": "pass | fail | cannot see", "evidence": "scratch/phases/A3/checks/evidence-1-item1.png", "box": [1298, 300, 2212, 700], "note": "..."}],
  "defects": [{"what": "...", "where": "scene/widget", "evidence": "scratch/phases/A3/checks/evidence-1-d1.png", "box": [0, 0, 100, 100]}],
  "forTheUser": ["What a crop cannot settle"],
  "autosave": "unchanged | not touched | hash differs",
  "newFacts": ["..."]
}
```

A passed item names the overview capture as its evidence; a failed or unseen item, and every defect, names a cut made with `python -I tools/crop_capture.py <capture> <l,t,r,b> --out scratch/phases/<id>/checks/evidence-<n>-<item>.png` and the box. The orchestrator reads the cuts and one overview per scene.

**`fixes.json`** (builder, stage 9), one entry per fix, appended round by round:

```json
[{"round": 1, "date": "2026-10-17", "issue": "What the check showed", "cause": "Why", "fix": "What changed, and where in layout.json", "retest": "What the re-test should look at", "by": "builder-screen"}]
```

## Several screens at once

The orchestrator may run several designers in parallel, and several builders each in its own worktree; the rules for the worktrees, the merge and the shared files are in [Contributing](Contributing.md), "Several screens at once". The contracts are written before the first agent starts. One design page carries every proposal, one report every check.
