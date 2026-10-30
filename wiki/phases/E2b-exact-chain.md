# Phase E2b: Officers, exact chain of command

## Scope

- The Officers page of the Records window (`mod1440_records_of`, scene `officers`) and the Army names switch of Army Readiness (scene `army_readiness`).
- What changes: with the Modding Manager's field marshal patch of `hoi4.exe` (SCR-086), each general is linked to his field marshal by an equal `has_orders_group`, exactly, instead of the guess of E2; the switch is renamed "Patched game". The guess stays for an unpatched game.
- Out of scope: division details (parked by the user on 2026-10-30); the names `GetHerHimCap` and `GetHersHisCap` the patch adds (the linked character gives them).

## Roles and handoffs

- Handoff folder: `scratch/phases/E2b/` (not in the repository)
- Short path (orchestrator's own `layout.json` and `design.json`, one figure group): the screen changes by one label.
- Builder: `builder-script`, main tree
- Design page: https://claude.ai/artifact/RiAwowr6CowK3JZ61bGAbU (2026-10-30, short path)
- Layout file: `scratch/phases/E2b/layout.json`, the E2 layout with the label changed
- Contracts written: `scratch/phases/E2b/contracts.md`

## Proposal

<!-- generated: proposal (tools/phase_notes.py; edit the handoff file, not this) -->
With the Manager's field marshal patch applied, has_orders_group gives every general the id of his army group and every field marshal the id of his own, so the daily chain of command links a general to the marshal whose id is equal: exact, with no capacity rule and no 'likely' mark. The switch 'Army names' is renamed 'Patched game' on both pages; the page tells a patched game from an unpatched one by the values themselves and falls back to today's guess when they are not the patch's. Nothing else on the screen moves. Verdict: refine; effort: S: one branch in mod1440_of_chain, a daily flag, a renamed label on two pages, tooltip texts; no new widget.

What vanilla does badly: The chain is guessed once a day from where each general's divisions stand, kept in check by each marshal's division count (E2 fix round 2). It can still link wrongly (a member army at sea, an outsider with a larger share in one state), marks a general matched to two marshals as 'likely', and is a day behind.

**The switch.** The gold checkbox behind the rule in the filters card reads 'Patched game' (was 'Army names'); the same variable mod1440_ar_names (a save contract), the same place (904,127), the text box widened from 78 to the card's inner edge. Army Readiness's button reads the same. The tooltip says what the patch gives (army and army group names; the exact chain of command) and that it comes from the Modding Manager's Set-HoiArmyNameProperty.ps1, undone by every game update.

**The chain, patched.** mod1440_of_chain, when mod1440_ar_names is 1 and the patch is detected that day: every general with an army takes the field marshal leading an army group whose has_orders_group equals his (non-zero); one marshal at most can match, so mod1440_of_fm_n is 1 and nothing is 'likely'. A general whose value is 0 stands under the High Command. Cost: generals x marshals comparisons a day, less than the guess. Battle credit (mod1440_of_g_won/_lost) follows the exact link without change.

**Telling a patched game.** The same daily round sets mod1440_of_exact to 1 when at least one army leader's has_orders_group is neither 0 nor 1, else 0. With the switch on and mod1440_of_exact 0 the chain is today's guess (state method with the capacity rule), and the tooltips of Reports to and of the Order of battle filter say 'guessed from where his troops stand: the game is not patched' instead of 'from the game'. With the switch off the guess runs as today.

**What the player sees.** No new widget. Reports to, the chain card and Order of battle look as in E2; their tooltips say whether the link is from the game or guessed. The 'likely' variant of Reports to only appears with the guess.

| Part | Current | Proposed |
|---|---|---|
| Switch label | Army names | Patched game (both pages) |
| Chain, switch on, patched | guess + capacity, a day late | equal has_orders_group, exact, daily and on the Order of battle click |
| Chain, switch on, not patched | guess + capacity | guess + capacity, tooltip says so |
| Chain, switch off | guess + capacity | unchanged |
| 'likely' mark | two marshals matched | only with the guess |

Additions, each with the row of "What a redesign can add" or the register id that allows it:

- mod1440_of_exact, a daily flag: the patch's values seen (SCR-086)

Open until the game shows it:

- has_orders_group on the patched 1.19.4.1: equal for a marshal and his generals, different between army groups, 0 for Cranz's army; the size of the ids (SCR-086's launch checks)
- check_variable comparing a general's has_orders_group with a marshal's held in a temp variable, in a character scope
- The unpatched value is 1 for a leader with an army (the detection rests on it)
- 'Patched game' fits its box in the game's font

