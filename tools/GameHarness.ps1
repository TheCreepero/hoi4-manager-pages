# Drives the game for a check: playset, launch, the menu clicks into a new 1936 game, the recipe steps that
# bring a screen up, console commands by simulated keystrokes, screen captures, panel crops and the error
# log. Dot-source this file; it only defines functions. Keep it ASCII and Windows PowerShell 5.1 compatible.
# The engine facts it relies on are the H rows of wiki/Engine-Facts.md; the short version: the game re-reads
# no .gui, .gfx or texture file while it runs, so every change needs a restart, and a restart takes about a
# minute and a half without a human.
#
# This script only captures the screen to PNG files under scratch/checks. Turning a capture into the
# compressed frames of reference/ is done by tools/save_reference.py on purpose: a PowerShell script that
# both grabs the screen and encodes it as JPEG matches an antivirus signature for screenshot stealers
# (Windows Defender removed this file once for that reason). Do not add image encoding here.

. (Join-Path $PSScriptRoot 'GuiParsing.ps1')

$script:HarnessRepoRoot = Split-Path -Parent $PSScriptRoot
$script:HarnessModFile = 'mod/hoi4-manager-pages.mod'
$script:HarnessScratch = Join-Path (Join-Path $script:HarnessRepoRoot 'scratch') 'harness'
$script:HarnessChecks = Join-Path (Join-Path $script:HarnessRepoRoot 'scratch') 'checks'
# Scan codes (set 1) the game reads regardless of keyboard layout: the key left of 1 opens the console.
$script:ScanConsole = 0x29
$script:ScanEnter = 0x1C
$script:ScanF11 = 0x57
$script:ScanEscape = 0x01
$script:ScanShift = 0x2A

# Where to click to get from the main menu into a new 1936 game as Germany, measured on a 2560x1440
# fullscreen game (game 1.19.3). Each entry: what it is, x, y, seconds to wait afterwards. The menu screens
# are kept in reference/harness/ for the day a game update moves a button.
$script:NewGameClicks = @(
    @{ Name = 'Single Player';     X = 1280; Y = 470;  Wait = 3 }
    @{ Name = 'New Game';          X = 1280; Y = 600;  Wait = 10 }
    @{ Name = '1 January 1936';    X = 1147; Y = 620;  Wait = 1 }
    @{ Name = 'Select Scenario';   X = 1427; Y = 937;  Wait = 6 }
    @{ Name = 'German Reich';      X = 1357; Y = 512;  Wait = 1 }   # 5th portrait since 2026-10-22 (France, UK, Japan, USA, Germany, Italy, USSR); 1507 is Italy now
    @{ Name = 'Select Country';    X = 1363; Y = 1056; Wait = 8 }
    @{ Name = 'Start';             X = 2417; Y = 1399; Wait = 0 }
)
# Where the cursor rests for a capture: over the map, clear of the panels, the screen edges and the tooltips.
$script:CursorPark = @(1500, 1000)

function Get-HoiPaths {
    param([string]$GameDir)

    $game = Resolve-HoiGameDir -GameDir $GameDir
    $user = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Paradox Interactive\Hearts of Iron IV'
    return [pscustomobject]@{
        GameDir        = $game
        Exe            = if ($game) { Join-Path $game 'hoi4.exe' } else { $null }
        UserDir        = $user
        DlcLoad        = Join-Path $user 'dlc_load.json'
        Logs           = Join-Path $user 'logs'
        ErrorLog       = Join-Path (Join-Path $user 'logs') 'error.log'
        GameLog        = Join-Path (Join-Path $user 'logs') 'game.log'
        Screenshots    = Join-Path $user 'Screenshots'
        ConsoleHistory = if ($game) { Join-Path $game 'console_history.txt' } else { $null }
        ModFile        = Join-Path $user $script:HarnessModFile
    }
}

# ---------------------------------------------------------------- playset

