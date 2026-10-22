# Checks of the scripted GUIs of Milestone D (wiki/Scripted-GUIs.md): the files under common/ and
# localisation/ that tools/build_managers.py writes, and the rules they follow.

BeforeAll {
    $script:RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
    . (Join-Path (Join-Path $script:RepoRoot 'tools') 'GuiParsing.ps1')

    $script:Prefix = 'mod1440_'
    $script:CommonDir = Join-Path $script:RepoRoot 'common'

    # A script file as a tree. Comparisons are turned into assignments first: the parser of GuiParsing.ps1
    # knows "=" only, and for these checks "unit_strength < 0.75" is a statement like any other.
    function Read-ScriptTree {
        param([string]$Path)
        $text = [regex]::Replace((Read-GuiText -Path $Path), '#[^\r\n]*', '')
        $text = [regex]::Replace($text, '(?<=\s)[<>](?=\s)', '=')
        return ConvertFrom-GuiText -Text $text
    }

    function Get-ScriptFiles {
        param([string]$Folder)
        $dir = Join-Path $script:CommonDir $Folder
        if (-not (Test-Path $dir)) { return @() }
        return @(Get-ChildItem -Path $dir -File -Filter '*.txt')
    }

    # Every scripted GUI of the mod: its name, its tree and the file it is in.
    function Get-ScriptedGuis {
        foreach ($file in @(Get-ScriptFiles -Folder 'scripted_guis')) {
            $root = Read-ScriptTree -Path $file.FullName
            foreach ($section in @($root.Children)) {
                if ($section.Key -ine 'scripted_gui' -or $null -eq $section.Children) { continue }
                foreach ($entry in @($section.Children)) {
                    if ($null -eq $entry.Children) { continue }
                    [pscustomobject]@{ Name = $entry.Key; Node = $entry; File = $file.Name }
                }
            }
        }
    }

    # The top-level container of a scripted GUI, from whichever mod .gui file defines it (parsed once, tools/GuiParsing.ps1).
    function Find-Container {
        param([string]$Name)
        return @(Get-GuiModWindows -InterfaceDir (Join-Path $script:RepoRoot 'interface') | Where-Object { $_.Name -eq $Name })[0]
    }

    function Get-WidgetNames {
        param($Node)
        $names = [System.Collections.Generic.HashSet[string]]::new()
        foreach ($block in @(Get-GuiNodes -Node $Node)) {
            $name = Get-GuiValue -Node $block -Key 'name'
            if ($name) { [void]$names.Add([string]$name) }
        }
        return , $names   # the comma keeps the set a set: PowerShell would hand its elements over one by one
    }

    # Commands whose block holds variables and numbers, not further commands.
    $script:ArgumentCommands = @(
        'set_variable', 'add_to_variable', 'subtract_from_variable', 'multiply_variable', 'divide_variable',
        'clamp_variable', 'round_variable', 'clear_variable', 'check_variable', 'has_variable',
        'set_temp_variable', 'add_to_temp_variable', 'subtract_from_temp_variable', 'multiply_temp_variable',
        'divide_temp_variable', 'round_temp_variable', 'add_to_array', 'add_to_temp_array', 'remove_from_array', 'clear_array',
        'clear_temp_array', 'resize_array', 'find_highest_in_array', 'find_lowest_in_array',
        'free_building_slots', 'is_in_array', 'has_country_leader', 'date',
        # --- e-diary-wars and e-officers-gov (2026-10-16): the marks of a war's track; the count of an officer's traits
        'clamp_temp_variable'
    )
    # Commands that write to the game itself, each with the page that needs it (wiki/Roleplay-Pages.md, the
    # changed rule). add_history_entry: a line in a division's own history, phase E6. Nothing else.
    $script:WritingCommands = @('add_history_entry')
    # Everything else the mod's script may say. A scripted GUI of this mod shows, navigates and keeps records
    # (wiki/Scripted-GUIs.md, rule 1): nothing that gives the player what the game charges for belongs here.
    # None of these writes to the game. A command that does (a role-play page of wiki/Roleplay-Pages.md)
    # gets a list of its own beside this one, with the page that needs it.
    $script:AllowedCommands = @(
        'if', 'else', 'else_if', 'limit', 'AND', 'OR', 'NOT', 'always', 'is_ai',
        'for_each_loop', 'for_each_scope_loop', 'for_loop_effect', 'while_loop_effect',
        'array', 'value', 'index', 'start', 'end', 'add', 'compare', 'break',
        'every_country', 'every_country_division', 'unit_strength', 'unit_organization', 'is_core_of',
        'goto_state', 'goto_province', 'log', 'ROOT', 'PREV', 'THIS', 'FROM', 'FROM.FROM', 'OWNER',
        # the Records window (Milestone E): what is asked of an officer, a country and a state
        'is_field_marshal', 'is_corps_commander', 'is_navy_leader', 'any_character', 'is_army_chief', 'is_navy_chief',
        'is_air_chief', 'is_theorist', 'has_idea', 'is_in_faction', 'has_capitulated', 'exists', 'is_capital',
        'is_controlled_by', 'has_dlc', 'tag', 'every_state_division', 'every_army_leader', 'every_navy_leader',
        # the conditions under which the game gives a country a medal, copied from the game (tools/unit_medals_table.py)
        'has_government', 'original_tag', 'has_completed_focus', 'has_country_flag', 'owns_state',
        # portraits and victory points (2026-10-13): whether a character is a certain one, whether the country is at war
        'is_character', 'has_character', 'has_war',
        # the map of another mod (2026-10-13): the states of the loaded game are counted to tell which map it is
        'every_state',
        # --- d3-states --- the band of the chosen state (2026-10-16): what is asked of a state for its card and chips
        'is_owned_by', 'has_state_category', 'is_coastal', 'is_island_state', 'is_demilitarized_zone', 'has_border_war',
        # --- e-diary-wars (2026-10-16): the days each state taken is held, for its card
        'every_controlled_state',
        # e-officers-gov (2026-10-16): an officer's traits, kept on him, and his status under his name
        'has_trait', 'is_general_captured', 'is_leading_army_group',
        # --- D2 round 2 --- (2026-10-17) Army Readiness: the commanders of single armies (Fighting, Without a
        # commander), and the countries whose states can hold the player's divisions (Location); all read-only
        'is_leading_army', 'is_in_faction_with', 'has_war_with'
    )

    # Adds to $Into every command of a block that is neither allowed nor an effect of the mod's own.
    function Find-ForeignCommands {
        param($Node, [System.Collections.Generic.List[string]]$Into, [string]$Where)
        foreach ($child in @($Node.Children)) {
            $key = [string]$child.Key
            if ($script:ArgumentCommands -contains $key -or $script:WritingCommands -contains $key) { continue }
            if ($key -like "$($script:Prefix)*") { continue }
            if ($key -like 'should_have_*_medals_trigger') { continue }   # the game's own scripted triggers for its medals
            # "<number> = { ... }" enters the scope of the state with that number (the state of a victory point)
            if ($key -match '^[0-9]+$') { if ($null -ne $child.Children) { Find-ForeignCommands -Node $child -Into $Into -Where $Where }; continue }
            # "var:<variable> = { ... }" enters the scope a variable holds (Engine Facts X33): no command of its own
            if ($key -notlike 'var:*' -and $script:AllowedCommands -notcontains $key) { $Into.Add("$Where line $($child.Line): $key") }
            if ($null -ne $child.Children) { Find-ForeignCommands -Node $child -Into $Into -Where $Where }
        }
    }
}

