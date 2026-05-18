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
$env:PYTHONPATH = Join-Path $WorkspacePath "engine"

if (-not $DoFile) {
    if ($Loop -eq "loop1") {
        $DoFile = Join-Path $ProjectPath "02_Loop1_RTL_TB\sim\rtl_functional.do"
    }
    else {
        $DoFile = Join-Path $ProjectPath "03_Loop2_UVM_Verify\sim\regression.do"
    }
}

$Vsim = (& python -m hdlflow.cli get-tool-launcher --workspace $WorkspacePath --tool modelsim --launcher vsim_exe).Trim()
if (-not $Vsim) {
    throw "ModelSim vsim_exe is not configured in config/global/toolchains/toolchains.yaml"
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
