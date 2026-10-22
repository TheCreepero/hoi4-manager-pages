# Contributing to HOI4 Manager Pages

## Development Workflow
1. Clone the repository.
2. Run `build.ps1 -DevLink` to link the mod directly to your Hearts of Iron IV launcher.
3. Read the [Roadmap](Roadmap.md) for what is being worked on, the [Design Rules](Design-Rules.md) for the rules every screen follows and the recipe, and the [Workflow](Workflow.md) for who does each step: a phase is run by an orchestrator with a designer, a builder and a game checker, and the user decides at three gates. In Claude Code the roles are the agent definitions under `.claude/agents/` and the runbook is `/pages-phase <id>`.
4. Make your modifications in the generator (`tools/build_managers.py`, `tools/build_records.py`) and run `python -I tools/build_managers.py`; keep `tools/scenes/<page>.json` current.
5. Run `build.ps1 -Check <screen>`: validation, the Pester suites and the scene render (`scratch/previews/`). Python 3 with Pillow is needed for the render.
6. Check in the game with `tools/Invoke-GameCheck.ps1 <screen>`: it restarts the game, brings the screen up and writes a capture and a crop to `scratch/checks/` in about two minutes, without a human. Log the launch in `wiki/phases/<screen>.md`.

## Several screens at once

Learned in the redesign pass of 2026-10-16, when thirteen screens and pages were built by parallel agents.

- **One git worktree per screen.** Agents that edit the main tree at the same time overwrite each other's edits of the shared files. Create each worktree with `git -c core.autocrlf=false worktree add --detach <dir>\hoi4-manager-pages HEAD`:
  - Without `core.autocrlf=false` the checkout writes CRLF where the generated files are LF, and `tests/ScriptedGuis.Tests.ps1` reports them out of date.
  - The folder must be named `hoi4-manager-pages`: `tests/BuildScript.Tests.ps1` checks it.
  - Copy `scratch/cache` into the worktree, or the first render rebuilds it: the sprite and window indexes, and under `textures/` every game texture already decoded (Pillow decodes DDS in pure Python, which is most of a first render's time).
  - The whole suite takes about three minutes alone (the render tests draw every window and scene in one `render_gui.py --batch` process) and longer with several worktrees testing at once, so agents run the test files their change touches and the full `build.ps1 -Check` once at the end.
- **Merge whole files, not patches.** Agents' tools rewrite files with CRLF, so a patch can rewrite every line. Compare base, ours and theirs with line endings normalised and merge with `git merge-file`. Write text files with LF and `.ps1` files with CRLF (`.gitattributes`).
- **Regenerate, never merge, generated files.** Merge the generators (`tools/build_managers.py`, `tools/build_records.py`), then run `python -I tools/build_managers.py`.
- **Appended blocks collide.** Every page appends sprites to `interface/mod1440_ui.gfx`; two blocks appended at the same place come out of a line-level merge interleaved. Take one side whole and insert the other block whole after it, then check for duplicate sprite names. Each agent marks its block (`# --- <screen> ---`).
- **Seed a later worktree from the merged state, and keep that state as the merge base.** A worktree seeded from uncommitted merges and merged back against `HEAD` reports conflicts in files it never touched.
- **Fix contracts before the agents start.** Hotkeys, shared windows and rows (`unit_template_entry` serves the division list and the division details window), and any frame two pages share, written down once. A component that cannot keep one reports a deviation.

What the renderer does not show, so a render can look right where the game does not:

- frames of a `corneredTileSpriteType` (the game tiles the whole texture [SPR-024]);
- sprites and flags a scripted GUI names in script (portraits, flags, trait icons);
- the scale of a flag drawn through `GetFlag` (the game ignores it);
- which of two top-level windows is drawn above the other.
