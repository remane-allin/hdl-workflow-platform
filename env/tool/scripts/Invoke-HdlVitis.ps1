param(
    [ValidateSet("xsct", "vitis", "bootgen")]
    [string]$Tool = "xsct",

    [string]$Source = "",

    [string]$Project = "",

    [string]$WorkspacePath = ".",

    [string]$LogDir = "",

    [string]$RunDir = "",

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ToolArgs
)

$ErrorActionPreference = "Stop"

$Workspace = Resolve-Path $WorkspacePath
$env:PYTHONPATH = Join-Path $Workspace "env\core"
$ToolDefaults = Join-Path $Workspace "env\tool\scripts\HdlToolDefaults.ps1"
$ProjectPath = $null
if ($Project) {
    $ProjectPath = Resolve-Path $Project
    & python -m hdlflow.cli workflow-stage-guard --project $ProjectPath.Path --stage loop3-preflight --action "Invoke-HdlVitis $Tool"
    if ($LASTEXITCODE -ne 0) {
        throw "HDL workflow stage guard blocked Invoke-HdlVitis $Tool"
    }
}

$LauncherKey = switch ($Tool) {
    "xsct" { "xsct_bat" }
    "vitis" { "vitis_bat" }
    "bootgen" { "bootgen_bat" }
}
if (Test-Path -LiteralPath $ToolDefaults) {
    . $ToolDefaults
    $Launcher = Resolve-HdlToolPath -WorkspacePath $Workspace -Tool vitis -Launcher $LauncherKey
}
else {
    $Launcher = (& python -m hdlflow.cli get-tool-launcher --workspace $Workspace --tool vitis --launcher $LauncherKey).Trim()
}
if (-not $Launcher) {
    throw "Vitis launcher is not configured: $LauncherKey"
}
if (-not (Test-Path -LiteralPath $Launcher)) {
    throw "Vitis launcher not found: $Launcher"
}
$env:HDLFLOW_VITIS_LAUNCHER = $Launcher
$env:HDLFLOW_VITIS_ROOT = Split-Path -Parent (Split-Path -Parent $Launcher)

if ($LogDir) {
    $ResolvedLogDir = $LogDir
}
elseif ($ProjectPath) {
    $ResolvedLogDir = Join-Path $ProjectPath "output\fpga\vitis\logs"
}
else {
    $ResolvedLogDir = Join-Path $Workspace "local\runtime\xil\vitis_logs"
}
if ($RunDir) {
    $ResolvedRunDir = $RunDir
}
else {
    $ResolvedRunDir = $ResolvedLogDir
}
New-Item -ItemType Directory -Force -Path $ResolvedLogDir | Out-Null
New-Item -ItemType Directory -Force -Path $ResolvedRunDir | Out-Null
$ResolvedLogDir = (Resolve-Path $ResolvedLogDir).Path
$ResolvedRunDir = (Resolve-Path $ResolvedRunDir).Path

$Args = @()
if ($Source) {
    $Args += (Resolve-Path $Source).Path
}
if ($ToolArgs.Count -gt 0) {
    $Args += $ToolArgs
}

$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogPath = Join-Path $ResolvedLogDir "$Tool`_$Stamp.log"

Push-Location $ResolvedRunDir
$ExitCode = 1
try {
    $PreviousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $Launcher @Args *> $LogPath
    $ExitCode = $LASTEXITCODE
}
finally {
    $ErrorActionPreference = $PreviousErrorActionPreference
    Pop-Location
}

Get-Content -LiteralPath $LogPath -ErrorAction SilentlyContinue
Write-Host "vitis_tool=$Tool"
Write-Host "vitis_log=$LogPath"
Write-Host "vitis_run_dir=$ResolvedRunDir"
exit $ExitCode
