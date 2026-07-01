param(
    [Parameter(Mandatory = $true)]
    [string]$Project,

    [string]$WorkspacePath = ".",

    [string]$SerialPort = "COM3",

    [int]$BaudRate = 115200,

    [int]$CaptureSeconds = 60,

    [string]$Command = "read;suite",

    [switch]$SkipProgram,

    [switch]$SkipPsRun
)

$ErrorActionPreference = "Stop"

function Get-HdlTimestamp {
    return (Get-Date).ToString("HH:mm:ss.fff")
}

function Wait-HdlJobOrThrow {
    param(
        [Parameter(Mandatory = $true)]
        [System.Management.Automation.Job]$Job,

        [int]$TimeoutSeconds = 180,

        [string]$Name = "background job"
    )

    $completed = Wait-Job $Job -Timeout $TimeoutSeconds
    if (-not $completed) {
        Stop-Job $Job
        Receive-Job $Job | ForEach-Object { Write-Host $_ }
        Remove-Job $Job -Force
        throw "$Name did not finish within $TimeoutSeconds seconds"
    }

    Receive-Job $Job | ForEach-Object { Write-Host $_ }
    $state = $Job.State
    Remove-Job $Job -Force
    if ($state -ne "Completed") {
        throw "$Name failed with state $state"
    }
}

$Workspace = Resolve-Path $WorkspacePath
$ProjectRoot = Resolve-Path $Project
$env:PYTHONPATH = Join-Path $Workspace "env\core"

& python -m hdlflow.cli workflow-stage-guard --project $ProjectRoot.Path --stage loop3-preflight --action "Invoke-HdlLoop3BoardVerify"
if ($LASTEXITCODE -ne 0) {
    throw "HDL workflow stage guard blocked Invoke-HdlLoop3BoardVerify"
}

$SerialDir = Join-Path $ProjectRoot "output\reports\loop3\serial"
$RawLog = Join-Path $SerialDir "latest_serial_text.log"
$ValidationReport = Join-Path $SerialDir "latest_serial_validation_report.md"
$VivadoProgramScript = Join-Path $ProjectRoot "output\fpga\vivado\scripts\program_bitstream.tcl"
$VitisBuildScript = Join-Path $ProjectRoot "output\fpga\vitis\scripts\build_ps_app_xsct.tcl"
$VitisRunScript = Join-Path $ProjectRoot "output\fpga\vitis\scripts\run_ps_app_jtag_xsct.tcl"
$VivadoWrapper = Join-Path $PSScriptRoot "Invoke-HdlVivado.ps1"
$VitisWrapper = Join-Path $PSScriptRoot "Invoke-HdlVitis.ps1"

New-Item -ItemType Directory -Force -Path $SerialDir | Out-Null

if ((-not $SkipProgram) -and (Test-Path -LiteralPath $VivadoProgramScript)) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $VivadoWrapper -WorkspacePath $Workspace.Path -Project $ProjectRoot.Path -Source $VivadoProgramScript
    if ($LASTEXITCODE -ne 0) {
        throw "Vivado board programming failed with code $LASTEXITCODE"
    }
}

if ((-not $SkipPsRun) -and (Test-Path -LiteralPath $VitisBuildScript)) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $VitisWrapper -WorkspacePath $Workspace.Path -Project $ProjectRoot.Path -Tool xsct -Source $VitisBuildScript
    if ($LASTEXITCODE -ne 0) {
        throw "PS application build failed with code $LASTEXITCODE"
    }
}

$RunJob = $null
if ((-not $SkipPsRun) -and (Test-Path -LiteralPath $VitisRunScript)) {
    $RunJob = Start-Job -ScriptBlock {
        param($wrapper, $workspace, $project, $source)
        & powershell -NoProfile -ExecutionPolicy Bypass -File $wrapper -WorkspacePath $workspace -Project $project -Tool xsct -Source $source
        if ($LASTEXITCODE -ne 0) {
            throw "PS application JTAG run failed with code $LASTEXITCODE"
        }
    } -ArgumentList $VitisWrapper, $Workspace.Path, $ProjectRoot.Path, $VitisRunScript
}

if ($RunJob) {
    Wait-HdlJobOrThrow -Job $RunJob -TimeoutSeconds 180 -Name "PS application JTAG run"
    $RunJob = $null
    Start-Sleep -Milliseconds 500
}

$AvailablePorts = [System.IO.Ports.SerialPort]::GetPortNames()
if ($AvailablePorts -notcontains $SerialPort) {
    $available = $AvailablePorts -join ", "
    throw "Serial port $SerialPort not found. Available ports: $available"
}

$RawLines = New-Object System.Collections.Generic.List[string]
$RxPayloads = New-Object System.Collections.Generic.List[string]
$TxLines = New-Object System.Collections.Generic.List[string]
$CommandList = @(
    $Command -split "[,;]" |
        ForEach-Object { $_.Trim() } |
        Where-Object { $_.Length -gt 0 }
)
if ($CommandList.Count -eq 0) {
    $CommandList = @("read")
}
$CurrentCommandIndex = 0
$CommandSent = $false
$ReadMatched = $false
$SuiteMatched = $false
$SuiteFailed = $false
$CheckFailed = $false
$serial = New-Object System.IO.Ports.SerialPort $SerialPort, $BaudRate, "None", 8, "One"
$serial.ReadTimeout = 200
$serial.WriteTimeout = 1000
$serial.NewLine = "`n"

