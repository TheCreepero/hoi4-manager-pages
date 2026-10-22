# Reference captures

One capture of every screen the mod works on or plans to, taken by `tools/Invoke-GameCheck.ps1 -SaveReference` at 2560x1440 in a paused 1936 game as Germany. Use them to plan a redesign, to compare before and after, and to see what a game update changed.

- `vanilla/` is the game without the mod. `mod/` is the screen as the mod last left it, for the screens it has reworked.
- `<screen>.jpg` is the whole frame, compressed: what is beside the panel and where it could grow.
- `<screen>-panel.png` is the panel region at 1:1 without loss: read text and measure edges here, never in the JPEG.
- The menu screens the harness clicks through (`reference/harness/`) stay in the 1440p UI mod; the click positions are in `tools/GameHarness.ps1`.
- Split from the HOI4 1440p UI Mod on 2026-10-21: the frames the page scenes draw over (`vanilla/`), the same screens with that mod and the pages themselves (`mod/`).
- `manifest.csv` records the game version and date of each capture. This file is rewritten from it; do not edit it by hand.

How each screen is brought up is in [wiki/Game-Recipes.md](../wiki/Game-Recipes.md). To refresh, for example after a game update:

```powershell
.\tools\Invoke-GameCheck.ps1 -All -Vanilla -SaveReference        # every screen without the mod, about six minutes
.\tools\Invoke-GameCheck.ps1 army_readiness -SaveReference        # one page with the mod, when its phase closes
```

`python -I tools\render_gui.py --scene <screen> --over` draws a proposal on top of the vanilla frame.

## Vanilla

| Phase | Screen | Frame | Panel | Game | Date |
|---|---|---|---|---|---|
| A5 | recruit_deploy | [recruit_deploy.jpg](vanilla/recruit_deploy.jpg) | [recruit_deploy-panel.png](vanilla/recruit_deploy-panel.png) | 1.19.3.0 | 2026-10-11 |
| A8 | theatre_bar | [theatre_bar.jpg](vanilla/theatre_bar.jpg) | [theatre_bar-panel.png](vanilla/theatre_bar-panel.png) | 1.19.3.0 | 2026-10-14 |
| C | construction | [construction.jpg](vanilla/construction.jpg) | [construction-panel.png](vanilla/construction-panel.png) | 1.19.3.0 | 2026-10-08 |
| C | politics | [politics.jpg](vanilla/politics.jpg) | [politics-panel.png](vanilla/politics-panel.png) | 1.19.3.0 | 2026-10-08 |

## With the mod

| Phase | Screen | Frame | Panel | Game | Mod | Date |
|---|---|---|---|---|---|---|
| A5 | recruit_deploy | [recruit_deploy.jpg](mod/recruit_deploy.jpg) | [recruit_deploy-panel.png](mod/recruit_deploy-panel.png) | 1.19.3.0 | 1.4 | 2026-10-12 |
| A8 | theatre_bar | [theatre_bar.jpg](mod/theatre_bar.jpg) | [theatre_bar-panel.png](mod/theatre_bar-panel.png) | 1.19.3.0 | 1.6 | 2026-10-14 |
| D2 | army_readiness | [army_readiness.jpg](mod/army_readiness.jpg) | [army_readiness-panel.png](mod/army_readiness-panel.png) | 1.19.3.0 | 1.6 | 2026-10-13 |
| D3 | states | [states.jpg](mod/states.jpg) | [states-panel.png](mod/states-panel.png) | 1.19.3.0 | 1.6 | 2026-10-13 |
| D4 | national_figures | [national_figures.jpg](mod/national_figures.jpg) | [national_figures-panel.png](mod/national_figures-panel.png) | 1.19.3.0 | 1.6 | 2026-10-13 |
| D5 | history | [history.jpg](mod/history.jpg) | [history-panel.png](mod/history-panel.png) | 1.19.3.0 | 1.6 | 2026-10-13 |
| E1 | war_diary | [war_diary.jpg](mod/war_diary.jpg) | [war_diary-panel.png](mod/war_diary-panel.png) | 1.19.3.0 | 1.6 | 2026-10-13 |
| E2 | officers | [officers.jpg](mod/officers.jpg) | [officers-panel.png](mod/officers-panel.png) | 1.19.3.0 | 1.6 | 2026-10-13 |
| E3 | government | [government.jpg](mod/government.jpg) | [government-panel.png](mod/government-panel.png) | 1.19.3.0 | 1.6 | 2026-10-13 |
| E4 | wars | [wars.jpg](mod/wars.jpg) | [wars-panel.png](mod/wars-panel.png) | 1.19.3.0 | 1.6 | 2026-10-13 |
