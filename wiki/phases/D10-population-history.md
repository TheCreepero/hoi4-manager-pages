# Phase D10: State population history

The population of each state month by month, on the States page. Opened on 2026-10-26 at the user's request. The page is described in [Scripted GUIs](../Scripted-GUIs.md), "States".

## Scope

- Page: States (D3), docked to Construction (`mod1440_states`, `tools/build_managers.py` section States). No vanilla window is overridden.
- What the game does not show: any history of a state's population. The state view gives today's number only.
- The user's words (2026-10-26): "A screen (or an addition to the "States" view) where I can see the historical population development of each state." They play with Better Mechanics : Devastation Overhaul, which lowers a state's population from weekly hooks (civilian casualties, refugees, sieges, strategic bombing, occupation deaths, nukes, assimilation) through `add_manpower` in state scope; in vanilla the number rarely moves.
- User decision (2026-10-26): every state of the map is read once a month, not only the player's.
- Value read: `state_population_k` (SCR-003).
- Out of scope: the causes of a change (another mod's own variables, rule 6); the population of states the player does not control on the page (rule 2).

## Roles and handoffs

- Handoff folder: `scratch/phases/D10/` (not in the repository)
- Builder: `builder-script`, the only builder of this mod (a scripted page)
- Path: full, with the designer (a new graph on the page and a monthly round over every state)
- Design page: https://claude.ai/artifact/TNeJCnJJiqG4KMFw2FTgtJ (round 1, 2026-10-26; passed gate A the same day: lint 0 errors, 0 of 106 texts under the contrast floor)
- Layout file: `scratch/phases/D10/layout.json` (the mock-ups and the build are made from it)
- Contracts written (hotkeys, shared rows, shared files): yes, `scratch/phases/D10/contracts.md`
- Worktrees: main tree

## Inventory

- References: `reference/mod/states.jpg` and `states-panel.png` (the page before the redesign of 2026-10-16), `reference/vanilla/construction.jpg`; `reference/mod/national_figures*` for the History graph.

## Proposal

Generated from `scratch/phases/D10/design.json` by `python -I tools/phase_notes.py D10` (the orchestrator runs it at every gate). Write under the markers only what the design file cannot hold.

<!-- generated: proposal (tools/phase_notes.py; edit the handoff file, not this) -->
Every state of the map is written down on the first of each month (its `state_population_k`), ten years at most, in one round a month for the whole game. The States page gets a Population view: a switch in the chosen state's card replaces the three right cards of the band with a graph card, History's columns for that state with a table of its figures beside them, zoomed in by default so that a 1 to 3% fall fills the chart. A sortable column In a year in the table finds the hardest-hit states in one click. Verdict: refine; effort: L: a monthly round over every state with a global guard and its on_startup call, a second scripted GUI for the graph card with three grids of column widgets and their sprites (152 steps at 22, 8 and 4 px, two colours), the drawing effect, the table column with its sort and total, the hiding triggers of the three cards, check effects that fill and time the record, and the scene.

What vanilla does badly: Neither vanilla nor the States page has any history of a state's population: the state view and the People column give today's number only. With Devastation Overhaul a state loses people every week, and the only way to see how much is to remember the number. The page cannot tell which of the player's states lost the most, short of clicking each one.

**Where the history stands: a Population view of the band.** The band under the table keeps its place and size (page 7,964, 1458x232). The state card (430) stays in both views. A switch **Population** (`GFX_sort_button_120x29`, frame 2 when on) stands in the state card's bottom row, page 147,1153, between People and Show on map. On, the three right cards (Building Slots, Buildings, Occupation) give way to one **graph card** of exactly their place, page 449,964, 1016x232; off, the cards are back. The view is kept per country (`mod1440_pop_view`), so after the first switch every click on a row redraws the graph: one click a state.

The graph card is a scripted GUI of its own, `mod1440_states_pop`, docked to `construction_tab` at 712+449, 964 and visible while the page is open and the view is on (a container in the page cannot be hidden, X15). The state-scoped texts and icons of the three cards in the list-of-one row and the country's modifiers get `NOT = { pop view }` in their triggers, so nothing shows through it.

**The graph card.** Title **Population** (`hoi_24header`, the page's card font) at 463,972 with `in thousands` in grey beside it. Right of it the range buttons of History, `GFX_sort_button_100x29`: 2 years at 683, 5 years at 787, 10 years at 891, and **Zoom in** (`GFX_sort_button_140x29`) at 995, all at y 972; until the player picks a range the graph takes the shortest that holds every month written down.

The chart: History's frame (a card plate) at 527,1012, 608x172, columns from 531,1012 in an area of 600x152 with an axis of 20 under it; bands on the second and fourth quarter. One grid per range: 24 columns of 22 on 25 px steps, 60 of 8 on 10, 120 of 4 on 5 (24x25 = 60x10 = 120x5). Heights 0 to 152, one frame a pixel (History's H_STEPS pattern). The scale: five values at the quarters, `hoi_16mbs`, right-aligned in 463..519. The years under the first month of each year, ten texts the script moves (X4).

**Zoom in is on by default** for population (from zero a 2% fall is 3 px): the columns start at the lowest month, and the lowest keeps a 4 px sliver. The column tooltip gives the date and the value.

**The figures: a banded table beside the chart.** At page 1151,972, 300 wide: a head bar of 30 (People, %, Month in `hoi_18mbs`) and seven rows of 24 with a band on every second: Latest, In a month, In a year, Since first, Highest, Lowest, Yours since. Columns: the label at 1159 (76), People at 1235 (72, right, `hoi_20b`), % at 1319 (50, right), Month at 1371 (72, right, grey). A change is red when it falls and green when it rises; Month is the month the row's number refers to (the month compared with, for a change). Yours since gives the day the state came into the player's hands from the War Diary's record on the state (`mod1440_sr_date`, E1), or a grey dash for a state held since before the record.

**The months before the player held it.** A state keeps its variables when it changes hands, so the graph shows its whole record. The months before it came into the player's hands are drawn in the unit list's preparing bar (`gfx/interface/unitlist_bar_prepare.dds`, blue-grey), from that month on in History's organisation bar (`navieslist_bar_org.dds`, green), with a 2 px line (`unit_xp_bar.dds`, yellow, as the label Yours since) at the first month in the player's hands, moved there by script. The index is found when the graph is drawn: the first month whose date is not before `mod1440_sr_date`. Rule 2 holds: only states the player controls are listed; the number before the conquest is the state's own population, which the game shows for any state.

**The table: a column In a year.** STATE_COLUMNS: the nine building columns 52 -> 46, the seven resource columns 56 -> 54, and a column **In a year** of 68 after People, in the people group, which gets a caption **Population** over it like the other groups. The row stays 1414 wide and the page 1472 (the page cannot grow: the theatre box stands about 60 px to its right). Head icons: buildings at x+9 (was +12), resources at x+15 (was +16). The cell is the state's change over the last twelve months in percent (`mod1440_pop_dy`, worked out in the monthly round), red for a fall, green for a rise, empty when 0 or with fewer than 13 months. The first click sorts the largest fall first (the sort key is the fall, the cell the change), a second turns it. The totals bar gives the change of all listed states together (their summed population now against twelve months ago).

**The record and the monthly round.** Storage: one array per state, `mod1440_pop_k`, one value a month; one array of the months for all, `global.mod1440_pop_date`, with `global.mod1440_pop_year` for the year marks. After 120 months the oldest goes from each. 1143 states x 120 = about 137,000 numbers at ten years with Road to 56.

Once a month in all: an effect `mod1440_pop_round` is called from the mod's on_monthly block (each human player's) and from on_startup (once, outside `every_country`). It runs only when `global.num_days` is at least 20 past `global.mod1440_pop_day`, and sets that stamp first, so with several players, or an on_monthly that fires on different days for different countries, the round runs once a month. It then does, for `every_state`: add `state_population_k` to `mod1440_pop_k`, forget the oldest past 120, and set `mod1440_pop_dy` from the value twelve months before. A state with a shorter array than the dates (none on a fixed map) is padded with -1 at the front, as History pads its newer series.

