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
    Write-HdlHookDecision -Decision approve -Reason "No local HDL project detected; checkpoint skipped"
    exit 0
}
$projectName = Split-Path $project -Leaf
$memoryRoot = Join-Path $project "memory\00_global"
$currentState = Join-Path $memoryRoot "CURRENT_STATE.md"
$omx = Join-Path $workspace ".omx"
Ensure-HdlDirectory -Path $omx

$summary = if (Test-Path $currentState) {
    (Get-Content -Path $currentState -Raw).Trim()
}
else {
    "No CURRENT_STATE.md found."
}

$payload = [ordered]@{
    project = $projectName
    workspace = $workspace
    updated_at = Get-HdlHookTimestamp
    authority = "Test project files are authoritative; .omx is runtime summary only."
    memories = @(
        [ordered]@{
            scope = "current-state"
            summary = $summary
        },
        [ordered]@{
            scope = "canonical-layout"
            summary = "Configuration lives under config/. Editable deliverables live under 05_Output/. Legacy workspace data is migration input only."
        }
    )
}

Write-HdlJsonAtomic -Data $payload -Path (Join-Path $omx "project-memory.json")
Write-HdlHookDecision -Decision approve -Reason "Test HDL checkpoint written"
