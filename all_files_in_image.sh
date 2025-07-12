#!/usr/bin/env nix-shell
#!nix-shell -i bash -p bash

set -Eeuo pipefail

podman run -ti --rm --device nvidia.com/gpu=all "$IMAGE_NAME" /bin/bash -c \
  'find / \( -path /proc -o -path /sys -o -path /dev -o -path /run -o -path /mnt -o -path /tmp \) -prune -o -type d -print 2>/dev/null' \
  | sort > /tmp/existing_files
