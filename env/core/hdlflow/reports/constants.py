"""Constants for unified HDL workflow reports."""

from __future__ import annotations

from dataclasses import dataclass


REPORT_SCHEMA = "hdlflow_report_v1"
EVENT_SCHEMA = "hdlflow_event_v1"
EVENT_VERSION = "1"
COMMAND_SCHEMA = "hdlflow_command_v1"
RUN_MANIFEST_SCHEMA = "hdlflow_run_current_v1"
REPORT_MANIFEST_SCHEMA = "hdlflow_report_manifest_v1"

PASS_BANNER = (
    "******************************************************************************************"
    "^^^^**********^^^^^***********************^^^^**^^^***************************************"
    "*************************************************************"
)
FAIL_BANNER = "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! RTL TEST FAILED !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
BLOCKED_BANNER = "?????????????????????????????????????????????????????? REPORT BLOCKED ???????????????????????????????????????????????????????"


@dataclass(frozen=True)
class StageReportDefinition:
    report_type: str
    stage: str
    stage_dir: str
    output_dir: str
    title: str
    report_json_schema: str
    tool: str
    primary_log: str

    @property
    def current_dir(self) -> str:
        return f"{self.stage_dir}/current"

    @property
    def command_json(self) -> str:
        return f"{self.current_dir}/cmd/command.json"

    @property
    def command_md(self) -> str:
        return f"{self.current_dir}/cmd/command.md"

    @property
    def log_rel(self) -> str:
        return f"{self.current_dir}/log/{self.primary_log}"

    @property
    def stdout_log(self) -> str:
        return f"{self.current_dir}/log/stdout.log"

    @property
    def stderr_log(self) -> str:
        return f"{self.current_dir}/log/stderr.log"

    @property
    def current_manifest(self) -> str:
        return f"{self.current_dir}/manifest.json"

    @property
    def report_md(self) -> str:
        return f"{self.output_dir}/{self.report_type}_report.md"

    @property
    def report_json(self) -> str:
        return f"{self.output_dir}/{self.report_type}_report.json"

    @property
    def report_manifest(self) -> str:
        return f"{self.output_dir}/{self.report_type}_report_manifest.json"


LOOP1_REPORT = StageReportDefinition(
    report_type="loop1",
    stage="loop1_rtl_tb",
    stage_dir="work/loop1_rtl_tb",
    output_dir="output/reports/loop1",
    title="Loop1 RTL/TB Report",
    report_json_schema="hdlflow_loop1_report_v1",
    tool="modelsim",
    primary_log="modelsim.log",
)

LOOP2_REPORT = StageReportDefinition(
    report_type="loop2",
    stage="loop2_uvm",
    stage_dir="work/loop2_uvm",
    output_dir="output/reports/loop2",
    title="Loop2 UVM Report",
    report_json_schema="hdlflow_loop2_report_v1",
    tool="modelsim",
    primary_log="modelsim.log",
)
