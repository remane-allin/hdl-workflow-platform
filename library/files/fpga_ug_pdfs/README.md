# FPGA UG PDF Inbox

Place official FPGA UG PDFs here for local parsing.

Recommended naming:

```text
<vendor>_<doc_id>_<version>.pdf
```

Examples:

```text
xilinx_ug835_2024_1.pdf
xilinx_ug903_2024_1.pdf
intel_quartus_pro_user_guide_timing_analyzer_24_1.pdf
```

PDF files in this directory are ignored by Git. For 600-page guides, parse them into a temporary workspace under `library/work/ug_ingest/<doc_id>/<version>/<run_id>/`, then normalize only useful topics into `library/parsed/fpga_ug_mineru/<doc_id>/<version>/`.

Use MinerU `extract` for library PDFs so table/image/page metadata stay stable for cross-indexing.

After the structured database artifacts are written, run:

```powershell
$env:PYTHONPATH='engine'; python -m hdlflow.cli library-finalize --workspace .
```

This rebuilds `library/.local/library.sqlite` and removes parser temporary outputs.