Drawing (rule 5): `mod1440_pop_draw` copies the chosen state's months in the range into the country's column arrays, finds the scale, the figures and the taken index, when a row is clicked, the view switched, a range or Zoom in clicked, and after the monthly round while the page is open. Never in a trigger drawn each tick.

**What does not change.** History and National Figures, their script and localisation (no country series unless the user asks, see decisions); the title strip and its choices; the state card's other lines; the 26 rows of the table; the hotkeys (none new: Shift+M keeps folding the page).

| Part | Vanilla | Current | Proposed |
|---|---|---|---|
| A state's population | today's number in the state view | today's number in the People column and the state card | the same, and every month since 1936 (ten years at most) in a graph |
| Band under the table |  | page 7,964, 1458x232: state 430, slots 300, buildings 404, occupation 288 | the same in the cards view; in the Population view the state card and a graph card 1016x232 at 449,964 |
| View switch |  |  | Population, GFX_sort_button_120x29 at 147,1153, frame 2 when on, kept per country |
| Chart |  |  | frame 608x172 at 527,1012; columns 600x152; 24x25, 60x10 or 120x5 px; axis 20; scale 56 px on the left; Zoom in on by default |
| Figures |  |  | banded table 300 wide at 1151,972: head 30, seven rows of 24, four columns 76, 72, 50, 72 |
| Table columns |  | buildings 9x52, resources 7x56, People 84 | buildings 9x46, resources 7x54, People 84 and In a year 68; row 1414, page 1472 unchanged |
| Record |  |  | every state, each month: mod1440_pop_k (state), global.mod1440_pop_date and _year; 120 months kept |

