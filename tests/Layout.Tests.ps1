BeforeDiscovery {
    $repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
    . (Join-Path (Join-Path $repoRoot 'tools') 'GuiParsing.ps1')
    $python = Get-Command python -ErrorAction SilentlyContinue
    $hasPillow = $false
    if ($python) {
        try { & $python.Source -I -c 'import PIL' 2>$null; $hasPillow = ($LASTEXITCODE -eq 0) } catch { $hasPillow = $false }
    }
    $canRender = $hasPillow -and (Resolve-HoiGameDir)
}

BeforeAll {
    $script:RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
    . (Join-Path (Join-Path $script:RepoRoot 'tools') 'GuiParsing.ps1')
    $script:Python = (Get-Command python -ErrorAction SilentlyContinue).Source
    $script:Tools = Join-Path $script:RepoRoot 'tools'
    $script:Example = Join-Path (Join-Path $script:Tools 'examples') 'a10-layout.json'
    $script:Work = Join-Path (Join-Path $script:RepoRoot 'scratch') 'test-layout'
    if (-not (Test-Path $script:Work)) { New-Item -ItemType Directory -Path $script:Work -Force | Out-Null }

    function Invoke-Tool {
        param([string[]]$Arguments)
        $output = & $script:Python -I @Arguments 2>&1
        return @{ Exit = $LASTEXITCODE; Output = ($output | Out-String) }
    }
}

Describe 'The layout file (tools/layout.py)' {
    It 'the worked example loads and expands its repeats' {
        if (-not $script:Python) { Set-ItResult -Skipped -Because 'python is not installed'; return }
        $code = "import sys; sys.path.insert(0, r'$($script:Tools)'); import layout; lay = layout.load(r'$($script:Example)'); n = sum(len(layout.items(w)) for w in lay['windows']); print(n); print(len(layout.plate_declarations(lay)))"
        $result = Invoke-Tool @('-c', $code)
        $result.Exit | Should -Be 0 -Because $result.Output
        $lines = @($result.Output -split '\r?\n' | Where-Object { $_ })
        [int]$lines[0] | Should -BeGreaterThan 150 -Because 'A10 moves about 150 widgets and adds about 40 plates and captions'
        [int]$lines[1] | Should -Be 11 -Because 'A10 declares eleven plate sprites of the card style'
    }

}

Describe 'The ruleset (tools/lint_layout.py, wiki/Design-Language.md)' {
    It 'passes both worked examples: the steel catalogue with no finding, A10 with its one argued exception' {
        if (-not $script:Python) { Set-ItResult -Skipped -Because 'python is not installed'; return }
        $steel = Invoke-Tool @((Join-Path $script:Tools 'lint_layout.py'), (Join-Path (Join-Path $script:Tools 'examples') 'steel-layout.json'))
        $steel.Exit | Should -Be 0 -Because $steel.Output
        $steel.Output | Should -Match 'steel look: 0 error\(s\), 0 warning\(s\), 0 excepted'
        $a10 = Invoke-Tool @((Join-Path $script:Tools 'lint_layout.py'), $script:Example)
        $a10.Exit | Should -Be 0 -Because $a10.Output
        $a10.Output | Should -Match 'card look: 0 error\(s\), 0 warning\(s\), 1 excepted'
    }

    It 'finds a foreign font, a wrong gap, row and head, and a misplaced close button, and honours a why' {
        if (-not $script:Python) { Set-ItResult -Skipped -Because 'python is not installed'; return }
        $bad = @{
            id = 'T2'; prefix = 'tt'
            windows = @(@{ path = 'w'; size = @(400, 400); background = 'GFX_1440p_steel_ground'; items = @(
                @{ kind = 'steel_title'; name = 'title'; x = 2; y = 2; w = 396; h = 46 },
                @{ kind = 'move'; path = 'close_button'; x = 300; y = 8 },
                @{ kind = 'steel'; name = 'a'; x = 6; y = 54; w = 388; h = 100; head = 30 },
                @{ kind = 'steel'; name = 'b'; x = 6; y = 164; w = 388; h = 100 },
                @{ kind = 'bands'; name = 'rows'; x = 14; y = 84; w = 372; row = 28; rows = 2 },
                @{ kind = 'text'; font = 'hoi_22tech'; x = 20; y = 90; text = 'x' },
                @{ kind = 'text'; font = 'hoi_22tech'; x = 20; y = 120; text = 'y'; why = 'a test' }
            ) })
        }
        $path = Join-Path $script:Work 'lint-bad.json'
        [System.IO.File]::WriteAllText($path, ($bad | ConvertTo-Json -Depth 6), [System.Text.UTF8Encoding]::new($false))
        $result = Invoke-Tool @((Join-Path $script:Tools 'lint_layout.py'), $path)
        $result.Exit | Should -Be 1
        foreach ($rule in @('font', 'gap', 'row', 'head', 'close')) { $result.Output | Should -Match ('(?m)^error\s+' + $rule + '\s') }
        $result.Output | Should -Match '5 error\(s\), 0 warning\(s\), 1 excepted'
    }

}

