#!/usr/bin/env nix-shell
#!nix-shell -i bash -p bash -p curl

set -Eeuo pipefail

test_dir=$(mktemp -d)

podman run -ti --rm -p 7860:7860 --device nvidia.com/gpu=all \
  -v "$MODELS_HOST_DIR:/ComfyUI/models:O" \
  -v "$test_dir:/ComfyUI/output:rw" \
  --name "$CONTAINER_NAME" \
  "$IMAGE_NAME" \
  pyrun /ComfyUI/main.py --listen --port 7860 --preview-method auto --verbose WARNING \
  >"$test_dir/logs" 2>&1 \
  &

echo "Logs: $test_dir/logs"

echo '{"prompt":' >"$test_dir/prompt.json"
cat test_workflow.json >>"$test_dir/prompt.json"
echo '}' >>"$test_dir/prompt.json"

while true; do
    curl --max-time 2 --fail http://127.0.0.1:7860/prompt -d @"$test_dir/prompt.json" && break || sleep 2
done

echo "prompt was queued, waiting for result"

while true; do
    ls -lh "$test_dir"/Comfy*.png && break || sleep 2
done

podman stop "$CONTAINER_NAME"
wait
rm -rf "$test_dir"
