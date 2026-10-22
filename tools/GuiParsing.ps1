# Shared Clausewitz GUI parsing helpers for the tools in this folder and the Pester suites.
# Dot-source this file; it only defines functions. Keep it ASCII and Windows PowerShell 5.1 compatible.

function Resolve-HoiGameDir {
    param([string]$GameDir)

    $candidates = [System.Collections.Generic.List[string]]::new()
    if ($GameDir) { $candidates.Add($GameDir) }
    if ($env:HOI4_GAME_DIR) { $candidates.Add($env:HOI4_GAME_DIR) }

    $steamRoots = [System.Collections.Generic.List[string]]::new()
    try {
        $steamPath = (Get-ItemProperty -Path 'HKCU:\Software\Valve\Steam' -ErrorAction Stop).SteamPath
        if ($steamPath) { $steamRoots.Add(($steamPath -replace '/', '\')) }
    } catch { }
    $steamRoots.Add('C:\Program Files (x86)\Steam')

    foreach ($root in @($steamRoots)) {
        $vdf = Join-Path $root 'steamapps\libraryfolders.vdf'
        if (Test-Path -LiteralPath $vdf) {
            foreach ($m in [regex]::Matches([System.IO.File]::ReadAllText($vdf), '"path"\s+"([^"]+)"')) {
                $steamRoots.Add(($m.Groups[1].Value -replace '\\\\', '\'))
            }
        }
    }
    foreach ($root in $steamRoots) {
        $candidates.Add((Join-Path $root 'steamapps\common\Hearts of Iron IV'))
    }

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath (Join-Path $candidate 'interface'))) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }
    return $null
}

function Read-GuiText {
    param([Parameter(Mandatory)][string]$Path)

    $bytes = [System.IO.File]::ReadAllBytes($Path)
    $offset = 0
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) { $offset = 3 }
    try {
        return [System.Text.UTF8Encoding]::new($false, $true).GetString($bytes, $offset, $bytes.Length - $offset)
    } catch {
        # Some vanilla files carry Windows-1252 bytes in comments.
        return [System.Text.Encoding]::GetEncoding(28591).GetString($bytes, $offset, $bytes.Length - $offset)
    }
}

function Test-GuiFileSyntax {
    param([Parameter(Mandatory)][string]$Path)

    $problems = [System.Collections.Generic.List[string]]::new()
    $bytes = [System.IO.File]::ReadAllBytes($Path)
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        $problems.Add('UTF-8 BOM detected')
    }

    $cleanText = [regex]::Replace((Read-GuiText -Path $Path), '#[^\r\n]*', '')
    $openCount = ([regex]::Matches($cleanText, '\{')).Count
    $closeCount = ([regex]::Matches($cleanText, '\}')).Count
    if ($openCount -ne $closeCount) { $problems.Add("Bracket mismatch (open $openCount, close $closeCount)") }

    $quoteCount = ([regex]::Matches($cleanText, '"')).Count
    if ($quoteCount % 2 -ne 0) { $problems.Add("Unbalanced double quotes ($quoteCount found)") }

    return $problems
}

