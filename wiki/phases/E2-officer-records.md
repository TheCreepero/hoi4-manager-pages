# Phase E2: Officers

One row per general and admiral with a service record the mod keeps, a card for the chosen officer, and decorations the player awards. The second page of [the Records](../Roleplay-Pages.md). Status: built and checked in game on 2026-10-12; awaiting the tester's judgement. Not seen: a battle counted, and an officer's record after a save and a load. How each value was checked is in [Scripted GUIs](../Scripted-GUIs.md), "The Records".

## Scope

- **Vanilla has:** the general's portrait, skills and traits in the selection list and on the army badge, one officer at a time. No table of all officers, no record of what an officer did, no date of anything. The Armies list of Army Readiness (D6) shows generals with troops and what they command today.
- **The page:** every officer in one table that sorts, with what the mod wrote down about him since it has been active.
- **Out of scope:** a portrait (none can be read); a trait by name (the page shows how many of each kind; see "Later"); selecting the officer's army (a row cannot select); renaming (no text field).

## The page

| Part | Size | Holds |
|---|---|---|
| Filter row | 1640x40 | All, Army, Navy, With a command, Decorated, Former |
| Table | 1010 wide, rows 40 high, 27 in sight | one row per officer; a click on a column head sorts, a second click turns the order; a click on a row chooses the officer |
| Card | 610 wide, beside the table | the chosen officer |

| Column | Width | Source |
|---|---|---|
| Name | 290 | `[THIS.GetName]` (X10) |
| Rank | 130 | Field Marshal, General or Admiral: three texts on the row, each shown by a `_visible` trigger on `is_field_marshal`, `is_corps_commander` or `is_navy_leader` (X39). `GetRank` is empty for every officer (X42) |
| Skill | 50 | `skill_level` (X21) |
| Attack, Defence, Planning, Logistics | 4 x 45 | `attack_level`, `defense_level`, `planning_level`, `logistics_level` (X21); for an admiral `maneuvering_level` and `coordination_level` take the last two |
| Traits | 50 | `num_traits` (X21) |
| Command | 70 | `num_units` or `num_ships` |
| Won, Lost | 2 x 55 | the record |
| Decorations | 120 | up to five small medal icons |

**The card** of the chosen officer:

- Name, rank, skill, the four levels.
- Traits by kind: basic, personality, terrain, status, assigned of the most he can take (`num_basic_traits` and its siblings, `num_max_traits`).
- Command today: divisions, battalions, divisions fighting, by kind (as the Armies list), or ships.
- Record: commissioned on (or "before the record began"), promoted on, last skill level on, battles won and lost, states taken under him.
- Decorations with their dates, and the buttons Award (one per grade) and Take back the last.
- His lines of the War Diary, newest first: the log filtered by subject.

## The record

Written by hooks into the officer himself. A general, an admiral and an advisor each keep variables of the mod, also through a promotion and a retirement (X32):

| Name | Written by | When |
|---|---|---|
| `mod1440_of_since` | `on_unit_leader_created` (the leader, FROM the country) | the date; officers of the start of a game get none and read "before the record began" |
| `mod1440_of_prom` | `on_army_leader_promoted` | the date |
| `mod1440_of_lvl` | `on_unit_leader_level_up` (ROOT the leader, FROM the country) | the date of the last level |
| `mod1440_of_won`, `mod1440_of_lost` | `on_army_leader_won_combat`, `on_army_leader_lost_combat`, and the two navy hooks | plus one |
| `mod1440_of_states` | `on_state_control_changed`, for the general with the most divisions in the state: `num_units_in_state@var:<the state>` in each general's scope (X44) | plus one |
| `mod1440_of_dec_1` to `_5` | the Award button | the date; cleared by Take back |

- **Seen firing:** the hooks of creation, promotion and skill level, each in the officer's scope with FROM his country (X43). An officer the game starts with gets no "commissioned" date, as planned.
- **Not seen:** the four battle hooks. They need fighting, so the two counts are checked in play.
- **What a battle is:** the hook does not say where or against whom, so the page counts and does not list. Whether a field marshal is counted with his general is seen only in play.
- **A retired officer keeps his record** (X34): he leaves the game's list of officers and stays readable from a list of the mod. The page keeps its own array of every officer it has seen, and a filter "Former" shows those no longer serving.
- **Through a save and a load:** not tested, because no check saves. It is the one thing the whole page rests on that has not been seen.

## Decorations