Additions, each with the row of "What a redesign can add" or the register id that allows it:

- The graph of a state's population month by month ('A graph over time' (X17): script writes the values down each month; each column is a progress bar it fills)
- Column In a year, sorted by a click ('A table of states or generals, sorted by a click' (X10, X22))
- The Population switch and the range and zoom buttons ('New buttons that do something': in a scripted GUI, a scripted button runs an effect that changes its page (X3, rule 1))
- Year marks and the line of the month taken, moved by script (SGUI-004 (X4): an `x` under properties follows a variable)
- The graph card as a scripted GUI of its own over the band (SGUI-013 (X15): a group of widgets is hidden as a scripted GUI of its own, through its visible block)
- A monthly record of every state ('New live values the screen does not show today' (X1, X2, X20): variables and arrays on the state, SCR-045, SCR-025 (arrays kept on a scope))
- Caption Population over the people group ('Fixed text and icons'; text of the mod in localisation)

Open until the game shows it:

- The time of the monthly round over 1143 states with Road to 56 and over 1081 in vanilla, measured with a check effect that runs it (and one that fills 120 months for every state), paused, without letting a month pass.
- The save's growth with 120 months for every state: a save is not allowed in a check, so the user's own game, or a check effect and a save the user makes.
- Whether `mod1440_states_pop`, a second scripted GUI on construction_tab, is drawn above the page `mod1440_states` (no register fact on the order of sibling scripted GUIs). If it is drawn under, the fallback is to take the three right cards out of the page into a scripted GUI `mod1440_states_cards` of their own, so that the two views never overlap.
- That the state-scoped texts of the three cards hide under the graph card through their triggers, and nothing shows through its card plate.
- `global.num_days` read in the round's guard (documented in the game's dynamic_variables_documentation, not yet used by the mod) and the round running once with on_monthly per country.
- The column colours: unitlist_bar_prepare.dds and navieslist_bar_org.dds as progress bar fills at 4 px, and unit_xp_bar.dds as a 2 px line.
- A month written by the real monthly hook (a check stays in January 1936): the user's game, as History's.

Figure groups of the design page: band, page, graph.
<!-- end generated: proposal -->

## Decisions

- 2026-10-26: the phase opened; every state of the map is read once a month (user).
- 2026-10-26: gate A passed (lint 0 errors, 0 of 106 texts under the contrast floor; the cited register ids checked). The draw order of two scripted GUIs on one tab is not in the register: an open question for the game, with the designer's fallback.
- 2026-10-26, the user on the design page: "Proceed with the recommended options." So: (1) a Population view of the band, the switch in the state card swapping the three right cards for a graph card; (2) a table column In a year, the change over twelve months in percent; (3) every month for every state, 120 values a state; (4) Zoom in on by default; (5) every month shown, those before the state was the player's in another colour with a line at the month taken; (6) no country series, National Figures untouched; (7) the card look kept, no move to steel.
- 2026-10-26: gate B passed. `build_managers.py --check` current, `lint_gui.py` 0 errors (one new exception with its reason, the graph's quarter bands as History's), the diff of every generated file read, `mod1440_figures.gui` and History's script unchanged, 79 new keys in each of the ten languages, the build renders match the mock-ups. The builder's deviations accepted: the three right cards in a scripted GUI of their own from the start (no overlap with the graph card), the month taken found by day numbers (SCR-014), Highest and Lowest over the state's whole record, the sort numbers of Compl. and Resist. moved by one. The design page carries the build renders (version 2).

