# FPGA UG Database Artifacts

Normalized FPGA user guide database artifacts belong here. This directory is a
database input area, not a PDF parsing workspace.

Suggested layout:

```text
fpga_guides/
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

Only curated structured rows and Markdown details should be retained here. The
SQLite library is built from these artifacts; raw PDFs, parser logs, and parser
work directories are intentionally excluded.
