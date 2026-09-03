# 2026-09-03T11:51:55.801035700
import vitis

client = vitis.create_client()
client.set_workspace(path="vitis")

platform = client.get_component(name="p1_eeg_platform")
status = platform.update_hw(hw_design = "$COMPONENT_LOCATION/../../vivado/hw/eeg_bci_ps_pl_system_wrapper.xsa")

status = platform.build()

comp = client.get_component(name="p1_eeg_diag")
status = comp.remove_files(files=["G:\EEG\Workflow\prj\eeg_2or8to2or16\output\vitis\p1_eeg_diag\src\helloworld.c"])

status = comp.import_files(from_loc="$COMPONENT_LOCATION/../app-src", files=["eeg_bci_diag.c"], dest_dir_in_cmp = "src")

comp.build()

vitis.dispose()

