# Checks that need the scene files (tools/scenes/*.json) and the game's fonts. They sit apart from
# GuiInvariants.Tests.ps1 so that the generic parser tests stay independent of the page descriptions. This mod
# keeps no baseline/ folder (it overrides no vanilla window): every shortcut of its windows counts as added.

BeforeAll {
    $script:RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
    . (Join-Path (Join-Path $script:RepoRoot 'tools') 'GuiParsing.ps1')

    $script:InterfaceDir = Join-Path $script:RepoRoot 'interface'
    $script:BaselineDir = Join-Path $script:RepoRoot 'baseline'
    $script:SceneDir = Join-Path (Join-Path $script:RepoRoot 'tools') 'scenes'
    $script:GameDir = Resolve-HoiGameDir

    function Get-ModGuiFiles {
        if (-not (Test-Path $script:InterfaceDir)) { return }
        Get-ChildItem -Path $script:InterfaceDir -Recurse -File -Filter '*.gui'
    }

    function Get-ModWindows {
        return @(Get-GuiModWindows -InterfaceDir $script:InterfaceDir)
    }

    function Get-Scenes {
        foreach ($sceneFile in @(Get-ChildItem -Path $script:SceneDir -Filter '*.json' -ErrorAction SilentlyContinue)) {
            Get-GuiScene -Name $sceneFile.FullName
        }
    }

    function Get-Shortcuts {
        param($Node, [string]$Window)
        foreach ($block in @(Get-GuiNodes -Node $Node)) {
            foreach ($child in $block.Children) {
                if ($null -eq $child.Children -and $child.Key -ieq 'shortcut' -and $child.Value) {
                    [pscustomobject]@{ Key = $child.Value.ToLowerInvariant(); Widget = "$Window/$(Get-GuiValue -Node $block -Key 'name')" }
                }
            }
        }
    }
}

Describe 'Variables' {
    It 'defines in the override file every @variable its windows use' {
        # a file-level @variable of a vanilla file does not travel with an overridden window (Engine Facts L6)
        $undefined = foreach ($file in @(Get-ModGuiFiles)) {
            $use = Get-GuiVariableUse -Path $file.FullName
            foreach ($name in $use.Undefined) { "$($file.Name): $name" }
        }
        $undefined | Should -BeNullOrEmpty
    }
}

