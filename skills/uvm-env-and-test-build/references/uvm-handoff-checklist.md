# UVM Handoff Checklist

Before simulation, confirm:

- interface names match the DUT contract
- transaction fields cover the meaningful protocol payload
- monitors sample the right side of each interface
- scoreboard expectation comes from spec rules
- base test and vseq base exist
- baseline tests exist
- package include order is coherent
- any dynamic register-driven behavior is documented
