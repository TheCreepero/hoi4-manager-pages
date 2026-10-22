# Phase D3: States, docked to Construction

A table of every state the player controls, beside the construction panel. Status: done on 2026-10-12, awaiting the tester's judgement. The page is described in [Scripted GUIs](../Scripted-GUIs.md).

## Scope

- Tab: Construction (`T`). The vanilla window `countryconstructionsview` is not overridden: it already has `clipping = no`, so a container attached with `parent_window_token = construction_tab` shows beside it.
- What the vanilla screen does not show: any list of states. Free slots, building levels and resources are read one state at a time, from the map or the state view.
- Out of scope: the construction queue (script has no list of it), queueing a building from the table (no effect does that without skipping the cost), buildings that stand in provinces.

## Inventory

- State values, all documented in the game's `dynamic_variables_documentation.md` and read in the probe (X20): `infrastructure_level`, `industrial_complex_level`, `arms_factory_level`, `building_level@<building>`, `resource@<resource>`, `state_population_k`, `compliance`, `resistance`.
- Free slots: no variable. The trigger `free_building_slots = { building = industrial_complex size > N include_locked = no }` takes a written N only, so a search of five questions is written out per state (`free_slot_tree` in `tools/build_managers.py`).
- The camera: `ROOT = { goto_state = PREV }` in the click effect of a row (X13).
- Icons of the column heads: frames of the vanilla `GFX_buildings_strip` and `GFX_resources_strip`, at 0.6 and 0.9 scale.

## Decisions

- Hidden by default. The construction tab needs the map: the table is a finder. Shift+M or the handle opens it, a click on a state moves the camera there and hides it again.
- 1422 px wide and as high as the screen allows above the bottom bar: 36 states without scrolling.
- A cell that would read 0 stays empty.
- The rows are updated through `dirty`: when the list is made, not every tick. 152 rows with 21 cells each then cost nothing (70 frames a second, as without the page).
- Sorting is an effect: the keys of the chosen column in one array, the game's `find_highest_in_array` picks the next row. A second click on the same head turns the order.

## Game checks

| # | Build | Checked | Result | Screenshot | Taught |
|---|---|---|---|---|---|
| 1 | first build | the handle beside the vanilla panel, the table, free slots | works on the first launch; Hessen reads 6 free, its state view 9 unlocked with 3 built | `scratch/checks/st_1-*`, `st_2-*`, `st_4-*` | X29 |
| 2 | the same game | a click on a row; sorting by population twice; "With free slots"; the Soviet Union | camera to Hessen and the page hidden; largest first, then smallest first with the arrow turned; 152 states at 70 frames a second | `scratch/checks/st_3-*`, `st_5-*` to `st_7-*` | - |
| 3 | final, cold start through `tools/Invoke-GameCheck.ps1` | the recipe (`T`, Shift+M), the two expected buttons | found where the layout puts them | `reference/mod/states.jpg` | - |

Not seen in game:

- The Cores and Occupied choices with different results, compliance and resistance with values: a 1936 start has no occupied state.
- The daily remake of an open list.
- A list longer than the page with the mouse wheel (the probe scrolled a scripted list by dragging the bar).

## Rework of the look (2026-10-12)

Part of the pass the user asked for after the Records had been polished ([D2 notes](D2-army-readiness.md), same section).

- **What changed.** The choices (All, Cores, Occupied, With free slots, Refresh) moved into the title strip, which gave the list a row more. The columns stand in five groups with 10 px between them, and a grey caption names the buildings, the resources and the occupation columns. Every second row is on a darker band. Under the list a bar holds the totals of every column over the states that are listed. Free slots are green; a state that is not a core has its name in another colour.
- **Decided:** 1472 px wide instead of 1422, for the gaps. The totals follow the choice: with "Cores" they are the totals of the cores. Compliance and resistance have no total. The arrow of the sorted column is now placed when the list is made, not by the click, so that a game saved with the old layout shows it over the right column.
- **Not checked in game on 2026-10-12** (the launch was refused that session, see D2). The user installed the build on 2026-10-13 and played with it: "Overall I'm very happy with the results"; the error log of that session names the mod nowhere.
- **Checked in game on 2026-10-13**, cold start through `tools/Invoke-GameCheck.ps1`: the page as the renderer drew it (`reference/mod/states-panel.png`). The totals of the 24 states of Germany's start agree with their columns, added up by hand from the capture: free slots 95, infrastructure 81, civilian factories 35 (the top bar's number), military factories 28, dockyards 10.
- **After the check:** the arrow of the sorted column is the game's small arrow at about half its size on the upper right corner of the head (at its own size it covered part of a narrow head). In the second check of the day it ran into the group caption above it: the game draws that text about 4 px lower than the renderer does. The captions were raised by 5 px in the open game and stand clear, under "Buildings" and under "Occupation" (`scratch/checks/b_st3-*`, `b_st4-*`). `reference/mod/states*` still shows the captions where they were: to be stored again at the next launch.
- **Left unseen:** as the United Kingdom (`tag ENG`) the Occupied choice and the colour of a name.

