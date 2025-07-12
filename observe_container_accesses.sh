#!/usr/bin/env nix-shell
#!nix-shell -i bash -p bash -p inotify-tools -p pv -p ripgrep

set -Eeuo pipefail

directories=$(podman run -ti --rm --device nvidia.com/gpu=all "$IMAGE_NAME" /bin/mount | rg 'lowerdir=(.+?),' -or '$1' | tr ':' ' ')
echo >&2 Watching:
echo >&2 "$directories" | tr ' ' '\n'

inotifywait -m -r -e access --no-dereference --csv $directories | pv --line-mode >> /tmp/used_files
