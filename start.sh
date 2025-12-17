#!/usr/bin/env nix-shell
#!nix-shell -i bash -p bash

set -Eeuo pipefail

DEFAULT=(pyrun /ComfyUI/main.py --listen --port 7860 --preview-method auto --verbose INFO)

(( $# == 0 )) && set -- "${DEFAULT[@]}"

mkdir -p "$COMFY_OUTPUT_DIR"

podman run -ti --rm -p 7860:7860 --device nvidia.com/gpu=all \
  -v "$MODELS_HOST_DIR:/ComfyUI/models:O" \
  -v "$COMFY_OUTPUT_DIR:/ComfyUI/output:rw" \
  --mount type=volume,source=comfyui-user-storage,destination=/ComfyUI/user \
  --mount type=tmpfs,destination=/ComfyUI/output/temp \
  --name "$CONTAINER_NAME" \
  "$IMAGE_NAME" \
  "$@"

# -v "/home/alex/dev/ml/ComfyUI-zopi:/ComfyUI/custom_nodes/comfyui-zopi:ro" \
# -v /tmp/touched:/tmp/touched:rw \
# strace -f -e file -o /tmp/touched uv run --python /venv \
