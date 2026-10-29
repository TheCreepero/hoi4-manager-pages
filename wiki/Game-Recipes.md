# Game Recipes

> (from the 1440p mod) Copied at the split of 2026-10-21 from the HOI4 1440p UI Mod, whose reworked vanilla screens it still describes beside the pages; a later pass trims it to the pages.

How the harness brings a screen up in the game without a human, which screens it already knows, and how to teach it a new one. The engine facts behind this page are rows H1 to H20 of [Engine Facts](Engine-Facts.md).

## What a recipe is

A recipe is a short list of steps that starts from the **clean state** and ends with one screen open. `tools/Invoke-GameCheck.ps1` runs it, captures the screen and cuts out the panel. Recipes live in two places:

- **A scene's `setup`** in `tools/scenes/<screen>.json`: the steps for that one screen.
- **A shared move** in `tools/moves.json`: steps that several screens need, used with `{ "move": "<name>" }`.

The clean state is a paused 1936 game as Germany with all 30 divisions in Army 1, nothing selected, no window open, the land map mode and the Home camera. A new game is put into it once: the harness runs the move `prepare_game`, which makes that army. `Reset-HoiState` restores the rest before every scene: Escape until the game menu shows, Escape once more, F1, Home. Nothing is ever unpaused or saved.

## Step kinds

Use the first kind in this list that can do the job. The order is how long a step keeps working.

| Step | Example | Keeps working until |
|---|---|---|
| A hotkey | `{ "key": "u" }`, `{ "key": "shift+q" }`, `{ "key": "escape" }` | the game changes the key |
| A click on a widget by name | `{ "clickWidget": "army_division_view/unitinfo_button" }` | the widget is renamed, which the mod never does |
| A drag between two widgets by name | `{ "dragWidget": ["ship_entry_compact/ship_button#4", "taskforce_view_entry/unit_name#1"] }` | either widget is renamed |
| A shared move | `{ "move": "select_army_1" }` | its own steps break |
| A raw position | `{ "click": [1592, 828] }`, `{ "rightClick": [x, y] }`, `{ "drag": [x1, y1, x2, y2] }` | anything at that spot moves |
| A console command | `{ "console": "tag GER" }` | the command changes |

Every step takes an optional `"wait": <seconds>` and a `"_note"`.

**Clicks by name.** `clickWidget` asks the renderer where the widget sits (`render_gui.py --scene <scene> --locate <spec>`), so the step follows every layout change and works for the vanilla and the modded window alike. The spec is `window/widget`, where the window is the top-level window that defines the widget: for a button of a list row that is the row window. `#n` picks the n-th drawn instance, counted from 0. The layout comes from the current scene; `"scene": "<other>"` borrows another scene's, and `"offset": [dx, dy]` and `"button": "right"` adjust the click.

**A widget that shows only in one state** is found with `"state": "<capture or state of the scene>"` on the step: the Back button of the symbol picker is laid out only in the scene's `icon-picker` state.

**A widget the code moves needs an offset.** The game centres a ship's icon in its row, 12 px above where the file puts it ([Engine Facts](Engine-Facts.md) S36), so the step that opens the ship details is `{ "clickWidget": "ship_entry_detailed/ship_button", "scene": "fleet", "offset": [0, -12] }`.

**Raw positions** are for the map and for vanilla panels the mod has not reworked yet. Map positions are measured in the Home view. A raw position inside a panel breaks the day that panel is reworked; the move's `_note` says so, and the fix is a `clickWidget` step.

## Proof that a recipe worked

A scene's `expect` list names widgets that must be visible once the screen is up:

```json
"expect": ["army_division_list_view/btn_delete", "army_badge_view/close_button"]
```

After the capture the harness looks for each one near where the layout puts it (`render_gui.py --verify`) and prints `found` with the offset, or an error. A recipe that silently opened nothing therefore fails loudly, and a game update that moves a button shows up as exactly the scenes it broke. Pick widgets with a fixed look: buttons and icons with their own sprite, not backgrounds, text or anything the code recolours.

## Screens the harness knows

Surveyed on game 1.19.3 on 2026-10-08, each recipe run unattended with the mod and without it. "Verified" means the scene has an `expect` list that passed; the others were checked by eye on their capture and get their `expect` list when their phase measures where the window sits.

