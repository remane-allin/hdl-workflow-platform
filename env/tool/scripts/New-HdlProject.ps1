param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Za-z0-9_][A-Za-z0-9_-]*$')]
    [string]$Name,

    [switch]$Force
)

$ErrorActionPreference = 'Stop'

$workspaceRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..\..')
$projectPath = Join-Path $workspaceRoot "prj\$Name"
$previousEntrypoint = $env:HDLFLOW_PROJECT_CREATE_ENTRYPOINT
$previousPythonPath = $env:PYTHONPATH
$env:HDLFLOW_PROJECT_CREATE_ENTRYPOINT = 'env/tool/scripts/New-HdlProject.ps1'
$env:PYTHONPATH = Join-Path $workspaceRoot 'env\core'

Push-Location $workspaceRoot
try {
    $argsList = @('-m', 'hdlflow.cli', 'init-project', $Name, '--workspace', '.')
    if ($Force) {
        $argsList += '--force'
    }
    & python @argsList
    if ($LASTEXITCODE -ne 0) {
        throw "hdlflow init-project failed with code $LASTEXITCODE"
    }

    & python -m hdlflow.cli ensure-output --project "prj\$Name"
    if ($LASTEXITCODE -ne 0) {
        throw "hdlflow ensure-output failed with code $LASTEXITCODE"
    }

    & python -m hdlflow.cli doctor --workspace . --project "prj\$Name"
    if ($LASTEXITCODE -ne 0) {
        throw "hdlflow doctor failed with code $LASTEXITCODE"
    }

    & python -m hdlflow.cli requirements-frontdoor-init --project "prj\$Name" --status DRAFT --force
    if ($LASTEXITCODE -ne 0) {
        throw "hdlflow requirements-frontdoor-init failed with code $LASTEXITCODE"
    }

    & python -m hdlflow.cli requirements-frontdoor-check --project "prj\$Name" --allow-draft
    if ($LASTEXITCODE -ne 0) {
        throw "hdlflow requirements-frontdoor-check failed with code $LASTEXITCODE"
    }

    $iterationId = "$($Name)_bootstrap_$(Get-Date -Format 'yyyyMMddHHmmss')"
    & python -m hdlflow.cli memory-record `
        --project "prj\$Name" `
        --iteration-id $iterationId `
        --node input `
        --gate-level develop `
        --gate-result PASS `
        --memory-record "work\memory\00_global\DECISIONS.md" `
        --report "output\reports\docparse\requirements_frontend_report.md" `
        --notes "Project created through env/tool/scripts/New-HdlProject.ps1." `
        --artifact "project_scaffold.yaml" `
        --artifact "work\config\project.yaml" `
        --artifact "work\docparse\frontdoor\srs.yaml" `
        --latest-summary "Project scaffold and six-agent frontdoor artifacts initialized as DRAFT." `
        --next-action "Add source requirements, then promote Spec Agent artifacts to READY after review." `
        --agent arbtr `
        --flow-direction forward `
        --arbtr-decision bootstrap_recorded `
        --baseline-version DRAFT-bootstrap
    if ($LASTEXITCODE -ne 0) {
        throw "hdlflow memory-record failed with code $LASTEXITCODE"
    }

    & python -m hdlflow.cli memory-check --project "prj\$Name"
    if ($LASTEXITCODE -ne 0) {
        throw "hdlflow memory-check failed with code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
    if ($null -eq $previousEntrypoint) {
        Remove-Item Env:\HDLFLOW_PROJECT_CREATE_ENTRYPOINT -ErrorAction SilentlyContinue
    }
    else {
        $env:HDLFLOW_PROJECT_CREATE_ENTRYPOINT = $previousEntrypoint
    }
    if ($null -eq $previousPythonPath) {
        Remove-Item Env:\PYTHONPATH -ErrorAction SilentlyContinue
    }
    else {
        $env:PYTHONPATH = $previousPythonPath
    }
}

Write-Host "HDL_PROJECT_CREATE_PASS project=$projectPath"