A decoration is a record of the mod: five dates on the officer. It gives no bonus and changes nothing the game works with.

- **Five grades**, awarded in any order by the player, each at most once. A line goes into the War Diary.
- **Names and icons (decision 5 of the Records):** either five neutral names with frames of the game's default medal strip (`GFX_medal_icon_default`), or the game's own medals of the country: vanilla has 103 unit medals in national sets, with names and icons. The second needs a table of sets per country in the tool and follows the vanilla triggers that say which country has which set. Start with the first; the second is an addition.
- **Not planned:** a cost in command power or political power for a decoration. It could be added; then it is a real spending and is said so in the tooltip.

- **2026-10-13:** the medal strips are sprites of this mod on the game's pictures, `GFX_1440p_medal_<set>` in `interface/1440p_ui.gfx`, made with `python -I tools/list_medals.py --sprites`. The game's own sprites are in `interface/medals.gfx`, and a mod that brings a file of that name drops the sets its copy lacks: with Road to 56 the game logged 19 lines for Ethiopia's (L10).

## Data and script

A section `officers()` of `tools/build_managers.py`.

| Name | What |
|---|---|
| `mod1440_of_known` | every officer the page has seen, serving or not: `army_leaders` and `navy_leaders` are added to it once a day |
| `mod1440_of_list` | the officers of the chosen filter in the chosen order, sorted with key arrays as the States page sorts (X22). The list is scoped to the officer, so a row reads his values and his record directly; an array of the country in a row needs `ROOT.` before its name (X36) |
| `mod1440_of_sel` | the chosen officer, held by the country: a row's click runs `ROOT = { set_variable = { mod1440_of_sel = PREV } }` (X33, seen). The card's name is `[?mod1440_of_sel.GetName]`, his record `[?mod1440_of_sel:<variable>]`, and his game values (skill, command) are copied by an effect that enters `var:mod1440_of_sel` |
| `mod1440_of_card` (effect) | fills the card and its diary lines; runs on a row click, on Award and once a day while the page is open |
| `mod1440_of_award_<n>_click`, `mod1440_of_takeback_click` | the decoration buttons |

Commands new to the test's list: `is_field_marshal`, `is_corps_commander`, `is_navy_leader`, `is_assigned`, `is_in_array`, `var:` scopes, and loops over the two arrays. The record is variables of the mod on a character, which the rule allows; no command that writes to the game is needed.

## What the probe settled

| Question | Answer | For this page |
|---|---|---|
| A variable on a general | yes (X32) | the record lives on the officer; flags are not needed |
| The country holds a general | yes (X33) | the card of the chosen officer, and officer lines in the diary |
| A held general once he is gone | everything stays readable (X34) | former officers keep their row and their lines |
| `_visible` per row | yes (X39) | the rank as a word |
| `navy_leaders` in a list | yes, like generals (X42) | admirals in the table |
| Troops in a state held by a variable | yes, `@var:` (X44) | "states taken" per general |

## Checks

1. **Paused, by effects:** promote a general (`promote_leader`), give a skill level, create one: the three dates are today's. Award and take back each grade. Sort by every column; the order is compared with the numbers.
2. **Values against the game:** skill and the four levels against the army badge (as X21); traits against the general's tooltip; command against the army's division count.
3. **Needs time:** battles won and lost, states taken. A week of fighting in the user's game, or decision 3 of the Records; the hooks log to `game.log` until seen.
4. **A retired general** (`retire`): the table, the card and the diary after it. The probe saw his name, skill and variables stay readable; a general who dies in the field is still to be seen.
5. **A save and a load,** if the user allows a check to save under a file name of its own, or in the user's own game: the record of an officer after loading.

## Later

- **Traits by name.** A text per vanilla trait through `has_trait`, joined in the card's tooltip. About a hundred traits typed into the tool; other mods' traits would not appear.
- **A portrait frame** with the rank's insignia, if a vanilla sprite suits.

## Decisions

- 2026-10-12: planned.
- 2026-10-12, the user: decorations are the game's own national medals. Built so: the 103 unit medals of the game with the game's own conditions (`tools/unit_medals_table.py`); a country is offered those it has, twelve at most, by name and icon.
- A medal can be awarded to an officer once. No cost, no bonus.
- The card shows seven decorations and seven diary lines; an officer with more keeps them, and the page shows the first seven.
- The rank column reads Marshal, General or Admiral: "Field Marshal" did not fit its 84 px.