Describe 'The review (tools/ux_audit.py, the review questions)' {
    It 'lists the same ten review questions in tools/layout.py and on the Design Language page' {
        if (-not $script:Python) { Set-ItResult -Skipped -Because 'python is not installed'; return }
        $code = "import sys; sys.path.insert(0, r'$($script:Tools)'); import layout; [print(i + '|' + t) for i, t, _q in layout.HEURISTICS]"
        $result = Invoke-Tool @('-c', $code)
        $result.Exit | Should -Be 0 -Because $result.Output
        $page = [System.IO.File]::ReadAllText((Join-Path (Join-Path $script:RepoRoot 'wiki') 'Design-Language.md'), [System.Text.Encoding]::UTF8)
        $rows = @($result.Output -split '\r?\n' | Where-Object { $_ })
        $rows.Count | Should -Be 10
        foreach ($row in $rows) {
            $id, $title = $row -split '\|', 2
            $page | Should -Match ('\| ' + [regex]::Escape($id) + ' \| ' + [regex]::Escape($title) + ' \|')
        }
    }

    It 'measures a design and puts the tasks, the answers and the measurements on the design page' -Skip:(-not $canRender) {
        $phase = Join-Path $script:Work 'audit-sample'
        if (Test-Path $phase) { Remove-Item -LiteralPath $phase -Recurse -Force }
        New-Item -ItemType Directory -Path $phase -Force | Out-Null
        Copy-Item -LiteralPath (Join-Path (Join-Path $script:Tools 'examples') 'steel-layout.json') -Destination (Join-Path $phase 'layout.json')
        $mock = Invoke-Tool @((Join-Path $script:Tools 'mockup.py'), (Join-Path $phase 'layout.json'), '--out', (Join-Path $phase 'proposed-main.png'))
        $mock.Exit | Should -Be 0 -Because $mock.Output
        Copy-Item -LiteralPath (Join-Path $phase 'proposed-main.png') -Destination (Join-Path $phase 'vanilla-main.png')
        $design = @{
            id = 'T3'; title = 'Audit sample'; kind = 'screen'; verdict = 'rework'; effort = 'S'; summary = 'Steel.'
            figures = @(@{ file = 'vanilla-main.png'; kind = 'vanilla'; group = 'main' }, @{ file = 'proposed-main.png'; kind = 'proposed'; group = 'main' })
            tasks = @(@{ task = 'How much artillery is short?'; vanilla = @{ clicks = 2; looks = 3 }; proposed = @{ clicks = 0; looks = 1 } })
            heuristics = @(@{ id = 'H1'; verdict = 'pass'; note = 'In the table.' }, @{ id = 'H9'; verdict = 'issue'; note = 'Red alone marks a shortage.' })
        }
        [System.IO.File]::WriteAllText((Join-Path $phase 'design.json'), ($design | ConvertTo-Json -Depth 6), [System.Text.UTF8Encoding]::new($false))
        $audit = Invoke-Tool @((Join-Path $script:Tools 'ux_audit.py'), $phase)
        $audit.Exit | Should -Be 0 -Because $audit.Output
        $audit.Output | Should -Match 'linter: 0 error\(s\)'
        $audit.Output | Should -Match 'contrast: \d+ of \d+ texts under the floor'
        $audit.Output | Should -Match 'squinted: figures/main-squint\.webp'
        $result = Invoke-Tool @((Join-Path $script:Tools 'make_design_page.py'), $phase)
        $result.Exit | Should -Be 0 -Because $result.Output
        $text = [System.IO.File]::ReadAllText((Join-Path $phase 'design.html'), [System.Text.Encoding]::UTF8)
        foreach ($part in @('Player tasks', 'How much artillery is short\?', 'Review questions', 'Hierarchy and legibility', 'not answered', 'Measured', 'Contrast', 'Squinted')) { $text | Should -Match $part }
        ([regex]::Matches($text, '<img ')).Count | Should -Be 2 -Because 'the figure group and its squinted copy'
    }
}

