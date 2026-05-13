param(
    [ValidateSet('pl', 'ps_pl')]
    [string]$Mode = 'pl',
    [string]$Board = 'navigator_zynq_7020'
)

$ErrorActionPreference = 'Stop'
$projectRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$workspaceRoot = Resolve-Path (Join-Path $projectRoot '..\..')
$engineRoot = Join-Path $workspaceRoot 'engine'

Push-Location $engineRoot
try {
    & python -m hdlflow.cli prototype-preflight --workspace .. --project $projectRoot --mode $Mode --board $Board
    if ($LASTEXITCODE -ne 0) { throw "prototype-preflight failed with code $LASTEXITCODE" }
    & python -m hdlflow.cli validate-prototype-plan --workspace .. --project $projectRoot
    if ($LASTEXITCODE -ne 0) { throw "validate-prototype-plan failed with code $LASTEXITCODE" }
}
finally {
    Pop-Location
}

Write-Host "PROTOTYPE_PREFLIGHT_PASS mode=$Mode board=$Board"
