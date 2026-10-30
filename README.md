# HOI4 Manager Pages

Manager pages and a Records window for Hearts of Iron IV at 2560x1440: scripted GUIs that put the values the game has and shows nowhere in one place, and keep a record of the campaign for role-play. Split from the [HOI4 1440p UI Mod](../hoi4-1440p-ui-mod) on 2026-10-21; that mod keeps the reworked vanilla screens, this one stands alone and needs it not.

## The pages

- **Army Readiness** (Shift+M on Recruit & Deploy): manpower, the army's counts, every kind of land equipment with stock, in the field, needed, short and a bar, and one row per general with troops.
- **States** (Shift+M on Construction): one row per controlled state, sorted by any column, a click moves the camera there; totals of the listed states.
- **National Figures** (Shift+M on Politics): the country's figures in tables with their change in a month and in a year and a sparkline each; the summed modifiers in four lists; resources; an equipment table whose balance (stock less what the field is short of) goes below zero in red.
- **History**, the graph of National Figures: forty figures written down on the first of each month and drawn as columns, among them the casualties of every war as a total that never falls and the dead of each month with the deadliest in gold; a figure below zero hangs red from a zero line.
- **Top bar strip**: value chips in the free middle of the top bar, chosen by the player among eighteen values; the choice is kept with the country.
- **The Records** (Shift+J, a handle in the top bar): the **War Diary** (a dated log of wars, peace, capitulations, territory, landings, government, promotions), the **Officers** (every general and admiral with the service record the mod keeps and the decorations the player awards; the order of battle, each general's command and trait effects; with a locally patched `hoi4.exe`, the names of armies and army groups), the **Government** (who holds which office since when, parties, laws, faction) and the **Wars** (one file per enemy and per finished war, with flags, heads of government, figures and lines).
- **The state card** in the state view and **unit honours**: lines the mod writes into a division's own history when a capital falls or on the player's click.

The script lives under `common/` and changes the checksum: no Ironman, no achievements, and in multiplayer every player needs the mod. Every name keeps the prefix of the 1440p mod (`mod1440_*`, `GFX_1440p_SG_*`), because the records live in players' saves.

## Overview

- **Game**: Hearts of Iron IV
- **Supported Version**: `1.19.*`
- **Mod Version**: `1.0`
- **Tags**: Utilities, Gameplay

---

## Directory Architecture

```
hoi4-manager-pages/
|-- descriptor.mod                  # Clausewitz engine descriptor
|-- thumbnail.png                   # Steam Workshop thumbnail (512x512)
|-- build.ps1                       # Lifecycle commands (thin wrapper around tools/HoiModBuild.ps1), plus -Check
|-- common/                         # The script: scripted_guis, scripted_effects, on_actions, synchronized_dynamic_tokens (generated)
|-- interface/                      # mod1440_*.gui (generated) and mod1440_ui.gfx (the sprites)
|-- gfx/interface/mod1440/          # The five textures of the mod's own
|-- localisation/                   # mod1440_l_<language>.yml (generated)
|-- tools/                          # The generator (build_managers.py, build_records.py), the game tables, the renderer, the harness, the scenes
|-- tests/                          # Pester suites
|-- reference/                      # Captures of the pages and of the frames they draw over (dev-only)
|-- wiki/                           # Documentation wiki
|-- .claude/                        # The agents and the /pages-phase skill
|-- assets/                         # Raw graphics and master art assets
|-- artifacts/                      # Packaged release archives (git-ignored)
\-- scratch/                        # Renders, checks, handoff files (git-ignored)
```

Only `common/`, `gfx/`, `interface/`, `localisation/`, `descriptor.mod` and `thumbnail.png` ship.

---

## Development & Automation Commands

Every file of the pages is written by the generator; change the tools, never their output:

```powershell
python -I tools\build_managers.py            # write every file of the pages and the Records window
python -I tools\build_managers.py --check    # exit 1 when a file on disk differs from what would be written
python -I tools\make_game_tables.py          # the tables of characters and victory points, after a game update
python -I tools\render_gui.py --scene war_diary   # draw a page into scratch\previews\
```

All lifecycle tasks are managed through `build.ps1`:

```powershell
# 1. Deploy mod to local Paradox Interactive Hearts of Iron IV mod folder
.\build.ps1 -Deploy

# 2. Configure zero-copy DevLink (the launcher loads this folder itself; restart the game to see a change)
.\build.ps1 -DevLink

# 3. Validate syntax and bracket balance without deploying
.\build.ps1 -ValidateOnly

# 4. Run automated test suites (Pester)
.\build.ps1 -Test

# 5. Package clean release zip archive
.\build.ps1 -Package

# 6. Publish to Steam Workshop (Dry Run preview)
.\build.ps1 -PublishSteam -DryRun

# 7. Clean deployed mod files and temporary archives
.\build.ps1 -Clean

# 8. Everything before a game check of one page: validation, the tests and the render of its scene
.\build.ps1 -Check war_diary          # scenes: army_readiness, states, national_figures, history, top_bar, war_diary, officers, government, wars
.\build.ps1 -Check war_diary -InGame  # ... then the unattended game check (tools\Invoke-GameCheck.ps1), with the user's permission
```

---

## Automated Testing

Unit tests are written with [Pester](https://pester.dev) and located in `tests/`. Execute tests using:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\Run-Tests.ps1
```

The render and layout tests need Python 3 with Pillow (`tests/requirements.txt`) and an installed game; without them they are skipped.

---

## Author & License

- **Author**: TheCreepero
