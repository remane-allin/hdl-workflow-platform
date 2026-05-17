# UG Database Policy

This repository now consumes only already-normalized library artifacts and the
SQLite database built from them. Raw PDF ingest is out of scope for this
workspace.

## Durable Inputs

Keep these as the source for library lookup:

- `library/parsed/`
- `library/indexes/`
- `library/sources/`
- `library/schema/library_schema.sql`

The generated database is local-only:

- `library/.local/library.sqlite`

Rebuild it from parsed artifacts with:

```powershell
python -m hdlflow.cli library-build --workspace .
```

## Retention Rules

- Do not keep raw UG PDFs, schematic PDFs, parser workspaces, parser raw output,
  OCR text dumps, extracted images, or temporary chunks in this workspace.
- Do not add new PDF ingest commands to `hdlflow.cli`.
- If new reference material is needed, add normalized artifacts directly under
  `library/parsed/` plus concise details under `library/sources/`, then update
  `library/indexes/` and rebuild the database.

