param(
    [string]$Workspace = ".",
    [Parameter(Mandatory = $true)]
    [string]$Project,
    [Parameter(Mandatory = $true)]
    [ValidateSet("loop1", "loop2")]
    [string]$Loop,
    [string]$DoFile
)

$ErrorActionPreference = "Stop"

$WorkspacePath = (Resolve-Path -LiteralPath $Workspace).Path
$ProjectPath = (Resolve-Path -LiteralPath $Project).Path
$env:PYTHONPATH = Join-Path $WorkspacePath "env\core"
$ToolDefaults = Join-Path $WorkspacePath "env\tool\scripts\HdlToolDefaults.ps1"

if (-not $DoFile) {
    if ($Loop -eq "loop1") {
        $DoFile = Join-Path $ProjectPath "work/loop1_rtl_tb\sim\rtl_functional.do"
    }
    else {
        $DoFile = Join-Path $ProjectPath "work/loop2_uvm\sim\regression.do"
    }
}

$Stage = if ($Loop -eq "loop1") { "loop1" } else { "loop2" }
& python -m hdlflow.cli workflow-stage-guard --project $ProjectPath --stage $Stage --action "Invoke-HdlModelSim $Loop"
if ($LASTEXITCODE -ne 0) {
    throw "HDL workflow stage guard blocked Invoke-HdlModelSim $Loop"
}

if (Test-Path -LiteralPath $ToolDefaults) {
    . $ToolDefaults
    $Vsim = Resolve-HdlToolPath -WorkspacePath $WorkspacePath -Tool modelsim -Launcher vsim_exe
}
else {
    $Vsim = (& python -m hdlflow.cli get-tool-launcher --workspace $WorkspacePath --tool modelsim --launcher vsim_exe).Trim()
}
if (-not $Vsim) {
    throw "ModelSim vsim_exe is not configured in env/rule/global/toolchains/toolchains.yaml"
}
if (-not (Test-Path -LiteralPath $Vsim)) {
    throw "Configured ModelSim vsim_exe does not exist: $Vsim"
}
if (-not (Test-Path -LiteralPath $DoFile)) {
    throw "ModelSim do file does not exist: $DoFile"
}

Push-Location -LiteralPath $ProjectPath
try {
    & $Vsim -c -do $DoFile
    if ($LASTEXITCODE -ne 0) {
        throw "ModelSim exited with code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}