# Parses Clausewitz script into a tree. A block node has Children (a list); a key = value leaf has
# Children = $null. Line and EndLine are 1-based line numbers of the key and of the closing brace.
function ConvertFrom-GuiText {
    param([Parameter(Mandatory)][AllowEmptyString()][string]$Text)

    $lineStarts = [System.Collections.Generic.List[int]]::new()
    $lineStarts.Add(0)
    foreach ($newline in [regex]::Matches($Text, "\n")) { $lineStarts.Add($newline.Index + 1) }

    $root = [pscustomobject]@{ Key = ''; Value = $null; Children = [System.Collections.Generic.List[object]]::new(); Line = 1; EndLine = $lineStarts.Count }
    $stack = [System.Collections.Generic.Stack[object]]::new()
    $stack.Push($root)
    $pendingKey = $null
    $pendingLine = 0
    $expectValue = $false

    foreach ($match in [regex]::Matches($Text, '#[^\r\n]*|"[^"]*"|[{}=]|[^\s{}=#"]+')) {
        $token = $match.Value
        if ($token.StartsWith('#')) { continue }

        $lineIndex = $lineStarts.BinarySearch($match.Index)
        if ($lineIndex -lt 0) { $lineIndex = (-bnot $lineIndex) - 1 }
        $line = $lineIndex + 1
        $current = $stack.Peek()

        if ($token -eq '{') {
            $key = ''
            $keyLine = $line
            if ($expectValue) {
                $key = $pendingKey
                $keyLine = $pendingLine
            } elseif ($null -ne $pendingKey) {
                $current.Children.Add([pscustomobject]@{ Key = $pendingKey; Value = $null; Children = $null; Line = $pendingLine; EndLine = $pendingLine })
            }
            $node = [pscustomobject]@{ Key = $key; Value = $null; Children = [System.Collections.Generic.List[object]]::new(); Line = $keyLine; EndLine = $keyLine }
            $current.Children.Add($node)
            $stack.Push($node)
            $pendingKey = $null
            $expectValue = $false
        } elseif ($token -eq '}') {
            if ($null -ne $pendingKey) {
                $current.Children.Add([pscustomobject]@{ Key = $pendingKey; Value = $null; Children = $null; Line = $pendingLine; EndLine = $pendingLine })
            }
            $pendingKey = $null
            $expectValue = $false
            if ($stack.Count -gt 1) {
                $closed = $stack.Pop()
                $closed.EndLine = $line
            }
        } elseif ($token -eq '=') {
            $expectValue = $true
        } else {
            $value = $token
            if ($value.Length -ge 2 -and $value.StartsWith('"')) { $value = $value.Substring(1, $value.Length - 2) }
            if ($expectValue) {
                $current.Children.Add([pscustomobject]@{ Key = $pendingKey; Value = $value; Children = $null; Line = $pendingLine; EndLine = $line })
                $pendingKey = $null
                $expectValue = $false
            } else {
                if ($null -ne $pendingKey) {
                    $current.Children.Add([pscustomobject]@{ Key = $pendingKey; Value = $null; Children = $null; Line = $pendingLine; EndLine = $pendingLine })
                }
                $pendingKey = $value
                $pendingLine = $line
            }
        }
    }

    return $root
}

function Get-GuiValue {
    param($Node, [string]$Key)

    if ($null -eq $Node -or $null -eq $Node.Children) { return $null }
    foreach ($child in $Node.Children) {
        if ($null -eq $child.Children -and $child.Key -ieq $Key) { return $child.Value }
    }
    return $null
}

function Get-GuiBlock {
    param($Node, [string]$Key)

    if ($null -eq $Node -or $null -eq $Node.Children) { return $null }
    foreach ($child in $Node.Children) {
        if ($null -ne $child.Children -and $child.Key -ieq $Key) { return $child }
    }
    return $null
}

function ConvertTo-GuiNumber {
    param([string]$Value)

    if ($Value -match '^-?\d+(\.\d+)?$') {
        return [double]::Parse($Value, [System.Globalization.CultureInfo]::InvariantCulture)
    }
    return $null
}

# Every block at or below $Node, parents before children.
function Get-GuiNodes {
    param([Parameter(Mandatory)]$Node)

    $stack = [System.Collections.Generic.Stack[object]]::new()
    $stack.Push($Node)
    while ($stack.Count -gt 0) {
        $current = $stack.Pop()
        $current
        for ($i = $current.Children.Count - 1; $i -ge 0; $i--) {
            if ($null -ne $current.Children[$i].Children) { $stack.Push($current.Children[$i]) }
        }
    }
}

function Get-GuiTopLevelWindows {
    param([Parameter(Mandatory)]$Root)

    foreach ($section in $Root.Children) {
        if ($null -eq $section.Children -or $section.Key -ine 'guiTypes') { continue }
        foreach ($child in $section.Children) {
            if ($null -eq $child.Children) { continue }
            $name = Get-GuiValue -Node $child -Key 'name'
            if ($name) {
                [pscustomobject]@{ Name = $name; Type = $child.Key; Node = $child; Line = $child.Line; EndLine = $child.EndLine }
            }
        }
    }
}

