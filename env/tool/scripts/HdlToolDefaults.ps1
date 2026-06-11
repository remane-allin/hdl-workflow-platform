$script:HdlToolDefaultPaths = @{
    "modelsim.vsim_exe"      = "D:/Modelsim/Modelsim/win64/vsim.exe"
    "modelsim.vlog_exe"      = "D:/Modelsim/Modelsim/win64/vlog.exe"
    "modelsim.vlib_exe"      = "D:/Modelsim/Modelsim/win64/vlib.exe"
    "modelsim.vdel_exe"      = "D:/Modelsim/Modelsim/win64/vdel.exe"
    "modelsim.uvm_src"       = "D:/Modelsim/Modelsim/verilog_src/uvm-1.1d/src"
    "vivado.vivado_bat"      = "E:/Vivado/Vivado/2024.2/bin/vivado.bat"
    "vivado.vivado_exe"      = "E:/Vivado/Vivado/2024.2/bin/vivado.exe"
    "vitis.xsct_bat"         = "E:/Vivado/Vitis/2024.2/bin/xsct.bat"
    "vitis.vitis_bat"        = "E:/Vivado/Vitis/2024.2/bin/vitis.bat"
    "vitis.vitis_exe"        = "E:/Vivado/Vitis/2024.2/bin/vitis.exe"
    "vitis.bootgen_bat"      = "E:/Vivado/Vitis/2024.2/bin/bootgen.bat"
    "iverilog.iverilog_exe"  = "D:/Iverilog/iverilog/bin/iverilog.exe"
    "iverilog.vvp_exe"       = "D:/Iverilog/iverilog/bin/vvp.exe"
}

$script:HdlToolEnvNames = @{
    "modelsim.vsim_exe"      = @("HDLFLOW_MODELSIM_VSIM_EXE", "HDL_MODELSIM_VSIM_EXE", "MODELSIM_VSIM_EXE")
    "modelsim.vlog_exe"      = @("HDLFLOW_MODELSIM_VLOG_EXE", "HDL_MODELSIM_VLOG_EXE", "MODELSIM_VLOG_EXE")
    "modelsim.vlib_exe"      = @("HDLFLOW_MODELSIM_VLIB_EXE", "HDL_MODELSIM_VLIB_EXE", "MODELSIM_VLIB_EXE")
    "modelsim.vdel_exe"      = @("HDLFLOW_MODELSIM_VDEL_EXE", "HDL_MODELSIM_VDEL_EXE", "MODELSIM_VDEL_EXE")
    "modelsim.uvm_src"       = @("HDLFLOW_MODELSIM_UVM_SRC", "HDL_MODELSIM_UVM_SRC", "MODELSIM_UVM_SRC")
    "vivado.vivado_bat"      = @("HDLFLOW_VIVADO_VIVADO_BAT", "HDL_VIVADO_VIVADO_BAT", "VIVADO_VIVADO_BAT")
    "vivado.vivado_exe"      = @("HDLFLOW_VIVADO_VIVADO_EXE", "HDL_VIVADO_VIVADO_EXE", "VIVADO_VIVADO_EXE")
    "vitis.xsct_bat"         = @("HDLFLOW_VITIS_XSCT_BAT", "HDL_VITIS_XSCT_BAT", "VITIS_XSCT_BAT")
    "vitis.vitis_bat"        = @("HDLFLOW_VITIS_VITIS_BAT", "HDL_VITIS_VITIS_BAT", "VITIS_VITIS_BAT")
    "vitis.vitis_exe"        = @("HDLFLOW_VITIS_VITIS_EXE", "HDL_VITIS_VITIS_EXE", "VITIS_VITIS_EXE")
    "vitis.bootgen_bat"      = @("HDLFLOW_VITIS_BOOTGEN_BAT", "HDL_VITIS_BOOTGEN_BAT", "VITIS_BOOTGEN_BAT")
    "iverilog.iverilog_exe"  = @("HDLFLOW_IVERILOG_IVERILOG_EXE", "HDL_IVERILOG_IVERILOG_EXE", "IVERILOG_IVERILOG_EXE")
    "iverilog.vvp_exe"       = @("HDLFLOW_IVERILOG_VVP_EXE", "HDL_IVERILOG_VVP_EXE", "IVERILOG_VVP_EXE")
}

function Resolve-HdlToolPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$WorkspacePath,
        [Parameter(Mandatory = $true)]
        [string]$Tool,
        [Parameter(Mandatory = $true)]
        [string]$Launcher
    )

    $key = "$Tool.$Launcher"
    foreach ($envName in ($script:HdlToolEnvNames[$key] + @())) {
        $value = [Environment]::GetEnvironmentVariable($envName)
        if ($value -and (Test-Path -LiteralPath $value)) {
            return $value
        }
    }

    $defaultPath = $script:HdlToolDefaultPaths[$key]
    if ($defaultPath -and (Test-Path -LiteralPath $defaultPath)) {
        return $defaultPath
    }

    $workspace = (Resolve-Path -LiteralPath $WorkspacePath).Path
    Push-Location -LiteralPath $workspace
    try {
        $env:PYTHONPATH = Join-Path $workspace "env\core"
        $resolved = (& python -m hdlflow.cli get-tool-launcher --workspace . --tool $Tool --launcher $Launcher).Trim()
    }
    finally {
        Pop-Location
    }
    return $resolved
}

function Resolve-HdlToolSetting {
    param(
        [Parameter(Mandatory = $true)]
        [string]$WorkspacePath,
        [Parameter(Mandatory = $true)]
        [string]$Tool,
        [Parameter(Mandatory = $true)]
        [string]$Key
    )

    $compound = "$Tool.$Key"
    foreach ($envName in ($script:HdlToolEnvNames[$compound] + @())) {
        $value = [Environment]::GetEnvironmentVariable($envName)
        if ($value) {
            return $value
        }
    }

    $defaultValue = $script:HdlToolDefaultPaths[$compound]
    if ($defaultValue) {
        return $defaultValue
    }

    $workspace = (Resolve-Path -LiteralPath $WorkspacePath).Path
    Push-Location -LiteralPath $workspace
    try {
        $env:PYTHONPATH = Join-Path $workspace "env\core"
        $resolved = (& python -m hdlflow.cli get-tool-setting --workspace . --tool $Tool --key $Key).Trim()
    }
    finally {
        Pop-Location
    }
    return $resolved
}
