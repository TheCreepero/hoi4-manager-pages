# Script Reference

What is known about the Hearts of Iron IV script language as far as a scripted GUI of this mod needs it, with the source of every claim and how sure it is. Researched on 2026-10-12 against game 1.19.3.0 (revision c01a3d50), before any scripted GUI was written. The probe and the builds of the same day then tried most of it in game: those results are rows X6 to X31 of [Engine Facts](Engine-Facts.md), which is the stronger source where the two differ, and the last section of this page says which rows here they settle. The pages built with it are in [Scripted GUIs](Scripted-GUIs.md).

The fact tables of this page (L, T and G) are written by a script from the knowledge register of the Modding Manager, where each fact is kept once with its evidence and shared with the author's other mods. Their ids are kept as the records' aliases (`1440p-script:L1` and so on), so `Find-HoiKnowledge.ps1 -Id 1440p-script:L1` finds a record. Change a fact in the register and run `Export-HoiKnowledge.ps1 -Repo hoi4-1440p-ui-mod`; never edit between the markers. A new fact goes into the register with `-Alias 1440p-script:<letter><next number>`. The "Source" column of the old tables is the evidence of each record.

Status values, strongest first:

- **confirmed**: seen working in this game version by this project (the probe of [D0](phases/D0-manager-feasibility.md)).
- **documented**: stated in a documentation file the game ships. The file is named; paths are relative to the game folder.
- **vanilla**: used in a vanilla 1.19.3 file, so it works in the place vanilla uses it. Not proof that it works in a scripted GUI on a tab.
- **mod**: used in The New Order (see Sources), a released mod for this game version with 133 scripted GUIs. It works there; this project has not run it. Stronger than a documentation line, weaker than a launch of our own.
- **recalled**: from the agent's training only, not found in a file of this install. A hypothesis; check it before relying on it.
- **untested**: documented or recalled, and never seen working where this mod needs it.

## How far the agent's own knowledge goes

- **Reliable:** the shape of the language (scopes, triggers and effects, variables, arrays, localisation with values in it, the anatomy of a scripted GUI). The D0 probe, about 40 lines in three files written from memory and the game's documentation, worked on its first launch.
- **Not reliable:** exact names, parameters and scopes of single commands, and anything the game added in recent versions. The research for this page turned up four parts of the language the agent did not know or knew wrongly: math expressions, collections, script constants, and the localisation objects. Every command is therefore looked up before it is written (`Find-HoiDoc` of the `hoi4-vanilla-lookup` skill, or the files below), never taken from memory.
- **No vanilla example:** vanilla has 17 scripted GUIs, and all are small display panels inside a decision category. None has a click effect, a list, an attachment to a tab or an AI block (see "What vanilla uses").
- **A large example from a mod:** The New Order uses every part of the system that vanilla leaves out, on the current game version (see "What The New Order uses"). It is read as evidence of what works and how it is put together. Its code and images are not copied: they are that team's work, and this mod builds its images from vanilla assets.
- **No test without the game:** script cannot be run outside the game, and the agent starts the game only with the user's permission. A claim is confirmed only by a launch.

## Sources

| Source | What it holds |
|---|---|
| `documentation/script_concept_documentation.md` | bindable, contextual and formatted localisation; collections; math expressions; script constants |
| `documentation/effects_documentation.md` (564 entries), `triggers_documentation.md` (610) | every effect and trigger with its scopes, targets and an example |
| `documentation/dynamic_variables_documentation.md` | the values script can read without setting them, per scope |
| `documentation/script_math_functions.md`, `script_collection_input.md`, `script_collection_operator.md` | the statements of a math expression; inputs and operators of a collection |
| `documentation/loc_objects_documentation.md`, `loc_formatter_documentation.md` | `[Object.Property]` in localisation; the formatters (`idea_desc\|...`) |
| `documentation/console_commands_documentation.md` | console commands, among them the ones that run and inspect script |
| `common/scripted_guis/_documentation.md` | the whole definition of a scripted GUI, as one commented example (145 lines) |
| `common/on_actions/_documentation.md`, `common/collections/_documentation.md`, `common/script_constants/documentation.md` | hooks that run script at fixed moments; named collections; constants |
| `common/scripted_guis/*.txt` with `interface/*scripted_gui*.gui` | the 17 vanilla scripted GUIs |
| `localisation/english/*.yml` | how vanilla writes values into texts |
| The New Order: Last Days of Europe 1.10.0b, Workshop id 2438003901, `supported_version="1.19.*"`; on this machine under `steamapps/workshop/content/394360/2438003901/` | 133 files and 56,916 lines under `common/scripted_guis/`, with their containers under `interface/`; 122 scripted localisation files. Named below as TNO with the path inside the mod |

The lookup scripts read a mod too: add `-Mod 2438003901` to `Find-HoiUsage.ps1` or `Find-HoiDefinition.ps1 <name> -Type scripted_gui`.

