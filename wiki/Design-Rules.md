# Design Rules

> (from the 1440p mod) Copied at the split of 2026-10-21 from the HOI4 1440p UI Mod, whose reworked vanilla screens it still describes beside the pages; a later pass trims it to the pages.

Rules every reworked screen follows, what a redesign can and cannot add, and what the first screens taught us about the engine. Items marked **provisional** have not been judged in game yet; the register of every engine fact with its status is [Engine Facts](Engine-Facts.md), and each phase keeps its own notes under `wiki/phases/` (template: [Phase Template](Phase-Template.md)).

## Target

- 2560x1440 at 100% UI scale (`gui_scale=1.0`).
- No `size` may exceed 2560x1440. The test suite enforces this.
- Panels docked at the top left may run down to about y 1130. The A1 list ends there and leaves the bottom bar free.
- **Provisional:** centred windows leave at least 100 px free above and below, so they are at most about 1240 px high. The first centred window reworked is the air wing reorganisation (A7, 995 high); the tester has not judged it yet.

## What a redesign can add

A screen is re-laid out around what the player wants to see at once, not only enlarged. The engine limits what "new" can mean. Checked on game 1.19.3.

| Change | Possible | How, and the limit |
|---|---|---|
| Move, resize and regroup panels; dock windows side by side | Yes | Values in the `.gui` file |
| Give each existing value its own place: full names, a column per status, larger bars | Yes | Larger art is built from vanilla assets |
| Hotkeys, including key chords | Yes | A `shortcut` line on a button the game already has |
| Fixed text and icons: column captions, legends, static tooltips | Yes | A vanilla text key needs no file; new text needs a file under `localisation/` |
| Stat rows as tiles: a grid with two or more columns, a wrapped label over a larger value | Yes | `max_slots_horizontal` and `slotsize` of the grid, layout of the row window ([Engine Facts](Engine-Facts.md) W16); labels that vanilla cuts can be shown whole |
| Tab hotkeys | Yes | `shortcut` on the tab buttons (W19) |
| Cards, panels, grouped headers | Yes | A container named `mod1440_*` holds the card's background and the vanilla widgets that belong in it (W34). A background drawn behind widgets that stay where they are works too, and is the way when a widget has alternative positions: the code finds `positionType` entries only among the window's own children (W34), so such a widget stays there. A9 builds its cards that way |
| New live values the screen does not show today | Not in a vanilla window; yes in a scripted GUI, for values of the country, its states and its generals | The game fills only the widgets its code asks for. A scripted GUI reads script variables ([Engine Facts](Engine-Facts.md) X1, X2, X19 to X21) and changes the checksum |
| A value shown in two places | No | A second widget with the same name is dropped (W14) |
| Wrapping widgets in a new container (cards that own their content) | Yes, on the patched executable | Name the container `mod1440_*`. With `hoi4.exe` patched by the Modding Manager's `Scripts\Executable\Set-HoiRecursiveLookups.ps1` the game finds a vanilla widget inside it, for every element type but scrollbars, list boxes and browsers (W34); the test suite checks both. On an unpatched game such a widget stays empty unless its view searches nested containers (W15, W31) |
| Showing two tabs at once | No | Duplicate tab containers are dropped (W14), and the code hides the other tab's container |
| New buttons that do something | Not in a vanilla window; yes in a scripted GUI | A scripted button runs a script effect (X3); what it can do is what effects can do. In this mod it changes its page or moves the camera, nothing in the game ([Scripted GUIs](Scripted-GUIs.md), rule 1) |
| A table of states or generals, sorted by a click | Yes, in a scripted GUI | A scripted list filled from an array (X10), sorted by an effect (X22) |
| A graph over time | Yes, in a scripted GUI | Script writes the values down each month; each column is a progress bar it fills (X17) |
| Lists the code fills, in several columns | No | `max_slots_horizontal` is not followed by them (S29): the code places each row itself (S37) |
| A panel that narrows or hides by itself | No | No file can ask what the player is doing; a scripted panel can fold on a click (X4) |

Where a row says No, the reason is in the game's code, which the Modding Manager reads since 2026-10-15 (its Ghidra project of `hoi4.exe`; [Roadmap](Roadmap.md), Milestone F). The reading reopened two limits: wrapping widgets, through a local patch of the executable (W34), and the width of the priority rows, through their sprites (G16). It confirmed the others: a list the code fills places each row itself (S37), and a vanilla window shows only the values its code asks for (W33). A patch works only on this machine; this mod accepts that, and the user decides each patch (Roadmap, Decisions).

- **The game fills only the widgets its code asks for, by name.** A widget with a name the code does not know stays empty and does nothing when clicked. The names are stored as text in `hoi4.exe`, so they can be listed.
  - Which names the code looks up in a window, and how it finds each one, is read from the executable: the Modding Manager's `Artifacts/executable/window-bindings-1440p.md` for the reworked windows and `window-bindings-1440p-backlog.md` for the screens of Milestone C (its `Scripts/Executable/README.md` says how to make the list for another file).
  - Every name the code looks up in the reworked windows is a widget vanilla defines (W33); `entry` and `army_division_list` are names of objects the code inserts (W4). Name lookups ignore case (W32).
  - `tools/Show-CodeNames.ps1 <file.gui> <window>` is the older guess from where the names are stored in the executable; use it only for a window the reports do not cover.
