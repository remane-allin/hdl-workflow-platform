param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectPath,
    [string]$OutputDir = "archive/project_exports",
    [switch]$IncludeRuntime
)

$ErrorActionPreference = "Stop"

function Get-RelativePathCompat {
    param(
        [Parameter(Mandatory = $true)][string]$BasePath,
        [Parameter(Mandatory = $true)][string]$ChildPath
    )

    $baseFull = [System.IO.Path]::GetFullPath($BasePath)
    $childFull = [System.IO.Path]::GetFullPath($ChildPath)
    if (-not $baseFull.EndsWith([System.IO.Path]::DirectorySeparatorChar)) {
        $baseFull += [System.IO.Path]::DirectorySeparatorChar
    }
    $baseUri = New-Object System.Uri($baseFull)
    $childUri = New-Object System.Uri($childFull)
    return [System.Uri]::UnescapeDataString($baseUri.MakeRelativeUri($childUri).ToString()).Replace("/", "\")
}

$project = Resolve-Path $ProjectPath
$projectName = Split-Path $project -Leaf
if (-not (Test-Path (Join-Path $project "project_scaffold.yaml"))) {
    throw "Not a generated HDL project: $project"
}

$workspace = Resolve-Path (Join-Path $PSScriptRoot "..")
$outputRoot = Join-Path $workspace $OutputDir
if (-not (Test-Path $outputRoot)) {
    New-Item -ItemType Directory -Path $outputRoot | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$zipPath = Join-Path $outputRoot "$projectName`_$timestamp.zip"
$staging = Join-Path ([System.IO.Path]::GetTempPath()) "hdl_project_export_$projectName`_$timestamp"
if (Test-Path $staging) {
    Remove-Item -LiteralPath $staging -Recurse -Force
}
New-Item -ItemType Directory -Path $staging | Out-Null

$projectStage = Join-Path $staging $projectName
New-Item -ItemType Directory -Path $projectStage | Out-Null

$skipPatterns = @(
    "\\_runtime(\\|$)",
    "\\work(\\|$)",
    "\\__pycache__(\\|$)",
    "\\.git(\\|$)",
    "\\.codex(\\|$)",
    "\\.omx(\\|$)",
    "\.wlf$",
    "\.vcd$",
    "\.fst$"
)

Get-ChildItem -LiteralPath $project -Recurse -File | ForEach-Object {
    $relative = Get-RelativePathCompat -BasePath $project -ChildPath $_.FullName
    $normalized = $relative -replace "/", "\"
    if (-not $IncludeRuntime) {
        foreach ($pattern in $skipPatterns) {
            if ($normalized -match $pattern) {
                return
            }
        }
    }
    $target = Join-Path $projectStage $relative
    $targetDir = Split-Path $target -Parent
    if (-not (Test-Path $targetDir)) {
        New-Item -ItemType Directory -Path $targetDir | Out-Null
    }
    Copy-Item -LiteralPath $_.FullName -Destination $target
}

$configPath = Join-Path $workspace "config\projects\$projectName"
if (Test-Path $configPath) {
    $configStage = Join-Path $staging "config\projects\$projectName"
    New-Item -ItemType Directory -Path $configStage -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $configPath "project_config.yaml") -Destination $configStage -Force
}

Compress-Archive -Path (Join-Path $staging "*") -DestinationPath $zipPath -Force
Remove-Item -LiteralPath $staging -Recurse -Force

Write-Host "HDL_PROJECT_EXPORT_PASS project=$project zip=$zipPath"