Describe 'The mock-up from a layout (tools/mockup.py)' -Skip:(-not $canRender) {
    It 'draws the steel catalogue' {
        # the A10 example draws on a capture of a reworked screen (reference/mod/air_selection.jpg) that stays in the
        # 1440p UI mod; the steel catalogue draws on a plain canvas
        $out = Join-Path $script:Work 'steel-mockup-test.png'
        if (Test-Path $out) { Remove-Item -LiteralPath $out -Force }
        $result = Invoke-Tool @((Join-Path $script:Tools 'mockup.py'), (Join-Path (Join-Path $script:Tools 'examples') 'steel-layout.json'), '--out', $out)
        $result.Exit | Should -Be 0 -Because $result.Output
        Test-Path $out | Should -BeTrue
        (Get-Item $out).Length | Should -BeGreaterThan 100000
    }
}

Describe 'The design page (tools/make_design_page.py)' {
    It 'makes a page with one composite image per figure group from a sample handoff folder' {
        if (-not $script:Python) { Set-ItResult -Skipped -Because 'python is not installed'; return }
        & $script:Python -I -c 'import PIL' 2>$null
        if ($LASTEXITCODE -ne 0) { Set-ItResult -Skipped -Because 'Pillow is not installed'; return }
        $phase = Join-Path $script:Work 'phase-sample'
        if (Test-Path $phase) { Remove-Item -LiteralPath $phase -Recurse -Force }
        New-Item -ItemType Directory -Path (Join-Path $phase 'build') -Force | Out-Null
        $design = @{
            id = 'T1'; title = 'Sample screen'; kind = 'screen'; verdict = 'rework'; effort = 'S'
            summary = 'Two **bold** words and `code`.'; current = 'Cramped.'
            proposal = @(@{ heading = 'Head'; body = 'Body.' })
            table = @{ columns = @('Part', 'Vanilla', 'Current', 'Proposed'); rows = @(, @('Panel', '1x1', '', '2x2')) }
            figures = @(@{ file = 'vanilla-main.png'; kind = 'vanilla'; group = 'main'; caption = 'v' }, @{ file = 'proposed-main.png'; kind = 'proposed'; group = 'main'; caption = 'p' })
            decisions = @(@{ question = 'Which width?'; options = @('A', 'B'); recommendation = 'A' })
            openInGame = @('The tooltip.'); risks = @(); knowledge = @(); additions = @()
        }
        [System.IO.File]::WriteAllText((Join-Path $phase 'design.json'), ($design | ConvertTo-Json -Depth 6), [System.Text.UTF8Encoding]::new($false))
        [System.IO.File]::WriteAllText((Join-Path $phase 'decisions-final.json'), '[{"question": "Which width?", "chosen": "A", "by": "user"}]', [System.Text.UTF8Encoding]::new($false))
        [System.IO.File]::WriteAllText((Join-Path (Join-Path $phase 'build') 'build.json'), '{"id": "T1", "summary": "Built.", "figures": [{"file": "build-main.png", "group": "main", "caption": "b"}], "deviations": [{"what": "x", "why": "y"}]}', [System.Text.UTF8Encoding]::new($false))
        $mk = "from PIL import Image; import os; d = r'$phase'; [Image.new('RGB', (200, 100), c).save(os.path.join(d, p)) for p, c in (('vanilla-main.png', (90, 30, 30)), ('proposed-main.png', (30, 90, 30)), ('build/build-main.png', (30, 30, 90)))]"
        $made = Invoke-Tool @('-c', $mk)
        $made.Exit | Should -Be 0 -Because $made.Output
        $result = Invoke-Tool @((Join-Path $script:Tools 'make_design_page.py'), $phase)
        $result.Exit | Should -Be 0 -Because $result.Output
        $page = Join-Path $phase 'design.html'
        Test-Path $page | Should -BeTrue
        $text = [System.IO.File]::ReadAllText($page, [System.Text.Encoding]::UTF8)
        $text | Should -Match 'Which width\?'
        $text | Should -Match 'Chosen: A'
        $text | Should -Match '<b>bold</b>'
        $text | Should -Match 'Where the build differs'
        ([regex]::Matches($text, '<img ')).Count | Should -Be 1 -Because 'one composite per figure group'
        Test-Path (Join-Path (Join-Path $phase 'figures') 'main.webp') | Should -BeTrue
    }
}