- **Hotkeys.** A button takes one `shortcut` line per key: a single key (`"h"`), a combination (`"ctrl+b"`) or a chord (`"ctrl+g+s"`).
  - A window cannot carry a hotkey. Where vanilla wants one without a visible button, it places a button the code knows off screen (`select_hq_shortcut_anchor` at -1000,-1000). (W6)
  - `tools/Show-GuiOutline.ps1 <file.gui> <window> -All` shows each button's keys, so buttons without one stand out.
  - Before assigning a key, search the vanilla `interface/` folder for it. Vanilla has 483 `shortcut` lines in 105 files and reuses keys between screens (`h` is "hold" in both the army and the air panel).
  - Every single letter is taken by some vanilla screen. Free on 1.19.3 are most `shift+` and `ctrl+` combinations with a letter.
  - **Confirmed in game (A2):** `shift+u`, added by the mod to the unassign button of the division list, works. (W5)
  - **Not yet tested:** two visible buttons sharing a key. (W7)
- **Fixed text.** A text box with `text = "<key>"` shows that key's text in the game language.
  - **Confirmed in game (A2):** captions on the sort buttons of the division list, using vanilla keys such as `ARMY_SORT_NAME` ("Name"). A vanilla key needs no localisation file. (W8) Search `localisation/english/` for a key whose whole text is the word needed.
  - Name an added widget `mod1440_*` and give it `alwaystransparent = yes`, so clicks reach the button under it.
  - Text of the mod's own needs a file under `localisation/`: UTF-8 **with** BOM, the opposite of the rule for `.gui` files, and one file per language of the game, or a player of another language sees the bare key. (W9) The scripted GUIs use this since D2; `tools/build_managers.py` writes the files.
- **Scripted GUIs are the manager pages of Milestone D**, in the mod since phase D2 (decided by the user on 2026-10-12). They are the game's way to add new values and buttons, described in `common/scripted_guis/_documentation.md` in the game folder. Their rules, what each page shows and how to work on them are in [Scripted GUIs](Scripted-GUIs.md); what is known about the script language, with the source and status of each fact, is in [Script Reference](Script-Reference.md): look a command up there or in the game's documentation before writing it, never from memory.
  - They live in `common/`, so they change the checksum: the mod is not compatible with Ironman and achievements, and in multiplayer every player needs it. The user accepts this.
  - They attach to the top bar, the side tabs, the focus tree, the country and state views and the ledgers, or stand as windows of their own. A page attached to a tab shows beside the panel only if the tab's window has `clipping = no` ([Engine Facts](Engine-Facts.md) X6): the mod's Recruit & Deploy window and the vanilla Construction and Trade windows do. The selected army, air wings, navy and the designers are not among the attach points.
  - They work on a country, a state or a general, never on the selected army, division, wing or fleet, and they have no list of templates, training lines or production lines.
  - A page is a finished widget tree of the mod's own: the rules above about vanilla widget names do not bind it, and it is reworked in a running game (X23, X27).

## Overriding vanilla windows