## Build

Generated from `scratch/phases/D10/build/build.json`: what was built, deviations, fallbacks, not seen in game, the game check line and the checker's checklist, the tests.

<!-- generated: build (tools/phase_notes.py; edit the handoff file, not this) -->
Status: built and checked by render and tests; not seen in game (by builder-script).

**What was built.** Every state of the map is written down once a month (mod1440_pop_round: guarded by global.num_days 20 days past global.mod1440_pop_day, called from each player's on_monthly after History's record and once from on_startup outside every_country): mod1440_pop_k per state, 120 months kept, the months for all in global.mod1440_pop_date, _year and _days, a state padded with -1 at the front, and its change in a year (mod1440_pop_dy, _fall, _ya, _last) worked out in the same round. The States page has a Population switch in the state card (frame 2 when on, kept per country): the graph card mod1440_states_pop (1016x232 at page 449,964) with 2/5/10 years, Zoom in on by default, three column grids (24x22 on 25, 60x8 on 10, 120x4 on 5, 152 steps), the scale, ten year marks and the yellow line of the month taken moved by script, the months before the state was the player's in the preparing colour, and the banded table of seven figures; drawn only by mod1440_pop_draw (row click, switch, range, Zoom in, the daily list while open, after the round). The table has building columns of 46, resource columns of 54, a column In a year of 68 under a caption Population (red fall, green rise, sorted largest fall first) and its total in the totals bar; the row stays 1414 and the page 1472. History, National Figures and their output are byte-identical.

**Deviations.**

- The three right cards (Building Slots, Buildings, Occupation) and the country's modifiers are a scripted GUI of their own, mod1440_states_cards, with their own list of one row (mod1440_states_cards_row, same array mod1440_st_card), shown while the view is off; the graph card mod1440_states_pop shows while it is on. The design's fallback, built from the start (the brief allowed it).: It cost the same as the hiding triggers: the cards' state texts were already a list row, and only the modifiers and the slot bar's property moved. It removes about seventy NOT-pop-view triggers and the open point that the cards' texts might show through the graph card; the two views are never drawn together. Both windows still lie over the page, so the draw order of sibling scripted GUIs is still the open point (see fallbacks).
- The state card's People text is 58 wide (was 160; layout said 72); layout.json changed with the reason.: A box of 72 from page x 87 runs 12 px under the Population switch at 147; 41250K in hoi_18mbs is 52 px.
- The graph card's title box is 118 wide (layout said 200); layout.json changed with the reason.: 200 would run under 'in thousands', which starts at card x 132.
- The month taken is found by day numbers: a third global array global.mod1440_pop_days (global.num_days of each month) is kept beside the dates and years and compared with the state's mod1440_sr_day.: The design compared dates with mod1440_sr_date; the raw value of a date is no day count (SCR-014), so an order of two dates is not sure. The day numbers are 120 more numbers in all.
- Highest and Lowest in the figures table are over every month written down for the state (as Since first), not over the range on the graph as History's plates are; the scale gives the range's extremes.: The design does not say; the table stands for the state's record and should not change with the range button.
- Percentages are worked out as (change x 10 / base) x 10, in steps of 0.01 and shown with one decimal (cut, X65).: A variable holds about 2.1 million: a large state's change times 100 could pass it.
- In a year takes sort number 19; Compl. and Resist. move from 19 and 20 to 20 and 21.: STATE_COLUMNS numbers its columns in order. A save whose page was sorted by Compl. opens sorted by In a year until the next click; nothing else depends on the numbers.

**Fallbacks.**

