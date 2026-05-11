param(
    [string]$WorkspaceRoot = ".",
    [string]$ProjectPath = ""
)

. (Join-Path $PSScriptRoot "HdlHook.Common.ps1")

$workspace = Find-HdlWorkspaceRoot -StartPath $WorkspaceRoot
$project = Resolve-HdlProjectRoot -ProjectPath $ProjectPath -WorkspaceRoot $workspace
$projectName = Split-Path $project -Leaf
$checks = @(
    "config\global\workspace_config.yaml",
    "config\projects\$projectName\project_config.yaml",
    "skills\hdl-workflow-orchestrator\SKILL.md",
    ".codex\hooks.json",
    ".omx"
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

