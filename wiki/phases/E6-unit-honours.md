# Phase E6: Unit honours

Lines in a division's own history, written by the mod when the division was part of something worth remembering, or on the player's word. It is the one part of [the Records](../Roleplay-Pages.md) that writes into the game's own records, which the rule allows since 2026-10-12. Status: built and checked in game on 2026-10-12; awaiting the tester's judgement. The probe ([E0](E0-roleplay-probe.md)) saw such a line in a division's History tab; the build was seen reaching the divisions, not read in a History tab again. It needs By Blood Alone, and [E1](E1-war-diary.md) for the territory hook.

## Scope

- **Vanilla has:** a History tab per division (By Blood Alone) that the game fills with battles, and medals the player awards for an entry, at a price.
- **The addition:** entries of the mod's own in that tab: "Took part in the capture of Paris", "Cited by the high command".
- **Out of scope:** a medal given by script (`add_unit_medal_to_latest_entry` gives a medal's bonus without its price, which the rule keeps out); a ship (no scope); choosing one division on a page (script has no list of divisions and cannot tell them apart by name).

## What is known

- `add_history_entry = { key = ... subject = "..." allow = yes/no }` in a division's scope (R11). The key is a text key or plain text. The game's test text shows two things the text can take: `$SUBJECT$` and `$PROVINCE$`.
- Vanilla uses it four times, from focuses, on one random division chosen by its units. Road to 56 uses it from a decision ("cite a unit") with `allow = yes`, which lets the player then pick a medal in the vanilla window.
- A division is reached through its country or through the state it stands in (R10). What can be asked of it: strength, organisation, its main kind of unit, a kind of battalion, whether its template is a reserve.
- The hook `on_add_history` runs in a division's scope whenever it gets an entry, the game's own included.

## The two ways an honour is written

**1. By the mod, when a capital falls.** In the territory hook of E1: if the player's country takes a state that is a capital (`is_capital`), every division in that state gets the entry "Took part in the capture of ...". The player switches this on or off on the Records window; the default is a decision for the user (decision 6 of the Records).

- **The place in the text:** `$PROVINCE$`. The game fills it with the name of the state the division stands in: the probe's line read "... province Ermland-Masuren" (X45). So the entry is "Took part in the capture of $PROVINCE$". A country's name cannot stand in it: `[...]` is shown as written.
- **Whom it reaches:** `every_state_division` reaches every division standing in the state, foreign ones included: 13 French divisions from an effect of Germany. A limit on the owner picks one's own: `limit = { OWNER = { has_country_flag = ... } }`, with the flag set on the country for the length of the effect, gave 6 of 6 own and none of the 13 (X46). So an ally's division gets no line.
- **One entry a day.** A division took one entry on a day and dropped the second and third (X45). A capture and a citation on the same day give one line, the first. When a division takes its next entry is not known yet; the automatic honour is written at once in the hook, so it comes before anything the player does that day.

**2. By the player, for the divisions in a state.** A button "Cite the divisions here" on the state card of E1, the strip in the vanilla state view. The probe showed such a card with a working button, in the state's scope (X47). Every division of the player in the selected state gets "Cited by the high command", with the date and the state's name from the game.

- **With a medal offer or without:** `allow = yes` makes each such entry one the player can award a vanilla medal for, at the game's price. Planned as `yes` for the player's citation and `no` for the automatic line, so the mod creates no flood of medal offers on its own (decision 6).
- **A limit against misuse:** none planned. A citation gives nothing but a line. With `allow = yes` it gives a chance to spend command power on a medal, which the game charges for.

## Data and script

A section `honours()` of `tools/build_managers.py`.

| Name | What |
|---|---|
| `mod1440_hn_auto` | 1 while the automatic honour is switched on |
| `mod1440_hn_capture` (effect) | called from the territory hook: the `is_capital` test, the `has_dlc` test, the loop over the divisions |
| `mod1440_hn_cite_click` | the button of the state card |
| `mod1440_hn_count` | how many entries the mod has written, shown beside the switch |
| texts `mod1440_hn_capture`, `mod1440_hn_cited` | the two entries, in the mod's localisation |

Commands new to the test, in its list of **writing** commands with this page named: `add_history_entry`. Also new: `every_state_division`, `has_dlc`, `is_capital`, and `set_country_flag`, `clr_country_flag`, `has_country_flag` for the owner limit (a flag of the mod on the player's country, set and cleared within one effect).

The War Diary gets a line for a citation ("Divisions cited in ...", the state).

## What the probe settled

| Question | Answer | For this page |
|---|---|---|
| The entry shows in the History tab with the mod's text | yes, with the date; a text key and plain text both work (X45) | as planned |
| `$PROVINCE$` | the state's name (X45) | the place in the entry |
| `[...]` in the entry's text | not worked out (X45) | plain words; no country name in the line |
| `allow = yes` | the medal button stands on the line (X45) | the citation offers a medal, the automatic line does not (decision 6) |
| Whom a state loop reaches | everyone's divisions; a limit on `OWNER` picks one's own (X46) | honours by state, for the player's divisions only |
| How many entries a division takes | one a day (X45) | the first of a day wins |
| The state card | yes, with a working button in the state's scope (X47) | the Cite button in the state view |
| A division's name | none (X45) | a line cannot name the division, and the War Diary's line names the state, not the units |

## Checks

1. **Paused, by effects:** a state where German divisions stand on the first day is given to another country and taken back with `set_state_controller`, with the capital test left out for the check: each division's History tab shows the line. Cite a state: the same, and the medal button of the vanilla window is there for that entry.
2. **Without the DLC:** cannot be checked on this machine; the `has_dlc` test is the same one vanilla wraps its own entries in.
3. **Needs time:** a capital taken by fighting, with several divisions in the state.

## Decisions

- 2026-10-12: the user allowed writing into the game's records ("I want that mod rule loosened").
- 2026-10-12, the user on "by itself or only on your click": "By itself." The automatic honour is on by default; the switch "Battle honours" on the War Diary page turns it off.
- The citation button was built as planned, since the state card was there for it. Its line offers a medal (`allow = yes`), the automatic line does not: the user did not answer that half of the question, so the plan's default stands until they do.
- The owner limit is `OWNER = { tag = ROOT }` (X46), without a flag.

## Game checks

| # | Date | Build | Checked | Result | Screenshot | Taught |
|---|---|---|---|---|---|---|
| 1 | 2026-10-12 | `1a08bb3` +dirty | Brandenburg given to Poland and taken back by effect, with six German divisions in it | "Capital taken from Poland" in the diary and six divisions reached (the counter of honours read 6) | `scratch/checks/crop_e1_2.png` | - |
| 2 | 2026-10-12 | the same game | the state card of Brandenburg and its Cite button | "Taken from Poland on 1936.1.1"; "6 cited today"; a line "Divisions cited" under Territory. The six had their one line of the day already, so this click added none (X45) | `scratch/checks/crop_e1_10.png`, `crop_e1_11.png`, `crop_e1_14.png` | - |


## Close

- [x] Engine Facts rows; `wiki/Scripted-GUIs.md`, with the rule's wording
- [x] README and Workshop description: the sentence that the pages change nothing in the game is replaced by what they write
- [x] The test's list of writing commands holds `add_history_entry` and nothing else
- [ ] A division's History tab read with a line of the build (the probe's line was read; the build's count was)
- [ ] A capital taken by fighting
- [ ] The tester's judgement, and their answer on the medal offer

## Redesign build (2026-10-16)

Status: **built and checked by render and tests; not seen in game.**

- **Three more occasions**, each with its switch on the War Diary's Battle honours card (decided by the user: landings and airborne on, a great city off):
  - "Landed from the sea in $PROVINCE$": `on_naval_invasion` (the state invaded in scope, ROOT the country that lands), the player's divisions in that state (`mod1440_hn_landing`, switch `mod1440_hn_sea`).
  - "Dropped from the air over $PROVINCE$": `on_units_paradropped_in_state` (ROOT the state, FROM the country), the divisions of FROM there (`mod1440_hn_drop`, switch `mod1440_hn_air`).
  - "Fought for $PROVINCE$, where a great city fell": a victory point of 15 or more taken (`mod1440_vp_changed`), the divisions in the point's state (`mod1440_hn_city`, switch `mod1440_hn_vp`, off by default).
  - `allow = no` on all three, as the capital's line; the citation keeps `allow = yes`. One line a day per division (X45): the first occasion of a day wins. The writing stays in `common/scripted_effects/mod1440_records.txt` (the test of the writing commands).
- **Counts:** by themselves (`mod1440_hn_auto_n`) and cited by you (`mod1440_hn_cite_n`), two tiles on the card; `mod1440_hn_count` stays as their sum. A record of an earlier build had only the sum: it stands under "by themselves". The last citation's state and date (`mod1440_hn_last_s`, `_d`) stand under the tiles.
- **The state card, 540x142** at 470,0 of the state view (500x94 before): a head strip "The record of <state>" with "N lines in the War Diary" (`mod1440_sr_lines`, raised when a line names the state or its victory point); the flag of whom it was taken from, "Taken from ... on ..., held N days" (`mod1440_sr_held`, worked out by the daily round for the player's states that were taken, `every_controlled_state`); "by the troops of <general>" with his portrait (`mod1440_sr_by`, `_by_p`, set from the general on the spot); Cite, "N cited today - N times in all" or "Cited N times before" (`mod1440_sr_cites`); "Its lines", which opens the War Diary on the lines of this state.
- **"By the troops of" is a window of its own** (`mod1440_state_card_by`, the same context and parent), shown only for a state taken with a general on the spot: a window that is not drawn never asks for a character, and a text that names one through an empty variable logs "invalid scope for var" also while hidden (X73).

**Fallbacks:**
- `on_naval_invasion`: if the landing divisions do not yet stand in the state when the hook fires, the honour reaches nobody (the hook's `game.log` line says how many: "[?hn_n] divisions honoured"); then the honour moves to the first `on_state_control_changed` of that state within the day of the landing.
- The second window of the state card: if it is drawn under the card (both are children of the state view), its line goes into the card itself with a default general for states nobody took.
- The larger card in the user's playset (Devastation Overhaul draws at 451,194 of the same view, Landlord adds buttons): to be seen with `tools/Invoke-GameSteps.ps1 -Start -Playset`.

**Not seen in game:** any of it. Game check `tools/Invoke-GameCheck.ps1 war_diary wars`; the tester's checklist is items 8 and 10 of the [E1 notes](E1-war-diary.md), and: a landing and an airborne drop in a game with fighting, with the History tab of a division that took part.

## The card can be hidden (2026-10-27)

User request outside a phase: the card covered a button of Landlord, the state coring mod of the playset. `tools/check_playset.py guis` reads Landlord's two windows at 462,40 and 464,8 (100x130) of the state view, under the card's left part (470,0, 540x142); the Compatibility note of 2026-10-13 was taken with the 500x94 card.

- **A close button** (`sc_hide`, the game's close sprite, its right edge 4 px inside the head strip's) hides the card and its "by the troops of" window; the lines count moved left of it, the title's box narrowed to 290. No ESCAPE on it: ESCAPE closes the state view, and would hide the card for good.
- **A Record button** (`mod1440_state_card_handle`, the game's 100x29 sort button at 570,6, right of Landlord's windows) brings it back while it is hidden.
- **Kept per country:** `mod1440_sc_hidden` on the player's country, 1 = hidden; a save of an earlier build reads 0 and shows the card as before. The windows stay in `selected_state_context`, so `tests/ScriptedGuis.Tests.ps1` now excepts every `mod1440_state_card*` window.
- Built with `build_managers.py`; `--check`, `lint_gui.py` (0 errors) and the suite (274 passed) clean. **Not seen in game:** the two buttons, and whether `ROOT = { check_variable }` holds in the `visible` block of the state context (X47 names ROOT for texts and click effects). Game check: select a state you control, close the card, select another state (the Record button, Landlord's buttons free), bring it back, and once with a save and a load.