try {
    $serial.Open()
    Start-Sleep -Milliseconds 200
    $serial.DiscardInBuffer()
    $serial.DiscardOutBuffer()

    $deadline = (Get-Date).AddSeconds($CaptureSeconds)
    $nextCommandAt = Get-Date
    while ((Get-Date) -lt $deadline) {
        if (($CurrentCommandIndex -ge $CommandList.Count) -and $ReadMatched -and (-not ($CommandList -contains "suite") -or $SuiteMatched)) {
            break
        }
        if ((Get-Date) -ge $nextCommandAt -and $CurrentCommandIndex -lt $CommandList.Count) {
            $ActiveCommand = $CommandList[$CurrentCommandIndex]
            $serial.Write("$ActiveCommand`r")
            $stamp = Get-HdlTimestamp
            $line = "TX[$stamp]: $ActiveCommand"
            $TxLines.Add($line)
            $RawLines.Add($line)
            $CommandSent = $true
            $nextCommandAt = (Get-Date).AddSeconds(6)
        }
        try {
            $line = $serial.ReadLine()
            if ($null -ne $line) {
                $payload = $line.Trim()
                if ($payload.Length -gt 0) {
                    $stamp = Get-HdlTimestamp
                    $entry = "RX[$stamp]: $payload"
                    $RawLines.Add($entry)
                    $RxPayloads.Add($payload)
                    if ($payload -match "^read data=0x[0-9A-Fa-f]{8}$") {
                        $ReadMatched = $true
                        if ($CurrentCommandIndex -lt $CommandList.Count -and $CommandList[$CurrentCommandIndex] -match "^(read|r)$") {
                            $CurrentCommandIndex++
                            $CommandSent = $false
                            $nextCommandAt = Get-Date
                        }
                    }
                    if ($payload -match "^LOOP3_CHECK .* FAIL\b") {
                        $CheckFailed = $true
                    }
                    if ($payload -match "^LOOP3_SUITE FAIL\b") {
                        $SuiteFailed = $true
                    }
                    if ($payload -match "^LOOP3_SUITE PASS\b") {
                        $SuiteMatched = $true
                        if ($CurrentCommandIndex -lt $CommandList.Count -and $CommandList[$CurrentCommandIndex] -match "^(suite|s)$") {
                            $CurrentCommandIndex++
                            $CommandSent = $false
                            $nextCommandAt = Get-Date
                        }
                    }
                    if ($CommandSent -and $CurrentCommandIndex -lt $CommandList.Count -and $CommandList[$CurrentCommandIndex] -notmatch "^(read|r|suite|s)$") {
                        $CurrentCommandIndex++
                        $CommandSent = $false
                        $nextCommandAt = Get-Date
                    }
                }
            }
        }
        catch [TimeoutException] {
        }
    }
}
finally {
    if ($serial.IsOpen) {
        $serial.Close()
    }
    if ($RunJob) {
        Wait-Job $RunJob -Timeout 30 | Out-Null
        if ($RunJob.State -ne "Completed") {
            Stop-Job $RunJob
        }
        Receive-Job $RunJob | ForEach-Object { Write-Host $_ }
        Remove-Job $RunJob -Force
    }
}

$MatchedPayload = $RxPayloads | Where-Object { $_ -match "^read data=0x[0-9A-Fa-f]{8}$" } | Select-Object -First 1
$TxReport = if ($TxLines.Count -gt 0) { $TxLines[0] } else { "TX[$(Get-HdlTimestamp)]: <not sent>" }

if ($MatchedPayload -and (-not ($CommandList -contains "suite") -or $SuiteMatched) -and (-not $SuiteFailed) -and (-not $CheckFailed)) {
    $rxReport = "RX[$(Get-HdlTimestamp)]: $MatchedPayload"
    $RawLines.Add("LOOP3_RESULT PASS")
    Set-Content -Path $RawLog -Value $RawLines -Encoding ASCII
    Set-Content -Path $ValidationReport -Value @(
        "# Loop3 Serial Validation",
        "",
        "- port: $SerialPort",
        "- baud: $BaudRate",
        "- $TxReport",
        "- $rxReport",
        "- suite: $(if ($CommandList -contains "suite") { "PASS" } else { "not-requested" })",
        "- result: PASS",
        "",
        "## Captured Lines",
        '```text',
        ($RawLines -join "`n"),
        '```'
    ) -Encoding ASCII
    Write-Host "LOOP3_BOARD_VERIFY_PASS payload=$MatchedPayload suite=$SuiteMatched"
    exit 0
}

$FailureReason = "read response not observed"
if ($MatchedPayload -and ($CommandList -contains "suite") -and (-not $SuiteMatched)) {
    $FailureReason = "suite PASS marker not observed"
}
if ($SuiteFailed) {
    $FailureReason = "suite reported FAIL"
}
if ($CheckFailed) {
    $FailureReason = "one or more LOOP3_CHECK lines reported FAIL"
}
$RawLines.Add("DUT_PROTOCOL_MODEL FAIL $FailureReason")
$RawLines.Add("LOOP3_RESULT FAIL")
Set-Content -Path $RawLog -Value $RawLines -Encoding ASCII
Set-Content -Path $ValidationReport -Value @(
    "# Loop3 Serial Validation",
    "",
    "- port: $SerialPort",
    "- baud: $BaudRate",
    "- $TxReport",
    "- RX[$(Get-HdlTimestamp)]: <not observed>",
    "- result: FAIL",
    "",
    "## Captured Lines",
    '```text',
    ($RawLines -join "`n"),
    '```'
) -Encoding ASCII

throw "Loop3 board validation failed on $SerialPort within $CaptureSeconds seconds: $FailureReason"
