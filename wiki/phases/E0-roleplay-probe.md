# Phase E0: probe for the role-play pages

One launch with a throwaway build, as D0 and the D2 probe were. It answered what the documentation left open before any page of [the Records](../Roleplay-Pages.md) is built. Status: run on 2026-10-12 with the user's permission; fifteen of seventeen questions answered, one in part, one not. The facts are rows X32 to X49 of [Engine Facts](../Engine-Facts.md).

## Scope

- Seven probe windows with one text or list per question, opened by a top bar button (Shift+J), a card in the state view, and a file of throwaway effects run from the console (`effect <name>`). Written and removed by `scratch/apply_e0.py`; changed while the game ran by `scratch/e0_live.py` (X27). Nothing of it is committed.
- The game stayed paused on 1 January 1936 and was never saved. Its state was changed by effects: a war with Poland and a white peace, Danzig taken, Luxembourg annexed, Denmark made a subject, a general promoted, one created, one retired, advisors hired, history entries written. That game is gone.
- Two countries: Germany, and Italy through `tag ITA` (at war with Ethiopia on the first day).

## Answers

| # | Question | Answer | Row |
|---|---|---|---|
| P1 | Does a general keep a variable of the mod? | **Yes.** Also an admiral and a hired advisor. Read back in his scope, in his list row and after promotion and retirement. Through a save and a load: not tested. | X32 |
| P2 | Can a country hold a general? | **Yes,** in a variable and in an array. His name by `[?holder.GetName]`, his scope by `var:holder`, his own variables by `[?holder:variable]`. Game values (skill) need `var:` in an effect or his own list row. | X33 |
| P3 | What does a held general show once he is gone? | **Everything he showed before.** Retired, he leaves `army_leaders`; the holder keeps his name, skill and variables. No error. The same for an annexed country. | X34 |
| P4 | A date in an array | **Yes,** in four forms. Days between two events need `global.num_days` stored beside the date. | X35 |
| P5 | A text key in a variable | **Yes,** from arrays and in rows. A `[...]` inside the fetched text is not worked out, so the text is plain words. | X37 |
| P6 | Scripted localisation in a row | **Yes,** with the row's value, index and scope, and its text does work out `[...]`. Not needed where P5 or P7 serves; it costs a fifth folder under `common/`. | X38 |
| P7 | `_visible` per row | **Yes,** by the row's value and by the row's scope. | X39 |
| P8 | A country in an array | **Yes:** name, flag in the text, tag, adjective, leader; in a scoped row its surrender progress and casualties. | X40 |
| P9 | Characters that are not generals | **In part.** The texts of the own country all work. Offices give a name once filled and the country's name before. An advisor who is no general has no scope in a list row: his name comes by index, his dates from arrays of the country. No ideology for an advisor. | X41, X42 |
| P10 | Hooks, fired by effects while paused | **Eleven seen** with their scopes. `on_puppet` did not fire for the effect `puppet`. `on_unit_leader_created` does not fire for the officers a game starts with. | X43 |
| P11 | A general's troops in a state held by a variable | **Yes:** `num_units_in_state@var:<variable>`. | X44 |
| P12 | Flags with a number on a general | **Yes.** Not needed, since P1 works. | X32 |
| P13 | A division | **No name.** A history entry of the mod shows in the History tab with the date, the subject and the state's name; no `[...]`; `allow = yes` offers a medal. **One entry per division per day.** A state loop reaches foreign divisions too; a limit on `OWNER` picks one's own. | X45, X46 |
| P14 | An ace | **Not answered.** `add_ace` does not fire `on_ace_promoted`, and there is no other way to an ace's scope in a paused game. | X43 |
| P15 | The selected state | **Yes.** A card shows in the state view, and beside it without being cut off; its scope is the state. | X47 |
| P16 | The top bar button and the window | **Yes.** Shift+J opened and closed the windows; a vanilla pop-up is drawn above them. | X48 |
| P17 | A long log | **No cost to speak of:** 500 lines filled and a 200-row view copied 50 times within one second; 68 frames per second with the list open. | X48 |

Also learned: in a scoped list row an array of the country needs `ROOT.` before its name (X36), and the console runs an effect in the scope of whatever is selected (X49).

## Still open

They need days to pass, or a save:

- **An ace** (P14): whether one can be kept, and what a dead ace's texts show.
- **The battle hooks:** `on_army_leader_won_combat`, `on_army_leader_lost_combat`, the two navy hooks: that they fire, for whom (the general, also his field marshal?), how often.
- **`on_capitulation`, `on_naval_invasion`, `on_units_paradropped_in_state`,** and `on_puppet` from a peace conference.
- **The daily comparison** of `enemies`, `subjects` and offices running by itself.
- **A save and a load:** whether a variable on a general, and a general held by the country, come back. Country and state variables do (History has columns in the user's game).
- **A general who dies** in the field, as against one retired.
- **When a division takes its next history entry:** the next day, or later.

Ways to settle them: the user's play with a build whose hooks write to `game.log`; a check that runs some days inside January 1936; a check that saves under a file name of its own. The second and third are decisions for the user ([the Records](../Roleplay-Pages.md), decision 3).

## Game checks

| # | Date | Build | Checked | Result | Screenshot | Taught |
|---|---|---|---|---|---|---|
| 1 | 2026-10-12 | `1a08bb3` +dirty, with the probe files | P1 to P17 as above, in one launch of about fourteen minutes, changed live seven times | fifteen answered, P9 in part, P14 not | `scratch/checks/e0_1-*` to `e0_14-*`, `crop_e0_*` | X32 to X49 |

After the launch: the probe files removed, `git status` shows the documentation only, the launcher file put back to the user's deployed copy (version 1.5), the playset back at 56 mods, `USA.hoi4` and `autosave.hoi4` with their times of before (19:23 and 19:21).