- **Method:** one file per screen, `interface/zz_1440p_<screen>.gui`, containing only the reworked top-level windows. The vanilla file is not copied or replaced.
- **Why the `zz_` prefix:** when two loaded files define a window with the same name, the game uses the definition it loads last, and it loads `.gui` files in `interface/` in file name order. The mod's file must therefore sort after the vanilla file, and its name is written in small letters, since capitals sort before them. (L1, L2, L11)
- **Evidence** (override test, game 1.19.3, vanilla playset): a redefinition in `interface/zz_*.gui` took effect, one in `interface/aa_*.gui` did not, and one in `interface/1440p_ui/override_test.gui` did. `error.log` had no line about the duplicates. (L1 to L3, L5)
- **Windows whose vanilla file sits in a subfolder of `interface/`** (factions, international market, military industrial organisation, special projects): every subfolder loads after the root files, so a root `zz_` file does not override them. The override goes into that subfolder, `interface/<subfolder>/zz_1440p_<screen>.gui`, or into a subfolder of the mod's own that sorts after it; `interface/1440p_ui/` sorts before `factions`. Read in the code and seen in the game on 2026-10-15 with the international market: a copy in a root `zz_` file lost, one in `interface/international_market/zz_*.gui` won, and one in `interface/international_market/ZZ_*.gui` lost to the vanilla file. (L4, L11)
- **Next to a mod that replaces the whole vanilla file** the mod's window wins the same way (seen on 2026-10-13 with RBM's GFX Overhaul and the VNR - RBM patch, [Engine Facts](Engine-Facts.md) L7), and what that mod changed in the window is lost. What else two mods share, and how a playset is checked: [Compatibility](Compatibility.md).
- **How to test an override:** copy the vanilla window into a test file and add one extra icon and text box near the top (for example sprite `GFX_header_bg` and text "OVERRIDE TEST A"). If the marker shows in game, that file won. Use windows that open from a top bar tab, so the check takes seconds.
- **Widget names stay; the nesting may grow.** The engine binds data to widgets by `name` (without regard to case, W32). A reworked window keeps every named vanilla widget with its element type and the same chain of named vanilla parents. Between them it may add containers of its own, named `mod1440_*`, which the patched executable searches (W34); scrollbars, list boxes and browsers stay directly under their vanilla parent. Position, size, font and sprite are free to change. The test suite compares each window with its baseline this way. (W1, W15)
- **Every overridden window has a baseline.** The vanilla text of the window is saved under `baseline/`, and the test suite compares the mod's window against it. `tools/New-OverrideFile.ps1` exports it when it starts a screen file. `tools/Export-VanillaBaseline.ps1 <file.gui> <window>` exports one on its own, for example to refresh it after a game update.
- **Each window is overridden in one file only.** With two definitions the file that loads last wins silently. The test suite enforces this.
- **File-level `@variables` do not travel with a window.** If a vanilla window uses one (for example `@equipment_entry_heigth` in `airselectionview.gui`), define it in the override file too before overriding that window. Untested, so check it in game the first time. (L6; a variable defined inside the window does travel, L9)
- **Mod-only windows** (no vanilla counterpart) are named `mod1440_*`.
- **Under `common/` only the script of the scripted GUIs**, in four folders (`scripted_guis`, `scripted_effects`, `on_actions`, `synchronized_dynamic_tokens`), every file named `mod1440_*`. Nothing under `events/`, `history/` or `map/`. These folders are part of the game checksum; `interface/`, `gfx/` and `localisation/` are not. (L8)

## How the engine treats sizes and containers

The `.gui` files do not state these outright, and the static tests cannot catch them. Each one cost a game launch to find.

- **Find the window that holds a list by its looks, not its name.** The link between a list and its rows is made in game code. The air wing rows sit in `unassigned_airwings_view` (a frame on `GFX_tiled_window_1b_thin_border` around a `clipping = yes` list), not in the `air_selection` list of `air_selection_view`. Match the frame in a screenshot to a background sprite and a clipping list of the right size before changing a row size. (S4)
- **The same rows can sit in a different list in another state of the screen.** With an air group selected, the game puts the group badge and the whole wing list frame into `air_groups_view`, a list from another vanilla file (`airgroupview.gui`). It was left at 580 px, so the wider rows were cut off there, and nobody saw it until a tester created an air group. During the inventory, list the states of the screen (nothing grouped, a group selected, several selected) and ask for a screenshot of each. (S35)
- **A clipping list cuts off anything wider than itself.** A list box (`smoothListBoxType`, `listBoxType`) has no slot size. Its `size.x` must be at least the row width, and its parent frame must be wider by the scrollbar gutter (26 px on `GFX_tiled_window_1b_thin_border`). (S5) Once a list and its rows are known, the pair goes into `$listRowCases` in `tests/GuiInvariants.Tests.ps1`; the suite then fails if a row outgrows its list or the list's window is not overridden with it.
- **Sizes "set in code" are maximums.** A vanilla comment such as `height set in code, but initial value here is used for max allowed height` means the engine shrinks the window to its content and treats the written size as the limit. Raising it is how a list gets more visible rows. Search the vanilla windows for "set in code" during the inventory. (S1)
- **A window can run behind its neighbour.** The division list frame starts at the top of the army badges and continues behind them. A badge narrower than the list leaves the empty top of the frame showing beside it, so badge and list need the same width. (S7)
- **Alternative positions are widgets too.** A window can hold `positionType` entries that the game applies in another state, for example `select_all_button_army_group_position` on the army badge. When a widget moves, its alternative positions move by the same amount. (S8) Not every entry is an alternative position: the code reads 111 of them by name as positions, offsets, sizes or counts, listed with their values in the Manager's `Artifacts/executable/position-types.md` (S38). Changing one moves or sizes what the code places, for example the ship class picker beside the composition editor.
- **Some widths are computed from a grid.** The mission toolbar is as wide as the number of slots times `slotsize.width`, plus twice the grid's `position.x`. Vanilla marks this with the comment "X value becomes spacing on both sides of the window". The result depends on how many entries the player's DLC and mods add, so it cannot be made to fit for everyone. (S9)
  - Such a width is the floor for a block of aligned panels. The air wing panel is 705 wide because the mission bar is 703 at vanilla spacing; the rows would need less.
