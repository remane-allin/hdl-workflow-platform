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

PDF files in this directory are ignored by Git. For 600-page guides, parse them into chunked MinerU output under `library/parsed/fpga_ug_mineru/<doc_id>/<version>/`, then index only the useful topics.
