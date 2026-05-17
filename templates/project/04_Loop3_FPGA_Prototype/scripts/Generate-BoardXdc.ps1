param(
    [string]$Output = ''
)

$ErrorActionPreference = 'Stop'
$projectRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$workspaceRoot = Resolve-Path (Join-Path $projectRoot '..\..')
$engineRoot = Join-Path $workspaceRoot 'engine'

Push-Location $engineRoot
try {
    $xdcArgs = @('-m', 'hdlflow.cli', 'generate-xdc', '--workspace', '..', '--project', $projectRoot)
    if ($Output) {
        $xdcArgs += @('--output', $Output)
    }
    & python @xdcArgs
    if ($LASTEXITCODE -ne 0) { throw "generate-xdc failed with code $LASTEXITCODE" }
}
finally {
    Pop-Location
}

$outputSource = if ($Output) { $Output } else { 'project_config' }
Write-Host "BOARD_XDC_GENERATE_PASS output=$outputSource"
