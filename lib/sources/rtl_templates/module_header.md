# RTL Module Header Template

## Use When

Use this entry when creating a new SystemVerilog RTL module and a consistent file header, parameter block, and port grouping are needed.

## Template Notes

- Keep clock and reset ports first.
- Group control, data, and status ports separately.
- Declare parameters before ports when they affect port widths.
- Keep implementation-specific comments in the module body, not in the header banner.

## Skeleton

```systemverilog
module module_name #(
    parameter int DATA_WIDTH = 32
) (
    input  logic                  clk,
    input  logic                  rst_n,
    input  logic                  enable,
    input  logic [DATA_WIDTH-1:0] data_i,
    output logic [DATA_WIDTH-1:0] data_o
);

endmodule
```