# One "parent/child/name|type" entry (lower case) per named block at or below $Node.
# The engine finds widgets by name inside their parent, so both the name and the nesting matter. A container whose
# name starts with $WrapperPrefix is left out of the paths: it is one the mod put around vanilla widgets. With
# -WrappedOnly only the widgets inside such a container are listed.
function Get-GuiWidgetPaths {
    param([Parameter(Mandatory)]$Node, [string]$WrapperPrefix, [switch]$WrappedOnly)

    $stack = [System.Collections.Generic.Stack[object]]::new()
    $stack.Push(@($Node, '', $false))
    while ($stack.Count -gt 0) {
        $item = $stack.Pop()
        $current = $item[0]
        $prefix = $item[1]
        $wrapped = $item[2]
        $name = Get-GuiValue -Node $current -Key 'name'
        if ($name -and $WrapperPrefix -and $prefix -and $current.Key -ieq 'containerWindowType' -and $name -like "$WrapperPrefix*") {
            $wrapped = $true
        }
        elseif ($name) {
            if ($prefix) { $prefix = "$prefix/$name" } else { $prefix = $name }
            if ($wrapped -or -not $WrappedOnly) { ('{0}|{1}' -f $prefix, $current.Key).ToLowerInvariant() }
        }
        foreach ($child in $current.Children) {
            if ($null -ne $child.Children) { $stack.Push(@($child, $prefix, $wrapped)) }
        }
    }
}

# Widget paths present in $Baseline but missing from $Actual. With $WrapperPrefix a vanilla widget inside containers
# the mod added counts as present at its vanilla path, as the game finds it once the Modding Manager's
# Scripts\Executable\Set-HoiRecursiveLookups.ps1 has patched hoi4.exe. The patch covers the element types below; a
# wrapped widget of another type (scrollbar, list box, browser, position) is still looked up among the direct
# children only, and is reported with " (wrapped)".
function Compare-GuiWidgetPaths {
    param([Parameter(Mandatory)]$Baseline, [Parameter(Mandatory)]$Actual, [string]$WrapperPrefix)

    $wrappableTypes = @('buttontype', 'guibuttontype', 'icontype', 'instanttextboxtype', 'overlappingelementsboxtype', 'editboxtype', 'checkboxtype', 'smoothlistboxtype', 'containerwindowtype', 'gridboxtype', 'extendedscrollbartype', 'dropdownboxtype')
    $have = [System.Collections.Generic.HashSet[string]]::new()
    foreach ($path in (Get-GuiWidgetPaths -Node $Actual -WrapperPrefix $WrapperPrefix)) { [void]$have.Add($path) }

    $vanilla = [System.Collections.Generic.HashSet[string]]::new()
    $reported = [System.Collections.Generic.HashSet[string]]::new()
    foreach ($path in (Get-GuiWidgetPaths -Node $Baseline)) {
        [void]$vanilla.Add($path)
        if (-not $have.Contains($path) -and $reported.Add($path)) { $path }
    }
    if (-not $WrapperPrefix) { return }
    foreach ($path in (Get-GuiWidgetPaths -Node $Actual -WrapperPrefix $WrapperPrefix -WrappedOnly)) {
        $type = $path.Substring($path.LastIndexOf('|') + 1)
        if ($vanilla.Contains($path) -and $wrappableTypes -notcontains $type -and $reported.Add("$path (wrapped)")) { "$path (wrapped)" }
    }
}

