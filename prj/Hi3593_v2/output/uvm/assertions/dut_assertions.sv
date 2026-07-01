module dut_top_sva (
  input wire ACLK,
  input wire MR,
  input wire CS,
  input wire SCK,
  input wire SI,
  input wire SO,
  input wire TX1IN,
  input wire TX0IN,
  input wire SLP,
  input wire TEMPTY,
  input wire TFULL,
  input wire R1FLAG,
  input wire R2FLAG,
  input wire MB1_1,
  input wire MB1_2,
  input wire MB1_3,
  input wire MB2_1,
  input wire MB2_2,
  input wire MB2_3
);
  property no_unknown_after_reset;
    @(posedge ACLK) (!MR) |-> (!$isunknown({CS, SCK, SI, SO, TX1IN, TX0IN, SLP, TEMPTY, TFULL, R1FLAG, R2FLAG, MB1_1, MB1_2, MB1_3, MB2_1, MB2_2, MB2_3}));
  endproperty

  assert property (no_unknown_after_reset);
endmodule

bind hi3593_v2_top dut_top_sva u_dut_top_sva (
  .ACLK(ACLK),
  .MR(MR),
  .CS(CS),
  .SCK(SCK),
  .SI(SI),
  .SO(SO),
  .TX1IN(TX1IN),
  .TX0IN(TX0IN),
  .SLP(SLP),
  .TEMPTY(TEMPTY),
  .TFULL(TFULL),
  .R1FLAG(R1FLAG),
  .R2FLAG(R2FLAG),
  .MB1_1(MB1_1),
  .MB1_2(MB1_2),
  .MB1_3(MB1_3),
  .MB2_1(MB2_1),
  .MB2_2(MB2_2),
  .MB2_3(MB2_3)
);
