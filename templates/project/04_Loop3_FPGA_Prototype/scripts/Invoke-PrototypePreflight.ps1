param(
    [ValidateSet('pl', 'ps_pl')]
    [string]$Mode = 'pl',
    [string]$Board = ''
)

$ErrorActionPreference = 'Stop'
$projectRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$workspaceRoot = Resolve-Path (Join-Path $projectRoot '..\..')
$engineRoot = Join-Path $workspaceRoot 'engine'

Push-Location $engineRoot
try {
    $preflightArgs = @('-m', 'hdlflow.cli', 'prototype-preflight', '--workspace', '..', '--project', $projectRoot, '--mode', $Mode)
    if ($Board) {
        $preflightArgs += @('--board', $Board)
    }
    & python @preflightArgs
    if ($LASTEXITCODE -ne 0) { throw "prototype-preflight failed with code $LASTEXITCODE" }
    & python -m hdlflow.cli validate-prototype-plan --workspace .. --project $projectRoot
    if ($LASTEXITCODE -ne 0) { throw "validate-prototype-plan failed with code $LASTEXITCODE" }
}
finally {
    Pop-Location
}

$boardSource = if ($Board) { $Board } else { 'project_config' }
Write-Host "PROTOTYPE_PREFLIGHT_PASS mode=$Mode board=$boardSource"
