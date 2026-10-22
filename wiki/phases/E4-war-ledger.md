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

## Game checks

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
