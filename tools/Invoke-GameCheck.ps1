<#
.SYNOPSIS
    Runs a game check of one or more screens without a human: restart, new game, recipe, capture, crop.

.DESCRIPTION
    The game re-reads no .gui, .gfx or texture file while it runs (wiki/Engine-Facts.md, H3 and H4), so a
    check of changed files always starts the game afresh. This script:

      1. writes an only-this-mod playset (the old one is backed up and restored at the end),
      2. starts hoi4.exe -debug and clicks through the menu into a new 1936 game as Germany, paused,
      3. for each scene: returns to the clean state, runs the scene's "setup" recipe (wiki/Game-Recipes.md),
         captures the screen, cuts out the scene's "crop" region at 2x and looks for the scene's "expect"
         widgets in the capture, which proves that the recipe brought the screen up,
      4. diffs error.log against baseline/error.log.vanilla,
      5. stops the game.

    It takes the main screen and the mouse for about a minute and a half plus ten seconds per scene. Output
    lands in scratch/checks/. Read the crop PNGs afterwards; this script only produces them.

.EXAMPLE
    .\tools\Invoke-GameCheck.ps1 army_selection
    One screen, from a cold start to a stopped game.

.EXAMPLE
    .\tools\Invoke-GameCheck.ps1 army_selection, air_selection
    Two screens in one launch.

.EXAMPLE
    .\tools\Invoke-GameCheck.ps1 -All -Vanilla -SaveReference
    Every scene of tools/scenes without the mod, stored for good under reference\vanilla: the captures a
    redesign is planned on, and the frame render_gui.py --over composes a proposal on. Run it after a game
    update; git then shows which screens changed.

.EXAMPLE
    .\tools\Invoke-GameCheck.ps1 army_selection -SaveReference
    The screen with the mod, stored under reference\mod: the state a finished phase leaves behind.

.EXAMPLE
    .\tools\Invoke-GameCheck.ps1 army_selection -KeepRunning
    Leaves the game open afterwards, for a human to try tooltips and clicks, or for tools\Invoke-GameSteps.ps1.
    The playset stays switched until Stop-Hoi4 or Restore-HoiPlayset (tools/GameHarness.ps1) is run.

.EXAMPLE
    .\tools\Invoke-GameCheck.ps1 army_readiness -WithScreens
    The page beside the HOI4 1440p UI Mod (the reworked vanilla screens), this mod last: how the two look together.

.EXAMPLE
    .\tools\Invoke-GameCheck.ps1 probe_portraits -Mods mod/rt56-vnr-utt-standalone-v16.mod -AfterLoad tools\playsets\rt56.json -TimeoutSec 900
    The scene with other mods of the launcher loaded before this one (their files under Documents\...\mod), this
    mod last. -AfterLoad closes what those mods open when a game starts (wiki/Game-Recipes.md).

.EXAMPLE
    .\tools\Invoke-GameCheck.ps1 air_selection -NoRestart
    Uses the game as it is running now: reset, recipe, capture and crop only. For a second look at files
    that did not change since the game started.
#>
[CmdletBinding()]
param(
    [Parameter(Position = 0, ValueFromRemainingArguments)][string[]]$Scene,
    [switch]$All,
    [switch]$NoRestart,
    [switch]$KeepRunning,
    [switch]$Vanilla,
    [switch]$WithScreens,
    [switch]$SaveReference,
    [switch]$F11,
    [string[]]$Mods,
    [string]$AfterLoad,
    [int]$TimeoutSec = 300
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'GameHarness.ps1')

# Accept "a, b" (PowerShell), "a b" and "a,b" (other shells) alike.
$Scene = @($Scene | ForEach-Object { $_ -split '[,\s]+' } | Where-Object { $_ })
if ($All) { $Scene = @(Get-ChildItem -Path (Join-Path $PSScriptRoot 'scenes') -Filter '*.json' | Sort-Object Name | ForEach-Object { $_.BaseName }) }
if (-not $Scene.Count) { throw 'Name one or more scenes (tools\scenes\<name>.json), or pass -All.' }
$scenes = @($Scene | ForEach-Object { Get-GuiScene -Name $_ })
# All scenes share one game. A scene marked "changesState" leaves something behind that other screens show
# (an air group badge above the wing list), so it runs after the others.
$scenes = @($scenes | Where-Object { -not $_.changesState }) + @($scenes | Where-Object { $_.changesState })
$watch = [System.Diagnostics.Stopwatch]::StartNew()

