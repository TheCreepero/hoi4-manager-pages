# Phase D2: Army Readiness, with the probe and the foundation of the scripted GUIs

The first scripted GUI of the mod, docked to Recruit & Deploy. The phase opened with a probe that settled the open engine questions and paid the one-time costs of every later page. D6 (the armies table) was built into the same page. Status: done on 2026-10-12, awaiting the tester's judgement. The page itself is described in [Scripted GUIs](../Scripted-GUIs.md).

## Scope

- Tab: Recruit & Deploy, the two panels of [A5](A5-recruit-deploy.md). The page is a container of the mod's own attached to the tab (`parent_window_token = deployment_tab`).
- What the vanilla screen does not show: how much manpower and equipment the country has left to recruit with, and how well the army in the field is equipped. The numbers sit in a top bar tooltip, on the logistics tab and in the army view.
- Out of scope: anything per template or per division in training. Script has no list of either (D0).

## Decisions

- 2026-10-12, user: all four managers (army readiness, states, armies, national figures) and graphs over time; pages docked to their tab; values of the own country only; a top bar strip later.
- 2026-10-12, user: "I am going away from my computer now so you can freely proceed with the implementation and testing." Taken as leave to start the game while the user was away; every launch is in the table below.
- A page changes nothing in the game: its buttons hide it, count again, sort or move the camera. A test holds the list of commands the mod's script may use.
- 975 px wide: the page stops short of the theatre box under the clock. The first build was 1216 wide and covered it.
- Counted values (two division counts, the equipment bars, the list of generals) carry the date of the count and a Count again button. Values of the game are live.
- One generator (`tools/build_managers.py`) writes every file of every page. Rows such as the sixteen kinds of equipment are tables in that file.
- No check runs time (the user's autosave is monthly). The daily and monthly hooks are asked of the tester.

## The probe

A throwaway build (`scratch/apply_probe2.py`, removed again) with one scripted GUI per question. What it showed is rows X6 to X25 of [Engine Facts](../Engine-Facts.md). In short:

| Question | Answer |
|---|---|
| A page docked beside its tab | Only if the tab's window has `clipping = no`; then it is drawn and clickable there |
| A window of its own, a hotkey, Escape | All work; the window takes the clicks inside its rectangle and takes Escape before the tab does |
| A list from an array: numbers, states, generals | Works, with the row's own values in each row; sideways too; the vanilla scrollbar scrolls it |
| A click in a row | Runs with the row's state as THIS and the country as ROOT; `ROOT = { goto_state = PREV }` moves the camera |
| Greyed buttons, right click, tooltips | Work |
| Hiding a group of widgets | Not through a nested container; a group is a scripted GUI of its own |
| `dirty` | Works, also for the first drawing |
| A progress bar filled by script | Works: the way to bars and to the columns of a graph |
| Sorting, a loop over every division | A few milliseconds for 152 states and 138 divisions |
| Values against the game's numbers | See X19 to X21 |
| Reload without a restart | Script, texts and layout of a scripted GUI are read again within seconds |

## What was built

- `interface/zz_1440p_recruit_deploy.gui`: `clipping = no` on `countrydeploymentview`, the one change to a vanilla window.
- `interface/mod1440_army_readiness.gui`, `common/scripted_guis/mod1440_army_readiness.txt`: the page, its handle, the row of the armies list.
- `common/scripted_effects/mod1440_effects.txt` (`mod1440_ar_count`), `common/on_actions/mod1440_on_actions.txt` (start of a game, each day), `common/synchronized_dynamic_tokens/mod1440_tokens.txt`, `localisation/<language>/mod1440_l_<language>.yml`.
- `interface/1440p_ui.gfx`: `GFX_1440p_SG_bar`, a bar from the vanilla organisation bar; `GFX_1440p_SG_column` and five `GFX_1440p_SG_head_*` for the later pages.
- Tools: `tools/build_managers.py`; `tools/render_gui.py` stacks the rows of a scripted list; `tools/GameHarness.ps1` counts `mod1440_` lines of `error.log` as the mod's.
- Tests: `tests/ScriptedGuis.Tests.ps1` (new); the checksum test of `tests/GuiInvariants.Tests.ps1` now allows the four script folders and nothing else; the text test of `tests/ScreenInvariants.Tests.ps1` measures the mod's own captions, and the recipe test skips the vanilla layout for a page that exists in the mod only.

## Game checks

Build: `8d5502c` plus uncommitted work, all on 2026-10-12.

| # | Build | Checked | Result | Screenshot | Taught |
|---|---|---|---|---|---|
| 1 | probe, first form | docked panels at x 1256, top bar button, window, `dirty` | the docked panels did not show; the rest worked | `scratch/checks/p_*-20261012-1614*` to `-1616*` | X6 to X9, X16 |
| 2 | probe, second form, then live changes | docking with `clipping = no`, lists, buttons, tooltips, camera, sort and loop as the Soviet Union, a general assigned, reload | all as in the table above | `scratch/checks/q_*-20261012-162*`, `-163*` | X6, X10 to X25 |
| 3 | first build of the page, then live changes | values against top bar and logistics; a math expression as bar fill | page up at 1216 px; the expression broke the file | `scratch/checks/ar_1-*`, `ar_3-*` | X26 |
| 4 | page at 975 px, new bar sprite | start-up count, training two divisions, hide and show, tooltips, the Soviet Union and Ethiopia | all work; shortages red, bars at their share | `scratch/checks/ar_4-*` to `ar_11-*` | X28, X29 |
| 5 | with the states table and the armies list | the armies list after assigning a general | Rundstedt: 30 divisions, 315 battalions, 100%, 26 / 3 / 1 | `scratch/checks/al_2-*` | X21 in use |
| 6 | with National Figures and History | see [D4](D4-national-figures.md) | - | - | X27 |
| 7 | final, cold start through `tools/Invoke-GameCheck.ps1` | Recruit & Deploy and the four pages, `error.log` | every expected widget found where the layout puts it; no line names the mod | `reference/mod/army_readiness.jpg`, `scratch/checks/*-20261012-173*`, `-174*` | the renderer lays a scripted page out to the pixel |

Not seen in game:

- A day or a month passing: the daily count and the monthly recording (X28).
- Garrison need above 0, a division below 75% strength or 50% organisation, a division fighting, planning above 0%.
- Shift, control and alt clicks.

## Rework of the look (2026-10-12)

The user, after the Records had been polished: "run a similar UI polishing pass on every other feature that has been implemented so far ... you may also add new visuals and reorganize elements where it is possible and make sense", to completion without their input.

- **What changed.** The two cards of label and value rows on the left are gone: their eleven figures are tiles in two rows across the top, with Count again and the date of the count in the twelfth place. The equipment table has the whole width for it, under a bar of column heads and with every second row on a darker band; it gained a column "Short" (needed less in the field, red) and the percentage beside a longer bar, which is orange below 75%. A kind the country neither has nor needs has a grey name. The armies table has the same heads and bands, the commander's rank (Marshal, General), his name in the highlight yellow and the percentage beside his bar.
- **Decided:** "Below 75% strength" and "Below 50% organisation" became "Under strength" and "Low organisation" to fit a tile; the thresholds are in the tooltips. A count above zero is yellow. The armies list shows ten rows before it scrolls (it showed seventeen): the equipment table took the height.
- **What it rests on.** Tiles, heads, bands, bars, colour codes and text icons as on the Records pages, which a game check saw (Engine Facts X56). New: row X57.
- **Not checked in game on 2026-10-12:** the launch was refused by the permission system of the assistant's tool that session ("Don't start the game without asking my permission first" stands; the user was away). The user installed the build on 2026-10-13 and played with it: "Overall I'm very happy with the results"; the error log of that session names the mod nowhere.
- **Checked in game on 2026-10-13**, cold start through `tools/Invoke-GameCheck.ps1` after the user allowed a launch: the page as the renderer drew it (`reference/mod/army_readiness-panel.png`). Eleven tiles (free manpower 1332K, as History's 1332.6; 269K, 19K and 37K in the three branches; 30 divisions, 315 battalions); five kinds of equipment with needed equal to in the field and a full green bar at 100%, the Short column empty; eleven kinds Germany neither has nor needs in grey; "No army has a commander yet". No line of `error.log` names the mod.
- **Checked as the Soviet Union the same day** (`tag SOV`, then Count again; `scratch/checks/b_ar1-*`, `b_ar2-*`): 138 divisions, 1231 battalions; five kinds short with the number in the field in red; the bar orange at 70% (support equipment) and 69% (light tanks), green at 76%, 78% and 91%.
  - **A fault:** Short read 1 less than needed less in the field for three kinds (27032 for 114750 and 87717). A text cuts the fraction of a number off, and equipment in the field has one (Engine Facts X65). The gap is now rounded up in script (`round_temp_variable`, a command new to the list of `tests/ScriptedGuis.Tests.ps1`); counted again in the open game it read 27033, 170, 218, 147 and 1000.
- **Changed on 2026-10-13 after the user's test with a mod that adds generals:** the armies list takes its commanders from the game's own loop (`every_army_leader`) and keeps each through `mod1440_of_me`, because the game's array `army_leaders` holds nothing for a general whose command came by an effect ([E2 notes](E2-officer-records.md), "Officers other mods add"; Engine Facts X66). The page was seen again as the USA with that mod loaded: counted on 4 January, no army with a commander.
- **Left unseen:** the rank and the band of a commander's row in the new look (the armies list was seen with a general before the rework); a commander without a number in that list.

## Close

- [x] The rework of 2026-10-12 seen in game, and `reference/mod/army_readiness*` stored again (2026-10-13)
- [x] Roadmap status and link
- [x] README and Workshop description: the pages, and that Ironman and achievements no longer work
- [x] `version` in `descriptor.mod` (1.5)
- [x] Engine Facts rows X6 to X31
- [x] Scene files (`tools/scenes/army_readiness.json`, written by the tool)
- [x] Finished page stored under `reference/mod/`
- [ ] The tester's judgement: width, what the page shows, the look of the cards
- [ ] The tester's look after a few days of game time

## Redesign build (2026-10-16)

Status: built and checked by render and tests; not seen in game. The design and the user's four decisions are on the review page of the redesign pass (proposal d2-readiness, "refine"); every decision was the recommended option.

### What was built

- **Two forms.** The page is now two scripted GUIs on `deployment_tab`, one under the other: `mod1440_army_readiness` (the head, 975x244: title strip and figures) and `mod1440_army_readiness_body` (975x966: equipment and armies), plus the handle as before. A group of widgets is hidden only as a scripted GUI of its own [SGUI-013]. Summary folds the page to its head, Full brings the body back (and counts). Shift+M stays hide and show on the close button and the handle; a hidden page comes back in the form it was left in.
- **Title strip.** "Counted <date>" right-aligned, Count again and Summary/Full beside it, the close button. The hint text is gone: the game writes the shortcut into the tooltip [SGUI-008].
- **Figures.** Two cards of 467x174, Manpower and Army, three tiles of 145x64 to a row. New: Fuel, `fuel_k` of `max_fuel_k` with a 117 px bar the count fills (orange below 75%).
- **Equipment.** A list (`dynamic_lists` over `mod1440_ar_fill`, the bar's fill as `v`) of the kinds in use only: stock or need above 0. The count copies stock, in the field, needed, short, share, the kind's text key and its picture's sprite as text keys into arrays and sorts them, worst equipped first, then the kinds in stock only [SGUI-009, SGUI-023, SCR-015]. Row: the game's archetype picture (`image` from a token [SGUI-026]), the game's name of the kind, the numbers, Short red when the stock cannot fill the gap and orange when it can, the bar and its percentage. Caption "N of M kinds in use".
- **The kinds come from a table.** `tools/make_game_tables.py` writes `tools/equipment_kinds_table.py` (the game: 44 kinds, every archetype a land sub-unit needs, duplicated archetypes such as tank destroyers included) and, with `--mods`, `tools/equipment_kinds_mods_table.py` (the user's playset: 55 kinds for 1143 states). Script counts the states once per country and counts the kinds of the table with that number, the game's otherwise [SCR-038]. Each row of a table carries the sprite of the kind's picture (`picture` of the archetype, as the loaded game declares it) and that picture's size.
- **Pictures at several scales.** The game's pictures are 47x32 to 131x52 and an icon has one scale, so a row has seven icons, one per scale (1.0 to 0.4), and script shows the one at which the kind's picture fits its box (84x30 in an equipment row, 56x24 for the worst kind).
- **Armies.** Ten rows of 50 px: portrait (`mod1440_p`, looked up once per table of portraits for a player's country, as the Officers page does), name, rank and skill; HQ as a button with the state of his deployed headquarters (`state_deployed` [SCR-069], a click moves the camera there with `goto_state` [SCR-001]) or "not deployed"; divisions; Inf, Arm, Mot and Mech (`num_mechanized`, new); fighting with "n att, n def" (`num_units_offensive_combats`, `num_units_defensive_combats`, new); planning as a percentage over a 68 px bar (counted); the worst equipped kind as its picture, its share and a 98 px bar. Battalions left the row.
- **Left edge** `AR_X = 1256`, unchanged.
- **Files:** `tools/build_managers.py` (the Army Readiness section, its scene, and the samples a scene may give per row of a list in `scene_files`), `tools/make_game_tables.py` (the two tables), `tools/check_playset.py` (the equipment check compares the playset with the table the page counts for it), `interface/1440p_ui.gfx` (the block `d2-readiness`: a 145x64 plate, two bands, a 136 px head for the HQ button, seven bars), and the generated files.

### Do the tank rows read 0 with Road to 56?

No, read from the files on 2026-10-16. Every tank battalion of the user's playset needs a chassis of No Step Back: `light_armor` of the RT56 standalone needs `light_tank_chassis`, and the medium, heavy and modern battalions come from the game's files and Better Mechanics: Extended Units Light. The standalone still defines those chassis as archetypes (`zz_FLTE_armor_equipment.txt`). The 21 `*_tank_equipment` archetypes it adds as well (`zz_FLTE_z_tank_chassis.txt`) are needed by no sub-unit of the playset, which is why `tools/check_playset.py` listed them as not named. What the old page missed were the kinds it never knew: the duplicated chassis (tank destroyers, self-propelled guns and anti-air, flame and amphibious tanks), super-heavy, para and wheeled tanks, motorcycles, the armoured and heavy mechanised kinds of RT56 and the six kinds of Better Mechanics: Extended Projects. The playset table holds all of them.

### Deviations

- The form is kept in two variables, not one: `mod1440_ar_folded` (hidden, as before, so a save keeps its state) and `mod1440_ar_small` (Summary). A hidden page comes back in the form it was left in.
- Pictures stand at the left of their box and in the middle of its height for their scale; an icon cannot be centred per kind.
- The worst kind is the lowest share; when every kind of an army is at 100% the first kind of the table it needs is shown.

### Not seen in game

- The two scripted GUIs one under the other: no seam beyond the two borders that meet at y 244; the body taking clicks while the head is in its short form.
- `image` with an array element at the row's index (`[?mod1440_ar_pic^i.GetTokenKey]`) in a list without a scope; the names from tokens in the same row.
- `frame = v` for the equipment bars in a list of numbers.
- `state_deployed` in a general's scope, `[?mod1440_al_hq.GetName]`, and the HQ button's camera move.
- Portraits in the armies rows, also for a commander without a number.
- Fuel against the top bar; the attack and defence counts and the mechanised count above 0.
- `num_equipment@` and its siblings with a kind the loaded game lacks, in the playset's table, while the game's own table is counted: no line in `error.log` expected, as that branch is not taken.

### Game check

`tools/Invoke-GameCheck.ps1 army_readiness`, and once with the playset (`tools/Invoke-GameSteps.ps1 -Start -Playset`). The tester's checklist is the scene's (`tools/scenes/army_readiness.json`):

1. Shift+M hides the page and brings it back in the form it was left in; the handle beside the template panel does the same.
2. Summary folds the page to its title strip and figures, with no seam left where the body was; Full brings the body back under them.
3. The equipment card lists only the kinds you have or need, the worst equipped first, each with the game's picture of the kind at a size that fits its row.
4. Short is red where the stock cannot fill the gap and orange where it can; In the field is red where it is short.
5. Fuel reads the top bar's fuel (297K of 371K for Germany in 1936) and its bar is that share.
6. Assign a general to an army, press Count again: the general is listed under Armies with his portrait, rank and skill.
7. Deploy his HQ: the HQ button names its state and a click moves the camera there; without one it reads not deployed.
8. Inf, Arm, Mot and Mech against the army badge; Worst kind shows a picture and its share.
9. Train a division: In training rises at once; In stock falls at the next count.
10. `error.log` names no mod1440 file and has no "Could not find sprite type" line for an archetype picture.

### Fix round 1

- Mechanized looked out of place (user's game, `army_readiness.png`): `KIND_SPRITE` gave it the technology picture `GFX_mechanised_infantry_medium`, a coloured halftrack with a level mark, 144x68 in the playset and drawn at 0.4 among the beige silhouettes. It now has `GFX_1440p_archetype_mechanized_equipment_medium` (63x28, `gfx/interface/1440p_ui/ar_mechanized_equipment.dds`): the same halftrack without its mark, in colours taken from three archetype pictures by rank of brightness (`archetype_picture` in `tools/stretch_background.py`). `make_game_tables.py` reads the size of a sprite of the mod from the repository; both kinds tables were made again (one row each changed; `write_mod_kinds` writes the playset's table alone). Re-test: the Mechanized row and a worst kind of Mechanized show a beige halftrack at full size; a new sprite and token need a fresh start.
- Armies: wrong portraits in the user's save: the cached portrait was a stale text key (E1, Fix round 1). The row's lookup follows the stamp of `global.mod1440_tk_ep` (`build_records.portrait_stale`), and a count first checks the record's kept keys (`mod1440_tk_check`), since the count runs before the Records' daily round. Re-test: the user's save, Count again: each commander with his own portrait.

## Round 2: redesign and feature upgrade (2026-10-17)

Opened on 2026-10-17 with `/phase D2`. The user asked for "improvements to the UI, additional information to be displayed if possible, verify if it's possible to list the name of the army instead of just the commander, UX consideration." Run under the orchestrated workflow of [Workflow](../Workflow.md).

### Scope

- The page as the redesign of 2026-10-16 left it (two forms, twelve tiles, equipment list from the kinds table, armies rows), generated by `tools/build_managers.py`.
- Four asks: a better page; more values script can reach, each checked against the game's number; a verified answer on army names; the use of the page (clicks, Count again, Summary, sorting, tooltips).
- Out of scope: the Recruit & Deploy panels of A5, the top bar strip of D7, the Records.

### Roles and handoffs

- Handoff folder: `scratch/phases/D2/` (not in the repository); `contracts.md` written 2026-10-17 (hotkeys, the free region, shared files and owners, the army-name finding).
- Builder: `builder-script` (a scripted page, generated by the tool).
- Design page: https://claude.ai/artifact/XKaDgiURhPKZ76cNyCQ6MU (round 1, 2026-10-17; the designer's handoff `scratch/phases/D2/design.json`, fifteen figures in five groups, `mock_d2r2.py`, `measure_names.py`). Gate A passed the same day: every addition names its row or register id, the triggers and variables of the new figures (`is_leading_army`, `is_leading_army_group`, `casualties_k`, `num_units_in_state`, `num_units_in_combat`, the entrenchment, plan and trait variables) confirmed in the game's documentation by the orchestrator; seven decisions for the user, the seventh (the commander name box, 198 or 210 px) added by the orchestrator.
- Worktrees: main tree (one page). Another session works on E1 in the same tree; its files are left alone.

### Decisions (round 2)

- 2026-10-17, user, on the design page (https://claude.ai/artifact/XKaDgiURhPKZ76cNyCQ6MU): "You can proceed with the plan and implementation." Every recommendation is the answer: 1 three banded tables of five rows; 2 a row click chooses the army and the Equipment card shows its own kinds, right-click moves the camera; 3 the camera button goes to the state with most of the army's divisions, the HQ written under it; 4 both tables sort by a click on a head; 5 975 px wide; 6 a field marshal leading an army group is listed and marked "Army group"; 7 the commander's name box 210 px if it fits, else 198. Also in `scratch/phases/D2/decisions-final.json`.
- 2026-10-17, user, decision 8 (army names): the orchestrator read `hoi4.exe` in Ghidra the same day; script has no path to an army's name, but the dead "not an operative" branch of the `GetCodeName` property of a unit leader can be patched to return the army's name [SCR-078]. The user chose to have it: the row carries the army's name through `GetCodeName` in a fixed box (empty on an unpatched game), and the patch is a separate item after the page passes gate B, built by the orchestrator through the Modding Manager's scripts (`Scripts\Executable`), with the hashes recorded, and tested in a fresh 1936 game before the user's save sees it.
- 2026-10-17, user: "You don't need to ask for permission to launch the game." Taken as the grant for every launch of this round while the user was away. Withdrawn by the user on their return the same day ("please ask me before launching the game"): from then on each launch is asked for by name. No launch had been made under the standing grant. Each launch is logged below. The grant was given again by the user the same evening, after the build passed gate B: "You can now also freely launch the game whenever you need to."
- 2026-10-17, orchestrator, the design addendum: the designer put the army's name on line 2 of the Commander cell (137 px box, white, `hoi_16mbs`; the cell 312 wide, the commander's name 210) and drew the unpatched form; the rank moved into the row's tooltip and the "Army group" mark of decision 6 became a grey division count with a tooltip. Accepted by the orchestrator and shown to the user on the design page ("Changed after your approval").
- 2026-10-17, orchestrator, the patch [SCR-078]: the bytes were encoded (the user ran the encoder, as the assistant's permission classifier refused it), disassembled by Ghidra at their addresses (`C:\dev\Ghidra\projects\work\d2-armyname\cave-disasm.txt`: every call and jump resolves to the intended function or return point), recorded in the Modding Manager's `Scripts\Executable\armyname-patch-sites.json`, and applied with the new `Set-HoiArmyNameProperty.ps1` (status, restore, what-if; hashes in `known-executables.json`, the new column "Army name property" in its README table). Applied with the game closed; `hoi4.exe` SHA-256 `14b71f0a...b9d68`. `-Restore` undoes only this patch.
- 2026-10-17, gate B passed (orchestrator): the diffs of `tools/render_gui.py` (the optional key `only`), `tools/build_records.py` (`mod1440_ar_sel` in `mod1440_ch_remap`) and `tests/ScriptedGuis.Tests.ps1` (three read-only triggers) read line by line; no vanilla window changed (no `zz_` file in the diff); the six build renders read beside their mock-ups at the same crop and agree; the nine deviations of `build.json` accepted (the row's tooltips merged into the row button's tooltip, the 518 px chosen caption, `every_controlled_state` instead of `CONTROLLER`, 190 px figure labels, the 64 px fighting text, the chosen army as a renderer state, the positions from the mock-up script, seven unused sprites left for the close, the renderer key); `build.ps1 -Check army_readiness` run by the orchestrator: 603 passed, 0 failed, 34 skipped (`scratch/phases/D2/build/check-orchestrator.log`). Build renders added to the design page (version 2).

### Army names, verified before the design (2026-10-17)

The game's documentation gives the `UnitLeader` localisation object `GetName`, `GetRank`, `GetLeaderSkill` and `GetCodeName`, and the `unit_leader` scope counts and levels only; no object, property or dynamic variable gives the name of the army a leader commands, and the five undocumented items of 1.19.3 (SCR-069) are not names either. The game writes an army's name only in the `army_name` text box of the army badge, filled by code. So a scripted page cannot show it; the designer re-checks and the design says what the row carries instead.

### Build (2026-10-17)

Status: built and checked by render and tests; not seen in game. Builder: `builder-script`, main tree. Handoff: `scratch/phases/D2/build/build.json` and the renders `build-frame.png`, `build-head.png`, `build-equipment.png`, `build-armies.png`, `build-armies-unpatched.png`, `build-chosen.png`, cropped as the design's figures.

#### What was built

All in the generator (`tools/build_managers.py`, section "Army readiness"), then `python -I tools/build_managers.py`.

- **Head (decision 1).** Three cards of 311x174 at x 14, 331, 648, y 66: a head bar of 299x30 and five rows of 26, every second on a band; the label at x 14, the value right-aligned at 297. Manpower: free, in training, in the army (its tooltip names the navy's and the air force's), garrisons need (yellow), **Casualties** (`casualties_k`). Army: divisions (tooltip: battalions), **Fighting** (sum of `num_units_in_combat` over the commanders with `is_leading_army = yes`), under strength, low organisation, **Without a commander** (`num_divisions` less the sum of `num_units` over the same commanders). Stocks: **Equipped in the field** (the pieces held of what is needed over every kind, none above its need, summed in thousands; bar of 64 at x 156), **Kinds short**, **Stock cannot cover**, fuel (bar of 64 at x 66), army experience. A value that is 0 shows a plain 0 (Equipped in the field a grey dash when nothing is needed). The head is still 244 high, so Summary keeps its size.
- **Equipment card (decision 4).** A plate per column (`GFX_1440p_SG_head_<w>`), each a sort button; the game's small arrow on the sorted plate, down for largest first, up for lowest first (`mod1440_ar_eq_arrow_x`, `_asc`). `mod1440_ar_eq_sort` re-orders the unsorted arrays `mod1440_ar_u_*` of the last list and counts nothing; Kind gives the first order back. Kind names in a fixed box of 240.
- **The chosen army (decision 2).** A click on an army row runs `mod1440_ar_choose`: the commander is kept as `mod1440_ar_sel` (what `mod1440_of_me` gives: his number, or his place) with `mod1440_ar_has_sel`, and his row gets the light band (`mod1440_al_pick`, set by `mod1440_ar_marks`). The equipment list is then made by `mod1440_ar_akinds_<table>`: `num_equipment@` and `num_target_equipment@` of each kind in `var:mod1440_ar_sel`, against the country's stock; In the field reads In the army, In stock turns grey, the caption names him, All armies and a second click on his row let him go. The figures of the head stay the country's. The count lets the chosen army go when its commander is no longer among the commanders with troops, and `mod1440_ch_remap` (`tools/build_records.py`) puts his place right after the game's list of characters changed.
- **Armies card.** Plates in the design's coordinates; Commander (the game's order), Div, Fighting (largest first), Planning, Equipped, Worst (lowest first) sort from keys the count keeps (`mod1440_ar_l_game`, `mod1440_ar_lk_*`, `mod1440_ar_al_sort`). The row: portrait 34x46 at 4,2; name in a fixed box of 210 (decision 7: "Kurt von Hammerstein-Equord" fits); skill on a 30x24 plate; **the army's name** `[THIS.GetCodeName]` in a fixed box of 137, `hoi_16mbs`, white (decision 8); attack, defence, planning and logistics with the game's trait icons at 0.6 from x 189; **Location** (decision 3), a button of 130x26 with the go-to icon and the state where most of his divisions stand (fixed box of 100), "HQ <state>" or "HQ not deployed" under it, "at sea" without a button; Div grey for a field marshal with `is_leading_army_group = yes` (decision 6); Inf, Arm, Mot, Mech and **Oth** (counted: Div less the four); Fighting with "n att n def"; Planning and **Equipped** (counted with the worst kind) over bars of 46x10; the worst kind's picture in a 52x22 box over its share.
- **Clicks.** The whole row is a transparent button (`GFX_1440p_SG_hit_889x50`, the game's `skill_transparent.dds`, as the Officers rows) under the Location button: a click chooses the army, a right-click moves the camera to the Location state, as the Location button does. The button has three twins by rank, so that its tooltip names the rank: General, Field Marshal, or Field Marshal of an army group.
- **When things are counted.** As before (start of a game for every country, each day for a player, Count again, Full, the handle), plus the new figures. Location runs for a player's country only: the states the country controls and those of every country in its faction or at war with it (`every_controlled_state`), collected once per count into a temporary array, then read once per commander with `num_units_in_state@var:`. A click on a row makes the equipment list again (`mod1440_ar_list`); a sort counts nothing.
- **Sprites.** 17 in the block `# --- D2 round 2 ---` of `interface/1440p_ui.gfx`: the figure head bar and band, nine plate widths, the Location button, the chosen row's band, the row's click area, two bars and their orange twins.
- **Tests.** `is_leading_army`, `is_in_faction_with` and `has_war_with` added to the allowed commands of `tests/ScriptedGuis.Tests.ps1` (all read-only).
- **Scene** (`tools/scenes/army_readiness.json`, written by the tool): the mock-ups' samples; captures `sorted` (In stock), `pick` (the first army row), `summary`; renderer states `chosen` (Guderian's army) and `unpatched` (no army names); the checklist below.
- **Renderer.** `tools/render_gui.py` takes `only` per window or state: a widget drawn in some rows of a list only (the band of every second row, the chosen row). Without the key nothing changes.

#### Deviations

1. **The cells' own tooltips are lines of the row's tooltip** (the rank on the name, Oth's four kinds, Fighting's combat progress, the worst kind's numbers, the army group's Div). The row's click area lies over the row, as on the Officers page, so that a click anywhere on it chooses the army; a text with a tooltip over it would take the click. The rank comes from the three twins of the row's button.
2. **The chosen army's caption is one right-aligned box of 518 px**, not a name box of 198 inside the line: a right-aligned line cannot hold a fixed box in its middle. The line with the longest of the 1597 names (252 px) fits in 518; a longer one is cut at the box.
3. **The states of the Location pass are collected with `every_controlled_state`** of the country and of every country `is_in_faction_with` it or `has_war_with` it, not with `every_state` limited by `CONTROLLER`: the same states, without `ROOT`, which the start of a game (`on_startup`, `every_country`) does not set to the counted country. `CONTROLLER` is not needed in the test's list.
4. **Labels of the figure tables are 190 px wide and values start at x 204** (rows without a bar): at the design's 136 "Without a commander" was cut.
5. **"n att n def" stands in a box of 64** (4 px into the gaps beside Fighting's 56): two digits each side are cut.
6. **The chosen army has no harness capture of its own.** No effect gives an army a commander, and the clean state's Army 1 has none: the capture `pick` clicks the first row, which is empty there. The renderer draws the chosen army as the state `chosen`; the checklist asks the checker to assign a general in an open game first.
7. **Seven sprites of the `d2-readiness` block are no longer used** (`tile_145x64`, `head_136`, `bar_68`, `bar_98`, `bar_low_98`, `bar_117`, `bar_low_117`); they are left declared.
8. **Captions and All armies stand at the mock-up script's page positions** (`mock_d2r2.py`: the equipment caption ends at page x 933, All armies at page 826, card 812), where the design's text says card 826: that would end the button at 926 of the 947 card, beside the scrollbar.

#### Not seen in game

- `[THIS.GetCodeName]` in a list row with `change_scope`: empty and silent on the unpatched game, the army's name on the patched one, for a general, a field marshal of an army group and a general kept by place (SCR-078).
- `is_leading_army` and `is_leading_army_group` of a field marshal leading an army group, and whether his counts include his generals' divisions (Fighting, Without a commander, Div in grey). A 1936 start has no army group.
- Fighting, Casualties and Location above 0 or at war; the Location pass's cost with RT56's 1143 states at war.
- The chosen army's equipment against the sum of its divisions, for a general with a number and one kept by place; the chosen army let go when it loses its troops; `mod1440_ar_sel` after `mod1440_ch_remap`.
- A left and a right click on the transparent row button of a list with `change_scope`, under the Location button; the light band after a sort.
- The row's tooltip with the commander's live variables, `GetTokenLocalizedKey` of the worst kind in a tooltip, and what `avg_unit_entrenchment_ratio`, `unit_ratio_ready_for_plan`, `avg_offensive_combat_status` and `avg_defensive_combat_status` read.
- The four levels and the skill plate against the army badge; Oth with the four kinds equal to Div.
- Both sorts and the arrow, also after the daily count; `find_highest_in_array` with keys turned negative.
- `error.log` with the playset's 55 kinds and the per-army pass.

#### Game check

`tools/Invoke-GameCheck.ps1 army_readiness`, then once with the playset. The checklist is the scene's:

1. The head: three tables, Manpower, Army and Stocks, five rows each on alternating bands, labels at the left and values at the right edge of each band; Count again, Summary and the close button in the title strip as before.
2. Manpower: Free manpower against the top bar's manpower; In the army's tooltip names the navy and the air force; Casualties reads 0 in a 1936 start.
3. Army: Divisions 30 for Germany in 1936 (its tooltip 315 battalions); Fighting 0; Without a commander 30 while Army 1 has no commander (the army overview's divisions), 0 after a general is assigned and Count again pressed.
4. Stocks: Equipped in the field 100% with a full green bar, Kinds short 0, Stock cannot cover 0 for Germany in 1936; Fuel 297K of 371K as the top bar with its bar at that share; Army experience as the top bar.
5. Summary folds the page to the head with no seam; Full brings the equipment and the armies back; Shift+M and the handle hide and show the page in the form it was left in.
6. Equipment: a plate per column; a click on In stock sorts largest first with the arrow on its plate's corner, a second click turns the order (arrow up); Equipped sorts the lowest first (arrow up); Kind gives the first order back (arrow on Kind). Kind names stand in 240 px and none runs into In stock.
7. Assign a general to Army 1 (the army badge) and press Count again: his row shows his portrait, his name in yellow and his skill on a plate as on the badge, and attack, defence, planning and logistics as in his leader window.
8. That row: Div is the badge's division count; Inf, Arm, Mot, Mech and Oth add up to Div; Location names the state where most of Army 1 stands (the map) and a click on it moves the camera there; HQ not deployed under it, or the HQ's state once deployed.
9. Line 2 of the row: on this (unpatched) game it holds the four levels only, with nothing else moved; on the locally patched game it gives the army's name (Army 1, or a name given to it), also right after renaming the army.
10. Click the row: it takes the light band, the equipment card reads The army of <his name>: N kinds it needs, In the field becomes In the army, In stock turns grey, All armies shows; In the army against the sum of his divisions (division details); click the row again, or All armies, for the country.
11. Right-click the row: the camera moves to the Location state and the row is not chosen; a click on the Location button does the same.
12. Hover the row: the tooltip gives his name and rank, the army's name line, entrenchment, readiness for the plan, battle plans, traits, the average combat progress, the other divisions and the worst kind with its numbers.
13. Sort the armies by Div, Fighting, Planning, Equipped and Worst: the arrow follows and the chosen army keeps its light band after a sort and after Count again.
14. A general without a number (`mod1440_chk_by_effect`, then given an army; or a general of Add German Generals AI REWORK): listed with his values, chosen by a click, his equipment shown.
15. `error.log`: no line naming mod1440, no "Could not find sprite type", no "invalid scope" line, also with the playset's 55 kinds.

### Game checks (round 2)

Build: `9fb9e0f` plus the uncommitted round 2 build, on 2026-10-17. The checker agent could not be spawned (the assistant's permission classifier refused the brief), so the orchestrator ran the launches itself under the user's grant.

| # | Date | Build | By | Checked | Result | Screenshot | Taught |
|---|---|---|---|---|---|---|---|
| 1 | 2026-10-17 | 9fb9e0f+dirty, patched hoi4.exe (SCR-078) | orchestrator | `tools/Invoke-GameCheck.ps1 army_readiness` (cold start, this mod alone, 1 January 1936): the page, the sort by In stock, the pick (empty list), the Summary form; `error.log` | the page as rendered: three figure tables (1332K, 30 divisions, 30 without a commander in yellow, fuel 297K of 371K), the equipment list with the game's own pictures, the arrow on In stock after the sort, Summary with the map free under it; every expected widget found; no line names the mod. 4346 new lines "Could not find coloring for character '.'" from the top bar strip of D7 (fix round 1) | `scratch/checks/army_readiness-20261017-1322*` | a text as wide as its box is cut inside its colour code (fix round 1) |
| 2 | 2026-10-17 | same, game left open (`Invoke-GameSteps -Start`) | orchestrator | by hand: Rundstedt assigned to Army 1 through the badge, Count again; the army renamed "Nord"; the row click; sort by Div; All armies; Shift+M twice; probe texts in the row | the row: portrait, name, skill plate 4, levels 5/3/5/2, Div 30 = Inf 26 + Arm 3 + Mot 1, Planning 0%, Equipped 100%, Worst 100%; Without a commander 30 then 0; the row click: light band, "The army of Gerd von Rundstedt: 5 kinds it needs", In the army, grey stock, All armies; the sort arrow on Div; All armies back; Shift+M hides to the handle and shows again. **Defects:** Location "at sea" and "HQ not deployed" for an army standing in Germany; the caption "1 commanders with troops". **Army name:** empty with `[THIS.GetCodeName]` and with `[THIS.Unit.GetCodeName]`; the probe `[THIS.GetLeaderSkill]\|[THIS.GetIdeologyGroup]\|[THIS.GetHerHis]\|[Unit.GetRank]\|[Character.GetHerHis]` printed "\|\|his\|\|his": the row's scope is the Character localisation object, the patched UnitLeader property is never asked (SCR-078 updated) | `scratch/checks/ar_r1_general-*`, `ar_r1_rename-*`, `ar_r1_pick-*`, `ar_r1_sortdiv-*`, `ar_r1_allarmies-*`, `ar_r1_hide-*`, `ar_r1_show-*`, `ar_r1_objects-*` | a script scope gives texts the Character object; `GetRank`, `GetLeaderSkill`, `GetCodeName` are empty there (X21 explained) |
| 3 | 2026-10-17 14:01 | fix round 1 | orchestrator | `Invoke-GameCheck.ps1 army_readiness top_bar` (cold start), then Rundstedt given Army 1 by hand, `effect mod1440_chk_ar_where` | top bar "+2.3/d", "+0.28/d", nothing cut, no "coloring" line; caption "1 commander with troops"; Location still "at sea", though the check effect put him in Brandenburg with 6 of 30 divisions (fix round 2) | `scratch/checks/top_bar-20261017-1402*`, `ar_r2_*` | a stored state tested with `> 0` in a row did not hold (fix round 2) |
| 4 | 2026-10-17 14:38 | fix round 2, Character patch of hoi4.exe | orchestrator | cold start, Rundstedt given Army 1, the Army names switch, the army renamed, the Location button | Location Brandenburg; the button moves the camera there; names on: "Army 1", then "nord" at once after the rename | `scratch/checks/ar_r3_*` | SCR-078 confirmed: the default name is in the string; a rename follows at once |
| 5 | 2026-10-17 14:47 | same, with "Add USA Generals AI REWORK" beside this mod | orchestrator | its event accepted as the USA, back to GER, `effect mod1440_chk_by_effect`, Martin Bormann (no number) given Army 1 | his row with skill 1, levels 1/1/1/1, Brandenburg, Div 30, "Army 1" with names on; **defects:** the row click did not choose him, his portrait was the silhouette (fix round 3) | `scratch/checks/ger_borm*` | a general without a number reads his army's name through the patch |
| 6 | 2026-10-17 15:37 | fix round 3 | orchestrator | cold start, Bormann given Army 1, row click, `effect mod1440_chk_ar_pick`, Rundstedt's row click | Bormann's portrait shows; the check effect chose his army (band, "The army of Martin Bormann", In the army); **regression:** a mouse click chose nobody, Rundstedt included (fix round 4: stacked transparent buttons toggled the choice twice) | `scratch/checks/r4_*` | |
| 7 | 2026-10-17 16:31 | fix round 4 | orchestrator | cold start; Rundstedt given Army 1, clicks on his commander cell; Bormann given Army 1, click; a click on the Planning column | the click chooses (band, "The army of Gerd von Rundstedt: 5 kinds it needs") and a second click lets go; Bormann chosen the same way; the Planning column takes the click too; the harness's aim at the row's centre lands in the Location button and moves the camera, as designed (the scene re-aimed); no line of `error.log` names the mod | `scratch/checks/r5_*` | |

- 2026-10-17, the army's name, decided again: the patch of the UnitLeader property is never asked from a scripted GUI (round 2, check 2). A second site, on the Character property `GetHerselfHimselfCap`, was built outside this session at the user's direction and recorded in SCR-078; `Set-HoiArmyNameProperty.ps1 -Status` reports it on (SHA-256 `e8b1880b...a94af6`). The row's line 2 reads `[THIS.GetHerselfHimselfCap]` behind a switch on the Armies card, off by default, because script cannot tell a patched executable and an unpatched one prints "Himself" (orchestrator's call; the user's note asked for an empty box on an unpatched game).

Not seen in game after check 7: the tooltips (the harness cannot hover), the right-click on a row (the harness's map drag did not move the camera, so a camera move could not be told apart), an army group and its grey Div, a deployed HQ, Fighting and Casualties above 0, the chosen army after a sort and after the daily count, time running, the user's whole playset of about 56 mods and its 55 kinds of equipment.

### Fix round 1 (2026-10-17)

- **Issue:** in the first game check of D2 round 2 the top bar strip read "+2.32.." and "+0.28.." for political and command power per day (Germany, 1 January 1936; `scratch/phases/D2/topbar-crop.png`, the top bar of `scratch/checks/army_readiness-20261017-132225.png`), and `error.log` got "[bitmapfont.cpp:2861]: Could not find coloring for character '.'" twice a frame, about 4900 lines in one launch.
- **Cause:** every chip's text box was as wide as its widest sample measured, with nothing to spare: "+2.00/d" and "+2.32/d" are 51 px in `hoi_18mbs` (the glyphs' advances; the game drew "+2.32" 35 px wide, as the fonts give it), and the box was 51. The game cuts a text that is as wide as its box. Its cut kept the "§" of the "§!" that ends the value's colour and dropped the "!", so the text ended in "§.." and the font asks for a colour named "." each frame. Stability and war support (67 of 67), consumer goods (42 of 42), the two manpower chips and the resources stood at the same edge.
- **Fix** (`tools/build_managers.py`, "Top bar strip (D7)"): each chip names its widest plausible value (`widest` in `TB_CHIPS`), and the generator stops when a box cannot hold it with `TB_TEXT_MARGIN` = 3 px to spare, measured with the game's font (`tb_widths()`). Political power per day has one decimal now (`|+=1`, "+2.3/d"; up to "+99.9/d"); command power keeps two (up to "+9.99/d"). New widths: political power 93 (was 90), command power 90 (87), stability 109 (106), war support 108 (105), civilian factories 114 (119, for "999  99 free"), military factories 110 (115, "999  99 idle"), dockyards 102 (107, "99  99 idle"), fuel 131 (128, "9999K/9999K"), consumer goods 77 (74), manpower in the field 122 (119), in training 142 (139), resources 64 (61, "-999"). The eight defaults still end at x 1951 (909 of 912 px), now at 1042, 1139, 1233, 1346, 1470, 1588, 1702, 1820; the edit button stays at 1970. The room budget and the "Needs N px" tooltips follow the widths. The chip boxes `GFX_1440p_SG_topbox_<w>x26` of the D7 block of `interface/1440p_ui.gfx` were made at the new widths.
- **Limits:** three-digit idle dockyards with a three-digit count, more than 99 free civilian factories, a weekly stability or war support change of 10% or more, and command power of 10 a day or more are cut with dots, without the colour error only if the cut does not fall at a colour code.
- **Re-test:** the eight chips with nothing cut ("+2.3/d", "+0.28/d" for Germany in 1936), at the positions above, the edit button and the Records handle where they were; `error.log` without "Could not find coloring"; the panel's widths (93, 90, 109, 108, 114, 110, 102, 77, 131, 122, 142, 64 px).

Two more findings of the same check, by hand in the open game (this mod alone, 1 January 1936, Rundstedt given Army 1, Count again; `scratch/checks/ar_r1_general-20261017-133137-grid.png`, `ar_r1_pick-20261017-134142-grid.png`). Seen working there: the row (portrait, name, skill 4, levels 5/3/5/2, Div 30 = Inf 26 + Arm 3 + Mot 1), Without a commander 30 then 0, the row click with the light band and "The army of Gerd von Rundstedt: 5 kinds it needs", In the army, the grey stock, All armies, the sort by Div with its arrow, Shift+M, Summary and Full, the equipment sort, no line naming the mod in `error.log`.

- **Issue A:** Location read "at sea" for Rundstedt, whose 30 divisions stand in German states.
- **Cause A** (by reading the generated script against the Records' pass, not seen in the game): the read itself, `num_units_in_state@var:<temporary variable>` in a general's scope, is the Records' proven form (SCR-021, `mod1440_of_best`: the state in a temporary variable, then the country's own `every_army_leader`). The first build differed in two things no check had seen: the states were collected with `every_controlled_state` into a temporary array (`add_to_temp_array` in each state's scope), and the array was looped over with `for_each_loop` inside each general's scope. One of the two gave the general no state; which one, a check effect tells (below).
- **Fix A** (`tools/build_managers.py`, `ar_count()`): the pass is the Records' form throughout. After the leaders pass, for a player's country, the states come from `controlled_states` with `for_each_scope_loop`, as the States page takes them (seen in game), the country's own and those of every country in its faction or at war with it; each state goes into the temporary `ar_st`, and the new scripted effect `mod1440_ar_here` enters the country (`var:ar_me`) and runs its `every_army_leader`, where each general keeps the state with most of his divisions (`mod1440_al_loc`, `mod1440_al_lcnt`, both reset in the leaders pass). No temporary array is used.
- **Check effect:** `mod1440_chk_ar_where` (`tools/check_effects.py`) logs how many states `every_controlled_state` put into a temporary array, how many of them a `for_each_loop` in a general's scope saw with his divisions summed over them, the same sum by the fixed form, and where the count then puts each general.
- **Issue B:** the caption read "1 commanders with troops". **Fix B:** a twin "1 commander with troops. Click him for his army's equipment, right-click for the map." shown when the list has one row (`ar_al_caption_one`); the plural shows from two.
- **Not changed:** the army's name line (`[THIS.GetCodeName]`): the row's scope answers as the Character object, which has no such property, so the line prints nothing and logs nothing; what it reads is the orchestrator's and the user's decision. The live probes in `localisation/english/mod1440_l_english.yml` were generated over. "HQ not deployed" under Location is what `state_deployed` gives for an army whose headquarters the player has not placed.
- **Re-test:** from a fresh start (a new scripted effect called from an earlier one is unknown at the first live reload, X70): Rundstedt given Army 1, Count again: Location names the state where most of his divisions stand and a click on it moves the camera there; `effect mod1440_chk_ar_where` and `game.log` say which of the two first-build constructs failed; the caption reads "1 commander with troops".

### Fix round 2 (2026-10-17)

Re-launch of 14:01 (cold start, this mod alone): the top bar fixed (+2.3/d, +0.28/d, nothing cut, no "coloring" line), the caption "1 commander with troops", no line naming the mod. Location still read "at sea" (`scratch/checks/ar_r2_general-20261017-140342-grid.png`, `ar_r2_recount-20261017-140447-grid.png`).

- **Issue:** Rundstedt, given Army 1, read "at sea" under Location, also after Count again.
- **What the check showed:** `effect mod1440_chk_ar_where` logged 24 states, his 30 divisions reached by the old and by the fixed pass, and after the count "Gerd von Rundstedt stands in Brandenburg with 6 divisions". The capture taken right after that effect (`ar_r2_after-20261017-140441.png`) still shows "at sea", while the same row shows the numbers the count wrote beside it in the same loop (Equipped 100%, Worst 100%). So the pass runs and writes `mod1440_al_loc`; the row's condition does not see it.
- **Cause** (from the generated files): the row asks `check_variable = { mod1440_al_loc > 0 }`, and `mod1440_al_loc` holds a state set from `THIS` of the state's scope. Nothing in the mod had asked a variable that holds a state whether it is above 0 and been seen to work: the Records keep a kind number beside every scope they store (`mod1440_wd_sa^i = 2` for a state) and test that, and the HQ condition of the first redesign (`mod1440_al_hq > 0`) was never seen true. The numbers of the row (`mod1440_al_fill`, `mod1440_al_eq`, written in the same leader's scope) are plain numbers and show.
- **Fix** (`tools/build_managers.py`, the armies row): Location is asked by `mod1440_al_lcnt > 0`, the number of his divisions in that state, a plain number written in the same pass; the right-click and the Location button's click ask the same. The HQ condition stays as it was (state_deployed is undocumented, SCR-069; an army of a 1936 start has no HQ deployed), to be settled by the check effect below once an HQ is deployed.
- **Check effect:** `effect mod1440_chk_ar_row` (`tools/check_effects.py`) enters each element of the list's array as the row does and logs `mod1440_al_loc` raw and by name, whether "> 0" and "not 0" hold for it, `mod1440_al_lcnt` and "> 0", the same two for the HQ, `state_deployed` and `mod1440_al_fill`: which form a row sees for a state.
- **Re-test:** Rundstedt given Army 1, Count again: Location names Brandenburg (6 of 30 divisions, as the check effect logged), a click on it and a right-click on the row move the camera there; `effect mod1440_chk_ar_row` (after `python -I tools/check_effects.py`, then `--restore`) shows "loc>0 0, lcnt>0 1" if the cause is as read here. With his HQ deployed, the same effect says whether the HQ line needs the same change.
- **Army names (decision 8), the source settled:** the user built a second site of the local patch (SCR-078, rewritten 2026-10-17; `Set-HoiArmyNameProperty.ps1 -Status`: "[Character.GetHerselfHimselfCap] of an army leader is the name of his army"). The row's line 2 is now `[THIS.GetHerselfHimselfCap]`, and the rank line of the row's tooltip carries it too. Script cannot tell whether the executable is patched, and an unpatched game (or a character with no army) gives the pronoun "Himself", so the line shows only while the country variable `mod1440_ar_names` is 1: a toggle "Army names" (`GFX_sort_button_100x29`, its second frame for on, as the choices of the States page) beside the Armies card's title, off by default, its tooltip saying it needs the local patch. The line is also hidden for a field marshal of an army group (`is_leading_army_group`), whom the patch, which answers for an army leader, is not known to answer. The row's button has two more twins (General and Field Marshal with the line), five in all. The captions of the card start at x 240 now, clear of the toggle. The scene draws the names in the state `names`; off is its own state.
- **Re-test (names):** Army names off: line 2 holds the four levels only. On: the button changes its look; on the patched game Army 1's name under Rundstedt and under his rank in the tooltip; renaming the army changes it; on an unpatched game the line would read "Himself" (not to be left on there); a field marshal of an army group (two armies under him) shows no line, which is not seen yet.

### Fix round 3 (2026-10-17)

Launches of 14:38 to 14:52 confirmed fix round 2: Location reads Brandenburg for Rundstedt's Army 1 and its button moves the camera there; Army names turns on with its second frame and line 2 reads "Army 1", and "nord" right after a rename (`scratch/checks/ar_r3_general-*`, `ar_r3_names-*`, `ar_r3_rename-*`). With "Add USA Generals AI REWORK" beside this mod, `mod1440_chk_by_effect` made Ferdinand Schoerner and Martin Bormann without a number; Bormann given Army 1 and Count again: his row with skill 1, levels 1/1/1/1, Brandenburg, Div 30 and "Army 1" (`ger_borm_pick-20261017-145134-grid.png`). No line of `error.log` names the mod. The right-click on a row stays unseen (the harness's drag did not move the map).

- **Issue 1:** a click on Bormann's row did not choose his army (no light band, the card stayed on all armies), with Army names on and off. Rundstedt (a number) was chosen in round 1.
- **Cause 1, not settled:** the effects the click runs are the same as the Officers row click, which chose a general of that mod by place in check 6 of E2: `mod1440_of_me` in the row's scope, then `mod1440_ar_choose` in ROOT, which sets `mod1440_ar_sel` and `mod1440_ar_has_sel` unless `of_me` is 0. The caption stayed on all armies, so `has_sel` was never set: either the click met no button (the five twins of the row's button are shown by `is_field_marshal`, `is_leading_army_group` and the Army names switch, and in the Officers page the button has no condition), or `of_me` was 0 in the click's scope.
- **Fix 1** (`tools/build_managers.py`, the armies row): under the five twins stands a sixth button, `ar_row_hit_any`, always shown, with the same click, so that a click meets a button whatever the twins' conditions answer; and a click whose `mod1440_of_me` gives 0 takes the list's element (`v`, what the count put in the array) instead. Check effect `mod1440_chk_ar_pick` (`tools/check_effects.py`): for each element of the list, as the row enters it, `THIS`, `of_me`, `mod1440_ch_at` and the twins' conditions; then the click's own effects on the first general kept by place, and what the page reads after them. Its log tells which of the two was the cause.
- **Issue 2:** Bormann's row showed the unknown leader; the game's list of leaders shows his picture.
- **Cause 2:** the officers' portrait lookup (`build_records.portraits()`) knew only characters whose file gives them a command (`corps_commander`, `field_marshal`, `navy_leader`). Bormann's file gives him an advisor role and an army portrait (`GFX_portrait_GER_martin_bormann`); `tools/make_game_tables.py` left such characters out of `tools/portraits_table.py`.
- **Fix 2:** `make_game_tables.py` takes a character of the game with an army or navy portrait and no command in his file as `officer_by_effect`, and the officers' lookup takes those too: 182 more rows, 1801 characters in the table (was 1619). The table's version changed, so every officer's portrait is looked up once again at the next count. The playset's table (`--mods`) is unchanged: its characters without a role were taken as officers already.
- **Re-test:** as in the launch, Bormann given Army 1, Count again: his portrait in the row; a click on his row chooses his army (light band, "The army of Martin Bormann", In the army); `effect mod1440_chk_ar_pick` (after `python -I tools/check_effects.py`, then `--restore`) logs the twins' conditions and `of_me` for him, which says which cause it was; Rundstedt still chosen as before.

### Fix round 4 (2026-10-17)

Launch of 15:37 to 15:40, this mod alone, the build of fix round 3. Bormann's portrait shows (`scratch/checks/r4_pick-20261017-153744-grid.png`). `effect mod1440_chk_ar_pick` logged for him THIS -21474.83648, `of_me` and his place 5368.72803, both rank conditions answering, and after the click's own steps `has_sel` 1, his army chosen, 5 kinds listed and his mark set; the page then showed the band and "The army of Martin Bormann: 5 kinds it needs" (`r4_reopen-20261017-153835-grid.png`). So the steps are right for a general kept by place.

- **Issue (a regression):** a real click on a row chose nobody: Bormann by `ar_row_hit#0` and by `ar_row_hit_any#0`, and Rundstedt (a number) by `ar_row_hit#0` (`r4_any-20261017-153904-grid.png`, `r4_rund-20261017-154005-grid.png`). In round 1, with one row button visible at a time, the same click chose Rundstedt.
- **Cause:** fix rounds 2 and 3 stacked transparent buttons over the whole row: five twins by rank and Army names, then a sixth always shown. A click then ran the choice more than once: the choice is a toggle (a second click on the chosen army lets it go), so an even number of runs leaves nothing chosen. The log above shows that one run chooses. Whether the game runs every button under the pointer or only the visible ones, round 3 had two visible at once for everyone (the twin of his rank and `ar_row_hit_any`).
- **Fix** (`tools/build_managers.py`, the armies row): one transparent button over the row, `ar_row_hit`, with no condition, under the Location button, its click `mod1440_of_me` then `mod1440_ar_choose` in ROOT (the steps the check effect proved for a place, and round 1's for a number), its right-click the camera. The `v` fallback of round 3 is gone. Its tooltip names him and the details without his rank or the army's name (a single tooltip cannot follow the rank or the Army names switch); the grey Div and its head's tooltip still mark an army group.
- **Re-test:** click `mod1440_army_readiness_row/ar_row_hit#0` (the only row button now): Rundstedt's army chosen (band, "The army of Gerd von Rundstedt"), a second click lets it go; the same for Bormann; All armies; the Location button still moves the camera.
- **Confirmed** in the launch of 16:31 to 16:34 (this mod alone): a click on the commander cell, or on the Planning column, chooses Rundstedt's army and a second click lets it go; the same for Martin Bormann, who has no number (`scratch/checks/r5_raw-*`, `r5_unpick-*`, `r5_borm-*`, `r5_div-*`); no line of `error.log` names the mod. The harness's `clickWidget mod1440_army_readiness_row/ar_row_hit#0` aims at the row's centre, inside the Location button, and moved the camera (right for the page): the scene's capture `pick` now clicks 300 px left of it, on the commander's name.