function Add-GuiProperties {
    param($Block, [string]$Widget, [string]$Prefix, $Map, $WidgetCounts)

    $keyCounts = @{}
    foreach ($child in $Block.Children) {
        $childName = $null
        if ($null -ne $child.Children) { $childName = Get-GuiValue -Node $child -Key 'name' }

        if ($childName) {
            $path = "$Widget/$childName"
            $pathKey = $path.ToLowerInvariant()
            $WidgetCounts[$pathKey] = 1 + [int]$WidgetCounts[$pathKey]
            if ($WidgetCounts[$pathKey] -gt 1) { $path = "$path#$($WidgetCounts[$pathKey])" }
            $Map[("$path`t(type)").ToLowerInvariant()] = [pscustomobject]@{ Widget = $path; Property = '(type)'; Value = $child.Key.ToLowerInvariant(); Line = $child.Line }
            Add-GuiProperties -Block $child -Widget $path -Prefix '' -Map $Map -WidgetCounts $WidgetCounts
            continue
        }

        # the name of a widget is already its path
        if ($null -eq $child.Children -and -not $Prefix -and $child.Key -ieq 'name') { continue }

        $key = $child.Key
        $countKey = $key.ToLowerInvariant()
        $keyCounts[$countKey] = 1 + [int]$keyCounts[$countKey]
        if ($keyCounts[$countKey] -gt 1) { $key = "$key#$($keyCounts[$countKey])" }

        if ($null -eq $child.Children) {
            $property = $Prefix + $key
            $Map[("$Widget`t$property").ToLowerInvariant()] = [pscustomobject]@{ Widget = $Widget; Property = $property; Value = [string]$child.Value; Line = $child.Line }
        } else {
            Add-GuiProperties -Block $child -Widget $Widget -Prefix ($Prefix + $key + '.') -Map $Map -WidgetCounts $WidgetCounts
        }
    }
}

# Flattens a window into one entry per property, keyed by widget path and property path.
# A block with a name is a widget. Unnamed blocks (position, size, slotsize ...) are property groups
# of the widget around them, so a value reads like "air_wing_toolbar/btn_close  position.x".
# Repeated keys and repeated widget names get a #2, #3 ... suffix in order of appearance.
function Get-GuiPropertyMap {
    param([Parameter(Mandatory)]$Node)

    $map = [ordered]@{}
    $widget = [string](Get-GuiValue -Node $Node -Key 'name')
    $map[("$widget`t(type)").ToLowerInvariant()] = [pscustomobject]@{ Widget = $widget; Property = '(type)'; Value = $Node.Key.ToLowerInvariant(); Line = $Node.Line }
    Add-GuiProperties -Block $Node -Widget $widget -Prefix '' -Map $map -WidgetCounts @{}
    return $map
}

# Every difference between two versions of a window, one object per changed, added or removed
# property. A widget that exists on one side only is reported once, not property by property.
function Compare-GuiWindows {
    param([Parameter(Mandatory)]$Baseline, [Parameter(Mandatory)]$Actual)

    $old = Get-GuiPropertyMap -Node $Baseline
    $new = Get-GuiPropertyMap -Node $Actual

    $newWidgets = @{}
    foreach ($key in $new.Keys) {
        $entry = $new[$key]
        if ($old.Contains($key)) {
            if ($old[$key].Value -cne $entry.Value) {
                [pscustomobject]@{ Kind = 'Changed'; Widget = $entry.Widget; Property = $entry.Property; Old = $old[$key].Value; New = $entry.Value; Line = $entry.Line }
            }
        } elseif ($entry.Property -eq '(type)') {
            $newWidgets[$entry.Widget] = $true
            [pscustomobject]@{ Kind = 'NewWidget'; Widget = $entry.Widget; Property = '(type)'; Old = $null; New = $entry.Value; Line = $entry.Line }
        } elseif (-not $newWidgets.ContainsKey($entry.Widget)) {
            [pscustomobject]@{ Kind = 'Added'; Widget = $entry.Widget; Property = $entry.Property; Old = $null; New = $entry.Value; Line = $entry.Line }
        }
    }

    $missingWidgets = @{}
    foreach ($key in $old.Keys) {
        if ($new.Contains($key)) { continue }
        $entry = $old[$key]
        if ($entry.Property -eq '(type)') {
            $missingWidgets[$entry.Widget] = $true
            [pscustomobject]@{ Kind = 'MissingWidget'; Widget = $entry.Widget; Property = '(type)'; Old = $entry.Value; New = $null; Line = $null }
        } elseif (-not $missingWidgets.ContainsKey($entry.Widget)) {
            [pscustomobject]@{ Kind = 'Removed'; Widget = $entry.Widget; Property = $entry.Property; Old = $entry.Value; New = $null; Line = $null }
        }
    }
}

