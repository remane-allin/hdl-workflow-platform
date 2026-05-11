# FPGA UG Database Artifacts

Normalized FPGA user guide database artifacts belong here. Raw MinerU output does not stay here after finalization.

Suggested layout:

```text
fpga_ug_mineru/
  <vendor>_<doc_id>/
    <version>/
      metadata.json
      metadata.yaml
      resources.json
      resources.yaml
      sections.json
      sections.yaml
      notes.json
      notes.yaml
```

For long guides, parse in `library/work/ug_ingest/`, extract only useful topic facts into structured files here, then run `library-finalize`. The SQLite library should point to concise structured rows and Markdown details, not to raw 600-page extracted text.
