"""Pipeline discovery and reporting."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PipelineNode:
    name: str
    index: int
    config: dict[str, Any]


def build_pipeline(project_data: dict[str, Any]) -> list[PipelineNode]:
    nodes = project_data.get("nodes", {})
    if not isinstance(nodes, dict):
        return []

    pipeline: list[PipelineNode] = []
    for name, cfg in nodes.items():
        try:
            index = int(name.split("_", 1)[0])
        except ValueError:
            index = 999
        pipeline.append(PipelineNode(name=name, index=index, config=cfg if isinstance(cfg, dict) else {}))
    return sorted(pipeline, key=lambda item: (item.index, item.name))


def format_pipeline(nodes: list[PipelineNode]) -> list[str]:
    lines = ["pipeline:"]
    for node in nodes:
        gates = node.config.get("gates", {})
        gate_names = ", ".join(gates.keys()) if isinstance(gates, dict) and gates else "none"
        lines.append(f"- {node.name} gates=[{gate_names}]")
    return lines