- 2026-10-12, the user: "a round of improving the UI ... really polished and fit their purpose really well", with free hands. Done the same day: striped rows with the chosen officer's row marked, numbers under the middle of their heads, and the card as a file: the name in the title font, rank and service in a line, four figures as tiles, the medals side by side at full size with name and date in the tooltip, the medals on offer with their own icon and an "awarded" mark on a button that no longer answers. Checked in game and from a cold start (`scratch/checks/crop_p_*.png`, `reference/mod/`).

## Additions of 2026-10-13: portraits, victory points, the lines of a file

The user had installed the build of 2026-10-12, played a war with it and wrote on 2026-10-13: "Overall I'm very happy with the results. I just want more graphical details", with three wishes: an officer's portrait in his file and in the list; a record, in the officer's file and in the War Diary, of each battle over a victory point won or lost and of each state captured; a file for a war as there is one for a general, with the flags and maybe the leaders of each side and some statistics.

- **Portraits.** The plan had "a portrait (none can be read)" under out of scope. That stays true for reading, but an icon's sprite can be named by script (`image`, Engine Facts X58), the game declares a sprite for each named character, and `is_character` tells who a character is (X60). So `tools/make_game_tables.py` reads the game's characters into `tools/portraits_table.py` (1619 with a sprite: 1034 generals and admirals, 663 heads of government), and `mod1440_p_officer` goes through the people of the officer's country, then through everybody, and leaves the sprite's name on him as a text key (`mod1440_p`), once per officer and again when the table changes.
  - A row is 48 px high instead of 30 and begins with the portrait at 34x46; 22 officers show before the list scrolls (35 before). The file has the portrait at its full 156x210, top left.
  - **Decided:** the game's own sprites by name, not copies: no image is added, and a character of a DLC the player lacks is simply not found. An admiral shows his navy portrait, a general his army portrait, whichever the game has otherwise. Eight characters whose names hold a hyphen are left out (a text key may not take it). A general the game made up shows the game's unknown leader.
