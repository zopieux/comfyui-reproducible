#!/usr/bin/env bash

set -Eeuo pipefail

DRY_RUN=""
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN="--dry-run"
    echo "--- DRY RUN MODE ---"
fi

# Check if CONTAINER_NAME is set
if [[ -z "${CONTAINER_NAME:-}" ]]; then
    echo "Error: CONTAINER_NAME environment variable is not set." >&2
    exit 1
fi

# Find the upperdir for the /ComfyUI/models mount
# We use a more robust way to extract the upperdir from the comma-separated Options string
UPPER_DIR=$(podman inspect "$CONTAINER_NAME" --format '{{range .Mounts}}{{if eq .Destination "/ComfyUI/models"}}{{range .Options}}{{if slice . 0 9 | eq "upperdir="}}{{slice . 9}}{{end}}{{end}}{{end}}{{end}}')

if [[ -z "$UPPER_DIR" ]]; then
    # Fallback for older podman or different formatting
    UPPER_DIR=$(podman inspect "$CONTAINER_NAME" --format '{{range .Mounts}}{{if eq .Destination "/ComfyUI/models"}}{{range .Options}}{{if (index (split . "=") 0 | eq "upperdir")}}{{index (split . "=") 1}}{{end}}{{end}}{{end}}{{end}}')
fi

if [[ -z "$UPPER_DIR" ]]; then
    echo "Error: Could not find upperdir for /ComfyUI/models in container $CONTAINER_NAME." >&2
    exit 1
fi

# Determine target directory
LOWER_DIR=$(podman inspect "$CONTAINER_NAME" --format '{{range .Mounts}}{{if eq .Destination "/ComfyUI/models"}}{{range .Options}}{{if slice . 0 9 | eq "lowerdir="}}{{slice . 9}}{{end}}{{end}}{{end}}{{end}}')
TARGET_DIR="${MODELS_HOST_DIR:-$LOWER_DIR}"

if [[ -z "$TARGET_DIR" ]]; then
    echo "Error: Could not determine target host directory." >&2
    exit 1
fi

echo
echo "Copying new files from container $CONTAINER_NAME..."
echo "Source (upperdir): $UPPER_DIR"
echo "Target:            $TARGET_DIR"
echo

# -r: recursive
# -l: copy symlinks as symlinks
# -t: preserve modification times
# --ignore-existing: skip files that already exist in the target
# --exclude='.wh.*': ignore whiteout files (deletions in overlay)
# --prune-empty-dirs: skip empty directories
# We omit -p (perms), -g (group), -o (owner) to inherit from the parent directory
rsync $DRY_RUN -rltv --ignore-existing --prune-empty-dirs --exclude='.wh.*' "$UPPER_DIR/" "$TARGET_DIR/"
