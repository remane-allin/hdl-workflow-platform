from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

WORKFLOW_ROOT = Path(__file__).resolve().parent
WORKSPACE_ROOT = WORKFLOW_ROOT.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from Workflow.core.access import discover_project, require_workspace_write
from Workflow.core.contracts import STAGES, WorkflowError
from Workflow.core.execution import clean_project, clean_workflow, recover_project, run_to
from Workflow.core.state import load_state, status_view
from Workflow.tools.assets import publish_release_assets
from Workflow.tools.delivery import create_archive, deliver_git, restore_archive
from Workflow.tools.design import load_design
from Workflow.tools.platform import load_platform, restore_platform, upgrade_platform
from Workflow.tools.profile import environment_gate


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="workflow.py")
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("environment")
    run = commands.add_parser("run")
    run.add_argument("--project", required=True)
    run.add_argument("--to", required=True, choices=STAGES)
    for name in ("status", "recover"):
        command = commands.add_parser(name)
        command.add_argument("--project", required=True)
    clean = commands.add_parser("clean")
    clean.add_argument("--project")
    deliver = commands.add_parser("deliver")
    deliver.add_argument("--project", required=True)
    deliver.add_argument("--message", required=True)
    deliver.add_argument("--tag")
    deliver.add_argument("--init", action="store_true")
    deliver.add_argument("--remote")
    deliver.add_argument("--push", action="store_true")
    publish = commands.add_parser("publish-assets")
    publish.add_argument("--project", required=True)
    publish.add_argument("--result", required=True, action="append")
    archive = commands.add_parser("archive")
    archive.add_argument("--project", required=True)
    archive.add_argument("--output", required=True)
    restore = commands.add_parser("restore-archive")
    restore.add_argument("--archive", required=True)
    restore.add_argument("--target", required=True)
    commands.add_parser("platform-status")
    for name in ("platform-upgrade", "platform-restore"):
        command = commands.add_parser(name)
        command.add_argument("--project", required=True, action="append")
        if name == "platform-upgrade":
            command.add_argument("--candidate", required=True)
    return result


def _workspace_path(value: str) -> Path:
    path = Path(value)
    target = path if path.is_absolute() else WORKSPACE_ROOT / path
    return require_workspace_write(target, WORKSPACE_ROOT)


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        platform = load_platform(WORKFLOW_ROOT)
        if arguments.command == "environment":
            value = environment_gate(WORKFLOW_ROOT)
            value["workflow_platform_version"] = platform["platform_version"]
            print(json.dumps(value, ensure_ascii=False, indent=2))
            return 0
        if arguments.command == "platform-status":
            print(json.dumps(platform, ensure_ascii=False, indent=2))
            return 0
        if arguments.command == "platform-upgrade":
            value = upgrade_platform(
                WORKFLOW_ROOT, _workspace_path(arguments.candidate), arguments.project
            )
            print(json.dumps(value, ensure_ascii=False, indent=2))
            return 0
        if arguments.command == "platform-restore":
            value = restore_platform(WORKFLOW_ROOT, arguments.project)
            print(json.dumps(value, ensure_ascii=False, indent=2))
            return 0
        if arguments.command == "restore-archive":
            value = restore_archive(
                WORKFLOW_ROOT,
                _workspace_path(arguments.archive),
                _workspace_path(arguments.target),
            )
            print(json.dumps(value, ensure_ascii=False, indent=2))
            return 0
        if arguments.command == "clean" and not arguments.project:
            print(json.dumps({"removed": clean_workflow(WORKFLOW_ROOT)}, ensure_ascii=False, indent=2))
            return 0
        context = discover_project(WORKFLOW_ROOT, arguments.project)
        if arguments.command == "run":
            value = run_to(context, arguments.to)
        elif arguments.command == "status":
            design = load_design(context.design_path)
            state = load_state(context, create=False, design_version=design["design_version"])
            value = status_view(context, state)
        elif arguments.command == "recover":
            value = recover_project(context)
        elif arguments.command == "clean":
            value = {"removed": clean_project(context)}
        elif arguments.command == "deliver":
            value = deliver_git(
                context,
                arguments.message,
                initialize=arguments.init,
                tag=arguments.tag,
                remote=arguments.remote,
                push=arguments.push,
            )
        elif arguments.command == "publish-assets":
            value = publish_release_assets(context, arguments.result)
        else:
            value = create_archive(context, _workspace_path(arguments.output))
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return 0
    except (WorkflowError, OSError, ValueError) as error:
        print(
            json.dumps({"status": getattr(error, "kind", "BLOCKED"), "message": str(error)}, ensure_ascii=False),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
