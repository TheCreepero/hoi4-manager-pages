# Phase D0: manager screens, feasibility

Four questions about turning Recruit & Deploy into a near full screen "manager", asked of the game in one launch on 2026-10-12. Status: done. The engine facts it gave are rows S29, S30, X1 to X6 and H33 of [Engine Facts](../Engine-Facts.md). Nothing of the experiment is left in the mod; the script that set it up is `scratch/apply_d0.py`.

## Scope

- The idea (user, 2026-10-12): a side panel becomes a near full screen manager with new information and quality of life options, and narrows by itself when the map is needed.
- Screen used: Recruit & Deploy as A5 left it (`interface/zz_1440p_recruit_deploy.gui`).
- Out of scope: any layout. This phase only finds out what the engine does.

## Questions and answers

| # | Question | Answer | Evidence |
|---|---|---|---|
| Q1 | Does `max_slots_horizontal = 2` put the rows of `templates_grid` into two columns? | **No**, in neither form. With a slot of 581x48 the list shows one template of five. With the vanilla slot height of 1 it stays one column: Italy's 14 templates one below the other in a panel 1200 px wide. | `scratch/checks/d0_a_open-20261012-150833.png` (slot 48), `d0_h_italy-*` and `d0_b_train-*` (slot 1) |
| Q2 | What does the code do with the two panels while a deploy location is picked? | **Nothing.** Both panels stay as they are; the map shows the allowed provinces hatched green and the others red. A click on a green province sets the location and ends the picking. Escape during the picking closes the whole tab. | `d0_c_pick-*`, `d0_d_located-*`, `d0_f_escape-*` |
| Q3 | Do clicks reach the map between the panels? | **Yes.** The template panel was moved to the right edge of the screen (x 1360), 726 px of map between the two panels; a click there picked Hannover. The two panels are separate windows, so nothing lies between them. | `d0_d_located-*` |
| Q4 | Does a scripted GUI work on this tab? | **Yes**, all of it: see below. | `d0_a_open-*`, `d0_b_train-*`, `d0_g_probe_click-*`, `d0_h_italy-*` |

What the scripted GUI probe showed (a container with one text, one button, attached with `parent_window_token = deployment_tab`):

- It is drawn inside the left panel: its `position` of 20,1150 landed at screen 14,1228, which is 20,1150 from the panel's corner at -6,78.
- A text whose localisation holds `[?variable]` shows values of the player's country: `amount_manpower_in_deployment_queue`, `max_available_manpower_k`, `army_experience`, `num_divisions`, `num_equipment@infantry_equipment`.
- The values follow the game while it is paused: three clicks on Train took the queue from 0 to 28800 and the infantry equipment in stock from 52 to 0.
- A click on the button runs its effect while the game is paused. The effect set a variable; the text with a `_visible` trigger on that variable went away, and the button, whose `x` property is another variable, moved 150 px.
- The variable belongs to the country: after `tag ITA` the text was back, with Italy's numbers.
- The localisation file (`localisation/english/*_l_english.yml`, UTF-8 with BOM) was read, and `error.log` named none of the three files.

Seen on the way:

- Each click on Train makes a card of its own with one line, also for a template that has a card already. More lines on one card come from Add Unit.
- The location button of a card shows its second frame, the one with chevrons, with the name of the place ("Hannover") once a location is set. The widened button of A5 draws it without a seam.

## What follows for the manager idea

- **A wider Recruit & Deploy has nothing to fill its width with.** Its two lists stay one column each, and the code offers no value the screen does not show already. D1 of the roadmap is dropped.
- **The game will not narrow a panel when the map is needed**, and no file can ask it to. What works instead: the panels are separate windows, so they can stand apart with the map between them; and a scripted panel can fold itself away on a click.
- **New information is possible with a scripted GUI**, for values of the country. Nothing per division in training or per template: script cannot list either.
- A scripted GUI lives in `common/`, which changes the checksum. The user decided on 2026-10-12 that this is acceptable in this mod. The mod stays outside the checksum until the first scripted GUI ships.

## Game checks

| # | Date | Build | Checked | Result | Screenshot | Taught |
|---|---|---|---|---|---|---|
| 1 | 2026-10-12 | 5a25450+dirty, experiment build with a slot of 581x48 | the first two steps; a power outage ended the run | one capture whole: one template visible, the probe on screen | `scratch/checks/d0_a_open-20261012-150833.png` | S29, X1 |
| 2 | 2026-10-12 | the same with a slot of 581x1 | all eight steps | see the table above; `error.log` clean | `scratch/checks/d0_*-20261012-1515*`, `-1516*` | S29, S30, X1 to X5, H33 |

Not seen:

- A scripted list (`dynamic_lists`), a scripted GUI larger than the panel it is attached to, and what a scripted panel does to clicks on the vanilla widgets under it.
- Whether the tab's Escape also closes a scripted panel that reaches outside the tab's window.
