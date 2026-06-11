param(
    [Parameter(Mandatory = $true)]
    [string]$Project,

    [string]$WorkspacePath = ".",

    [string]$SerialPort = "COM3",

    [int]$BaudRate = 115200,

    [int]$CaptureSeconds = 18,

    [string]$Command = "read",

    [switch]$SkipProgram,

    [switch]$SkipPsRun
)

$ErrorActionPreference = "Stop"

function Get-HdlTimestamp {
    return (Get-Date).ToString("HH:mm:ss.fff")
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
        exit $LASTEXITCODE
    } -ArgumentList $VitisWrapper, $Workspace.Path, $ProjectRoot.Path, $VitisRunScript
}

$AvailablePorts = [System.IO.Ports.SerialPort]::GetPortNames()
if ($AvailablePorts -notcontains $SerialPort) {
    $available = $AvailablePorts -join ", "
    throw "Serial port $SerialPort not found. Available ports: $available"
}

$RawLines = New-Object System.Collections.Generic.List[string]
$RxPayloads = New-Object System.Collections.Generic.List[string]
$TxLines = New-Object System.Collections.Generic.List[string]
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
        $matched = $RxPayloads | Where-Object { $_ -match "^read data=0x[0-9A-Fa-f]{8}$" } | Select-Object -First 1
        if ($matched) {
            break
        }
        if ((Get-Date) -ge $nextCommandAt) {
            $serial.Write("$Command`r")
            $stamp = Get-HdlTimestamp
            $line = "TX[$stamp]: $Command"
            $TxLines.Add($line)
            $RawLines.Add($line)
            $nextCommandAt = (Get-Date).AddSeconds(2)
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
        Wait-Job $RunJob -Timeout 5 | Out-Null
        if ($RunJob.State -ne "Completed") {
            Stop-Job $RunJob -Force
        }
        Remove-Job $RunJob -Force
    }
}

$MatchedPayload = $RxPayloads | Where-Object { $_ -match "^read data=0x[0-9A-Fa-f]{8}$" } | Select-Object -First 1
$TxReport = if ($TxLines.Count -gt 0) { $TxLines[0] } else { "TX[$(Get-HdlTimestamp)]: <not sent>" }

if ($MatchedPayload) {
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
        "- result: PASS"
    ) -Encoding ASCII
    Write-Host "LOOP3_BOARD_VERIFY_PASS payload=$MatchedPayload"
    exit 0
}

$RawLines.Add("DUT_PROTOCOL_MODEL FAIL read response not observed")
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

throw "No PL UART read data line observed on $SerialPort within $CaptureSeconds seconds"
