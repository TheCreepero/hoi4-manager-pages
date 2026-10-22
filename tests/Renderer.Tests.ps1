BeforeDiscovery {
    $repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
    . (Join-Path (Join-Path $repoRoot 'tools') 'GuiParsing.ps1')

    $python = Get-Command python -ErrorAction SilentlyContinue
    $hasPillow = $false
    if ($python) {
        try { & $python.Source -I -c 'import PIL' 2>$null; $hasPillow = ($LASTEXITCODE -eq 0) } catch { $hasPillow = $false }
    }
    $gameDir = Resolve-HoiGameDir
    $canRender = $hasPillow -and $gameDir

    # Every overridden window renders; every scene composes. All of them in one render_gui.py --batch run
    # (see BeforeAll), so the textures, fonts and indexes load once instead of once per window.
    $windowCases = @()
    $sceneCases = @()
    if ($canRender) {
        foreach ($window in @(Get-GuiModWindows -InterfaceDir (Join-Path $repoRoot 'interface'))) {
            $windowCases += @{ Window = $window.Name; File = $window.File }
        }
        foreach ($scene in @(Get-ChildItem -Path (Join-Path (Join-Path $repoRoot 'tools') 'scenes') -Filter '*.json' -ErrorAction SilentlyContinue)) {
            $sceneCases += @{ Scene = $scene.BaseName }
        }
    }
}

BeforeAll {
    $script:RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
    . (Join-Path (Join-Path $script:RepoRoot 'tools') 'GuiParsing.ps1')
    $script:Python = (Get-Command python -ErrorAction SilentlyContinue).Source
    $script:RenderPy = Join-Path (Join-Path $script:RepoRoot 'tools') 'render_gui.py'
    $script:OutDir = Join-Path (Join-Path $script:RepoRoot 'scratch') 'test-renders'
    if (-not (Test-Path $script:OutDir)) { New-Item -ItemType Directory -Path $script:OutDir -Force | Out-Null }

    $script:RenderJobs = @{}
    $hasPillow = $false
    if ($script:Python) {
        & $script:Python -I -c 'import PIL' 2>$null
        $hasPillow = ($LASTEXITCODE -eq 0)
    }
    if ($hasPillow -and (Resolve-HoiGameDir)) {
        $jobs = [System.Collections.Generic.List[object]]::new()
        foreach ($window in @(Get-GuiModWindows -InterfaceDir (Join-Path $script:RepoRoot 'interface'))) {
            $jobs.Add(@{ id = "window:$($window.Name)"; args = @($window.Name, '--scale', '1', '--out', (Join-Path $script:OutDir "$($window.Name).png")) })
        }
        foreach ($scene in @(Get-ChildItem -Path (Join-Path (Join-Path $script:RepoRoot 'tools') 'scenes') -Filter '*.json' -ErrorAction SilentlyContinue)) {
            $jobs.Add(@{ id = "scene:$($scene.BaseName)"; args = @('--scene', $scene.BaseName, '--out', (Join-Path $script:OutDir "$($scene.BaseName)_scene.png")) })
        }
        $script:RenderJobs = Invoke-GuiRenderBatch -Python $script:Python -RenderPy $script:RenderPy -Jobs $jobs -JobsPath (Join-Path $script:OutDir 'render-jobs.json')
    }

    function Get-RenderJob {
        param([string]$Id)
        $job = $script:RenderJobs[$Id]
        if (-not $job) {
            $batchLines = @($script:RenderJobs['*'].Output | Select-Object -First 20)
            throw "the render batch gave no result for $Id (exit $($script:RenderJobs['*'].Exit)); its output starts: $($batchLines -join "`n")"
        }
        return $job
    }
}

Describe 'Renderer prerequisites' {
    It 'has Python with Pillow and a game install, or the render tests are skipped' {
        if (-not $script:Python) { Set-ItResult -Skipped -Because 'python is not installed'; return }
        & $script:Python -I -c 'import PIL' 2>$null
        if ($LASTEXITCODE -ne 0) { Set-ItResult -Skipped -Because 'Pillow is not installed'; return }
        if (-not (Resolve-HoiGameDir)) { Set-ItResult -Skipped -Because 'no Hearts of Iron IV install (textures and fonts come from it)'; return }
        $true | Should -BeTrue
    }
}

if ($windowCases.Count -gt 0) {
    Describe 'Render window <Window> (<File>)' -ForEach $windowCases {
        It 'draws without an error and names no undeclared sprite' {
            $job = Get-RenderJob -Id "window:$Window"
            $output = @($job.Output)
            $job.Exit | Should -Be 0 -Because ($output -join "`n")
            Test-Path (Join-Path $script:OutDir "$Window.png") | Should -BeTrue
            # vanilla windows carry placeholder sprite names the code replaces (GFX_idea_HOL_wilhelmina ...), so only mod sprites count
            @($output | Where-Object { $_ -match 'GFX_1440p_\w+ is not declared in any \.gfx file' }) | Should -BeNullOrEmpty -Because 'a sprite name the game cannot find draws nothing'
            @($output | Where-Object { $_ -match '(mod1440|GFX_1440p_).*not found' }) | Should -BeNullOrEmpty -Because 'a missing mod texture draws nothing in game either'
            @($output | Where-Object { $_ -match 'font .* not found' }) | Should -BeNullOrEmpty -Because 'a font name that vanilla does not declare shows no text'
        }
    }
}

if ($sceneCases.Count -gt 0) {
    Describe 'Render scene <Scene>' -ForEach $sceneCases {
        It 'composes every window of the scene' {
            $job = Get-RenderJob -Id "scene:$Scene"
            $output = @($job.Output)
            $job.Exit | Should -Be 0 -Because ($output -join "`n")
            @($output | Where-Object { $_ -match 'NOT FOUND' }) | Should -BeNullOrEmpty -Because 'every window named in a scene must exist'
            @($output | Where-Object { $_ -match '^\s*cut off\s' }) | Should -BeNullOrEmpty -Because 'a sample text that is cut off needs a wider box or a shorter sample'
        }
    }
}
