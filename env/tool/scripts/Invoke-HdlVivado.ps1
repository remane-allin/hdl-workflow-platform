param(
    [Parameter(Mandatory = $true)]
    [string]$Source,

    [string]$Project = "",

    [string]$WorkspacePath = ".",

    [string]$Mode = "batch",

    [string]$LogDir = "",

    [string]$RunDir = "",

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$TclArgs
)

$ErrorActionPreference = "Stop"

function Move-HdlVivadoProjectRootLogs {
    param(
        [Parameter(Mandatory = $true)][string]$ProjectRoot,
        [Parameter(Mandatory = $true)][string]$ControlledLogDir
    )

    if (-not (Test-Path -LiteralPath $ProjectRoot)) {
        return
    }
    New-Item -ItemType Directory -Force -Path $ControlledLogDir | Out-Null
    $RootLogs = @(
        Get-ChildItem -Path $ProjectRoot -File -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -like "vivado*.jou" -or $_.Name -like "vivado*.log" }
    )
    foreach ($RootLog in $RootLogs) {
        $Target = Join-Path $ControlledLogDir $RootLog.Name
        if (Test-Path -LiteralPath $Target) {
            $Stem = [IO.Path]::GetFileNameWithoutExtension($RootLog.Name)
            $Ext = [IO.Path]::GetExtension($RootLog.Name)
            $Target = Join-Path $ControlledLogDir "$Stem`_relocated_$(Get-Date -Format 'yyyyMMdd_HHmmss')$Ext"
        }
        Move-Item -LiteralPath $RootLog.FullName -Destination $Target -Force
        Write-Host "vivado_relocated_root_log=$Target"
    }
}

$Workspace = Resolve-Path $WorkspacePath
$SourcePath = Resolve-Path $Source
$env:PYTHONPATH = Join-Path $Workspace "env\core"
$ToolDefaults = Join-Path $Workspace "env\tool\scripts\HdlToolDefaults.ps1"
$ProjectPath = $null
if ($Project) {
    $ProjectPath = Resolve-Path $Project
    & python -m hdlflow.cli workflow-stage-guard --project $ProjectPath.Path --stage loop3-preflight --action "Invoke-HdlVivado"
    if ($LASTEXITCODE -ne 0) {
        throw "HDL workflow stage guard blocked Invoke-HdlVivado"
    }
}
if (Test-Path -LiteralPath $ToolDefaults) {
    . $ToolDefaults
    $Vivado = Resolve-HdlToolPath -WorkspacePath $Workspace -Tool vivado -Launcher vivado_bat
}
else {
    $Vivado = (& python -m hdlflow.cli get-tool-launcher --workspace $Workspace --tool vivado --launcher vivado_bat).Trim()
}
if (-not $Vivado) {
    throw "Vivado vivado_bat is not configured in env/rule/global/toolchains/toolchains.yaml"
}
if (-not (Test-Path $Vivado)) {
    throw "Vivado launcher not found: $Vivado"
}

if ($LogDir) {
    $ResolvedLogDir = $LogDir
}
elseif ($Project) {
    $ResolvedLogDir = Join-Path $ProjectPath "output\fpga\vivado\logs"
}
else {
    $ResolvedLogDir = Join-Path $Workspace "local\runtime\xil\launch_logs"
}
if ($RunDir) {
    $ResolvedRunDir = $RunDir
}
else {
    $ResolvedRunDir = $ResolvedLogDir
}

$ProjectRootForLogSweep = $null
if ($Project) {
    $ProjectRootForLogSweep = $ProjectPath.Path
}

New-Item -ItemType Directory -Force -Path $ResolvedLogDir | Out-Null
New-Item -ItemType Directory -Force -Path $ResolvedRunDir | Out-Null
$ResolvedLogDir = (Resolve-Path $ResolvedLogDir).Path
$ResolvedRunDir = (Resolve-Path $ResolvedRunDir).Path
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BaseName = [IO.Path]::GetFileNameWithoutExtension($SourcePath)
$LogPath = Join-Path $ResolvedLogDir "$BaseName`_$Stamp.log"
$JournalPath = Join-Path $ResolvedLogDir "$BaseName`_$Stamp.jou"

$Args = @(
    "-mode", $Mode,
    "-source", $SourcePath,
    "-log", $LogPath,
    "-journal", $JournalPath
)
if ($TclArgs.Count -gt 0) {
    $Args += "-tclargs"
    $Args += $TclArgs
}

$OldProjectRoot = $env:HDLFLOW_PROJECT_ROOT
$OldVivadoRoot = $env:HDLFLOW_VIVADO_ROOT
$OldVivadoLogDir = $env:HDLFLOW_VIVADO_LOG_DIR
$OldVivadoRunDir = $env:HDLFLOW_VIVADO_RUN_DIR
if ($ProjectRootForLogSweep) {
    $env:HDLFLOW_PROJECT_ROOT = $ProjectRootForLogSweep
    $env:HDLFLOW_VIVADO_ROOT = Join-Path $ProjectRootForLogSweep "output\fpga\vivado"
}
$env:HDLFLOW_VIVADO_LOG_DIR = $ResolvedLogDir
$env:HDLFLOW_VIVADO_RUN_DIR = $ResolvedRunDir

Push-Location $ResolvedRunDir
$ExitCode = 1
try {
    & $Vivado @Args
    $ExitCode = $LASTEXITCODE
}
finally {
    Pop-Location
    $env:HDLFLOW_PROJECT_ROOT = $OldProjectRoot
    $env:HDLFLOW_VIVADO_ROOT = $OldVivadoRoot
    $env:HDLFLOW_VIVADO_LOG_DIR = $OldVivadoLogDir
    $env:HDLFLOW_VIVADO_RUN_DIR = $OldVivadoRunDir
    if ($ProjectRootForLogSweep) {
        Move-HdlVivadoProjectRootLogs -ProjectRoot $ProjectRootForLogSweep -ControlledLogDir $ResolvedLogDir
    }
}
Write-Host "vivado_log=$LogPath"
Write-Host "vivado_journal=$JournalPath"
Write-Host "vivado_run_dir=$ResolvedRunDir"
exit $ExitCode
