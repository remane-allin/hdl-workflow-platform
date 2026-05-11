param(
    [string]$WorkspaceRoot = ".",
    [string]$ProjectPath = ""
)

. (Join-Path $PSScriptRoot "HdlHook.Common.ps1")

$workspace = Find-HdlWorkspaceRoot -StartPath $WorkspaceRoot
try {
    $project = Resolve-HdlProjectRoot -ProjectPath $ProjectPath -WorkspaceRoot $workspace
}
catch {
    Write-HdlHookDecision -Decision approve -Reason "No local HDL project detected; state sync skipped"
    exit 0
}
$projectName = Split-Path $project -Leaf
$stateDir = Join-Path $workspace ".omx\state"
Ensure-HdlDirectory -Path $stateDir

$state = [ordered]@{
    workspace = $workspace
    project = $projectName
    updated_at = Get-HdlHookTimestamp
    config = "config/projects/$projectName/project_config.yaml"
    output = "projects/$projectName/05_Output"
}
Write-HdlJsonAtomic -Data $state -Path (Join-Path $stateDir "hdl-workflow-state.json")
Write-HdlHookDecision -Decision approve -Reason "Test HDL state synced"
