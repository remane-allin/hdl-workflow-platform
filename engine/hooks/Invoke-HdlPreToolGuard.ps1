param(
    [string]$WorkspaceRoot = ".",
    [string]$ProjectPath = "",
    [string]$RawInput = ""
)

. (Join-Path $PSScriptRoot "HdlHook.Common.ps1")

$event = Read-HdlHookJson -RawInput $RawInput
$command = ""
if ($event -and $event.command) {
    $command = [string]$event.command
}
elseif ($event -and $event.tool_input -and $event.tool_input.command) {
    $command = [string]$event.tool_input.command
}

if (Test-HdlCommandLooksDestructive -Command $command) {
    Write-HdlHookDecision -Decision block -Continue $false -Reason "destructive command requires explicit user request"
    exit 0
}

Write-HdlHookDecision -Decision approve -Reason "Test HDL guard passed"
