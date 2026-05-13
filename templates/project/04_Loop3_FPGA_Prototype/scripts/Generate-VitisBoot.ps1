param(
    [string]$OutputDir = '05_Output/fpga/vitis/boot'
)

$ErrorActionPreference = 'Stop'
$projectRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$workspaceRoot = Resolve-Path (Join-Path $projectRoot '..\..')
$engineRoot = Join-Path $workspaceRoot 'engine'

Push-Location $engineRoot
try {
    & python -m hdlflow.cli generate-vitis-boot --project $projectRoot --output-dir $OutputDir
    if ($LASTEXITCODE -ne 0) { throw "generate-vitis-boot failed with code $LASTEXITCODE" }
}
finally {
    Pop-Location
}

Write-Host "VITIS_BOOT_TEMPLATE_GENERATE_PASS output_dir=$OutputDir"