- **The file** has six figures in two rows beside the portrait: skill, battles won and lost, states taken, victory points taken and lost (new: counted for the general with the most divisions in the point's state). Its last part, "In the War Diary", now also lists the states and victory points he was at, with their names; five decorations are listed by name instead of seven (the rack still shows seven medals).
- **Checked in game on 2026-10-13** (checks 3 and 4 below). The fault with `is_character` and its mending are in the [E1 notes](E1-war-diary.md).
- **After the check:** the band of the chosen row had a scalloped edge (the texture is a disc; its border is now 12 instead of 6, Engine Facts G17; seen right on the History table in the cold start, the same sprite at another size). The arrow of the sorted column stood over the last letter of "Skill": it is now drawn at about half its size on the upper right corner of the head. Both were seen in the second check of the day: the band a clean pill on a row of 48 px, the arrow clear of "Skill" (`scratch/checks/b_of1-*`).

**Left unseen:** an officer of another country (`tag ITA`); a portrait after a save and a load (the text key is kept on the officer, as the rest of his record).

## Officers other mods add (2026-10-13)

The user had deployed the build and tested with other mods: "generals added by mods don't show up in the list. I tested this with the Add USA Generals which adds it's new generals with an event on the 9th of january 1936. I would really like this issue fixed."

- **The cause.** The mod defines its characters bare and gives them their command by event (`add_corps_commander_role`). The game gives such a leader no number: `THIS` is -21474.83648 for every one of them, and the arrays `army_leaders` and `navy_leaders` hold that same nothing in his place ([Engine Facts](../Engine-Facts.md) X66). The list was built from those arrays; a loop over them stays in the scope it was in for such an element, so the 73 were passed by without a word. The game's own focuses add generals the same way (125 uses of these effects in its files).
- **The fix.** A variable holds a character who is no unit leader as his place in the game's list of characters, and a place leads to a unit leader too (X67). `mod1440_of_refs` gives each leader without a number a mark and enters every place until all marks are met (75 found at places up to 5146, in less than a second); the place is kept on him as `mod1440_ch_at`. `mod1440_of_me` leaves in `of_me` what a variable can hold of the officer in scope, and everything that kept an officer through `THIS` or the arrays goes through it: the list, the row click, the general on the spot (`mod1440_of_best`), the three hooks, and the armies list of Army Readiness. Officers are collected with `every_army_leader` and `every_navy_leader`.
- **Stale places.** A place lasts as long as the game loads the same characters. Everybody kept by place carries it on himself; the character at the highest place kept is asked each day whether it is still his, and if not everybody is found again and the logs, the list, the chosen officer and the offices of the Government page are put right (`mod1440_ch_remap`). The advisors and heads of government of the diary and of the Government page were kept by place all along, without anybody knowing that it could go stale: they are marked too, also those a save of an earlier build holds (`mod1440_ch_adopt`).
- **Commissioned.** `on_unit_leader_created` does not fire for these leaders. The daily round takes an officer it meets for the first time as commissioned that day (the day after the effect, as the round runs at midnight): eight lines at most for one day, then one line "More officers commissioned". The first round of this build in a game saved before takes the officers it had missed without a date and without lines: nothing says when they came.
- **Portraits.** `has_character` is false and silent for a name the game does not know (X68), so the lookup may name the characters of mods. `tools/make_game_tables.py --mods` wrote `tools/portraits_mods_table.py` from the user's playset: 858 characters of five mods. A character whose file gives him no role is taken as an officer by effect.
- **Decided:** the game's own characters keep the game's sprite name where a mod changes them (it is there in every game). A mod's file is taken as a country's when its name is a tag or holds one (`AUGA_USA`), so that its people are asked for before everybody else's.

**Left unseen:** a commander without a number in the armies list of Army Readiness and as the general on the spot; the user's whole playset; a real change of the character files.

## Game checks

| # | Date | Build | Checked | Result | Screenshot | Taught |
|---|---|---|---|---|---|---|
| 1 | 2026-10-12 | `1a08bb3` +dirty | the page as Germany: 27 officers; a click on a row; Award twice; the Former filter after a retirement by effect | the table and the card as planned; Iron Cross and Knight's Cross listed with the date; the retired general under Former as "no longer serving" | `scratch/checks/crop_e1_5.png`, `crop_e1_6.png`, `crop_e1_18.png` | X51 |
| 2 | 2026-10-12 | the same game | nine days at war with one army under a general | no battle was fought: Won, Lost and the states taken stayed 0 | - | X55 |
| 3 | 2026-10-13 | `9c832ae` +dirty | live session: the list and a file; Rundstedt given the army, then Breslau lost and Niederschlesien lost and taken back by effect; a general made by `create_corps_commander` | 26 officers each with a face of his own in the rows (34x46), the admirals in navy uniform; Rundstedt's file with his portrait at full size, "commands 30 divisions", states taken 1, points lost 1 and the three lines with the names of the places; the made-up general with the unknown leader and "Commissioned" on the day | `scratch/checks/of2-*`, `of3-*`, `of4-*` | X58, X60, G17 |
| 4 | 2026-10-13 | the same build, cold start through `tools/Invoke-GameCheck.ps1` with ten other scenes | the page in a new game; `error.log` | 22 rows with portraits before the list scrolls; every expected widget found where the layout puts it; no line names the mod | `reference/mod/officers-panel.png` | - |
| 5 | 2026-10-13 | `9c832ae` +dirty, with the mod "Add USA Generals AI REWORK" loaded beside this one (allowed by the user: "Yes, start it now") | as the USA on 1 January 1936: the mod's event fired from the console; then what script can learn about its 73 leaders, by throwaway effects that write to `game.log` | the game's arrays and loops count 78 generals and 24 admirals, the mod's list 29; `THIS` and the array elements of the 73 are -21474.83648; they have variables of their own; a place found by search leads to each of them (75 with two made by the check) | `game.log` ("MOD1440 leaders", "loop", "ref", "ids", "legacy", "enc", "step", "scan") | X66, X67, X68, X69 |
| 6 | 2026-10-13 | the same game, the fix written into it | the Officers page; a click on a general of the mod; a medal for him; every kept place and mark moved three on by effect and the search run; ten more characters given a command and the daily round | 104 listed, the mod's generals and admirals among them with their skills, sorted with the others; the file of Troy Houston Middleton; after the made-up change the list, the choice, his Bronze Star and his line "Decorated" as before (75 found again and renumbered, with 120000 places entered, inside a second); eight lines "Commissioned" with names and a ninth without its words (X70) | `scratch/checks/c_of2-*` to `c_of4-*`, `c_wd2-*` | X67, X70 |
| 7 | 2026-10-13 | the finished build, cold start with the same mod; time run from 1 to 4 January (the user's autosave copied first and found unchanged) | the daily round of 2 and 3 January as the USA; the mod's event on the 3rd; the round of the 4th | 29 officers known on the 3rd, 102 on the 4th; "Commissioned" for the first eight with their names and "More officers commissioned"; the mod's officers with their own portraits in the rows and in the file, "Commissioned 4 January, 1936"; Government and Army Readiness as before; no line of `error.log` names the mod | `scratch/checks/d_wd-*`, `d_of-*`, `d_gv-*`, `d_ar-*` | - |


## Close

- [x] Engine Facts rows; `wiki/Scripted-GUIs.md`
- [x] README and Workshop description
- [x] Scene file and recipe (`tools/scenes/officers.json`), reference capture
- [ ] Battles won and lost seen counting in a game with fighting
- [ ] An officer's record after a save and a load, in the tester's game
- [ ] The tester's judgement

## With the user's playset (2026-10-13)

- As the United States: 29 officers at the start, 102 after the event of "Add USA Generals" came by itself on 10 January. One of the 29 has no portrait.
- As Germany: 36 officers, six of the first 23 with the outline of the unknown leader. Road to 56 gives 1451 portraits as a file (`large = "gfx/leaders/GER/r56_portrait_...dds"`) and not as a sprite, and script can show a sprite only. Not solved: a sprite of this mod for each file would log a missing texture for every player without that mod. [Compatibility](../Compatibility.md).

## Redesign build (2026-10-16)

Status: built and checked by render and tests; not seen in game. The design, the user's decisions and the mock-ups are in `scratch/redesign/e-officers-gov/` of the main repository (review page of 2026-10-16); the renders of the build beside them in `build/`.

**What was built** (`tools/build_records.py`, `officers()`; `tools/make_game_tables.py`):

- The page fills the body of the Records frame, `REC_BODY_X, REC_BODY_Y, REC_BODY_W, REC_BODY_H = 14, 116, 1652, 1090` (54 px less than before): the six filters at the top of the body, the heads at y 154, the list from y 186. 21 rows of 48 in sight (22 before).
- **Row** (948 + 30 scroll): portrait 34x46; the name, in yellow for the chosen officer; under it in grey the rank and the status, one of 13 texts by `is_field_marshal`, `is_corps_commander`, `is_navy_leader`, `is_general_captured`, `is_leading_army_group`, `num_units` / `num_ships` and the day last seen ("General - commands 30 divisions", "leads an army group", "captured", "no longer serving", "unassigned"). Skill, the four levels under the game's icons `GFX_trait_attack`, `_defense`, `_planning`, `_logistics` on the head plates, up to six trait icons and "+N", Cmd, Won, Lost, up to three medals at half size. The rank column is gone. The button of the row is the portrait and the name, 300x48, drawn with nothing (`GFX_1440p_SG_hit_300x48`, the game's `skill_transparent.dds`).
- **Trait cache on the officer** (`mod1440_of_traits`): the array `mod1440_of_tr` of text keys, those with an icon first, padded to six with `unknown`; `mod1440_of_tr_i` (with an icon), `_k` (named by the table), `_n` (num_traits when made), `_v` (table version), `_plus` (what the row's "+N" says). The daily round (`mod1440_of_seen`) makes it again only when `num_traits` or the table changed; an officer who serves no longer gets it when the list is made. It is kept on the officer himself, so officers without a number (reached through `mod1440_of_me`) have it too. Icons: `image = "GFX_trait_[?mod1440_of_tr^k.GetTokenKey]"`.
- **Trait table**: `tools/traits_table.py` (182 traits of the game, 7 without an icon; operatives' traits left out) and `tools/traits_mods_table.py` from `make_game_tables.py --mods` (46 traits of Road to 56 for the playset "Reordered Pack"; `jaeger` listed as gone). A general is asked about 174 traits, an admiral about 125, in groups of 16 that stop when every trait he has is found.
- **The file**: five cards drawn as icons in one container (`GFX_1440p_SG_card_662x*`), so that the Award mode can lay one card over two: who he is (portrait 156x210, name, rank, status, Skill and the four levels with their icons; Divisions, Battalions, Fighting, Armoured, Planning; an admiral: manoeuvring and coordination icons, Ships and four ship kinds by `num_ships_with_type@carrier/capital/screen/submarine`), Traits (icon and name of six, "N of M he can take", "+N of other mods", "+N more"), Service record (six tiles, three dates), Decorations (rack of nine at full size with name and date as tooltip, three named; Award..., Take back last) and In the War Diary (eleven lines with the family's icon, every second striped).
- **Award mode** (`mod1440_of_awarding`): Award... hides the rack, the names and the whole diary card, and shows the country's medals over both cards (522 px): plates 306x68, two to a row, the medal at 0.7, the name, an Award button or "awarded <date>". Back to his file, choosing another officer, or losing the choice ends it.
- **Medal strips by token**: a medal picture is one widget per slot, `image = "[?<strip>^k.GetTokenKey]"` with `frame = <frame>^k`, for the row (`mod1440_of_rm`, `_rf`, made by `mod1440_of_rack`), the rack (`mod1440_of_c_dec_strip`) and the Award plates (`mod1440_md_strip`). The strip token is worked out from the set number the decorations already keep, so an older save needs nothing new.
- **Tab count** for the frame: `[?mod1440_of_serving|0]`, the officers who serve today, counted by the daily round.
- New commands in `tests/ScriptedGuis.Tests.ps1`: `has_trait`, `is_general_captured`, `is_leading_army_group`, `clamp_temp_variable` (looked up in the game's `documentation/`).
- `tools/check_effects.py`: `mod1440_chk_traits` (the trait round ten times between two lines of `game.log`, then each officer's cache and new values) and `mod1440_chk_trait_unknown` (a condition on a trait nobody defined).

**Cost.** First daily round after the update: every officer once, at most 174 tests for a general and 125 for an admiral; for the 102 officers of the user's USA game about 16 000 `has_trait` tests once (not measured: `effect mod1440_chk_traits` measures ten rounds). After that one comparison per officer a day. **Save size**, worked out from the binary save `USA.hoi4` (a variable is 16 bytes plus its name; an array element is a variable `<name>^k`): 660 bytes per officer, 67 KB for 102 officers, and about 7.7 KB on the country (the file's copies and the Government seats), together about 0.07 % of the 104 MB save. `common/scripted_effects/mod1440_portraits.txt` grows from 0.65 to 2.7 MB with the advisors of E3.

**Deviations.** 21 rows in sight, not 22 (the frame's body is 54 px lower). The cards are 240, 108, 184, 220 and 290 high, 12 apart (design: 248, 100, 196, 220, 306, 10 apart), so that all five fit in 1090. Plates are 64 high (the tile of every page), not 56. Trait icons stand 24 apart (design 27) so that "+N" fits before Cmd. Three decorations are named under the rack (the card has room for three). The design's third array of strips on the officer is worked out from the set number instead (older decorations need nothing).

**Not seen in game:** the composed trait icon in a row and in the file; `frame` and `image` together on one icon; `has_trait` with a name the loaded game lacks; what `num_max_traits` counts and how `avg_unit_planning_ratio` is written (the file shows it as a percentage of 0 to 1); `num_ships_with_type` in an admiral's scope; `is_general_captured` and `is_leading_army_group` in a row; the transparent row button over 300x48.

**Fallbacks.** If the medal strips show the first frame or nothing: go back to one widget per set and slot with `frame` and a `_visible` on the set (the build of 2026-10-13). If `has_trait` logs an error for a name the loaded game lacks: build without `traits_mods_table.py` (delete it), or only from the active playset. If the row button takes no click: give it the head plate `GFX_1440p_SG_head_300`. If Planning reads 4000 %: drop the `%` format.

Game check: `tools/Invoke-GameCheck.ps1 officers government`. Checklist: `tools/scenes/officers.json`.

### Fix round 1

- Portraits wrong, small or missing in the user's save (`records_officers.png`): the cached `mod1440_p` was a text key whose number had moved (E1, Fix round 1). Every cache of a key now carries the stamp `<stamp>_ep` of `global.mod1440_tk_ep`, which goes up when the numbers move: the portrait (`mod1440_p_ver`), the traits (`mod1440_of_tr_v`), and the medals (`mod1440_of_md`: `mod1440_of_medals_again` makes the names of the decorations again from their numbers, then the row's strips). A fresh game was right and stays so. Re-test: the user's save, Officers: each general with his own portrait at row size.
- Karl Oesch (`portrait_question.png`): the page shows the game's own portrait of him (`GFX_portrait_FIN_karl_lennart_oesch`); Road to 56 gives him a texture path instead of a sprite (`large="gfx/leaders/FIN/r56_portrait_FIN_Karl_Lennart_Oesch.dds"`), as it does for 2141 characters, and a scripted icon can only be given a sprite name kept as a text key. Not changed: the same man, another painting.