Describe 'Scripted GUI files' {
    It 'are what tools/build_managers.py writes' {
        $python = (Get-Command python -ErrorAction SilentlyContinue).Source
        if (-not $python) { Set-ItResult -Skipped -Because 'Python is not installed'; return }
        $output = & $python -I (Join-Path (Join-Path $script:RepoRoot 'tools') 'build_managers.py') --check 2>&1
        $LASTEXITCODE | Should -Be 0 -Because ("the generated files are edited through the tool: " + ($output -join ' '))
    }

    It 'rest on tables of game content that match the installed game' {
        # tools/portraits_table.py and tools/victory_points_table.py: after a game update, tools/make_game_tables.py
        $python = (Get-Command python -ErrorAction SilentlyContinue).Source
        if (-not $python) { Set-ItResult -Skipped -Because 'Python is not installed'; return }
        $output = & $python -I (Join-Path (Join-Path $script:RepoRoot 'tools') 'make_game_tables.py') --check 2>&1
        if (($output -join ' ') -match 'game folder|not found|No such file') { Set-ItResult -Skipped -Because 'the game is not installed'; return }
        $LASTEXITCODE | Should -Be 0 -Because ("the tables are made by the tool from the game: " + ($output -join ' '))
    }

    It 'carry the mod prefix in every file name under common/' {
        $wrong = foreach ($folder in @(Get-ChildItem -Path $script:CommonDir -Directory -ErrorAction SilentlyContinue)) {
            foreach ($file in @(Get-ChildItem -Path $folder.FullName -Recurse -File)) {
                if ($file.Name -notlike "$($script:Prefix)*") { "$($folder.Name)\$($file.Name)" }
            }
        }
        $wrong | Should -BeNullOrEmpty -Because 'a file named like a vanilla file would replace it'
    }
}