# A file parsed once per process: the Pester suites ask for the same 18 files hundreds of times. The key
# carries the write time and the length, so a file edited meanwhile is parsed again.
function Get-GuiParsedFile {
    param([Parameter(Mandatory)][string]$Path)

    if (-not $script:GuiParsedFiles) { $script:GuiParsedFiles = @{} }
    $item = Get-Item -LiteralPath $Path
    $key = "$($item.FullName)|$($item.LastWriteTimeUtc.Ticks)|$($item.Length)"
    if (-not $script:GuiParsedFiles.ContainsKey($key)) {
        $script:GuiParsedFiles[$key] = ConvertFrom-GuiText -Text (Read-GuiText -Path $item.FullName)
    }
    return $script:GuiParsedFiles[$key]
}

# Every top-level window of every .gui file under a folder (the mod's interface/), with the file it is in.
# Built once per process and set of files; a window defined twice is listed twice.
function Get-GuiModWindows {
    param([Parameter(Mandatory)][string]$InterfaceDir)

    if (-not $script:GuiModWindowSets) { $script:GuiModWindowSets = @{} }
    $files = @()
    if (Test-Path -LiteralPath $InterfaceDir) {
        $files = @(Get-ChildItem -LiteralPath $InterfaceDir -Recurse -File -Filter '*.gui' | Sort-Object FullName)
    }
    $key = @($files | ForEach-Object { "$($_.FullName)|$($_.LastWriteTimeUtc.Ticks)|$($_.Length)" }) -join "`n"
    if (-not $script:GuiModWindowSets.ContainsKey($key)) {
        $windows = [System.Collections.Generic.List[object]]::new()
        foreach ($file in $files) {
            $root = Get-GuiParsedFile -Path $file.FullName
            foreach ($window in @(Get-GuiTopLevelWindows -Root $root)) {
                $windows.Add([pscustomobject]@{ Name = $window.Name; Type = $window.Type; Node = $window.Node; File = $file.Name; FullPath = $file.FullName; Line = $window.Line; EndLine = $window.EndLine })
            }
        }
        $script:GuiModWindowSets[$key] = $windows
    }
    return @($script:GuiModWindowSets[$key])
}

# Many render_gui.py calls in one Python process (its --batch mode). $Jobs holds hashtables with an id and
# an args array; the result maps each id to @{ Exit; Output }, and '*' to the whole run.
function Invoke-GuiRenderBatch {
    param(
        [Parameter(Mandatory)][string]$Python,
        [Parameter(Mandatory)][string]$RenderPy,
        [Parameter(Mandatory)]$Jobs,
        [Parameter(Mandatory)][string]$JobsPath
    )

    $jobsDir = Split-Path -Parent $JobsPath
    if (-not (Test-Path -LiteralPath $jobsDir)) { New-Item -ItemType Directory -Path $jobsDir -Force | Out-Null }
    $json = ConvertTo-Json -InputObject @($Jobs) -Depth 4
    [System.IO.File]::WriteAllText($JobsPath, $json, [System.Text.UTF8Encoding]::new($false))

    $lines = @(& $Python -I $RenderPy --batch $JobsPath 2>&1 | ForEach-Object { "$_" })
    $results = @{ '*' = @{ Exit = $LASTEXITCODE; Output = $lines } }
    $current = $null
    foreach ($line in $lines) {
        if ($line -match '^=== JOB (.*) ===$') {
            $current = $Matches[1]
            $results[$current] = @{ Exit = $null; Output = [System.Collections.Generic.List[string]]::new() }
            continue
        }
        if ($line -match '^=== END (.*) exit (-?\d+) ===$') {
            if ($results.ContainsKey($Matches[1])) { $results[$Matches[1]].Exit = [int]$Matches[2] }
            $current = $null
            continue
        }
        if ($current) { $results[$current].Output.Add($line) }
    }
    return $results
}