- **Tiled panels look smaller than their `size`.** Tiled sprites have a soft, partly transparent edge. Panels placed edge to edge therefore show the map between them, and panels of equal width do not end at the same visible edge. (G5)
  - `GFX_tiled_plain_bg_small`: visible area starts about 3 px inside the box on each side.
  - `GFX_tiled_window_1b_thin_border`: about 4 px at the top, 5 px at the right.
  - Values that gave touching, aligned panels in A1: place a `plain_bg_small` panel 6 px into the `plain_bg_small` panel above it, place a `thin_border` frame 8 px into the `plain_bg_small` panel above it, and make the `plain_bg_small` panel 2 px narrower than the frame.

## Spacing

The same distances everywhere, so that cards, columns and pictures read as one design (user, 2026-10-16). Measured in the file's pixels at 2560x1440. The ruleset that a layout is checked against (the look, fonts by role, fixed places, hotkeys) is [Design Language](Design-Language.md); this section keeps the reasons.

| Between | Space |
|---|---|
| An icon and its text, a value and its unit | 4 |
| Content and the edge of its card or plate; the items of one group | 8 |
| Two cards side by side or stacked | 6 (a tiled plate shows its edge about 3 px inside its size, G5, so the gap reads as 12) |
| Two columns or groups of a row; a group and the card after it | 16 |
| A picture and its frame | the same at both ends; where the code places the picture itself, measure it in the game first and size the frame around it |

- A new layout uses these values, and a layout script names them (`INFO_X = 298 + 16`). Screens built before 2026-10-16 follow them when a phase touches them again.
- First used by the card pass (A9: cards 6 apart) and production (C1: the column after the equipment plate starts 16 after it; the plate leaves 20 on each side of a picture that the code places at a fixed spot).

## Fonts

Larger text means choosing a larger font that vanilla already ships; which font each role takes is in [Design Language](Design-Language.md), "Fonts by role". Sizes in use in vanilla GUI files:

| Use | Vanilla fonts |
|---|---|
| Body text | `hoi_16mbs`, `hoi_18mbs` |
| Emphasis | `hoi_18`, `hoi_18b`, `hoi_20b`, `hoi_20bs` |
| Headers | `hoi_22tech`, `hoi_24header`, `hoi_30header`, `hoi_33`, `hoi_36header` |

- **Confirmed in game (A1):** `hoi_16mbs` to `hoi_18mbs` for row text, and `hoi_18` to `hoi_20b` for a row heading. (F1)
- Two 18 px lines fit a 48 px row at y 4 and y 22 (vanilla has 16 px lines at y 7 and y 23), so a larger font does not force a taller row.
- **Confirmed in game (A2):**
  - `hoi_18` to `hoi_20b` for division names, and `hoi_18mbs` to `hoi_20b` for the "30 Selected" count.
  - `hoi_16mbs` to `hoi_18mbs` for the commander's title, name and stat numbers on the army badge.
  - `hoi_18` to `hoi_20b` in an edit box (the army name), together with a wider box.
- Text inside a fixed-size box, such as a count badge, keeps its vanilla font. (F3)
- **Provisional:** every other step up in the table. (F4)
- **A text's width can be worked out before a launch.** The `xadvance` values in `gfx/fonts/<font>.fnt` add up to its width in pixels. For "Kavallerie-Kommando Insterburg" this gives 199 px in `hoi_18`, which vanilla cuts off at 175, and 231 px in `hoi_20b`; both matched the game. Use it to size name columns and to check that a caption fits its button. (W11)

## Lists and scrolling

- `slotsize.width` of a grid equals the width of the entry window that fills it. The link between a grid and its entry window lives in game code, so add the pair to `$entryPairCases` in `tests/GuiInvariants.Tests.ps1`. (S6)
- `scroll_wheel_factor` is a whole multiple of the row height. The test suite enforces this for every scroll container with one grid. Vanilla breaks the rule in places (45 for 30 px rows in the division name dropdown), so a window copied into an override file can fail the test until the value is rounded.
- **One entry window can fill several lists.** `unit_template_entry` fills three template dropdowns: two in the division list and one in the division details window. Widening an entry means widening every list that shows it, even in a window that is otherwise left alone; a scrolling list cuts off a wider entry. (W12) The window bindings report (which views look up the grid) and a search for grids with the same slot size help to find the lists.
- Dropdowns set `expandedOnTop = yes`.

## Sprites and backgrounds

- New sprites are named `GFX_1440p_*` and declared in `interface/1440p_ui.gfx`. A vanilla sprite name is declared again only when every place that shows the sprite should change, and those places are now known: the `.gui` files that name it (search vanilla `interface/`) and the code that sets it (the Manager's `Artifacts/executable/code-set-sprites.md`). The priority rows of Recruit & Deploy are such a case: the code puts the six row sprites only on those rows, and a wider texture under their names widens the rows (G16, Roadmap F3) [LOAD-012]. Such declarations go into `interface/zz_1440p_vanilla_sprites.gfx`, which sorts after the vanilla files, and each name into the list of the test "gives every declared sprite the GFX_1440p_ prefix, but the listed vanilla names" in `tests/GuiInvariants.Tests.ps1` (user's decision of 2026-10-16; used by A5 and C1).
- **No AI-generated images.** Every image is built from vanilla game assets.
- For a window or row that needs a larger background, use the first option that gives a clean result:
  1. An existing vanilla tiled window sprite, used as it is (for example `GFX_tiled_window_1b_thin_border`).
  2. A new tiled sprite declared in `interface/1440p_ui.gfx` that points at an existing vanilla texture file. No new image file.
  3. A background composed from several vanilla sprites: a tiled base plus vanilla frames, header bars and boxes placed as separate icons.
  4. A script that copies pixels from the vanilla bitmap into a larger texture. Output goes to `gfx/interface/1440p_ui/`.