Describe 'Scripted GUIs' {
    BeforeAll {
        $script:Guis = @(Get-ScriptedGuis)
    }

    It 'exist' {
        $script:Guis.Count | Should -BeGreaterThan 0
    }

    It 'are named after the mod and show a container of the mod' {
        $problems = foreach ($gui in $script:Guis) {
            if ($gui.Name -notlike "$($script:Prefix)*") { "$($gui.Name): name without the mod prefix" }
            $window = [string](Get-GuiValue -Node $gui.Node -Key 'window_name')
            if ($window -notlike "$($script:Prefix)*") { "$($gui.Name): window '$window' without the mod prefix" }
            elseif (-not (Find-Container -Name $window)) { "$($gui.Name): no .gui file of the mod defines '$window'" }
        }
        $problems | Should -BeNullOrEmpty
    }

    It 'point every effect, trigger and property at a widget of their container' {
        $problems = foreach ($gui in $script:Guis) {
            $window = Find-Container -Name ([string](Get-GuiValue -Node $gui.Node -Key 'window_name'))
            if (-not $window) { continue }
            $names = Get-WidgetNames -Node $window.Node
            # a list row is a container of its own: its widgets count as well
            $lists = Get-GuiBlock -Node $gui.Node -Key 'dynamic_lists'
            if ($lists) {
                foreach ($list in @($lists.Children)) {
                    if (-not $names.Contains([string]$list.Key)) { "$($gui.Name): list '$($list.Key)' is not a grid of '$($window.Name)'" }
                    $entry = Find-Container -Name ([string](Get-GuiValue -Node $list -Key 'entry_container'))
                    if (-not $entry) { "$($gui.Name): list '$($list.Key)' has no entry container in a .gui file of the mod"; continue }
                    foreach ($name in (Get-WidgetNames -Node $entry.Node)) { [void]$names.Add($name) }
                }
            }
            foreach ($part in 'effects', 'triggers', 'properties') {
                $block = Get-GuiBlock -Node $gui.Node -Key $part
                if (-not $block) { continue }
                foreach ($entry in @($block.Children)) {
                    $widget = [string]$entry.Key
                    if ($part -eq 'effects') { $widget = $widget -replace '(_alt|_control|_shift)?(_right)?_click$', '' }
                    if ($part -eq 'triggers') { $widget = $widget -replace '(_click_enabled|_visible)$', '' }
                    if (-not $names.Contains($widget)) { "$($gui.Name): $part '$($entry.Key)' names no widget of '$($window.Name)'" }
                }
            }
        }
        $problems | Should -BeNullOrEmpty
    }

    It 'keep the AI away from every panel' {
        $problems = foreach ($gui in $script:Guis) {
            $ai = Get-GuiBlock -Node $gui.Node -Key 'ai_enabled'
            if (-not $ai -or (Get-GuiValue -Node $ai -Key 'always') -ne 'no') { "$($gui.Name): no 'ai_enabled = { always = no }'" }
        }
        $problems | Should -BeNullOrEmpty -Because 'the panels are for the player; an AI that looks at them costs time'
    }

    It 'belong to the player and to nobody else' {
        # One exception: the card in the state view belongs to the state the player has selected, and shows
        # itself only for a state the player controls. So does its line of who took it (e-diary-wars).
        $problems = foreach ($gui in $script:Guis) {
            $context = Get-GuiValue -Node $gui.Node -Key 'context_type'
            if ($gui.Name -eq 'mod1440_state_card' -or $gui.Name -eq 'mod1440_state_card_by') {
                if ($context -ne 'selected_state_context') { "$($gui.Name): context is not selected_state_context" }
                $visible = Get-GuiBlock -Node $gui.Node -Key 'visible'
                if (-not $visible -or (Get-GuiValue -Node $visible -Key 'is_controlled_by') -ne 'ROOT') { "$($gui.Name): not limited to states the player controls" }
            }
            elseif ($context -ne 'player_context') { "$($gui.Name): context is not player_context" }
        }
        $problems | Should -BeNullOrEmpty -Because 'the mod shows values of the own country only (wiki/Scripted-GUIs.md, rule 2)'
    }
}