# Backs up dlc_load.json once and writes a playset with only this mod (or none, with -Vanilla; the mods of
# -Mods; with -UserPlayset the launcher's own playset as it is, this mod last). The DevLink .mod file must exist.
function Set-HoiPlayset {
    param([switch]$OnlyThisMod, [switch]$Vanilla, [switch]$UserPlayset, [string[]]$Mods)

    $paths = Get-HoiPaths
    if (-not (Test-Path -LiteralPath $paths.ModFile)) { throw "Launcher mod file not found: $($paths.ModFile). Run build.ps1 -DevLink first." }
    if (-not $Vanilla -and -not $Mods) {
        # The launcher file names the folder the game loads. After build.ps1 -Deploy that is a copy in
        # Documents, and a check would then show that copy instead of the working tree, without any error.
        $modText = [System.IO.File]::ReadAllText($paths.ModFile, [System.Text.Encoding]::UTF8)
        $loaded = $null
        if ($modText -match '(?m)^\s*path\s*=\s*"([^"]+)"') { $loaded = $Matches[1] }
        $normalise = { param($p) ([string]$p).Replace('\', '/').TrimEnd('/').ToLowerInvariant() }
        if ((& $normalise $loaded) -ne (& $normalise $script:HarnessRepoRoot)) {
            throw "The launcher mod file points to '$loaded', not to this repository ($script:HarnessRepoRoot): the game would load that copy and none of the changes here. Run build.ps1 -DevLink first."
        }
    }
    if (-not (Test-Path -LiteralPath $script:HarnessScratch)) { New-Item -ItemType Directory -Path $script:HarnessScratch -Force | Out-Null }
    $backup = Join-Path $script:HarnessScratch 'dlc_load.backup.json'
    $disabled = @()
    if ($UserPlayset -and -not (Test-Path -LiteralPath $paths.DlcLoad)) { throw "No dlc_load.json: the launcher has no playset to start with." }
    if (Test-Path -LiteralPath $paths.DlcLoad) {
        $current = [System.IO.File]::ReadAllText($paths.DlcLoad, [System.Text.Encoding]::UTF8)
        if (-not (Test-Path -LiteralPath $backup)) { [System.IO.File]::WriteAllText($backup, $current, [System.Text.UTF8Encoding]::new($false)) }
        try { $disabled = @(($current | ConvertFrom-Json).disabled_dlcs) } catch { $disabled = @() }
    }
    $enabled = @($script:HarnessModFile)
    if ($Mods) { $enabled = @($Mods) }
    if ($UserPlayset) {
        # the user's playset is the backup when an earlier call has already put a playset of the harness in place
        $own = [System.IO.File]::ReadAllText($backup, [System.Text.Encoding]::UTF8)
        $others = @(@(($own | ConvertFrom-Json).enabled_mods) | Where-Object { $_ -and $_ -ne $script:HarnessModFile })
        $enabled = @($others) + @($script:HarnessModFile)
        Write-Host "  [INFO] the launcher's playset: $($others.Count) mods, then this mod" -ForegroundColor Gray
    }
    if ($Vanilla) { $enabled = @() }
    # ConvertTo-Json turns an empty array inside a hashtable into null on PowerShell 5.1, so build the list by hand
    $modList = (@($enabled) | ForEach-Object { '"' + $_ + '"' }) -join ','
    $dlcList = (@($disabled) | Where-Object { $_ } | ForEach-Object { '"' + $_ + '"' }) -join ','
    $json = '{"enabled_mods":[' + $modList + '],"disabled_dlcs":[' + $dlcList + ']}'
    [System.IO.File]::WriteAllText($paths.DlcLoad, $json, [System.Text.UTF8Encoding]::new($false))
    Write-Host "  [OK] dlc_load.json: $json" -ForegroundColor Green
    return $backup
}

function Restore-HoiPlayset {
    $paths = Get-HoiPaths
    $backup = Join-Path $script:HarnessScratch 'dlc_load.backup.json'
    if (-not (Test-Path -LiteralPath $backup)) { Write-Host '  [INFO] no playset backup to restore'; return }
    Copy-Item -LiteralPath $backup -Destination $paths.DlcLoad -Force
    Remove-Item -LiteralPath $backup -Force
    Write-Host '  [OK] dlc_load.json restored' -ForegroundColor Green
}

# ---------------------------------------------------------------- process

function Get-Hoi4Process {
    return (Get-Process -Name 'hoi4' -ErrorAction SilentlyContinue | Select-Object -First 1)
}

# Starts hoi4.exe straight from the game folder (no launcher) with the debug console enabled.
function Start-Hoi4 {
    param([switch]$Windowed, [string[]]$ExtraArgs, [int]$TimeoutSec = 300, [switch]$NoWait)

    $paths = Get-HoiPaths
    if (-not $paths.Exe -or -not (Test-Path -LiteralPath $paths.Exe)) { throw 'hoi4.exe not found. Pass -GameDir to Get-HoiPaths or set HOI4_GAME_DIR.' }
    if (Get-Hoi4Process) { throw 'The game is already running.' }
    $arguments = @('-debug', '-gdpr-compliant')
    if ($Windowed) { $arguments += '-windowed' }
    if ($ExtraArgs) { $arguments += $ExtraArgs }
    $started = Get-Date
    $process = Start-Process -FilePath $paths.Exe -ArgumentList $arguments -WorkingDirectory $paths.GameDir -PassThru
    Write-Host "  [OK] started hoi4.exe $($arguments -join ' ') (pid $($process.Id))" -ForegroundColor Green
    if ($NoWait) { return $process }
    # game.log is rewritten per launch; "Resetting game" is its line for "the main menu is loading"
    $line = Wait-HoiLog -Path $paths.GameLog -Pattern 'Resetting game' -Since $started -TimeoutSec $TimeoutSec
    if (-not $line) { throw 'The game did not reach the main menu.' }
    Start-Sleep -Seconds 12   # the menu needs this long after the log line before it takes clicks
    return $process
}

# How many lines of a log match a pattern (0 when the file is missing or older than $Since).
function Get-HoiLogCount {
    param([Parameter(Mandatory)][string]$Path, [Parameter(Mandatory)][string]$Pattern, [datetime]$Since = [datetime]::MinValue)

    if (-not (Test-Path -LiteralPath $Path)) { return 0 }
    if ($Since -gt [datetime]::MinValue.AddDays(1) -and (Get-Item -LiteralPath $Path).LastWriteTime -lt $Since.AddSeconds(-2)) { return 0 }
    return @(Read-HoiSharedLines -Path $Path | Where-Object { $_ -match $Pattern }).Count
}

# Waits until a log holds more than $MoreThan lines that match $Pattern. Returns the newest one, or $null on
# a timeout. Pass the count taken before the action, so an older line of the same session does not match.
function Wait-HoiLog {
    param([Parameter(Mandatory)][string]$Path, [Parameter(Mandatory)][string]$Pattern, [datetime]$Since = [datetime]::MinValue, [int]$MoreThan = 0, [int]$TimeoutSec = 300)

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if ((Get-HoiLogCount -Path $Path -Pattern $Pattern -Since $Since) -gt $MoreThan) {
            return (Read-HoiSharedLines -Path $Path | Where-Object { $_ -match $Pattern } | Select-Object -Last 1)
        }
        Start-Sleep -Seconds 2
    }
    Write-Host "  [WARN] timed out after $TimeoutSec s waiting for '$Pattern' in $Path" -ForegroundColor Yellow
    return $null
}

# From the main menu into a new 1936 game as Germany, by clicks, and on into the clean state every recipe
# starts from. The game starts paused and is never unpaused or saved. Throws, with a capture in
# scratch/checks, when the map does not load.
function Start-HoiNewGame {
    # AfterLoad: steps for what a playset opens when the game starts (a welcome event, a splash window): they run
    # once the map is up and before the clean state is made.
    param([int]$TimeoutSec = 180, $AfterLoad)

    $paths = Get-HoiPaths
    $bounds = Get-HoiScreenBounds
    if ($bounds.Width -ne 2560 -or $bounds.Height -ne 1440) { Write-Host "  [WARN] the primary screen is $($bounds.Width)x$($bounds.Height); the menu clicks were measured at 2560x1440" -ForegroundColor Yellow }
    $before = Get-HoiLogCount -Path $paths.GameLog -Pattern 'End RestoreDeviceObjects'
    foreach ($step in $script:NewGameClicks) {
        Send-HoiClick -X $step.X -Y $step.Y
        if ($step.Wait) { Start-Sleep -Seconds $step.Wait }
    }
    $line = Wait-HoiLog -Path $paths.GameLog -Pattern 'End RestoreDeviceObjects' -MoreThan $before -TimeoutSec $TimeoutSec
    if (-not $line) {
        $shot = Save-HoiScreenshot -Name 'new-game-failed'
        throw "The new game did not load. Look at $shot to see where the menu clicks ended up (the menu screens as they should look are in reference\harness)."
    }
    Start-Sleep -Seconds 6   # the map fades in after the log line
    Hide-HoiErrorLogWindows | Out-Null   # the game has just opened error.log in Notepad, if the load logged errors
    if ($AfterLoad) {
        Start-Sleep -Seconds 3   # the window that was minimised gives the screen back; the game needs a moment to be in front again
        Invoke-HoiSteps -Steps $AfterLoad
    }
    Reset-HoiState | Out-Null   # nothing open, land map mode, Home camera
    # once per game: what every recipe may rely on (all divisions in Army 1), then back to the clean state
    $moves = Get-HoiMoves
    if ($moves.ContainsKey('prepare_game')) {
        Invoke-HoiSteps -Steps $moves['prepare_game'].steps
        Reset-HoiState | Out-Null
    }
    Write-Host '  [OK] new 1936 game as Germany, paused, in the clean state' -ForegroundColor Green
}

# ---------------------------------------------------------------- recipes
#
# A recipe is a list of steps. Each step is an object with one of:
#   key: "u" | "shift+q" | "escape" | "home" ...   a hotkey; the most durable way to open a screen
#   clickWidget: "window/widget" or "window/widget#n"   a click on a widget found by name: the renderer
#                works out where it sits (tools/render_gui.py --locate), so the step survives layout
#                changes and works for the vanilla and the modded window alike. The window is the one
#                that defines the widget (the row window for a widget of a row); #n is the n-th drawn
#                instance. Optional: scene (whose layout to use, default the current scene), state (one
#                of that scene's captures or states, for a widget that shows only then),
#                offset [dx, dy], button "right".
#   dragWidget: ["window/widget", "window/widget"]   press on the first widget, release on the second, both
#                found by name like clickWidget (same optional scene): a drag and drop inside a panel
#   move: "<name>"            the steps of a shared move from tools/moves.json
#   click: [x, y]             a raw screen position; only for the map, whose Home camera never changes
#   rightClick: [x, y]        drag: [x1, y1, x2, y2] (box selection)
#   console: "<command>"      typed into the console
# and optionally wait: <seconds> after it. The method for finding a recipe is in wiki/Game-Recipes.md.

$script:HarnessVanilla = $false
$script:HarnessScene = $null
$script:HarnessLocateCache = @{}
$script:HarnessMoves = $null

# Which scene's layout clickWidget uses by default, and whether the game runs without the mod (the
# widgets then sit where the vanilla files put them).
function Set-HoiHarnessContext {
    param([string]$Scene, [switch]$Vanilla)
    $script:HarnessScene = $Scene
    $script:HarnessVanilla = [bool]$Vanilla
}

$script:NamedKeys = @{
    'escape' = @(0x01, $false); 'esc' = @(0x01, $false); 'enter' = @(0x1C, $false); 'return' = @(0x1C, $false)
    'tab' = @(0x0F, $false); 'space' = @(0x39, $false); 'backspace' = @(0x0E, $false)
    'delete' = @(0x53, $true); 'del' = @(0x53, $true); 'home' = @(0x47, $true); 'end' = @(0x4F, $true)
    'pageup' = @(0x49, $true); 'pagedown' = @(0x51, $true)
    'up' = @(0x48, $true); 'down' = @(0x50, $true); 'left' = @(0x4B, $true); 'right' = @(0x4D, $true)
    'f1' = @(0x3B, $false); 'f2' = @(0x3C, $false); 'f3' = @(0x3D, $false); 'f4' = @(0x3E, $false); 'f5' = @(0x3F, $false)
    'f6' = @(0x40, $false); 'f7' = @(0x41, $false); 'f8' = @(0x42, $false); 'f9' = @(0x43, $false); 'f10' = @(0x44, $false)
    'f11' = @(0x57, $false); 'f12' = @(0x58, $false)
    'ctrl' = @(0x1D, $false); 'shift' = @(0x2A, $false); 'alt' = @(0x38, $false)
}

# Presses a key or a combination such as "u", "shift+q", "ctrl+b" or "escape". Everything before the last
# part is held while the last part is pressed. Letters and digits follow the active keyboard layout.
function Send-HoiKey {
    param([Parameter(Mandatory)][string]$Key, [int]$HoldMs = 50)

    Initialize-HoiInput
    if (-not (Test-HoiForeground)) { Set-HoiForeground | Out-Null }
    $codes = @()
    foreach ($part in ($Key.ToLowerInvariant() -split '\+')) {
        if (-not $part) { continue }
        if ($script:NamedKeys.ContainsKey($part)) { $codes += , $script:NamedKeys[$part]; continue }
        if ($part.Length -ne 1) { throw "Unknown key '$part' in '$Key'." }
        $vk = [HoiInput]::VkKeyScan([char]$part)
        if ($vk -eq -1) { throw "The key '$part' is not on this keyboard layout." }
        $codes += , @([int][HoiInput]::MapVirtualKey([uint32]($vk -band 0xFF), 0), $false)
    }
    if (-not $codes.Count) { return }
    foreach ($code in $codes) { [HoiInput]::Key([uint16]$code[0], $false, [bool]$code[1]); Start-Sleep -Milliseconds $HoldMs }
    for ($i = $codes.Count - 1; $i -ge 0; $i--) { [HoiInput]::Key([uint16]$codes[$i][0], $true, [bool]$codes[$i][1]); Start-Sleep -Milliseconds 20 }
    Start-Sleep -Milliseconds 150
}

# The shared moves of tools/moves.json: name -> steps.
function Get-HoiMoves {
    if ($null -eq $script:HarnessMoves) {
        $path = Join-Path $PSScriptRoot 'moves.json'
        $script:HarnessMoves = @{}
        if (Test-Path -LiteralPath $path) {
            $json = [System.IO.File]::ReadAllText($path, [System.Text.Encoding]::UTF8) | ConvertFrom-Json
            foreach ($prop in $json.moves.PSObject.Properties) { $script:HarnessMoves[$prop.Name] = $prop.Value }
        }
    }
    return $script:HarnessMoves
}

# Where a named widget sits on the screen: its centre, from the renderer's layout of a scene.
function Resolve-HoiWidget {
    param([Parameter(Mandatory)][string]$Spec, [string]$Scene = $script:HarnessScene, [string]$State)

    if (-not $Scene) { throw "clickWidget '$Spec' needs a scene: the scene says where its window sits on the screen." }
    $key = "$Scene|$State|$($script:HarnessVanilla)|$Spec"
    if (-not $script:HarnessLocateCache.ContainsKey($key)) {
        $python = (Get-Command python -ErrorAction SilentlyContinue).Source
        if (-not $python) { throw 'clickWidget needs Python with Pillow (tools/render_gui.py does the layout).' }
        $arguments = @('-I', (Join-Path $PSScriptRoot 'render_gui.py'), '--scene', $Scene, '--locate', $Spec)
        if ($script:HarnessVanilla) { $arguments += '--vanilla' }
        if ($State) { $arguments += '--state'; $arguments += $State }
        $line = @(& $python @arguments 2>$null | Where-Object { $_ -like "LOCATE`t*" })[0]
        $fields = @([string]$line -split "`t")
        if ($fields.Count -lt 4 -or $fields[2] -eq 'NOTFOUND') { throw "Widget '$Spec' is not in the layout of scene '$Scene'. Check the window and widget names with tools\Show-GuiOutline.ps1, and that the scene lists the window." }
        $script:HarnessLocateCache[$key] = @([int]$fields[2], [int]$fields[3])
    }
    return $script:HarnessLocateCache[$key]
}

# Runs recipe steps (see the list above). -Scene is the scene whose layout clickWidget uses by default.
function Invoke-HoiSteps {
    param($Steps, [string]$Scene = $script:HarnessScene, [int]$Depth = 0)

    if ($Depth -gt 8) { throw 'Moves are nested more than 8 deep; one of them probably includes itself.' }
    foreach ($step in @($Steps)) {
        if ($null -eq $step) { continue }
        if ($step -is [array]) {   # ConvertFrom-Json hands a JSON array over as one object on PowerShell 5.1
            Invoke-HoiSteps -Steps $step -Scene $Scene -Depth $Depth
            continue
        }
        if ($step.move) {
            $moves = Get-HoiMoves
            if (-not $moves.ContainsKey([string]$step.move)) { throw "Unknown move '$($step.move)'. The moves are in tools\moves.json." }
            Invoke-HoiSteps -Steps $moves[[string]$step.move].steps -Scene $Scene -Depth ($Depth + 1)
        }
        elseif ($step.clickWidget) {
            $stepScene = if ($step.scene) { [string]$step.scene } else { $Scene }
            $at = Resolve-HoiWidget -Spec ([string]$step.clickWidget) -Scene $stepScene -State ([string]$step.state)
            $x = $at[0]; $y = $at[1]
            if ($step.offset) { $x += [int]$step.offset[0]; $y += [int]$step.offset[1] }
            Send-HoiClick -X $x -Y $y -Right:($step.button -eq 'right')
        }
        elseif ($step.dragWidget) {
            $stepScene = if ($step.scene) { [string]$step.scene } else { $Scene }
            $from = Resolve-HoiWidget -Spec ([string]$step.dragWidget[0]) -Scene $stepScene
            $to = Resolve-HoiWidget -Spec ([string]$step.dragWidget[1]) -Scene $stepScene
            Send-HoiDrag -X1 $from[0] -Y1 $from[1] -X2 $to[0] -Y2 $to[1]
        }
        elseif ($step.key) { Send-HoiKey -Key ([string]$step.key) }
        elseif ($step.click) { Send-HoiClick -X ([int]$step.click[0]) -Y ([int]$step.click[1]) }
        elseif ($step.rightClick) { Send-HoiClick -X ([int]$step.rightClick[0]) -Y ([int]$step.rightClick[1]) -Right }
        elseif ($step.drag) { Send-HoiDrag -X1 ([int]$step.drag[0]) -Y1 ([int]$step.drag[1]) -X2 ([int]$step.drag[2]) -Y2 ([int]$step.drag[3]) }
        elseif ($step.console) { Send-HoiConsole -Command ([string]$step.console) | Out-Null }
        if ($step.wait) { Start-Sleep -Milliseconds ([int](1000 * [double]$step.wait)) }
    }
}

# Looks for a scene's "expect" widgets in a capture (tools/render_gui.py --verify): did the screen come up,
# and how far from the layout does the game draw each widget? Returns objects with Spec, Found, Dx, Dy, Score.
function Test-HoiCapture {
    param([Parameter(Mandatory)][string]$Scene, [Parameter(Mandatory)][string]$Image, [string[]]$Expect)

    $python = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $python) { Write-Host '  [WARN] no Python: the capture is not verified' -ForegroundColor Yellow; return @() }
    $arguments = @('-I', (Join-Path $PSScriptRoot 'render_gui.py'), '--scene', $Scene, '--verify', $Image)
    if ($script:HarnessVanilla) { $arguments += '--vanilla' }
    if ($Expect) { $arguments += '--expect'; $arguments += $Expect }
    $results = @()
    foreach ($line in @(& $python @arguments 2>$null | Where-Object { $_ -like "VERIFY`t*" })) {
        $fields = @([string]$line -split "`t")
        if ($fields[2] -eq 'SKIPPED') { continue }
        $result = [pscustomobject]@{ Spec = $fields[1]; Found = ($fields[2] -eq 'FOUND'); Dx = [int]$fields[3]; Dy = [int]$fields[4]; Score = [double]::Parse($fields[5], [System.Globalization.CultureInfo]::InvariantCulture) }
        $results += $result
        if ($result.Found) {
            $where = if ($result.Dx -or $result.Dy) { "found $($result.Dx),$($result.Dy) px from the layout" } else { 'found where the layout puts it' }
            Write-Host "  [OK] $($result.Spec): $where" -ForegroundColor Green
        } else {
            Write-Host "  [ERROR] $($result.Spec): not visible in the capture (best match $($result.Score)). The recipe did not bring the screen up, or the layout is off." -ForegroundColor Red
        }
    }
    return $results
}

