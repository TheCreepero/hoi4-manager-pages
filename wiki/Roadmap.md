# Roadmap

HOI4 Manager Pages is built one page at a time. Each phase adds or reworks one scripted page and can be tested and released on its own. The rules every page follows are in [Scripted GUIs](Scripted-GUIs.md) and the design ruleset in [Design Language](Design-Language.md); who does each step, and where the user decides, is in [Workflow](Workflow.md).

## Standalone

- **The split (user decision, 2026-10-21):** the scripted GUIs of the HOI4 1440p UI Mod (the manager pages of Milestone D, the Records window of Milestone E, the state card and the unit honours) are this mod, HOI4 Manager Pages. The reworked vanilla screens stay in the 1440p mod. This repository was populated from the 1440p repository on 2026-10-21; the pages' history before that day is in that repository's phase notes, copied here under `phases/`.
- **Names stay.** Every `mod1440_*` file, window, variable and effect and every `GFX_1440p_SG_*` and `GFX_1440p_medal_*` sprite keeps its name: the variables live in players' saves, and a game with the old mod goes on with this one.
- **No dependency on the 1440p mod.** The mod loads alone. Phase D8 makes National Figures and Army Readiness free windows (X7), so that no page needs the `clipping = no` line the 1440p mod's politics and recruit-deploy overrides gave (X6). Until D8 closes, those two pages are cut at their tab's window without the 1440p mod loaded; `tools/Invoke-GameCheck.ps1 <scene> -WithScreens` checks a page with both mods.
- **Checksum:** script lives under `common/` and changes the game's checksum: no Ironman and no achievements, and in multiplayer every player needs the mod (user decision, 2026-10-12). Only four folders under `common/` are used, every file named `mod1440_*`, and the tests hold that line.

## Decisions

