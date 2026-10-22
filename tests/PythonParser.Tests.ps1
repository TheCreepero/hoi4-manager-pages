BeforeDiscovery {
    $repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
    . (Join-Path (Join-Path $repoRoot 'tools') 'GuiParsing.ps1')

    $script:PythonCommand = Get-Command python -ErrorAction SilentlyContinue
    $hasPython = $false
    if ($script:PythonCommand) {
        try { $hasPython = ((& $script:PythonCommand.Source --version 2>&1) -match '^Python 3') } catch { $hasPython = $false }
    }

    # Every mod .gui file, plus a fixed sample of vanilla files when the game is installed: the big
    # ones, one from a subfolder, and the two the mod overrides windows from.
    $parityCases = @()
    if ($hasPython) {
        foreach ($file in @(Get-ChildItem -Path (Join-Path $repoRoot 'interface') -Recurse -File -Filter '*.gui')) {
            $parityCases += @{ Label = $file.Name; FullPath = $file.FullName }
        }
        $gameDir = Resolve-HoiGameDir
        if ($gameDir) {
            foreach ($rel in 'unitview.gui', 'airselectionview.gui', 'naviesview.gui', 'core.gui', 'countrydivisiondesignerview.gui', 'factions\factions_view.gui') {
                $full = Join-Path (Join-Path $gameDir 'interface') $rel
                if (Test-Path -LiteralPath $full) { $parityCases += @{ Label = "vanilla $rel"; FullPath = $full } }
            }
        }
    }
}

BeforeAll {
    $script:RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
    . (Join-Path (Join-Path $script:RepoRoot 'tools') 'GuiParsing.ps1')
    $script:GuiParsePy = Join-Path (Join-Path $script:RepoRoot 'tools') 'guiparse.py'
    $script:Python = (Get-Command python -ErrorAction SilentlyContinue).Source
}

Describe 'Python parser' {
    It 'is available, or the parity tests are skipped' {
        if (-not $script:Python) { Set-ItResult -Skipped -Because 'python is not installed'; return }
        (& $script:Python -I $script:GuiParsePy --game-dir) | Out-Null
        $LASTEXITCODE | Should -Be 0
    }
}

if ($parityCases.Count -gt 0) {
    Describe 'Python parser on <Label>' -ForEach $parityCases {
        It 'lists the same widget paths as the PowerShell parser' {
            $expected = @()
            $root = ConvertFrom-GuiText -Text (Read-GuiText -Path $FullPath)
            foreach ($window in @(Get-GuiTopLevelWindows -Root $root)) { $expected += @(Get-GuiWidgetPaths -Node $window.Node) }

            $actual = @(& $script:Python -I $script:GuiParsePy --dump $FullPath)
            $LASTEXITCODE | Should -Be 0
            $actual.Count | Should -Be $expected.Count
            # order matters too: both walk the tree the same way
            $mismatch = 0
            for ($i = 0; $i -lt $expected.Count; $i++) { if ($actual[$i] -cne $expected[$i]) { $mismatch++ } }
            $mismatch | Should -Be 0 -Because 'the renderer relies on the Python tree matching the tested one'
        }
    }
}
