#!/bin/bash

set -Exeuo pipefail

# Meant to run in the container.
[[ -e /ComfyUI ]] || exit 1

# The sad state of security in ML supply chains.
sed -i '/security_check/d' /ComfyUI/custom_nodes/ComfyUI-Manager/prestartup_script.py

# Shut up.
sed -i 's/warning("No target revision/debug("No target revision/' /ComfyUI/app/database/db.py
# Remove when nvidia ubuntu image contains ImageMagick ≥.0
sed -i '/DESCRIPTION = Image./d' /ComfyUI/custom_nodes/ComfyUI-MagickWand/nodes.py
sed -i '/www.instagram.com/d' /ComfyUI/custom_nodes/ComfyUI-Crystools/nodes/image.py