# The vanilla reference copy of a window, as saved by Export-VanillaBaseline.ps1, or $null. The folder is
# indexed once per process and every baseline parsed once.
function Find-GuiBaseline {
    param([Parameter(Mandatory)][string]$BaselineDir, [Parameter(Mandatory)][string]$Name)

    if (-not (Test-Path -LiteralPath $BaselineDir)) { return $null }
    if (-not $script:GuiBaselineIndex) { $script:GuiBaselineIndex = @{} }
    if (-not $script:GuiBaselines) { $script:GuiBaselines = @{} }
    $dirKey = (Resolve-Path -LiteralPath $BaselineDir).Path.ToLowerInvariant()
    if (-not $script:GuiBaselineIndex.ContainsKey($dirKey)) {
        $index = @{}
        foreach ($candidate in @(Get-ChildItem -LiteralPath $BaselineDir -Recurse -File -Filter '*.gui')) {
            if (-not $index.ContainsKey($candidate.BaseName)) { $index[$candidate.BaseName] = $candidate }
        }
        $script:GuiBaselineIndex[$dirKey] = $index
    }
    $file = $script:GuiBaselineIndex[$dirKey][$Name]
    if (-not $file) { return $null }
    $cacheKey = "$dirKey|$Name"
    if ($script:GuiBaselines.ContainsKey($cacheKey)) { return $script:GuiBaselines[$cacheKey] }

    $text = (Read-GuiText -Path $file.FullName) -replace "`r`n", "`n"
    $window = @(Get-GuiTopLevelWindows -Root (ConvertFrom-GuiText -Text $text))[0]
    if (-not $window) { return $null }

    $gameVersion = ''
    $source = ''
    if ($text -match '^# Vanilla (\S+), (\S+), lines') {
        $gameVersion = $Matches[1]
        $source = $Matches[2]
    }
    $lines = $text -split "`n"
    $baseline = [pscustomobject]@{
        Name        = $window.Name
        Node        = $window.Node
        Path        = $file.FullName
        GameVersion = $gameVersion
        Source      = $source
        Lines       = $lines[($window.Line - 1)..($window.EndLine - 1)]
    }
    $script:GuiBaselines[$cacheKey] = $baseline
    return $baseline
}

# Width of a window, list or tiled button. Windows write width/height, list boxes and buttons x/y.
function Get-GuiWidth {
    param($Node)

    $size = Get-GuiBlock -Node $Node -Key 'size'
    $width = ConvertTo-GuiNumber (Get-GuiValue -Node $size -Key 'width')
    if ($null -eq $width) { $width = ConvertTo-GuiNumber (Get-GuiValue -Node $size -Key 'x') }
    return $width
}

# Scroll containers whose scroll_wheel_factor is not a whole number of rows.
function Get-GuiScrollViolations {
    param([Parameter(Mandatory)]$Node)

    foreach ($block in (Get-GuiNodes -Node $Node)) {
        $factor = ConvertTo-GuiNumber (Get-GuiValue -Node $block -Key 'scroll_wheel_factor')
        if ($null -eq $factor) { continue }

        $heights = @(
            foreach ($child in $block.Children) {
                if ($null -eq $child.Children -or $child.Key -ine 'gridBoxType') { continue }
                $height = ConvertTo-GuiNumber (Get-GuiValue -Node (Get-GuiBlock -Node $child -Key 'slotsize') -Key 'height')
                if ($null -ne $height -and $height -gt 0) { $height }
            }
        ) | Sort-Object -Unique
        $heights = @($heights)
        if ($heights.Count -ne 1) { continue }

        if (($factor % $heights[0]) -ne 0) {
            $name = Get-GuiValue -Node $block -Key 'name'
            "line $($block.Line): '$name' has scroll_wheel_factor $factor, not a multiple of the row height $($heights[0])"
        }
    }
}

# size blocks larger than the design target.
function Get-GuiOversizeViolations {
    param([Parameter(Mandatory)]$Node, [int]$MaxWidth = 2560, [int]$MaxHeight = 1440)

    foreach ($block in (Get-GuiNodes -Node $Node)) {
        if ($block.Key -ine 'size') { continue }
        $width = ConvertTo-GuiNumber (Get-GuiValue -Node $block -Key 'width')
        $height = ConvertTo-GuiNumber (Get-GuiValue -Node $block -Key 'height')
        if (($null -ne $width -and $width -gt $MaxWidth) -or ($null -ne $height -and $height -gt $MaxHeight)) {
            "line $($block.Line): size ${width}x${height} exceeds ${MaxWidth}x${MaxHeight}"
        }
    }
}