- If none of the four looks clean, the window keeps its vanilla size and only its lists and fonts are reworked.
- **Judge each option in a preview image before it goes into the game.** Simulate option 2 by repeating the centre strip between the two border strips; `tools/stretch_background.py --preview <dir>` writes vanilla and widened frames side by side for option 4. This settled the A1 backgrounds without a game launch.

What A1 showed about the options:

- **Option 2 works for a texture with a plain middle.** Declare a `corneredTileSpriteType` with `size` equal to the texture size, a `borderSize` and `tilingCenter = yes`. On a button, use `quadTextureSprite` and `size = { x = .. y = .. }` instead of `spriteType`. Confirmed in game for the airbase row. (G1)
- **Option 2 fails when the texture has decorations away from its corners or a repeating pattern.** A tiled centre repeats or cuts the decorations, and the pattern breaks wherever the centre strip is not a whole number of pattern periods. (G8)
- **A background button with several frames needs the same number of frames.** The wing row is a two-frame button, striped when unselected and red when selected, and the engine switches the frame. The two frames repeat at different intervals (73 and 62 px), so no single border size tiles both. (G7)
- **Option 4, widening a patterned bitmap:** `widen_periodic` in `tools/stretch_background.py` keeps the left part, continues the inner pattern by repeating one period, and copies the border rows, edge bars and corner rivets back from the vanilla right end.
  - Find the period by comparing the texture with itself shifted by 1 to 96 columns; the shift with the smallest difference is the period.
  - Find border rows, bars and rivets by printing pixel values along a plain column and a decorated column.
- **Pillow writes a DDS the game loads:** uncompressed 32-bit, the pixel format of the vanilla interface textures. Confirmed in game. (G9)
- **Not attempted:** making a patterned bitmap taller. A1 kept the vanilla row height of 48 to avoid it. (G10)

What A2 showed (division list), confirmed in game unless noted:

- **A progress bar takes any size.** Declare a new `progressbartype` on the vanilla textures with a larger `size`; the gradient textures stretch cleanly. Vanilla draws its small bars upright with `rotation = 1.5708`; without that line the bar lies down and fills from the left. (G6, S13)
- **An icon draws a tiled sprite at the sprite's own `size`.** An `iconType` has no size of its own, so declare the `corneredTileSpriteType` at the size wanted. This widened the toolbar plate without a new image. (G3)
- **Two more ways to widen a bitmap** in `tools/stretch_background.py`:
  - `widen_spread` for a smooth gradient without a pattern: the middle columns are spread over the new width. Used for the selected row frame.
  - `widen_mirror` for an irregular texture: a plain section is inserted mirrored and then the right way round, so every join is between a column and its copy. Used for the footer plate.
- **A bitmap with several painted areas is widened area by area.** The army badge is painted with a name field, a commander box, a stats box and a plain right area. `widen_mirror_multi` puts one mirrored insert inside each area, so the art follows the layout and no single area becomes a large blank.
  - Find the edges of the areas by listing, along a few rows, the columns where the brightness jumps.
  - Each insert takes its columns from inside one area, clear of every edge.
- **Width is the first thing to be judged in game.** The first build had 90 px bars and a 96 px warnings column; both were sent back as too wide. A column gets the width its content needs and no more, and width that is saved goes back to the map, not to another column.
- **Untested: a tiled sprite replacing a plain one as a window `background`.** The footer plate is a plain sprite drawn at its own size. A tiled sprite normally takes the window's size, which here is set in code, so the plate got a widened texture instead. (G4)

What A3 showed (unit details windows), confirmed in game:

- **A row can be shared between vanilla files.** Before enlarging a row, search the vanilla `interface/` files and the window bindings report for the row's name; `stat_entry` turned two windows into four.
- **A window the code places can still be moved.** Give the window a 10x10 rectangle and put the background (with a `position`) and every widget where the window should appear. The division details window opens 505 px further right this way, clear of the army panel in each of the places the game picks for it ([Engine Facts](Engine-Facts.md) S17 to S20).
  - Do not pad the texture with a transparent strip instead: the strip swallows clicks on whatever lies under it.
  - Give children that were sized in per cent of the window an explicit size.