# Mean brightness (0-255) of the left part of the top bar. Nothing ever covers it, and the game dims the
# whole screen while its Escape menu is open, so a drop here means "the menu just opened".
function Get-HoiTopBarBrightness {
    Add-Type -AssemblyName System.Drawing
    $bitmap = New-Object System.Drawing.Bitmap 700, 48
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $bounds = Get-HoiScreenBounds
    $graphics.CopyFromScreen($bounds.X, $bounds.Y, 0, 0, $bitmap.Size)
    $sum = 0; $count = 0
    for ($y = 2; $y -lt 48; $y += 4) {
        for ($x = 2; $x -lt 700; $x += 4) {
            $pixel = $bitmap.GetPixel($x, $y)
            $sum += $pixel.R + $pixel.G + $pixel.B
            $count += 3
        }
    }
    $graphics.Dispose(); $bitmap.Dispose()
    return [double]$sum / $count
}

# Back to the clean state from anywhere in a running game: Escape closes one window or selection at a time
# and, when nothing is left, opens the game menu, which one more Escape closes. F1 restores the land map
# mode and Home puts the camera on the capital at a fixed zoom. That view, not the one a new game opens
# with, is where every map position of a recipe is measured, because it can be restored at any time.
function Reset-HoiState {
    param([int]$MaxPresses = 12)

    Set-HoiForeground | Out-Null
    $clean = $false
    for ($i = 0; $i -lt $MaxPresses; $i++) {
        $before = Get-HoiTopBarBrightness
        Send-HoiScan -Scan $script:ScanEscape
        Start-Sleep -Milliseconds 550
        $after = Get-HoiTopBarBrightness
        if ($after -lt $before * 0.8) {
            Send-HoiScan -Scan $script:ScanEscape   # the menu opened: nothing else was open; close it again
            Start-Sleep -Milliseconds 550
            $clean = $true
            break
        }
    }
    if (-not $clean) { Write-Host "  [WARN] reset: the game menu did not show after $MaxPresses Escape presses; the state is unknown" -ForegroundColor Yellow }
    Send-HoiKey -Key 'f1'     # land map mode: the bottom bar shows armies again after a navy or air screen
    Start-Sleep -Milliseconds 400
    Send-HoiKey -Key 'home'
    Start-Sleep -Milliseconds 900
    [HoiInput]::SetCursorPos($script:CursorPark[0], $script:CursorPark[1]) | Out-Null
    return $clean
}