- If After the switch the band's right part shows the page's empty ground, and in the cards view the three cards are missing too (both sibling scripted GUIs drawn under mod1440_states): In states_table() put the scripted_gui blocks of mod1440_states_cards and mod1440_states_pop before mod1440_states (declaration order is the likely key) and check again; if they stay under, the page window ends above the band (height 952) and the state card becomes a third window of its own, so that no window of the page lies under the two views.
- If The graph card shows over the cards view only in part, or the cards view shows through its card plate: Cannot happen with the cards in their own window; if it does, the visible blocks are not read again: add mod1440_st_dirty to the switch (it is) and check that both windows have dirty = mod1440_st_dirty.
- If After effect mod1440_chk_pop_months the graph says nothing is written down, while game.log says 120 months (a global array cannot be read by for_each_loop, or a temp array not indexed by a temp variable): Copy the three global arrays into arrays of each human country in mod1440_pop_month (every_country is_ai = no) and read those in mod1440_pop_draw; and/or keep the state's months in a country array instead of the temp array pd_all.
- If The yellow line of the month taken is not drawn, or striped (corneredTileSpriteType with tilingCenter = no does not stretch): Declare GFX_1440p_SG_line_2x152 as a progressbartype with unit_xp_bar.dds as both textures (a progress bar stretches its texture, as the columns show).
- If The preparing colour and History's green are hard to tell apart at 4 px: Use navieslist_bar_str.dds (History's brown of casualties) or unitlist_bar_prepare_bg.dds for the months before; the line and Yours since stay.
- If The round over every state takes a noticeable time (game.log of mod1440_chk_pop_round10 over a second for ten months with Road to 56): It runs once a month only; if a stutter is felt on the first of a month, split every_state into two halves by state number on two days, each with its own stamp.
- If on_monthly does not reach mod1440_pop_round, or runs it for each player (two months on one day in multiplayer): The guard's stamp global.mod1440_pop_day: read it in game.log with mod1440_chk_pop_twice; if global variables are not set from on_monthly, keep the stamp on the first human country instead.

**Not seen in game.**

- Whether mod1440_states_pop and mod1440_states_cards, two more scripted GUIs on construction_tab, are drawn above the page mod1440_states (no register fact on sibling order)
- A month written by the real on_monthly (no check lets a month pass): the user's game
- The round once a month in multiplayer (several human players)
- The time of the round over 1081 states (vanilla) and 1143 (Road to 56); the save's growth at ten years (to be measured in the user's game, or with mod1440_chk_pop_months and a save the user makes)
- global.mod1440_pop_* read by for_each_loop, temp arrays indexed by temp variables in the drawing (temp arrays are used by the Records, global arrays by vanilla)
- The column sprites at 152 steps with unitlist_bar_prepare.dds, and the 2 px line of unit_xp_bar.dds
- A state taken in a real war (the made-up mod1440_chk_pop_taken stands for it), and the months before the state was the player's after the War Diary's record
- The value check of the state's population against the game's state view (checklist item 23)

Shared files touched: `interface/mod1440_ui.gfx`, `tools/check_effects.py`, `tools/design_exceptions.json`.

**Game check.** `tools/Invoke-GameCheck.ps1 states`

Checklist for the game checker:

