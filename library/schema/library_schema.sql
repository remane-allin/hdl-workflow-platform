CREATE TABLE IF NOT EXISTS library_entries (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    domain TEXT,
    title TEXT,
    workflow_id TEXT,
    workflow_node TEXT,
    tool TEXT,
    vendor TEXT,
    stage TEXT,
    short_description TEXT,
    detail_path TEXT,
    tags TEXT,
    source_index TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_library_kind ON library_entries(kind);
CREATE INDEX IF NOT EXISTS idx_library_domain ON library_entries(domain);
CREATE INDEX IF NOT EXISTS idx_library_tool ON library_entries(tool);
CREATE INDEX IF NOT EXISTS idx_library_workflow ON library_entries(workflow_id);
CREATE INDEX IF NOT EXISTS idx_library_node ON library_entries(workflow_node);
CREATE INDEX IF NOT EXISTS idx_library_stage ON library_entries(stage);

CREATE TABLE IF NOT EXISTS fpga_io_tables (
    table_id TEXT PRIMARY KEY,
    title TEXT,
    source_file TEXT,
    source_type TEXT,
    parser TEXT,
    page_count INTEGER,
    pin_count INTEGER,
    parsed_dir TEXT
);

CREATE TABLE IF NOT EXISTS fpga_io_pins (
    table_id TEXT NOT NULL,
    connector TEXT NOT NULL,
    connector_pin INTEGER NOT NULL,
    signal_name TEXT,
    zynq_pin TEXT,
    raw_zynq_pin TEXT,
    bank TEXT,
    voltage TEXT,
    category TEXT,
    source_file TEXT,
    PRIMARY KEY (table_id, connector, connector_pin)
);

CREATE INDEX IF NOT EXISTS idx_fpga_io_pins_signal ON fpga_io_pins(signal_name);
CREATE INDEX IF NOT EXISTS idx_fpga_io_pins_bank ON fpga_io_pins(bank);
CREATE INDEX IF NOT EXISTS idx_fpga_io_pins_category ON fpga_io_pins(category);
CREATE INDEX IF NOT EXISTS idx_fpga_io_pins_connector ON fpga_io_pins(connector);

CREATE TABLE IF NOT EXISTS fpga_schematics (
    schematic_id TEXT PRIMARY KEY,
    title TEXT,
    source_file TEXT,
    source_type TEXT,
    parser TEXT,
    page_count INTEGER,
    net_count INTEGER,
    parsed_dir TEXT
);

CREATE TABLE IF NOT EXISTS fpga_schematic_sheets (
    schematic_id TEXT NOT NULL,
    page INTEGER NOT NULL,
    title TEXT,
    interfaces TEXT,
    net_count INTEGER,
    summary TEXT,
    PRIMARY KEY (schematic_id, page)
);

CREATE TABLE IF NOT EXISTS fpga_schematic_nets (
    schematic_id TEXT NOT NULL,
    net_name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    interface TEXT,
    category TEXT,
    schematic_connector TEXT,
    schematic_connector_pin INTEGER,
    core_connector TEXT,
    core_connector_pin INTEGER,
    zynq_pin TEXT,
    bank TEXT,
    voltage TEXT,
    linked_io_signal TEXT,
    source_sheet TEXT,
    confidence TEXT,
    source_file TEXT,
    notes TEXT,
    PRIMARY KEY (
        schematic_id,
        net_name,
        schematic_connector,
        schematic_connector_pin,
        core_connector,
        core_connector_pin
    )
);

CREATE INDEX IF NOT EXISTS idx_fpga_schematic_nets_name ON fpga_schematic_nets(net_name);
CREATE INDEX IF NOT EXISTS idx_fpga_schematic_nets_normalized ON fpga_schematic_nets(normalized_name);
CREATE INDEX IF NOT EXISTS idx_fpga_schematic_nets_interface ON fpga_schematic_nets(interface);
CREATE INDEX IF NOT EXISTS idx_fpga_schematic_nets_category ON fpga_schematic_nets(category);
CREATE INDEX IF NOT EXISTS idx_fpga_schematic_nets_connector ON fpga_schematic_nets(schematic_connector);