Write-Host "`n==> Game check: $(($scenes | ForEach-Object { $_.screen }) -join ', ')" -ForegroundColor Cyan

$results = [System.Collections.Generic.List[object]]::new()
try {
    if (-not $NoRestart) {
        if (Get-Hoi4Process) {
            Write-Host '  [INFO] the game is running; it is restarted because it does not re-read changed files' -ForegroundColor Gray
            Stop-Hoi4 -KeepPlayset
            Start-Sleep -Seconds 3
        }
        if ($Vanilla) { Set-HoiPlayset -Vanilla | Out-Null }
        elseif ($WithScreens -or $Mods) {
            # -Mods: launcher files of other mods (mod/<name>.mod), loaded before this one
            $others = @($Mods | ForEach-Object { $_ -split '[,\s]+' } | Where-Object { $_ })
            foreach ($other in $others) {
                if (-not (Test-Path -LiteralPath (Join-Path (Get-HoiPaths).UserDir $other))) { throw "-Mods: the launcher has no $other." }
            }
            if ($WithScreens) {
                # the HOI4 1440p UI Mod (the reworked vanilla screens) beside this one, this mod last; its launcher
                # file exists once build.ps1 -DevLink has run in that repository
                $screensMod = 'mod/hoi4-1440p-ui-mod.mod'
                if (-not (Test-Path -LiteralPath (Join-Path (Get-HoiPaths).UserDir $screensMod))) { throw "-WithScreens: the launcher has no $screensMod. Run build.ps1 -DevLink in the hoi4-1440p-ui-mod repository first." }
                $others += $screensMod
            }
            Set-HoiPlayset -Mods (@($others) + @($script:HarnessModFile)) | Out-Null
        }
        else { Set-HoiPlayset -OnlyThisMod | Out-Null }
        $closing = $null
        if ($AfterLoad) {
            # steps as JSON or a file of them, as tools\Invoke-GameSteps.ps1 -AfterLoad takes them
            if (Test-Path -LiteralPath $AfterLoad) { $AfterLoad = [System.IO.File]::ReadAllText((Resolve-Path -LiteralPath $AfterLoad), [System.Text.Encoding]::UTF8) }
            $closing = @($AfterLoad | ConvertFrom-Json | ForEach-Object { $_ })
        }
        Start-Hoi4 -TimeoutSec $TimeoutSec | Out-Null
        Start-HoiNewGame -TimeoutSec ([Math]::Max(180, $TimeoutSec)) -AfterLoad $closing
        Write-Host ("  [INFO] in the game after {0:0} s" -f $watch.Elapsed.TotalSeconds) -ForegroundColor Gray
    } elseif (-not (Get-Hoi4Process)) {
        throw 'The game is not running. Leave out -NoRestart to start it.'
    }

    $kind = 'mod'
    if ($Vanilla) { $kind = 'vanilla' }
    $first = $true
    foreach ($sceneData in $scenes) {
        Write-Host "`n==> Scene $($sceneData.screen)" -ForegroundColor Cyan
        $label = $sceneData.screen
        if ($Vanilla) { $label = "$label-vanilla" }
        Set-HoiHarnessContext -Scene $sceneData.screen -Vanilla:$Vanilla
        # every recipe starts from the clean state; a new game is already in it
        if (-not $first -or $NoRestart) { Reset-HoiState | Out-Null }
        $first = $false

        $result = [pscustomobject]@{ Scene = $label; Screenshot = $null; Crop = $null; Verified = $null; Problem = $null }
        try {
            Invoke-HoiSteps -Steps $sceneData.setup -Scene $sceneData.screen
            $result.Screenshot = Save-HoiScreenshot -Name $label -F11:$F11
            if ($result.Screenshot) {
                $result.Crop = Export-HoiPanelCrop -Scene $sceneData.Path -Image $result.Screenshot
                if (@($sceneData.expect).Count) {
                    $found = @(Test-HoiCapture -Scene $sceneData.screen -Image $result.Screenshot)
                    $result.Verified = (@($found | Where-Object { -not $_.Found }).Count -eq 0)
                    if (-not $result.Verified) { $result.Problem = 'expected widgets are not visible' }
                }
                # keep it for good only when the screen verifiably came up, or has no expect list to say otherwise
                if ($SaveReference -and -not $result.Problem) { Save-HoiReference -SceneData $sceneData -Image $result.Screenshot -Kind $kind | Out-Null }
            }
        } catch {
            $result.Problem = $_.Exception.Message
            Write-Host "  [ERROR] $($sceneData.screen): $($result.Problem)" -ForegroundColor Red
        }
        $results.Add($result)

        # extra captures of the same scene: an opened dropdown, another tab ...
        foreach ($extra in @($sceneData.captures)) {
            if ($null -eq $extra -or $result.Problem) { continue }
            $extraResult = [pscustomobject]@{ Scene = "$label-$($extra.name)"; Screenshot = $null; Crop = $null; Verified = $null; Problem = $null }
            try {
                Invoke-HoiSteps -Steps $extra.steps -Scene $sceneData.screen
                $extraResult.Screenshot = Save-HoiScreenshot -Name $extraResult.Scene -F11:$F11
                if ($extraResult.Screenshot) {
                    $extraResult.Crop = Export-HoiPanelCrop -Scene $sceneData.Path -Image $extraResult.Screenshot
                    if ($SaveReference) { Save-HoiReference -SceneData $sceneData -Image $extraResult.Screenshot -Kind $kind -Capture $extra.name | Out-Null }
                }
            } catch {
                $extraResult.Problem = $_.Exception.Message
                Write-Host "  [ERROR] $($extraResult.Scene): $($extraResult.Problem)" -ForegroundColor Red
            }
            $results.Add($extraResult)
        }

        # steps that undo what the scene changed for good (a switch to another country), so later scenes start clean
        if ($sceneData.teardown) {
            try { Invoke-HoiSteps -Steps $sceneData.teardown -Scene $sceneData.screen }
            catch { Write-Host "  [WARN] $($sceneData.screen): teardown failed: $($_.Exception.Message)" -ForegroundColor Yellow }
        }
    }

    if ($SaveReference) { Update-HoiReferenceIndex }

    Write-Host "`n==> error.log" -ForegroundColor Cyan
    Compare-HoiErrorLog | Out-Null
} finally {
    if (-not $KeepRunning -and -not $NoRestart) { Stop-Hoi4 }
    elseif ($KeepRunning) { Write-Host '  [INFO] the game stays open; run Stop-Hoi4 (tools\GameHarness.ps1) to close it and restore the playset' -ForegroundColor Yellow }
}

