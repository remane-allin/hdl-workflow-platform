# UG Database Policy

This library is designed for many large FPGA user guides. Raw PDFs and parser output must not become the long-term lookup surface. The durable lookup surface is the structured database layer.

## Storage Zones

```text
library/
  files/fpga_ug_pdfs/        Source UG PDFs, local only and ignored by Git
  work/ug_ingest/            Temporary parse workspace, ignored and disposable
  parsed/fpga_ug_mineru/     Structured normalized artifacts only
  indexes/document_index.yaml
  sources/hardware_guides/   Concise human-readable detail pages
  .local/library.sqlite      Generated query database, local only
```

## UG Identity

Every guide must use a stable identity:

```text
<vendor>_<doc_id>/<version>/
```

Examples:

```text
xilinx_ug835/2024_1/
xilinx_ug903/2024_1/
alientek_navigator_zynq_fpga_dev_guide/v3_3/
```

The SQLite `guide_id` should be stable and explicit:

```text
<vendor>.<doc_id>.<version>[.<chapter_or_topic>]
```

## Ingest Lifecycle

1. Put the raw PDF under `library/files/fpga_ug_pdfs/`.
2. Parse into `library/work/ug_ingest/<doc_id>/<version>/<run_id>/`.
3. Normalize only useful content into `library/parsed/fpga_ug_mineru/<doc_id>/<version>/`.
4. Add or update `library/indexes/document_index.yaml`.
5. Add concise detail pages under `library/sources/hardware_guides/` when a topic needs narrative guidance.
6. Run:

```powershell
$env:PYTHONPATH='engine'; python -m hdlflow.cli library-finalize --workspace .
```

`library-finalize` rebuilds `library/.local/library.sqlite` and removes parser temporary outputs.

## Final Artifacts

Keep only normalized, queryable artifacts in `parsed/`:

- `metadata.json` / `metadata.yaml`
- `resources.json` / `resources.yaml`
- `sections.json` / `sections.yaml`
- `notes.json` / `notes.yaml`
- optional topic-specific structured files, for example `commands.json`, `constraints.json`, `interfaces.yaml`

Do not retain raw MinerU output, raw OCR text, extracted images, or temporary chunks after the database is built.

## Cleanup Contract

The following paths are temporary and can be deleted after successful database build:

- `library/work/`
- `library/parsed/**/mineru_raw/`
- `library/parsed/**/mineru_extract/`
- `library/parsed/**/text_raw/`
- `library/parsed/**/images/`
- `library/parsed/**/chunks/`
- `library/parsed/**/extracted_tables/`

The original PDF remains under `library/files/fpga_ug_pdfs/` as a local source-of-truth file, but normal AI lookup should use SQLite and structured artifacts first.
