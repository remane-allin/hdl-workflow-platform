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
    Write-HdlHookDecision -Decision approve -Reason "No local HDL project detected; workspace context restore skipped"
    exit 0
}
$projectName = Split-Path $project -Leaf
$omx = Join-Path $workspace ".omx"
Ensure-HdlDirectory -Path $omx

$notepad = Join-Path $omx "notepad.md"
$lines = @(
    "# HDL Workflow Context",
    "",
    "- workspace: $workspace",
    "- project: $projectName",
    "- project_config: config/projects/$projectName/project_config.yaml",
    "- canonical_sources: 05_Output/rtl, 05_Output/tb, 05_Output/uvm",
    "- canonical_reports: 05_Output/reports",
    "- legacy_boundary: legacy workspace data is read-only unless the user explicitly asks for migration input",
    "- updated_at: $(Get-HdlHookTimestamp)"
)
Set-Content -Path $notepad -Value $lines -Encoding UTF8

Write-HdlHookDecision -Decision approve -Reason "Test HDL context restored" -Additional ([pscustomobject]@{
    workspace = $workspace
    project = $project
    notepad = $notepad
})
