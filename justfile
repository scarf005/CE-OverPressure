export RIMWORLD_DIR := env("RIMWORLD_DIR", "/media/scarf/@steam/SteamLibrary/steamapps/common/RimWorld")
export RIMWORLD_MODS_CONFIG := env("RIMWORLD_MODS_CONFIG", "/home/scarf/.config/unity3d/Ludeon Studios/RimWorld by Ludeon Studios/Config/ModsConfig.xml")

mod_directory := "CE-Realistic-Autocannon-Explosions"

fmt:
    @:

build:
    deno run --allow-read ~/.config/pi/agent/skills/rimworld/scripts/validate-mod.ts

install: build
    #!/bin/sh
    set -eu
    mods_directory="${RIMWORLD_DIR}/Mods"
    if [ ! -d "$mods_directory" ]; then
        printf 'RimWorld Mods directory not found: %s\n' "$mods_directory" >&2
        exit 1
    fi
    destination="$mods_directory/{{mod_directory}}"
    staging="$(mktemp -d)"
    trap 'rm -rf "$staging"' EXIT
    rsync --archive About Patches "$staging/"
    mkdir -p "$destination"
    rsync --archive --delete "$staging/" "$destination/"
    printf 'Installed {{mod_directory}} to %s\n' "$destination"

enable: install
    #!/usr/bin/env python3
    import os
    import subprocess
    import xml.etree.ElementTree as ET
    from pathlib import Path

    if subprocess.run(
        ["pgrep", "-x", "RimWorldLinux"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0:
        raise SystemExit("Close RimWorld before enabling the mod.")

    package_id = (ET.parse("About/About.xml").getroot().findtext("packageId") or "").strip()
    config_path = Path(os.environ["RIMWORLD_MODS_CONFIG"])
    tree = ET.parse(config_path)
    active_mods = tree.getroot().find("activeMods")
    if active_mods is None:
        raise SystemExit(f"{config_path} has no activeMods element.")

    if package_id in ((node.text or "").strip() for node in active_mods.findall("li")):
        print(f"{package_id} is already enabled.")
        raise SystemExit(0)

    ET.SubElement(active_mods, "li").text = package_id
    ET.indent(tree, space="  ")
    temporary_path = config_path.with_name(f"{config_path.name}.tmp")
    tree.write(temporary_path, encoding="utf-8", xml_declaration=True)
    os.chmod(temporary_path, config_path.stat().st_mode)
    temporary_path.replace(config_path)
    print(f"Enabled {package_id} in {config_path}.")
