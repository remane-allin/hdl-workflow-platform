# Loop2 Database Preflight

- project: Hi3593_v2
- library_db: `G:/Codex_Workflow/Test_new/lib/local/library.sqlite`

## Template Entries

- uvm.rkv_style_framework: PASS
  - title: RKV-style UVM framework template
  - detail_path: sources/uvm_templates/rkv_style_uvm_framework.md
  - detail_bytes: 4862
- uvm.rkv_i2c_reference_profile: PASS
  - title: RKV I2C reference profile
  - detail_path: sources/uvm_templates/rkv_i2c_reference_profile.md
  - detail_bytes: 2377

## UVM Guide Entries

- uvm.methodology_reference: PASS
  - title: UVM methodology reference
  - detail_path: 
- accellera.uvm_users_guide.1_1: PASS
  - title: Universal Verification Methodology (UVM) 1.1 User Guide
  - detail_path: sources/uvm_guides/accellera_uvm_users_guide_1_1.md
  - detail_status: DB entry only; UVM guide chunks/examples are checked below
- verification_academy.uvm_cookbook.complete: PASS
  - title: Verification Academy UVM Cookbook
  - detail_path: sources/uvm_guides/verification_academy_uvm_cookbook_complete.md
  - detail_status: DB entry only; UVM guide chunks/examples are checked below

## Project Layout

- output/uvm: PASS
- output/uvm/env: PASS
- output/uvm/agents: PASS
- output/uvm/cov: PASS
- output/uvm/seq_lib: PASS
- output/uvm/tests: PASS
- output/uvm/tb: PASS
- work/loop2_uvm/sim/regression.do: PASS
- instantiated_uvm_sources: PASS

## Required Use

- Run this preflight before building or closing Loop2 UVM.
- UVM framework selection must come from the local template database.
- After the template skeleton is created, use `G:/Codex_Workflow/Test_new/prj/Hi3593_v2/output/reports/loop2/preflight/uvm_flesh_plan.md` to flesh out cfg, agents, sequences, scoreboard, coverage, and RAL from the UVM database.
- Project-specific UVM files must still be completed from the normalized spec and checked against the database-backed flesh plan.

result: PASS