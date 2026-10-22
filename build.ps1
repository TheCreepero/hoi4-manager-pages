[CmdletBinding(DefaultParameterSetName = 'Deploy')]
param(
    [Parameter(ParameterSetName = 'Deploy')]
    [switch]$Deploy,

    [Parameter(ParameterSetName = 'DevLink')]
    [switch]$DevLink,

    [Parameter(ParameterSetName = 'Package')]
    [switch]$Package,

    [Parameter(ParameterSetName = 'PublishSteam')]
    [switch]$PublishSteam,

    [Parameter(ParameterSetName = 'InstallSteamCmd')]
    [switch]$InstallSteamCmd,

    [Parameter(ParameterSetName = 'ValidateOnly')]
    [switch]$ValidateOnly,

    [Parameter(ParameterSetName = 'Test')]
    [switch]$Test,

    # Everything before a game check of one screen: validation, tests and the scene render. With -InGame
    # it goes on to the unattended game check (tools/Invoke-GameCheck.ps1), which takes over the main
    # screen for about two minutes.
    [Parameter(ParameterSetName = 'Check')]
    [string]$Check,

    [Parameter(ParameterSetName = 'Check')]
    [switch]$InGame,

    [switch]$Validate,
    [switch]$NoValidate,
    [switch]$Clean,

    [string]$ModDir,
    [string]$ZipOutput,
    [string]$SteamUser,
    [string]$ChangeNote,
    [string]$SteamCmdPath,
    [switch]$DryRun,
    [switch]$UpdateDescription
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'tools\HoiModBuild.ps1')

$buildConfig = Get-ModBuildConfig -RepoDir $PSScriptRoot -ModDir $ModDir
$RepoDir = $buildConfig.RepoDir

if ($Check) {
    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    if (-not (Invoke-ModValidation -Config $buildConfig)) { Write-Host "`nValidation failed!" -ForegroundColor Red; exit 1 }

    Write-Step "Running the test suite..."
    & (Join-Path $RepoDir "tests\Run-Tests.ps1")
    if ($LASTEXITCODE -ne 0) { Write-Err "Tests failed. Fix them before a game check."; exit 1 }

    Write-Step "Rendering the scene '$Check' (scratch\previews\$Check`_scene.png and _crop.png)..."
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) {
        Write-Warn "python not found: no render. Install Python 3 with Pillow."
    } else {
        & $python.Source -I (Join-Path $RepoDir "tools\render_gui.py") --scene $Check
        if ($LASTEXITCODE -ne 0) { Write-Err "The render failed; read the output above."; exit 1 }
    }

    if ($InGame) {
        Write-Step "Game check of '$Check': restart, new 1936 game, capture (scratch\checks)..."
        & (Join-Path $RepoDir "tools\Invoke-GameCheck.ps1") $Check | Out-Null
    } else {
        Write-Info "Look at the render first. Then check in the game with: tools\Invoke-GameCheck.ps1 $Check  (or add -InGame here)"
    }
    $stopwatch.Stop()
    Write-Host "`nCheck of '$Check' finished in $($stopwatch.Elapsed.TotalSeconds.ToString('0.00'))s" -ForegroundColor Green
    exit 0
}

$buildParameters = Select-ModBuildParameters -BoundParameters $PSBoundParameters
exit (Invoke-ModBuild -Config $buildConfig @buildParameters)
