<#
.SYNOPSIS
    Prints the structure of a HOI4 .gui file, or of single windows in it.

.DESCRIPTION
    The inventory step of every screen phase. Reads the vanilla file from the game install
    unless -FromMod is given or -File is an existing path.

.EXAMPLE
    .\tools\Show-GuiOutline.ps1 airselectionview.gui
    Lists every top-level window with its size, line range and scrollbar count.

.EXAMPLE
    .\tools\Show-GuiOutline.ps1 airselectionview.gui air_selection_view -Depth 3
    Outlines the containers, grids and dropdowns of one window.

.EXAMPLE
    .\tools\Show-GuiOutline.ps1 airselectionview.gui air_selection_view -All
    Also lists text boxes, icons and buttons, with their fonts, sprites and hotkeys.

.EXAMPLE
    .\tools\Show-GuiOutline.ps1 airselectionview.gui air_selection_view -Widgets
    Lists the named widget paths that the name-parity test compares.

.EXAMPLE
    .\tools\Show-GuiOutline.ps1 unitview.gui army_division_list_view -Comments
    Lists the vanilla comments that say what the engine does with a widget ("set in code", grid spacing ...).
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory, Position = 0)][string]$File,
    [Parameter(Position = 1, ValueFromRemainingArguments)][string[]]$Window,
    [int]$Depth = 2,
    [switch]$All,
    [switch]$Widgets,
    [switch]$Comments,
    [switch]$FromMod,
    [string]$GameDir
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'GuiParsing.ps1')

# Accept "a, b" (PowerShell), "a b" and "a,b" (other shells) alike. A PowerShell array bound through
# ValueFromRemainingArguments arrives as one space-joined string, so split on whitespace as well.
$Window = @($Window | ForEach-Object { $_ -split '[,\s]+' } | Where-Object { $_ })

$repoRoot = Split-Path -Parent $PSScriptRoot
if (Test-Path -LiteralPath $File -PathType Leaf) {
    $path = (Resolve-Path -LiteralPath $File).Path
} elseif ($FromMod) {
    $path = Join-Path (Join-Path $repoRoot 'interface') $File
} else {
    $resolvedGameDir = Resolve-HoiGameDir -GameDir $GameDir
    if (-not $resolvedGameDir) { throw 'Hearts of Iron IV install not found. Pass -GameDir or set HOI4_GAME_DIR.' }
    $path = Join-Path (Join-Path $resolvedGameDir 'interface') $File
}
if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "File not found: $path" }

function Format-GuiPair {
    param($Node, [string]$Key, [string]$First, [string]$Second, [string]$Separator)

    $block = Get-GuiBlock -Node $Node -Key $Key
    if ($null -eq $block) { return '' }
    $a = Get-GuiValue -Node $block -Key $First
    $b = Get-GuiValue -Node $block -Key $Second
    if ($null -eq $a -and $null -eq $b -and $Key -ieq 'size') {
        # list boxes and tiled buttons write their size as x/y instead of width/height
        $a = Get-GuiValue -Node $block -Key 'x'
        $b = Get-GuiValue -Node $block -Key 'y'
    }
    return ('{0}{1}{2}' -f $a, $Separator, $b)
}

function Get-GuiNodeDetails {
    param($Node)

    $details = [System.Collections.Generic.List[string]]::new()
    $slot = Format-GuiPair -Node $Node -Key 'slotsize' -First 'width' -Second 'height' -Separator 'x'
    if ($slot) { $details.Add("slot $slot") }
    if (Get-GuiValue -Node $Node -Key 'verticalScrollbar') { $details.Add('vscroll') }
    if (Get-GuiValue -Node $Node -Key 'horizontalScrollbar') { $details.Add('hscroll') }
    $factor = Get-GuiValue -Node $Node -Key 'scroll_wheel_factor'
    if ($factor) { $details.Add("wheel $factor") }
    foreach ($key in 'font', 'buttonFont') {
        $font = Get-GuiValue -Node $Node -Key $key
        if ($font) { $details.Add("font $font") }
    }
    foreach ($key in 'quadTextureSprite', 'spriteType') {
        $sprite = Get-GuiValue -Node $Node -Key $key
        if ($sprite) { $details.Add($sprite) }
    }
    $orientation = Get-GuiValue -Node $Node -Key 'orientation'
    if ($orientation) { $details.Add("orient $orientation") }
    # a button can carry several hotkeys, one per shortcut line
    $hotkeys = @($Node.Children | Where-Object { $null -eq $_.Children -and $_.Key -ieq 'shortcut' } | ForEach-Object { $_.Value })
    if ($hotkeys.Count) { $details.Add("key $($hotkeys -join ' / ')") }
    return ($details -join ', ')
}