Figure groups of the design page: main.
<!-- end generated: proposal -->

## Decisions

- 2026-10-30: phase opened after the Manager built the field marshal patch (`Set-HoiArmyNameProperty.ps1`, reviewed "ready", not applied; SCR-086). The user's decisions of the same day (E2 notes): the Manager builds the patch, one switch named "Patched game", E2 closed on the guess, division details parked. Short path.
- 2026-10-30, gate A (short path, own design): `lint_layout` 0 errors (the shared window ground, as in E2), contrast 0 of 271; one figure group (the switch label). Design page published; two decisions sent to the user.
- 2026-10-30, user gate 1: "Go with your recommendations. You can also apply the patch." 1A: switch on but the game not patched, the guess with tooltips that say so; 2A: the patch's values drive the chain whether the switch is on or off, the switch governs the names only. Written to `decisions-final.json`.
- 2026-10-30: on the user's word the orchestrator applied the Manager's patch with the game closed: `Set-HoiArmyNameProperty.ps1` changed `hoi4.exe` 1.19.4.1 from `b588b69d…` (the army-name patch) to `153df2fd…` (army-name and field marshal patches), matching `known-executables.json`; `-Status`: GetHerHimCap, GetHersHisCap and has_orders_group on [SCR-086]. Builder briefed.
- 2026-10-30, gate B: `mod1440_of_chain`, `_exact` and the texts read; the label moved 4 px left to fit (a deviation, `layout.json` updated); `build_managers --check` clean, `build.ps1 -Check officers` and `-Check army_readiness` 296 passed, 0 failed each; `build-main.png` against the mock-up. Passed; left to the user's campaign on the patched game.
- 2026-10-30, capture review of the user's test (Game checks row 1): "Everything seems to work." The orchestrator read `error.log`: `can_select_trait = yes` is refused at load (SCR-087), so E2's trait mark never filtered; to the builder as fix round 1 (`num_assigned_traits < num_max_traits`, a test against the refused form). Checked: `build.ps1 -Check officers` 297 passed, 0 failed.

## Game checks

