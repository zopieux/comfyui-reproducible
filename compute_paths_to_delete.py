#!/usr/bin/env nix-shell
#!nix-shell -i python -p python3

import csv
import sys
from pprint import pprint
from pathlib import Path
from typing import List, Set
from collections import defaultdict

PREFIX_LEN = len(Path('/home/u/.local/share/containers/storage/overlay/layer/*').parts)


def parse_inotify_csv():

  def kill_prefix(p: Path):
    return Path(*(('/',) + p.parts[PREFIX_LEN:]))

  with open('/tmp/used_files') as f:
    return {(kill_prefix(Path(d)) / f, 'ISDIR' in flags) for d, flags, f in csv.reader(f)}


def parse_strace():
  with open('/tmp/used_files_strace') as f:
    return {(Path(d), False) for d in f.read().splitlines()}


def explode_paths(files):
  for f, is_dir in files:
    if is_dir:
      yield f
    yield from f.parents


def only_leaves(paths: Set[Path]) -> Set[Path]:
  if not paths:
    return set()
  dirs = set(paths)
  sorted_dirs = sorted(dirs)
  summarized = []
  if sorted_dirs:
    last_kept = sorted_dirs[0]
    for i in range(1, len(sorted_dirs)):
      current = sorted_dirs[i]
      if current.is_relative_to(last_kept):
        last_kept = current
      else:
        summarized.append(last_kept)
        last_kept = current
    summarized.append(last_kept)
  return set(summarized)


def find_smallest_rm_set(candidates: Set[Path], interesting: Set[Path]) -> Set[Path]:
  """
  Computes the smallest set of folders to delete to remove all non-interesting folders.
  """
  non_deletable_paths = set()
  for path in interesting:
    non_deletable_paths.add(path)
    non_deletable_paths.update(path.parents)

  leaves_to_delete = candidates - interesting
  if not leaves_to_delete:
    return set()

  potentially_deletable_paths = set()
  for path in leaves_to_delete:
    potentially_deletable_paths.add(path)
    potentially_deletable_paths.update(path.parents)

  deletable_paths = potentially_deletable_paths - non_deletable_paths
  return {path for path in deletable_paths if path.parent not in deletable_paths}


def parse_find():
  with open('/tmp/existing_files') as f:
    for line in f.read().splitlines():
      if line:
        yield Path(line)


if __name__ == '__main__':
  used = list(parse_strace())
  # used = list(parse_inotify_csv())
  print(f"{len(used)=}", file=sys.stderr)
  used_exploded = set(explode_paths(used))
  print(f"{len(used_exploded)=}", file=sys.stderr)
  used_leaves = set(only_leaves(used_exploded))
  print(f"{len(used_leaves)=}", file=sys.stderr)

  exist = set(parse_find())
  print(f"{len(exist)=}", file=sys.stderr)

  to_rm = find_smallest_rm_set(exist, used_leaves)
  keep = {
      Path(_) for _ in [
          # "/ComfyUI",
          "/ComfyUI/alembic_db",
          "/ComfyUI/output",
          # "/ComfyUI/user",
          # "/ComfyUI/custom_nodes/comfyui-impact-pack/js",
          "/ComfyUI/custom_nodes",
          # "/ComfyUI/models",
          # "/usr/lib/python3.12/",
          "/usr/libexec",
          "/usr/lib/ssl",
          "/usr/local/bin",
          "/usr/sbin",
          "/usr/lib64",
          "/etc/ld.so.conf.d",
          "/etc/apt/apt.conf.d",
          "/etc/ssl/certs",
          "/venv/lib/python3.12/site-packages/",
          "/usr/share/terminfo",
          # "/usr",
          # "/venv/bin",
      ]
  }
  for target in list(to_rm):
    if any(target.is_relative_to(p) or target == p or str(p).startswith(str(target)) for p in keep):
      to_rm.discard(target)

  to_rm -= {Path(_) for _ in [
      Path("/var"),
  ]}

  print(f"{len(to_rm)=}", file=sys.stderr)

  for _ in sorted(to_rm):
    print(_)
