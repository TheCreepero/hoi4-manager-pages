<#
.SYNOPSIS
    Lists the widget names the game code asks for around a vanilla window.

.DESCRIPTION
    The game fills a window by looking up widgets by name, and those names are stored as text in
    hoi4.exe. This script finds where the widget names of a vanilla window are stored together and
    prints every name stored there, marked by where vanilla defines it:

      =  in this window
      ~  in another window of the same file
      .  in another vanilla .gui file
      +  in no vanilla .gui file

    A "+" name is either a widget the code would fill if the window had it, or not a widget name at
    all (a sprite, a sound, a column id). No "+" names means the window already shows every value
    the code can give it, so a redesign can re-arrange it but cannot add data.

    The executable stores each distinct name once. A name that several windows share therefore sits
    with only one of them, and the script lists the names it did not find with the others.

.EXAMPLE
    .\tools\Show-CodeNames.ps1 unitview.gui army_division_view
    The names stored with the division row's widget names.

.EXAMPLE
    .\tools\Show-CodeNames.ps1 unitview.gui army_division_view -All
    Also lists the other strings stored there. Text keys in capitals show which labels and tooltips
    the code builds for the window.

.EXAMPLE
    .\tools\Show-CodeNames.ps1 airselectionview.gui airwing_selection_item -Gap 4096
    Joins hits up to 4096 bytes apart, for a window whose names are stored with wide gaps.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory, Position = 0)][string]$File,
    [Parameter(Mandatory, Position = 1, ValueFromRemainingArguments)][string[]]$Window,
    [int]$Gap = 2048,
    [int]$Margin = 256,
    [switch]$All,
    [string]$GameDir
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'GuiParsing.ps1')

# Accept "a, b" (PowerShell), "a b" and "a,b" (other shells) alike.
$Window = @($Window | ForEach-Object { $_ -split '[,\s]+' } | Where-Object { $_ })

$resolvedGameDir = Resolve-HoiGameDir -GameDir $GameDir
if (-not $resolvedGameDir) { throw 'Hearts of Iron IV install not found. Pass -GameDir or set HOI4_GAME_DIR.' }
$interfaceDir = Join-Path $resolvedGameDir 'interface'
$path = Join-Path $interfaceDir $File
if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "File not found: $path" }
$exePath = Join-Path $resolvedGameDir 'hoi4.exe'
if (-not (Test-Path -LiteralPath $exePath -PathType Leaf)) { throw "File not found: $exePath" }

function Get-GuiNames {
    param($Node)
    foreach ($block in (Get-GuiNodes -Node $Node)) {
        $name = Get-GuiValue -Node $block -Key 'name'
        if ($name) { $name }
    }
}

$windows = @(Get-GuiTopLevelWindows -Root (ConvertFrom-GuiText -Text (Read-GuiText -Path $path)))

# name -> first window of this file that defines it
$inFile = [System.Collections.Generic.Dictionary[string, string]]::new()
foreach ($w in $windows) {
    foreach ($name in (Get-GuiNames -Node $w.Node)) {
        if (-not $inFile.ContainsKey($name)) { $inFile[$name] = $w.Name }
    }
}

# name -> first vanilla .gui file that defines it
$inVanilla = [System.Collections.Generic.Dictionary[string, string]]::new()
foreach ($guiFile in (Get-ChildItem -LiteralPath $interfaceDir -Recurse -File -Filter '*.gui' | Sort-Object FullName)) {
    $relPath = $guiFile.FullName.Substring($interfaceDir.Length + 1) -replace '\\', '/'
    $text = (Read-GuiText -Path $guiFile.FullName) -replace '#[^\r\n]*', ''
    foreach ($m in [regex]::Matches($text, '(?i)\bname\s*=\s*"?([^\s"{}=]+)"?')) {
        $name = $m.Groups[1].Value
        if (-not $inVanilla.ContainsKey($name)) { $inVanilla[$name] = $relPath }
    }
}

$exeText = Read-ExeText -Path $exePath

foreach ($windowName in $Window) {
    $w = $windows | Where-Object { $_.Name -ieq $windowName } | Select-Object -First 1
    if (-not $w) { Write-Warning "Window '$windowName' not found in $path"; continue }

    $names = [System.Collections.Generic.HashSet[string]]::new()
    foreach ($name in (Get-GuiNames -Node $w.Node)) { [void]$names.Add($name) }

    $clusters = @(Get-ExeNameClusters -Text $exeText -Names @($names) -Gap $Gap)
    if (-not $clusters.Count) {
        "## $($w.Name)  none of its $($names.Count) widget names is stored in hoi4.exe"
        continue
    }
    $cluster = $clusters[0]
    "## {0}  ({1})  {2} of {3} widget names stored together at 0x{4:x}-0x{5:x}" -f $w.Name, $File, $cluster.Names.Count, $names.Count, $cluster.Start, $cluster.End

    $candidates = 0
    $shown = [System.Collections.Generic.HashSet[string]]::new()
    foreach ($string in (Get-ExeStrings -Text $exeText -Start ($cluster.Start - $Margin) -End ($cluster.End + $Margin))) {
        $value = $string.Value
        if (-not $shown.Add($value)) { continue }
        # identifiers with a lower-case letter; text keys are all capitals and GFX_ names are sprites
        $isName = ($value -cmatch '^[A-Za-z_][A-Za-z0-9_]*$') -and ($value -cmatch '[a-z]') -and ($value -cnotmatch '^GFX_')
        if (-not $isName) {
            if ($All) { "       $value" }
            continue
        }
        if ($names.Contains($value)) {
            "  =    $value"
        } elseif ($inFile.ContainsKey($value)) {
            "  ~    {0,-44} {1}" -f $value, $inFile[$value]
        } elseif ($inVanilla.ContainsKey($value)) {
            "  .    {0,-44} {1}" -f $value, $inVanilla[$value]
        } else {
            $candidates++
            "  +    $value"
        }
    }

    $elsewhere = @($names | Where-Object { -not $cluster.Names.Contains($_) } | Sort-Object)
    "  $candidates name(s) marked + are in no vanilla .gui file."
    if ($elsewhere.Count) {
        "  Stored elsewhere (shared with other windows, or not looked up by name): $($elsewhere -join ', ')"
    }
}
