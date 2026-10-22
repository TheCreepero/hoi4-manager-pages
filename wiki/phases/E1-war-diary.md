# Phase E1: War Diary

A dated log of the campaign, written by the mod as the game goes: wars, peace, capitulations, territory, landings, changes of government, promotions. It is the first page of [the Records](../Roleplay-Pages.md), and this phase also builds the Records window and the recording that the other pages use. Status: built and checked in game on 2026-10-12; awaiting the tester's judgement. Not seen: a capitulation, a landing, an ace. What the page shows and how each value was checked is in [Scripted GUIs](../Scripted-GUIs.md), "The Records".

## Scope

- **Vanilla has:** pop-ups at the moment of an event, and nothing to read them in afterwards. A division has a history (By Blood Alone); the country has none.
- **The page:** one line per event with its date, newest first, filtered by kind. A line about a state moves the camera there.
- **Out of scope:** events the game has no hook for (a finished focus or research, a lost division or ship, where a battle was fought); events of other countries the player is not part of; a note typed by the player (no text field exists).

## The page

The Records window is about 1680x1220 at 440,100. Under its title strip (page buttons, Close) the diary has a filter row and the list.

| Part | Size | Holds |
|---|---|---|
| Filter row | 1640x40 | All, War and peace, Territory, Government, Officers, Air and sea; beside them "Older" and "Newer" (pages of 200 lines) and the number of lines kept |
| List | 1640x1080, rows 34 high, 31 in sight | the lines, newest first, scrolled with the vanilla scrollbar |

| Column | Width | Text | Source |
|---|---|---|---|
| Date | 150 | 1939.9.1 | the stored date, `GetDateStringNoHour` (X35) |
| Icon | 40 | one frame per family of events | an icon strip of the mod built from vanilla icons; `frame` from the row's value (X10) |
| Event | 380 | "War declared on", "Capital taken", "Promoted to field marshal" | a text key held by the line (X37). The fetched text is plain words: a name cannot stand inside it, which is why subject and other party have columns of their own |
| Subject | 560 | the country (with its flag), the state or the officer | `GetName` or `GetNameWithFlag` of the stored scope (X18, X33, X40) |
| Other party | 400 | "France", "Germany" under a column head that fits the filter | the second stored scope |
| Go | 60 | a camera button, on lines about a state | `goto_state` (X13); shown per row by a `_visible` trigger (X39) |

- **A line keeps its name.** A retired general and an annexed country still give their names from the log (X34).
- **State names follow the holder:** the probe's Danzig read "Gdańsk" once Poland held it again. A line shows the name of today.

## What gets a line

Each hook runs for every country, so its first line asks whether a human country is involved; the line is written for that country. The scopes of the hooks marked "seen" were logged in the probe (X43); the others are those of the vanilla comments (R5).

| Family | Event | Found by | Subject, other party |
|---|---|---|---|
| Record | The record begins | the first run in a game (`on_startup`, or the first day with the mod) | - |
| War and peace | War declared on, War declared by | `on_war_relation_added` (ROOT attacker, FROM defender): seen | the other country |
| | Peace with | the daily comparison of `enemies` with the mod's copy (`on_peace` fires, seen, but does not say with whom) | the country |
| | Capitulated (an enemy), We capitulated | `on_capitulation` (ROOT the capitulated, FROM the winner): not seen, needs fighting | the country, the winner |
| | Annexed | `on_annex` (ROOT the annexer, FROM the annexed): seen | the country |
| | Made a subject, Released | the daily comparison of `subjects`: `on_puppet` did not fire for the effect `puppet`, and may fire only from a peace conference | the country |
| | Joined, left, founded a faction | `on_join_faction`, `on_leave_faction`, `on_create_faction` | the faction leader |
| Territory | State taken, State lost; Capital taken, Capital lost when `is_capital` | `on_state_control_changed` (ROOT new controller, FROM old, FROM.FROM the state): seen. It also fires for the states of an annexed country and for a state handed back in a peace, so many lines can come on one day | the state, the other country |
| | Landing in, Airborne landing in | `on_naval_invasion`, `on_units_paradropped_in_state`; one line per state and day | the state |
| | Nuclear strike | `on_nuke_drop` (ROOT the country that drops; the target is read at build) | the state or country |
| Government | Government changed, Ruling party changed, Election held, Coup, Civil war ended | `on_government_change`, `on_ruling_party_change`, `on_new_term_election`, `on_coup_succeeded`, `on_civil_war_end` | - |
| | New head of government | the daily comparison of `country_leader` | the character |
| Officers | Commissioned, Promoted to field marshal, Gained a skill level | `on_unit_leader_created`, `on_army_leader_promoted`, `on_unit_leader_level_up` (the officer, FROM his country): all three seen. The first does not fire for the officers a game starts with | the officer |
| | Decorated | the Award button of [E2](E2-officer-records.md) | the officer |
| Air and sea | Pride of the fleet sunk (ours, theirs) | `on_pride_of_the_fleet_sunk` (ROOT the owner, FROM the sinker) | the other country |
| | Ace promoted, Ace lost | the ace hooks (not seen: `add_ace` does not fire them) | no name, until play shows that an ace can be kept ([E5](E5-aces-roll.md)) |
| | Operative captured, Operative lost | `on_operative_captured`, `on_operative_death` | the operative |

- **Not every battle.** A general's battles are counted on his record (E2), not listed here: a front makes hundreds.
- **Territory** goes into its own log, so a large offensive does not push out the rest. The All view shows capitals only; the Territory filter shows every state (decision 4 of the Records).

## Data and script

Written by a new section `records()` and `war_diary()` of `tools/build_managers.py`.

| Name | What |
|---|---|
| `mod1440_ev_date`, `_day`, `_kind`, `_a`, `_b` | the log: five arrays of the country, 500 lines. `_date` is a `global.date` for the text, `_day` a `global.num_days` for counting days (X35), `_kind` a text key (X37) |
| `mod1440_tr_date`, `_day`, `_kind`, `_a`, `_b` | the territory log, 500 lines |
| `mod1440_ev_add` (effect) | appends the line held in the temporary variables `ev_kind`, `ev_a`, `ev_b` with today's date, drops the oldest beyond 500, raises `mod1440_wd_dirty` |
| `mod1440_ev_daily` (effect) | compares `enemies` and `country_leader` with `mod1440_ev_enemies` and `mod1440_ev_leader`, writes the lines, takes the new copy |
| `mod1440_wd_list` (effect) | copies the lines of the chosen filter and page, newest first, into `mod1440_wd_date`, `_kind`, `_a`, `_b`; runs when the page opens, on a filter or page button and once a day while it is open |
| `mod1440_rec_open`, `mod1440_rec_page`, `mod1440_wd_filter`, `mod1440_wd_from` | what the window shows |
| `on_actions` | one entry per hook of the table, each a few lines that end in `mod1440_ev_add`; `on_daily` gets `mod1440_ev_daily` for human countries |

Commands new to the test's list: `is_in_array`, `has_war_with`, `is_capital`, `every_enemy_country` or a loop over `enemies`, `var:` scopes. None writes to the game.

## Part C: the state card

A small strip in the vanilla state view: "Taken from France on 1940.6.14, held for 312 days", from variables the territory hook leaves on the state. The probe showed such a card: it appears while a state is selected, its scope is the state, and it may stand inside the state view or beside it (X47). Where it stands is chosen with a mock-up when the phase starts; [E6](E6-unit-honours.md) puts its Cite button on it.

- **2026-10-13:** the card's line "Taken from ..." reads a country from `mod1440_sr_from`, and a state nobody took held none: the game logged "invalid scope for var" at every selection of such a state, although the line was hidden (X73). `mod1440_ev_init` now gives every state a country once (`global.mod1440_sr_named`). Seen: one line before, none for three selections after. Next to Landlord's buttons in the state view the card stands free.

## What the probe settled

| Question | Answer | For this page |
|---|---|---|
| A date in an array | yes (X35) | the date column as planned; a day number is stored beside it |
| A text key in a variable | yes, plain words (X37) | the Event column; no scripted localisation, so no fifth folder under `common/` |
| A held general, also once he is gone | yes (X33, X34) | officer lines carry the name for good |
| A country in an array | yes, with its flag (X40) | the subject and other party columns |
| The hooks | eleven seen; `on_puppet` not by effect (X43) | subjects by the daily comparison; capitulation, landings and aces still to be seen in play |
| A long log | no cost to speak of (X48) | 500 lines, pages of 200 |
| A scoped row and the country's arrays | need `ROOT.` (X36) | the diary's list is not scoped: its rows read the arrays by index |

