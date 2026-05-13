param(
    [string]$Output = '05_Output/fpga/vivado/constraints/generated_board.xdc'
)

$ErrorActionPreference = 'Stop'
$projectRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$workspaceRoot = Resolve-Path (Join-Path $projectRoot '..\..')
$engineRoot = Join-Path $workspaceRoot 'engine'

Push-Location $engineRoot
try {
    & python -m hdlflow.cli generate-xdc `
        --workspace .. `
        --project $projectRoot `
        --output $Output `
        --port sys_clk=PL_GCLK_50MHZ `
        --clock sys_clk=20.000 `
        --port pl_led0=PL_LED0 `
        --port uart_rx_i=UART3_RX `
        --port uart_tx_o=UART3_TX
    if ($LASTEXITCODE -ne 0) { throw "generate-xdc failed with code $LASTEXITCODE" }
}
finally {
    Pop-Location
}

Write-Host "BOARD_XDC_GENERATE_PASS output=$Output"