$structural = @('containerwindowtype', 'windowtype', 'gridboxtype', 'dropdownboxtype', 'expandedwindow', 'listboxtype', 'smoothlistboxtype')
$root = ConvertFrom-GuiText -Text (Read-GuiText -Path $path)
$windows = @(Get-GuiTopLevelWindows -Root $root)

if (-not $Window) {
    "{0}  ({1} top-level windows)" -f $path, $windows.Count
    foreach ($w in $windows) {
        $scrollbars = @(Get-GuiNodes -Node $w.Node | Where-Object { Get-GuiValue -Node $_ -Key 'verticalScrollbar' }).Count
        "  {0,-48} {1,-12} lines {2,5}-{3,-5} scrollbars {4}" -f $w.Name, (Format-GuiPair -Node $w.Node -Key 'size' -First 'width' -Second 'height' -Separator 'x'), $w.Line, $w.EndLine, $scrollbars
    }
    return
}

foreach ($name in $Window) {
    $w = $windows | Where-Object { $_.Name -ieq $name } | Select-Object -First 1
    if (-not $w) { Write-Warning "Window '$name' not found in $path"; continue }

    "## {0}  [{1}]  size {2}  lines {3}-{4}  {5}" -f $w.Name, $w.Type, (Format-GuiPair -Node $w.Node -Key 'size' -First 'width' -Second 'height' -Separator 'x'), $w.Line, $w.EndLine, (Get-GuiNodeDetails -Node $w.Node)

    if ($Widgets) {
        Get-GuiWidgetPaths -Node $w.Node | Sort-Object | ForEach-Object { "  $_" }
        continue
    }

    if ($Comments) {
        # the comments that say what the engine does with a widget: sizes set in code, widths computed from a grid
        $sourceLines = (Read-GuiText -Path $path) -replace "`r`n", "`n" -split "`n"
        for ($i = $w.Line; $i -le $w.EndLine -and $i -le $sourceLines.Count; $i++) {
            $line = $sourceLines[$i - 1]
            $hash = $line.IndexOf('#')
            if ($hash -lt 0) { continue }
            $comment = $line.Substring($hash + 1).Trim()
            if ($comment -match '(?i)in code|spacing|max |maximum|set to|stretch|replaced|hidden|not used|overrid') {
                "  L{0,-5} {1,-50} # {2}" -f $i, $line.Substring(0, $hash).Trim(), $comment
            }
        }
        continue
    }

    $background = Get-GuiBlock -Node $w.Node -Key 'background'
    if ($background) { "  background: {0}" -f (Get-GuiNodeDetails -Node $background) }

    $stack = [System.Collections.Generic.Stack[object]]::new()
    for ($i = $w.Node.Children.Count - 1; $i -ge 0; $i--) {
        if ($null -ne $w.Node.Children[$i].Children) { $stack.Push(@($w.Node.Children[$i], 1)) }
    }
    while ($stack.Count -gt 0) {
        $item = $stack.Pop()
        $node = $item[0]
        $level = $item[1]
        $type = $node.Key.ToLowerInvariant()
        $nodeName = Get-GuiValue -Node $node -Key 'name'
        $show = ($structural -contains $type) -or ($All -and $nodeName -and $type -ne 'background')
        if ($show) {
            "{0}{1,-22} {2,-40} pos {3,-10} size {4,-12} {5}  L{6}" -f ('  ' * $level), ($node.Key -replace '(?i)containerWindowType', 'container'), $nodeName, (Format-GuiPair -Node $node -Key 'position' -First 'x' -Second 'y' -Separator ','), (Format-GuiPair -Node $node -Key 'size' -First 'width' -Second 'height' -Separator 'x'), (Get-GuiNodeDetails -Node $node), $node.Line
        }
        if ($level -lt $Depth) {
            for ($i = $node.Children.Count - 1; $i -ge 0; $i--) {
                if ($null -ne $node.Children[$i].Children) { $stack.Push(@($node.Children[$i], ($level + 1))) }
            }
        }
    }
}
