# Phase E4: Wars

One row per enemy of today and one per finished war: since when, for how long, what it cost, what was taken and lost. A page of [the Records](../Roleplay-Pages.md). Status: built and checked in game on 2026-10-12; awaiting the tester's judgement. Not seen: casualties and the other totals above zero, a capitulation. How each value was checked is in [Scripted GUIs](../Scripted-GUIs.md), "The Records".

## Scope

- **Vanilla has:** the war overview, per war, while the war lasts: the sides, their strength and losses. A finished war is gone from the game's screens.
- **The page:** the wars of the whole campaign in one table, the finished ones included, with numbers the mod wrote down at their start and end.
- **Out of scope:** losses inflicted on an enemy (the documentation has no such value); a war as the game groups it (script sees enemies, not wars, so the page has a row per enemy); the strength of an enemy (the game's estimate belongs to its intelligence system).

## The page

| Part | Size | Holds |
|---|---|---|
| Totals card | 1640x150 | own casualties of all wars; convoys sunk by us; months of the longest war; war support lost to casualties, to convoy losses and to bombing; own surrender progress |
| At war with | 1640 wide, rows 40 high | one row per enemy of today |
| Finished wars | the rest, rows 40 high, scrolls | one row per enemy of a finished war, newest first |

| Column | Width | Today's enemy | Finished war |
|---|---|---|---|
| Country | 380 | name with flag | the same |
| Since, until | 2 x 150 | the date the war began | both dates |
| Days | 80 | today minus the start | end minus start |
| Our casualties | 150 | own casualties since the start | own casualties between the dates |
| States taken, lost | 2 x 90 | counted by the territory hook, by the other country of each line | the same, frozen |
| Their surrender | 110 | `surrender_progress` of the enemy, as the vanilla war overview shows it | - |
| Outcome | 250 | Capitulated, if so | Peace, Capitulated, Annexed, Made a subject |

- **Our casualties is the country's whole loss in that time.** With two enemies at once both rows count the same dead, and the column head says "in that time". The Totals card has the true sum.
- **A row is an enemy, not a war.** The Allies show as several rows with the same dates.

## Data and script

A section `wars()` of `tools/build_managers.py`. The rows are kept by the same two mechanisms as the diary: the hook for the start of a war, the daily comparison of `enemies` for its end.

| Name | What |
|---|---|
| `mod1440_wr_enemy`, `_since`, `_day0`, `_cas0`, `_taken`, `_lost` | arrays of the country, one element per enemy of today: the country, the date, the day number (`global.num_days`, for the Days column: X35), own `casualties` on that day, two counters |
| `mod1440_wo_enemy`, `_since`, `_until`, `_days`, `_cas`, `_taken`, `_lost`, `_outcome` | arrays for finished wars, 200 rows. `_outcome` is a text key (X37) |
| `mod1440_wr_open` (effect) | called where E1 writes "War declared": adds the enemy's row |
| `mod1440_wr_close` (effect) | called where E1 writes "Peace with": moves the row to the finished wars with the end date and the difference in casualties. The outcome is set on the row before it closes: "Annexed" by `on_annex` (seen), "Capitulated" by `on_capitulation` (not seen yet) or by `has_capitulated` asked when the row closes, "Made a subject" when the country is in `subjects` then. It reads "Peace" otherwise. A country that no longer exists still gives its name and flag from the row (X34) |
| the territory hook of E1 | also adds one to `_taken` or `_lost` of the other country's row |

Values of the totals card: `casualties`, `convoys_destroyed`, `longest_war_length`, `has_casualties_war_support`, `has_convoys_war_support`, `has_bombing_war_support`, `surrender_progress` (R14). Commands new to the test's list: `has_capitulated`, `has_war_with`. Nothing writes to the game.

## What the probe settled

| Question | Answer | For this page |
|---|---|---|
| A country in an array, with a value read in its scope | yes: name, flag, surrender progress, casualties (X40) | the enemy rows as planned. The list of today's enemies is scoped to the country; the finished wars are read by index |
| The hooks of a war | `on_war_relation_added` and `on_annex` seen with their scopes; `on_peace` fires without saying with whom; `on_capitulation` not triggered (X43) | starts from the hook, ends from the daily comparison, as planned |
| A date in an array | yes (X35) | the date columns; days from the stored day numbers |
| The values of a war at a start | Italy on 1 January 1936: one enemy, casualties 0, months at war 0 | nothing above zero has been seen: every value of the Totals card is compared with the game in the user's play |

## Checks

1. **Paused, by effects:** `declare_war_on` Poland as Germany: a row with today's date and zero days. `white_peace`, then the daily effect from the console: the row moves down with the same date twice and "Peace". `annex_country`: "Annexed". Take two states by `set_state_controller`: the counters.
2. **A war that runs at the start:** Italy on 1 January 1936 has Ethiopia as an enemy; the row reads "before the record began".
3. **Values against the game:** casualties against the war overview; war support losses against the tooltip of war support; surrender progress against the war overview.
4. **Needs time:** casualties that rise, a war that ends by fighting. The user's play, or decision 3 of the Records.

## Later

- **A graph of casualties per month** is on History already (D5). A link button is all this page adds.
- **Per war instead of per enemy:** rows with the same start date joined under the first attacker. Only if the plain table proves hard to read.

## Decisions

- 2026-10-12: planned.
- The three counters for aces of [E5](E5-aces-roll.md) stand on this page as the card "In the air".
- A capitulation is found by asking each enemy once a day, not by the hook.

- 2026-10-12, the user: "a round of improving the UI ... really polished and fit their purpose really well", with free hands. Done the same day: the totals and the three ace counters as ten tiles in a row, both tables striped under bars of heads, and a bar for each enemy's surrender progress beside its percentage. Checked in game and from a cold start (`scratch/checks/crop_p_*.png`, `reference/mod/`).

## Additions of 2026-10-13: the file of a war

The user had installed the build of 2026-10-12, played a war with it and wrote on 2026-10-13: "Overall I'm very happy with the results. I just want more graphical details", with three wishes: an officer's portrait in his file and in the list; a record, in the officer's file and in the War Diary, of each battle over a victory point won or lost and of each state captured; a file for a war as there is one for a general, with the flags and maybe the leaders of each side and some statistics.

- **The page** has the two tables on the left (940 px) and the file of the chosen war on the right (700 px), as the Officers page has its file. A row is chosen by a click on the plate with the enemy's name; the chosen row has the lighter band. With nothing chosen the file opens on the first war there is, and a war that ends keeps its file as it moves to the finished wars.
- **The file:** the two flags and names; the two heads of government with portrait, party and ideology (the enemy's are public: the game shows them in the diplomacy view); since when, until when and how it ended; six figures (days, casualties, states taken and lost, victory points taken and lost) and how close each side is to giving up, as bars; and the newest twenty lines the War Diary has about this enemy, from both logs.
- A row counts victory points taken and lost (`mod1440_wr_vpt`, `_vpl`); rows of an older save get zeros (`mod1440_wr_grow`). The tables lost the columns that the file now holds (casualties and the counts of a finished war).
- An enemy that is no more (annexed) has no leader to show: the file says so and shows its flag and name, which the record keeps (X34).
- **Checked in game on 2026-10-13** (checks 3 and 4 below). The fault that kept wars from closing and its mending are in the [E1 notes](E1-war-diary.md).

**Left unseen:** casualties in a war with fighting. A surrender between 0 and 100% was seen in the second check of the day (theirs 18%, ours 4%, `scratch/checks/b_wr1-*`), and so were the counts an older save lacks: they are padded when the war is next written to (check 5 of the [E1 notes](E1-war-diary.md)).

**Seen and left as it is:** an annexation writes "State taken" for every state of the country (nine lines for Czechoslovakia), and a state that goes back in a white peace reads "State lost".

## Checks in game (2026-10-12 and 13)

| # | Date | Build | Checked | Result | Screenshot | Taught |
|---|---|---|---|---|---|---|
| 1 | 2026-10-12 | `1a08bb3` +dirty | war on Poland by effect, two states taken and one lost by effect, a white peace, the daily run from the console | a row with the day's date, 2 taken, 1 lost, surrender 9%; after the peace the row under Finished wars with both dates and "Peace" | `scratch/checks/crop_e1_8.png`, `view_e1_9.png` | - |
| 2 | 2026-10-12 | the same game | a second war and nine days of game time | 8 days on the 9th, 2 states lost to Polish troops, casualties 0 (no battle) | `scratch/checks/crop_e1_19.png` | X55 |
| 3 | 2026-10-13 | `9c832ae` +dirty | live session: war on Poland by effect, three victory points and two states changing hands, a white peace; war on Czechoslovakia and its annexation; a click on each row | the file opened by itself on the first war: both flags, Hitler and Ignacy Mościcki with party and ideology, since and until, 2 states taken and 2 lost, 3 points taken and 1 lost, both surrender bars, the lines of the diary about Poland with the names of the places; after the peace the file followed the war to the finished wars ("Peace"); Czechoslovakia: 10 states taken, their surrender 100%, "has capitulated", and after the annexation "This country is no more." with flag and name kept | `scratch/checks/wr1-*` to `wr4-*` | X59, X64 |
| 4 | 2026-10-13 | the same build, cold start through `tools/Invoke-GameCheck.ps1` with ten other scenes | the page in a new game; `error.log` | both tables on the left and the empty file on the right ("Click a war in a table to open its file."); every expected widget found where the layout puts it; no line names the mod | `reference/mod/wars-panel.png` | - |


## Close

- [x] Engine Facts rows; `wiki/Scripted-GUIs.md`
- [x] README and Workshop description
- [x] Scene file and recipe (`tools/scenes/wars.json`), reference capture
- [ ] The totals compared with the game's war overview in a game with fighting
- [ ] The tester's judgement

## Redesign build (2026-10-16)

Status: **built and checked by render and tests; not seen in game.** The Wars page of the redesign pass (design `scratch/redesign/e-diary-wars/` of the main repository), in the frame described in the [E1 notes](E1-war-diary.md).

- **The left column, 548 wide.** The country at war: twelve tiles of 123x64 (casualties, longest war, our surrender, convoys sunk; war support lost to casualties, convoys and bombing, prides of an enemy fleet sunk; aces promoted, aces lost, enemy aces down, our pride lost). At war with: one row per enemy on the game's own `GFX_war_participant_entry` (531x41, frame 2, the red plate), 46 apart, its flag and name on the striped part and days, states taken : lost, points taken : lost and surrender in the four dark slots, under a bar of heads that names them. The list has the enemy as its scope (`change_scope`), so the flag is `[THIS.GetFlag]`; the row's numbers are the country's arrays read as `[?ROOT.mod1440_wr_...^i]` (X36). A click finds the enemy in `mod1440_wr_enemy` and opens its file; the chosen row is lighter (`mod1440_wr_pk`). Finished wars: the same plate, its frame by the outcome (green when the enemy capitulated, was annexed, made a subject or is gone, blue for a peace), and the game's icon of the outcome in the fourth slot with the word as its tooltip; the list runs over `mod1440_wo_fr`, so the plate's frame is the row's `v`.
- **The file of a war, 1092x1090** on the war overview's own frame: `gfx/interface/1440p_ui/wr_file_bg.dds`, made by `tools/stretch_background.py` (`war_file`) from `waroverview_bg_tiled.dds`: 76 columns taken out of the plain middle of the two panels (40 and 36, in multiples of the mesh's period of 4) and the panel bodies 584 rows higher in copies of 4 rows.
  - The top plate: "The war with ..." and the two flags on the rays. Band A: both names and, between them, since, until or today, the days and the outcome (five texts for a war of today, one that has capitulated, a finished war, and each of them begun before the record). Band B, Day by day: the war overview's progress frame as a track from the war's first day to its last or today, with a mark for each of the newest 20 lines of the diary about this war at the place of its day (`x` by property from `mod1440_wr_mx`, the date and the words in its tooltip).
  - Two panels of 522, each headed by its head of government: portrait at 0.8 (ours left, theirs right), party, ideology, faction (`GetFactionName` where there is one, the enemy's found by `mod1440_wr_card`), the surrender bar of each side, and three tiles: our casualties, states and points taken; their casualties, states and points lost. Their casualties are the enemy's whole loss since the war began (`ecas0` at the start, `ecas` each day).
  - **Our commanders in this war:** up to six officers with portrait, name, rank and "States, Points, Capitals". **Counted per war and officer** (the user's choice): when a state or a point is taken, the general on the spot (`of_best`) adds it to arrays of his own, one element per war by the war's number (`mod1440_ow_id`, `_st`, `_vp`, `_cap`; each war row has its number `id`). The file gathers them from every officer the record knows and takes the best six (`find_highest_in_array`). Exact over any length of war; it starts counting with this build.
  - **In the War Diary:** the newest 20 lines of this war, 26 high (the design's 30 did not fit 20 lines above the panel's foot): short date, icon, words, the place as a button that moves the camera.
- **Records already in saves:** `mod1440_wr_grow` gives each war row of an older save a number of its own, the enemy's casualties of today as `ecas0` (their casualties count from the upgrade), and each finished war a first day "not known" (-1, the track then runs between its oldest and newest line), 0 casualties of theirs, and its outcome read from the text it kept. `mod1440_chk_old2` makes a game look like that.

**Deviations from the design:**
- Finished wars read their flag by row index (`[?mod1440_wo_enemy^i.GetFlag]`), because the list runs over the plates' frames as the design wants; only today's enemies have the enemy as their scope.
- The plate is an icon with a static frame for today's enemies and an icon whose frame follows `v` for the finished wars; a click lands on a transparent button over the plate (`GFX_1440p_SG_hit_531x41`, the game's transparent window tile), so the plate stays as the game draws it.
- A commander's tally reads "States 5  Points 2  Capitals 1" instead of "5 states, 2 points, 1 capital": a text cannot choose between "state" and "states".
- The lines of the file are 26 high, see above. Their words are in hoi_16mbs in 200 px: "Our pride of the fleet was sunk by" did not fit 186 px in hoi_18mbs.
- Finished wars with the blue plate (a peace) show the days on the plate's plain part: the blue frame has dark slots only for states and points.

**Fallbacks:**
- `[?mod1440_wo_enemy^i.GetFlag]` by index: if the finished wars show plain shields, those rows take `GetNameWithFlag` text.
- `[?ROOT.<array>^i]` in the enemy rows is confirmed for texts (X36); if a `_visible` trigger with `ROOT.mod1440_wr_pk^i` does not work, the chosen enemy row loses its lighter band (the file still opens).
- `x` by property on the icons of the track: if the marks stand all at the track's start, the marks are dropped and the track keeps its two dates.
- `GetDateStringShortMonth` on a stored date (open): if it shows nothing, the dates of the file's lines take `GetDateStringNoHourLong` in 115 px.
- `GetFactionName` of the enemy and the faction test `mod1440_wr_c_efac`: if the name is empty where there is a faction, the line reads only "in a faction".
- Enemy casualties above zero have not been read (only 0, X40).

**Not seen in game:** the whole page. Measured without the game: the counters per war and officer cost 4 entries per officer and war he took something in, about 24 KB for 30 officers in 5 wars, 163 KB for 60 in 20 (the save-size note of the [E1 notes](E1-war-diary.md)); the tally walks the record's officers once on a click.

**Game check:** `tools/Invoke-GameCheck.ps1 war_diary wars`. The tester's checklist:

1. Declare war on Poland (`mod1440_chk_war`): a red plate with Poland's flag and name under At war with, 0 days, "0 : 0".
2. The file opens on it: the war overview frame, "The war with Poland", both flags on the rays, both names, "1 January, 1936 - today - 0 days".
3. Both heads of government with portrait, party, ideology; the faction lines; both surrender bars.
4. Take Danzig (`mod1440_chk_state2`) with a general there: a mark on the track, a line under In the War Diary, his face under Our commanders in this war with "States 1".
5. A white peace (`mod1440_chk_peace`): the plate moves to Finished wars in blue with the peace icon; the file stays on it.
6. Annex Czechoslovakia after a war (`mod1440_chk_war2`, `mod1440_chk_annex`): a green plate with the annex icon, its tooltip "Annexed".
7. `effect mod1440_chk_card_time`: 20 files between two lines of `game.log`.
8. `error.log`: no line that names the mod, no "invalid scope for var", no "Could not find sprite type".

### Fix round 1

- Flags at the wrong size and the head of government's portrait (`records_wars.png`), "GFX_portrait_..." under In the War Diary: as E1 and E3, Fix round 1 (flags `GFX_flag_small2`, kept keys written again, stale caches by `global.mod1440_tk_ep`; the ends of finished wars, `mod1440_wo_outcome`, are in the dictionary too). The rows ran over the note under today's wars: their lists got a background (E3, Fix round 1).
- The flag of the State of Japan (a red, white and blue flag like Czechoslovakia's, also on the Subjects tile): `[?mod1440_wr_c_enemy.GetFlag]` gives that flag, at the right size; whether the game's own views draw another flag for that country (a puppet or cosmetic flag of the playset) needs the game. Not changed. Re-test: compare with the flag the diplomacy view draws for it.

### Planned, not built: our war in the diplomacy view

The user chose to plan it (2026-10-16). A strip of our war with the country selected in the diplomacy view: a scripted GUI of `selected_country_context` attached to `selected_country_view` (SGUI-045, documented), shown when the selected country is an enemy of today or of a finished war. It would show the plate of that war (days, states and points taken : lost, surrender) and a button that opens its file in the Records window. Open: the scopes of a selected-country GUI (THIS the selected country, ROOT the player, as the state card has it, SGUI-022?), whether `selected_country_view` takes a child without clipping, and the place in the view beside what other mods of the playset add there (`tools/check_playset.py`). Rule 2 holds: it shows our own record of the war, nothing the intelligence system hides.

## Redesign round (2026-10-28)

Opened with `/pages-phase` on 2026-10-28. The user: "I'd like a refactor and redesign of the Wars tab in the Records. Some issues: Casualties drop to 0 once the war is over. Leader portraits are often missing and update even for wars that have ended if the country leader changes. Casualties shown are total from during the time period, not specific to that war. Also think about how the UI and user experience could be improved in any other ways."

### Scope

- **The three faults, as the orchestrator read them before the design (to be confirmed by the designer):**
  1. *Casualties drop to 0 once the war is over.* `mod1440_wr_close` takes `casualties` minus the row's `cas0` on the day the war ends; the game's `casualties` counts only the wars in progress (X78, register SCR-079), so the war's own dead have already left it and the finished row reads 0 (or less). The daily value `mod1440_wr_cas` was right until that day and is thrown away.
  2. *Leaders missing, and changing after the war.* The file reads `[ROOT.GetLeader]` and `[?enemy.GetLeader]` and the portraits `mod1440_gv_p` and `mod1440_wr_c_p` of today, also for a finished war; nothing about the leaders is kept on the row. Our portrait is the one the Government page last looked up. A portrait is found only for a character in `tools/portraits_table.py` (SGUI-028); Road to 56 names 1451 portraits by file, which no sprite can show (RT56-007).
  3. *Casualties are the country's whole loss in that time*, as the notes of 2026-10-12 say on purpose ("Our casualties is the country's whole loss in that time"). The game has a trigger `casualties_inflicted_by = { opponent = <country> thousands > <n> }` (`triggers_documentation.md:2069`), per opponent, which the 2026-10-12 design did not know ("the documentation has no such value" in Scope above): it may give each enemy's share, read by comparisons. Not in the register; what it counts (this war or all time, after the war) is unknown.
- **And the rest of the page:** a review of the whole Wars tab for a player who looks back on a campaign: per enemy versus per war, the tables, the file, the twelve tiles, what is kept at the end of a war.
- **Out of scope:** the planned strip in the diplomacy view (above); the Aces roll (E5), whose three counters stay on the page; anything another country's intelligence would hide (rule 2).

### Roles and handoffs

- Handoff folder: `scratch/phases/E4/` (not in the repository)
- Builder: `builder-script` (a generated page; the rows of a war are a save contract)
- Design page: https://claude.ai/artifact/JA1oSEQpLAcHzr5aEG1yX6 (round 1, 2026-10-28, after gate A round 2)
- Layout file: `scratch/phases/E4/layout.json`
- Contracts written (hotkeys, shared rows, shared files): yes, `scratch/phases/E4/contracts.md` (2026-10-28)
- Worktrees: main tree
- Path: the designer (a data model, the lists and the file change: not the short path)

### Decisions

- 2026-10-28: round opened; designer briefed.
- 2026-10-28, gate A, round 1: the designer's verdict `rework` (casualties from `casualties_inflicted_by` both ways, kept leaders at both ends, one row per war by `has_war_together_with`, the left column in steel, seven decisions). Passed: the faults' causes confirmed with three more found (our surrender of today and diary lines of every war with the enemy on a finished war's file; `cas0` holding other wars' dead), every addition named, `lint_layout` 0 errors (the one warning is the shared window ground, decision 5), contrast 0 of 258 under the floor, the squint by hand (`work/squint-page.png`, the audit squints no current figure). Sent back: H8, the file of a war with one enemy, the common case, leaves the right panel mostly empty.
- 2026-10-28, gate A, round 2: passed. The file of a one-enemy war now reads full (the enemies table hidden for one enemy, 5 rows that scroll for several; the War Diary runs over both columns, 31 or 23 lines); `lint_layout` 0 errors, contrast 0 of 260 under the floor, the file group squinted. Design page published; seven decisions sent to the user.
- 2026-10-29, user gate 1: the user took the recommendations ("Take the recommendations"): (1) a head of government changed during a war shows both, at the start and at the end, one portrait when the same person; (2) a row per war, its enemies in the file; (3) casualties from `casualties_inflicted_by` per enemy both ways, the daily rise as the fallback if the game check shows it unusable; (4) the plate: Days (or the year it began), Our dead, Their dead, Surr./End; (5) the Wars body in steel now, the frame and the other pages when next touched; (6) finished wars of an old save whose dead were lost show a dash, "not kept" (the real value for an enemy fought once if the game keeps it after the peace); (7) the War Diary in the file runs over both columns (31 or 23 lines) with "All its lines". Builder `builder-script` briefed.
- 2026-10-29, gate B: passed after one return (two tooltips named `casualties_inflicted_by` to the player; reworded). `build_managers.py --check` clean; the generated diff read (effects and scripted GUIs whole, English localisation whole and the nine others identical, the .gui by kind of key: layout only, no new shortcut); lint_gui 0 errors, contrast 0 of 260 under the floor; the three build renders match the mock-ups. `build.ps1 -Check wars` 275 passed, 1 failed: the game tables were made from 1.19.3.0 and the game is now 1.19.4.0 (not this build). Design page republished with the build.
- 2026-10-29, user gate 2: the user had the game tables refreshed for 1.19.4.0 (`make_game_tables.py`: the five tables, `mod1440_portraits.txt`, `mod1440_victory_points.txt`, one line of `mod1440_effects.txt`; a change of its own beside E4's) and granted no launch ("Not yet at least. I can also test this myself."). `build.ps1 -Check wars`: 276 passed, 0 failed, 68 skipped. No game check by agent; the build's checklist (`scratch/phases/E4/build/build.json`) is what the user's own test settles.
- 2026-10-29, fix round 1 opened from the user's own test: the user confirmed the second "Kingdom of France" in the German war was their own country (a defect, cause unknown); with the user's go-ahead, the builder was sent that defect, the Wars tab counting enemies instead of wars, and the two flag boxes when neither head is recorded.
- 2026-10-29, fix round 1, gate B: passed. The builder found no path in either build that opens a row against the country itself; the likely cause is the other side of a civil war (a country of its own with the player's name and flag, declared 1942.6.26, annexed 1943.6.28), put on the German war's plate by the migration's rule that finished rows ending the same day are one war. Fixed anyway: a guard in `mod1440_wr_open`, a once-per-save repair in `mod1440_wr_grow`, check effects `mod1440_chk_self_row` and `mod1440_chk_civil_war`. The tab reads the number of wars of today (`mod1440_wr_wars`, kept by open, close and the daily round); one flag box and "Not recorded" when neither head is kept. `build.ps1 -Check wars` 276 passed, 0 failed. Open for the user: whether there was a civil war, and whether a civil war shows apart.
- 2026-10-29: the user: there was no civil war at any point of that game. The cause of the row "Kingdom of France" against the player stays unknown; the user leaves it open and will try to reproduce it in game (the guard, the repair and the check effects stay). The user asked for the changes to be committed and pushed.

## Proposal

<!-- generated: proposal (tools/phase_notes.py; edit the handoff file, not this) -->
The record of a war stops reading `casualties`, which counts only the wars in progress (X78) and the whole country's loss: each enemy's row keeps both sides' dead from `casualties_inflicted_by` (our dead by their hand, theirs by ours), refreshed every day and frozen at the peace, and keeps the heads of government of both sides at the war's start and end, with their portraits, so a finished war never follows today's leaders. Rows that the game fights as one war are joined into one (enemies on the same side of a war, `has_war_together_with`), so the lists show wars and the file lists a war's enemies. The page keeps the game's war plates and the war overview frame; the lists show both sides' dead at a glance, the twelve tiles become one banded table, and the file shows the leaders at both ends, the war's figures and its enemies. Verdict: rework; effort: L: a refactor of the war record (33 new parts, the migration, the grouping, the daily reads, the kept leaders through the places), two lists built per war, the file re-laid, two outcomes, check effects for a war with casualties, a leader change and a war of two enemies.

What vanilla does badly: **Fault 1, casualties 0 after the peace (confirmed).** `mod1440_wr_close` writes the finished row's `cas` as `casualties` minus `cas0` on the day the record notices the peace. `casualties` counts only the wars in progress (X78), so the ended war's dead have left it: 0, or below 0 when another war ran at its start (`cas0` held that war's dead too). The daily `mod1440_wr_cas^i` held the number of the day before and is thrown away. The same value is wrong before the peace too: it falls on the day any other war ends, and the tile Casualties reads `casualties` and so shows 0 at peace. `casualties` is also a raw count, which a variable holds only up to 2 147 483 (newFacts).

**Fault 3, casualties not of that war (confirmed, and it was on purpose).** The 2026-10-12 design took the country's whole loss in the war's time ("the documentation has no such value"); with two enemies both rows count the same dead. Their casualties (`ecas`) are the enemy's whole loss, also to its other wars (Britain against Italy, Poland against the Soviet Union).

**Fault 2, leaders missing and following today (confirmed, with more causes).** The file reads `[ROOT.GetLeader]`, `[?enemy.GetLeader]`, `GetRulingParty`, `GetRulingIdeology`, `GetFactionName` and our surrender bar of today for every war, finished ones included (the current file figure shows Peter II of 1942 on a war of 1938, and our surrender of today on a finished war). A row keeps no leader. Portraits go missing for five reasons: (1) an enemy that no longer exists shows no leader at all ("This country is no more."): the common end of a finished war; (2) a leader whose portrait the game names by file, 1451 in Road to 56 (RT56-007); (3) a leader the game or a mod makes up (`create_country_leader`, a party that comes to power without a defined leader): a random portrait no script can name (SGUI-028); (4) characters with no row in the tables: 233 of Reichskommissariats Plus in the user's playset (`tools/check_playset.py`); (5) the lookup is done when the file opens, on today's leader, and our own portrait is the Government page's `mod1440_gv_p` of today.

**And the page.** A row is an enemy, not a war: the Allies are a dozen rows with the same dates, and a war's cost cannot be read anywhere. The twelve figures are label-over-value tiles (the ruleset wants a banded table). The file's diary lines of an enemy fought twice mix both wars (no date test), and the lists show states and points, not what a war cost.

**1. Casualties of a war: from each enemy, both ways, kept at the peace (faults 1 and 3).** Each enemy's row keeps two numbers in thousands with one decimal (a variable holds them whatever the war's length): `kus`, our dead by this enemy's hand (`ROOT = { casualties_inflicted_by = { opponent = <enemy> thousands > n } }`), and `kthem`, its dead by ours (the same asked in the enemy's scope with `opponent = ROOT`). The war's figure is the sum over its enemies; the campaign's "Casualties we inflicted" the sum over every row.

**When.** At the start: the baselines `kus0`, `kthem0` (the reading of the day, 0 for a pair never fought before) and `kday`, the day the count began. Every day, in `mod1440_wr_daily`: the reading minus the baseline, kept only when higher (a value that never falls). At the end, in `mod1440_wr_close`: one more reading, the higher of it and yesterday's is frozen on the finished row. So whether the game's value counts one war or every war between the two (the baseline), and whether it survives the peace or falls to 0 like `casualties` (the daily copy, at most a day lost), the row is right; the game check says which.

**The two ways weighed.** (A) `casualties_inflicted_by` per enemy: exact per pair, both sides, unaffected by wars that overlap or a war that ends while others go on; it misses the dead no enemy caused (attrition, weather, supply), which the game's war overview counts in a participant's casualties, and an enemy fought in two wars is told apart only by the baseline. (B) The daily rise of `casualties_k` given to the war of the day (D9's way): all causes, but exact only while one war runs; with two wars at once it cannot be split, on the day a war ends the fall hides the others' rise, and it says nothing of the enemy's dead by our hand. **Recommended: A** (decision 3); B is the fallback if the check shows A unusable. The campaign table keeps D9's all-causes total beside it.

**Reading a number from a trigger.** A trigger answers yes or no, so the number is searched: `meta_trigger` with `thousands > [N]` and N from a variable (`"[?wr_kn|1]"`), first upward from yesterday's value in doubling steps, then halving: 1 comparison on a quiet day, 6 to 10 when a front moves; a full search (about 17) only on the first reading. If the check shows `meta_trigger` cannot take a number so, a generated ladder of fixed thresholds (1K steps to 100K, 5K to 1M, 50K above, about 460, 9 comparisons deep) gives the value within 1%.

**Daily cost (rule 5):** per enemy of today two searches and one comparison of its head of government; with 25 enemies (Germany in 1942) about 50 to 500 trigger checks a day, in the daily round that already runs. Nothing is drawn from a loop.

**2. Leaders kept on the row (fault 2).** A row keeps the head of government of each side at the war's start and at its end, by place (X67), with his portrait and his ideology group:

- **At the start** (`mod1440_wr_open`): ours `lu0` = `country_leader`, `pu0` = `mod1440_gv_p` (the Government page's lookup, which runs daily), `gu0` = the ideology group (1 to 4, 0 other); theirs `lt0`, `pt0`, `gt0` read in the enemy's scope with `mod1440_p_leader`.
- **Every day while the war runs:** the enemy's `country_leader` is compared with `lt1`; on a change `lt1`, `pt1`, `gt1` are written and the portrait looked up once. So an enemy annexed at the end still has the leader of its last day.
- **At the end** (`mod1440_wr_close`): the finished row takes ours `lu1`, `pu1`, `gu1` of that day and theirs from `lt1`. Nothing of a finished war is looked up again, except the portrait tokens when the names' numbers move (SCR-076): then each is looked up again from the kept character, with the epoch stamp, as the Government page's heads are (`rulers_again`).
- The places go into `mod1440_ch_remap` (`in_array` for `mod1440_wr_lu0`, `_lt0`, `_lt1`, `mod1440_wo_lu0`, `_lu1`, `_lt0`, `_lt1`) and are marked in `mod1440_gv_marks`, marked E4.

**What the file shows** (decision 1): both when the leader changed, as two portraits "At the start" and "At the end" ("Today" for a war that runs); one portrait with "Throughout the war" ("At the start and today") when it is the same person. The party name cannot be frozen (a text of today), so a kept leader shows his ideology group's icon and word instead; the faction line goes (the enemies table is the side).

**Missing portraits.** (1) annexed enemies: fixed, the leader is kept. (5) today's lookups: fixed, kept at the time. (3) made-up leaders and (2) Road to 56's file portraits: no script can show them; (4) characters with no row: the tables can grow (`make_game_tables.py --mods`), outside this phase. Where no portrait can be named the box shows, by design, the country's flag (GFX_shield_medium at its own size, centred, a flag ignores scale) on a dark inset with the ideology icon under it, and the tooltip "No portrait the game can name" (the Yugoslav leader at the end in the file figure).

**3. Per war, not per enemy.** The game groups enemies into wars; script has no war object, but it can ask two countries whether they fight on the same side of a war (`has_war_together_with`, documented) and whether the player is the attacker against each (`has_offensive_war_with`). **Rule:** when a row opens, the enemy joins the war of the first open row whose enemy fights on its side and against whom the player has the same role (attacker or defender); otherwise it opens a war of its own. Each row keeps `grp`, the number (`id`) of its war's first row; `id` keeps its meaning (the officers' tallies `mod1440_ow_*` still point to rows). Weighed and dropped: the same start day and attacker (the Commonwealth joins days later, two wars declared on one day would merge); the war leader (no documented trigger or variable names it); the `enemies` of the first enemy (they span all its wars: the United Kingdom's include Italy and Japan). Edge: two enemies who are allies in a third, unrelated war against the player and declared separately would merge; the role test makes it rare.

**What the page does with it** (decision 2): the lists show one plate per war, named after its first enemy with "+12" for the others; a war is "of today" while any of its rows is open. Its figures are the sums of its rows. The file lists the war's enemies in a table (joined, how each ended, both sides' dead, states), and a click on one shows that enemy's heads of government. The list per war is built when the page shows and on a click (`mod1440_wr_show`, `mod1440_wr_card`: a walk over at most 240 rows, rule 5), into `mod1440_wv_*`; the open war's enemies into `mod1440_we_*`.

**4. What a row keeps, and the save.** **New parts at the end** (contracts): `WR_NEW_3` for today's rows: grp, how (1 we declared, 2 they declared, 3 joined, 0 not known), kday, kus0, kthem0, kus, kthem, lu0, pu0, gu0, lt0, pt0, gt0, lt1, pt1, gt1 (16); `WO_NEW_3` for finished rows: grp, how, kday, kus, kthem, lu0, pu0, gu0, lu1, pu1, gu1, lt0, pt0, gt0, lt1, pt1, gt1 (17). `cas`, `cas0`, `ecas0`, `ecas` stay in the save and are no longer shown. Two outcomes are added at the end of `OUTCOMES` and the dictionary of kept keys: 6 "We capitulated" (`has_capitulated` of the player at the end), 7 "We were made a subject" (`is_subject_of` the enemy).

**Cost:** about 520 bytes a row of today and 550 a finished row; a campaign like the user's (33 rows, 20 wars) about 30 KB with the list and the file's table, the worst case (40 open, 200 finished) about 200 KB, 0.2% of the user's 104 MB save (`work/save_cost.py`).

**Migration** (`mod1440_wr_grow`, once per save, honest about what is lost):
- grp: today's rows by the rule of part 3; finished rows with the same last day form one war (an enemy that left earlier stays a war of its own).
- Casualties of today's rows: baseline 0 for an enemy never fought before (then the whole war counts, from its first day), else the reading of the upgrade day and `kday` that day ("counted since" in the tooltip).
- Casualties of finished rows: **not recoverable from the old row** (`cas` is 0 or wrong, `ecas` is the enemy's whole loss). If the check shows `casualties_inflicted_by` survives the peace, an enemy fought once and not at war now gets its value read once; every other old finished row shows "—" with the tooltip "Not kept: this war ended before the record kept its dead" (decision 6).
- Leaders of today's rows: ours at the start from the Government page's heads since the record began (`mod1440_gv_rul`, by date); theirs at the start not known (the fallback box, "Not recorded"), at the end today's. Finished rows: ours at both ends from `mod1440_gv_rul` by date; theirs "Not recorded".

**5. The left column, 548 wide (the plates kept).** - **The campaign**, steel card 548x220 at 14,116, head 27: fourteen figures as a banded table, 7 rows of 24, two pairs of label (hoi_18mbs) and value (hoi_20b, right-aligned): Casualties, all wars (D9's `mod1440_h_cas_sum`, new); in wars of today (`casualties_k`); Casualties we inflicted (sum of `kthem`, new); Longest war; Our surrender; Convoys sunk; Prides of their fleet sunk — War support: casualties, convoys, bombing; Our pride of the fleet lost; the three Ace counters (contracts). Replaces the twelve tiles of 123x64 (262 high).
- **Wars of today**, steel 548x188 at 14,342: the game's `GFX_war_participant_entry` (531x41, red) at a pitch of 48, three visible, scrolls. Flag (41x26) and the first enemy's name in a fixed box of 162, "+N" for the others; the four dark slots: Days, Our dead, Their dead (hoi_20b, "2210.4K" is 59 px in 73), Surr. (the first enemy of the war that still fights). Column heads in the card's head band.
- **Finished wars**, steel 548x670 at 14,536: twelve plates visible, scrolls, newest first; slots Began (the year), Our dead, Their dead, End (the game's icon of the outcome, its word in the tooltip). Plate green when they gave up, blue for a peace, red when we gave up. One line of legend.
- A click on a plate opens its file; the chosen plate is lighter (PICK, as today).

**6. The file of a war, 1092x1090 on the war overview's frame (kept).** - **Top plate and band A:** "The war with Poland" (hoi_24header, 470 centred), the two flags on the rays; our name and "Poland +12" (hoi_24header, fixed 260; the first enemy alone for a war of one) and between them the dates and days.
- **Band B:** the track day by day with twenty marks, kept; its lines are now only those within the war's dates (today an enemy fought twice mixes both wars).
- **Panel heads:** "Our side" and "Their side", with the number of enemies when there are several.
- **Heads of government** at y 206: portraits 125x168 (two, or one and the twin text of 353), text column 216 wide in rows of 24: the country, "At the start", name, ideology icon and word, "At the end" or "Today", name, ideology. Theirs show the enemy chosen in the table (the first by default).
- **In this war** at y 386: a head strip and **4 rows of 24 on both sides, always full**. Ours: Casualties, by their hand; States taken; Victory points taken; Capitals taken (the war's capital lines in the territory log). Theirs: Casualties, by our hand; States taken from us; Victory points taken from us; and in row 4, for a war of one enemy, its surrender (today) or How it ended (finished: the outcome's word, which band A no longer carries), for several enemies Enemies who gave up "7 of 13". Our surrender leaves the file: it is not of one war, and the campaign table has it.
- **Below, from y 516, the file reads full for a war of one enemy and holds one of thirteen.** Ours: Our commanders in this war, 5 rows of 48 (portrait 34x46, name, rank, and three columns States, Points, Capitals) gathered over every row of the war; then In the War Diary from y 790, 10 lines of 24, with "All its lines" in its head strip. Theirs, **several enemies:** The enemies in this war, rows of 32, **5 visible** (scrolls): flag, name (fixed 120), Joined, End (the outcome's icon, or the surrender of one still fighting), Their dead, Our dead (hoi_20b, 68 and 64 wide), States taken : lost; the chosen enemy on the lighter plate; then "In the War Diary, continued" from y 710, 13 more lines. **One enemy:** the table, which would have nothing to choose, is hidden by a visible trigger on the number of the war's rows, and the diary continues from y 516 with 21 lines. So the file shows the newest 31 lines of a war of one enemy and 23 of a war of several, in one run, newest first, left column then right. A war of 2 to 4 enemies leaves 1 to 3 empty rows of the table (up to 96 px).

**7. Every value and the game's number it is checked against (rule 3).** - Our dead and their dead of a war with **one** enemy: the war overview's casualties of each participant while it runs (`war_ally_entry/casualties`); the difference is the dead no enemy caused, written down in the check. Several enemies: the sum against the side's `defender_casualty`/`attacker_casualty`, the same way. After the peace: the value of the day before, in the game check's log.
- Casualties, all wars: National Figures' "Casualties, all wars" (D9). In wars of today: the sum of the war overview's own casualties.
- Surrender: the war overview's capitulation bar of that enemy. Capitals taken: the war's "Capital taken" lines in the War Diary. How it ended: the outcome's line of the War Diary on the war's last day.
- Heads of government at start and end: the diplomacy view on those days; a change made by effect in the check (`mod1440_chk_*`).
- Joined, days, states and points: the War Diary's lines of that war (as today).
- The grouping: the war overview's attacker and defender lists of each war.

| Part | Current | Proposed |
|---|---|---|
| Our dead in a war | `casualties` - `cas0` at the peace: 0 after it; the whole country's loss before | `casualties_inflicted_by` from each enemy, kept daily, frozen at the end; the war's sum |
| Their dead | the enemy's whole loss since the start, to every war | by our hand, per enemy; a campaign total |
| Heads of government | today's, looked up when the file opens; none for an annexed enemy | kept at start and end with portrait and ideology; the flag when no portrait exists |
| A row of the lists | an enemy (the Allies: a dozen rows) | a war, "Poland +12"; its enemies in the file |
| List columns | Days, States, Points, Surr./End | Days/Began, Our dead, Their dead, Surr./End |
| Campaign figures | 12 tiles of 123x64 in a card of 262 | a banded table of 14 in 220 (two new: all wars, inflicted) |
| The file | leader, party, faction, 3 tiles each side; 6 commanders; 20 diary lines | leaders at both ends; 4 figures each side; 5 commanders; the enemies table of 5 rows (several enemies only); the newest 23 or 31 diary lines in two columns |
| Outcomes | 5 | 7 (we capitulated, we were made a subject) |
| Look | card (tiles, head plates) | steel cards in the left column; the frame and the war overview frame kept |
| A row in the save | 16 parts | 16 + 16 (today) / 16 + 17 (finished), about 0.5 KB a row |

Additions, each with the row of "What a redesign can add" or the register id that allows it:

- Both sides' dead per enemy and per war (New live values in a scripted GUI (What a redesign can add); `casualties_inflicted_by` (documented trigger, triggers_documentation.md:2069) read by `meta_trigger` (SCR-054))
- One row per war, its enemies in the file (`has_war_together_with`, `has_offensive_war_with` (documented triggers); a scripted list from an array (A table ... sorted by a click; X10, X36))
- Heads of government kept at the start and end of a war (Characters kept by place (X67, X66: `mod1440_ch_remap`, `mod1440_gv_marks`); portraits by the table (SGUI-028), stamped (SCR-076))
- The flag in place of a portrait that cannot be named (An icon whose image is `[X.GetFlag]` (`flown()`, X40), at its own size)
- The campaign as a banded table with two new totals (Stat rows as a table (Design Language, Tables); D9's `mod1440_h_cas_sum` (X78), read only)
- "All its lines": the War Diary filtered to the chosen enemy (A scripted button that changes its page (rule 1; E1's country filter, `WD_COUNTRY_FILTER`))
- Outcomes "We capitulated", "We were made a subject" (`has_capitulated`, `is_subject_of` at the end; kept keys (`kept_tokens()`, SCR-076))

Open until the game shows it:

- casualties_inflicted_by: in Germany's scope with opponent POL, Germany's dead by Poland's hand; in Poland's with opponent GER the reverse; the same numbers as the war overview's casualties of each participant in a one-enemy war (the difference: the dead no enemy caused).
- casualties_inflicted_by after the peace: kept or 0; and a second war with the same enemy: starts from 0 or from the first war's value.
- meta_trigger with a number from a variable: `thousands > [N]` with N = "[?wr_kn|1]" answers right, also with a decimal; no error.log line.
- has_war_together_with between two enemies of one war (Poland and the United Kingdom: yes) and of two wars (the United Kingdom and the Soviet Union: no); has_offensive_war_with for a country that joined a war the player declared.
- on_war_relation_added for a country that joins a war: does it fire, and which is ROOT.
- A kept head of government of a country that was annexed: his name and kept portrait still show (X34 has been seen for countries, not for characters).
- The war plates at a pitch of 48, the outcome icons (the surrender icon's frame 2 for "we capitulated"), the flag box in a portrait's place.
- The daily round with 25 enemies: no stutter (game.log time stamps around mod1440_wr_daily).

Figure groups of the design page: page, file, lists.
<!-- end generated: proposal -->

## Build

<!-- generated: build (tools/phase_notes.py; edit the handoff file, not this) -->
Status: built and checked by render and tests; not seen in game (by builder-script).

**What was built.** The war record is refactored and the Wars page redesigned in tools/build_records.py (wars(), wars_script(), the WR_/WO_/WF_ constants, the Wars scene). Each enemy's row now keeps both sides' dead from casualties_inflicted_by (kus, kthem; searched through meta_trigger, read daily, never falling, read once more and frozen at the peace), both heads of government at the war's start and end with portrait and ideology group, and the war it belongs to (grp, grouped by has_war_together_with and the same role); a save's existing rows are migrated once in mod1440_wr_grow. The page draws one war plate per war in steel cards (the campaign as a banded table of 14, Wars of today, Finished wars), and the file shows the leaders at both ends (one portrait when the same person, the flag box when the game names no portrait), four figures per side, five commanders, the enemies table (several enemies only) and the war's newest War Diary lines in one run over both columns (31 or 23), with 'All its lines'.

**Deviations.**

- The commanders' column heads States / Points / Capitals stand over their values (x 334, 396, 458 in the file), 22 px left of the layout's: At the layout's place 'Capitals' ran past the strip's right end and the heads stood off their columns; layout.json (and work/layout-file*.json) changed to match.
- The enemies table's outcome column is headed 'End' (layout: 'Surr.'), and 'Their dead' is 76 wide at x 296 (layout 68 at 302): The column shows the outcome's icon for an enemy that left the war and the surrender only for one still fighting (the design's own words); 'Their dead' in hoi_18mbs is 72 px and was cut at 68. layout.json changed.
- Dates in the file (the track's ends, the War Diary lines, Joined) are written '1942.5.12' (GetDateStringNoHour), not '12 May 1942': The game's short-month date carries the hour (' 12:00, 12 May, 1942', SCR-014/X35) and is cut in the 86 and 80 px boxes; no date function of the game gives '12 May 1942'.
- A War Diary line about a country and no place (War declared on, Capitulated:) names the country in the place column as plain yellow text (mod1440_wr_ln_b), not on a camera button: A war of several enemies needs to say whom the line is about (the design's figures show the name there); a country is no place to move the camera to. A new part 'b' of the file's line arrays, not of the save's rows.
- The kept heads of government are marked for the remap (mod1440_ch_mark) when a row writes them (open, close, a daily change, the migration), not in mod1440_gv_marks: mod1440_gv_marks runs every day; marking up to 7 places on 240 rows each day is a loop the page does not need (rule 5). mod1440_ch_remap puts right mod1440_wr_lu0/lt0/lt1 and mod1440_wo_lu0/lu1/lt0/lt1 as designed.
- casualties_inflicted_by is asked as meta_trigger = { text = { [V] = { casualties_inflicted_by = { opponent = [O] thousands > [N] } } } V = "[?mod1440_wr_kv.GetTag]" O = "[?mod1440_wr_ko.GetTag]" N = "[?mod1440_wr_kn|1]" } (both countries as tags, the documentation's own form), searched in 0.1K steps: doubling up from yesterday's reading, then halving: The design named the search, not the text; the documentation's example passes the scope as a tag placeholder, which keeps the trigger free of ROOT/PREV (ROOT is the attacker in on_war_relation_added for a war declared on the player). A quiet day costs 2 readings per side and enemy.
- mod1440_wr_close no longer moves the old selection (mod1440_wr_sel_kind/_i); the page chooses by war (mod1440_wr_sel_g) and enemy (mod1440_wr_sel_e): A war's plate can move from today's list to the finished list when its last enemy leaves; a selection by the war's number survives that. A save's old selection falls back to the first war.
- tools/render_gui.py takes a list of frames per widget (one per row) in a scene's 'frames': The finished wars' plates are green, blue or red by row (frame = v); the renderer drew every row in one frame. A marked E4 round 2 change, backwards compatible.
- Gate B finding (orchestrator, 2026-10-29): the tooltips of the file's two casualty rows (MOD1440_WR_C_KUS_TT, MOD1440_WR_C_KTHEM_TT) named the script trigger casualties_inflicted_by; they now say 'The dead this war's enemies caused us' / 'The dead we caused this war's enemies', counted each day while it runs and once more at its end, without the dead no enemy caused (attrition, weather): A player-facing text uses the player's words, not the script's; fixed in tools/build_records.py (dead_tip), regenerated, build_managers.py --check and lint_gui clean.

**Fallbacks.**

- If meta_trigger does not take the placeholders: error.log names meta_trigger, a '[N]', '[V]' or '[O]', or the readings stay 0 in a war with dead (mod1440_chk_wr_log): Replace the search in mod1440_wr_kread by a generated ladder of fixed thresholds (1K steps to 100K, 5K to 1M, 50K above, about 460, 9 comparisons deep) inside the victim's scope with opponent = PREV, as design.json part 1 names; if only the tags fail, run the meta_trigger in the victim's scope (var:mod1440_wr_kv = { ... opponent = [O] }) and keep N.
- If casualties_inflicted_by is unusable (an unknown trigger, or a value far from the war overview's casualties of a one-enemy war): Fallback B of decision 3: the daily rise of casualties_k given to the war of the day (ours only, D9's way), kthem left as 'not kept'; the parts kus/kthem keep their meaning.
- If casualties_inflicted_by falls to 0 at the peace: Nothing to change: the daily copy (kus/kthem never fall) holds the value of the day before; write the finding into the register. The migration's 'value read once for an enemy fought once' then gives the dash, as decision 6 says.
- If casualties_inflicted_by counts every war between the pair, not this one: Nothing to change: the first day's reading is the base (kus0, kthem0); write the finding into the register.
- If Enemies of one alliance war stand on separate plates (has_war_together_with or has_offensive_war_with does not hold as expected, mod1440_chk_ally_join): Group in mod1440_wr_open by the war's first enemy's faction or by the same day and role; if neither holds, grp = id (a plate per enemy as before), the rest of the page unchanged.
- If on_war_relation_added does not fire for a country that joins a war: Nothing to change: the daily comparison opens its row the next day with how = 3 and groups it.
- If A kept head of government of an annexed country shows no name or a wrong one: Show 'Not recorded' for a kept leader whose country no longer exists (a visible trigger on the row's enemy), and record the fact.
- If The steel cards are drawn wrong (a seam, the wrong size) or the war plates sit off their 48 pitch: Remake gfx/interface/mod1440/wr_*.dds with python -I tools/stretch_background.py --only wr_; WR_ROW and the list's slot pitch in tools/build_records.py.
- If The daily round stutters with many enemies (game.log stamps around mod1440_chk_kread_time): Read each row's dead every second day by its id's parity, or only while the page is open and once at the end.

**Not seen in game.**

- Whether casualties_inflicted_by counts only this war, every war between the pair, and whether it survives the peace (open in the design; the checklist asks it of mod1440_chk_wr_log before and after a peace)
- meta_trigger with placeholders filled from variables and tags ([?var|1], [?var.GetTag]); its cost per reading
- has_war_together_with and has_offensive_war_with grouping several enemies of one war, and a joiner's role
- The heads of government kept on a row after a leader change during and after a war; their portraits as kept text keys; the flag box for a leader with no portrait
- The migration of a save of the build before (mod1440_wr_grow for WR_NEW_3 and WO_NEW_3): grouping by the last day, the dash, the heads from the Government page by date (dates compared as values)
- The two new outcomes 'We capitulated' (has_capitulated) and 'We were made a subject' (is_subject_of) on their red plate
- The steel cards' bitmaps (GFX_1440p_WR_campaign, _today, _done) and every new sprite of the E4 round 2 block in the game
- The year a finished war began (its first day's number / 365, rounded down)
- The War Diary lines of a war limited to its dates and its enemies; 'All its lines'
- Every value against the game's own number (rule 3): the dead against the war overview, Casualties, all wars against National Figures

Shared files touched: `interface/mod1440_ui.gfx`, `tests/ScriptedGuis.Tests.ps1`, `tools/check_effects.py`, `tools/render_gui.py`, `tools/stretch_background.py`, `tools/design_exceptions.json`.

**Game check.** `tools/Invoke-GameCheck.ps1 wars`

Checklist for the game checker:

1. The page in the steel look: three steel cards in the left column (The campaign 548x220, Wars of today 548x188, Finished wars 548x670), 6 apart, each with a head band of 27 holding its title and the column heads (Days / Our dead / Their dead / Surr.; Began / Our dead / Their dead / End); the window's ground, title strip and tabs unchanged; the Wars tab's tooltip 'One row per war, its enemies joined'
2. The campaign table: 14 figures in two columns, bands on rows 2, 4, 6. Compare 'Casualties, all wars' with National Figures' 'Casualties, all wars'; 'in wars of today' with the war overview's casualties of your side; Our surrender with the war overview's bar; 'Casualties we inflicted' with the sum of Their dead over both lists
3. Declare war on Poland (effect mod1440_chk_war), run 3 days: one red plate under Wars of today with Poland's flag and name, Days 3, Our dead and Their dead in K with one decimal, Surr. as the war overview's capitulation bar of Poland; 'At peace.' gone
4. Grouping (has_war_together_with): effect mod1440_chk_ally_join (the United Kingdom and France join Poland's side), run 1 day: still ONE plate, 'Poland +2'; effect mod1440_chk_wr_log: game.log 'MOD1440 wr: wr' lines give POL, ENG and FRA the same grp and role 1. Then mod1440_chk_war2 (Czechoslovakia, a war of its own): a second plate, its own grp
5. The file of the war: 'The war with Poland', both flags, 'German Reich' and 'Poland +2' in hoi_24header, '1 January, 1936 - today - N days'; the track and its marks; Their side '3 enemies'; the enemies table, 3 rows (flag, name, Joined, surrender %, Their dead, Our dead, States), Poland on the lighter band; click the United Kingdom: its row lights and Their side shows its head of government with his portrait
6. Casualties (casualties_inflicted_by, faults 1 and 3): after days of fighting, mod1440_chk_wr_log: each row's kus/kthem and 'now' readings in thousands; compare a one-enemy war's Our dead and Their dead with the war overview's casualties of each participant (the difference is the dead no enemy caused) and write both numbers down; the plate, the file's 'Casualties, by their hand / by our hand' and the enemies table agree with the sums
7. meta_trigger with numbers from variables: after Reloading Database and a daily round, error.log has no line about meta_trigger, casualties_inflicted_by, a '[N]', '[V]' or '[O]' placeholder or a parse error; mod1440_chk_kread_time: the time of 100 full readings between two game.log lines
8. The peace (mod1440_chk_peace: white peace with Poland), run 1 day: the war moves to Finished wars on a blue plate with the peace icon (or Poland's row leaves a war that goes on); Our dead and Their dead keep the values of the day before, NOT 0 (fault 1); mod1440_chk_wr_log after the peace: the 'now' reading says whether casualties_inflicted_by keeps its value after a peace or falls to 0 (write it down)
9. A second war with Poland after the peace (mod1440_chk_war again, 2 days): a plate of its own; its dead count from its first day (kday and the base in the log); the first war's file keeps its numbers, and its War Diary lines stop at its last day (designer's fault 3)
10. Kept heads of government (fault 2): during a war, mod1440_chk_leader_change (Poland's head of government retired), run 1 day: mod1440_chk_wr_log shows lt0 the head of the first day and lt1 the new one; the file shows 'At the start' and 'Today', two portraits. After the peace, mod1440_chk_leader_change_us (ours retired), run 1 day: the finished war still shows our head of that time, 'Throughout the war', one portrait
11. An annexed enemy (mod1440_chk_war2, mod1440_chk_annex, 1 day): a green plate with the annex icon; its file still shows Czechoslovakia's head of government at the start and the end with his portrait (no 'This country is no more')
12. The flag box: a head of government the game has no portrait for shows the country's flag (82x52) on the dark inset with the ideology icon under it, tooltip 'No portrait the game can name'
13. A finished war of one enemy: no enemies table; the War Diary runs from the left column (10 lines) into the right one (up to 21 lines, 'In the War Diary, continued'); 'How it ended' in the fourth figure row with the outcome's words
14. 'All its lines' in the War Diary strip: the War Diary opens filtered to the chosen enemy ('<country>: lines 1 - N of N')
15. A place in the file's War Diary is a button: the camera moves to it and the Records close; a line about a country names it in the place column without a button
16. Migration of an existing save: effect mod1440_chk_old4 (the rows as the build before left them), open the Records: game.log 'the rows of wr ... wo were given their wars, casualties and leaders'; mod1440_chk_sizes4 logs every new part as long as the rows; the old finished wars show the dash in both dead slots (tooltip 'Not kept'), an enemy fought once and not at war now may show the game's value instead; rows that ended on the same day are one plate; our heads come from the Government page, theirs 'Not recorded' at the start
17. The lists scroll with the wheel: Finished wars past 12 plates, the enemies table past 5 rows
18. error.log: no line that names the mod, no 'invalid scope for var', no 'Could not find sprite type' (GFX_1440p_WR_*, GFX_1440p_SG_inset_125x168), no unknown trigger or effect has_war_together_with, has_offensive_war_with, casualties_inflicted_by, is_subject_of

**Tests.** build.ps1 -Check wars (after fix round 1, tables refreshed for 1.19.4.0): 276 passed, 0 failed, 68 skipped; build_managers.py --check and lint_gui clean.

Candidate engine facts (for the orchestrator at the close):

- Candidate (from this repository's hook comments, not new to the engine): in on_war_relation_added for a war declared on the player, the mod's effect runs inside FROM = { } while ROOT is the attacker; a scripted effect that names the player there must use THIS. The readings name THIS for that reason.
- Candidate, to be confirmed by the check: meta_trigger placeholders take a number formatted from a variable ('[?var|1]') and a tag from a country variable ('[?var.GetTag]'), as vanilla's meta_effect takes '[?skoda_optimization_tier]' (CZE_scripted_effects.txt:446); its cost per call is unknown.
- Candidate, to be confirmed: casualties_inflicted_by semantics (one war or all between the pair; kept or 0 after the peace), read by mod1440_chk_wr_log before and after mod1440_chk_peace.
- Not an engine fact, for the orchestrator: the installed game is now 1.19.4.0; register records confirmed on 1.19.3 count as provisional until re-seen.
<!-- end generated: build -->

## Game checks

- 2026-10-29, the user's own test, an existing save of 1945 (Kingdom of France; screenshot `scratch/phases/E4/user-test-2026-10-29.jpg`, not in the repository): the migration ran (finished wars grouped into plates, the dash in both dead columns, their heads "Not recorded", ours from the Government page). The per-enemy dead read through `meta_trigger` give values in game (SSSR +6: 7.7K / 167.6K; United Kingdom +25: 306.5K / 863.3K). Rule 3: "Casualties we inflicted" 1030.9K is the sum of Their dead (167.6K + 863.3K); "in wars of today" (the game's `casualties_k`) 328.3K against the sum of Our dead 314.2K, 14.1K the dead no enemy caused, as designed. Not yet seen: the value after a peace, a second war with the same enemy, a leader change. Findings: the Wars tab counts enemies ("33 at war") where the page counts wars (2); both heads "Not recorded" draw two flag boxes where one would do.

## Fix rounds
