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

CREATE TABLE IF NOT EXISTS fpga_hardware_guides (
    guide_id TEXT PRIMARY KEY,
    title TEXT,
    source_file TEXT,
    source_type TEXT,
    parser TEXT,
    page_count INTEGER,
    chapter TEXT,
    chapter_title TEXT,
    resource_count INTEGER,
    section_count INTEGER,
    linked_io_count INTEGER,
    linked_schematic_count INTEGER,
    parsed_dir TEXT
);

CREATE TABLE IF NOT EXISTS fpga_hardware_resources (
    guide_id TEXT NOT NULL,
    domain TEXT,
    source_table TEXT,
    resource_group TEXT,
    signal_name TEXT NOT NULL,
    aliases TEXT,
    direction TEXT,
    package_pin TEXT,
    mio_pin TEXT,
    interface TEXT,
    description TEXT,
    io_table_links TEXT,
    schematic_links TEXT,
    source_section TEXT,
    source_file TEXT,
    PRIMARY KEY (guide_id, signal_name, package_pin, mio_pin, description)
);

CREATE INDEX IF NOT EXISTS idx_fpga_hardware_resources_signal ON fpga_hardware_resources(signal_name);
CREATE INDEX IF NOT EXISTS idx_fpga_hardware_resources_aliases ON fpga_hardware_resources(aliases);
CREATE INDEX IF NOT EXISTS idx_fpga_hardware_resources_interface ON fpga_hardware_resources(interface);
CREATE INDEX IF NOT EXISTS idx_fpga_hardware_resources_package_pin ON fpga_hardware_resources(package_pin);
CREATE INDEX IF NOT EXISTS idx_fpga_hardware_resources_mio_pin ON fpga_hardware_resources(mio_pin);

CREATE TABLE IF NOT EXISTS software_tool_documents (
    doc_id TEXT PRIMARY KEY,
    title TEXT,
    vendor TEXT,
    tool TEXT,
    tool_version TEXT,
    source_file TEXT,
    source_type TEXT,
    parser TEXT,
    page_count INTEGER,
    command_count INTEGER,
    parsed_dir TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS software_tcl_commands (
    command_id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL,
    tool TEXT,
    tool_version TEXT,
    command TEXT NOT NULL,
    summary TEXT,
    syntax TEXT,
    returns_text TEXT,
    categories TEXT,
    description TEXT,
    arguments_text TEXT,
    examples_text TEXT,
    see_also TEXT,
    source_pages TEXT,
    source_file TEXT,
    full_text TEXT
);

CREATE INDEX IF NOT EXISTS idx_software_tcl_commands_command ON software_tcl_commands(command);
CREATE INDEX IF NOT EXISTS idx_software_tcl_commands_tool ON software_tcl_commands(tool);
CREATE INDEX IF NOT EXISTS idx_software_tcl_commands_version ON software_tcl_commands(tool_version);
CREATE INDEX IF NOT EXISTS idx_software_tcl_commands_categories ON software_tcl_commands(categories);

CREATE TABLE IF NOT EXISTS software_tcl_command_options (
    command_id TEXT NOT NULL,
    option_name TEXT NOT NULL,
    description TEXT,
    source TEXT,
    PRIMARY KEY (command_id, option_name)
);

CREATE INDEX IF NOT EXISTS idx_software_tcl_options_name ON software_tcl_command_options(option_name);

CREATE TABLE IF NOT EXISTS software_doc_chunks (
    chunk_id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL,
    tool TEXT,
    tool_version TEXT,
    section_type TEXT,
    anchor TEXT,
    page_start INTEGER,
    page_end INTEGER,
    text TEXT
);

CREATE VIRTUAL TABLE IF NOT EXISTS software_doc_chunks_fts USING fts5(
    chunk_id UNINDEXED,
    doc_id UNINDEXED,
    tool UNINDEXED,
    tool_version UNINDEXED,
    anchor UNINDEXED,
    text
);

CREATE TABLE IF NOT EXISTS software_tcl_topics (
    topic_id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL,
    tool TEXT,
    tool_version TEXT,
    title TEXT,
    section_type TEXT,
    summary TEXT,
    page_start INTEGER,
    page_end INTEGER,
    tags TEXT,
    text TEXT
);

CREATE INDEX IF NOT EXISTS idx_software_tcl_topics_doc ON software_tcl_topics(doc_id);
CREATE INDEX IF NOT EXISTS idx_software_tcl_topics_title ON software_tcl_topics(title);
CREATE INDEX IF NOT EXISTS idx_software_tcl_topics_type ON software_tcl_topics(section_type);

CREATE TABLE IF NOT EXISTS software_tcl_examples (
    example_id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL,
    topic_id TEXT,
    tool TEXT,
    tool_version TEXT,
    title TEXT,
    page_start INTEGER,
    page_end INTEGER,
    code TEXT,
    description TEXT,
    commands TEXT,
    tags TEXT
);

CREATE INDEX IF NOT EXISTS idx_software_tcl_examples_doc ON software_tcl_examples(doc_id);
CREATE INDEX IF NOT EXISTS idx_software_tcl_examples_topic ON software_tcl_examples(topic_id);