Describe 'The phase notes (tools/phase_notes.py)' {
    It 'writes the generated sections between markers from the handoff files, and a second run changes nothing' {
        if (-not $script:Python) { Set-ItResult -Skipped -Because 'python is not installed'; return }
        $scratch = Join-Path $script:Work 'notes-scratch'
        $phase = Join-Path $scratch 'N1'
        if (Test-Path $scratch) { Remove-Item -LiteralPath $scratch -Recurse -Force }
        New-Item -ItemType Directory -Path (Join-Path $phase 'checks') -Force | Out-Null
        New-Item -ItemType Directory -Path (Join-Path $phase 'build') -Force | Out-Null
        $utf8 = [System.Text.UTF8Encoding]::new($false)
        [System.IO.File]::WriteAllText((Join-Path $phase 'design.json'), '{"id": "N1", "summary": "A card pass.", "verdict": "refine", "effort": "S", "proposal": [{"heading": "Head", "body": "Body."}], "table": {"columns": ["Part", "Vanilla", "Proposed"], "rows": [["Panel", "1", "2"]]}, "figures": [{"file": "a.png", "kind": "proposed", "group": "main"}]}', $utf8)
        [System.IO.File]::WriteAllText((Join-Path (Join-Path $phase 'build') 'build.json'), '{"id": "N1", "agent": "builder-screen", "summary": "Built.", "deviations": [{"what": "x", "why": "y"}], "gameCheck": "tools/Invoke-GameCheck.ps1 air_region", "checklist": ["one", "two"], "tests": "green"}', $utf8)
        [System.IO.File]::WriteAllText((Join-Path (Join-Path $phase 'checks') 'check-1.json'), '{"id": "N1", "round": 1, "date": "2026-10-20", "build": "abc+dirty", "playset": "this mod only", "launches": [{"command": "tools/Invoke-GameCheck.ps1 air_region", "captures": ["scratch/checks/air_region_crop.png"], "clock": "1 Jan 1936", "errorLog": []}], "checklist": [{"item": 1, "result": "pass"}, {"item": 2, "result": "fail", "note": "cut", "evidence": "e.png", "box": [0, 0, 1, 1]}], "defects": [{"what": "cut", "where": "w", "evidence": "e.png"}], "forTheUser": ["tooltip"], "autosave": "not touched"}', $utf8)
        [System.IO.File]::WriteAllText((Join-Path $phase 'fixes.json'), '[{"round": 1, "date": "2026-10-20", "issue": "cut", "cause": "c", "fix": "f", "retest": "r", "by": "builder-screen"}]', $utf8)
        $notes = Join-Path $scratch 'N1-sample.md'
        Copy-Item -LiteralPath (Join-Path (Join-Path $script:RepoRoot 'wiki') 'Phase-Template.md') -Destination $notes -Force
        $first = Invoke-Tool @((Join-Path $script:Tools 'phase_notes.py'), 'N1', '--notes', $notes, '--scratch', $scratch)
        $first.Exit | Should -Be 0 -Because $first.Output
        $text = [System.IO.File]::ReadAllText($notes, [System.Text.Encoding]::UTF8)
        foreach ($name in @('proposal', 'build', 'game checks', 'fix rounds')) {
            $text | Should -Match ('<!-- generated: ' + $name + ' \(')
            $text | Should -Match ('<!-- end generated: ' + $name + ' -->')
        }
        $text | Should -Match 'A card pass\. Verdict: refine; effort: S\.'
        $text | Should -Match '\| 1 \| 2026-10-20 \| abc\+dirty \| game-checker \|'
        $text | Should -Match '### Fix round 1 \(2026-10-20\)'
        $text | Should -Match '(?m)^## Scope' -Because 'the hand-written sections stay'
        $check = Invoke-Tool @((Join-Path $script:Tools 'phase_notes.py'), 'N1', '--notes', $notes, '--scratch', $scratch, '--check')
        $check.Exit | Should -Be 0 -Because $check.Output
        $second = Invoke-Tool @((Join-Path $script:Tools 'phase_notes.py'), 'N1', '--notes', $notes, '--scratch', $scratch)
        [System.IO.File]::ReadAllText($notes, [System.Text.Encoding]::UTF8) | Should -Be $text
    }

    It 'the crop tool cuts a box out of a capture' {
        if (-not $script:Python) { Set-ItResult -Skipped -Because 'python is not installed'; return }
        & $script:Python -I -c 'import PIL' 2>$null
        if ($LASTEXITCODE -ne 0) { Set-ItResult -Skipped -Because 'Pillow is not installed'; return }
        $src = Join-Path $script:Work 'crop-src.png'
        $mk = "from PIL import Image; Image.new('RGB', (300, 200), (10, 20, 30)).save(r'$src')"
        (Invoke-Tool @('-c', $mk)).Exit | Should -Be 0
        $out = Join-Path $script:Work 'crop-out.png'
        $result = Invoke-Tool @((Join-Path $script:Tools 'crop_capture.py'), $src, '10,10,110,60', '--out', $out, '--scale', '2')
        $result.Exit | Should -Be 0 -Because $result.Output
        $result.Output | Should -Match '200x100'
    }
}