# Sprites declared in a parsed .gfx file.
function Get-GuiSpriteDeclarations {
    param([Parameter(Mandatory)]$Root)

    foreach ($section in $Root.Children) {
        if ($null -eq $section.Children -or $section.Key -ine 'spriteTypes') { continue }
        foreach ($sprite in $section.Children) {
            if ($null -eq $sprite.Children) { continue }
            $name = Get-GuiValue -Node $sprite -Key 'name'
            if (-not $name) { continue }
            # sprites name one texture (texturefile); progress bars name two (textureFile1, textureFile2)
            $textures = @($sprite.Children | Where-Object { $null -eq $_.Children -and $_.Key -imatch '^texturefile\d?$' } | ForEach-Object { ([string]$_.Value) -replace '[\\/]+', '/' })
            [pscustomobject]@{ Name = $name; Type = $sprite.Key; Texture = [string]($textures | Select-Object -First 1); Textures = $textures; Line = $sprite.Line }
        }
    }
}

# The game executable as text, one character per byte, for the two functions below.
function Read-ExeText {
    param([Parameter(Mandatory)][string]$Path)

    return [System.Text.Encoding]::GetEncoding(28591).GetString([System.IO.File]::ReadAllBytes($Path))
}

# Where the given names are stored as string literals in the executable text, grouped into clusters
# of hits at most $Gap bytes apart, the cluster with the most names first. The game code finds
# widgets by name, and the literals of one source file are stored together, so the largest cluster
# for the widget names of a window is the code that fills that window.
function Get-ExeNameClusters {
    param([Parameter(Mandatory)][string]$Text, [Parameter(Mandatory)][string[]]$Names, [int]$Gap = 2048)

    $nul = [string][char]0
    $seen = [System.Collections.Generic.HashSet[string]]::new()
    $hits = [System.Collections.Generic.List[object]]::new()
    foreach ($name in $Names) {
        if (-not $name -or -not $seen.Add($name)) { continue }
        $needle = $nul + $name + $nul
        $at = $Text.IndexOf($needle, [System.StringComparison]::Ordinal)
        while ($at -ge 0) {
            $hits.Add([pscustomobject]@{ Offset = $at + 1; Name = $name })
            $at = $Text.IndexOf($needle, $at + 1, [System.StringComparison]::Ordinal)
        }
    }

    $clusters = [System.Collections.Generic.List[object]]::new()
    $current = $null
    foreach ($hit in ($hits | Sort-Object Offset)) {
        if ($null -eq $current -or ($hit.Offset - $current.End) -gt $Gap) {
            $current = [pscustomobject]@{ Start = $hit.Offset; End = 0; Names = [System.Collections.Generic.List[string]]::new() }
            $clusters.Add($current)
        }
        $current.End = $hit.Offset + $hit.Name.Length
        if (-not $current.Names.Contains($hit.Name)) { $current.Names.Add($hit.Name) }
    }
    return @($clusters | Sort-Object @{ Expression = { $_.Names.Count }; Descending = $true }, Start)
}

# The string literals stored between two offsets of the executable text, in stored order.
function Get-ExeStrings {
    param([Parameter(Mandatory)][string]$Text, [int]$Start, [int]$End)

    $Start = [Math]::Max(0, $Start)
    $End = [Math]::Min($Text.Length, $End)
    if ($End -le $Start) { return }
    foreach ($m in [regex]::Matches($Text.Substring($Start, $End - $Start), '(?<=\x00)[\x20-\x7e]{3,}(?=\x00)')) {
        [pscustomobject]@{ Offset = $Start + $m.Index; Value = $m.Value }
    }
}

# The list/row and grid/entry links the engine makes in code, from tools/gui-links.json.
# Returns an object with EntryPairs (grid, entry), ListRows (listWindow, list, row) and Variables.
function Get-GuiLinks {
    param([string]$Path)

    if (-not $Path) { $Path = Join-Path $PSScriptRoot 'gui-links.json' }
    $json = [System.IO.File]::ReadAllText($Path, [System.Text.Encoding]::UTF8) | ConvertFrom-Json
    return [pscustomobject]@{
        EntryPairs = @($json.entryPairs | Where-Object { $_.grid })
        ListRows   = @($json.listRows | Where-Object { $_.row })
        Variables  = $json.variables
        Path       = $Path
    }
}