- **Bitmaps with painted areas grow band by band.** `grow_bands` in `tools/stretch_background.py` gives each band of rows its own column inserts, and `grow` adds rows between printed lines. Find the plain ranges of each band first: the columns without an edge in any row of the band. (G12)
  - Paper, scratched metal: many single-line copies spread over the area (`stretched`).
  - A hatch or dotted line: copies of one period (`spread` with the period).
  - A plain bar: one mirrored insert.
- **Move widgets by name, with a script.** `tools/guiedit.py` sets positions, sizes, fonts and sprites by widget path and leaves the rest of the file alone. A layout is then a short script of numbers that can be run again with other numbers.
- **States a scene cannot reach are still rendered.** A scene's `captures` and `states` can carry `hide`, `rows`, `samples` and `expand`; `render_gui.py --scene <screen> --state <name>` draws them. A sample can be a list, one text per row.
- **A text the design cuts on purpose is listed.** `knownCuts` in the scene names the widget, the text and the reason; the tests then accept it.

What A4 showed (fleet panel), confirmed in game:

- **Look for the row a card does not need.** The vanilla task force card kept a whole row for a few small counters. At 740 px the counters fit beside the mission text, the card went from 125 to 86 px, and 12 task forces fit where 8 did. The code places cards, rows and counters by the size of their entry window ([Engine Facts](Engine-Facts.md) S21), so a lower card needs no other change.
- **Two lines become a table row when the width allows it.** Name and class of a ship side by side took 248 px more width and gave four more ships on the screen, and the class column could be wider than vanilla's.
- **A sample text is not the longest text.** The class name that vanilla cuts was assumed to end where the cut began; the real one was 35 px longer, which cost a launch. Bring up the fullest state the harness can reach (`tag ENG` for a large navy) before settling a column width.
- **A bitmap can lose rows** (`cut` in `tools/stretch_background.py`): spans of one pattern period out of a mesh, or a whole painted band. (G14)
- **A window that widens pushes its neighbours.** List what opens beside the panel during the inventory: one follows a button (the composition editor), one has a file position (the home base picker), one is placed by code and needs the 10x10 treatment (the ship details window), and one is placed by code at an offset its own file gives (the ship class picker, `sub_unit_selection_window_default_pos`). (S22, S24, S38)
- **Keep a layout script absolute.** A script that adds to the current value moves the widget again on every run; write the vanilla value plus the growth.
- **A pop-up gets a scene of its own.** The composition editor, the home base picker and the transfer window each have a recipe, an `expect` list and references, apart from the panel that opens them. A window the code places is measured twice, with the mod and without it (`at`, `atVanilla`).
- **What cannot be brought up stays close to vanilla.** The template list of the composition editor never opened in a check, so it got the width its dropdown needs and kept its vanilla height.
- **Two vanilla windows can share a grid name.** `templates_grid` and `ships_grid` each exist twice; an entry pair in `tools/gui-links.json` names its window then.
- **Recipes break with the panel they click into.** When a raw recipe step clicks into a panel that is being reworked, turn it into a `clickWidget` step in the same change; three shared moves and the carrier capture of the ship details scene clicked into the fleet panel.

What the second A3 redesign showed (unit details as tables, 2026-10-16; judged by the user in their own game):

- **A list of numbers is a table, not tiles.** The stat tiles of the first redo (a 16 px label on a plate over a 20 px value, 25 of them on a grid) were judged less readable than vanilla's two aligned columns after playing with them. Stats, counts and figures go in rows of one line, label left and value right-aligned, every second row banded, a head bar per group: the look of the Records and the manager pages. Tiles stay for a handful of headline figures, never for a list.
- **A shared row is sized for every window that uses it.** `stat_entry` fills four windows, so the column width was settled by measuring every label and value of all four in the candidate font (261 px for the one long label, 130 for the next, 74 for the longest value), not the labels of the window being redesigned. The one label that does not fit is a listed cut (`knownCuts`), chosen over 80 px of extra height.
- **A window's height is shared by its tabs.** Shrinking the Stats tab from 609 to 562 px left the Template board (513 px) hanging out of the frame; the mock-ups showed one tab at a time and missed it. Before settling a new height, list the tallest content of every tab and every code-driven state (a tank division's second row of adjusters, an HQ template).
- **Banded rows for a code-filled grid are fixed plates.** The engine lays rows at the grid's slot pitch (S37), and the game fills a known number of rows per window, so one band icon per odd row behind the grid lines up with the rows. A list box that scrolls (the History rows) gets the band on the row itself instead.
- **A mock-up script saves its figures beside itself.** The second round's script reused the first round's helper, whose `save` writes into the helper's folder, and overwrote the first round's figures before the mistake was seen. A helper that is reused takes the output folder as an argument.
What A5 showed (recruit and deploy), confirmed in game:

