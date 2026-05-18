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

    $current = (Get-Location).Path
    while ($current) {
        $projectMarker = Join-Path $current "project_scaffold.yaml"
        if ((Test-Path $projectMarker) -and (Test-Path (Join-Path $current "05_Output"))) {
            $candidateRoot = Join-Path $workspace "projects"
            $resolvedCurrent = (Resolve-Path $current).Path
            try {
                $null = Resolve-Path $candidateRoot
                $relative = Get-HdlRelativePath -BasePath (Resolve-Path $candidateRoot).Path -ChildPath $resolvedCurrent
                if (-not $relative.StartsWith("..")) {
                    return $resolvedCurrent
                }
            }
            catch {
                return $resolvedCurrent
            }
        }
        $parent = Split-Path $current -Parent
        if ($parent -eq $current -or [string]::IsNullOrWhiteSpace($parent)) {
            break
        }
        $current = $parent
    }

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

function Get-HdlRelativePath {
    param(
        [Parameter(Mandatory = $true)][string]$BasePath,
        [Parameter(Mandatory = $true)][string]$ChildPath
    )

    $baseFull = [System.IO.Path]::GetFullPath($BasePath)
    $childFull = [System.IO.Path]::GetFullPath($ChildPath)
    if (-not $baseFull.EndsWith([System.IO.Path]::DirectorySeparatorChar)) {
        $baseFull += [System.IO.Path]::DirectorySeparatorChar
    }
    $baseUri = New-Object System.Uri($baseFull)
    $childUri = New-Object System.Uri($childFull)
    return [System.Uri]::UnescapeDataString($baseUri.MakeRelativeUri($childUri).ToString()).Replace("/", "\")
}

function Get-HdlProjectRecords {
    param([Parameter(Mandatory = $true)][string]$WorkspaceRoot)

    $workspace = (Resolve-Path $WorkspaceRoot).Path
    $projectsRoot = Join-Path $workspace "projects"
    if (-not (Test-Path $projectsRoot)) {
        return @()
    }

    return @(Get-ChildItem -Path $projectsRoot -Directory | Where-Object {
        (Test-Path (Join-Path $_.FullName "project_scaffold.yaml")) -and
        (Test-Path (Join-Path $_.FullName "05_Output"))
    } | Sort-Object Name | ForEach-Object {
        $projectName = $_.Name
        $statePath = Join-Path $_.FullName "memory\00_global\CURRENT_STATE.md"
        $loopStatePath = Join-Path $_.FullName "loop\loop_state.json"
        $activeNode = ""
        $latestSummary = ""
        if (Test-Path $loopStatePath) {
            try {
                $loopState = Get-Content -Path $loopStatePath -Raw | ConvertFrom-Json
                $loopName = [string]$loopState.current_loop
                $activeNode = Convert-HdlLoopNameToNode -LoopName $loopName
                $latestSummary = ("{0}; current_loop={1}" -f $loopState.overall_status, $loopName)
            }
            catch {
                $activeNode = ""
                $latestSummary = ""
            }
        }
        if ((-not $activeNode) -and (Test-Path $statePath)) {
            foreach ($line in Get-Content -Path $statePath) {
                if ($line -match '^\s*-\s*active_node:\s*(.+)\s*$') {
                    $activeNode = $Matches[1].Trim()
                }
                elseif ($line -match '^\s*-\s*latest_summary:\s*(.+)\s*$') {
                    $latestSummary = $Matches[1].Trim()
                }
            }
        }
        [ordered]@{
            name = $projectName
            path = $_.FullName
            config = "config/projects/$projectName/project_config.yaml"
            output = "projects/$projectName/05_Output"
            memory = "projects/$projectName/memory"
            active_node = $activeNode
            latest_summary = $latestSummary
        }
    })
}

function Convert-HdlLoopNameToNode {
    param([string]$LoopName)

    switch ($LoopName) {
        "spec" { return "00_SPEC" }
        "docparse" { return "01_DocParse" }
        "loop1" { return "02_Loop1_RTL_TB" }
        "loop2" { return "03_Loop2_UVM_Verify" }
        "loop3" { return "04_Loop3_FPGA_Prototype" }
        "final" { return "05_Output" }
        "complete" { return "05_Output" }
        default { return "" }
    }
}

function Write-HdlWorkspaceStateIndex {
    param(
        [Parameter(Mandatory = $true)][string]$WorkspaceRoot,
        [string]$ActiveProject = ""
    )

    $workspace = (Resolve-Path $WorkspaceRoot).Path
    $stateDir = Join-Path $workspace ".omx\state"
    Ensure-HdlDirectory -Path $stateDir
    $projects = @(Get-HdlProjectRecords -WorkspaceRoot $workspace)
    $state = [ordered]@{
        schema_version = 2
        workspace = $workspace
        updated_at = Get-HdlHookTimestamp
        authority = "Project-local memory under projects/<name>/memory is authoritative; .omx is a multi-project runtime index only."
        active_project = if ($ActiveProject) { $ActiveProject } else { $null }
        projects = @($projects)
    }
    Write-HdlJsonAtomic -Data $state -Path (Join-Path $stateDir "hdl-workflow-state.json")
    return $state
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
    $tmp = "$Path.$([System.Guid]::NewGuid().ToString('N')).tmp"
    $json = $Data | ConvertTo-Json -Depth 16
    Set-Content -Path $tmp -Value $json -Encoding UTF8
    $json | ConvertFrom-Json | Out-Null
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
