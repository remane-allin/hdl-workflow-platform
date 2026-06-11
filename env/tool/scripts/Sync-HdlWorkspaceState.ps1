param(
    [string]$WorkspaceRoot = ".",
    [string]$ActiveProject = ""
)

$ErrorActionPreference = "Stop"

$hookRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..\core\hooks")
. (Join-Path $hookRoot "HdlHook.Common.ps1")

$workspace = Find-HdlWorkspaceRoot -StartPath $WorkspaceRoot
$state = Write-HdlWorkspaceStateIndex -WorkspaceRoot $workspace -ActiveProject $ActiveProject

Write-Host "HDL_WORKSPACE_STATE_SYNC_PASS state=local/runtime/omx/state/hdl-workflow-state.json"
Write-Host "active_project=$($state.active_project)"
Write-Host "project_count=$(@($state.projects).Count)"
Write-Host "orphan_config_count=$(@($state.orphan_project_configs).Count)"
foreach ($orphan in @($state.orphan_project_configs)) {
    Write-Host "orphan_config=$orphan"
}
