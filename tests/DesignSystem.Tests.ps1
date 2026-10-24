BeforeAll {
    $script:RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
    $script:Python = (Get-Command python -ErrorAction SilentlyContinue).Source
    $script:Tools = Join-Path $script:RepoRoot 'tools'
    $script:Lint = Join-Path $script:Tools 'lint_gui.py'
    $script:Work = Join-Path (Join-Path $script:RepoRoot 'scratch') 'test-design-system'
    if (-not (Test-Path $script:Work)) { New-Item -ItemType Directory -Path $script:Work -Force | Out-Null }

    function Invoke-Lint {
        param([string]$Exceptions)
        $output = & $script:Python -I $script:Lint '--exceptions' $Exceptions 2>&1
        return @{ Exit = $LASTEXITCODE; Output = ($output | Out-String) }
    }

    function Write-Exceptions {
        param([string]$Name, [object[]]$Exceptions)
        $path = Join-Path $script:Work $Name
        $json = ConvertTo-Json -InputObject @{ exceptions = @($Exceptions) } -Depth 4
        [System.IO.File]::WriteAllText($path, $json, [System.Text.UTF8Encoding]::new($false))
        return $path
    }

    function Get-ListedExceptions {
        $text = [System.IO.File]::ReadAllText((Join-Path $script:Tools 'design_exceptions.json'), [System.Text.Encoding]::UTF8)
        return @(($text | ConvertFrom-Json).exceptions)
    }
}

Describe 'The written pages against the ruleset (tools/lint_gui.py, wiki/Design-Language.md)' {
    It 'finds no deviation that tools/design_exceptions.json does not list with its reason' {
        if (-not $script:Python) { Set-ItResult -Skipped -Because 'python is not installed'; return }
        $result = Invoke-Lint (Join-Path $script:Tools 'design_exceptions.json')
        $result.Exit | Should -Be 0 -Because $result.Output
        $result.Output | Should -Match '0 error\(s\), \d+ warning\(s\), [1-9]\d* excepted'
    }

    It 'fails on a deviation that is not listed' {
        if (-not $script:Python) { Set-ItResult -Skipped -Because 'python is not installed'; return }
        $kept = @(Get-ListedExceptions | Where-Object { -not ($_.rule -eq 'font' -and $_.item -eq 'hoi_36header') })
        $result = Invoke-Lint (Write-Exceptions 'unlisted.json' $kept)
        $result.Exit | Should -Be 1
        $result.Output | Should -Match '(?m)^error\s+font\s+\S+ hoi_36header:'
    }

    It 'fails on a listed exception that no longer occurs' {
        if (-not $script:Python) { Set-ItResult -Skipped -Because 'python is not installed'; return }
        $listed = [System.Collections.Generic.List[PSObject]]::new()
        foreach ($exception in Get-ListedExceptions) { $listed.Add($exception) }
        $listed.Add([pscustomobject]@{ rule = 'row'; window = 'mod1440_no_such_window'; item = 'GFX_1440p_SG_stripe_10x10'; why = 'a test' })
        $result = Invoke-Lint (Write-Exceptions 'stale.json' @($listed))
        $result.Exit | Should -Be 1
        $result.Output | Should -Match '(?m)^error\s+stale\s+mod1440_no_such_window '
    }
}

Describe 'One source for the pieces (tools/layout.py)' {
    It 'the generators name no font, ground, title strip, close button, head plate or band themselves' {
        $pattern = '"(hoi_\w+|GFX_closebutton|GFX_tiled_header|GFX_tiled_plain_bg_small|GFX_tiled_window_1b_thin_border|GFX_1440p_SG_(head|stripe|pick)_[^"]*)"'
        foreach ($generator in @('build_managers.py', 'build_records.py')) {
            $hits = @(Select-String -LiteralPath (Join-Path $script:Tools $generator) -Pattern $pattern | ForEach-Object { '{0}:{1}: {2}' -f $generator, $_.LineNumber, $_.Line.Trim() })
            $hits | Should -BeNullOrEmpty -Because 'the generators take these from tools/layout.py'
        }
    }
}
