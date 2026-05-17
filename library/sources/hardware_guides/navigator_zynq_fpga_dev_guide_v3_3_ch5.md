# Navigator ZYNQ FPGA Development Guide V3.3 Chapter 5

## Purpose

AI-facing retrieval entry for Chapter 5 hardware resources. This entry links
board-guide signal descriptions with the normalized IO table and schematic
database so Loop3 work can answer pin, connector, interface, and board-resource
questions from one place.

## Source

- Parsed data: `library/parsed/fpga_guides/navigator_zynq_fpga_dev_guide/v3_3/`
- Guide ID: `navigator_zynq_fpga_dev_guide.v3_3.chapter5`
- Retention: structured database artifacts only
- Related IO table: `zynq_core_board_pin_map.v1_0`
- Related schematic: `navigator_zynq_baseboard_schematic.v3_8`

## Query Pattern

```powershell
$env:PYTHONPATH=".\engine"
python -m hdlflow.cli library-build --workspace .
python -m hdlflow.cli get-fpga-hardware-resource --workspace . --guide-id navigator_zynq_fpga_dev_guide.v3_3.chapter5 --signal PL_LED0
python -m hdlflow.cli get-fpga-hardware-resource --workspace . --guide-id navigator_zynq_fpga_dev_guide.v3_3.chapter5 --package-pin H15
python -m hdlflow.cli get-fpga-hardware-resource --workspace . --guide-id navigator_zynq_fpga_dev_guide.v3_3.chapter5 --interface hdmi
```

## Indexed Content

- PL IO resource table from Chapter 5.1.1.
- PS MIO resource table from Chapter 5.1.2.
- Chapter section list for hardware resource navigation.
- Key notes for part numbers, BANK13 availability, and PUDC_B caution.

## Retrieval Notes

- PL rows include package pin, direction, board resource description, IO-table
  link, and schematic link when matched.
- PS rows include normalized MIO pin and IO-table link when matched.
- The local repository consumes normalized rows only; raw documents and parser
  workspaces are intentionally excluded.
