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
    $project = ""
    $projectName = ""
}
$omx = Join-Path $workspace ".omx"
Ensure-HdlDirectory -Path $omx
$state = Write-HdlWorkspaceStateIndex -WorkspaceRoot $workspace -ActiveProject $projectName

if ($project) {
    $currentState = Join-Path $project "memory\00_global\CURRENT_STATE.md"
    $summary = if (Test-Path $currentState) {
        (Get-Content -Path $currentState -Raw).Trim()
    }
    else {
        "No CURRENT_STATE.md found."
    }
    $memories = @(
        [ordered]@{
            scope = "current-state"
            project = $projectName
            summary = $summary
        },
        [ordered]@{
            scope = "canonical-layout"
            summary = "Configuration lives under config/. Editable deliverables live under each project's 05_Output/. Legacy workspace data is migration input only."
        }
    )
}
else {
    $memories = @()
    foreach ($record in @($state.projects)) {
        $statePath = Join-Path $workspace ("projects\{0}\memory\00_global\CURRENT_STATE.md" -f $record.name)
        $summary = if (Test-Path $statePath) {
            (Get-Content -Path $statePath -Raw).Trim()
        }
        else {
            "No CURRENT_STATE.md found."
        }
        $memories += [ordered]@{
            scope = "current-state"
            project = $record.name
            summary = $summary
        }
    }
}

$payload = [ordered]@{
    schema_version = 2
    active_project = if ($projectName) { $projectName } else { $null }
    workspace = $workspace
    updated_at = Get-HdlHookTimestamp
    authority = "Test project files are authoritative; .omx is a multi-project runtime summary only."
    memories = $memories
}

Write-HdlJsonAtomic -Data $payload -Path (Join-Path $omx "project-memory.json")
Write-HdlHookDecision -Decision approve -Reason "Test HDL multi-project checkpoint written" -Additional ([pscustomobject]@{
    active_project = if ($projectName) { $projectName } else { $null }
    project_count = @($state.projects).Count
})
