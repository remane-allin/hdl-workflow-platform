Set-StrictMode -Version 2.0

function Get-HdlHookTimestamp {
    return (Get-Date).ToString("s")
}

function Find-HdlWorkspaceRoot {
    param([string]$StartPath = (Get-Location).Path)

    $current = (Resolve-Path $StartPath).Path
    while ($current) {
        if ((Test-Path (Join-Path $current "config\global\workspace_config.yaml")) -and
            (Test-Path (Join-Path $current "projects"))) {
            return $current
        }

        $parent = Split-Path $current -Parent
        if ($parent -eq $current -or [string]::IsNullOrWhiteSpace($parent)) {
            break
        }
        $current = $parent
    }

    $candidate = Join-Path (Get-Location).Path "Test"
    if (Test-Path (Join-Path $candidate "config\global\workspace_config.yaml")) {
        return (Resolve-Path $candidate).Path
    }

    throw "Unable to locate Test HDL workspace root from '$StartPath'."
}

function Resolve-HdlProjectRoot {
    param(
        [string]$ProjectPath,
        [string]$WorkspaceRoot
    )

    if ($ProjectPath) {
        $resolved = (Resolve-Path $ProjectPath).Path
        if (-not (Test-Path (Join-Path $resolved "05_Output"))) {
            throw "ProjectPath is not a Test HDL project: $resolved"
        }
        return $resolved
    }

    if ($env:HDL_PROJECT_PATH) {
        return Resolve-HdlProjectRoot -ProjectPath $env:HDL_PROJECT_PATH -WorkspaceRoot $WorkspaceRoot
    }

    $workspace = if ($WorkspaceRoot) { (Resolve-Path $WorkspaceRoot).Path } else { Find-HdlWorkspaceRoot }
    $projectsRoot = Join-Path $workspace "projects"
    $projects = @(Get-ChildItem -Path $projectsRoot -Directory | Where-Object {
        $config = Join-Path $workspace "config\projects\$($_.Name)\project_config.yaml"
        (Test-Path $config) -and (Test-Path (Join-Path $_.FullName "05_Output"))
    })

    if ($projects.Count -eq 1) {
        return $projects[0].FullName
    }

    throw "Unable to infer HDL project. Set HDL_PROJECT_PATH or pass -ProjectPath."
}

function Ensure-HdlDirectory {
    param([Parameter(Mandatory = $true)][string]$Path)
    if (-not (Test-Path $Path)) {
        New-Item -ItemType Directory -Path $Path | Out-Null
    }
}

function Read-HdlHookJson {
    param([string]$RawInput)

    if (-not $RawInput) {
        try {
            if (-not [Console]::IsInputRedirected) {
                return $null
            }
            $RawInput = [Console]::In.ReadToEnd()
        }
        catch {
            return $null
        }
    }

    if ([string]::IsNullOrWhiteSpace($RawInput)) {
        return $null
    }

    try {
        return $RawInput | ConvertFrom-Json
    }
    catch {
        return [pscustomobject]@{
            raw = $RawInput
            parse_error = $_.Exception.Message
        }
    }
}

function Write-HdlHookDecision {
    param(
        [ValidateSet("approve", "block")]
        [string]$Decision = "approve",
        [string]$Reason = "",
        [bool]$Continue = $true,
        $Additional = $null
    )

    $payload = [ordered]@{
        continue = $Continue
        decision = $Decision
        reason = $Reason
    }

    if ($Additional) {
        foreach ($property in $Additional.PSObject.Properties) {
            $payload[$property.Name] = $property.Value
        }
    }

    $payload | ConvertTo-Json -Depth 8
}

function Write-HdlJsonAtomic {
    param(
        [Parameter(Mandatory = $true)]$Data,
        [Parameter(Mandatory = $true)][string]$Path
    )

    $dir = Split-Path $Path -Parent
    Ensure-HdlDirectory -Path $dir
    $tmp = "$Path.tmp"
    $json = $Data | ConvertTo-Json -Depth 16
    Set-Content -Path $tmp -Value $json -Encoding UTF8
    Get-Content -Path $tmp -Raw | ConvertFrom-Json | Out-Null
    Move-Item -Path $tmp -Destination $Path -Force
}

function Test-HdlCommandLooksDestructive {
    param([string]$Command)

    if (-not $Command) {
        return $false
    }

    $patterns = @(
        "git\s+reset\s+--hard",
        "git\s+clean\s+-fdx",
        "\brm\s+-rf\b",
        "Remove-Item\s+.*-Recurse.*-Force",
        "Remove-Item\s+.*-Force.*-Recurse",
        "del\s+/s\s+/q",
        "rmdir\s+/s\s+/q"
    )

    foreach ($pattern in $patterns) {
        if ($Command -match $pattern) {
            return $true
        }
    }

    return $false
}

