# FPGA IO Table Inbox

Place FPGA IO tables, pin lists, bank assignment spreadsheets, and board interface tables here.

Recommended naming:

```text
<board_or_project>_<device>_io_table_<version>.<ext>
```

Examples:

```text
devboard_xc7a200t_io_table_rev_a.xlsx
prototype_ku060_io_table_2026_05.csv
```

Supported source formats can include `.xlsx`, `.xls`, `.csv`, `.tsv`, `.pdf`, or Markdown tables.

Raw uploaded tables are local inputs. After review or parsing, put structured results under `library/parsed/fpga_io_tables/` and curated connection guidance under `library/sources/schematic_patterns/`.
