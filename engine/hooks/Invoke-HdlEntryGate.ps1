param(
    [string]$WorkspaceRoot = ".",
    [string]$ProjectPath = ""
)

. (Join-Path $PSScriptRoot "HdlHook.Common.ps1")

$workspace = Find-HdlWorkspaceRoot -StartPath $WorkspaceRoot
try {
    $project = Resolve-HdlProjectRoot -ProjectPath $ProjectPath -WorkspaceRoot $workspace
    $projectName = Split-Path $project -Leaf
    $activeProject = $projectName
}
catch {
    $project = ""
    $projectName = ""
    $activeProject = ""
}
$omx = Join-Path $workspace ".omx"
Ensure-HdlDirectory -Path $omx
$state = Write-HdlWorkspaceStateIndex -WorkspaceRoot $workspace -ActiveProject $activeProject
$projects = @($state.projects)

$notepad = Join-Path $omx "notepad.md"
$lines = @(
    "# HDL Workflow Context",
    "",
    "- workspace: $workspace",
    "- active_project: $(if ($projectName) { $projectName } else { 'UNSET' })",
    "- authority: project-local memory under projects/<name>/memory is authoritative; .omx is only a multi-project runtime index",
    "- canonical_sources: projects/<name>/05_Output/rtl, tb, uvm",
    "- canonical_reports: projects/<name>/05_Output/reports",
    "- legacy_boundary: legacy workspace data is read-only unless the user explicitly asks for migration input",
    "- updated_at: $(Get-HdlHookTimestamp)",
    "",
    "## Projects"
)
foreach ($record in $projects) {
    $activeMark = if ($record.name -eq $projectName) { " active" } else { "" }
    $summary = if ($record.latest_summary) { $record.latest_summary } else { "no latest summary" }
    $node = if ($record.active_node) { $record.active_node } else { "unknown" }
    $lines += "- $($record.name)$activeMark | node=$node | $summary"
}
Set-Content -Path $notepad -Value $lines -Encoding UTF8

Write-HdlHookDecision -Decision approve -Reason "Test HDL context restored" -Additional ([pscustomobject]@{
    workspace = $workspace
    project = $project
    notepad = $notepad
    project_count = $projects.Count
})
