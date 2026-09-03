from Workflow.core.review import review_design


def gate_a(context):
    return review_design(context)

