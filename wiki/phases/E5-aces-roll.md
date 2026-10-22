# Phase E5: Aces

The aces of the air force: who, in which wing, since when, and what became of them. A page of [the Records](../Roleplay-Pages.md), and the least certain one: whether it is a roll of names or two counters rests on one question, and the probe ([E0](E0-roleplay-probe.md)) could not answer it. Status: Plan B built on 2026-10-12 (three counters on the Wars page, lines without a name in the War Diary); Plan A waits until play shows that an ace can be kept.

## Scope

- **Vanilla has:** a pop-up when an ace appears or dies, and the ace on his wing. No list of aces.
- **The page, if an ace can be kept:** one row per ace of the campaign, the fallen included.
- **Out of scope:** an ace's kills or missions (no value of an ace is documented but whether the ace is a woman); assigning an ace.

## What is known

- The game calls script for an ace seven times: promoted, killed, killed in an accident, killed by an enemy ace, killed an enemy ace, two aces killed each other, and an enemy ace shot down by a pilot without a name. The country is the scope and the ace is FROM (R5).
- An ace has texts: full name, surname, call sign, kind, wing, short wing name, the region of his mission (R2).
- Vanilla keeps one number from these hooks (`SIA_ace_count` for Siam) and no ace.
- Nothing documented says an ace can be put into an array, and no trigger can ask an ace anything.
- **The probe:** `add_ace` made an ace and did not fire `on_ace_promoted` (X43). An ace's scope is reached only as FROM of the seven hooks, and those fire from air combat, which needs time. So the question is open.
- **How it gets answered:** the hooks of E1 already count aces. For one release they also try to keep the ace (`add_to_array` with FROM) and write the result to `game.log`, with the name read back the same day and again when the ace has died. The user's first air war answers it; a check that runs time would too.

## Plan A: a roll (if P14 says an ace can be kept)

| Column | Width | Source |
|---|---|---|
| Name | 360 | `GetFullName` |
| Call sign | 220 | `GetCallsign` |
| Kind | 200 | `GetAceType` |
| Wing | 300 | `GetWing`, as it is today |
| Promoted | 150 | the date, from `on_ace_promoted` |
| Fate | 300 | "Killed in action 1941.3.2", "Killed in an accident", "Shot down by an enemy ace"; empty while he flies |

- **Data:** arrays of the country `mod1440_ac_ace`, `_since`, `_fate`, `_fate_date`, 300 rows. A death finds the ace's row by comparing FROM with the array.
- **Cards above the table:** aces promoted, aces lost, enemy aces shot down.
- **Risk:** what a dead ace's texts show. If they are empty, the fallen keep a row without a name, which defeats the page; then Plan B.

## Plan B: counters (if not)

- No page. The Wars page ([E4](E4-war-ledger.md)) gets a card "In the air": aces promoted, aces lost, enemy aces shot down, each a counter raised by a hook.
- The War Diary writes "An ace was promoted" and "An ace was lost" without a name. The name is in the game's own pop-up of that moment.

## Checks

1. **Paused:** nothing. `add_ace` does not fire the hook.
2. **Needs time:** all of it. The user's play in a war with an air force, with the hooks logging to `game.log`.

## Decisions

- 2026-10-12: planned as the last page.
- 2026-10-12, after the probe: Plan B is built with E1 and E4. Plan A waits for the log of a real air war.
- Built: each ace hook raises its counter and writes its line; `on_ace_promoted` also tries to keep the ace in an array and writes to `game.log` what it reads back ("MOD1440 listening"). None of it has been seen firing.

## Close

- [ ] Plan A or B recorded here with the probe's answer
- [ ] Engine Facts rows; `wiki/Scripted-GUIs.md`
- [ ] README and Workshop description, if Plan A
- [ ] Scene file and recipe (`tools/scenes/aces.json`), if Plan A

## Redesign build (2026-10-16)

Status: **built and checked by render and tests; not seen in game.** Plan B stays. The three counters (aces promoted, aces lost, enemy aces down) stand among the twelve tiles of "The country at war" on the Wars page, beside the two counters of the prides of a fleet (`mod1440_ct` of the kinds `pride_sunk` and `pride_lost`); the diary's air and sea lines keep their family and filter. The tab bar of the Records window has a fifth place free for Plan A, a roll of aces, once an air war shows that an ace can be kept: the "MOD1440 listening" lines of the hooks are not in today's `game.log`, which the game writes anew at each start, so that says nothing yet. Game check and checklist: the [E4 notes](E4-war-ledger.md).