## Checks

1. **Paused, by effects** (a throwaway effect file, as History's made-up months): a declared war, a state taken with `set_state_controller`, an annexation, a promotion, a new general. The probe fired all of these this way. Each line is compared with what was done: date, words, names. 600 made-up lines: the oldest 100 are gone. The console runs an effect in the scope of what is selected (X49): deselect first.
2. **Values against the game:** the date of a line against the clock; a state's name against the map; the enemy list after `declare_war_on` against the diplomacy view.
3. **Needs time** (the user's play, or decision 3 of the Records): peace found by the daily comparison, a state taken by fighting, a capitulation, a landing. Until seen, each hook also writes `log = "mod1440 <hook> ..."` to `game.log`.
4. **Cost:** the time of `on_state_control_changed` for a country that is not human (it should leave at its first line), measured as X22 was.

## Decisions

- 2026-10-12: planned.
- 2026-10-12, the user: one Records window opened from the top bar ("the window is better"); capitals in the main view and every state under the Territory filter ("sounds good"); a check may run up to ten days inside January 1936 with a copy of the autosave made first.
- Built without an icon column: the words of the Event column proved enough, and an icon strip would have been a new texture.
- Capitulation is found by the daily comparison (`has_capitulated` of each enemy), not by `on_capitulation`: the comparison needs no scope the probe could not see.
- Faction, subjects and the head of government are found by the daily comparison as well.
- Not built: lines for operatives and for a nuclear strike.

- 2026-10-12, the user: "a round of improving the UI ... really polished and fit their purpose really well", with free hands. Done the same day: striped rows under a bar of heads, dates written out, the family's text icon before each line, names in yellow with flags, a country beside its event when the line has no state or person, and the record in twelve figures beside the list, with the switch of the battle honours and its explanation. Checked in game and from a cold start (`scratch/checks/crop_p_*.png`, `reference/mod/`).

## Additions of 2026-10-13: officers on the lines, victory points, All through both logs

The user had installed the build of 2026-10-12, played a war with it and wrote on 2026-10-13: "Overall I'm very happy with the results. I just want more graphical details", with three wishes: an officer's portrait in his file and in the list; a record, in the officer's file and in the War Diary, of each battle over a victory point won or lost and of each state captured; a file for a war as there is one for a general, with the flags and maybe the leaders of each side and some statistics.

- **A line has an officer.** A line about a state names the general who had the most divisions in the state when it changed hands (the search E2 used for its count, now the effect `mod1440_of_best`). The log got four parts: `c` and `sc` (the officer), `p` (the state of a victory point, for the camera) and `x` (the line stands in the other log too). A game saved before gets zeros for the lines that are there (`mod1440_ev_grow`), and its capitals in the territory log the mark `x`.
- **Victory points.** "A battle over a victory point won or lost" cannot be had from the battle hooks: they give the general and his country, not the place. What can be had is the place changing hands: once a day while the country is at war, `mod1440_vp_scan` reads `global.province_controllers` for each of the game's 1495 victory points (`tools/victory_points_table.py`) and compares with the copy of the day before. A point that passed between the country and an enemy is a line "Victory point taken" or "Victory point lost" with its name (the game's text `VICTORY_POINTS_<province>`), the enemy and the general on the spot; its button moves the camera to its state. The copy is taken again without lines on the first day of a war and when the list of points changes.
  - **Decided:** every point, also the small ones (the wish said "a victory point"). A point worth 15 or more (107 of them) stands in the main log too, as a capital does. No line when the old holder has capitulated or is gone: those points were not fought for. A battle won without the place changing hands leaves only its count on the officer.
  - **Cost:** 1495 comparisons a day at war; by Engine Facts X22 a few milliseconds. Not measured.
- **All means all.** The All view goes through both logs together, by day, the main log first on the same day; a line that stands in both is shown once (`merged()` in `tools/build_records.py`). This replaces the user's choice of 2026-10-12 (single states under the Territory filter only): the new wish asked for captures in the diary.
- **The page:** the list is 1270 px wide instead of 1190 for a fifth column, Officer; the pane beside it is narrower and has fourteen figures (victory points taken and lost are new).
- **Checked in game on 2026-10-13** (checks 3 and 4 below), after the user allowed the launch ("Yes, start it now"). Two faults showed and were mended in the open game:
  - **No war closed.** The effect that writes a line kept the officer in the temporary variables `ev_c` and `ev_sc`; `ev_c` is also the country in the loops of the daily comparison, and a temporary variable is one for the whole run (Engine Facts X64). The officer now has `ev_o` and `ev_so`.
  - **An error line per unknown character.** `is_character` wrote "is not a valid character" to `error.log` for a character no country has recruited. Each test now asks the country `has_character` first (X60).

**Left unseen:** a state or a victory point taken by troops in a running game (the lines here were caused by effect while paused); a real save of the build of 2026-10-12 (check 5 took the newer parts away in a new game, which is the same to the script).

## Game checks

| # | Date | Build | Checked | Result | Screenshot | Taught |
|---|---|---|---|---|---|---|
| 1 | 2026-10-12 | `1a08bb3` +dirty | the page in a new game; events caused by effects while paused (war on Poland, Danzig and Brandenburg taken, Luxembourg annexed, Denmark a subject, a promotion, a new general, four advisors); the filters; the state button | every line with the right date, words, name and flag; Territory lists the single states; the button moved the camera to Berlin and closed the window | `scratch/checks/crop_e1_2.png`, `crop_e1_4.png`, `view_e1_3.png` | X50, X52 |
| 2 | 2026-10-12 | the same game | nine days of game time, 1 to 9 January, as Germany at war with Poland | the daily comparison ran each night: three advisors the game had dropped read "Left office"; two states Poland walked into read "State lost to"; the autosave was not written | `scratch/checks/crop_e1_14.png`, `crop_e1_17a.png` | X53, X54, X55 |
| 3 | 2026-10-13 | `9c832ae` +dirty | live session, paused on 1 January 1936, events by the throwaway effects of `scratch/check_f.py`: war on Poland; Toruń, Kraków and Breslau handed over (`set_province_controller`) and the comparison run; Niederschlesien lost and taken back with Rundstedt's army in it; a white peace; war on Czechoslovakia and its annexation; 400 comparisons between two lines of `game.log` | every victory point line with its name, the enemy and the right word; Kraków (20 points) in both logs and once in the All view, Toruń (5) and Breslau (10) in the territory log; Rundstedt on the lines of Niederschlesien and Breslau, nobody on Kraków's; the button of a point moved the camera to its state; the figures followed (3 wars begun and ended, 12 states taken, 2 lost, 3 points taken, 1 lost, 1 capital, 1 annexation); 400 comparisons inside a second. The two faults above | `scratch/checks/wd1-*`, `wd2-*`, `wd3-*` | X60 to X64 |
| 4 | 2026-10-13 | the same build, cold start through `tools/Invoke-GameCheck.ps1` with ten other scenes | the page in a new game; `error.log` | the list 1270 px wide with its fifth column and the fourteen figures; every expected widget found where the layout puts it; no line names the mod | `reference/mod/war_diary-panel.png` | - |
| 5 | 2026-10-13 | the same build, second live session (allowed by the user: "Yes, start it now") | a game as an older build left it: a war, a victory point and a state by effect, then the four newer parts of both logs and the two newer counts of the wars cleared (`mod1440_chk_old` of `scratch/check_f.py`); the Records opened; another victory point lost | the newer parts were 0 long beside 3 and 4 lines, and 3 and 4 again once the Records had opened; the list read as before, without officers; the next lines went in at the right place (6 of 6 in every part); the war's counts were padded when it was next written to, and its file read 1 point lost; no line of `error.log` names the mod | `scratch/checks/b_wd2-*`, `b_wd3-*`, `b_wr1-*` | X57 (`add_to_array` with `index`) |
| 6 | 2026-10-13 | the finished build with the mod "Add USA Generals AI REWORK", cold start, 1 to 4 January | the lines for officers no hook tells of (their command came by an effect) | eight "Commissioned" with names on the day the daily round met them, then "More officers commissioned"; a person kept by his place stayed right through a change of places made up by effect ([E2 notes](E2-officer-records.md), checks 5 to 7) | `scratch/checks/d_wd-*` | X66, X67 |


## Proposal

<!-- generated: proposal (tools/phase_notes.py; edit the handoff file, not this) -->
The page is right in its bones: the kinds of line are the right ones for a role-player, and the user's own save (read for this review: 155 main-log lines, 178 territory lines, 1084 days) shows few lines that are noise. What is wrong is narrower and has numbers: 70 of 152 state lines are hand-overs in peace counted as battles ("States lost 54" where the battle losses were about 7), 31 of 155 main-log lines repeat or name nobody, and the list spends a fifth of its rows on day headers while one peace day writes 88 lines.

The proposal: split taken and lost by whether we are at war; the day in a column and runs of states folded, so the whole campaign fits one page of 200 rows instead of two; names that lead somewhere (a country to its lines, an officer to his file); new lines marked; thirteen new kinds the hooks can tell, and a number on a line; the pane as banded tables with the chronicle in view. Verdict: refine; effort: L: the generator only (build_records.py): 13 kinds and 6 hooks, the split and two daily checks in the recording, part n with its grow line, the list's row and copy (day column, folds, new mark, filter 8, two link buttons), the pane rebuilt as tables with a small chronicle list, the badge and state card texts, about 15 new sprite sizes in the E1 review block, the scene's states and samples, and check effects for the new kinds.

What vanilla does badly: Read from the user's save (scratch/phases/E1/read_save*.py, save_facts.json):

**The territory log mixes battles with treaties.** state_taken 93: 57 from an enemy, 36 from countries never at war with us (34 on the day of an annexation). state_lost 53: 30 to our own subjects (28 on one peace day), 22 to a former enemy, 16 of them on that same peace day. vp_lost is 0. The campaign card shows "States 98 taken, 54 lost" and a bar two-thirds green: a war that went far better than that.

**The main log repeats.** member_in is the largest kind (27 of 155), and 17 of those are a country that became our subject that day, which "Made a subject:" already says. ace_new writes 14 lines that name nobody.

**The list is slow to read back.** The All view has 318 lines on 83 days and needs 401 rows (2 pages): every day costs a header row, and 52 of 83 days have one line. One day holds 100 lines (a peace: 41 states taken, 28 handed to subjects, 16 to the former enemy). A page of 200 rows holds 163 lines.

**Following one enemy or one general** takes another page: the Wars file shows 20 lines, the Officers file 11.

**The pane** uses tiles for what is a list of figures (the rule of 2026-10-16: tables, not tiles), gives the chronicle three lines of explanation and leaves 90 px empty under them, and keeps the honours' switches and a Kept card of three lines (one of them a hotkey hint) in sight at all times.

**Counting fault:** landings (6 lines) and airborne landings are never counted (ct 0), because a family-2 line that stands only in the main log is counted in neither log.

**1. Relevance: what the 39 kinds earn.** Judged on the user's save (the table gives every kind with its count). **Keep 30** as they are: wars, peace, capitulations, annexations, subjects, factions, capitals, landings, victory points, government, officers, the pride of a fleet. **Split 4** (state and capital taken and lost) by whether we are at war. **Refine 2** (no faction line for a new subject; no "government changed" on the day of a party change). **Quiet 3** (the nameless ace lines: decision 2). **Fix 2** (landings and airborne are never counted). Two kinds get a number (skill level reached, how many more officers).

Noise in numbers: of 155 main-log lines 31 repeat or name nobody (20%); of 152 state lines 70 are treaties read as battles (46%). Nothing else in the save is noise: skill levels, feared to flood, were 4.

**2. Recording: battles apart from treaties.** In mod1440_tr_taken and mod1440_tr_lost, before the line: `has_war_with = var:tr_c` (the country in scope against the other). At war: as today (state_taken, capital_taken, the general on the spot, the war's and the officer's counts, the honour). Not at war: kind 39 "Received from" or 40 "Handed over to" into the territory log only (a capital too: the main log has the Annexed, Peace or Made a subject line), no general searched (mod1440_of_best skipped: 88 searches on the user's peace day), no war or officer counted, the state card told it came by treaty (mod1440_sr_how = 2).

Ground counts battles: in the user's save States 59 : 7, Victory points 25 : 0, Capitals 2 : 1, and a row "By treaty: received 39, handed over 47" (7 and 47 if the 16 states that went back to the former enemy on the peace day count as a treaty: open in game). Lines already written keep their kinds; the figures of an existing save stay as they were until new lines come (the counters cannot be split after the fact).

**3. Recording: fewer repeats, a number on a line.** member_in is not written for a country in our `subjects` (the daily round compares subjects first, so it is there). government is not written on a day party was (a day variable). The nameless ace lines: decision 2. Landings and airborne are counted (count a main-log line of family 2 when its x is 0).

**Part n:** LOG_ARRAYS gets "n" at its end and mod1440_ev_grow a line for it (zeros for the lines a save has; the chronicle the same). Written for: level (the skill reached), commissioned_more (how many), cited (divisions), casualties (the step). Shown in the list right-aligned at the end of the words column in hoi_20b yellow; hidden on the Wars and Officers files on purpose (their lines are 26 high and narrow).

**4. More to store: thirteen kinds and two values.** New kinds at the end of KINDS (39 to 51; codes stay below 90): the two of the split; **Left the service** and **Captured:** (the daily round already marks each serving officer with the day: one loop over the known officers finds who was not met, and is_general_captured who is held; the line names him by of_me, so his file shows it); **Volunteers sent to / recalled from**; **our government in exile, hosting one, back from exile**; **Broke the cipher of**; **Won the civil war against**; **We fight on**; **Our casualties passed** (a step of casualties_k, once a day).

Cost: the hooks cost nothing on a day they do not fire and leave at their first line for a country that is no player's; the daily round adds one loop of ~100 officers and one comparison. Save: a new kind adds no bytes at full logs (a line takes an old line's place) and 29 bytes of counter; part n +73 KB, the officer marks +6 KB, everything of this design +88 KB, 0.08% of the user's 104 MB save (save_cost.py).

Not proposed, with the reasons in the table: a nuclear strike (no target in scope), a coup, a border war, an autonomy level, the end of a peace conference, operatives (later, with a page of their own), battles as lines.

**5. The list: the day in a column, a run folded, new lines marked.** The card widens from 1172 to 1240 (the pane gives 68), rows 1198x34 [WD_ROW_W], 29 in sight. Columns: date 8 (118, hoi_16mbs, "30 September, 1944" measures 115), icon 132, words 160 (232, hoi_18mbs; the longest words, "Hosting the exiled government of", 224), plate 398 (260x28; text 240), flag 668 and country 716 (228, as today), officer's face 954 and name 986 (176, as today), mark 1170.

**No day rows:** the date stands on a day's first line; every line of a day shares one band (the stripe follows the day's parity, not the line's). The day rows go (WD_MORE loses hd and hn); a page of 200 rows holds 200 lines instead of 163.

**Folds:** in All and in the country filter, three or more state lines of one day, one kind and one country become one row: the first state's plate and "+40 states" (hoi_16mbs, right in the plate), no officer, the tooltip "The Territory filter lists each state." Territory and the lines of a state show every line. In the user's save: 318 lines in 207 rows instead of 401, the whole campaign on one page.

**New lines:** a line written while the window was closed stands on the lighter band (GFX_1440p_SG_pick, the chosen-row band of the other pages): its number above mod1440_rec_seen, set at Close.

**6. Names that lead somewhere.** The country's flag and name become a button (a transparent hit area of 276x28 over them): the diary shows that country's lines only, filter 8 (`mod1440_wd_country`, the next filter number), from both logs as the lines of a state do; the head bar shows "§Y<country>§!: lines 1 - N of N" where the Officer head was. Following an enemy back to the first day is one click; the Wars file keeps its 20 lines.

The officer's face and name (the general on the spot, or the person of an officer line) become a button: the Officers page with his file open (mod1440_of_sel, as a row click sets it). The state's plate keeps moving the camera.

**7. Filters and pages.** The seven filters stay (numbers kept); filter 8 is reached from a name and left by any filter button. The arrows stay. "lines 1 - N of M" counts lines, a fold as its states. Its tooltip takes the text of the Kept card: "Main log 155 of 1000 lines, territory 178 of 1000. The oldest line goes first; a marked line stays."

**8. The right pane, 400 wide.** **The campaign** (414 high): banded tables under head bars (rows 26, hoi_16mbs labels, hoi_18mbs yellow values), two figures to a row. War and peace: wars begun, wars ended, capitulations, annexations, subjects made, at war today. Ground, in battle: states, victory points, capitals with taken, a bar of 116 and lost; then by treaty: received, handed over. The service: commissioned, promotions, skill levels, decorations, left the service, governments.

**The chronicle** (348): the four to six newest marked lines (date in grey, icon, words, name), copied by mod1440_wd_list from the end of mod1440_kp_*; "Read the chronicle" opens the Marked filter. Empty: the two lines that say how to mark.

**Battle honours** (196): one line of what they are, the four switches in two rows, "By themselves | Cited by you" as a table row, the last citation.

**Kept** (96): two lines. The hint "Shift+J or Escape closes the window" goes: the top bar button's tooltip and Close say it.

**9. The state card.** Unchanged but for a state that came by treaty: "Received from §YCuba§! by treaty on 17 May, 1943, held 26 days" and, in grey, that no troops are named (mod1440_sr_how 2 hides the "by the troops of" window). "Its lines" stays.

**10. The top bar badge.** The count turns red (§R) when one of the new lines is of War and peace (mod1440_rec_new_war, set by mod1440_ev_add while the window is closed, cleared at Close). The button's tooltip adds "N new lines since you last closed the Records, K of war and peace" and the newest line: its words, its name and date (mod1440_rec_last_k, _a or _b, _d, written by mod1440_ev_add). The button stays 150x28 at 2002,3 (D7).

**11. What stays (the contracts).** KINDS only grows at its end; LOG_ARRAYS gets "n" at its end with its grow line; page numbers and filters 0 to 7 keep their values, the country filter is 8; the Records frame is untouched (no tab, title or body change); MARK_KEEP, LOG_KEEP and VIEW_ROWS stay. The Wars and Officers files read the new kinds by take() and show their words; part n is hidden there on purpose. The split changes what the Wars page counts per enemy: a hand-over is no longer "lost" to a former enemy (written down as a deviation with the build). New commands for the test's list: has_war_with.

| Kind (number, name) | Words | Family | In the user's save (main / territory) | Verdict | Why, and the hook or value with its cost |
|---|---|---|---|---|---|
| 0 begins | The record begins | 1 | 1 | Keep | The anchor of the record. |
| 1 war_on | War declared on | 1 | 9 | Keep | Core of the story. |
| 2 war_by | War declared by | 1 | 24 | Keep | Core. They come in bursts (9 on one day when the Axis minors declared war); one line each still names each enemy. |
| 3 war_with | At war with | 1 | 0 | Keep | The daily comparison's backstop: 0 here because the hooks caught every war. |
| 4 peace | Peace with | 1 | 22 | Keep | Core. |
| 5 capitulated | Capitulated: | 1 | 2 | Keep | Core. |
| 6 we_capitulated | We capitulated | 1 | 0 | Keep | Core. |
| 7 annexed | Annexed | 1 | 2 | Keep | Core. |
| 8 subject_new | Made a subject: | 1 | 17 | Keep | Core: 9 and 5 on two days of a peace. |
| 9 subject_gone | No longer a subject: | 1 | 2 | Keep |  |
| 10 faction_in | Joined the faction led by | 1 | 0 | Keep | Rare and important. |
| 11 faction_out | Left the faction | 1 | 0 | Keep |  |
| 12 member_in | Joined our faction: | 1 | 27 | Refine | The largest kind of the main log (17%). 17 of the 27 are a country that became our subject the same day: a subject joins its overlord's faction, so the line repeats "Made a subject:". Not written for a country that is our subject (is_in_array subjects); the other 10 stay. |
| 13 member_out | Left our faction: | 1 | 1 | Keep |  |
| 14 state_taken | State taken | 2 | - / 93 | Split | 36 of the 93 came from a country never at war with us (an annexation brought 34 on one day). A state that changes hands with a country we are not at war with (has_war_with) becomes kind 39 "Received from"; the Ground figures count battles only. |
| 15 state_lost | State lost | 2 | - / 53 | Split | 30 of the 53 went to our own subjects at a peace (28 on one day), and vp_lost is 0: the campaign card's "States lost 54" was nearly all hand-overs. Without a war: kind 40 "Handed over to". |
| 16 capital_taken | Capital taken | 2 | 5 (both logs) | Split | 3 of the 5 from a country never an enemy (annexations): those become "Received from" in the territory log; the main log has the Annexed line already. |
| 17 capital_lost | Capital lost | 2 | 1 (both logs) | Split | Same rule. |
| 18 landing | Landing in | 2 | 6 | Keep, fix | Core. Its counter reads 0 for 6 lines: a family-2 line of the main log that is not in the territory log is never counted (recording(): counted only in tr, or in ev when fam is not 2). Count it. |
| 19 airborne | Airborne landing in | 2 | 0 | Keep, fix | Same counter fault. |
| 20 cited | Divisions cited in | 2 | - / 1 | Keep | The player's own act. Gets the number of divisions (part n). |
| 21 party | The ruling party changed | 3 | 0 | Keep |  |
| 22 government | The government changed | 3 | 0 | Refine | Probably fires with a party change (both hooks for one event): not written on a day a party line was written. To be seen in game. |
| 23 election | An election was held | 3 | 0 | Keep |  |
| 24 leader | New head of government | 3 | 0 | Keep | Core for role-play (a person with a portrait). |
| 25 appointed | Appointed | 3 | 2 | Keep |  |
| 26 dismissed | Left office | 3 | 2 | Keep |  |
| 27 commissioned | Commissioned | 4 | 1 | Keep |  |
| 28 promoted | Promoted to field marshal | 4 | 1 | Keep |  |
| 29 level | Gained a skill level | 4 | 4 | Keep, add n | Not the noise it was feared to be (4 lines in 1084 days). Gets the level reached (part n). |
| 30 decorated | Decorated | 4 | 3 | Keep |  |
| 31 ace_new | An ace was promoted | 5 | 14 | Quiet (decision 2) | 14 lines (9% of the main log) that name nobody: the ace cannot be kept yet (E5). The counter stays (Wars page); the line waits for E5. |
| 32 ace_lost | An ace was lost | 5 | 0 | Quiet (decision 2) | Same. |
| 33 ace_down | An enemy ace was shot down | 5 | 0 | Quiet (decision 2) | Same; an air war makes many. |
| 34 pride_lost | Our pride of the fleet was sunk by | 5 | 0 | Keep |  |
| 35 pride_sunk | Sank the pride of the fleet of | 5 | 0 | Keep |  |
| 36 vp_taken | Victory point taken | 2 | 9 / 25 | Keep | Core; only 5 of 25 fell on the day their state did, so no merging. |
| 37 vp_lost | Victory point lost | 2 | 0 | Keep | Its 0 is the evidence that the 53 states lost were not battles. |
| 38 commissioned_more | More officers commissioned | 4 | 0 | Keep, add n | Says how many (part n). |
| 39 state_received (new) | Received from | 2 | would be 39 (36 states, 3 capitals) | Add | on_state_control_changed (R5), when NOT has_war_with FROM (triggers_documentation.md:5051). No daily cost; a trigger per hook that reaches a human. |
| 40 state_handed (new) | Handed over to | 2 | would be 31 to 47 | Add | The same hook, the other side. |
| 41 officer_gone (new) | Left the service | 4 | - | Add | Daily: an officer of mod1440_of_known whose mod1440_of_seen_day is yesterday's (the round marks every serving officer, build_records.py 1270). 103 scope entries a day in this save, under 1 ms by X69. Save: one mark per officer (3 KB). |
| 42 officer_captured (new) | Captured: | 4 | - | Add | is_general_captured (CHARACTER, triggers_documentation.md:5603) asked in the same daily loop; one mark per officer (3 KB). |
| 43 volunteers_sent (new) | Volunteers sent to | 1 | - | Add | on_send_volunteers: ROOT sender, FROM receiver (vanilla 07_nsb_on_actions.txt:2003). No daily cost. |
| 44 volunteers_back (new) | Volunteers recalled from | 1 | - | Add if seen | on_recall_volunteers: documented, scopes not commented in vanilla: open in game. |
| 45 exiled (new) | Our government went into exile in | 3 | - | Add | on_government_exiled: ROOT the exile, FROM the host (09_aat_on_actions.txt:219). |
| 46 exile_hosted (new) | We host the government in exile of | 3 | - | Add | The same hook, FROM human. |
| 47 reinstated (new) | Our government is back from exile | 3 | - | Add | on_exile_government_reinstated: ROOT the exile, FROM the old host (04_mtg_on_actions.txt:23). |
| 48 cipher (new) | Broke the cipher of | 1 | - | Add | on_fully_decrypted_cipher: scope the target, FROM the decrypter (05_lar_on_actions.txt:341). Only our own success: that an enemy broke ours is the intelligence the game hides. |
| 49 civil_war_won (new) | Won the civil war against | 1 | - | Add | on_civil_war_end: ROOT the winner, FROM annexed, fires on_annex too (00_on_actions.txt:1397): the Annexed line is then not written. |
| 50 fought_on (new) | We fight on: no longer capitulated | 1 | - | Add | on_uncapitulation: ROOT the country (00_on_actions.txt:1165). |
| 51 casualties (new) | Our casualties passed | 1 | - | Add | Daily: casualties_k (R14; trigger at triggers_documentation.md:2085) against the next of 10, 25, 50, 100, 250, 500, 1000, 2000, 5000 thousand; one comparison a day, one variable. The number is part n. |
| not proposed | on_nuke_drop | - | - | No | ROOT the country that drops; the target is in no scope (00_on_actions.txt:384). |
| not proposed | on_coup_succeeded, on_border_war_lost | - | - | No | Scopes not commented in vanilla; the border war is China's. |
| not proposed | on_subject_autonomy_level_change | - | - | No | ROOT subject, FROM overlord (01_tfv_on_actions.txt:171), but no text names the new level. |
| not proposed | on_peaceconference_ended | - | - | No | Repeats the Peace line. |
| not proposed | on_operative_captured, on_operative_death | - | - | Later | A person kept by place (mod1440_ch_remap); belongs with an operatives page. |
| not proposed | battle hooks as lines | - | - | No | A front makes hundreds: they stay counts on the officer (E2). |
| part n (new) | a number on a line | - | - | Add | LOG_ARRAYS + ["n"] with a line in mod1440_ev_grow (zeros for old lines). For: the skill level reached, how many more officers, divisions cited, the casualty step. +73 KB with both logs and the chronicle full, 0.07% of the user's save. |

Additions, each with the row of "What a redesign can add" or the register id that allows it:

- The day in a column on a day's first line; the day's lines on one band; no day rows (Scripted GUI row widgets shown per row by _visible triggers on the row's index (X39, X50); 'A table of states or generals' row of What a redesign can add (scripted GUI, X10))
- Folded runs of states in All and the country filter (+N states) (The page's copy made by script (mod1440_wd_list, X48, X69); a count array of the copy read by index (X30))
- Lines written while the window was closed on the lighter band (A per-row _visible trigger (X39) on a number the copy carries; the band sprite GFX_1440p_SG_pick_* of the other pages)
- A country's name as a button: its lines only (filter 8) ('New buttons that do something: yes in a scripted GUI' (X3); the row's index in a click effect (X50); as filter 7 of a state)
- An officer's name as a button: his file on the Officers page (X3, X50; the officer entered by the number or place the line keeps (X66, X67))
- Kinds 39 and 40: received by treaty, handed over (on_state_control_changed (R5, X43) with has_war_with (documented, triggers_documentation.md:5051))
- Kinds 41 and 42: left the service, captured (The daily round's mark of serving officers (build_records.py, mod1440_of_seen); is_general_captured (R4, documented))
- Kinds 43 to 50: volunteers, exile, cipher, civil war, fought on (R5 hooks with the scopes of the vanilla comments (SCR-062); X52 for carrying the scope into the effect)
- Kind 51 and part n: casualty steps and a number on a line (casualties_k (R14, documented); a new part of the logs grown like NEW_ARRAYS (contracts))
- The campaign as banded tables; Ground in battle and by treaty (Design Rules, 'A list of numbers is a table, not tiles' (second A3 redesign); counters mod1440_ct (save contract kept))
- The chronicle's newest marked lines in the pane (A scripted list from an array (X10) copied by mod1440_wd_list)
- Red badge and the newest line in the button's tooltip (Colour codes in a scripted text (X56); a variable in a pdx_tooltip (X30), GetTokenLocalizedKey there untested (openInGame))
- State card wording for a state received by treaty (The card's selected_state_context (X47) reading one more state variable)

Open until the game shows it:

- Whether has_war_with is still true when a peace conference moves states: the user's peace day wrote 16 "lost" to the former enemy. If it is, those stay battles; fallback: also count as by treaty a change on a day the other country has capitulated (has_capitulated).
- The scopes of on_recall_volunteers (not commented in vanilla) and whether on_send_volunteers fires once per sending.
- Whether on_government_change and on_ruling_party_change fire together for one change (the reason to skip the second line).
- The order of on_annex and on_state_control_changed for an annexation (the received states and the Annexed line on one day either way).
- [?mod1440_rec_last_k.GetTokenLocalizedKey] inside the pdx_tooltip of the top bar button.
- The lighter band of new lines against the day bands: whether it reads as "new" (the user's judgement).
- The daily round's cost with the loop over known officers, and the page's with folds, by mod1440_chk_list_time after mod1440_chk_fill.
- Left the service: a retired general and one killed in the field both read as not met; captured generals (is_general_captured) are told apart. A general who comes back is not written twice (the mark clears when he is met again).
- The new hooks in play: none of 43 to 50 can be caused paused in January 1936 except by effect (send_volunteers, decryption); the check writes "MOD1440 listening" to game.log as the landing hooks do.

Figure groups of the design page: page, list, follow, pane, badge, state.
<!-- end generated: proposal -->

## Build (generated)

<!-- generated: build (tools/phase_notes.py; edit the handoff file, not this) -->
Status: built and checked by render and tests; not seen in game (by builder-script).

**What was built.** The UX review is built in tools/build_records.py with all eight decisions taken. Recording: 13 new kinds at the end of KINDS (39 to 51). State changes split by has_war_with = var:tr_c: not at war, a 'Received from' or 'Handed over to' line goes into the territory log only, with no general, no war or officer count and the state card set to sr_how 2. member_in is not written for a subject; government is skipped on a day of party; ace lines are quiet (counters kept); landings and airborne are now counted. Part n is added at the end of LOG_ARRAYS with a grow line for ev, tr and kp. Officers who left the service or were captured get lines from the daily round (mod1440_of_gone), as do casualty steps; six new hooks (exile, cipher, volunteers, civil war, uncapitulation) write lines. The page: a list card of 1240 with the day in a column on each day's first row, one band per day, new lines on the pick band (id above mod1440_rec_seen, set at Close) and runs of 3 or more states folded in All and in a country's lines. A country's name opens filter 8; an officer's name opens his file. The pane is 400 wide: banded tables, the chronicle with its 4 newest marked lines, compact honours, and Kept in two lines. The badge turns red with the newest line in its tooltip, and the state card shows the treaty wording.

**Deviations.**

- Kind 46 reads 'Hosting the exiled government of', not the table's 'We host the government in exile of'.: The table's words measure 233 px in hoi_18mbs, over the 232 px words column. The design's own section 5 measured 'Hosting the exiled government of' at 224 px.
- The number of a casualty line is stored in thousands (n = 250 for 250 000). The row has three twins of the number: as it is, ' 000', and ' 000 000' for a step of 1000 thousand or more, written as n/1000 into the page's copy.: A variable stops at about 2.1 million, so the steps of 2 and 5 million cannot be stored whole. The game's formatting has no thousands separator.
- The badge tooltip names the newest line through one variable, mod1440_rec_last_n. It holds the person or state, or the state of a victory point instead of the point's name, or the country; a line without a subject names the player's own country.: A tooltip cannot show one of several twins, and a point's name is a text key that GetName cannot read.
- The chronicle in the pane shows 4 lines.: The design said four to six and its mock-up shows four; a fifth would leave 7 px above the button.
- The Country head is also hidden in filter 8, as well as the Officer head.: The follow mock-up shows only When, What happened and Where, or who; every row names the same country.
- A folded row's box marks the first state's line only. Its plate has its own twin button whose tooltip says the Territory filter lists each state.: One row stands for several lines. Marking each line of the run would need a loop on a click, and the design says nothing about it.
- on_recall_volunteers is written with the scopes of on_send_volunteers (ROOT sender, FROM receiver) and logs both scopes to game.log.: Vanilla gives no comment for its scopes; the design said 'add if seen'.
- kept_tokens() now also maps mod1440_rec_last_k (the badge's newest kind) when the token numbers move. The new kinds change the dictionary's version, so an existing save runs mod1440_tk_fix once and game.log gets its line once.: Contract: a kept text key goes through the dictionary.
- The split changes what the Wars page counts per enemy: a hand-over is no longer 'lost' to a former enemy, and a received state is no longer 'taken'. An officer's states also count battles only.: This was the deviation the design announced (section 11). Lines already written keep their kinds.
- tools/build_managers.py (D7's top bar scene, not D8's code): the handle window hides rec_badge_war, in a block marked '# --- E1 ---'.: The badge now has a red twin, so the top bar scene would otherwise draw both counts on top of each other.
- Honour switch labels are shortened as in the mock-up: 'a capital falls' and 'a city of 15 or more falls'.: There are two switches to a row at 188 px.
- The government line is left out only when on_ruling_party_change came first on the same day.: The order of the two hooks is open in game (fallback below).
- Kind 49 'Won the civil war against' is written from on_civil_war_end_before_annexation, not on_civil_war_end (gate B).: Vanilla documents that it fires just before FROM is annexed and also fires on_annex (04_mtg_on_actions.txt:194). The skip in on_annex (mod1440_ev_cw_day and _cw_c) therefore holds: one line, not two.
- Gate B, W28: the row's name boxes are fixedsize with a one-line maxHeight: wd_row_a, _point, _who, _name, _b, _b_near, _c. A longer name ends in dots. The state card's names (sc_title, sc_taken, sc_received, sc_by) already were.: A name another mod can lengthen gets a box of fixed size (contracts).
- Gate B: the chronicle's words box (wd_ch_0..3) is 208 px instead of 200, and fixedsize.: The longest kind measures 202 px in hoi_16mbs ('Our government went into exile in', 'Our government is back from exile'). At 40 + 208 the box ends under the name box, which is right-aligned in 216..384.
- Gate B, words column: all 52 kinds (0 to 51) measure 228 px or less in hoi_18mbs against 232. The widest are 'Our government is back from exile' and 'We fight on: no longer capitulated' at 228. The number of a line never meets its words in the 228 px it is right-aligned in: the closest are 'More officers commissioned' (190) + '120' (27) = 217, 11 px apart, and 'Our casualties passed' (145) + '5 000 000' (71) = 216, 12 px apart.: Measured with the game's fonts (scratch/phases/E1/build/measure_kinds.py).

**Fallbacks.**

- If Peace-conference hand-overs to the former enemy still come out as 'State lost' (has_war_with still true while the conference moves the states).: In mod1440_tr_taken and mod1440_tr_lost, also count as a treaty a change on a day the other country has capitulated: add 'NOT = { var:tr_c = { has_capitulated = yes } }' to the at-war test (the design's fallback).
- If on_government_change fires before on_ruling_party_change, so both lines are written.: Write the government line one day late: keep the day in mod1440_ev_gov_day and write it from the daily round when mod1440_ev_party_day is not that day.
- If game.log shows on_recall_volunteers with other scopes (FROM is not a country, or the scopes are swapped).: Swap ROOT and FROM in the hook, or remove kind 44's hook (the kind stays in KINDS).
- If The tooltip of the top bar button shows '[?mod1440_rec_last_k.GetTokenLocalizedKey]' raw or empty.: Drop the words from the tooltip, so it reads 'Newest: <name>, <date>'.
- If The lighter band of new lines does not read as 'new' against the day bands (the user's judgement).: Keep the day band and put a small yellow mark at the row's left edge (GFX_1440p_SG_tile_30x24 or a text icon) on the new rows instead.
- If mod1440_chk_list_time shows the folds costing noticeably more than the last check (about 80 ms a view).: Fold in All only (WD_FOLDING = (0,)), or fold runs of the territory log only.
- If error.log shows 'invalid scope' lines from mod1440_of_gone for a fallen general (for_each_scope_loop over a character who no longer exists).: Wrap the loop body in 'limit = { exists = yes }' and write 'Left the service' from the mark only.
- If A click on an officer's name does nothing for a general given his command by effect (a place, not a number).: Run mod1440_of_refs before open_file, as the hooks do, and enter him through mod1440_ch_at.
- If game.log's 'MOD1440 listening: on_government_exiled' line shows ROOT as the host and FROM as the exile (04_mtg_on_actions.txt:444 gives no scopes; 09_aat_on_actions.txt:219 says ROOT the exile, FROM the host).: Swap the two lines: 'Hosting the exiled government of' for ROOT, and 'Our government went into exile in' in FROM's scope.
- If Both 'Annexed' and 'Won the civil war against' appear for one civil war (on_civil_war_end_before_annexation fired after on_annex, against its comment).: Move the line to on_civil_war_end and drop the Annexed line there by removing the last main-log line when it is annexed with b = FROM on the same day.

**Not seen in game.**

- Everything of this round: the split by has_war_with, the 13 new kinds and their 6 hooks, the officers' daily marks, the casualty steps, part n and its grow line for an older save
- The list: the day column, the bands, the new-line band, the folds and their counts, filter 8, the country and officer buttons over the flag, face and name (the transparent skill_transparent hit sprites at 276, 260 and 208)
- The pane: banded tables, the chronicle's newest marked lines and 'Read the chronicle', the compact honours
- The red badge and the tooltip with GetTokenLocalizedKey; the state card's treaty wording
- Volunteers, a civil war won, fighting on after capitulation and a government back from exile: no effect causes them on a paused January 1936 (no send_volunteers effect exists), so they are left to a played game

Shared files touched: `interface/mod1440_ui.gfx (block '# --- E1 ---' at the end: stripe and pick 1198x34, head 260x28, hit 276x28, 260x28 and 208x28, head 384x26, stripe 384x26 and 384x46, bar 116)`, `tools/check_effects.py (block '# --- E1 ---': mod1440_chk_treaty, _treaty_run, _level, _cipher, _exile, _old3, _sizes3)`, `tools/build_managers.py (one line in D7's top bar scene, marked '# --- E1 ---': the handle hides rec_badge_war)`, `tools/scenes/war_diary.json and tools/scenes/top_bar.json (generated)`.

**Game check.** `tools/Invoke-GameCheck.ps1 war_diary wars`

Checklist for the game checker:

1. 1. Title strip and tabs as before (Germany's flag, Records, German Reich, 'Kept since 1 January, 1936 - 0 days on record'). The War Diary tab has the gold chevrons, and each tab opens its page.
2. 2. The list has no rows of its own for days. The date (hoi_16mbs) stands on a day's first line only, all lines of a day share one band, and two days have different bands. 'The record begins' sits on the lighter band of a new line until the window has been closed once; after that it is on the day's band.
3. 3. Close and reopen the Records after a day with a line: the new lines are on the lighter band (pick). Does it read as 'new' against the day bands?
4. 4. mod1440_chk_war: 'War declared on' Poland with its flag (41x26) and name. Click the name: only Poland's lines show, 'Poland: lines 1 - N of N' stands in the head bar, the Country and Officer heads are gone and no filter is lit. All brings every line back.
5. 5. mod1440_chk_state2 (Danzig, at war): 'State taken' with the plate that moves the camera, Poland in the Country column, and the general's face and name. Click his name: the Officers page opens with his file. Wars page: Danzig counts as taken in the war with Poland.
6. 6. mod1440_chk_treaty: 'Handed over to' Austria and 'Received from' Austria, also under Territory, with no general. Niederschlesien's state card reads 'Received from Austria by treaty on 1 January, 1936, held 0 days' with the grey no-troops line. The Wars page counts nothing for it, and the pane's By treaty row reads received 1, handed over 1.
7. 7. mod1440_chk_treaty_run (four Austrian states): All shows one 'Received from <state>' row with '+3 states' at the plate's right end and the fold tooltip on the plate. Territory lists four lines. The head bar counts four lines for that row.
8. 8. mod1440_chk_level: 'Gained a skill level' with the level reached in yellow at the right end of the words. Compare it with the level in the general's own window and with game.log's 'MOD1440 check: level' line.
9. 9. mod1440_chk_retire, then mod1440_chk_daily: 'Left the service' with his face and name, and The service shows 'Left the service 1'. A second mod1440_chk_daily writes no second line.
10. 10. mod1440_chk_cipher and mod1440_chk_exile: 'Broke the cipher of' Poland (if the full ratio fires the hook) and 'Hosting the exiled government of' Poland, each with its flag. Note which lines came. For exile, also note the 'MOD1440 listening: on_government_exiled' line in game.log: which country is ROOT and which FROM.
11. 10b. Hover a long name on a row (a state, a person, a country of the playset): it stays on one line and ends in dots; nothing wraps into the next row.
12. 11. The pane: The campaign as banded tables under three head bars. 'At war today' equals the number of enemies on the Wars page (rule 3: the game's own war list in the diplomacy view). Wars begun and Wars ended match the Wars page rows. 'Skill levels' counts the levels gained.
13. 12. The chronicle: mark three lines with their boxes. The pane lists them newest first (date in grey, icon, words, name), and 'Read the chronicle' opens the Marked filter. Unmark them all: the two lines that say how to mark come back.
14. 13. Battle honours: the four switches toggle in two rows; By themselves and Cited by you form one table row; the last citation stands under them.
15. 14. Kept has two lines. Hover the head bar's 'lines 1 - N of M': its tooltip carries the Kept text.
16. 15. mod1440_chk_fill, then the arrows: 200 lines a page with no day rows, 'lines 1 - 200 of M'. Scroll the list to its end. Run mod1440_chk_list_time and mod1440_chk_card_time and compare their game.log times with the last check's.
17. 16. Top bar: a War and peace line written while the window is closed (mod1440_chk_war with the Records closed) turns the count red. The tooltip says 'N new lines since you last closed the Records, K of war and peace' and 'Newest: War declared on Poland, 1 January, 1936'. Open and close the window: the badge clears and the count is yellow again for a non-war line.
18. 17. mod1440_chk_old3, then open the Records: mod1440_chk_sizes3 in game.log reads ev, tr and kp n as long as their dates. No line is on the lighter band, no 'Left the service' line appears for an officer gone before, and no casualty line appears for steps already passed.
19. 18. error.log: no line that names the mod, no 'invalid scope for var', no 'Could not find sprite type', no unknown trigger or effect (has_war_with, casualties_k, is_general_captured) and nothing from on_recall_volunteers.

**Tests.** build.ps1 -Check war_diary: 254 passed, 0 failed (59 skipped) after gate B; build_managers.py --check clean; war_diary rendered again (default, follow)
<!-- end generated: build -->

## Close

- [x] Engine Facts rows for what the checks taught (X50 to X55)
- [x] `wiki/Scripted-GUIs.md`: the page, its values and gaps
- [x] README and Workshop description; `version` 1.6 in `descriptor.mod`
- [x] Scene file and recipe (`tools/scenes/war_diary.json`), reference capture
- [ ] The `log` lines of the landing, airborne and ace hooks taken out once each was seen in a game
- [ ] The tester's judgement

## Another map (2026-10-13)

Road to 56 replaces `history/states`: 1143 states for the game's 1081, with other numbers for many. Of the 1495 points of the game's table 223 were in another state there, 252 had another value, 220 were no victory points, and 597 points of that map were not in the table. `python -I tools/make_game_tables.py --mods` now also writes `tools/victory_points_mods_table.py` when the playset has states of its own (1860 points). `mod1440_vp_map` counts the states of the loaded game, and `mod1440_vp_sync` and `mod1440_vp_scan` take the table of the map with that number (`_0` the game's, `_1` Road to 56's); a change of table is a change of version, so the copy is taken anew without a line.

Seen with the user's playset as the United States: "1143 states, table 1", 1860 points copied; at war with Mexico, Monterrey (another state and value than in the game's table), Tampico and Eureka (points only that map has) each gave a line, and the war's file counts 2 taken and 1 lost. [Compatibility](../Compatibility.md).

## Redesign build (2026-10-16)

Status: **built and checked by render and tests; not seen in game.** The design of the redesign pass (`scratch/redesign/e-diary-wars/` of the main repository, approved by the user with every decision chosen) built through `tools/build_records.py`: the frame of the Records window, the War Diary, the top bar button and the state card here; the Wars page in the [E4 notes](E4-war-ledger.md), the honours in the [E6 notes](E6-unit-honours.md).

**The frame** (every page): a title strip 3..59 with the country's flag (`GFX_shield_medium` at 0.8, `[ROOT.GetFlag]`), "Records", the country's name in a fixed box of 420, "Kept since ... - N days on record" (`mod1440_rec_days`, worked out when the window shows) and Close; a tab bar 64..108 with tabs of 236x44 on `GFX_1440p_SG_tab_236x44` (the intel ledger's tab, two frames: the page in front has the gold chevrons), in the order War Diary, Wars, Officers, Government (the page numbers a save keeps are unchanged: `TAB_ORDER`), each with its family's icon, its name and a live count (lines of the main log, enemies today, the Officers page's `OF_TAB_COUNT`; Government none). What each page is for is its tab's tooltip. Every page has the body 14,116 to 1666,1206 (`REC_BODY_*`). A fifth tab place is free for an Aces roll.

**The War Diary:**
- A card of 1172 with seven filters (All, the five families, Marked) and page arrows `<` `>` on the game's sort button at 136 and 40 px; a bar of heads with "lines 1 - 200 of N".
- **Day headers:** `mod1440_wd_list` puts a row for the day before the first line of each day (`hd`, the date, "N lines"); the 200 rows of a page include them. The arrows keep the starts of the pages seen before (`mod1440_wd_back`), since a page holds fewer than 200 lines.
- **A line:** the family's icon, the words (240), then a state or a victory point on a plate that moves the camera, an officer with his portrait at 0.15 and his name, or another person by name; the country with its flag at 0.5 and its name (in its column, or at 290 for a line about a country alone); the officer on the spot with his portrait; a box at the end. A portrait is copied into the page (`mod1440_wd_ap`, `_cp`) from the officer's `mod1440_p`, looked up when he has none.
- **Marked lines:** the box marks the line in both logs (each line has a number of its own, `id`, the same in both logs for a line in both) and copies it into a chronicle `mod1440_kp_*` of up to 300 lines, kept in the order of the days and never trimmed; a second click takes the mark off and the line out. The Marked filter reads the chronicle. Only the mod's own variables are written. People named in the chronicle are put right with the logs when the game's list of characters changes (`places()`).
- **The lines of one state:** filter 7, opened by "Its lines" on the state card; the state's name stands in the head bar.
- **The campaign** (468 wide): War and peace in four tiles; Ground as three rows (states, victory points, capitals) with taken, a bar of taken / (taken + lost) and lost; The service in four tiles; the marked lines. **Battle honours:** four switches, two tiles (by themselves, cited by you), the last citation. **Kept:** the length of each log.
- **Logs of 1000 lines each** (`LOG_KEEP`, 500 before).
- **The top bar button:** 168x36, "£army_experience Records" and a badge with the main-log lines written while the window was closed (`mod1440_rec_new`, cleared by `mod1440_rec_close`).

**Records already in saves:** `mod1440_ev_grow` gives the lines of an older save a mark of 0 and a number below zero of their own, each log apart; the honours get their new switches (landings and airborne on, a great city off) and the old count of honours stands under "by themselves"; the wars get theirs in `mod1440_wr_grow` ([E4](E4-war-ledger.md)). `mod1440_chk_old2` of `tools/check_effects.py` makes a game look like that.

**Deviations from the design:**
- The tab's count stands at the tab's right end and the name at its left, not as a centred group: both are texts over the button (`alwaystransparent`), a button's own text being one font.
- Ground has one green bar per row on its dark ground, without the orange bar under it: a progress bar draws its background over what lies beneath, so the dark part is the share lost.
- The mark is two buttons (an empty and a ticked box, static frames) with `_visible` triggers on the row's `mod1440_wd_k^i`, the confirmed pattern, instead of one button whose frame follows the row.
- The badge counts the lines written while the window is closed directly (`mod1440_rec_new`) instead of a total less the value at Close.
- Country names on the lines stand in white, as the mock-up drew them; people and places in yellow.

**Fallbacks** (what the game check may show):
- Flags and portraits by row index (`[?mod1440_wd_b^i.GetFlag]`, `[?mod1440_wd_ap^i.GetTokenKey]`, open since the design): if a row shows the plain shield or the unknown leader everywhere, the country goes back to `GetNameWithFlag` text and the lines lose their faces (the rows keep the place the portraits had).
- The tab sprite (a `corneredTileSpriteType` of two frames on a button whose frame follows a variable): if both frames look alike, the tabs take `GFX_sort_button_140x29` stretched as before.

**Not seen in game:** the whole build. **Measured without the game:**
- **Save size.** A binary save keeps each element of an array as an entry of its own named `<array>^<index>`, the name's length plus 16 bytes (read from the user's `USA.hoi4` of 2026-10-16: 11 778 entries of the mod, 381 838 bytes, 0.37% of 104 MB). Two logs full: 394 KB with 500 lines of 12 parts, 921 KB with 1000 lines of 14 parts (+527 KB). The chronicle full: +137 KB. The diary's page of 200 rows: +52 KB. Everything full, with 200 finished wars and 30 officers who took something in 5 wars each: +776 KB, 0.75% of that save; 60 officers in 20 wars each add 163 KB more. `scratch/redesign/e-diary-wars/build/save_size.py` of the main repository.
- **Daily cost.** Nothing new loops over a log on a day the window is closed: a line costs a number, a counter on the state it names and, when a log is full, 14 removals at index 0. The daily round adds `every_controlled_state` over the player's states (the held days of the state card) and the enemy's casualties in the loop over the enemies. With the window open the page is made again each day: the All view walks both logs (2000 lines instead of 1000) and copies 200 rows of 18 parts. The view of 200 out of 500 lines was copied 50 times within a second (X48); the new view is about four times the walk, so roughly 80 ms a day while the page is open, by estimate. To be read in a game: `effect mod1440_chk_fill` (both logs to 1000 lines), then `mod1440_chk_list_time` and `mod1440_chk_card_time` (20 views, 20 files between two lines of `game.log`).

**Game check:** `tools/Invoke-GameCheck.ps1 war_diary wars`, then in a live session (`tools/Invoke-GameSteps.ps1 -Start`) the effects of `tools/check_effects.py`. The tester's checklist:

1. The title strip: Germany's flag, Records, German Reich, "Kept since 1 January, 1936 - 0 days on record"; the tabs in the order War Diary, Wars, Officers, Government; the War Diary's with the gold chevrons; the counts.
2. Each tab opens its page, the chevrons move to it, its tooltip says what the page is for.
3. The diary's lines stand under a row for their day, with the date and the number of lines.
4. A line about a country: its flag (41x26) and name. A line about an officer (a promotion by effect): his face and name.
5. A state taken (`mod1440_chk_state2`): the plate moves the camera; the general's face and name at the right.
6. The box at the end of a line: ticked on a click; the Marked filter lists the line; a second click takes it out (`mod1440_chk_mark` does the same from the console).
7. `mod1440_chk_fill`, then the arrows past 200 rows, "lines 1 - N of M"; `mod1440_chk_list_time` and `mod1440_chk_card_time` in `game.log`.
8. The campaign card: the tiles and the three bars of ground; the four honour switches toggle; landings and airborne ticked, the great city not.
9. The top bar button with the badge of new lines; closing the window clears it.
10. The state card: the flag of whom it was taken from, the days held, "by the troops of" with the general's face, "Its lines" opens the diary on that state.
11. `mod1440_chk_old2`, then the Records opened: `mod1440_chk_sizes2` reads every newer part as long as the logs and the wars; the honours switched as above.
12. `error.log`: no line that names the mod, no "invalid scope for var", no "Could not find sprite type".

### Fix round 1

- Kept text keys (user's USA save, `records_wardiary.png`, `records_wars.png`): a variable holds `token:<key>` as the key's number in the game's table of names, the save keeps the number, and the mod's names are numbered in the sorted order of `mod1440_tokens.txt` (the save's 333 kinds are 22336 + their rank among the 39 sorted kinds, matching the counters exactly). The redesign added some 3500 names before `mod1440_ev_*`, so every kept kind, point name and portrait named another key ("GFX_portrait_..." as What happened, Eisenhower on every line). Now each record keeps a dictionary of its kept keys with their numbers (`mod1440_tk_k`, `mod1440_tk_v`, codes in `_kc`/`_vc`, `kept_tokens()` in `tools/build_records.py`); `mod1440_ev_grow` checks it first (every kind, every 16th point name) and `mod1440_tk_fix` writes the logs again by the old dictionary; a save older than the dictionary gets its kinds by the one base where every line's family agrees (it finds 22336 in the user's save), and a point whose name cannot be recovered names its state. Re-test: the user's save, Records open while paused: What happened reads words again, `game.log` has "MOD1440 records: the numbers of the kept text keys had moved" once.
- Flags (`records_wars.png`): an icon whose image is `[<country>.GetFlag]` came out at 82x52 at scale 0.5 and 0.8 alike, over the rows and the title. Small flags now use the game's `GFX_flag_small2` (41x26, as Kaiserreich does) unscaled, the title flag `GFX_shield_medium` at its size with the title moved 8 px right. Re-test: flags on the diary lines, the war rows and the state card 41x26 inside their rows.
- Tabs (all pages): a `corneredTileSpriteType` draws its whole texture and takes no `frame`, so each tab showed both frames of `tab_small.dds` stretched. The frames are cut apart (`rec_tab_off.dds`, `rec_tab_on.dds`, `rec_sort_off.dds` by `tools/stretch_background.py`), each page writes its own tab with the chevrons, and the diary's filters use the game's `GFX_sort_button_140x29` (spaced 144). Re-test: one tab with gold chevrons, the page in front; the chosen filter with chevrons.

## UX review round (2026-10-17)

Opened with `/phase E1 War Diary`. The user: "I want this looked at from a UX view. Is the information it stores relevant, could it be expanded to store more info? Are there any UI improvements that could be made?" A review of the built page, not a new one: the designer judges the 39 kinds of line, proposes what else script can reach and what the page should do better, with the cost of each.

### Roles and handoffs

- Handoff folder: `scratch/phases/E1/` (not in the repository)
- Builder: `builder-script` (a generated page; the log's shape is a save contract). Started 2026-10-22 in the main tree of this repository (D7 is in the initial commit of the split).
- Design page: https://claude.ai/artifact/QhAoDf1vp7YntBu8PBfcgy (round 1, 2026-10-17; the designer's handoff `scratch/phases/E1/design.json`, thirteen figures, `mock_page.py`, `mocklib.py`, and the save-reading scripts `read_save*.py` that gave the counts)
- Contracts written (hotkeys, shared rows, shared files): yes, `scratch/phases/E1/contracts.md` (2026-10-17): the order of `KINDS`, `LOG_ARRAYS` and the page and filter numbers are save contracts; the Records frame is shared by four pages; the logs are read by the Wars and Officers pages too.
- Worktrees: main tree

### Review (2026-10-17)

Designer, 2026-10-17: verdict refine. Judged on the user's own save (`USA.hoi4` of 2026-10-16, read without changing it; the totals agree with `screenshots/records_wardiary.png`): 30 of the 39 kinds kept; state and capital taken and lost split by `has_war_with` (70 of 152 state lines were hand-overs in peace, and the card read "States lost 54" where battle losses were about 7); the faction line not written for a new subject (17 of 27); the nameless ace lines quieted until E5; landings and airborne lines never counted (a fault in `recording()`: a family-2 line of the main log alone is counted in neither log). Thirteen new kinds from hooks and the daily round (received and handed over by treaty, left the service, captured, volunteers, exile, cipher, civil war, fought on, casualty steps) and a number on a line (part `n`, +73 KB in a full save). The list: the day in a column on its first line and no day rows (200 lines a page instead of 163), runs of three or more states folded in All (the campaign's 318 lines in 207 rows instead of 401), new lines on the lighter band, a country's name opens its lines (filter 8), an officer's name his file. The pane as banded tables with Ground in battle and by treaty, the chronicle's newest marked lines in view, the honours compact; the badge red for a war-and-peace line with the newest line in the tooltip; the state card tells a treaty from a battle.

- 2026-10-17, gate A passed: every addition names its row or id; every figure group has the current build and the proposal at the same crop (the page has no vanilla counterpart); the contracts are kept, the one deviation named (the Wars page's taken and lost per enemy no longer count hand-overs); the game-only items are under `openInGame`; the playset report was read. Sent to the user with eight decisions.

### Gate B (2026-10-22)

- 2026-10-22, gate B passed after one round with the builder: `build_managers.py --check` clean, `build.ps1 -Check war_diary` 254 passed, 0 failed; the whole diff of the generated files read; the six figure groups match their mock-ups (flags and portraits are blank in the renders, the renderer's blind spot). Sent back and fixed: kind 49 from `on_civil_war_end_before_annexation` (fires before `on_annex`, vanilla `04_mtg_on_actions.txt:194`), so the Annexed line is skipped by a documented order; the name boxes of a row `fixedsize` (W28); the chronicle's words 208 px and fixed (longest kind 202 px); every kind measured at most 228 of 232 px; `on_government_exiled` logs its scopes. Design page republished with the build renders (version 2).

### Decisions (2026-10-22)

The user, with `/pages-phase E1 from 4`: "Go with the recommended options to the questions asked in the artefact". All eight recommendations are taken (`scratch/phases/E1/decisions-final.json`):

1. Changes of hands with a country we are not at war with get their own words, "Received from" and "Handed over to"; Ground counts battles only.
2. Ace lines: a counter only until E5 can keep an ace.
3. The day stands in a column on its first line; no day rows (200 lines a page).
4. Runs of three or more states of one day, kind and country are folded into one row (+N states) in the All view; every state stays under Territory.
5. All thirteen new kinds of line (39 to 51).
6. A click on an officer's name opens his file on the Officers page.
7. The right pane: banded tables, the chronicle in view, the honours compact, 400 wide.
8. A number on a line (part `n`), +73 KB in a full save.