# A scene file from tools/scenes/<name>.json: the windows of one screen, sample texts and the
# screenshot region to crop. $Name may also be a path.
function Get-GuiScene {
    param([Parameter(Mandatory)][string]$Name)

    $path = $Name
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        $path = Join-Path (Join-Path $PSScriptRoot 'scenes') "$Name.json"
    }
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Scene not found: $Name (looked for $path)" }
    $scene = [System.IO.File]::ReadAllText($path, [System.Text.Encoding]::UTF8) | ConvertFrom-Json
    $scene | Add-Member -NotePropertyName Path -NotePropertyValue $path -Force
    return $scene
}

# Pixel width of a line of text in a vanilla bitmap font: the sum of the xadvance values in
# gfx/fonts/<font>.fnt (see Design Rules, "A text's width can be worked out before a launch").
# $Font is the font name used in .gui files (hoi_18, hoi_20b ...); the .fnt file is looked up in the mod
# first, then in the game install. Returns $null when the font file cannot be found.
function Measure-GuiText {
    param([Parameter(Mandatory)][string]$Font, [Parameter(Mandatory)][AllowEmptyString()][string]$Text, [string]$GameDir)

    if (-not $script:GuiFontCache) { $script:GuiFontCache = @{} }
    if (-not $script:GuiFontCache.ContainsKey($Font)) {
        $repoRoot = Split-Path -Parent $PSScriptRoot
        $resolvedGameDir = Resolve-HoiGameDir -GameDir $GameDir
        $file = $null
        foreach ($base in @($repoRoot, $resolvedGameDir)) {
            if (-not $base) { continue }
            $candidate = Join-Path (Join-Path (Join-Path $base 'gfx') 'fonts') "$Font.fnt"
            if (Test-Path -LiteralPath $candidate) { $file = $candidate; break }
        }
        $table = $null
        if ($file) {
            $table = @{}
            foreach ($line in [System.IO.File]::ReadAllLines($file)) {
                if ($line -match '^char\s+id=(\d+)\s.*\sxadvance=(-?\d+)') { $table[[int]$Matches[1]] = [int]$Matches[2] }
                elseif ($line -match '^common\s+lineHeight=(\d+)') { $table[-1] = [int]$Matches[1] }
            }
        }
        $script:GuiFontCache[$Font] = $table
    }
    $table = $script:GuiFontCache[$Font]
    if ($null -eq $table) { return $null }
    if ($Text.Length -eq 0) { return 0 }
    $width = 0
    foreach ($ch in $Text.ToCharArray()) {
        $code = [int]$ch
        if ($table.ContainsKey($code)) { $width += $table[$code] }
        elseif ($table.ContainsKey(63)) { $width += $table[63] }
    }
    return $width
}

# Line height of a vanilla bitmap font in pixels (the lineHeight of its .fnt), or $null.
function Get-GuiFontLineHeight {
    param([Parameter(Mandatory)][string]$Font, [string]$GameDir)

    if ($null -eq (Measure-GuiText -Font $Font -Text '' -GameDir $GameDir)) { return $null }
    $table = $script:GuiFontCache[$Font]
    if ($table.ContainsKey(-1)) { return $table[-1] }
    return $null
}

# Height of a window, list or tiled button (the counterpart of Get-GuiWidth).
function Get-GuiHeight {
    param($Node)

    $size = Get-GuiBlock -Node $Node -Key 'size'
    $height = ConvertTo-GuiNumber (Get-GuiValue -Node $size -Key 'height')
    if ($null -eq $height) { $height = ConvertTo-GuiNumber (Get-GuiValue -Node $size -Key 'y') }
    return $height
}

# The @variables a window's text uses, and the ones its file defines (they do not travel with a window).
function Get-GuiVariableUse {
    param([Parameter(Mandatory)][string]$Path)

    $text = [regex]::Replace((Read-GuiText -Path $Path), '#[^\r\n]*', '')
    $defined = @([regex]::Matches($text, '(?m)^\s*(@[A-Za-z0-9_]+)\s*=') | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique)
    $used = @([regex]::Matches($text, '=\s*(@[A-Za-z0-9_]+)') | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique)
    return [pscustomobject]@{ Defined = $defined; Used = $used; Undefined = @($used | Where-Object { $defined -notcontains $_ }) }
}