function Stop-Hoi4 {
    param([switch]$KeepPlayset)

    $process = Get-Hoi4Process
    if ($process) {
        Stop-Process -Id $process.Id -Force
        Write-Host '  [OK] hoi4.exe stopped' -ForegroundColor Green
    }
    if (-not $KeepPlayset) { Restore-HoiPlayset }
}

# ---------------------------------------------------------------- input

function Initialize-HoiInput {
    if ('HoiInput' -as [type]) { return }
    Add-Type -Namespace '' -Name 'HoiInput' -MemberDefinition @'
[StructLayout(LayoutKind.Sequential)]
public struct KEYBDINPUT { public ushort wVk; public ushort wScan; public uint dwFlags; public uint time; public IntPtr dwExtraInfo; }
[StructLayout(LayoutKind.Sequential)]
public struct MOUSEINPUT { public int dx; public int dy; public uint mouseData; public uint dwFlags; public uint time; public IntPtr dwExtraInfo; }
[StructLayout(LayoutKind.Explicit)]
public struct INPUTUNION { [FieldOffset(0)] public MOUSEINPUT mi; [FieldOffset(0)] public KEYBDINPUT ki; }
[StructLayout(LayoutKind.Sequential)]
public struct INPUT { public uint type; public INPUTUNION u; }
[DllImport("user32.dll", SetLastError = true)] public static extern uint SendInput(uint nInputs, INPUT[] pInputs, int cbSize);
[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
[DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
[DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, IntPtr lpdwProcessId);
[DllImport("user32.dll")] public static extern bool AttachThreadInput(uint idAttach, uint idAttachTo, bool fAttach);
[DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
[DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
[DllImport("user32.dll")] public static extern short VkKeyScan(char ch);
[DllImport("user32.dll")] public static extern uint MapVirtualKey(uint uCode, uint uMapType);
[DllImport("kernel32.dll")] public static extern uint GetCurrentThreadId();
[StructLayout(LayoutKind.Sequential)]
public struct POINT { public int X; public int Y; }
[DllImport("user32.dll")] public static extern IntPtr WindowFromPoint(POINT point);
[DllImport("user32.dll")] public static extern IntPtr GetAncestor(IntPtr hWnd, uint flags);
[DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder text, int count);
public static IntPtr RootAt(int x, int y) { POINT p; p.X = x; p.Y = y; return GetAncestor(WindowFromPoint(p), 2); }
public static string TitleOf(IntPtr hWnd) { System.Text.StringBuilder text = new System.Text.StringBuilder(200); GetWindowText(hWnd, text, 200); return text.ToString(); }
public const uint INPUT_KEYBOARD = 1;
public const uint INPUT_MOUSE = 0;
public const uint KEYEVENTF_SCANCODE = 0x0008;
public const uint KEYEVENTF_KEYUP = 0x0002;
public const uint KEYEVENTF_EXTENDEDKEY = 0x0001;
public const uint MOUSEEVENTF_MOVE = 0x0001;
public const uint MOUSEEVENTF_LEFTDOWN = 0x0002;
public const uint MOUSEEVENTF_LEFTUP = 0x0004;
public const uint MOUSEEVENTF_RIGHTDOWN = 0x0008;
public const uint MOUSEEVENTF_RIGHTUP = 0x0010;
public static void Key(ushort scan, bool up, bool extended) {
    INPUT[] inputs = new INPUT[1];
    inputs[0].type = INPUT_KEYBOARD;
    inputs[0].u.ki.wScan = scan;
    inputs[0].u.ki.dwFlags = KEYEVENTF_SCANCODE | (up ? KEYEVENTF_KEYUP : 0) | (extended ? KEYEVENTF_EXTENDEDKEY : 0);
    SendInput(1, inputs, Marshal.SizeOf(typeof(INPUT)));
}
public static void Mouse(uint flags) {
    INPUT[] inputs = new INPUT[1];
    inputs[0].type = INPUT_MOUSE;
    inputs[0].u.mi.dwFlags = flags;
    SendInput(1, inputs, Marshal.SizeOf(typeof(INPUT)));
}
'@
}

function Test-HoiForeground {
    Initialize-HoiInput
    $process = Get-Hoi4Process
    if (-not $process -or $process.MainWindowHandle -eq [IntPtr]::Zero) { return $false }
    return ([HoiInput]::GetForegroundWindow() -eq $process.MainWindowHandle)
}

# Brings the game window to the front. Windows only lets the foreground thread hand over the foreground,
# so the calling thread is attached to it for the switch. Throws when the game does not come to the front:
# keys sent then would land in another window.
function Set-HoiForeground {
    Initialize-HoiInput
    $process = Get-Hoi4Process
    if (-not $process) { throw 'The game is not running.' }
    $handle = $process.MainWindowHandle
    if ($handle -eq [IntPtr]::Zero) { throw 'The game has no main window yet.' }
    if ([HoiInput]::GetForegroundWindow() -eq $handle) { return $handle }
    $current = [HoiInput]::GetCurrentThreadId()
    for ($attempt = 0; $attempt -lt 6; $attempt++) {
        $foreground = [HoiInput]::GetForegroundWindow()
        $owner = [HoiInput]::GetWindowThreadProcessId($foreground, [IntPtr]::Zero)
        $target = [HoiInput]::GetWindowThreadProcessId($handle, [IntPtr]::Zero)
        if ($owner -ne 0) { [HoiInput]::AttachThreadInput($current, $owner, $true) | Out-Null }
        [HoiInput]::AttachThreadInput($current, $target, $true) | Out-Null
        [HoiInput]::ShowWindow($handle, 9) | Out-Null   # SW_RESTORE
        [HoiInput]::SetForegroundWindow($handle) | Out-Null
        [HoiInput]::AttachThreadInput($current, $target, $false) | Out-Null
        if ($owner -ne 0) { [HoiInput]::AttachThreadInput($current, $owner, $false) | Out-Null }
        Start-Sleep -Milliseconds 700   # a fullscreen game needs a moment to take the screen back
        if ([HoiInput]::GetForegroundWindow() -eq $handle) { return $handle }
    }
    throw 'The game window did not come to the front; no keys were sent.'
}

# In debug mode the game starts Notepad with error.log when a new game has loaded with errors in the log
# (wiki/Engine-Facts.md, H27), and that window can land in front of the game: clicks then go to Notepad.
# Minimises every window that shows error.log. Nothing is closed.
function Hide-HoiErrorLogWindows {
    Initialize-HoiInput
    $hidden = 0
    foreach ($process in @(Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne [IntPtr]::Zero -and $_.MainWindowTitle -like 'error.log*' })) {
        [HoiInput]::ShowWindow($process.MainWindowHandle, 6) | Out-Null   # SW_MINIMIZE
        $hidden++
    }
    if ($hidden) {
        Write-Host "  [INFO] minimised $hidden window(s) showing error.log: the game opens that file itself in debug mode" -ForegroundColor Gray
        Start-Sleep -Milliseconds 600
    }
    return $hidden
}

# Throws unless the game window is what a click at this screen position would reach. A click is sent by
# position, so it lands in whatever window is on top there, whichever window has the keyboard.
function Assert-HoiPointIsGame {
    param([Parameter(Mandatory)][int]$X, [Parameter(Mandatory)][int]$Y)
    Initialize-HoiInput
    $process = Get-Hoi4Process
    if (-not $process) { throw 'The game is not running.' }
    $root = [IntPtr]::Zero
    for ($attempt = 0; $attempt -lt 2; $attempt++) {
        $root = [HoiInput]::RootAt($X, $Y)
        if ($root -eq $process.MainWindowHandle) { return }
        if ($attempt -eq 0) {
            Hide-HoiErrorLogWindows | Out-Null
            Set-HoiForeground | Out-Null
        }
    }
    throw "Another window ('$([HoiInput]::TitleOf($root))') covers the game at $X,$Y; nothing was sent there."
}

function Send-HoiScan {
    param([Parameter(Mandatory)][int]$Scan, [int]$HoldMs = 40, [switch]$Extended)
    Initialize-HoiInput
    if (-not (Test-HoiForeground)) { Set-HoiForeground | Out-Null }
    [HoiInput]::Key([uint16]$Scan, $false, [bool]$Extended)
    Start-Sleep -Milliseconds $HoldMs
    [HoiInput]::Key([uint16]$Scan, $true, [bool]$Extended)
    Start-Sleep -Milliseconds $HoldMs
}

# Types text with the current keyboard layout: each character becomes its virtual key, then its scan code.
function Send-HoiText {
    param([Parameter(Mandatory)][string]$Text, [int]$DelayMs = 25)
    Initialize-HoiInput
    if (-not (Test-HoiForeground)) { Set-HoiForeground | Out-Null }
    foreach ($ch in $Text.ToCharArray()) {
        $vk = [HoiInput]::VkKeyScan($ch)
        if ($vk -eq -1) { Write-Host "  [WARN] cannot type '$ch' on this layout" -ForegroundColor Yellow; continue }
        $code = $vk -band 0xFF
        $shift = (($vk -shr 8) -band 1) -eq 1
        $scan = [HoiInput]::MapVirtualKey([uint32]$code, 0)
        if ($shift) { [HoiInput]::Key([uint16]$script:ScanShift, $false, $false) }
        [HoiInput]::Key([uint16]$scan, $false, $false)
        Start-Sleep -Milliseconds $DelayMs
        [HoiInput]::Key([uint16]$scan, $true, $false)
        if ($shift) { [HoiInput]::Key([uint16]$script:ScanShift, $true, $false) }
        Start-Sleep -Milliseconds $DelayMs
    }
}

# Opens the console, types a command, presses Enter and closes the console again. Returns whether the game
# ran the command.
function Send-HoiConsole {
    param([Parameter(Mandatory)][string]$Command, [int]$ConsoleScan = $script:ScanConsole, [int]$SettleMs = 400, [switch]$LeaveOpen)

    Set-HoiForeground | Out-Null
    $history = (Get-HoiPaths).ConsoleHistory
    Send-HoiScan -Scan $ConsoleScan
    Start-Sleep -Milliseconds $SettleMs
    Send-HoiText -Text $Command
    Send-HoiScan -Scan $script:ScanEnter
    Start-Sleep -Milliseconds $SettleMs
    if (-not $LeaveOpen) { Send-HoiScan -Scan $ConsoleScan }
    Start-Sleep -Milliseconds $SettleMs

    # The game rewrites console_history.txt after every command it runs. If the command is not its last
    # line, the console was already open when this started: the keys went to the game as hotkeys.
    $arrived = $false
    if ($history -and (Test-Path -LiteralPath $history)) {
        $last = Read-HoiSharedLines -Path $history | Where-Object { $_ } | Select-Object -Last 1
        $arrived = ($last -eq $Command)
    }
    if ($arrived) { Write-Host "  [OK] console: $Command" -ForegroundColor Green }
    else { Write-Host "  [WARN] console: '$Command' is not in console_history.txt; the console was probably open already, so the keys acted as hotkeys" -ForegroundColor Yellow }
    return $arrived
}

# Box selection: press at one corner, move in steps, release at the other.
function Send-HoiDrag {
    param([Parameter(Mandatory)][int]$X1, [Parameter(Mandatory)][int]$Y1, [Parameter(Mandatory)][int]$X2, [Parameter(Mandatory)][int]$Y2, [int]$SettleMs = 400)
    Initialize-HoiInput
    Set-HoiForeground | Out-Null
    Assert-HoiPointIsGame -X $X1 -Y $Y1
    Assert-HoiPointIsGame -X $X2 -Y $Y2
    [HoiInput]::SetCursorPos($X1, $Y1) | Out-Null
    Start-Sleep -Milliseconds 120
    [HoiInput]::Mouse([HoiInput]::MOUSEEVENTF_LEFTDOWN)
    for ($i = 1; $i -le 12; $i++) {
        [HoiInput]::SetCursorPos([int]($X1 + ($X2 - $X1) * $i / 12), [int]($Y1 + ($Y2 - $Y1) * $i / 12)) | Out-Null
        [HoiInput]::Mouse([HoiInput]::MOUSEEVENTF_MOVE)
        Start-Sleep -Milliseconds 25
    }
    Start-Sleep -Milliseconds 80
    [HoiInput]::Mouse([HoiInput]::MOUSEEVENTF_LEFTUP)
    Start-Sleep -Milliseconds $SettleMs
}

function Send-HoiClick {
    param([Parameter(Mandatory)][int]$X, [Parameter(Mandatory)][int]$Y, [switch]$Right, [int]$SettleMs = 300)
    Initialize-HoiInput
    Set-HoiForeground | Out-Null
    Assert-HoiPointIsGame -X $X -Y $Y
    [HoiInput]::SetCursorPos($X, $Y) | Out-Null
    Start-Sleep -Milliseconds 100
    if ($Right) { [HoiInput]::Mouse([HoiInput]::MOUSEEVENTF_RIGHTDOWN); Start-Sleep -Milliseconds 60; [HoiInput]::Mouse([HoiInput]::MOUSEEVENTF_RIGHTUP) }
    else { [HoiInput]::Mouse([HoiInput]::MOUSEEVENTF_LEFTDOWN); Start-Sleep -Milliseconds 60; [HoiInput]::Mouse([HoiInput]::MOUSEEVENTF_LEFTUP) }
    Start-Sleep -Milliseconds $SettleMs
}

# ---------------------------------------------------------------- captures

function Get-HoiScreenBounds {
    Add-Type -AssemblyName System.Windows.Forms
    return [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
}

# Copies the primary screen while the game is in front and saves it as PNG under
# scratch/checks/<Name>-<time>.png. This works in fullscreen, in the menus as well as in the game. -F11 uses
# the game's own screenshot key instead, which only works in a running game and leaves a file in the user's
# Screenshots folder. -Desktop is accepted for older calls and means the default.
function Save-HoiScreenshot {
    param([string]$Name = 'check', [int]$TimeoutSec = 15, [switch]$F11, [switch]$Desktop, [switch]$KeepCursor)

    if (-not (Test-Path -LiteralPath $script:HarnessChecks)) { New-Item -ItemType Directory -Path $script:HarnessChecks -Force | Out-Null }
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $target = Join-Path $script:HarnessChecks "$Name-$stamp.png"

    if (-not $F11) {
        Add-Type -AssemblyName System.Drawing
        Set-HoiForeground | Out-Null   # throws when the game is not in front: no capture of another window
        # having the keyboard is not enough: another window can still lie on top of the game
        foreach ($point in @(@(640, 400), @(1920, 400), @(1280, 1000))) { Assert-HoiPointIsGame -X $point[0] -Y $point[1] }
        if (-not $KeepCursor) {
            [HoiInput]::SetCursorPos($script:CursorPark[0], $script:CursorPark[1]) | Out-Null
            Start-Sleep -Milliseconds 400
        }
        $bounds = Get-HoiScreenBounds
        $bitmap = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        $graphics.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
        $bitmap.Save($target, [System.Drawing.Imaging.ImageFormat]::Png)
        $graphics.Dispose(); $bitmap.Dispose()
        Write-Host "  [OK] capture: $target" -ForegroundColor Green
        return $target
    }

    $paths = Get-HoiPaths
    $before = @{}
    if (Test-Path -LiteralPath $paths.Screenshots) {
        foreach ($f in (Get-ChildItem -LiteralPath $paths.Screenshots -Filter 'hoi4_*.png')) { $before[$f.Name] = $true }
    }
    Set-HoiForeground | Out-Null
    Send-HoiScan -Scan $script:ScanF11
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Milliseconds 500
        $new = @(Get-ChildItem -LiteralPath $paths.Screenshots -Filter 'hoi4_*.png' -ErrorAction SilentlyContinue | Where-Object { -not $before.ContainsKey($_.Name) })
        if ($new.Count) {
            $file = $new | Sort-Object LastWriteTime | Select-Object -Last 1
            Start-Sleep -Milliseconds 800   # let the game finish writing
            Copy-Item -LiteralPath $file.FullName -Destination $target -Force
            Write-Host "  [OK] screenshot: $target (from $($file.Name))" -ForegroundColor Green
            return $target
        }
    }
    Write-Host "  [WARN] no new screenshot appeared in $($paths.Screenshots) within $TimeoutSec s" -ForegroundColor Yellow
    return $null
}

# Captures the screen and writes a region of it enlarged, with a grid labelled in screen coordinates, so a
# click position can be read off exactly. The way to find a raw position for a recipe step.
function Save-HoiGridCapture {
    param([string]$Name = 'grid', [int[]]$Region = @(0, 0, 1280, 720), [int]$Scale = 2, [int]$Step = 50, [switch]$KeepCursor)

    Add-Type -AssemblyName System.Drawing
    $shot = Save-HoiScreenshot -Name $Name -KeepCursor:$KeepCursor
    $source = [System.Drawing.Image]::FromFile($shot)
    $x = [Math]::Max(0, $Region[0]); $y = [Math]::Max(0, $Region[1])
    $w = [Math]::Min($Region[2], $source.Width - $x); $h = [Math]::Min($Region[3], $source.Height - $y)
    $bitmap = New-Object System.Drawing.Bitmap ($w * $Scale), ($h * $Scale)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::NearestNeighbor
    $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::Half
    $graphics.DrawImage($source, (New-Object System.Drawing.Rectangle 0, 0, ($w * $Scale), ($h * $Scale)), (New-Object System.Drawing.Rectangle $x, $y, $w, $h), [System.Drawing.GraphicsUnit]::Pixel)
    $pen = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(110, 255, 255, 0)), 1
    $font = New-Object System.Drawing.Font 'Consolas', 9
    $brush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 255, 255, 0))
    $shade = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(170, 0, 0, 0))
    for ($gx = [Math]::Ceiling($x / $Step) * $Step; $gx -lt ($x + $w); $gx += $Step) {
        $px = ($gx - $x) * $Scale
        $graphics.DrawLine($pen, $px, 0, $px, $h * $Scale)
        $graphics.FillRectangle($shade, $px + 1, 0, 34, 13)
        $graphics.DrawString([string]$gx, $font, $brush, $px + 1, 0)
    }
    for ($gy = [Math]::Ceiling($y / $Step) * $Step; $gy -lt ($y + $h); $gy += $Step) {
        $py = ($gy - $y) * $Scale
        $graphics.DrawLine($pen, 0, $py, $w * $Scale, $py)
        $graphics.FillRectangle($shade, 0, $py + 1, 34, 13)
        $graphics.DrawString([string]$gy, $font, $brush, 0, $py + 1)
    }
    $target = [System.IO.Path]::ChangeExtension($shot, $null).TrimEnd('.') + '-grid.png'
    $bitmap.Save($target, [System.Drawing.Imaging.ImageFormat]::Png)
    $pen.Dispose(); $font.Dispose(); $brush.Dispose(); $shade.Dispose(); $graphics.Dispose(); $bitmap.Dispose(); $source.Dispose()
    Write-Host "  [OK] grid: $target (screen $x,$y ${w}x$h at ${Scale}x, lines every $Step px)" -ForegroundColor Green
    return $target
}

