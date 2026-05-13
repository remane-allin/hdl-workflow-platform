param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Za-z0-9_][A-Za-z0-9_-]*$')]
    [string]$Name,

    [switch]$Force
)

$ErrorActionPreference = 'Stop'

$workspaceRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$engineRoot = Join-Path $workspaceRoot 'engine'
$projectPath = Join-Path $workspaceRoot "projects\$Name"

Push-Location $engineRoot
try {
    $argsList = @('-m', 'hdlflow.cli', 'init-project', $Name, '--workspace', '..')
    if ($Force) {
        $argsList += '--force'
    }
    & python @argsList
    if ($LASTEXITCODE -ne 0) {
        throw "hdlflow init-project failed with code $LASTEXITCODE"
    }

    & python -m hdlflow.cli doctor --workspace .. --project "..\projects\$Name"
    if ($LASTEXITCODE -ne 0) {
        throw "hdlflow doctor failed with code $LASTEXITCODE"
    }

    & python -m hdlflow.cli ensure-output --project "..\projects\$Name"
    if ($LASTEXITCODE -ne 0) {
        throw "hdlflow ensure-output failed with code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}

Write-Host "HDL_PROJECT_CREATE_PASS project=$projectPath"
