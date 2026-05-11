# Navigator ZYNQ Baseboard Schematic V3.8

## Purpose

AI-facing retrieval entry for the Navigator ZYNQ baseboard schematic. Use it during Loop3 FPGA prototype work to locate board nets, connector pins, core-board IO pins, and likely interface ownership without opening the full PDF first.

## Source

- Source PDF: `library/files/fpga_schematics/领航者ZYNQ底板原理图_V3.8.pdf`
- Parsed data: `library/parsed/fpga_schematics/navigator_zynq_baseboard_schematic/v3_8/`
- Schematic ID: `navigator_zynq_baseboard_schematic.v3_8`
- Parser flow: MinerU flash extraction plus `pdftotext` layout text plus cross-indexing against `zynq_core_board_pin_map.v1_0`

## Query Pattern

Use the SQLite index for lookup:

```powershell
$env:PYTHONPATH=".\engine"
python -m hdlflow.cli library-build --workspace .
python -m hdlflow.cli get-fpga-schematic-nets --workspace . --schematic-id navigator_zynq_baseboard_schematic.v3_8 --net SD_D2
python -m hdlflow.cli get-fpga-schematic-nets --workspace . --schematic-id navigator_zynq_baseboard_schematic.v3_8 --interface hdmi
python -m hdlflow.cli get-fpga-schematic-nets --workspace . --schematic-id navigator_zynq_baseboard_schematic.v3_8 --connector J2
```

## Retrieval Notes

- High-confidence rows are matched to the core-board IO table and include core connector, connector pin, ZYNQ package pin, bank, and voltage when available.
- Medium-confidence rows are extracted from schematic text/OCR tokens and are useful for discovery, but the original PDF remains the hardware signoff source.
- Schematic connector mapping follows the parsed baseboard/core-board relationship: `J2` corresponds to core connector `X3`, and `J1` corresponds to core connector `X4`.
- For names with spaces in the PDF, query either form. For example, `SD D2` and `SD_D2` resolve through normalized signal matching.

## Main Interfaces

- `hdmi`: HDMI data/clock/DDC/HPD nets.
- `rgb_lcd`: LCD RGB, sync, clock, backlight, reset, and touch-related nets.
- `camera`: CMOS camera data, clock, sync, reset, power-down, and I2C nets.
- `ethernet_rgmii` and `ethernet_phy`: RGMII and PHY-side MDI/control nets.
- `usb_otg`: OTG ULPI/data/control nets.
- `sd_card`, `qspi`, `ps_mio`, `jtag`: PS-side and debug nets.
- `uart`, `rs485`, `can`, `i2c`: low-speed board interfaces.

## Signoff Boundary

This entry is a local retrieval database for AI/debug assistance. Before changing constraints, board wiring, or FPGA pin assignments, verify the result against the original schematic PDF and the core-board IO table.