- **Look up the sprites the code sets during the inventory.** The Manager's `Artifacts/executable/code-set-sprites.md` lists them per `.gfx` file. A widget the code puts one of them on shows it at that sprite's size, whatever the `.gui` file says: the priority rows get their background that way, which was found only after the layout had been proposed (G16). Such a widget changes size through its sprite (see "Sprites and backgrounds").
- **A two-line row becomes a one-line row by cutting its bitmap in two parts.** The template row lost its button strip: the icon box gave up rows of its plain inside, the name box rows of mesh and the strip, each part where it is plain, and the parts were joined at the frame line between them (`template_row` in `tools/stretch_background.py`).
- **What sits in a row limits how low it can get.** The priority mark of a template is a strip of 52 px with a chevron at each end; the row is 48 px for it.
- **A side panel may end above the bottom bar.** Vanilla runs the panels of a top bar tab down the whole screen, and they cover the bottom bar up to their width. A panel that reaches the army portraits (from about x 1150) gets a plain height instead ([Engine Facts](Engine-Facts.md) S28).
- **Count rows with the height that is left**, and measure the widths, before putting numbers to the user: the question named 26 templates and about 1220 px; the build has 22 and 1246.
- **One list can hold several kinds of rows.** The scene's `listRows` is then the sequence of row windows, and the renderer stacks them as the game does (S27).

What A6, A7 and A8 showed (army overview, air wing reorganisation, theatre boxes), confirmed in game:

- **List what slides in beside a side panel.** A side panel of a top bar tab is drawn above the windows that open beside it ([Engine Facts](Engine-Facts.md) S32): Equipment Details and Sunk Ships opened at x 540 under the 900 px overview and could not be seen. Search the vanilla files for `show_position` and `position` near the panel's old width (540 for a 550 panel) and move those windows with it.
- **A grid without `format` centres its column** (S31). Grow such a list and its slot by the same amount and the entries stay where they were; the scene places the grid, since the renderer does not centre.
- **Several grids of one name in one window are told apart by their container**: `army_units/item_grid` in `tools/gui-links.json`, a scene's `listRows`, `rows` and `place`.
- **A container's margin can go into its children** (S33): with the margin at 0 and every child moved by it, the file says where each widget is and the renderer agrees with the game.
- **Boxes that a window stacks at their own x grow to the left** (S34): the right edge stays where vanilla has it, and alerts placed from the right edge move by the growth.
- **Measure names before choosing a column**: `names_divisions` holds 27 485 division names, 99 % of them 291 px or less in `hoi_18mbs`. The check with the user's playset still found a longer name than the samples (an air wing of 258 px), so a phase is checked with the playset before it closes.
- **When the mod overrides a window another mod of the playset changes**, take over that mod's values where they also read better in vanilla (the gaps between theatre shields, from RBM's GFX Overhaul), and leave alone the windows that need nothing (the window holding the theatre boxes, which RBM moves).

## Recipe for a screen phase

Who does each step, what is handed from one to the next and where the user decides is in [Workflow](Workflow.md): the designer does steps 1 and 2, the builder 3 to 6, the game checker 7, the orchestrator 8 and the reviews between them. The steps themselves are here.