Describe 'Texts' {
    BeforeAll {
        # Every text box or button caption of the mod whose text is known: a scene sample, a literal, or a
        # vanilla localisation key without variables. Measured with the real font against maxWidth (Engine Facts W11).
        # A sample is one text, or a list with one text per drawn instance (the rows of a grid). The states of
        # a scene (its captures and render-only states) may bring samples of their own. A text the design
        # knowingly cuts off is listed under the scene's "knownCuts" and is not judged here.
        $samples = @{}
        $knownCuts = [System.Collections.Generic.HashSet[string]]::new()
        foreach ($scene in @(Get-Scenes)) {
            $tables = @($scene.samples) + @(@($scene.captures) + @($scene.states) | Where-Object { $_ -and $_.samples } | ForEach-Object { $_.samples })
            foreach ($table in $tables) {
                if (-not $table) { continue }
                foreach ($windowName in @($table.PSObject.Properties.Name)) {
                    foreach ($prop in @($table.$windowName.PSObject.Properties)) {
                        $key = "$windowName/$($prop.Name)"
                        if (-not $samples.ContainsKey($key)) { $samples[$key] = [System.Collections.Generic.List[string]]::new() }
                        foreach ($value in @($prop.Value)) { if (-not $samples[$key].Contains([string]$value)) { $samples[$key].Add([string]$value) } }
                    }
                }
            }
            foreach ($cut in @($scene.knownCuts)) { if ($cut) { [void]$knownCuts.Add("$($cut.widget)|$($cut.text)") } }
        }
        $keys = [System.Collections.Generic.HashSet[string]]::new()
        $boxes = @()
        foreach ($window in @(Get-ModWindows)) {
            foreach ($node in @(Get-GuiNodes -Node $window.Node)) {
                $type = $node.Key.ToLowerInvariant()
                if ($type -notin @('instanttextboxtype', 'textboxtype', 'buttontype', 'guibuttontype')) { continue }
                $font = Get-GuiValue -Node $node -Key 'font'
                if (-not $font) { $font = Get-GuiValue -Node $node -Key 'buttonFont' }
                $maxWidth = ConvertTo-GuiNumber (Get-GuiValue -Node $node -Key 'maxWidth')
                if ($null -eq $maxWidth) { $maxWidth = Get-GuiWidth -Node $node }
                if (-not $font -or -not $maxWidth) { continue }
                $maxHeight = ConvertTo-GuiNumber (Get-GuiValue -Node $node -Key 'maxHeight')
                if ($null -eq $maxHeight) { $maxHeight = Get-GuiHeight -Node $node }
                $literal = Get-GuiValue -Node $node -Key 'text'
                if (-not $literal) { $literal = Get-GuiValue -Node $node -Key 'buttonText' }
                $boxes += [pscustomobject]@{ Window = $window.Name; Widget = (Get-GuiValue -Node $node -Key 'name'); Font = $font; MaxWidth = $maxWidth; MaxHeight = $maxHeight; Literal = $literal; File = $window.File; Line = $node.Line }
                if ($literal -and $literal -cmatch '^[A-Z][A-Z0-9_]+$') { [void]$keys.Add($literal) }
            }
        }
        # resolve the vanilla keys in one pass over the English localisation
        $loc = @{}
        if ($script:GameDir -and $keys.Count) {
            $pattern = '^\s*(' + (($keys | ForEach-Object { [regex]::Escape($_) }) -join '|') + '):\d*\s*"(.*)"'
            foreach ($hit in (Select-String -Path (Join-Path $script:GameDir 'localisation\english\*.yml') -Pattern $pattern)) {
                $loc[$hit.Matches[0].Groups[1].Value] = $hit.Matches[0].Groups[2].Value
            }
        }
        # the mod's own texts (the captions of its scripted GUIs) are judged the same way
        $modLoc = Join-Path $script:RepoRoot 'localisation\english'
        if (Test-Path $modLoc) {
            foreach ($hit in (Select-String -Path (Join-Path $modLoc '*.yml') -Pattern '^\s*([A-Z][A-Z0-9_]+):\d*\s*"(.*)"')) {
                $loc[$hit.Matches[0].Groups[1].Value] = $hit.Matches[0].Groups[2].Value
            }
        }
        $colorCode = [string][char]0xA7 + '[A-Za-z0-9!]'
        $script:TextCases = @()
        foreach ($box in $boxes) {
            $texts = @()
            $source = $null
            $sampleKey = "$($box.Window)/$($box.Widget)"
            if ($samples.ContainsKey($sampleKey)) { $texts = @($samples[$sampleKey]); $source = 'sample' }
            elseif ($box.Literal -and $loc.ContainsKey($box.Literal)) { $texts = @($loc[$box.Literal]); $source = 'localisation' }
            elseif ($box.Literal -and $box.Literal -cnotmatch '^[A-Z][A-Z0-9_]+$') { $texts = @($box.Literal); $source = 'literal' }
            foreach ($text in $texts) {
                if (-not $text) { continue }
                if ($text.Contains('$') -or $text.Contains('[')) { continue }   # dynamic text, length unknown
                if ($knownCuts.Contains("$sampleKey|$text")) { continue }
                $text = $text -replace $colorCode, ''
                $script:TextCases += [pscustomobject]@{ Where = "$($box.File):$($box.Line) $($box.Window)/$($box.Widget)"; Text = $text; Font = $box.Font; MaxWidth = $box.MaxWidth; MaxHeight = $box.MaxHeight; Source = $source }
            }
        }
    }

    It 'fit their box in their font: one line in maxWidth, or wrapped into the lines maxHeight holds' {
        if (-not $script:GameDir) { Set-ItResult -Skipped -Because 'the fonts live in the game install'; return }
        $tooWide = foreach ($case in $script:TextCases) {
            $lineHeight = Get-GuiFontLineHeight -Font $case.Font
            if ($null -eq $lineHeight) { continue }
            $linesAllowed = 1
            if ($case.MaxHeight -and $lineHeight -gt 0) { $linesAllowed = [Math]::Max(1, [Math]::Floor($case.MaxHeight / $lineHeight)) }
            # greedy word wrap, the way the game fills a box that holds more than one line (Engine Facts W10)
            $lines = 0
            $overflow = $null
            # the game draws a text icon (a pound sign and a name) as a small picture and a colour code (a section
            # sign and a letter) not at all; the signs are written as numbers here, because this file is ASCII
            $shown = $case.Text -replace ([string][char]0xA7 + '[A-Za-z!]'), '' -replace ([string][char]0xA3 + '\w+'), 'MM'
            foreach ($paragraph in ($shown -split '\\n|\n')) {
                $current = ''
                foreach ($word in ($paragraph -split ' ')) {
                    $trial = if ($current) { "$current $word" } else { $word }
                    if ((Measure-GuiText -Font $case.Font -Text $trial) -le $case.MaxWidth -or -not $current) {
                        $current = $trial
                    } else {
                        $lines++
                        $current = $word
                    }
                    if ((Measure-GuiText -Font $case.Font -Text $current) -gt $case.MaxWidth) { $overflow = $current }
                }
                $lines++
            }
            if ($overflow) { "$($case.Where): '$overflow' is $(Measure-GuiText -Font $case.Font -Text $overflow) px in $($case.Font), maxWidth $($case.MaxWidth) ($($case.Source))" }
            elseif ($lines -gt $linesAllowed) { "$($case.Where): '$($case.Text)' needs $lines lines of $lineHeight px in $($case.Font); maxHeight $($case.MaxHeight) holds $linesAllowed ($($case.Source))" }
        }
        $tooWide | Should -BeNullOrEmpty -Because 'the game cuts off text that does not fit its box (Engine Facts W10); widen the box or shorten the sample'
    }
}

