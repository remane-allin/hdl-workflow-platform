param(
    [string]$Output = '05_Output/fpga/vivado/scripts/generated_ps_pl_bd.tcl'
)

$ErrorActionPreference = 'Stop'
$projectRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$workspaceRoot = Resolve-Path (Join-Path $projectRoot '..\..')
$engineRoot = Join-Path $workspaceRoot 'engine'

Push-Location $engineRoot
try {
    & python -m hdlflow.cli generate-ps-pl-bd --project $projectRoot --output $Output
    if ($LASTEXITCODE -ne 0) { throw "generate-ps-pl-bd failed with code $LASTEXITCODE" }
}
finally {
    Pop-Location
}

Write-Host "PS_PL_BD_GENERATE_PASS output=$Output"