1. 1. The page opens with the first state of the list chosen: its row on the light band, its name yellow, its cards under the table
2. 2. A left click on another state chooses it: the band and the mark follow, the page stays open
3. 3. A right-click on a state, and Show on map in the band, move the camera there and hide the page
4. 4. Sort by a column, choose Cores, press Refresh: the chosen state keeps its mark while it is listed
5. 5. Hessen against its state view: 6 free of 9 slots, the slot bar a third full, coal 17 (the state view's number), buildings 4, 2, 1
6. 6. The state card: Capital Frankfurt and Dense Urban Region, Core of the German Reich, the Core and Inland chips
7. 7. The occupation card: compliance growth -2.0% and resistance target +5.0% as on National Figures, required garrisons a grey dash
8. 8. A click on a column head sorts, a second click turns the order; State gives the game's order back
9. 9. The totals against the sum of a column
10. 10. D10 table (no effect): the building columns 46 px and the resource columns 54 px wide, their icons centred over the values; a caption Population over People and In a year; the row still ends at the scrollbar and the page at 1472 px
11. 11. D10 1 January 1936, no effect: In a year is empty in every row and in the totals bar (one month written down by on_startup)
12. 12. D10 drawn over or under (capture population, no effect): after the Population switch the graph card stands over the three right cards with nothing of them showing through; after a second click (capture cards) the three cards are back and the graph is gone. If neither the graph nor the cards show, see fallbacks
13. 13. D10 1 January 1936, the Population view, no effect: one column at the left of the 2-year range, 22 px wide, at full height; its tooltip gives 1 January, 1936 and the state's population as the People column has it; Latest equals the People of the state card; In a month, In a year and Since first empty; Highest and Lowest equal Latest; Yours since a grey dash
14. 14. D10 the switch keeps frame 2 (gold chevrons) while on; a click on another row in the Population view (capture pop_row) draws that state at once; Shift+M and the close button hide the page and the graph card with it
15. 15. D10 after `effect mod1440_chk_pop_months` (120 made-up months for every state, the page open): 120 columns of 4 px on the 10-year range by default, year marks 1937 to 1945 under the columns of their Januaries, Zoom in on (frame 2), the lowest column a 4 px sliver
16. 16. D10 after `effect mod1440_chk_pop_months`: 2 years and 5 years show the last 24 and 60 months (columns of 22 and 8 px); Zoom in off starts the columns at zero and the scale at 0; the scale's five values against the tooltips of the highest and the lowest column
17. 17. D10 after `effect mod1440_chk_pop_months`: In a year in every row, red, different from state to state, and the totals bar's In a year in white; a click on the In a year head sorts the largest fall first, a second click turns it; the arrow stands on its head
18. 18. D10 after `effect mod1440_chk_pop_months`: the table of figures against the columns: Latest is the last column's tooltip (today's People), In a month the last less the one before, In a year the last less the 13th from the end, in thousands and in percent, red for a fall (the made-up dates are all 1 January 1936)
19. 19. D10 after `effect mod1440_chk_pop_months` then `effect mod1440_chk_pop_taken` (Brandenburg, state 64, taken between month 44 and 45 of the made-up record): with Brandenburg chosen the first 45 columns of the 10-year range are blue-grey, the rest green, a 2 px yellow line before the 46th; Yours since gives a date; on 5 years the line moves with its month, on 2 years it is gone and every column is green
20. 20. D10 after `effect mod1440_chk_pop_clear` (a save of an earlier build: no months): the graph card says that nothing is written down yet, no column, no scale, no value in the table; In a year empty everywhere
21. 21. D10 after `effect mod1440_chk_pop_round` and `effect mod1440_chk_pop_round10` (paused): game.log has the MOD1440 lines with their times before and after one round and ten rounds over every state, and the months counted; the graph gains the months. Once in vanilla (1081 states); with Road to 56 (1143) if granted
22. 22. D10 after `effect mod1440_chk_pop_twice`: game.log says the guarded round twice on one day wrote one month (months before and after differ by one; the stamp equals today's day number)
23. 23. D10 the value check: the chosen state's People in its card and the graph's Latest (no effect: the month on_startup wrote) against the population of the same state in the game's state view (select the state on the map)
24. 24. D10 error.log: no line names mod1440_pop, mod1440_states_pop, mod1440_states_cards, GFX_1440p_SG_column_*x152 or GFX_1440p_SG_line_2x152

**Tests.** build.ps1 -Check states: 272 passed, 0 failed, 66 skipped; python -I tools/build_managers.py --check up to date; tools/lint_gui.py 0 errors (one new exception: the graph's quarter bands GFX_1440p_SG_stripe_600x38, as History's); tools/lint_layout.py D10 0 errors

Candidate engine facts (for the orchestrator at the close):

- Not new: global.num_days is already confirmed in the register (SCR-014: 706640 read in a launch; SCR-027) and the Records use it (mod1440_sr_day, sc_cited_day); the design's 'documented, not yet used by the mod' is out of date.
- Open question for the register, answered by checklist item 12: the drawing order of two scripted GUIs with the same parent_window_token (construction_tab), here mod1440_states (declared first) and mod1440_states_cards / mod1440_states_pop (declared after) over it.
- Candidate, to confirm in the check: for_each_loop over a global array (array = global.mod1440_pop_date) fills a temp array, and a temp array is indexed by a temp variable (pd_date^pd_i) in set_temp_variable.
- Candidate, to confirm in the check: a corneredTileSpriteType with borderSize 0 and tilingCenter = no stretches its texture to the sprite's size (GFX_1440p_SG_line_2x152 from unit_xp_bar.dds, 28x6).
<!-- end generated: build -->

## Game checks

One row per launch, generated from `scratch/phases/D10/checks/check-<n>.json`. The user's own tests are added by hand under the markers.

<!-- generated: game checks (tools/phase_notes.py; edit the handoff file, not this) -->
<!-- end generated: game checks -->

## Fix rounds

Generated from `scratch/phases/D10/fixes.json`.

<!-- generated: fix rounds (tools/phase_notes.py; edit the handoff file, not this) -->
<!-- end generated: fix rounds -->

## Close

- [ ] Roadmap status and link
- [ ] README
- [ ] Workshop description
- [ ] `version` in `descriptor.mod`
- [ ] Engine Facts rows confirmed or added
- [ ] Scene file final (`tools/scenes/states.json`)
- [ ] Finished page stored: `tools/Invoke-GameCheck.ps1 states -SaveReference` (`reference/mod/`)
