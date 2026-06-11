param(
    [string]$WorkspaceRoot = ".",
    [string]$ProjectPath = ""
)

. (Join-Path $PSScriptRoot "HdlHook.Common.ps1")

$workspace = Find-HdlWorkspaceRoot -StartPath $WorkspaceRoot
$project = Resolve-HdlProjectRoot -ProjectPath $ProjectPath -WorkspaceRoot $workspace
$projectName = Split-Path $project -Leaf
$checks = @(
    "env\rule\global\workspace_config.yaml",
    "prj\$projectName\work\config\project_config.yaml",
    "env\rule\skills\hdl-workflow-orchestrator\SKILL.md",
    "env\rule\agents\codex\hooks.json",
    "local\runtime\omx"
)

$missing = @()
foreach ($rel in $checks) {
    if (-not (Test-Path (Join-Path $workspace $rel))) {
        $missing += $rel
    }
}

if ($missing.Count -gt 0) {
    Write-Host "FAIL"
    foreach ($item in $missing) {
        Write-Host "missing: $item"
    }
    exit 1
}

Write-Host "PASS"
Write-Host "workspace: $workspace"
Write-Host "project: $project"
Write-Host "hooks: $($checks.Count) checks"
