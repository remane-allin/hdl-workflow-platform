# FPGA UG MinerU Output

MinerU output for FPGA user guides belongs here.

Suggested layout:

```text
fpga_ug_mineru/
└─ <vendor>_<doc_id>/
   └─ <version>/
      ├─ metadata.json
      ├─ chunks/
      ├─ images/
      └─ extracted_tables/
```

For long guides, split output into topic chunks before indexing. The SQLite library should point to concise Markdown details, not to raw 600-page extracted text.