# Cuts the scene's crop rectangle out of a capture and writes it enlarged next to it.
function Export-HoiPanelCrop {
    param([Parameter(Mandatory)][string]$Scene, [Parameter(Mandatory)][string]$Image, [int]$Scale = 2, [int[]]$Crop)

    Add-Type -AssemblyName System.Drawing
    if (-not $Crop) {
        $sceneData = Get-GuiScene -Name $Scene
        $Crop = @($sceneData.crop)
    }
    if ($Crop.Count -ne 4) { throw 'Crop must be x, y, width, height.' }
    $source = [System.Drawing.Image]::FromFile($Image)
    $x = [Math]::Max(0, $Crop[0]); $y = [Math]::Max(0, $Crop[1])
    $w = [Math]::Min($Crop[2], $source.Width - $x); $h = [Math]::Min($Crop[3], $source.Height - $y)
    $bitmap = New-Object System.Drawing.Bitmap ($w * $Scale), ($h * $Scale)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::NearestNeighbor
    $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::Half
    $graphics.DrawImage($source, (New-Object System.Drawing.Rectangle 0, 0, ($w * $Scale), ($h * $Scale)), (New-Object System.Drawing.Rectangle $x, $y, $w, $h), [System.Drawing.GraphicsUnit]::Pixel)
    $target = [System.IO.Path]::ChangeExtension($Image, $null).TrimEnd('.') + '-crop.png'
    $bitmap.Save($target, [System.Drawing.Imaging.ImageFormat]::Png)
    $graphics.Dispose(); $bitmap.Dispose(); $source.Dispose()
    Write-Host "  [OK] crop: $target ($w x $h at ${Scale}x)" -ForegroundColor Green
    return $target
}

