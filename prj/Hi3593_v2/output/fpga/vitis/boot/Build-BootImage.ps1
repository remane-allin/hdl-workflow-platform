param(
    [string]$Bif = (Join-Path $PSScriptRoot 'boot_image.bif'),
    [string]$Output = (Join-Path $PSScriptRoot 'BOOT.bin')
)
$ErrorActionPreference = 'Stop'
$projectRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..\..\..')
$workspaceRoot = Resolve-Path (Join-Path $projectRoot '..\..')
$vitisWrapper = Join-Path $workspaceRoot 'env\tool\scripts\Invoke-HdlVitis.ps1'
if (-not (Test-Path -LiteralPath $vitisWrapper)) { throw "Invoke-HdlVitis wrapper not found: $vitisWrapper" }
$bootgenArgs = @('-image', $Bif, '-arch', 'zynq', '-o', $Output, '-w')
& $vitisWrapper -Tool bootgen -Project $projectRoot.Path -WorkspacePath $workspaceRoot.Path -RunDir $PSScriptRoot -ToolArgs $bootgenArgs
if ($LASTEXITCODE -ne 0) { throw "Invoke-HdlVitis bootgen failed with code $LASTEXITCODE" }
Write-Host "VITIS_BOOT_IMAGE_PASS output=$Output"
