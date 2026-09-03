# 2026-09-03T11:23:41.679952600
import vitis

client = vitis.create_client()
client.set_workspace(path="vitis")

platform = client.create_platform_component(name = "p1_eeg_platform",hw_design = "$COMPONENT_LOCATION/../../vivado/hw/eeg_bci_ps_pl_system_wrapper.xsa",os = "standalone",cpu = "ps7_cortexa9_0",domain_name = "p1_eeg_standalone",generate_dtb = True)

platform = client.get_component(name="p1_eeg_platform")
status = platform.build()

comp = client.create_app_component(name="p1_eeg_diag",platform = "$COMPONENT_LOCATION/../p1_eeg_platform/export/p1_eeg_platform/p1_eeg_platform.xpfm",domain = "p1_eeg_standalone",template = "empty")

vitis.dispose()

