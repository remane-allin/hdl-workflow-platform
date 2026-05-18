param(
    [Parameter(Mandatory = $true)]
    [string]$Source,

    [string]$Project = "",

    [string]$WorkspacePath = ".",

    [string]$Mode = "batch",

    [string]$LogDir = "",

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$TclArgs
)

$ErrorActionPreference = "Stop"

$Workspace = Resolve-Path $WorkspacePath
$SourcePath = Resolve-Path $Source
$Vivado = (& python -m hdlflow.cli get-tool-launcher --workspace $Workspace --tool vivado --launcher vivado_bat).Trim()
if (-not $Vivado) {
    throw "Vivado vivado_bat is not configured in config/global/toolchains/toolchains.yaml"
}
if (-not (Test-Path $Vivado)) {
    throw "Vivado launcher not found: $Vivado"
}

if ($LogDir) {
    $ResolvedLogDir = $LogDir
}
elseif ($Project) {
    $ProjectPath = Resolve-Path $Project
    $ResolvedLogDir = Join-Path $ProjectPath "05_Output\fpga\vivado\logs"
}
else {
    $ResolvedLogDir = Join-Path $Workspace ".Xil\launch_logs"
}

New-Item -ItemType Directory -Force -Path $ResolvedLogDir | Out-Null
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

& $Vivado @Args
$ExitCode = $LASTEXITCODE
Write-Host "vivado_log=$LogPath"
Write-Host "vivado_journal=$JournalPath"
exit $ExitCode
