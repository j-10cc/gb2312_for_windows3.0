param(
    [switch]$WhatIf
)

$ErrorActionPreference = 'Stop'
$workspace = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..')).TrimEnd('\')
$testRoot = [IO.Path]::GetFullPath((Join-Path $workspace 'output\setup-test')).TrimEnd('\')
$workspacePrefix = $workspace + '\'
if (-not $testRoot.StartsWith($workspacePrefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Test root is outside the workspace: $testRoot"
}
if (-not (Test-Path -LiteralPath $testRoot -PathType Container)) {
    Write-Output "No verification directory: $testRoot"
    exit 0
}

$references = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
$documents = @(
    (Join-Path $workspace 'README.md'),
    (Join-Path $workspace 'docs'),
    (Join-Path $workspace 'tests'),
    (Join-Path $workspace 'tools')
) | Where-Object { Test-Path -LiteralPath $_ }
$matches = & rg --no-filename --only-matching --glob '*.md' 'output/setup-test/[A-Za-z0-9_./-]+' @documents
if ($LASTEXITCODE -gt 1) { throw 'Could not scan Markdown references.' }
foreach ($match in $matches) {
    $parts = $match -split '/'
    if ($parts.Length -ge 3) { [void]$references.Add($parts[2]) }
}

# Reusable input fixtures and the shared installed baseline used by test scripts.
foreach ($name in @('A', 'C', 'C32', 'WORD11A-EXTRACT')) { [void]$references.Add($name) }

function Get-ByteCount([string]$path) {
    $sum = (Get-ChildItem -LiteralPath $path -File -Recurse -Force -ErrorAction SilentlyContinue |
        Measure-Object -Property Length -Sum).Sum
    if ($null -eq $sum) { return [long]0 }
    return [long]$sum
}

$before = Get-ByteCount $testRoot
$testPrefix = $testRoot + '\'
$targets = @(Get-ChildItem -LiteralPath $testRoot -Directory -Force |
    Where-Object { -not $references.Contains($_.Name) -and -not ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) })
$plannedBytes = [long]0
foreach ($item in $targets) {
    $target = [IO.Path]::GetFullPath($item.FullName).TrimEnd('\')
    if (-not $target.StartsWith($testPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove a directory outside setup-test: $target"
    }
    $bytes = Get-ByteCount $target
    $plannedBytes += $bytes
    if (-not $WhatIf) { Remove-Item -LiteralPath $target -Recurse -Force }
}

$after = Get-ByteCount $testRoot
Write-Output ('Referenced cases retained: {0}' -f $references.Count)
Write-Output ('Unreferenced cases {0}: {1}' -f $(if ($WhatIf) { 'found' } else { 'removed' }), $targets.Count)
Write-Output ('setup-test before: {0:N1} MiB' -f ($before / 1MB))
Write-Output ('planned removal:  {0:N1} MiB' -f ($plannedBytes / 1MB))
Write-Output ('setup-test after:  {0:N1} MiB' -f ($after / 1MB))
if (-not $WhatIf) {
    Write-Output ('space freed:       {0:N1} MiB' -f (($before - $after) / 1MB))
}
$windowsReferenced = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
foreach ($match in $matches) {
    $parts = $match -split '/'
    if ($parts.Length -ge 4 -and $parts[3] -ieq 'WINDOWS') {
        [void]$windowsReferenced.Add($parts[2])
    }
}
$beforeCompact = Get-ByteCount $testRoot
$windowsTargets = @(Get-ChildItem -LiteralPath $testRoot -Directory -Force |
    Where-Object { -not $windowsReferenced.Contains($_.Name) -and $_.Name -notin @('A', 'C', 'C32', 'WORD11A-EXTRACT') } |
    ForEach-Object {
        $candidate = Join-Path $_.FullName 'WINDOWS'
        if (Test-Path -LiteralPath $candidate -PathType Container) {
            Get-Item -LiteralPath $candidate -Force
        }
    } |
    Where-Object { -not ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) })
$windowsBytes = [long]0
foreach ($item in $windowsTargets) {
    $target = [IO.Path]::GetFullPath($item.FullName).TrimEnd('\')
    if (-not $target.StartsWith($testPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove a directory outside setup-test: $target"
    }
    $bytes = Get-ByteCount $target
    $windowsBytes += $bytes
    if (-not $WhatIf) { Remove-Item -LiteralPath $target -Recurse -Force }
}
$afterCompact = Get-ByteCount $testRoot
Write-Output ('Referenced Windows trees retained: {0}' -f $windowsReferenced.Count)
Write-Output ('Unreferenced Windows trees {0}: {1}' -f $(if ($WhatIf) { 'found' } else { 'removed' }), $windowsTargets.Count)
Write-Output ('Windows trees planned removal: {0:N1} MiB' -f ($windowsBytes / 1MB))
Write-Output ('setup-test final size: {0:N1} MiB' -f ($afterCompact / 1MB))
if (-not $WhatIf) {
    Write-Output ('additional space freed: {0:N1} MiB' -f (($beforeCompact - $afterCompact) / 1MB))
}
