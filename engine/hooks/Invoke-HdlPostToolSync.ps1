param(
    [string]$WorkspaceRoot = ".",
    [string]$ProjectPath = ""
)

. (Join-Path $PSScriptRoot "HdlHook.Common.ps1")

$workspace = Find-HdlWorkspaceRoot -StartPath $WorkspaceRoot
try {
    $project = Resolve-HdlProjectRoot -ProjectPath $ProjectPath -WorkspaceRoot $workspace
    $projectName = Split-Path $project -Leaf
}
catch {
    $state = Write-HdlWorkspaceStateIndex -WorkspaceRoot $workspace
    Write-HdlHookDecision -Decision approve -Reason "No active HDL project inferred; multi-project state index synced" -Additional ([pscustomobject]@{
        state = ".omx/state/hdl-workflow-state.json"
        project_count = @($state.projects).Count
    })
    exit 0
}

$state = Write-HdlWorkspaceStateIndex -WorkspaceRoot $workspace -ActiveProject $projectName
Write-HdlHookDecision -Decision approve -Reason "Test HDL multi-project state index synced" -Additional ([pscustomobject]@{
    active_project = $projectName
    project_count = @($state.projects).Count
})
