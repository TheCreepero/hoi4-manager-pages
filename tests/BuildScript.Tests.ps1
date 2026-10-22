BeforeAll {
    $script:RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
    . (Join-Path $script:RepoRoot 'tools\HoiModBuild.ps1')
    $script:BuildConfig = Get-ModBuildConfig -RepoDir $script:RepoRoot
}

Describe 'build.ps1 configuration' {
    It 'ships the common, gfx, interface and localisation folders with the descriptor and thumbnail' {
        $shippedTopLevel = @(Get-ModContentFiles -Config $script:BuildConfig | ForEach-Object { ($_ -split '/')[0] } | Sort-Object -Unique)
        $shippedTopLevel | Should -Be @('common', 'descriptor.mod', 'gfx', 'interface', 'localisation', 'thumbnail.png') -Because 'tools, tests, wiki and reference are development folders'
    }

    It 'installs as hoi4-manager-pages and packages hoi4-manager-pages.zip' {
        $script:BuildConfig.ModFolderName | Should -Be 'hoi4-manager-pages'
        $script:BuildConfig.ZipArchiveName | Should -Be 'hoi4-manager-pages.zip'
        $script:BuildConfig.PackageLayout | Should -Be 'Flat'
    }
}