- **Baseline:** vanilla 1.19. Every page is built and checked in a playset that contains just this mod, and then looked at in the user's own playset at a compatibility checkpoint (see "Compatibility checkpoints"). The first was on 2026-10-13, inside the 1440p mod.
- **Design target:** 2560x1440 at 100% UI scale. The mod does not fit smaller resolutions or a higher UI scale.
- **What a page of the mod may write:** its own records, and lines the game keeps for show (a division's history). Nothing the game charges for. Until 2026-10-12 a page changed nothing in the game; the user loosened this for the role-play pages of Milestone E ([Roleplay Pages](Roleplay-Pages.md)).
- **Art:** no AI-generated images. Backgrounds are built from vanilla game assets.
- **Hotkeys:** Shift+M hides and shows the page of the open tab, Shift+J the Records window; both are reserved for this mod and no reworked screen of the 1440p mod uses them (`tools/hotkeys.json`, [Design Language](Design-Language.md)).
- **Orchestrated phases** (user, 2026-10-16): a phase is run by an orchestrator (the interactive Claude Fable 5.1 session) with a designer (Claude Opus 5.5), the builder `builder-script` (Claude Opus 5.5; the only builder here, every component being a scripted page) and a game checker (Claude Opus 5.5). The orchestrator reviews every handoff and reads the captures itself; the user decides at three gates: the design page, the launches, the final report and their own test. Fix rounds go back to the same builder. The page is [Workflow](Workflow.md); the agent definitions are under `.claude/agents/`.

## Status

Status values: Not started, In progress, Done. Each phase keeps its inventory, decisions and game-check log in `wiki/phases/` ([D0](phases/D0-manager-feasibility.md), [D2](phases/D2-army-readiness.md), [D3](phases/D3-states.md), [D4 and D5](phases/D4-national-figures.md), [D7](phases/D7-top-bar.md), [D8](phases/D8-free-pages.md), and the plans of Milestone E: [E0](phases/E0-roleplay-probe.md) to [E6](phases/E6-unit-honours.md); template: [Phase Template](Phase-Template.md)); what the launches taught about the engine is in [Engine Facts](Engine-Facts.md).

| Milestone | Scope | Status |
|---|---|---|
| D | Manager pages: Army Readiness, States, National Figures and History, the top bar strip | Done but D8 (free windows), open |
| E | Role-play pages: the Records window (War Diary, Officers, Government, Wars), the state card, unit honours | Done but E5 (aces), waiting for an air war |

## Milestone D: manager pages

The idea (user, 2026-10-12): a side panel such as Recruit & Deploy becomes a near full screen "manager" with new information and quality of life options, and narrows by itself when the map is needed, for example to pick a deploy location. The feasibility phase D0 was run on 2026-10-12 ([notes](phases/D0-manager-feasibility.md)). The table gives what it found.

| Part of the idea | Possible | How, and the limit |
|---|---|---|
| A panel that fills most of the screen | Yes, but with nothing to fill it | Sizes in the `.gui` file. The lists of Recruit & Deploy do not run in columns: `max_slots_horizontal = 2` on the template list failed in two forms (S29). |
| Narrowing by itself when the map is needed | No | A window has one size in its file, and no file can ask what the player is doing. The code leaves both panels as they are while a deploy location is picked (S30). |
| The map stays usable beside the panels | Yes | The two panels are separate windows and can stand apart: with the template panel at the right edge of the screen, a click on the map between them picked a deploy location (S30). |
| New information on the screen | Yes, with a scripted GUI | Attached to this tab (`parent_window_token = deployment_tab`) it showed values of the country that follow the game while it is paused: queued and available manpower, army experience, number of divisions, equipment in stock (X1, X2). It lives in `common/` and changes the checksum, which the user accepts. |
| Information per division in training or per template | No | Script sees the country, not a line of this list or a template: no array of either exists for a scripted list. |
| New working buttons | Yes, with a scripted GUI, but few are useful here | A scripted button runs its effect, also while the game is paused (X3). No effect queues a division, sets a priority or a deploy location; effects on templates lock them, cap them or change their units. |
| Folding the extra part away on a click | Yes, for the scripted panel | A scripted button set a variable; a text with a `_visible` trigger went away and a widget with an `x` property moved (X4). A vanilla window cannot be resized this way. |

So a manager is not a wider version of the vanilla panels: they have nothing more to show and cannot use the width. It is a scripted panel of the mod's own beside or over them, with values of the country and a fold button, and it gives the map back on a click, not by itself.

| # | Phase | Scope | Status |
|---|---|---|---|
| D0 | Feasibility | Four questions on Recruit & Deploy in one launch: columns in the template list (no), what the code does while a deploy location is picked (nothing), clicks on the map between the panels (they arrive), a scripted GUI on this tab (works). | Done |
| D1 | Recruit & Deploy as a wider arrangement of its vanilla lists | Templates in two or three columns beside the divisions in training. | Dropped: the lists stay one column (D0) |
| D2 | Army Readiness, docked to Recruit & Deploy | Opened with a probe of two launches that settled the open engine questions (rows X6 to X25 of [Engine Facts](Engine-Facts.md)). Then the foundation, paid once: the tool that writes every file of a page (`tools/build_managers.py`), the tests (`tests/ScriptedGuis.Tests.ps1`), the changed checksum rule, the renderer and the harness reading a scripted page. The page: manpower, the army's counts, a table of land equipment (stock, in the field, needed, a bar). [Notes](phases/D2-army-readiness.md) | Done |
| D3 | States, docked to Construction | One row per controlled state, sorted by any column, a click moves the camera there. The vanilla Construction window needs no override: it already lets a page stand beside it. [Notes](phases/D3-states.md) | Done |
| D4 | National Figures, opened from Politics | The country's summed modifiers (93, in six groups), factories, fuel, party popularity, resources. A window of its own: the vanilla Politics window would have to be overridden to dock a page. [Notes](phases/D4-national-figures.md) | Done |
| D5 | History, the second page of National Figures | Twelve figures written down on the first of each month and drawn as columns. The graph is checked with made-up months. The monthly recording runs: no check lets time pass, and the user reported it after playing (2026-10-12). [Notes](phases/D4-national-figures.md) | Done |
| D6 | Armies, on the Army Readiness page | One row per general with troops: divisions, battalions, fighting, planning, the worst equipped kind, divisions by kind. Built with D2. | Done |
| D7 | Top bar strip | Value chips in the free middle of the top bar, drawn like the vanilla values: by default political power and command power per day, stability and war support per week, the three factories with free and idle, fuel in store. An edit button opens a panel where the player chooses among eighteen values; the choice is kept with the country. The Records handle moved to the right end, inside the band. Designed from scratch (the eight-tile mock-up of 2026-10-15 was dropped by the user). [Notes](phases/D7-top-bar.md) | Done (built 2026-10-17, tested by the user in their own game the same day) |
| D8 | Free pages | National Figures and Army Readiness become windows of their own (X7) instead of pages docked to their tab, so that they no longer need the `clipping = no` line of the 1440p mod's politics and recruit-deploy overrides (X6). The first step of the split of the scripted GUIs into this standalone mod (user decision, 2026-10-21). [Notes](phases/D8-free-pages.md) | Open (2026-10-21) |

What each page shows, the rules they follow and how to work on them: [Scripted GUIs](Scripted-GUIs.md). What the user chose on 2026-10-12: all four managers and graphs over time, pages docked to their tab, values of the own country only, the top bar strip later.

- **Look reworked on 2026-10-12, seen in game on 2026-10-13.** After the Records had been polished the user asked for "a similar UI polishing pass on every other feature". Army Readiness, States, National Figures and History were rebuilt in the look of the Records: figures as tiles, tables under a bar of heads with banded rows, shares as bars, grey for what does not apply. New on the pages: what each kind of equipment is short of, the totals of the listed states, a card of occupation and diplomacy modifiers, and for History a table of the twelve figures with their change in a month and in a year, a zoom and year marks. A cold start on 2026-10-13 showed all four as the renderer had drawn them. A second check the same day showed what a new game of 1936 does not: History over ten years of made-up months, and the orange bars and the Short column as the Soviet Union.

- **Asked of the tester, and answered on 2026-10-12:** a few days and a month of game time with the mod, because no check lets time pass (the user's autosave is monthly, and a check that let a month pass would overwrite it). The user: "This is good, everything seems to be working, including the history ticks."
- **Not built, and why:** a table of other countries (own country only); anything per template, per training line or per production line (script has no list of them).
- A layout D0 showed to work and nobody has asked for: the template panel at the right edge of the screen, the divisions in training at the left, the map between them.

## Milestone E: role-play pages

The idea (user, 2026-10-12): "I like to treat Hoi4 as a role-playing game. That means giving accurate names to units, keeping track of characters." The manager pages show what the country has today; these pages keep a record of the campaign as it is played. The game keeps almost no history that script can read, so the mod writes it down itself, from the day it is active in a game. What script can and cannot reach, the Records window that holds the pages, the recording they share and the decisions still open: [Roleplay Pages](Roleplay-Pages.md).

The user asked for each page to be planned in detail and written down before anything is built. The plans were written, the probe ran and corrected them, the user answered the open decisions, and on 2026-10-12 the pages were built: version 1.6. What each shows and how each value was checked: [Scripted GUIs](Scripted-GUIs.md), "The Records".

| # | Phase | Scope | Status |
|---|---|---|---|
| E0 | Probe | One launch on 2026-10-12, seventeen questions the documentation left open. Answered: a general keeps a record and the country can hold him, also once he has retired; dates, text keys and words chosen per row work in a list; eleven hooks fire with the scopes the vanilla comments give; a line of the mod shows in a division's history with the state's name; a card shows in the state view. Not answered: an ace. Rows X32 to X49 of [Engine Facts](Engine-Facts.md). [Notes](phases/E0-roleplay-probe.md) | Done |
| E1 | War Diary | A dated log: wars, peace, capitulations, territory, landings, government, promotions. Builds the Records window (a button in the top bar, Shift+J), the recording and the card in the state view. [Notes](phases/E1-war-diary.md) | Built and checked in game on 2026-10-12; found working by the tester in a long game with several wars (2026-10-14) |
| E2 | Officers | Every general and admiral in one table, with a service record the mod keeps (commissioned, promoted, battles won and lost, states taken) and decorations the player awards: the game's own medals of the country, as a record with no effect. [Notes](phases/E2-officer-records.md) | Built and checked in game on 2026-10-12; found working by the tester in a long game with several wars (2026-10-14) |
| E3 | Government | Head of government, parties, cabinet, high command, laws, faction, operatives, by name and with the date each took office. Operatives are a number only. [Notes](phases/E3-cabinet.md) | Built and checked in game on 2026-10-12; found working by the tester in a long game with several wars (2026-10-14) |
| E4 | Wars | One row per enemy and per finished war: dates, days, losses, states taken and lost, outcome. [Notes](phases/E4-war-ledger.md) | Built and checked in game on 2026-10-12; found working by the tester in a long game with several wars (2026-10-14) |
| E5 | Aces | A roll of the air force's aces, if one can be kept. The probe could not ask: no effect fires the ace hooks. Three counters on the Wars page until an air war answers. [Notes](phases/E5-aces-roll.md) | Counters built; the roll waits |
| E6 | Unit honours | Lines in a division's own history: written by the mod when a capital falls, or for the divisions of a state on the player's click. The one part that writes into the game's records. [Notes](phases/E6-unit-honours.md) | Built and checked in game on 2026-10-12; found working by the tester in a long game with several wars (2026-10-14) |

- **Order:** E1, E2, E4, E3, E6, E5.
- **Seen in a check that ran nine days:** the daily comparison running by itself, states lost to enemy troops, and that the monthly autosave is not written inside a month. No battle happened in those days.
- **Not possible, and why:** typing a note or a name (no text field); a division's or a ship's name on a page (script has none); the portrait of a general the game made up (nothing reads it); a list of battles with place and enemy (the hook gives neither).
- **Added on 2026-10-13, at the user's wish for "more graphical details", and checked in game the same day:** portraits (in the Officers list, in an officer's file, of the head of government, in the file of a war) and flags; a line in the War Diary and in the officer's file for each victory point that passes between the country and an enemy, and the general on the spot on every line about a state; the All view of the diary through both logs; a file for each war with the two flags, the two heads of government, figures and lines. [Scripted GUIs](Scripted-GUIs.md), "The Records".
- **Officers other mods add (2026-10-13).** The user's test with a mod that adds generals showed them missing from the Officers list: a leader whose command comes by an effect has no number a variable can hold. They are kept by their place in the game's list of characters now, listed with the others, and shown with their own portraits for the mods of the user's playset. Checked in game with that mod. [Scripted GUIs](Scripted-GUIs.md), "The Records"; [E2 notes](phases/E2-officer-records.md).
- **Decided by the user on 2026-10-12:** the rule as worded, one Records window, capitals in the main view and every state under a filter, the game's national medals as decorations, unit honours written by the mod itself, version 1.6, and time in a check: up to ten days inside January 1936 with a copy of the autosave made first.
- **Asked of the tester:** a war. Battles won and lost per general, a capitulation, casualties, a landing and an ace have not been seen; and a save and a load, after which an officer's record should still be there.
  - Answered on 2026-10-14: the user played a longer game with several wars and found that everything seems to work as intended. They will come back with suggestions for changes and improvements. The items above were not reported one by one.

## Compatibility checkpoints

A checkpoint looks at the mod in the playset the user plays with: from the files with `tools/check_playset.py`, then in the game with that playset loaded. The method and every finding are in [Compatibility](Compatibility.md).

- **Checkpoint 1, 2026-10-13, done (inside the 1440p mod).** The playset "Reordered Pack (USA)": 55 mods, among them Road to 56 with Vanilla Navy Rework, RBM's GFX Overhaul and the Better Mechanics mods. For the pages: the victory points of Road to 56's map, a medal sprite that mod drops, a button on another mod's button, and an error line of the state card were fixed in the mod itself.
- **Checkpoint 2:** when the playset changes much, or when a page reads something a mod of the playset changes.

## Risks

- **Other mods.** What a playset can break is listed in [Compatibility](Compatibility.md): sprites a mod drops or resizes, texts it makes longer, a second scripted GUI on the same spot, a mod that replaces the window a page is docked to, and a map or characters the mod's tables do not know.
- **Game updates.** A new game version can change the characters, the victory points and the medals the mod's tables carry: `python -I tools/make_game_tables.py` and `tools/list_medals.py` make them again, and a test fails while they differ from the game.
- **Saves.** The records live in `mod1440_*` variables of the players' saves; a renamed variable loses a campaign's records. Names are never changed.