Look-ups: `Find-HoiDoc.ps1 <name>` prints one entry, `Find-HoiDoc.ps1 -ListScope COUNTRY -Kind trigger` everything valid in a scope, `Find-HoiUsage.ps1 <name>` the vanilla uses, `Find-HoiDoc.ps1 -Topic scripted_guis` a format note.

## The language

<!-- knowledge:begin alias=1440p-script:L format=table -->
<!-- Generated by Export-HoiKnowledge.ps1 from the central knowledge register. Do not edit between the markers. -->

| # | Fact | Status | Evidence |
|---|---|---|---|
| L1 | **Script is nested `key = value` and `key = { ... }` blocks in `.txt` files under `common/`, UTF-8 without BOM.** A trigger asks a question and is true or false; an effect changes the game. A block takes one kind or the other, never both. Status note: every documented example has this shape | recalled | effects and triggers documentation |
| L2 | **Every trigger and effect runs in a scope: the thing it is about.** The documentation knows the scopes COUNTRY (323 effects, 336 triggers), STATE, CHARACTER, INDUSTRIAL_ORG, SPECIAL_PROJECT, OPERATION, COMBATANT, FACTION, PURCHASE_CONTRACT, RAID_INSTANCE, STRATEGIC_REGION, ACE, and "any" (104 effects, 94 triggers). A command used in a scope it does not support does nothing or logs an error. | documented | "Supported Scopes" line of each entry |
| L3 | **A division is a scope too, reached from a country with `every_country_division`, `random_country_division` and `any_country_division` (each with a `limit`).** The documentation lists the commands of that scope with an empty scope line: effects `change_division_template`, `set_unit_organization`, `destroy_unit`, `add_history_entry`, `add_divisional_commander_xp`, `promote_officer_to_general`; triggers `unit_strength`, `unit_organization`, `division_has_majority_template`, `division_has_battalion_in_template`, `is_unit_template_reserves`, `has_officer_name`. Divisions in the field only; a division in training is not one. Status note: that training lines are left out: recalled | documented | effects and triggers documentation |
| L4 | **Scope targets `THIS`, `ROOT`, `PREV`, `FROM` (and `OWNER`, `CONTROLLER`, `OCCUPIED`, `CAPITAL`) name other scopes from inside a block.** In a scripted GUI with `player_context` the scope is the player's country. Status note: "Supported Targets"; `_documentation.md` of scripted GUIs | documented | - |
| L5 | **`if = { limit = { <triggers> } <effects> }` with `else_if` and `else`; `AND`, `OR`, `NOT`, `count_triggers`, `hidden_effect`, `hidden_trigger`, `random`, `random_list`.** Status note: but `if` only as "a conditional effect": `limit`, `else_if` and `else` are vanilla (thousands of uses under `common/`) | documented | effects and triggers documentation |
| L6 | **Variables are numbers stored on a scope (country, state, character) or globally.** Variables are numbers stored on a scope (country, state, character) or globally: `set_variable`, `add_to_variable`, `subtract_from_variable`, `multiply_variable`, `divide_variable`, `modulo_variable`, `round_variable`, `clamp_variable`, `clear_variable`; read with `check_variable = { var = a value = b compare = less_than }` and `has_variable`. `set_variable = { name = 42 }` is the short form. All work in any scope. Status note: `set_variable`, `add_to_variable` and `check_variable` confirmed (D0) | documented | effects and triggers documentation |
| L7 | **A variable that was never set reads as 0.** A variable that was never set reads as 0: the probe's `NOT = { check_variable = { x = 1 } }` was true before the first click, and an `x` property on an unset variable put the button at 0. | confirmed | D0 launch 2 |
| L8 | **Temp variables (`set_temp_variable`, `add_to_temp_variable` ...) live for one run of a block and need no scope.** They also work inside triggers. | documented | triggers documentation lists them |
| L9 | **A variable is addressed across scopes as `ROOT.name`, `FROM.name`, `global.name`, `TAG.name`, `event_target:x`.** A variable is addressed across scopes as `ROOT.name`, `FROM.name`, `global.name`, `TAG.name`, `event_target:x`; a value with a parameter as `name@token` (`num_equipment@infantry_equipment`); an array element as `array^index`. Status note: (localisation and `SOV_paranoia_system_scripted_gui.txt`); `@` documented in the dynamic variables | vanilla | - |
| L10 | **Arrays hold numbers or scopes, with effects to add, remove, resize and search.** Arrays: `add_to_array`, `remove_from_array`, `clear_array`, `resize_array`, temp twins of each, `is_in_array`, `find_highest_in_array`, `find_lowest_in_array`, `random_scope_in_array`. An element is a number or a scope (`add_to_array` without a value adds the current scope). | documented | effects documentation |
| L11 | **Loops are `for_each_loop`, `for_each_scope_loop`, `for_loop_effect` and `while_loop_effect`, each with a `break` temp variable.** Loops: `for_each_loop` (value and index of each element in temp variables `v` and `i`), `for_each_scope_loop` (scopes to each element), `for_loop_effect` (start, end, step), `while_loop_effect` (a trigger as `limit`); each has a `break` temp variable. `all_of`, `any_of`, `all_of_scopes`, `any_of_scopes` are the trigger side. | documented | effects and triggers documentation |
| L12 | **A value can be a math expression: a block that starts with `value = ...` and is changed by statements in order.** Math expressions: a value can be a block that starts with `value = ...` and is changed by statements in order (`add`, `subtract`, `multiply`, `divide`, `mod`, `min`, `max`, `clamp`, `round`, `pow`, `root`, `log`, comparisons that give 1 or 0, `if` and `else`, `every_collection`). Fixed point; a broken expression counts as 0. `set_variable = { n = { value = a multiply = 2 add = 1 } }`, and `check_expr = { ... }` as a trigger. Said to be faster than temp variables. Status note: new to the agent | documented | `script_concept_documentation.md`, `script_math_functions.md` |
| L13 | **Collections are sets of countries or states built from an input and operators.** Collections: sets of countries or states built from an input (`game:all_countries`, `game:all_states`, `game:scope`, `collection:<name>`) and operators (`faction_members`, `owned_states`, `controlled_states`, `country_and_all_subjects`, a `limit`). Used by `collection_size`, `any_collection_element`, `all_collection_elements`, `every_collection_element`. Countries and states only: no collection of divisions or templates. Status note: new to the agent | documented | `script_collection_input.md`, `script_collection_operator.md` |
| L14 | **Script constants: named numbers in `common/script_constants/`, usable as `constant:<group>.<name>` wherever a variable is accepted.** No cost at run time. Status note: new to the agent | documented | `common/script_constants/documentation.md` |
| L15 | **`meta_effect` and `meta_trigger` build a command from text with `[PLACEHOLDER]` parts filled from variables, for cases where a name must be computed.** | documented | effects and triggers documentation |
| L16 | **Scripted effects and scripted triggers (`common/scripted_effects/`, `common/scripted_triggers/`) are named blocks to reuse.** Status note: vanilla has both folders | recalled | - |
| L17 | **`on_actions` run effects at fixed moments: `on_startup`, `on_daily`, `on_daily_TAG`, `on_weekly`, `on_monthly`, and many for wars, leaders and states.** None fires when a division is queued, trained or deployed. | documented | `common/on_actions/_documentation.md` |
| L18 | **Flags (`set_country_flag`, `has_country_flag`, `set_global_flag`) are yes or no markers with an optional number and lifetime.** | documented | effects documentation |
| L19 | **A token variable is saved as its index in the game's table of names, so adding a mod's tokens changes the meaning of tokens an existing save holds.** A variable that holds a token (`set_variable = { x = token:some_key }`) is written to the save as the token's index in the game's table of names, not as the name. The names a mod adds through `common/synchronized_dynamic_tokens/` are numbered after every name loaded before them, in the sorted order of that file. So a build of a mod that adds or removes names, or a playset that loads other mods before it, gives every saved token of an existing save another meaning: a kind of line reads as another text key, a cached sprite name as another sprite. What to do: a page that keeps tokens in a save keeps beside them a small dictionary of the numbers of a few known names, compares it on load or first use, and rewrites its tokens when they moved. Cached names (portraits, trait names) carry a stamp that goes stale with the dictionary, so they are looked up again. Names that cannot be told apart afterwards (victory point names in HOI4 1440p UI Mod) are replaced by something recoverable. | confirmed | the user's binary save `USA.hoi4` (2026-10-16) with HOI4 1440p UI Mod: every saved kind of a War Diary line was 22336 plus the sorted rank of its key in `mod1440_tokens.txt`, matching the kind counters exactly; the redesign build added about 3500 names and every old line showed another key (raw `GFX_portrait_...` strings, one general's portrait on every line). The repair (`mod1440_tk_fix`, `kept_tokens()` in tools/build_records.py) restored the lines in the tester's re-test of 2026-10-16. |
| L20 | **on_startup runs when a game starts, not when a saved game is loaded.** `on_startup` runs when a game starts, not when a saved game is loaded. Vanilla relies on it for one-time setup (`common/on_actions/00_on_actions.txt`, the relations block near line 1634), and a game that gets hoi4-1440p-ui-mod after its start has no History column until the next `on_monthly` and no top bar strip variables until the next `on_daily`: both pages carry a fallback for a save that never ran the mod's `on_startup`. What to do about it: anything a mod sets up in `on_startup` needs a second path for a save that predates the mod or the build, such as a check on the daily hook or on the first click. | vanilla | vanilla's own use, and the two fallbacks of hoi4-1440p-ui-mod (History since 2026-10-12, the top bar strip's fixed twin since 2026-10-17). Inferred, not watched in a load. |

<!-- knowledge:end -->

## Localisation

<!-- knowledge:begin alias=1440p-script:T format=table -->
<!-- Generated by Export-HoiKnowledge.ps1 from the central knowledge register. Do not edit between the markers. -->

| # | Fact | Status | Evidence |
|---|---|---|---|
| T1 | **A mod localisation file must be UTF-8 with BOM, named `<name>_l_<language>.yml`, and must be packaged.** The mod's texts are read from `localisation/english/<name>_l_english.yml`: UTF-8 **with** BOM, first line `l_english:`, entries ` KEY:0 "text"`. A mod needs one file per language of the game, even with the same English texts: without a file for the player's language the game shows the bare key. The packaging step must put `localisation/` into the archive. Status note: confirmed for English (read with a BOM; `error.log` named none of the probe's three files); the other languages untested **The suffix is the whole rule** (seen on 1.19.4.1, 2026-10-30): files named `mod1440_l_traits_english.yml` (the `_l_` inside the name, not before the language) were not read at all: every key in them showed as its bare key in a tooltip, with no line in `error.log`. Renamed to `mod1440_traits_l_english.yml` they were read after a restart. HOI4 Manager Pages has a test that fails on a file under `localisation/` not ending in `_l_<its folder's language>.yml`. | confirmed | D0 launch 2 (1440p rows X5 and W9), D2 package listing |
| T2 | **`[?variable]` in a text shows the value of a variable or of a dynamic variable of the scope the text is shown in.** Status note: X2 | confirmed | D0 launch 2 |
| T3 | **A format follows a bar: `[?v\|0]` no decimals, `[?v\|1]`, `[?v\|2]`; `%` as a percentage; `Y`, `G`, `R`, `H` a colour; `+` a sign with green and red by sign.** Combined freely: `\|%Y0`, `\|+0`. The game's documentation does not describe them; the D0 probe showed `1639.884k` with no format, so a format is needed for tidy numbers. Status note: (145 uses of `+0`, 82 of `Y0`, 60 of `%` in the English localisation); the meaning of each letter recalled | vanilla | `localisation/english/` |
| T4 | **`[Scope.GetName]`-style calls read properties of localisation objects (Country, State, Character, UnitLeader, Faction ...).** `[Scope.GetName]`-style calls read properties of localisation objects (Country, State, Character, UnitLeader, Faction ...); a variable that holds a scope can be used the same way (`[?global.x.GetName]`). `[OBJECT ? 'KEY : 'KEY]` chooses by whether an object exists. Status note: vanilla | documented | `loc_objects_documentation.md`, `script_concept_documentation.md` |
| T5 | **Scripted localisation (`common/scripted_localisation/`).** Scripted localisation (`common/scripted_localisation/`): `defined_text = { name = GetX text = { trigger = { ... } localization_key = KEY } ... }` picks a text by triggers and is called as `[GetX]`. Vanilla scripted GUIs use it to pick an image: `image = "[INS_GET_..._COLOR]"`. This is the way to turn a number into words or into a sprite. | vanilla | `common/scripted_localisation/00_scripted_localisation.txt`, `common/scripted_guis/INS_revolution_scripted_gui.txt` |
| T6 | **Bindable localisation: where the documentation says so, a text can be a block with `localization_key` and named parameters that fill `$PARAM$` in the text.** Formatters (`idea_desc\|<idea>`, `tech_effect\|<tech>`, `character_name\|<id>` and five more) produce a ready description. | documented | `script_concept_documentation.md`, `loc_formatter_documentation.md` |
| T7 | **Colour codes (`§Y...§!`) and text icons (`£GFX_...`) inside a text.** | vanilla | `localisation/english/` |

<!-- knowledge:end -->

## Scripted GUIs

A scripted GUI is an entry in a file under `common/scripted_guis/` that names a container from an interface file and says where it is attached, when it shows, and what its widgets do. Everything in this table that is not marked confirmed comes from the 145 lines of `common/scripted_guis/_documentation.md`.

<!-- knowledge:begin alias=1440p-script:G format=table -->
<!-- Generated by Export-HoiKnowledge.ps1 from the central knowledge register. Do not edit between the markers. -->

| # | Fact | Status | Evidence |
|---|---|---|---|
| G1 | **`context_type` sets the scope and the place.** `context_type` sets the scope and the place: `player_context` (the player's country), `selected_country_context`, `selected_state_context`, `diplomacy_target_context`, `decision_category`, `diplomatic_action`, `national_focus_context`, `country_mapicon`, `state_mapicon`. Status note: `player_context` confirmed (X1) and mod (71 TNO files); `decision_category` vanilla; the state, country and map icon contexts mod | documented | - |
| G2 | **`window_name` is the container in a `.gui` file.** `parent_window_token` attaches it to a game window: `top_bar`, `decision_tab`, `technology_tab`, `trade_tab`, `construction_tab`, `production_tab`, `deployment_tab`, `logistics_tab`, `diplomacy_tab`, `politics_tab`, `national_focus`, `selected_country_view` (with `_info` and `_diplomacy`), `selected_state_view`, the four ledgers and the eleven technology folders. Without it the container hangs on the main window. Status note: `deployment_tab` confirmed (X1) and mod; twelve other tokens mod (56 TNO files: `politics_tab` 29, `top_bar` 25, `decision_tab` 19, `trade_tab` 12 ...). TNO also uses `officers_tab`, which the documentation does not list | documented | - |
| G3 | **`parent_window_window`, as the scripted GUI documentation writes it, is not a key the game reads; the executable knows `parent_window_name`.** `common/scripted_guis/_documentation.md` shows `parent_window_window = "container_name"` to attach to a container by name and says it may not work. The string `parent_window_window` is nowhere in hoi4.exe 1.19.3, so the parser cannot know it. `parent_window_name` is there, next to `parent_window_token` and other interface keys: probably the key the documentation means, untested in the game. No vanilla scripted GUI uses either. `parent_scripted_gui` attaches to another scripted GUI. `map_mode` limits it to one map mode. Status note: until 2026-10-15 the register held the documented spelling as an untested way to attach to any container. | executable | string search of hoi4.exe 1.19.3 on 2026-10-15: no `parent_window_window`, one `parent_window_name`; vanilla `common/scripted_guis/` searched for both. |
| G4 | **`visible = { <triggers> }` shows or hides the whole container.** Status note: `always = yes` confirmed | documented | - |
| G5 | **A scripted button runs `<button>_click` on a click, with variants for the right button and for modifier keys.** `effects = { <button>_click = { ... } }` runs on a click; `<button>_right_click`, and `_alt_`, `_control_`, `_shift_` before `click` for the combinations. The game's documentation names them too (`button_name_alt_right_click`, `common/scripted_guis/_documentation.md`), and hoi4.exe 1.19.3 holds the suffixes `_control`, `_alt` and `_shift` next to `_click`, `_right_click` and `_click_enabled`. Status note: `_click` confirmed while paused (X3); the others mod (TNO: 205 `right_click`, 101 `shift_click`, 92 `control_click`, 11 `alt_click`) | confirmed | - |
| G6 | **`<button>_click_enabled` greys a button out and `<widget>_visible` hides a widget.** `triggers = { <button>_click_enabled = { ... } <widget>_visible = { ... } }` greys a button out or hides a widget. Status note: `_visible` confirmed (X4) and vanilla (`RAJ_tax_fraud_scripted_gui.txt`); `_click_enabled` mod (60 TNO files) | confirmed | - |
| G7 | **`properties` sets a widget's sprite, frame and position from script.** `properties = { <widget> = { image = "<scripted loc>" frame = <variable> x = <variable> y = <variable> } }` sets a widget's sprite, frame and position from script. Status note: `x` confirmed (X4); `frame` and `image` vanilla (11 of 17 files); all four mod (TNO: `frame` 1169 times, `image` 556, `x` 196, `y` 201) | confirmed | - |
| G8 | **The texts of a scripted container are ordinary text boxes whose `text` is a localisation key.** Texts of the container are ordinary text boxes whose `text` is a localisation key; values come in through `[?variable]` (T2). `pdx_tooltip = "KEY"` on a widget gives it a tooltip. Status note: (X2); the tooltip vanilla (`interface/RAJ_eic_tax_fraud.gui`) | confirmed | - |
| G9 | **`dynamic_lists` builds one copy of an entry container for each element of an array.** `dynamic_lists = { <grid> = { array = <array> value = v index = i change_scope = yes entry_container = "<container>" } }` builds one copy of a container per element of an array, with the element in a temp variable or as the scope. The grid is a `gridboxtype` with `slotsize = { width = 1 height = 1 }` inside a scrolling container, and the entry is a top-level container of the same `.gui` file: the same arrangement as the vanilla lists of Engine Facts S27. A list can sit inside the entry of another list, its array named with the outer value (`array = TNO_plot_points@var:plot`). `change_scope` is used with arrays of countries and states. Status note: (54 TNO files; the smallest is `common/scripted_guis/TNO_MEX_Plot_GUI.txt` with `interface/Mexico/TNO_MEX_Plot_GUI.gui`); not run by this project | mod | - |
| G10 | **A scripted GUI is updated every tick by default.** `dirty = <variable>` updates it only when that variable changes; an effect then changes the variable to ask for an update (`add_to_variable = { <name>_dirty = 1 }` at the end of each click effect). The variable can be a value of the game: `dirty = resource@power`. Status note: (40 TNO files, for example `TNO_economy.txt`); not run by this project. The probe's values did follow the game while it was paused (X2), without `dirty` | mod | - |
| G11 | **The AI can click scripted buttons: `ai_enabled`, `ai_check`, `ai_test_interval`, `ai_weights`.** A panel for the player's eyes needs `ai_enabled = { always = no }`, so the AI never spends time on it. Status note: the keys mod (18 TNO files); that a panel without them costs the AI nothing is not known | mod | - |
| G12 | **A scripted button that runs an effect shows that effect's tooltip when hovered.** Status note: untested | recalled | - |
| G13 | **A window of its own, not tied to a tab.** A `player_context` GUI without `parent_window_token` is a free window: its container has a size (533x623 in the example), `moveable = yes`, a `visible` trigger on a country flag, and a close button whose effect clears the flag. A button attached to a tab sets the flag. This is the pattern for a manager window that opens on a click and gives the map back on another. Status note: `TNO_MEX_Plot_GUI.txt`; the opener pattern in `TNO_Additional_Help_Buttons.txt`, attached to `deployment_tab` | mod | - |
| G14 | **A scripted container can cover a whole tab.** TNO lays a 555 px wide, full-height container with one image over Recruit & Deploy for some countries, to close the screen off. So a scripted container is drawn above the vanilla widgets of its tab; that it also takes their clicks is what TNO relies on and this project has not seen. Status note: `Antarctica_Deploy_Panel` in TNO's `interface/countrydeploymentview.gui` | mod | - |

<!-- knowledge:end -->

What The New Order uses (133 files, 56,916 lines; the largest are `TNO_Antarctica_GUI.txt` with 4458 lines and `TNO_economy.txt` with 4361): `player_context` in 71 files and `decision_category` in 77; a `parent_window_token` in 56; click effects in 97 (2374 of them); `_visible` triggers in 94 and `_click_enabled` in 60; `properties` in 115; `dynamic_lists` in 54; `dirty` in 40; AI keys in 18; loops inside effects in 16. It never uses `parent_window_window` or `parent_scripted_gui`. TNO also replaces whole vanilla interface files, `interface/countrydeploymentview.gui` among them, which matters for the compatibility checkpoint of the [Roadmap](Roadmap.md) and is not a pattern for this mod.

What vanilla uses (17 files, 9 to 86 lines each): all are `context_type = decision_category`, referenced from `common/decisions/categories` (13) and one scripted diplomatic action. 11 use `properties` with `frame` or `image`; one uses `_visible`. None uses `player_context`, a `parent_window_token`, click effects, `dynamic_lists`, `dirty` or the AI keys.

## What script can read for a recruitment manager

All in country scope, from `dynamic_variables_documentation.md` and `triggers_documentation.md`. "Read" means usable as `[?name]` in a text and in `check_variable`.

| Value | Name | Status |
|---|---|---|
| Manpower in the training queue | `amount_manpower_in_deployment_queue` | confirmed (0, then 28800 after three divisions were queued) |
| Manpower free to use, in thousands | `max_available_manpower_k`; `manpower_k`, `max_manpower_k` | first confirmed; others documented |
| Manpower in the field, in thousands | `deployed_army_manpower_k`, `deployed_navy_manpower_k`, `deployed_airforce_manpower_k`, `deployed_total_manpower_k` | documented |
| Manpower the garrisons need | `garrison_manpower_need` | documented |
| Divisions, armies, battalions | `num_divisions` (confirmed: 30), `num_armies`, `num_armies_with_type@<type>`, `num_battalions`, `num_battalions_with_type@<sub unit>` | documented |
| Equipment in stock, per type | `num_equipment@<equipment>` | confirmed (52, then 0 once the queue took it) |
| Equipment in the field, and what the field needs | `num_equipment_in_armies@<equipment>`, `num_target_equipment_in_armies@<equipment>` (and `_k`) | documented. The difference is the shortage of the divisions in the field |
| Stock against use | trigger `stockpile_ratio` ("2 means double in stockpile of what is fielded or in training") | documented; a trigger, so it gives yes or no against a threshold, not a number |
| Army experience, command power | `army_experience` (confirmed), `command_power`, `command_power_daily` | documented |
| Factories | `num_of_military_factories`, `num_of_available_military_factories`, `manpower_per_military_factory` | documented |
| Equipment produced so far | `total_equipment_produced_<kind>` (infantry, artillery, armor, motorized ...) | documented |
| Conscription | triggers `conscription_ratio`, `current_conscription_amount`, `target_conscription_amount` | documented; triggers |
| Whether a template exists | trigger `has_template = "<name>"`, `has_template_majority_unit`, `has_template_containing_unit` | documented |
| Divisions in the field by kind or state | a loop: `every_country_division` with `limit = { division_has_majority_template = <sub unit> }` or `unit_strength < 0.8`, adding 1 to a variable | documented; untested. The cost of looping over every division on each update is not known |

What script cannot read, as far as the documentation goes: a list of the country's templates or their names; the lines of the training queue, their names, progress, equipment or location; the priority dots of reinforcements, upgrades and the other rows.

## What script can do

| Wish | Effect | Status |
|---|---|---|
| Queue a division for training, add a line, cancel one | none | documented list has no such effect |
| Set a deploy location, a priority, the series count | none | the same |
| Put a division on the map at once | `create_unit` | documented. It skips training, manpower and equipment cost: a cheat, not a quality of life option |
| Lock, cap or delete a template | `set_division_template_lock`, `set_division_template_cap`, `clear_division_template_cap`, `delete_unit_template_and_units`, `set_division_force_allow_recruiting`, each by template name | documented. They change rules of the game, which a UI mod should not do |
| Change the template of divisions in the field | `change_division_template` in division scope | documented |
| Remember a choice of the player (a folded panel, a chosen equipment type) | `set_variable` on the country | confirmed |
| Write to a log | `log = "text [?var]"` (to `game.log`), `print_variables` (to a file) | documented |

So the buttons of a manager panel are for the panel itself: fold, switch what it shows, pick the equipment to watch. The actions of recruiting stay with the vanilla buttons.

## Testing script

| Tool | Use | Status |
|---|---|---|
| `error.log` | a broken file or an unknown command is named here at load; the harness already diffs it | confirmed for interface files; for script recalled |
| `log` effect, `game.log` | a button's effect writes a line the harness can read, so a click is proved without a screenshot | documented |
| Console `eval_effect`, `eval_trigger`, `effect`, `trigger` | run an effect or a trigger from the console on the selected scope | documented; not tried |
| Console `get_var`, `set_var`, `list_vars`, `trigger_docs`, `loc_check`, `update_loc` | read and set variables; dump the trigger list; check and reload localisation | documented; not tried |
| Whether script files reload in a running game | - | yes: script, localisation and the layout of a scripted GUI are read again; a new `.gui` file is not (X23, X27). Other interface files are not (H3) |

## Costs of the first scripted GUI

- **Checksum:** a file under `common/` changes it. Ironman and achievements stop, and in multiplayer every player needs the mod. Accepted by the user on 2026-10-12.
- **Saves:** variables the panel sets are stored in the save [SGUI-044]. Whether removing the mod leaves them behind unused and harmless is untested.
- **Performance:** an update every tick unless `dirty` is used (G10). Loops over all divisions belong behind a button or a daily `on_action`, not in a text that is redrawn every tick.
- **Other mods:** a scripted GUI adds a container and does not replace one, so it does not collide with a mod that reworks the same tab; it can overlap what that mod draws.

## What the probe and the builds settled

The eight questions this page ended with on the morning of 2026-10-12, and what a launch said. The row of [Engine Facts](Engine-Facts.md) has the evidence.

| Question | Answer | Row |
|---|---|---|
| `dynamic_lists` from an array of our own, with and without `change_scope` (G9) | Works for numbers, states and generals; a slot of 1x1 with `add_horizontal = no` stacks rows, a real slot with `add_horizontal = yes` runs sideways | X10, X12 |
| A window of its own, opened and closed; clicks under a scripted container (G13, G14) | Works; with a background it takes every click inside its rectangle | X7, X9 |
| `_click_enabled`, `_right_click`, the tooltip of a scripted button (G5, G6, G12) | The first two work. A button whose effect only sets a variable shows no tooltip; `pdx_tooltip` gives it one. G12 is not confirmed. Shift, control and alt clicks stay untried | X14 |
| `dirty` (G10) | Works, also for the first drawing: the page shows raw text until the variable first changes | X16 |
| A loop over every division | Under a hundredth of a second for 138 divisions | X22 |
| `log` and the console for the harness | `log` writes to `game.log` with values; `effect <name>` runs a scripted effect. `get_var` and `list_vars` were not needed and not tried | X25, X31 |
| Reload without a restart | Script, localisation and the layout of a scripted GUI are read again; a new `.gui` file is not | X23, X27 |
| The shortage the logistics screen shows | `num_equipment@` is its stock column and never negative; in the field against needed covers the divisions in the field, not those in training | X19, X29 |

Found on the way, and not on this page before:

- **A page attached to a tab is cut off at the tab's window** unless that window has `clipping = no` (X6). This decides where a page can be docked.
- **`_visible` and the `x`, `y` properties do not act on a nested container** (X15), and **a property takes a variable only**, no math expression (X26). So a group that hides is a scripted GUI of its own, and a derived number is worked out by an effect.
- **State and general values** read in a list row (X20, X21); `goto_state` wants country scope: `ROOT = { goto_state = PREV }` (X13).
- **Number formats** (X18) and more on texts (X30): row T3 above is confirmed and extended by `=` (the sign), `*` (K and M) and `-` (colours turned).
- **Names after `@` must be listed** in `common/synchronized_dynamic_tokens/` (X24, X31).
- **Hooks:** `on_startup` seen; `on_daily` and `on_monthly` written after vanilla and The New Order. No check has seen them run; the user reported them working after playing (X28).

## What the research for the role-play pages added

Read on 2026-10-12 for Milestone E. The facts, with their sources, are rows R1 to R14 of [Roleplay Pages](Roleplay-Pages.md): the arrays and single values of a country that hold characters, the texts of a general, a character, a country and an ace, the hooks and their scopes, scopes and text keys held in variables, flags with a number on a character, how a division is reached, and `add_history_entry`. The [E0 probe](phases/E0-roleplay-probe.md) tried them in game the same day: rows X32 to X49 of [Engine Facts](Engine-Facts.md). What it found beyond the documentation:

- A variable set in a character's scope stays there; a country's variable or array can hold the character, and `[?holder:variable]` reads his variable from the country.
- In a list row scoped to something else, a variable of the country needs `ROOT.` before its name.
- `[?variable.GetTokenLocalizedKey]` writes the text of a key held as `token:<key>`; the text is not worked out further. A scripted localisation's text is.
- `@var:<variable>` passes a variable where a value takes a name after `@` (`num_units_in_state@var:x`).
- The console command `effect` runs in the scope of what is selected.

## What the portraits and the victory points added

Read on 2026-10-13, after the user asked for portraits, a record of victory points and a file for each war. Sources and status: rows X58 to X64 of [Engine Facts](Engine-Facts.md); each was seen in the game that day.

- **`NOT = { A B }` is "neither A nor B"**, not "not both". The test "this holder is not the one written down" was written that way for the offices of the Government page and missed a holder replaced on the same day. "Not both" is `OR = { NOT = { A } NOT = { B } }`.
- A character is known by `is_character = <character>` in his own scope; a country's head of government is the variable `country_leader`. `is_character` logs an error for a character no country has recruited, so the country is asked `has_character = <character>` first (the game's own scripts do the same).
- **A temporary variable is shared with every scripted effect a run calls.** A called effect that sets `ev_c` changes the caller's `ev_c` (X64). Temporary variables carry the prefix of their effect.
- **A number written with `|0` has its fraction cut off**, it is not rounded (X65). Where a difference stands beside its two terms, round it up in script first.
- A state's scope can be entered by its number: `64 = { ... }`. The victory point script takes the state of a point that way.
- A text key held in a variable gives its own name with `[?v.GetTokenKey]` and its text with `[?v.GetTokenLocalizedKey]`; the first is what an icon's `image` wants.
- `global.province_controllers^<province>` and `global.year` are read like any array element and value.

## What the officers of another mod taught

Found on 2026-10-13, when the user's test showed that generals a mod adds were missing from the Officers list. Rows X66 to X70 of [Engine Facts](Engine-Facts.md).

- **Go through officers with `every_army_leader` and `every_navy_leader`**, not with the arrays `army_leaders` and `navy_leaders`: an array holds nothing in the place of a leader whose command came by an effect, and the loop over it then stays in the scope it was in.
- **`THIS` is not a way to keep a person.** For such a leader it is -21474.83648. `mod1440_of_me = yes` leaves what a variable can hold of the officer in scope in `of_me` (0: not known yet).
- **A variable that holds nothing leaves the scope where it is.** `var:v = { ... }` then runs in the scope around it, without a word in the log. A test that must fail for an empty variable is run from a scope that cannot pass it: the search asks from the country's scope, never from the leader's own.
- **Numbers have five decimals**, and a person in a variable is a number: -21474.83648 and up for unit leaders by their number, 5368.70912 and up for characters by their place. A sum on it works.
- **A loop ends after 1000 rounds.** Longer: a loop in a loop.
- **`on_unit_leader_created` fires for `create_corps_commander`, not for `add_corps_commander_role`.**
- **`has_character = <name>` is false and silent for a name the game does not know.**

## Open questions

1. `on_daily` and `on_monthly` running for a player: answered by the user's play on 2026-10-12 ("everything seems to be working, including the history ticks"). Still true: no check runs time.
2. Shift, control and alt clicks: the game's documentation and the executable both have them (`<button>_shift_click` and so on, G5); the harness still cannot make such a click, so none is seen in a check.
3. A list filled straight from a game array (X11): one row showed; not needed so far.
4. Buildings that stand in provinces (forts, naval bases) through `building_level@`: 0 in the two states tried.
5. What a scripted GUI costs while the game runs at speed: every frame rate here was read with the game paused.