## Redesign build (2026-10-16)

Status: built and checked by render and tests; not seen in game. The design and the user's choices are in `scratch/redesign/d3-states/` (`design.json`, `decisions-final.json`), reviewed on the redesign page of 2026-10-16; all five decisions as recommended.

**What was built** (`tools/build_managers.py`, section States, and the scene `states`):

- **Place unchanged:** docked to `construction_tab` at 712,0, 1472x1210, hidden by default (Shift+M or the handle).
- **Table card** (`st_table`, page 7,62, 1458x890): group captions Slots, Buildings, Resources, Occupation 27 px above the heads; 26 rows of 30 px (was 36); all 20 columns, every head still sorts. State 200 px (was 240), Slots 100 px (was 60): a 56x8 bar of the used share of the shared slots (tooltip: the game's own shared buildings only) and the free count in green.
- **Rows:** the chosen row on the light band (`GFX_1440p_SG_pick_1414x30`) with its name in yellow; a state held but not owned has the owner's flag (`GFX_flag_smallest`, `[THIS.Owner.GetFlag]`) left of its name, which moves right; a damaged building's level stands in red (a twin text with `damaged_building_level@<b> > 0`); resources are the list effect's rounded copies (`mod1440_st_r_<resource>`, `round_variable`), so totals and sort use the same numbers.
- **Clicks:** left click chooses the state (`mod1440_st_sel` on the country, the mark `mod1440_st_picked` on the state, `mod1440_st_pick`), the page stays open; right-click (`st_row_right_click`) and the band's Show on map do what the left click did before: `goto_state` and hide. When the chosen state is not in the list (first opening, another choice, a state lost), the first row is chosen.
- **The band** (page 7,964, 1458x232): four cards on `GFX_tiled_plain_bg_small` drawn by the page, with the state's content as a one-row list over them (`st_card_grid`, array `mod1440_st_card`, entry `mod1440_states_card`, `change_scope = yes`).
  - The state (430): owner's flag (`GFX_flag_small2`, 41x26), name, "Capital <GetCapitalVictoryPointName> · <category>" (the category a token per state, `mod1440_st_cat`, from `has_state_category` over the game's 13 categories, named by the game's key), "Core of / Owned by <owner>", the War Diary's record (`mod1440_sr_from`, `mod1440_sr_date`), four chips (Core / Not a core / Occupied; Coastal / Inland; Capital; Island / Demilitarised / Border war), the seven resources with their icons, people, Show on map.
  - Building slots (300): the free count, "free of N" (free plus the shared buildings), a 272x14 bar, the five main shared buildings by icon with their levels, the other eight together, a note that only the game's shared buildings count.
  - Buildings (404): nine icons, the level under each (grey dash for none), a red "-N" for damaged levels, the sum of damaged levels, the last strategic bombing.
  - Occupation (288): compliance with its speed, resistance with its speed, resistance target, for a state that is not a core; "A core of yours: no occupation" otherwise. Under it the country's compliance growth, resistance target and required garrisons (`modifier@`), drawn by the page in country scope over the row.
- **List effect:** per state also the used share (`mod1440_st_used`, 0 to 100), the shared buildings (`mod1440_st_used_n`, `_other`), the slots (`mod1440_st_slots`), the damage sum (`mod1440_st_dmg`), the rounded resources and the category token. Daily remake while open, as before.
- New sprites (`interface/1440p_ui.gfx`, block `d3-states`): `GFX_1440p_SG_head_200`, `_head_100`, `_pick_1414x30`, `_bar_56` (56x8), `_bar_272` (272x14). New triggers in the test's list: `is_owned_by`, `has_state_category`, `is_coastal`, `is_island_state`, `is_demilitarized_zone`, `has_border_war` (all STATE scope in `documentation/triggers_documentation.md`).
- The scene now carries three captures: a left click on the fourth row, a right-click on the third, Shift+M to bring the page back.

**Deviations from the design:**

- The cards stand 7 px inside the page, not 14: the rows and their scrollbar take the page's width less 14 a side, so a 14 px card margin would need a page 28 px wider. The rows stay where they were.
- The heads stand at page y 93 and the list at 127 (the mock-up: 92 and 126) so that the captions keep the 27 px from the heads the check of 2026-10-13 asked for.
- The shared buildings are icons with levels, not a sentence ("Civilian factories 2, military factories 1"): script cannot leave out the zero terms of a sentence. The damage line gives the number of levels damaged, not which: the red marks under the icons say which.
- The chips have four fixed places; the fourth shows the first of Island, Demilitarised and Border war that applies. The capital chip says "Capital", not "Capital of <owner>".
- The resources of the state card are seven fixed places with a grey dash for none, on their own line; people on the line of Show on map.

**Not seen in game:** everything of this build. In particular the one-row list as a card, `[THIS.Owner.GetFlag]` and `[THIS.GetCapitalVictoryPointName]` in a row, `_right_click` on a row button (X14 has it confirmed on a scripted button), the category token, `round_variable` on `resource@` (Hessen's coal should read 17), `damaged_building_level@` and `days_since_last_strategic_bombing` (what a state never bombed reads: the build takes 1 to 3649 as a bombing), `compliance_speed` and `resistance_speed` and their unit, and the mark after a sort and the daily remake.

**Game check:** `tools/Invoke-GameCheck.ps1 states`

Checklist for the tester:

1. The page opens (Shift+M) with the first state of the list chosen: its row on the light band, its name yellow, its cards under the table.
2. A left click on another state chooses it: band and mark follow, the page stays open (capture `states-pick`).
3. A right-click on a state, and Show on map in the band, move the camera there and hide the page (capture `states-goto`); Shift+M brings it back with the same state chosen (capture `states-back`).
4. Sort by a column, choose Cores, press Refresh: the chosen state keeps its mark while it is listed.
5. Hessen against its state view: 6 free of 9, the slot bar a third full, coal 17, buildings 4, 2, 1.
6. The state card: Capital Frankfurt, Dense Urban Region, Core of the German Reich, the Core and Inland chips, the German flag.
7. The occupation card: compliance growth -2.0% and resistance target +5.0% as on National Figures; required garrisons a grey dash.
8. Tooltips of the two slot bars; `error.log` names no line of the mod, and no "invalid scope for var" or dynamic token line.
9. Later, with an occupied and a bombed state (ten days of war inside January, or the tester's game): the owner's flag in the row and the card, Occupied chip, the record of the taking, compliance and resistance with their speeds, red levels, the day of the last bombing.

### Fix round 1

- Sort tooltips showed `$PRODUCTION_MATERIALS_OIL$` and the like as written (user's game, `states.png`): a `$key$` in the text of a `pdx_tooltip` is not resolved, unlike in a text box (SGUI-019). The tips of the building, resource and occupation heads are now plain words ("Oil.", "Civilian factories."), and `build_managers.py` stops with an error when a tooltip's text holds a `$key$`.
- Values of the table, their damaged variants and the totals are centred in their column, under the head, which was already centred (were right-aligned, 2 px in and 8 px short); the free count is centred in the 38 px the slot bar leaves (`ST_FREE_BAR`). Re-test: hover a few heads of each group; numbers under their icons, also with 4 or 5 digits.

## Close

- [x] The rework of 2026-10-12 seen in game, and `reference/mod/states*` stored again (2026-10-13)
- [x] Roadmap status and link
- [x] README and Workshop description
- [x] Scene file (`tools/scenes/states.json`, written by the tool)
- [x] Finished page stored under `reference/mod/`
- [ ] The tester's judgement: the columns, the default order, hidden by default
