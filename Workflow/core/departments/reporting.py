from Workflow.reports.tools.extract import merge_stage_report


def record(context, design, stage, result):
    return merge_stage_report(context, design, stage, result)