# ---------------------------------------------------------------- reference archive
#
# reference/ keeps one capture per screen for planning and for comparing later. The files are written by
# tools/save_reference.py from a PNG this script captured (see the note at the top of this file).

# Stores a capture under reference/<Kind>/ and records it in reference/manifest.csv. Returns $true on success.
function Save-HoiReference {
    param([Parameter(Mandatory)]$SceneData, [Parameter(Mandatory)][string]$Image, [Parameter(Mandatory)][ValidateSet('vanilla', 'mod')][string]$Kind, [string]$Capture = '')

    $python = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $python) { Write-Host '  [WARN] no Python: the capture is not stored under reference' -ForegroundColor Yellow; return $false }
    $arguments = @('-I', (Join-Path $PSScriptRoot 'save_reference.py'), '--scene', $SceneData.screen, '--image', $Image, '--kind', $Kind)
    if ($Capture) { $arguments += '--capture'; $arguments += $Capture }
    $output = @(& $python @arguments 2>&1)
    if ($LASTEXITCODE -ne 0) { Write-Host "  [WARN] reference not stored: $($output -join ' ')" -ForegroundColor Yellow; return $false }
    Write-Host "  [OK] $($output -join ' ')" -ForegroundColor Green
    return $true
}

# Rewrites reference/README.md from the manifest.
function Update-HoiReferenceIndex {
    $python = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $python) { return }
    $output = @(& $python -I (Join-Path $PSScriptRoot 'save_reference.py') --index 2>&1)
    Write-Host "  [OK] $($output -join ' ')" -ForegroundColor Green
}

