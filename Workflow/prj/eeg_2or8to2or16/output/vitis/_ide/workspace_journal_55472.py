# 2026-09-03T11:47:08.942890100
import vitis

client = vitis.create_client()
client.set_workspace(path="vitis")

platform = client.get_component(name="p1_eeg_platform")
status = platform.update_hw(hw_design = "$COMPONENT_LOCATION/../../vivado/hw/eeg_bci_ps_pl_system_wrapper.xsa")

status = platform.build()

comp = client.create_app_component(name="p1_eeg_diag",platform = "$COMPONENT_LOCATION/../p1_eeg_platform/export/p1_eeg_platform/p1_eeg_platform.xpfm",domain = "p1_eeg_standalone",template = "hello_world")

comp = client.get_component(name="p1_eeg_diag")
status = comp.remove_files(files=["/src/helloworld.c"])

vitis.dispose()