if ($scenes.Count -le 3) {
    foreach ($sceneData in $scenes) {
        if ($sceneData.manual -or $sceneData.checklist) { Write-Host "`n==> Left for a human on $($sceneData.screen)" -ForegroundColor Cyan }
        foreach ($item in @($sceneData.manual)) { if ($item) { Write-Host "  - $item" } }
        $i = 0
        foreach ($item in @($sceneData.checklist)) { if ($item) { $i++; Write-Host "  $i. $item" } }
    }
}

Write-Host ("`n==> Files to read ({0:0} s in all)" -f $watch.Elapsed.TotalSeconds) -ForegroundColor Cyan
foreach ($result in $results) {
    $state = if ($result.Problem) { "PROBLEM: $($result.Problem)" } elseif ($result.Verified) { 'verified' } elseif ($null -eq $result.Verified) { 'not verified (no expect list)' } else { '' }
    $color = if ($result.Problem) { 'Red' } else { 'Gray' }
    Write-Host ("  {0,-34} {1}" -f $result.Scene, $result.Crop)
    Write-Host ("  {0,-34} {1}" -f '', $state) -ForegroundColor $color
}
$problems = @($results | Where-Object { $_.Problem })
if ($problems.Count) { Write-Host "`n$($problems.Count) scene(s) with a problem: the recipe or the layout needs a look (wiki/Game-Recipes.md)." -ForegroundColor Red }
return $results
