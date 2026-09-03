import json
import sys
from pathlib import Path

import vitis


design_path = Path(sys.argv[-1]).resolve()
with design_path.open("r", encoding="utf-8") as stream:
    design = json.load(stream)
project_root = design_path.parents[2]
configuration = design["implementation"]["vitis"]
workspace = (project_root / configuration["workspace"]).resolve()
xsa = (project_root / configuration["xsa"]).resolve()
source_dir = (project_root / configuration["source_dir"]).resolve()
if not xsa.is_file() or not source_dir.is_dir():
    raise RuntimeError("approved XSA or Vitis application source is missing")

client = vitis.create_client()
client.update_workspace(str(workspace))
components = {item["name"]: item["location"] for item in client.list_components()}
if configuration["platform"] not in components:
    platform = client.create_platform_component(
        name=configuration["platform"],
        hw_design=str(xsa),
        domain_name=configuration["domain"],
        cpu=configuration["processor"],
        os=configuration["os"],
    )
else:
    platform = client.get_component(configuration["platform"])
    platform.update_hw(hw_design=str(xsa))
platform.build()
platform_xpfm = client.find_platform_in_repos(configuration["platform"])
if configuration["application"] not in components:
    application = client.create_app_component(
        name=configuration["application"],
        platform=platform_xpfm,
        domain=configuration["domain"],
        template="hello_world",
    )
else:
    application = client.get_component(configuration["application"])
component_source = Path(application.component_location) / "src"
for managed_name in ("helloworld.c", "eeg_bci_diag.c"):
    managed_file = component_source / managed_name
    if managed_file.is_file():
        application.remove_files(files=[str(managed_file)])
application.import_files(from_loc=str(source_dir), files=["eeg_bci_diag.c"], dest_dir_in_cmp="src")
application.build()
elf = Path(application.component_location) / "build" / f"{configuration['application']}.elf"
if not elf.is_file():
    raise RuntimeError(f"application build did not create the native ELF: {elf}")
print(f"WF_VITIS|elf={elf}")
vitis.dispose()
