# Phase <id>: <screen name>

Copy this file to `wiki/phases/<screen>.md` when a phase starts (stage 1 of [Workflow](Workflow.md)) and fill it in as the phase goes: the orchestrator writes Scope, Roles and handoffs, Decisions and Close; the designer's work lands in Inventory and Proposal; the builder writes Build and the Fix rounds; the game checker adds the rows of Game checks. The [Roadmap](Roadmap.md) keeps only the status and a link here.

## Scope

- Vanilla file and windows:
- What the vanilla screen crams or hides (from the screenshot):
- Out of scope:

## Roles and handoffs

- Handoff folder: `scratch/phases/<id>/` (not in the repository)
- Builder: `builder-screen` or `builder-script`, and why
- Design page: link (`python -I tools/make_design_page.py <id>`), and the date of each round
- Layout file: `scratch/phases/<id>/layout.json` (the mock-ups and the build are made from it)
- Contracts written (hotkeys, shared rows, shared files): yes / none needed
- Worktrees (several screens at once): paths, or "main tree"

## Inventory

- Vanilla reference: `reference/vanilla/<screen>.jpg` and `-panel.png` exist and show the state the redesign is about. If not: the recipe in `tools/scenes/<screen>.json` ([Game Recipes](Game-Recipes.md)), then `tools/Invoke-GameCheck.ps1 <screen> -Vanilla -SaveReference`:
- Where each window sits (`at`, measured with `render_gui.py --verify`) and the `expect` widgets:
- `tools/Show-GuiOutline.ps1 <file> <window> -All` done for:
- `tools/Show-GuiOutline.ps1 <file> <window> -Comments`: sizes set in code, grid-computed widths:
- `tools/Show-CodeNames.ps1 <file> <window>`: names marked `+` (data the code could fill):
- Lists and their rows (added to `tools/gui-links.json`):
- Bitmap backgrounds and which option of the Design Rules applies:
- Engine facts this screen depends on that are still **untested** in [Engine Facts](../Engine-Facts.md):

## Proposal

Generated from `scratch/phases/<id>/design.json` by `python -I tools/phase_notes.py <id>` (the orchestrator runs it at every gate). Write under the markers only what the design file cannot hold.

<!-- generated: proposal (tools/phase_notes.py; edit the handoff file, not this) -->
<!-- end generated: proposal -->

## Decisions

Dated, one line each: what was agreed, what was sent back and why. The user's answers to the design page's questions go here, with the date (they are also in `decisions-final.json`).

- 

## Build

Generated from `scratch/phases/<id>/build/build.json`: what was built, deviations, fallbacks, not seen in game, the game check line and the checker's checklist, the tests.

<!-- generated: build (tools/phase_notes.py; edit the handoff file, not this) -->
<!-- end generated: build -->

## Game checks

One row per launch, generated from `scratch/phases/<id>/checks/check-<n>.json` (columns | # | Date | Build | By | Checked | Result | Screenshot | Taught |; By = `game-checker`). The user's own tests (their game and playset) are added by hand under the markers: date, what they looked at, their words, their screenshots, and the play verdict ([Design Language](Design-Language.md), "Review questions"): what they looked for and did not find; what they misread; what they still opened another screen or vanilla's window for.

<!-- generated: game checks (tools/phase_notes.py; edit the handoff file, not this) -->
<!-- end generated: game checks -->

## Fix rounds

Generated from `scratch/phases/<id>/fixes.json`: one line per fix under a heading per round (issue, cause, fix, what the re-test should look at). Findings from the user's own game name their screenshot.

<!-- generated: fix rounds (tools/phase_notes.py; edit the handoff file, not this) -->
<!-- end generated: fix rounds -->

## Close

- [ ] Roadmap status and link
- [ ] README "Reworked screens"
- [ ] Workshop description
- [ ] `version` in `descriptor.mod`
- [ ] Engine Facts rows confirmed or added
- [ ] Scene file final (`tools/scenes/<screen>.json`)
- [ ] Finished screen stored: `tools/Invoke-GameCheck.ps1 <screen> -SaveReference` (`reference/mod/`)
