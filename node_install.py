from pathlib import Path
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pprint import pprint
from typing import List, Set, Optional
import json
import os
import random
import subprocess
import sys
import time
import functools

COMFY_DIR = Path(os.environ.get('COMFY_PATH', '/ComfyUI'))
CUSTOM_NODES_DIR = COMFY_DIR / 'custom_nodes'
MANAGER_DIR = CUSTOM_NODES_DIR / 'ComfyUI-Manager'
CUSTOM_NODE_DEFS = MANAGER_DIR / 'custom-node-list.json'
MAX_WORKERS = int(os.environ.get('MAX_WORKERS', '4'))


@dataclass
class DownloadedNode:
    directory: Path
    requirements: Optional[Path]
    install_py: Optional[Path]


def uv(args):
    return subprocess.run([Path(sys.executable).parent / 'uv'] + args, check=True)


def run_silently(args, *, raise_on_error=True, **kwargs):
    try:
        return subprocess.run(args, **kwargs, check=True, capture_output=True)
    except subprocess.CalledProcessError as err:
        tqdm.write(f"Process exited with {err.returncode} while running {args}:\n"
                   f"stdout:\n{err.stdout}\n\nstderr:\n{err.stderr}")
        if raise_on_error:
            raise


def download_node(node_registry, node) -> DownloadedNode:
    try:
        repository: str = node_registry[node]["files"][0]
    except KeyError:
        repository = node
    assert repository.startswith("https://"), f"{repository=}"

    dir_name = Path(repository).stem
    directory = CUSTOM_NODES_DIR / dir_name
    run_silently(['git', 'clone', '--quiet', '--depth=1', '--recursive', repository, str(directory)], text=True)

    requirements = directory / 'requirements.txt'
    if not requirements.is_file():
        requirements = None

    install_py = directory / 'install.py'
    if not install_py.is_file():
        install_py = None

    return DownloadedNode(directory, requirements, install_py)


def post_install(downloaded: DownloadedNode):
    tqdm.write(f"Installing: running {downloaded.install_py}")
    run_silently([sys.executable, downloaded.install_py], text=True)


def load_fucked_up_registry() -> dict:
    with CUSTOM_NODE_DEFS.open() as f:
        nodes = json.load(f)["custom_nodes"]

    def generate_ids(node: dict):
        for f in node["files"]:
            f: str
            if "github.com" in f and not f.endswith(".py") and not f.endswith(".js"):
                yield Path(f).stem
        try:
            yield node["id"]
        except KeyError:
            pass

    return {raw_id.strip().lower(): node for node in nodes for raw_id in generate_ids(node)}


if __name__ == '__main__':
    assert CUSTOM_NODES_DIR.is_dir()

    tqdm.write(f"Python: {sys.executable}")
    uv(["self", "version"])

    nodes = list(set(n.lower() for n in sys.argv[1:]))
    tqdm.write(f"Installing {len(nodes)} nodes")

    if False:
        # REMOVE ME after debug
        import shutil
        for n in CUSTOM_NODES_DIR.iterdir():
            if n != MANAGER_DIR and n.is_dir():
                shutil.rmtree(n)

    node_registry = load_fucked_up_registry()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        downloaded: List[DownloadedNode] = list(
            tqdm(executor.map(functools.partial(download_node, node_registry), nodes),
                 total=len(nodes),
                 desc="Downloading",
                 unit="node"))

    needs_install = [d for d in downloaded if d.install_py]

    # This may have to run after requirements have been installed.
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = list(
            tqdm(executor.map(post_install, needs_install), total=len(needs_install), desc="Installing", unit="node"))

    requirements = [part for d in downloaded if d.requirements for part in ('-r', d.requirements)]

    tqdm.write(f"Installing requirement with uv")
    uv(['pip', 'install', '--link-mode=copy'] + requirements)
