# Loop1 ModelSim Scripts

Use these project-local entries for directed RTL/TB verification:

```tcl
do compile.do
do rtl_functional.do
```

`rtl_functional.do` defaults to a TB top named `loop1_tb`. Project scripts may
override before running:

```tcl
set loop1_tb_tops [list my_unit_tb my_top_tb]
do rtl_functional.do
```

The template fails when RTL or TB sources are missing, so Loop1 cannot report a
false pass.