1. **Inventory** (designer).
   - Start from the vanilla screen at 2560x1440: `reference/vanilla/<screen>.jpg` is the whole frame and `<screen>-panel.png` the panel at 1:1 without loss (index in `reference/README.md`). A screen that is not there yet needs a recipe first ([Game Recipes](Game-Recipes.md)), then `tools/Invoke-GameCheck.ps1 <screen> -Vanilla -SaveReference`. Ask the user for a screenshot only for a state a 1936 start cannot show.
   - `tools/Show-GuiOutline.ps1 <file.gui>` lists the windows; add a window name and `-All` for its widgets, fonts and sprites.
   - Note which backgrounds are bitmaps, which sizes are "set in code", which widths come from a grid, which window really holds each list (see "How the engine treats sizes and containers"), and which `positionType` entries of the windows the code reads (the Manager's `Artifacts/executable/position-types.md`, S38).
   - Look the screen's `.gfx` files up in the Manager's `Artifacts/executable/code-set-sprites.md`: the code sets those sprites itself, and the widget they land on takes the sprite's size.
   - List what the vanilla screen crams or hides: values stacked on one spot, text that is cut off, things reached only through a click or a tooltip, and buttons without a hotkey.
   - Look each window up in the Manager's window bindings report (`Artifacts/executable/window-bindings-1440p*.md`): which widgets the code fills and how it finds them (see "What a redesign can add").
2. **Layout proposal** (designer; the orchestrator reviews it and the user approves it, [Workflow](Workflow.md) stages 3 and 4). Start from what the player should see at once on this screen, then give target sizes, row heights and font choices as a short text mock-up, agreed before any file is written. The numbers go into `scratch/phases/<id>/layout.json` ([Workflow](Workflow.md), "Handoff files"; the pieces in [Design Language](Design-Language.md)), and the mock-up is drawn from that file: `python -I tools/mockup.py <layout> --out <png> --crop <box>` on the reference capture, with a short script only for what the code draws. The builder applies the same file, so every number is written once.
   - Cover every panel that is on screen together, not only the ones being resized: say where each panel's visible edges end up and whether each gap between panels stays or closes.
   - Name each addition (a column, a caption, a hotkey) and the row of the table in "What a redesign can add" that makes it possible.
   - Where width or empty space is a matter of judgement, add a mock-up composed from the screenshot: draw the widened background and paste the screenshot's own widgets at their new positions. In A2 the badge was agreed on a mock-up and needed one game check; the division list was agreed on a table of numbers and needed four.
   - **Design page first** (user, 2026-10-16). Before any override file is written, the proposal goes on one page that the user reviews: each screen's vanilla capture beside its mock-up at the same scale, what changes and why, and what is still open. The user marks it up, the mock-ups are redrawn, and only an agreed design is built. After the build, the page gets the renders of the mod's files, so the user can compare design and build before the game check. C1, C2, A9 and step 2 of A5 went this way in two rounds of feedback without touching the game.
     - Mock-ups are composed at 1:1 with `tools/mockup.py` from the layout file: the game's own sprites and fonts through the renderer, the plates of the card style, pieces of the reference captures for what the code draws (pictures, portraits, values), widened bitmaps from `tools/stretch_background.py`. A script that adds what the code draws stays under `scratch/phases/<id>/`.
     - `python -I tools/make_design_page.py <id>` makes the page from the handoff files, with one composite image per figure group. An agent that can publish one (Claude Code's Artifact tool) publishes `scratch/phases/<id>/design.html` and gives the user the link; otherwise the user opens the file.
     - Every claim on the page is one the inventory backs: the window bindings, the sprites the code sets, the playset's mods that change the same file. What only the game can show is listed as open, not promised.
3. **Baseline and starting file** (builder). `tools/New-OverrideFile.ps1 <screen> <file.gui> <window> [<window> ...]` exports the missing baselines and creates `interface/zz_1440p_<screen>.gui` with untouched vanilla copies of the windows. Run it again to add windows later; it never overwrites existing content.
4. **Background** (builder). Only for bitmap backgrounds: work down the four options, judge them in previews, declare the sprite.
5. **Build** (builder). `python -I tools/apply_layout.py scratch/phases/<id>/layout.json` first: it moves the vanilla widgets, inserts the plates and captions as `mod1440_*` icons after the background, declares their sprites and writes the samples into the scene; a number that has to change is changed in the layout and applied again. Then edit what the layout cannot say; leave names alone, and add containers only as `mod1440_*` cards around vanilla widgets. Add each list and its row window to `tools/gui-links.json`. Then run `tools/Compare-Baseline.ps1 zz_1440p_<screen>.gui` (`-Group` for one line per widget) and read every changed value before the game check.
6. **Static checks and render** (builder; the orchestrator reviews the baseline diff and the renders, [Workflow](Workflow.md) stage 6). `build.ps1 -Check <screen>` runs the validation, the whole test suite and the scene render, and prints which texts fit their boxes. Look at `scratch/previews/<screen>_crop.png` (and `--bounds` for widget outlines, `--expand <dropdown>` for an opened dropdown) and fix what the render shows. No game check is requested before the render has been looked at.
7. **Game check** (game checker, after the user granted the launches; the orchestrator reads the captures too). Vanilla playset with only this mod, at 2560x1440. The game re-reads no interface file while it runs ([Engine Facts](Engine-Facts.md) H3, H4), so each check is a fresh start, and `tools/Invoke-GameCheck.ps1 <screen>` does it without a human in about two minutes: launch, a new 1936 game as Germany, the scene's `setup` clicks, a capture and a 2x crop in `scratch/checks/`, the `error.log` diff, exit. Read the crop; the human judges only what a crop cannot settle (tooltips, click targets, states a 1936 start does not show, and whether a width is too much).
   - Give the tester one numbered list per launch that covers everything changed: every list scrolled to the end, every dropdown opened, both states of selectable rows, tooltips and click targets, and every state of the screen (for example with and without a group selected).
   - Screenshots taken with F11 land in `Documents\Paradox Interactive\Hearts of Iron IV\Screenshots\hoi4_<n>.png` at full resolution. Crop the panel and enlarge it 2x to inspect it and to measure edges. (H6)
   - `Documents\Paradox Interactive\Hearts of Iron IV\logs\error.log` is rewritten on every launch. A run without the mod already logs about 50 lines on 1.19.3 (DLC, equipment icon and entity messages). Search it for the mod's file names, window names and `GFX_1440p`. (H9)
8. **Close** (orchestrator, after the user's own test). Store the finished screen with `tools/Invoke-GameCheck.ps1 <screen> -SaveReference` (it goes to `reference/mod/`, beside the vanilla frame). Fill the game-check log in `wiki/phases/<screen>.md`, move the [Engine Facts](Engine-Facts.md) rows the checks confirmed, update the status in [Roadmap](Roadmap.md), the README and the Workshop description; raise `version` in `descriptor.mod`.