Describe 'Script of the mod' {
    It 'uses only the commands this test lists' {
        $foreign = [System.Collections.Generic.List[string]]::new()
        foreach ($gui in @(Get-ScriptedGuis)) {
            foreach ($part in 'visible', 'effects', 'triggers') {
                $block = Get-GuiBlock -Node $gui.Node -Key $part
                if (-not $block) { continue }
                if ($part -eq 'visible') { Find-ForeignCommands -Node $block -Into $foreign -Where "$($gui.File) $($gui.Name)" }
                else { foreach ($entry in @($block.Children)) { if ($null -ne $entry.Children) { Find-ForeignCommands -Node $entry -Into $foreign -Where "$($gui.File) $($entry.Key)" } } }
            }
        }
        foreach ($file in @(Get-ScriptFiles -Folder 'scripted_effects')) {
            foreach ($effect in @((Read-ScriptTree -Path $file.FullName).Children)) {
                if ($effect.Key -notlike "$($script:Prefix)*") { $foreign.Add("$($file.Name): effect '$($effect.Key)' without the mod prefix") }
                if ($null -ne $effect.Children) { Find-ForeignCommands -Node $effect -Into $foreign -Where "$($file.Name) $($effect.Key)" }
            }
        }
        foreach ($file in @(Get-ScriptFiles -Folder 'on_actions')) {
            $actions = Get-GuiBlock -Node (Read-ScriptTree -Path $file.FullName) -Key 'on_actions'
            foreach ($action in @($actions.Children)) {
                foreach ($effect in @($action.Children | Where-Object { $_.Key -eq 'effect' -and $null -ne $_.Children })) {
                    Find-ForeignCommands -Node $effect -Into $foreign -Where "$($file.Name) $($action.Key)"
                }
            }
        }
        $names = @($foreign | ForEach-Object { ($_ -split ': ')[-1] } | Sort-Object -Unique)
        ($names + @($foreign | Select-Object -First 5)) | Should -BeNullOrEmpty -Because 'a new command goes into the list of this test first, and one that writes to the game only with the page that needs it'
    }

    It 'writes to the game only in the files of the Records window' {
        $problems = foreach ($file in @(Get-ChildItem -Path $script:CommonDir -Recurse -File -Filter '*.txt')) {
            $text = [System.IO.File]::ReadAllText($file.FullName)
            foreach ($command in $script:WritingCommands) {
                if ($text -match "\b$command\b" -and $file.Name -ne 'mod1440_records.txt') { "$($file.Name): $command" }
            }
        }
        $problems | Should -BeNullOrEmpty -Because 'the unit honours of phase E6 are the one thing the mod writes into the game (wiki/Roleplay-Pages.md)'
    }

    It 'lists every name used after @ or as token: as a synchronised token' {
        $tokenFiles = @(Get-ScriptFiles -Folder 'synchronized_dynamic_tokens')
        $listed = @{}
        foreach ($file in $tokenFiles) { foreach ($line in [System.IO.File]::ReadAllLines($file.FullName)) { if ($line.Trim()) { $listed[$line.Trim()] = $true } } }
        $sources = @(Get-ChildItem -Path $script:CommonDir -Recurse -File -Filter '*.txt') +
                   @(Get-ChildItem -Path (Join-Path $script:RepoRoot 'interface') -Recurse -File -Filter "$($script:Prefix)*.gui")
        $locDir = Join-Path $script:RepoRoot 'localisation'
        if (Test-Path $locDir) { $sources += @(Get-ChildItem -Path $locDir -Recurse -File -Filter '*.yml') }
        $missing = foreach ($file in $sources) {
            foreach ($m in [regex]::Matches([System.IO.File]::ReadAllText($file.FullName), '(?:@(?!var:)|token:)([A-Za-z_][A-Za-z0-9_]*)')) {
                if (-not $listed.ContainsKey($m.Groups[1].Value)) { "$($file.Name): $($m.Groups[1].Value)" }
            }
        }
        @($missing | Sort-Object -Unique) | Should -BeNullOrEmpty -Because 'an unlisted token logs an error each time its text is worked out (Engine Facts X24)'
    }
}

Describe 'Texts of the mod' {
    It 'exist for every key a container of the mod shows' {
        $locDir = Join-Path $script:RepoRoot 'localisation'
        $keys = @{}
        if (Test-Path $locDir) {
            foreach ($file in @(Get-ChildItem -Path $locDir -Recurse -File -Filter '*_l_english.yml')) {
                foreach ($m in [regex]::Matches([System.IO.File]::ReadAllText($file.FullName), '(?m)^\s*([A-Za-z0-9_]+):\d*\s*"')) { $keys[$m.Groups[1].Value] = $true }
            }
        }
        $missing = foreach ($file in @(Get-ChildItem -Path (Join-Path $script:RepoRoot 'interface') -Recurse -File -Filter "$($script:Prefix)*.gui")) {
            foreach ($m in [regex]::Matches([System.IO.File]::ReadAllText($file.FullName), '"(MOD1440_[A-Z0-9_]+)"')) {
                if (-not $keys.ContainsKey($m.Groups[1].Value)) { "$($file.Name): $($m.Groups[1].Value)" }
            }
        }
        @($missing | Sort-Object -Unique) | Should -BeNullOrEmpty
    }
}