| Phase | Scene | Recipe | Notes |
|---|---|---|---|
| A1 | `air_selection` | `select_airbase` | verified, mod and vanilla |
| A1 | `air_group` | `select_airbase`, then click `air_selection_view/btn_create_air_group` | the group badge moves the list down; runs last |
| A2 | `army_selection` | `select_army_1` | verified, mod and vanilla; extra capture of the template dropdown |
| A3 | `division_details` | `select_army_1`, sort by name, then click `army_division_view/unitinfo_button` | verified, mod and vanilla; extra captures: History and Template tabs, both dropdowns, a tank and a motorised division (each a further window) |
| A3 | `ship_details` | `open_ship_details` | verified, mod and vanilla; extra captures: History tab, a British carrier (`tag ENG`; the scene's `teardown` switches back) |
| A3 | `air_wing_details` | `select_airbase`, then click `airwing_selection_item/unitinfo_button` | verified, mod and vanilla |
| A4 | `fleet` | `select_fleet` (since A6 a click on the first fleet row of the navy overview by name) | verified, mod and vanilla; extra captures: a selected ship, the task force list (Back), home base picker, composition editor, the British Home Fleet and its task force list (`tag ENG`; the scene's `teardown` switches back) |
| A4 | `fleet_composition` | `select_fleet`, Back, then click `taskforce_view_entry/btn_composition_editor` | verified, mod and vanilla; the ship class picker opens with it |
| A4 | `fleet_home_base` | `open_home_base_picker` | verified, mod and vanilla |
| A4 | `fleet_transfer` | `select_fleet`, Back, then drag the first ship counter of the first task force onto the second task force | verified, mod and vanilla |
| A5 | `recruit_deploy` | `open_recruit_deploy` (key `u`), Train on the first three templates and Add Unit three times on the first card | verified, mod and vanilla; extra captures: the name list of a line, the symbol picker, Italy's templates with the decommissioned ones (`tag ITA`); the scene's `teardown` switches back and cancels the training |
| A6 | `army_overview` | `open_army_overview` (key `o`) | verified, mod and vanilla; extra captures: navy (`p`) and air (`l`) tabs, Sunk Ships, Equipment Details (`shift+i` with the mod), a row's details button |
| A7 | `air_wing_reorg` | `planes_into_reserve`, then click `airbase_selection_item/new_btn` | verified, mod and vanilla; disbands the Brandenburg wings, runs last |
| A8 | `theatre_bar` | `select_army_1` | verified, mod and vanilla; the theatre boxes at the top right; extra captures: navy (`select_fleet`) and air (`select_airbase`). With RBM's GFX Overhaul the boxes sit 24 px higher and the expect list misses them |
| B1 | `division_designer` | `open_division_designer` | verified, mod and vanilla; screen out of scope |
| B2 | `tank_designer` | `open_tank_designer` | verified, mod and vanilla; screen out of scope |
| B3 | `plane_designer` | `open_plane_designer` | verified, mod and vanilla; screen out of scope |
| B4 | `ship_designer` | `open_ship_designer` | verified, mod and vanilla; screen out of scope |
| D2 | `army_readiness` | `open_recruit_deploy`: the page is docked to the tab and open by default | verified; mod only (a scripted GUI has no vanilla layout: the scene says `modOnly`) |
| D3 | `states` | `open_construction`, then Shift+M; the `teardown` hides the page again | verified; mod only |
| D4 | `national_figures` | `open_politics`, then Shift+M; a capture `all` clicks `mod1440_figures/nf_view_all`; the `teardown` gives the default view back and folds the page | verified before the redesign of 2026-10-16; the docked page not yet; mod only |
| D5 | `history` | as `national_figures`, then a click on the tile `mod1440_figures/nf_t4` (Military factories) | verified before the redesign of 2026-10-16; the docked page not yet; mod only |
| E1 | `war_diary` | Shift+J opens the Records window, then a click on its first page button; the `teardown` closes it | verified; mod only |
| E2 | `officers` | Shift+J, then a click on `mod1440_records_wd/wd_tab_1` | verified; mod only |
| E3 | `government` | Shift+J, then a click on `mod1440_records_wd/wd_tab_2` | verified; mod only |
| E4 | `wars` | Shift+J, then a click on `mod1440_records_wd/wd_tab_3` | verified; mod only |
| C | `leader_selection`, `advisor_selection`, `focus_tree`, `tech_tree` | see `tools/moves.json` | |
| C | `politics`, `decisions`, `research`, `international_market`, `trade`, `construction`, `production`, `logistics`, `officer_corps`, `intelligence`, `faction` | one top bar hotkey each | |

Not reached, and why:

- **Ship refit** (`ship_refit_equipment_view`): needs a ship with a newer design to refit to.
- **The template list of the composition editor**: a new game has no saved template, and Save did nothing after one click.
- **Several fleets selected at once**: needs a shift-click, which the harness does not have ([Engine Facts](Engine-Facts.md) H30).
- **Combat, low supply, attrition, exile markers, commander traits**: not in a 1936 start. Out of scope for now.
- **Military industrial organisations, special projects, raids, front end screens**: not surveyed.

`tools\Invoke-GameCheck.ps1 -All -Vanilla -SaveReference` re-runs every recipe and stores the capture of each scene under `reference/vanilla/` (the whole frame as JPEG, the panel region as lossless PNG; index in `reference/README.md`). Run it after a game update: the scenes it reports are the recipes to redo, and `git diff --stat reference` shows which screens changed. Without `-SaveReference` a run only writes to `scratch/checks`.

## Teaching a new recipe

1. **Read the files first.** `tools\Show-GuiOutline.ps1 <file.gui> <window> -All` lists a window's buttons with their hotkeys. A screen with a `shortcut` in `topbar.gui` needs one `key` step and nothing else.
2. **Start the game and keep it open.**

   ```powershell
   .\tools\Invoke-GameSteps.ps1 -Start
   ```

3. **Try steps one at a time and look at the capture.** Each call runs a few steps and saves a capture to `scratch\checks`; `-Reset` starts from the clean state.

   ```powershell
   .\tools\Invoke-GameSteps.ps1 -Reset -Steps '[{"key":"y","wait":1.2}]'
   ```

   Read `scratch\checks\view.png`, the capture at half size.
4. **Read a position off a grid capture, never off the overview.** `-Region x,y,w,h` saves that part enlarged with a grid labelled in screen coordinates.

   ```powershell
   .\tools\Invoke-GameSteps.ps1 -Region 0,60,560,420
   ```

5. **Prefer a name.** If the button is in a window a scene already lays out, use `clickWidget` with `-Scene <scene>` and check on the capture that it hit.
6. **Write the steps down.** Into the scene's `setup`, or into `tools/moves.json` when another scene will need them. Add an `expect` list.
7. **Prove it from a cold start.** `.\tools\Invoke-GameCheck.ps1 <scene>` must report every expected widget as found. `.\tools\Invoke-GameSteps.ps1 -Stop` closes the game left open in step 2.

Run the steps in PowerShell with `&` or `-File`, and keep the JSON in single quotes.

## Measuring where a window sits

A scene window without `at` is laid out where the file alone puts it. That is exact for centred windows (the four designers and the air wing reorganisation verify without any `at`) and wrong for every window the code docks or stacks. To measure one, name a few widgets with a fixed look and run the check against a capture:

```powershell
python -I tools\render_gui.py --scene <scene> --verify <capture.png> --expect <window>/<widget> ...
```

Each `VERIFY` line gives the offset between the layout and the game, up to 20 px each way. Add the offset to `at` and run it again until it reads `0 0`. For a window that is further off, read its top-left corner from a grid capture first. `--vanilla` lays the scene out without the mod, for a vanilla capture. A window the code places next to others sits elsewhere in vanilla, because its neighbours have other sizes: give it an `atVanilla` beside `at` (the wing list frame is at 2,168 with the mod and at 2,197 without).

## Letting time run

A check stays paused unless time is what it checks. The user allows up to ten days inside January 1936: copy `autosave.hoi4` first and compare its hash afterwards, never save, and never let a month pass ([Scripted GUIs](Scripted-GUIs.md), "Working on a page").

- **Speed** is set with the plus button of the clock at (2428, 20): three clicks from speed 1 to speed 4. The number keys do not set it.
- **Space** runs and pauses. Speed 4 is nine to ten game hours a second on this machine: five seconds are about two days.
- **Read the clock after every burst**: `-Region 2050,0,510,120` gives it enlarged.
- The daily round of the scripted pages runs at midnight, so something that happened on the 3rd is in the Records on the 4th.

```powershell
.\tools\Invoke-GameSteps.ps1 -Reset -Name t1 -Region 2050,0,510,120 -Steps '[{"click":[2428,20],"wait":0.4},{"click":[2428,20],"wait":0.4},{"click":[2428,20],"wait":0.4},{"key":"space","wait":5.0},{"key":"space","wait":1.0}]'
```

## With another mod loaded

`Invoke-GameSteps.ps1 -Start` and `Invoke-GameCheck.ps1` load this mod alone. The user plays with dozens of mods, and what a mod adds can behave unlike the game's own content: generals a mod adds by event were missing from the Officers list in every check made with this mod alone ([Engine Facts](Engine-Facts.md) X66). A page that reads characters, leaders, states or equipment is therefore also checked with one such mod beside this one.

```powershell
.\build.ps1 -DevLink                      # this way of starting does not check where the launcher file points
. .\tools\GameHarness.ps1
Set-HoiPlayset -Mods @('mod/ugc_2978117558.mod', 'mod/hoi4-1440p-ui-mod.mod') | Out-Null
Start-Hoi4 | Out-Null
Start-HoiNewGame
```

- The launcher's files are in `Documents\Paradox Interactive\Hearts of Iron IV\mod`; the `name` line of each says which mod it is. This mod goes last.
- From there on `Invoke-GameSteps.ps1` works as always, and `-Stop` puts the user's playset back.
- In one command (phase E7): `.\tools\Invoke-GameCheck.ps1 <scene> -Mods mod/<file>.mod -AfterLoad <steps> -TimeoutSec 900` loads the named launcher files before this mod (the DevLink check still applies), closes what they open at the start, runs the scene and puts the playset back. `tools/playsets/rt56.json` closes what Road to 56 (`mod/rt56-vnr-utt-standalone-v16.mod`) is expected to open, taken from the user's playset of 2026-10-13; a click whose window is missing lands on the map before the reset.
- Another country: the console command `tag USA`. The scripted pages follow, and their first daily round for that country runs at the next midnight.
- An event of the other mod: `event <id>` in the console, then a click on its option.

## With the user's playset

One mod beside this one shows what that mod does. The user plays with about 56, and some things only show with all of them: another map, pictures of another size, a second button on the same spot ([Compatibility](Compatibility.md)).

```powershell
python -I tools/check_playset.py          # first, from the files: seconds, no game
.\build.ps1 -DevLink                      # after a copy of the launcher's file of this mod, as for every start
.\tools\Invoke-GameSteps.ps1 -Start -Playset -TimeoutSec 900 -AfterLoad tools\playsets\reordered-pack-usa.json
.\tools\Invoke-GameCheck.ps1 army_selection division_details fleet -NoRestart
.\tools\Invoke-GameSteps.ps1 -Stop       # puts the playset back; then copy the launcher's file back
```

- **`-Playset`** leaves the launcher's list of mods as it is and puts this mod last. The launcher's file of this mod must point at the repository (`build.ps1 -DevLink`), or the start stops.
- **`-AfterLoad`** takes steps, as JSON or as a file of them, that close what the playset opens when a game starts. They run once the map is up and before the clean state is made. `tools/playsets/reordered-pack-usa.json` has the twelve clicks for the user's playset of 2026-10-13. For another playset: start without `-AfterLoad`, look at the capture the failed start leaves, and close the windows one by one with `-Steps`, a capture after each.
- **The menu** is the plain game's with Road to 56, except for the scenario screen, where the harness's click on the first scenario lands beside the picture and does no harm.
- **The recipes work as Germany** in this playset too (30 divisions, a fleet, an airbase). `Invoke-GameCheck.ps1 ... -NoRestart` runs them in the open game; its comparison of `error.log` is with the plain game, so only its first line counts: whether a line names the mod or a sprite its windows name.
- **The country the user plays:** `tag USA` in the console, with nothing selected.
- **`error.log`** has about 9000 lines from such a playset. Read the whole of it once, not only the lines with the mod's name: "Could not find sprite type" and "invalid scope for var" name no file.


## Effects for a check

`python -I tools/check_effects.py` writes `common/scripted_effects/mod1440_check.txt`, and a game left open reads it within seconds. `--restore` removes it; the test suite fails while it is there. Each effect is run from the console with nothing selected (`{"console":"effect mod1440_chk_war"}`) and changes the game of the check, which is never saved. What an effect finds out goes to `game.log` as a line that starts with "MOD1440".

| For | Effects |
|---|---|
| events while paused, as Germany | `war`, `war2`, `peace`, `annex`, `puppet`, `state`, `state2`, `capital`, `vp1` to `vp3` after `sync`, `officers`, `gen`, `retire`, `hire` |
| officers without a number (X66), without another mod | `by_effect` gives two characters a command by effect |
| the rounds of the mod | `daily`, `refs` (the search for places), `time` (400 victory point comparisons) |
| a game as something else left it | `old` (the logs of an earlier build), `shift` (the game's list of characters changed) |
| the History page | `months`, `months_old`, `months_few`: made-up months |
| numbers | `leaders`, `sizes`, `log` |


## Pitfalls

- **State leaks between recipes.** Opening the navy overview switches the map mode, and the bottom bar then lists fleets where the army portraits were. The reset presses F1 for that reason; a recipe that needs another map mode must set it itself.
- **The Home view is not the view a new game opens with.** Positions measured before the first reset are wrong afterwards. The harness resets right after loading, so measure only after a reset.
- **The army of the clean state is sometimes not made.** In one of six starts on 2026-10-14 `prepare_game` left the 30 divisions unassigned ([Engine Facts](Engine-Facts.md) H37): the army overview then says "Unassigned", no theatre box shows and `select_army_1` clicks the map. Run the check again.
- **An expect widget needs a fixed look.** The details button of a division row in the army overview is mostly transparent and was not found; the sort buttons were.
- **A selection can move the camera.** Selecting an army by its portrait pans to it. Do map clicks before such a step, or reset in between.
- **A recipe can change what the next one sees.** `Invoke-GameCheck.ps1` runs all scenes in one game, and the reset closes windows but does not undo what a recipe created. Creating the army a second time failed for that reason, so it now happens once, in `prepare_game`. A scene that leaves something behind which other screens show gets `"changesState": true` and runs last; `air_group` is the one so far.
- **Earlier clicks shift later positions.** An air group badge pushes the wing list down by its height. A `clickWidget` step uses the layout of the scene it names, so name a scene that describes the state the click happens in.
- **A disabled button swallows the click.** The "Add new Air Wing" button did nothing until there were planes in reserve. When a click has no effect, hover the button and capture with `Save-HoiGridCapture -KeepCursor`: the tooltip says why.
- **A details window opens somewhere else each time.** The game counts the division details windows opened in a game and places each one by that count ([Engine Facts](Engine-Facts.md) S17). A scene's `at` describes the first; a step that clicks into a later one needs an `offset`.
- **Another window can cover the game.** In debug mode the game itself opens `error.log` in Notepad. The harness minimises it after loading and refuses to click or capture where the game is not on top.
- **The game may be loading a copy of the mod.** After `build.ps1 -Deploy` the launcher file points at the copy under Documents. The harness stops with a message; run `build.ps1 -DevLink`.
- **A wrong `at` makes a named click miss silently.** The vanilla wing list was 15 px from where the scene put it, which is half a button. Measure `at` (and `atVanilla`) before relying on `clickWidget` in a window the code places.
- **The cursor leaves a tooltip.** It is parked over the map before each capture; keep the crop region clear of (1500, 1000).
- **A click only counts while the game is in front.** The harness checks before every key and click and stops with an error otherwise. Moving the mouse during a run still derails it.
- **Positions are for 2560x1440 at 100 % UI scale.**
- **A scripted page remembers whether it is open**, per country, in a variable. A recipe that opens one with Shift+M closes it again in its `teardown`, or the next run of the same recipe closes it instead of opening it.
- **A named click on a page that is not up lands on the map** and selects whatever is there. After a reset the States page is as it was left, National Figures and History are closed. Look at the capture before the next step when a page was opened by a toggle.
- **The scenes of the scripted pages are written by `tools/build_managers.py`.** Change them there; the test suite fails when a scene file on disk differs.
- **A window script shows in some states only** carries `drawIn` in its scene: the names of the captures and states it is drawn in, `""` for the scene's own. A state may also `place` widgets per window, where script's `x` puts them (phase D7: the top bar's panel, its fixed twin and the chips of another choice).