# ---------------------------------------------------------------- error log

# Lines of a file the game holds open for writing (error.log, game.log, console_history.txt).
function Read-HoiSharedLines {
    param([Parameter(Mandatory)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return @() }
    $stream = New-Object System.IO.FileStream($Path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
    try {
        $reader = New-Object System.IO.StreamReader($stream)
        $text = $reader.ReadToEnd()
        $reader.Dispose()
    } finally { $stream.Dispose() }
    return @($text -split "`r?`n")
}

function Get-HoiErrorLines {
    param([Parameter(Mandatory)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return @() }
    return @(Read-HoiSharedLines -Path $Path | ForEach-Object { $_ -replace '^\[\d\d:\d\d:\d\d\]', '' } | Where-Object { $_.Trim() })
}

# Saves the current error.log (timestamps stripped) as the vanilla baseline. Run after a launch without the mod.
function Save-HoiErrorLogBaseline {
    param([string]$Target = (Join-Path (Join-Path $script:HarnessRepoRoot 'baseline') 'error.log.vanilla'))
    $paths = Get-HoiPaths
    $lines = Get-HoiErrorLines -Path $paths.ErrorLog
    [System.IO.File]::WriteAllText($Target, (($lines -join "`n") + "`n"), [System.Text.UTF8Encoding]::new($false))
    Write-Host "  [OK] $($lines.Count) baseline lines -> $Target" -ForegroundColor Green
}

# Lines of error.log that a vanilla launch does not produce; the ones that name the mod come first.
function Compare-HoiErrorLog {
    param([string]$Baseline = (Join-Path (Join-Path $script:HarnessRepoRoot 'baseline') 'error.log.vanilla'))

    $paths = Get-HoiPaths
    $current = Get-HoiErrorLines -Path $paths.ErrorLog
    $known = @{}
    if (Test-Path -LiteralPath $Baseline) {
        foreach ($line in (Get-HoiErrorLines -Path $Baseline)) { $known[$line] = $true }
    } else {
        Write-Host "  [WARN] no baseline at $Baseline (Save-HoiErrorLogBaseline after a vanilla launch); showing the whole log" -ForegroundColor Yellow
    }
    $windowNames = @()
    $spriteNames = @{}
    foreach ($file in @(Get-ChildItem -Path (Join-Path $script:HarnessRepoRoot 'interface') -Recurse -File -Filter '*.gui')) {
        $text = Read-GuiText -Path $file.FullName
        foreach ($w in @(Get-GuiTopLevelWindows -Root (ConvertFrom-GuiText -Text $text))) { $windowNames += $w.Name }
        foreach ($m in [regex]::Matches($text, '"(GFX_[A-Za-z0-9_\-]+)"')) { $spriteNames[$m.Groups[1].Value] = $true }
    }
    # mod1440_ is the prefix of the mod's script files under common/ and of its scripted GUI windows
    $pattern = '(zz_1440p|GFX_1440p|1440p_ui|mod1440_|' + (($windowNames | ForEach-Object { [regex]::Escape($_) }) -join '|') + ')'
    $new = @($current | Where-Object { -not $known.ContainsKey($_) })
    # A sprite the mod's windows name and the loaded game does not have gives a line that names neither the mod
    # nor a file. That happens next to a mod whose copy of a game .gfx file lacks the sprite (Engine Facts L10).
    $isMods = {
        param($line)
        if ($line -match $pattern) { return $true }
        if ($line -match 'Could not find sprite type \[([^\]]+)\]' -and $spriteNames.ContainsKey($Matches[1])) { return $true }
        return $false
    }
    $mod = @($new | Where-Object { & $isMods $_ })
    $other = @($new | Where-Object { -not (& $isMods $_) })
    if ($mod.Count) {
        Write-Host "  [ERROR] $($mod.Count) error.log line(s) name the mod or a sprite its windows name:" -ForegroundColor Red
        $mod | ForEach-Object { Write-Host "    $_" -ForegroundColor Red }
    } else {
        Write-Host '  [OK] no error.log line names the mod or a sprite its windows name' -ForegroundColor Green
    }
    if ($other.Count) {
        Write-Host "  [INFO] $($other.Count) other new line(s) compared with the vanilla baseline:" -ForegroundColor Gray
        $other | Select-Object -First 20 | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
    }
    return [pscustomobject]@{ Mod = $mod; Other = $other; Total = $current.Count }
}
