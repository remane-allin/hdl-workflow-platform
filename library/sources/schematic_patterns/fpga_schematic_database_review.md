# FPGA Schematic Database Review

## Use When

Use this entry when Loop3 prototype work needs board net, connector, clock,
reset, power, or interface evidence from the already normalized schematic
database.

## Agent Procedure

1. Query `get-fpga-schematic-nets` for the target net, connector, interface, or
   category.
2. Cross-check returned rows against available IO-table and hardware-guide
   database rows.
3. Treat low-confidence or unmatched rows as review warnings.
4. Record unresolved ambiguity in project evidence before generating
   constraints or prototype scripts.
5. Link reusable connection patterns back into `connection_index.yaml` only
   after the structured row has been reviewed.

## Expected Database Artifacts

```text
metadata.yaml
sheets.yaml
nets.yaml
interfaces.yaml
power_tree.yaml
clock_reset.yaml
review_notes.md
```

## Notes

This repository consumes the parsed schematic database only. Raw schematic PDFs,
parser output, and intermediate parser workspaces are intentionally excluded.