Describe 'Hotkeys' {
    It 'adds no shortcut that another button of the same screen or of the vanilla file already uses' {
        # keys added by the mod, compared with every other shortcut in the same scene and in the vanilla
        # file the window comes from (Engine Facts W5, W7)
        $sceneOf = @{}
        # a window drawn only in some states of its scene (drawIn) is never on the screen together with a window
        # drawn in none of those states: a handle shown while its page is closed and the page's close button may share a key
        $drawIn = @{}
        $links = Get-GuiLinks
        foreach ($scene in @(Get-Scenes)) {
            foreach ($w in @($scene.windows)) {
                $sceneOf[$w.name] = $scene.screen
                if ($null -ne $w.drawIn) { $drawIn[$w.name] = @($w.drawIn | ForEach-Object { [string]$_ }) }
            }
        }
        function Test-DrawnTogether {
            param([string]$A, [string]$B)
            if (-not $drawIn.ContainsKey($A) -or -not $drawIn.ContainsKey($B)) { return $true }
            foreach ($s in $drawIn[$A]) { if ($drawIn[$B] -contains $s) { return $true } }
            return $false
        }
        foreach ($pair in @($links.ListRows)) {
            if ($sceneOf.ContainsKey($pair.listWindow) -and -not $sceneOf.ContainsKey($pair.row)) { $sceneOf[$pair.row] = $sceneOf[$pair.listWindow] }
        }
        $all = @()
        $added = @()
        $vanillaFiles = @{}
        foreach ($window in @(Get-ModWindows)) {
            $scene = $sceneOf[$window.Name]
            $mine = @(Get-Shortcuts -Node $window.Node -Window $window.Name)
            foreach ($s in $mine) { $all += [pscustomobject]@{ Key = $s.Key; Widget = $s.Widget; Scene = $scene; Window = $window.Name } }
            # a window of the mod's own has no baseline: every one of its shortcuts is added
            $baseline = Find-GuiBaseline -BaselineDir $script:BaselineDir -Name $window.Name
            $vanilla = @()
            if ($baseline) { $vanilla = @(Get-Shortcuts -Node $baseline.Node -Window $window.Name) }
            foreach ($s in $mine) {
                if (-not ($vanilla | Where-Object { $_.Key -eq $s.Key -and $_.Widget -eq $s.Widget })) {
                    $source = if ($baseline) { $baseline.Source } else { $null }
                    $added += [pscustomobject]@{ Key = $s.Key; Widget = $s.Widget; Scene = $scene; Source = $source; Window = $window.Name }
                    if ($source) { $vanillaFiles[$source] = $true }
                }
            }
        }
        $vanillaKeys = @()
        if ($script:GameDir) {
            foreach ($rel in $vanillaFiles.Keys) {
                $path = Join-Path $script:GameDir ($rel -replace '/', '\')
                if (-not (Test-Path -LiteralPath $path)) { continue }
                $root = ConvertFrom-GuiText -Text (Read-GuiText -Path $path)
                foreach ($window in @(Get-GuiTopLevelWindows -Root $root)) {
                    foreach ($s in @(Get-Shortcuts -Node $window.Node -Window $window.Name)) { $vanillaKeys += [pscustomobject]@{ Key = $s.Key; Widget = $s.Widget; Source = $rel } }
                }
            }
        }
        $collisions = foreach ($a in $added) {
            foreach ($other in $all) {
                if ($other.Widget -ne $a.Widget -and $other.Key -eq $a.Key -and $a.Scene -and $other.Scene -eq $a.Scene -and (Test-DrawnTogether -A $a.Window -B $other.Window)) { "$($a.Widget) added '$($a.Key)', also on $($other.Widget) in scene $($a.Scene)" }
            }
            foreach ($v in $vanillaKeys) {
                if ($v.Source -eq $a.Source -and $v.Key -eq $a.Key -and $v.Widget -ne $a.Widget) { "$($a.Widget) added '$($a.Key)', also on vanilla $($v.Widget) in $($v.Source)" }
            }
        }
        @($collisions | Sort-Object -Unique) | Should -BeNullOrEmpty
    }

    It 'gives every hotkey the mod adds the key of its action in the shared table (tools/hotkeys.json)' {
        # wiki/Design-Language.md, Hotkeys (user decision 2026-10-21): one key per action on every screen, one action per key
        $table = Get-Content -LiteralPath (Join-Path (Join-Path $script:RepoRoot 'tools') 'hotkeys.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        $always = @($table.always.PSObject.Properties.Name | ForEach-Object { $_.ToLowerInvariant() })
        $pattern = '\bshortcut\s*=\s*"?([^"\s}]+)"?'
        function Get-KeyedButtons([string]$Path) {
            $text = [regex]::Replace([System.IO.File]::ReadAllText($Path), '#[^\r\n]*', '')
            foreach ($m in [regex]::Matches($text, $pattern)) {
                $names = [regex]::Matches($text.Substring(0, $m.Index), 'name\s*=\s*"([^"]+)"')
                if ($names.Count) { [pscustomobject]@{ Button = $names[$names.Count - 1].Groups[1].Value; Key = $m.Groups[1].Value.ToLowerInvariant() } }
            }
        }
        $vanilla = @{}
        foreach ($file in @(Get-ChildItem -Path $script:BaselineDir -Recurse -File -Filter '*.gui' -ErrorAction SilentlyContinue)) {
            foreach ($b in @(Get-KeyedButtons $file.FullName)) { $vanilla["$($b.Button)|$($b.Key)"] = $true }
        }
        $added = @{}
        foreach ($file in @(Get-ModGuiFiles)) {
            foreach ($b in @(Get-KeyedButtons $file.FullName)) {
                if ($always -contains $b.Key -or $vanilla.ContainsKey("$($b.Button)|$($b.Key)")) { continue }
                $added["$($file.Name):$($b.Button)"] = $b.Key
            }
        }
        $listed = @{}
        $problems = @()
        foreach ($a in @($table.actions)) {
            if ($a.key -notmatch '^shift\+[a-z]$') { $problems += "the action '$($a.action)' has '$($a.key)'; an added hotkey is shift+letter" }
            foreach ($id in @($a.buttons)) {
                $listed[$id] = $a.key
                if (-not $added.ContainsKey($id)) { $problems += "$id is listed under '$($a.action)' but carries no added hotkey" }
                elseif ($added[$id] -ne $a.key) { $problems += "$id has '$($added[$id])'; its action '$($a.action)' has '$($a.key)'" }
            }
        }
        foreach ($id in $added.Keys) {
            if (-not $listed.ContainsKey($id)) { $problems += "$id adds '$($added[$id])' and is not in tools/hotkeys.json" }
        }
        foreach ($dup in @($table.actions | Group-Object key | Where-Object Count -gt 1)) { $problems += "'$($dup.Name)' is the key of $($dup.Count) actions" }
        @($problems | Sort-Object) | Should -BeNullOrEmpty
    }
}

Describe 'Localisation' {
    It 'has UTF-8 with BOM .yml files only, and build.ps1 packages the folder' {
        $locDir = Join-Path $script:RepoRoot 'localisation'
        $buildText = [System.IO.File]::ReadAllText((Join-Path $script:RepoRoot 'build.ps1'))
        $buildText | Should -Not -Match "'localisation'" -Because 'Copy-ModContent must not exclude the folder'
        if (-not (Test-Path $locDir)) { return }
        $problems = foreach ($file in (Get-ChildItem -Path $locDir -Recurse -File)) {
            if ($file.Extension -ne '.yml') { "$($file.Name): not a .yml file"; continue }
            $bytes = [System.IO.File]::ReadAllBytes($file.FullName)
            if (-not ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF)) { "$($file.Name): no UTF-8 BOM (the game needs one here, unlike .gui files)" }
        }
        $problems | Should -BeNullOrEmpty
    }
}

Describe 'Screen heights' {
    It 'keeps every docked window of a scene above the bottom bar (y 1140)' {
        # Engine Facts S15: a panel docked top left may run down to about y 1130; A1's accepted maxima end at 1139
        $windows = @{}
        foreach ($w in @(Get-ModWindows)) { $windows[$w.Name] = $w }
        $tooLow = foreach ($scene in @(Get-Scenes)) {
            foreach ($w in @($scene.windows)) {
                if (-not $w.at -or -not $windows.ContainsKey($w.name)) { continue }
                # a side panel of a top bar tab runs down the whole screen in vanilla and covers the left end
                # of the bottom bar by design; the scene marks it
                if ($w.sidePanel) { continue }
                $node = $windows[$w.name].Node
                $orientation = [string](Get-GuiValue -Node $node -Key 'orientation')
                if ($orientation -and $orientation -notmatch '(?i)upper_left') { continue }
                $height = if ($w.height) { [double]$w.height } else { Get-GuiHeight -Node $node }
                # a window of the mod's own in the middle of the screen (the Records) may run down to the army
                # portraits of the bottom bar, which start at y 1320; the scene marks it
                $limit = if ($w.freeWindow) { 1320 } else { 1140 }
                if ($height -and ([double]$w.at[1] + $height) -gt $limit) { "$($scene.screen)/$($w.name): bottom at $([double]$w.at[1] + $height), limit $limit" }
            }
        }
        $tooLow | Should -BeNullOrEmpty
    }

}

Describe 'Game recipes' {
    BeforeAll {
        # Every step of every scene and move, flattened: what a game check would run (wiki/Game-Recipes.md).
        $script:MovesPath = Join-Path (Join-Path $script:RepoRoot 'tools') 'moves.json'
        $script:Moves = @{}
        foreach ($prop in ([System.IO.File]::ReadAllText($script:MovesPath, [System.Text.Encoding]::UTF8) | ConvertFrom-Json).moves.PSObject.Properties) { $script:Moves[$prop.Name] = $prop.Value }
        $script:StepKinds = @('key', 'clickWidget', 'dragWidget', 'move', 'click', 'rightClick', 'drag', 'console')

        function Get-RecipeSteps {
            param($Steps, [string]$Where, [string]$Scene, [int]$Depth = 0)
            foreach ($step in @($Steps)) {
                if ($null -eq $step) { continue }
                [pscustomobject]@{ Step = $step; Where = $Where; Scene = $Scene }
                if ($step.move -and $script:Moves.ContainsKey([string]$step.move) -and $Depth -lt 8) {
                    Get-RecipeSteps -Steps $script:Moves[[string]$step.move].steps -Where "$Where > $($step.move)" -Scene $Scene -Depth ($Depth + 1)
                }
            }
        }

        $script:AllSteps = @()
        foreach ($scene in @(Get-Scenes)) {
            $script:AllSteps += @(Get-RecipeSteps -Steps $scene.setup -Where "$($scene.screen) setup" -Scene $scene.screen)
            foreach ($capture in @($scene.captures)) {
                if ($capture) { $script:AllSteps += @(Get-RecipeSteps -Steps $capture.steps -Where "$($scene.screen) capture $($capture.name)" -Scene $scene.screen) }
            }
            $script:AllSteps += @(Get-RecipeSteps -Steps $scene.teardown -Where "$($scene.screen) teardown" -Scene $scene.screen)
        }
        foreach ($name in $script:Moves.Keys) {
            $script:AllSteps += @(Get-RecipeSteps -Steps $script:Moves[$name].steps -Where "move $name" -Scene $null)
        }
    }

    It 'uses only known step kinds, with well-formed values' {
        $problems = foreach ($item in $script:AllSteps) {
            $names = @($item.Step.PSObject.Properties.Name | Where-Object { $_ -notin @('wait', '_note', 'scene', 'state', 'offset', 'button') })
            $kinds = @($names | Where-Object { $script:StepKinds -contains $_ })
            $unknown = @($names | Where-Object { $script:StepKinds -notcontains $_ })
            if ($unknown.Count) { "$($item.Where): unknown key '$($unknown -join ', ')'" }
            if ($kinds.Count -gt 1) { "$($item.Where): more than one action in a step ($($kinds -join ', '))" }
            if (-not $kinds.Count -and -not $item.Step.wait) { "$($item.Where): a step without an action" }
            foreach ($pair in @(@('click', 2), @('rightClick', 2), @('drag', 4), @('dragWidget', 2))) {
                $value = $item.Step.($pair[0])
                if ($null -ne $value -and @($value).Count -ne $pair[1]) { "$($item.Where): $($pair[0]) needs $($pair[1]) values" }
            }
            foreach ($position in @($item.Step.click, $item.Step.rightClick)) {
                if ($position -and ([int]$position[0] -lt 0 -or [int]$position[0] -ge 2560 -or [int]$position[1] -lt 0 -or [int]$position[1] -ge 1440)) { "$($item.Where): position $($position -join ',') is off a 2560x1440 screen" }
            }
        }
        @($problems | Sort-Object -Unique) | Should -BeNullOrEmpty
    }

    It 'names only moves that tools/moves.json defines' {
        $missing = foreach ($item in $script:AllSteps) {
            if ($item.Step.move -and -not $script:Moves.ContainsKey([string]$item.Step.move)) { "$($item.Where): move '$($item.Step.move)'" }
        }
        @($missing | Sort-Object -Unique) | Should -BeNullOrEmpty
    }

    It 'gives every scene a recipe' {
        $empty = foreach ($scene in @(Get-Scenes)) { if (-not @($scene.setup).Count) { $scene.screen } }
        $empty | Should -BeNullOrEmpty -Because 'a scene without setup captures an empty map; write its recipe (wiki/Game-Recipes.md)'
    }

    It 'finds every widget a recipe clicks or expects, in the modded and in the vanilla layout' {
        $python = (Get-Command python -ErrorAction SilentlyContinue).Source
        if (-not $python -or -not $script:GameDir) { Set-ItResult -Skipped -Because 'the layout needs Python with Pillow and the game install'; return }
        & $python -I -c 'import PIL' 2>$null
        if ($LASTEXITCODE -ne 0) { Set-ItResult -Skipped -Because 'Pillow is not installed'; return }

        # scene (and the state of it a step names, after a "|") -> the widget specs laid out with it
        $wanted = @{}
        foreach ($item in $script:AllSteps) {
            $specs = @($item.Step.clickWidget) + @($item.Step.dragWidget) | Where-Object { $_ }
            if (-not $specs) { continue }
            $sceneName = if ($item.Step.scene) { [string]$item.Step.scene } else { $item.Scene }
            if (-not $sceneName) { "$($item.Where): clickWidget in a shared move needs a 'scene'" | Should -BeNullOrEmpty; continue }
            $layout = "$sceneName|$($item.Step.state)"
            if (-not $wanted.ContainsKey($layout)) { $wanted[$layout] = [System.Collections.Generic.HashSet[string]]::new() }
            foreach ($spec in $specs) { [void]$wanted[$layout].Add([string]$spec) }
        }
        foreach ($scene in @(Get-Scenes)) {
            foreach ($spec in @($scene.expect)) {
                if (-not $spec) { continue }
                if (-not $wanted.ContainsKey("$($scene.screen)|")) { $wanted["$($scene.screen)|"] = [System.Collections.Generic.HashSet[string]]::new() }
                [void]$wanted["$($scene.screen)|"].Add([string]$spec)
            }
        }
        # a page of the mod's own (a scripted GUI) has no vanilla layout: its scene says "modOnly"
        $modOnly = @{}
        foreach ($scene in @(Get-Scenes)) { if ($scene.modOnly) { $modOnly[[string]$scene.screen] = $true } }
        # every layout in one render_gui.py --batch run: the textures, fonts and indexes load once
        $renderPy = Join-Path (Join-Path $script:RepoRoot 'tools') 'render_gui.py'
        $jobs = [System.Collections.Generic.List[object]]::new()
        foreach ($layout in $wanted.Keys) {
            $sceneName, $state = $layout -split '\|', 2
            $modes = if ($modOnly.ContainsKey($sceneName)) { @('') } else { @('', '--vanilla') }
            foreach ($mode in $modes) {
                $arguments = @('--scene', $sceneName, '--locate') + @($wanted[$layout])
                if ($state) { $arguments += '--state'; $arguments += $state }
                if ($mode) { $arguments += $mode }
                $jobs.Add(@{ id = "$layout|$mode"; args = $arguments })
            }
        }
        $results = Invoke-GuiRenderBatch -Python $python -RenderPy $renderPy -Jobs $jobs -JobsPath (Join-Path (Join-Path (Join-Path $script:RepoRoot 'scratch') 'test-renders') 'locate-jobs.json')
        $notFound = foreach ($job in $jobs) {
            $sceneName, $state, $mode = $job.id -split '\|', 3
            $label = if ($mode) { 'vanilla' } else { 'mod' }
            $result = $results[$job.id]
            if (-not $result) { "$($job.id): no result from the render batch (exit $($results['*'].Exit))"; continue }
            foreach ($line in @($result.Output | Where-Object { $_ -like "LOCATE`t*NOTFOUND" })) {
                "$sceneName$(if ($state) { " in state $state" }) ($label): $(($line -split "`t")[1])"
            }
        }
        @($notFound) | Should -BeNullOrEmpty -Because 'a click on a widget the layout does not contain cannot be aimed; check the window/widget names and the scene windows'
    }
}
