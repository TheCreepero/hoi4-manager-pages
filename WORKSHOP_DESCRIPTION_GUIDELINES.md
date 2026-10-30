# Steam Workshop Description Guidelines & Reference

This document provides formatting rules, length limits, and reference templates for maintaining the Steam Workshop listing for **HOI4 Manager Pages**.

---

## Core Rules & Invariants

1. **No Emojis**: Strictly avoid emojis anywhere in the description text.
2. **Character Limits**: Steam Workshop descriptions have a max limit of ~17,000 raw BBCode characters. Keep bullet points concise and direct.
3. **No Planned Section**: Do not include speculative 'Planned' sections in the public description. List a page only when its phase is marked Done in `wiki/Roadmap.md`.
4. **Valid Steam BBCode**:
   - Headers: `[h1]Title[/h1]`
   - Bold: `[b]Text[/b]`
   - Italics: `[i]Text[/i]`
   - Links: `[url=https://...]Text[/url]`
   - Bullets: Standard hyphen (`- Item`)
5. **Sentences that rest on game time**: "fill in after a day" and "month by month" rest on hooks no automated check sees run, because no check lets game time pass (`wiki/Scripted-GUIs.md`, "Known gaps"). The user played past the first of a month and reported them working on 2026-10-12. A new page that records over time is played the same way before its sentence goes into the template.
6. **What the mod writes** is said in the Info lines: unit honours are the one thing (`wiki/phases/E6-unit-honours.md`).
7. **Before the first upload**: "battles won and lost" under Officers was seen counting in the user's campaign (2026-10-30, E2: Witzleben 2, Halder 3). "Capitulations" rests on a daily comparison never seen finding one: play a war to a capitulation first, and if the War Diary shows no line for it, take the word out or fix the comparison (`wiki/Scripted-GUIs.md`, "Known gaps").
8. **The split**: these pages shipped inside the HOI4 1440p UI Mod until 2026-10-21 (versions 1.5 to 1.9 of that mod). The description says that the mod stands alone and names the 1440p mod as the companion for the reworked screens; once both are on the Workshop, link them both ways.

---

## Template Description

