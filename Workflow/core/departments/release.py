from Workflow.tools.vitis import build_vitis
from Workflow.tools.xilinx import run_vivado


def run(context, design):
    hardware = run_vivado(context, design, "release")
    software = build_vitis(context, design) if design["implementation"]["vitis"].get("enabled") else {"status": "NOT_APPLICABLE"}
    return {"status": "PASS", "hardware": hardware, "software": software}