| # | Date | Build | Checked | Result | Screenshot | Taught |
|---|---|---|---|---|---|---|
| 1 | 2026-10-30 | E2b build, uncommitted, in the user's own campaign (Germany, 1939, their playset, `hoi4.exe` 1.19.4.1 patched to `153df2fd…`) | Order of battle, Reports to, the tooltips, the switch on both pages; then the orchestrator read the user's `error.log` | the chain of command right in every army group, the tooltips "from the game", the label fits; `error.log`: three lines "Not a valid value: yes" at `can_select_trait = yes` (E2's trait mark, fixed in fix round 1), 177 lines of E7's portrait tables at one moment (noted in the E7 notes, not fixed here); nothing about `has_orders_group` or the chain | - | SCR-086 confirmed, SCR-087 |

## Build (generated)

<!-- generated: build (tools/phase_notes.py; edit the handoff file, not this) -->
Status: built and checked by render and tests; not seen in game (by builder-script).

**What was built.** The chain of command is exact on a game with the Modding Manager's field marshal patch (SCR-086). Each day mod1440_of_chain sets mod1440_of_exact to 1 when some army leader's has_orders_group is neither 0 nor 1, and then links every general with an army to the field marshal leading an army group whose value equals his (mod1440_of_chain_exact: mod1440_of_fm_n 1, no capacity rule, no 'likely'; 0 is the High Command), whatever the switch says (decision 2A). Otherwise E2's guess runs unchanged (mod1440_of_chain_guess). The switch reads 'Patched game' on Officers and Army Readiness (the same mod1440_ar_names) with a new shared tooltip, and the tooltips of Reports to and the Order of battle filter say how the links were made through a text key the chain sets (mod1440_of_chain_how: from the game / guessed from where his troops stand / ... : the game is not patched, decision 1A).

**Deviations.**

- The rule, the checkbox and the words stand 4 px further left than E2 and the design put them (rule 891, box 900, words 927 with 85 px to the card's inner edge at 1012); E2b's layout.json is changed to match.: 'Patched game' is 83 px in hoi_16mbs, and from 931 to the inner edge there are 81: the text was cut ('Patched ga...'). The gap to the Order of battle button stays 5 px.
- The words of the two tooltips are one text key the chain sets each day and the switch's click renews (mod1440_of_chain_how, three keys mod1440_chain_exact, _guess, _unpatched), not twin widgets.: A tooltip resolves [?variable.GetTokenLocalizedKey] (SGUI-019; the trait tooltips of E2 show it in the game), so no widget is doubled; the Order of battle filter and Reports to keep their names.
- The exact branch does not depend on the switch, and the design's 'when mod1440_ar_names is 1' is left out.: Decision 2A (the user took the recommendation): the values prove the patch by themselves; the switch governs the names only.

**Fallbacks.**

- If mod1440_chk_e2b_log shows the patched values but the links stay empty or wrong (check_variable with var/value on two temporary copies of has_orders_group not accepted, or not equal): Compare in the marshal's scope with check_variable = { has_orders_group = ch_o } (the short form), or with the values multiplied by 100000 and rounded into temporary variables first.
- If An unpatched game reads has_orders_group other than 0 or 1 for a leader with an army (the detection rests on 1): Detect by a value below 1 that is not 0 (ids x 0.00001), or by two army leaders with different non-zero values.
- If The tooltip shows the text key's name or nothing in place of 'from the game': Twin hit buttons of Reports to and twin filter buttons with fixed tooltips, shown by mod1440_of_exact and mod1440_ar_names.

**Not seen in game.**

- has_orders_group on the patched 1.19.4.1 (SHA 153df2fd...): the same value for a field marshal and his generals, different values between army groups, 0 for Cranz's army; the size of the ids.
- has_orders_group on an unpatched game reading 1 for a leader with an army.
- check_variable = { var = ch_mo value = ch_o compare = equals } on two temporary copies of has_orders_group, in a character scope.
- 'Patched game' in the game's font in its 85 px box; the switch's tooltip on both pages; the how-words in the tooltips of Reports to and of the Order of battle filter.

Shared files touched: `tools/build_managers.py (Army Readiness's switch, marked E2b)`, `tools/check_effects.py (block E2b)`, `tools/build_records.py (officers() and the chain)`, `scratch/phases/E2b/layout.json (the switch 4 px left)`.

**Game check.** `tools/Invoke-GameCheck.ps1 officers`

Checklist for the game checker:

1. 1. Patched game (1.19.4.1, SHA 153df2fd...), Germany of the user's campaign: effect mod1440_chk_e2b_log, then game.log 'MOD1440 e2b': 'exact 1'; every army leader's has_orders_group x100000 is the same integer for a field marshal and each general of his army group (compare with the game's army-group panel), different between two army groups, and 0 for Friedrich-Carl Cranz (I. SS-Standarten, no army group) and for leaders without an army. Write down the size of the ids (the raw value with five decimals and x100000).
2. 2. The links: each general's 'fm' in that log is the marshal of his army group, fm_n 1, and each marshal's subs is the number of his armies; Order of battle lists each army group with exactly its armies, Cranz among the armies under the High Command; no Reports to tooltip says 'Likely'. Move an army to another army group, one day (or click Order of battle): it follows.
3. 3. The comparison: the links in point 2 show that check_variable with var/value on two temporary copies of has_orders_group is accepted in a character scope; error.log has no line about check_variable, has_orders_group or mod1440_of_chain_exact.
4. 4. Unpatched game (the Manager's -Restore, or a game update before the patch is applied again): mod1440_chk_e2b_log shows has_orders_group x100000 = 100000 (raw 1) for a leader with an army and 0 without, and 'exact 0'; the chain is the guess of E2 (Cranz under the High Command by the capacity rule).
5. 5. The label: 'Patched game' fits its box behind the rule in the filters' card, not cut and not over the card's edge; Army Readiness's button reads 'Patched game' inside its 100 px plate. Both checkboxes show the same state; ticking one ticks the other.
6. 6. The tooltips: the switch's on both pages says what the patch gives (army and army group names, the exact chain of command), that it comes from the Modding Manager's Set-HoiArmyNameProperty.ps1 and that every game update undoes it. Reports to of a general and the Order of battle filter say 'from the game' on the patched game; on an unpatched game 'guessed from where his troops stand', and with Patched game ticked on an unpatched game '... : the game is not patched'. Untick and tick the switch: the words follow at once.
7. 7. Battle credit: mod1440_chk_e2_battle on the patched game credits the marshal of the exact link (gwon/glost 1 each).

**Tests.** build.ps1 -Check officers: 296 passed, 0 failed, 76 skipped; build.ps1 -Check army_readiness: 296 passed, 0 failed, 76 skipped; python -I tools/build_managers.py --check clean; python -I tools/lint_gui.py 0 errors (63 excepted, unchanged)

Candidate engine facts (for the orchestrator at the close):

- hoi_16mbs renders 'Patched game' 83 px wide and 'Army names' 74 px (tools/guiparse.py BitmapFont.width on the game's font, 2026-10-30).
<!-- end generated: build -->

## Fix rounds

<!-- generated: fix rounds (tools/phase_notes.py; edit the handoff file, not this) -->
### Fix round 1 (2026-10-30)

- error.log of the user's campaign at load: 'Not a valid value: yes' in common/scripted_effects/mod1440_records.txt (line 12422) and common/scripted_guis/mod1440_records.txt (lines 3697, 3767), all three 'can_select_trait = yes'; the green mark of a free trait showed on every row. Cause: can_select_trait takes a trait, not yes/no (no vanilla file uses it, the documentation gives no argument); E2 wrote it as a yes/no trigger, so the mark of the row, of the chain card and the file's 'a trait can be chosen' (mod1440_of_c_can) never tested anything. Fix: tools/build_records.py: FREE_SLOT = check_variable = { num_assigned_traits < num_max_traits } in the officer's scope (the pair of the Traits head's 'N of M chosen'; no loop) for the row's mark, the chain card's mark and mod1440_of_c_can; the tooltips say 'A free slot in his trait tree: a trait can be chosen there.'; tools/check_effects.py logs the same test. can_select_trait left the command list of tests/ScriptedGuis.Tests.ps1; new test 'Triggers of the mod: ask can_select_trait only with a trait' fails on can_select_trait = yes/no or an empty block anywhere under common/ (checked with a probe file: fails with it, passes without). Re-test: error.log at load: no 'Not a valid value: yes' in the mod's files. The green mark only on rows whose Traits head reads fewer chosen than slots (e.g. '0 of 1 chosen'), not on '2 of 2 chosen'; the same in the chain card and the file's 'a trait can be chosen'. Compare two officers with their trait trees. (builder-script)
<!-- end generated: fix rounds -->

## Close

- Closed on the user's word, 2026-10-30 ("you can close this, document whatever isn't yet documented, and commit and push"). The trait mark's fix was not seen in the game; the retest is in `fixes.json` (the star only where "N of M chosen" has N below M).
- Register: SCR-086 confirmed in the game (the exact chain, the comparison form, 0 for an army in no army group); SCR-087 added (`can_select_trait = yes` refused). `Export-HoiKnowledge.ps1` run, audit 0 blocking.
- No harness launch in E2 or E2b, so the reference capture of the Officers page in `reference/mod/` is still the 2026-10-13 build.
- Found and left open: E7's portrait tables logged 177 lines at one moment in the user's game (E7 notes, "Open").
- Roadmap E2 and E2b rows updated.
