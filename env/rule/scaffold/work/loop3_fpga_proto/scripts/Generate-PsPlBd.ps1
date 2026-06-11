param(
    [string]$Output = ''
)

$ErrorActionPreference = 'Stop'
$projectRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..\..')
$workspaceRoot = Resolve-Path (Join-Path $projectRoot '..\..')
$engineRoot = Join-Path $workspaceRoot 'env\core'

Push-Location $engineRoot
try {
    $bdArgs = @('-m', 'hdlflow.cli', 'generate-ps-pl-bd', '--workspace', $workspaceRoot, '--project', $projectRoot)
    if ($Output) {
        $bdArgs += @('--output', $Output)
    }
    & python @bdArgs
    if ($LASTEXITCODE -ne 0) { throw "generate-ps-pl-bd failed with code $LASTEXITCODE" }
}
finally {
    Pop-Location
}

$outputSource = if ($Output) { $Output } else { 'project_config' }
Write-Host "PS_PL_BD_GENERATE_PASS output=$outputSource"