```bbcode
Manager pages beside the vanilla panels of Hearts of Iron IV fill the free width of a 2560x1440 screen with tables and figures of your country, and a Records window keeps a war diary, your officers, your government and your wars for those who play the game as a story.

This mod stands on its own. The reworked vanilla screens for 1440p are in the companion mod HOI4 1440p UI Mod, which keeps Ironman and achievements; this one cannot (below).

Check out my other mods:
- [url=https://steamcommunity.com/sharedfiles/filedetails/?id=2967389401]Immersive Namelists Expanded[/url]
- [url=https://steamcommunity.com/sharedfiles/filedetails/?id=3807415216]Immersive Ship Names Expanded[/url]

[h1]Requirements:[/h1]
- A resolution of 2560x1440 or higher with the in-game UI scale at 100%. At a lower resolution or a higher UI scale the pages do not fit on screen.

[h1]Info:[/h1]
- [b]Not compatible with Ironman and achievements:[/b] the pages need script files, which change the game checksum. They show values and keep records of their own. The one thing written into your game is a line in a division's history (unit honours, below), which you can switch off.
- [b]Multiplayer:[/b] every player needs the mod.
- [b]Save Game Compatible:[/b] Can be added to or removed from ongoing games. Added to a running game, the manager pages fill in after a day, the History graph starts on the first of the next month, and the Records begin on that day.
- Built for Hearts of Iron IV version 1.19.*.

[h1]Manager pages:[/h1]
Shift+M shows and hides the page of the open tab; a page that is open closes with its X, Shift+M or Escape.
- [b]Army Readiness[/b] (beside Recruit & Deploy, opened with the Readiness button): manpower free, in training, in the field and needed by garrisons, and divisions below 75% strength and below 50% organisation, as tiles. For sixteen kinds of land equipment the stock, what your divisions hold, what they need and what they are short of, with a bar, shortages in red. One row per general with troops: divisions, battalions, divisions fighting, planning and the worst equipped kind of equipment.
- [b]States[/b] (beside Construction): every state you control as a table: free building slots, building levels, resources, population, compliance and resistance. Click a column head to sort. Click a state and the camera goes there. The totals of the listed states stand under the list.
- [b]National Figures[/b] (Shift+M on Politics): the figures of your country in tables, each with its change in a month and in a year and twelve months as a sparkline; the summed modifiers of your country, 101 of them: what all your laws, spirits, advisors and technologies together add to factory output, construction speed, research speed, organisation, compliance and the rest; what does not apply is grey. A table of resources and one of equipment: in stock, what your divisions are short of, and the balance, red below zero.
- [b]History[/b] (in National Figures): forty figures of your country month by month: manpower, divisions, factories, stability, war support, fuel, equipment balances, surrender progress, your casualties in every war, ended or not, and the dead of each month with the deadliest in gold. A click on a row draws its graph, over 2, 5 or 10 years, with a zoom; what goes below zero hangs red from the zero line.
- [b]Top bar strip[/b] (every screen): the numbers the top bar keeps in its tooltips, as chips in its empty middle: political power and command power per day, stability and war support per week, free civilian factories, idle military factories and dockyards, fuel in store. An edit button opens a panel where you choose among eighteen values; the choice is kept with your country.
- The pages show your own country only. Equipment, buildings and resources added by other mods do not appear in them.

[h1]The Records:[/h1]
The Records button of the top bar or Shift+J opens a window that writes your campaign down as you play.
- [b]War Diary:[/b] a dated log of wars, peace, capitulations, annexations, subjects, your faction, every state and victory point taken or lost with the general on the spot, changes of government and your officers' careers. Filters by kind; a button on a line about a place moves the camera there.
- [b]Officers:[/b] every general and admiral with his portrait in a table you can sort, and a file for each: commissioned, promoted, battles won and lost, states and victory points taken under him, his command (divisions by kind, planning, entrenchment, equipment) and his traits with their effects. An Order of battle view lists your field marshals with the generals under them, worked out once a day from where their troops stand. A retired officer keeps his record. Award him your country's medals from the game, by name and icon: for an officer a record only, with no bonus and no cost.
- Officers that other mods add are listed as well. Their portraits show for the mods this build knows; from other mods they show the unknown leader.
- [b]Government:[/b] head of government, parties and their leaders, laws, cabinet, high command, faction and subjects, each name with the day it took office.
- [b]Wars:[/b] one row per enemy and per finished war, and a file for the war you click: the flags and heads of government of both sides, days, your casualties, states and victory points taken and lost, how it ended.
- [b]Unit honours[/b] (By Blood Alone): your divisions that stand in an enemy capital when it falls get a line in their own history. A button beside the state view cites the divisions in a state the same way. The Battle honours switch on the War Diary turns the automatic line off.
- The record starts on the day the mod is first active in a game. Nothing can be typed into a page, and the game gives no page the name of a division or a ship.

[h1]Compatibility:[/h1]
- Built against the vanilla game; works with and without the HOI4 1440p UI Mod.
- Checked in October 2026 in a playset with Road to 56, Vanilla Navy Rework, RBM's GFX Overhaul and the Better Mechanics mods: the pages work there. The victory points of Road to 56's map are followed.
- Known with those mods: laws, equipment, buildings and medals they add are not in the pages (a law of theirs reads "another law"), and officers whose portrait Road to 56 gives as a picture file show the unknown leader.
- A mod that replaces the Politics or Recruit & Deploy window keeps the page's button only if it leaves the title strip as vanilla has it.

[h1]Feedback & Contributions:[/h1]
Please report issues, suggestions, or feedback in the Steam Workshop discussion threads.
```
