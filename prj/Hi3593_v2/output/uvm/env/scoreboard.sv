`ifndef SCOREBOARD_SV
`define SCOREBOARD_SV

class dut_scoreboard extends uvm_component;
  `uvm_component_utils(dut_scoreboard)

  uvm_analysis_imp #(spi_item, dut_scoreboard) analysis_export;
  int total_checks;
  int failed_checks;

  function new(string name, uvm_component parent);
    super.new(name, parent);
    analysis_export = new("analysis_export", this);
    total_checks = 0;
    failed_checks = 0;
  endfunction

  virtual function void write(spi_item observed);
    int expected_code;
    string result_text;
    expected_code = predict_expected(observed);
    total_checks++;
    if (observed.actual_code != expected_code) begin
      failed_checks++;
      result_text = "FAIL";
      `uvm_error("MISMATCH", $sformatf("observed=%0d expected=%0d scenario=%0s opcode=%02h", observed.actual_code, expected_code, observed.scenario_name, observed.opcode))
    end
    else begin
      result_text = "PASS";
    end
    $display("HDLFLOW|UVM_CHECK|schema=hdlflow_event_v1|version=1|stage=loop2|test_id=%0s|txn_id=txn_%0d|sent=opcode_%02h|expected=code_%0d|actual=code_%0d|latency_cycles=%0d|result=%0s",
      observed.scenario_name, total_checks, observed.opcode, expected_code, observed.actual_code, observed.latency_cycles, result_text);
  endfunction

  function int predict_expected(spi_item observed);
    case (observed.scenario_code)
      1: return 100;
      2: return 101;
      3: return 102;
      4: return 103;
      5: return 104;
      default: return 200 + int'(observed.opcode);
    endcase
  endfunction
endclass

`endif
