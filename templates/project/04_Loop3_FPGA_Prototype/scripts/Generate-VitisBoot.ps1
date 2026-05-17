param(
    [string]$OutputDir = ''
)

$ErrorActionPreference = 'Stop'
$projectRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$workspaceRoot = Resolve-Path (Join-Path $projectRoot '..\..')
$engineRoot = Join-Path $workspaceRoot 'engine'

Push-Location $engineRoot
try {
    $bootArgs = @('-m', 'hdlflow.cli', 'generate-vitis-boot', '--project', $projectRoot)
    if ($OutputDir) {
        $bootArgs += @('--output-dir', $OutputDir)
    }
    & python @bootArgs
    if ($LASTEXITCODE -ne 0) { throw "generate-vitis-boot failed with code $LASTEXITCODE" }
}
finally {
    Pop-Location
}

$outputSource = if ($OutputDir) { $OutputDir } else { 'project_config' }
Write-Host "VITIS_BOOT_TEMPLATE_GENERATE_PASS output_dir=$outputSource"
