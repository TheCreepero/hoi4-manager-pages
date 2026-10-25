BeforeAll {
    $script:RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
    $script:AgentDir = Join-Path $script:RepoRoot '.claude\agents'
    # builder-screen (vanilla screens) stays in the 1440p UI mod; this mod has scripted pages only
    $script:AgentNames = @('designer', 'builder-script', 'game-checker')
    $script:AllowedModels = @('opus', 'sonnet')

    function Read-RepoText {
        param([string]$RelativePath)
        return [System.IO.File]::ReadAllText((Join-Path $script:RepoRoot $RelativePath), [System.Text.Encoding]::UTF8)
    }

    function Get-Frontmatter {
        param([string]$Text)
        if ($Text -notmatch '(?s)\A---\r?\n(.*?)\r?\n---\r?\n') {
            return $null
        }
        $fields = @{}
        foreach ($line in ($Matches[1] -split '\r?\n')) {
            if ($line -match '^([A-Za-z_-]+):\s*(.*)$') {
                $fields[$Matches[1]] = $Matches[2].Trim()
            }
        }
        return $fields
    }

    function Get-SharedBlock {
        param([string]$Text)
        if ($Text -notmatch '(?s)<!-- hoi-agent-block:ui-builder-rules:begin -->(.*?)<!-- hoi-agent-block:ui-builder-rules:end -->') {
            return $null
        }
        return ($Matches[1] -replace '\r\n', "`n")
    }
}

Describe 'Orchestrated phase workflow' {
    It 'wiki/Workflow.md exists and assigns the stages' {
        $text = Read-RepoText 'wiki/Workflow.md'
        $text | Should -Match '(?m)^## Roles and models'
        $text | Should -Match '(?m)^## The stages'
        $text | Should -Match '(?m)^## Handoff files'
        foreach ($name in $script:AgentNames) {
            $text | Should -Match ([regex]::Escape('`' + $name + '`'))
        }
    }

    It 'AGENTS.md, Home.md and the sidebar point to the Workflow page' {
        (Read-RepoText 'AGENTS.md') | Should -Match 'wiki/Workflow\.md'
        (Read-RepoText 'wiki/Home.md') | Should -Match '\(Workflow\.md\)'
        (Read-RepoText 'wiki/_Sidebar.md') | Should -Match '\(Workflow\.md\)'
    }

    It 'the orchestrator skill exists' {
        $skillPath = Join-Path $script:RepoRoot '.claude\skills\pages-phase\SKILL.md'
        Test-Path -LiteralPath $skillPath | Should -BeTrue
        $fields = Get-Frontmatter ([System.IO.File]::ReadAllText($skillPath, [System.Text.Encoding]::UTF8))
        $fields | Should -Not -BeNullOrEmpty
        $fields['name'] | Should -Be 'pages-phase'
        $fields['description'] | Should -Not -BeNullOrEmpty
    }

    It 'the skill is mirrored byte for byte under .agents/skills for Antigravity' {
        $claudeCopy = [System.IO.File]::ReadAllBytes((Join-Path $script:RepoRoot '.claude\skills\pages-phase\SKILL.md'))
        $agentsPath = Join-Path $script:RepoRoot '.agents\skills\pages-phase\SKILL.md'
        Test-Path -LiteralPath $agentsPath | Should -BeTrue -Because 'the knowledge audit requires a copy under .agents/skills'
        $agentsCopy = [System.IO.File]::ReadAllBytes($agentsPath)
        [System.Convert]::ToBase64String($agentsCopy) | Should -Be ([System.Convert]::ToBase64String($claudeCopy)) -Because 'edit .claude/skills/pages-phase/SKILL.md and copy it over the mirror'
    }

    It 'every agent definition exists with a name, a description and an allowed model' {
        foreach ($name in $script:AgentNames) {
            $path = Join-Path $script:AgentDir ($name + '.md')
            Test-Path -LiteralPath $path | Should -BeTrue -Because "$name is a role of wiki/Workflow.md"
            $fields = Get-Frontmatter ([System.IO.File]::ReadAllText($path, [System.Text.Encoding]::UTF8))
            $fields | Should -Not -BeNullOrEmpty -Because "$name.md needs YAML frontmatter"
            $fields['name'] | Should -Be $name
            $fields['description'] | Should -Not -BeNullOrEmpty
            $script:AllowedModels | Should -Contain $fields['model']
        }
    }

    It 'the models follow the user decision of 2026-10-16' {
        $expected = @{ 'designer' = 'opus'; 'builder-script' = 'opus'; 'game-checker' = 'opus' }
        foreach ($name in $expected.Keys) {
            $fields = Get-Frontmatter ([System.IO.File]::ReadAllText((Join-Path $script:AgentDir ($name + '.md')), [System.Text.Encoding]::UTF8))
            $fields['model'] | Should -Be $expected[$name] -Because "$name"
        }
    }

    It 'the builder carries the shared block of the builders' {
        # the 1440p UI mod has two builders with one identical block; here only builder-script exists and keeps it
        $script = Get-SharedBlock (Read-RepoText '.claude/agents/builder-script.md')
        $script | Should -Not -BeNullOrEmpty -Because 'the shared block holds the hard rules of every builder'
    }

    It 'no agent may start the game or commit on its own' {
        foreach ($name in $script:AgentNames) {
            $text = Read-RepoText ('.claude/agents/' + $name + '.md')
            $text | Should -Match 'Invoke-GameCheck\.ps1' -Because "$name names the harness it may or may not run"
            $text | Should -Match '(?i)commit' -Because "$name says who commits"
        }
        foreach ($name in @('designer', 'builder-script')) {
            (Read-RepoText ('.claude/agents/' + $name + '.md')) | Should -Match '(?i)(never|do not) start the game'
        }
        (Read-RepoText '.claude/agents/game-checker.md') | Should -Match '(?i)grant'
    }

    It 'the Phase Template carries the workflow sections' {
        $text = Read-RepoText 'wiki/Phase-Template.md'
        $text | Should -Match '(?m)^## Roles and handoffs'
        $text | Should -Match '(?m)^## Build'
        $text | Should -Match '(?m)^## Fix rounds'
        $text | Should -Match '\| By \|'
    }

    It 'the .claude folder is not git-ignored' {
        $ignore = Read-RepoText '.gitignore'
        $ignore | Should -Not -Match '(?m)^\.claude/?\s*$'
    }
}
