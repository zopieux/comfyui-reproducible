#!/usr/bin/env nix-shell
#!nix-shell -i python -p "python3.withPackages(p: [ p.requests ])"

from pathlib import Path
import time
import shutil
import sys
import difflib
import os
import requests

WORKFLOW = {
    "1": {
        "inputs": {
            "filename_prefix": "tensorrt/X",
            "batch_size_min": 1,
            "batch_size_opt": 1,
            "batch_size_max": 4,
            "height_min": 512,
            "height_opt": 768,
            "height_max": 1024,
            "width_min": 512,
            "width_opt": 768,
            "width_max": 1024,
            "context_min": 1,
            "context_opt": 1,
            "context_max": 128,
            "num_video_frames": 1,
            "model": ["2", 0]
        },
        "class_type": "DYNAMIC_TRT_MODEL_CONVERSION",
        "_meta": {
            "title": "DYNAMIC TRT_MODEL CONVERSION"
        }
    },
    "2": {
        "inputs": {
            "ckpt_name": "X.safetensors"
        },
        "class_type": "CheckpointLoaderSimple",
        "_meta": {
            "title": "Load Checkpoint"
        }
    }
}


def enqueue_engine(model: str, checkpoints):
  ckpt = difflib.get_close_matches(model, checkpoints, n=1, cutoff=0.0)[0]
  prefix = model
  if "xl" in model.lower():
    WORKFLOW["1"]["inputs"]["width_opt"] = WORKFLOW["1"]["inputs"]["height_opt"] = 1024
    WORKFLOW["1"]["inputs"]["width_max"] = WORKFLOW["1"]["inputs"]["height_max"] = 1280
    prefix = f"{prefix}-SDXL"
  WORKFLOW["1"]["inputs"]["filename_prefix"] = f"tensorrt/{prefix}"
  WORKFLOW["2"]["inputs"]["ckpt_name"] = ckpt
  print(f"Enqueuing “${model}”, built from {ckpt} SD model, output prefix “{prefix}”")
  response = requests.post("http://127.0.0.1:7860/prompt", json={"prompt": WORKFLOW})
  response.raise_for_status()


if __name__ == '__main__':
  print(
      "For this to work, ensure that the container's models/tensorrt/ directory is mounted where engines need to be stored on the host."
  )
  checkpoints_host_dir = Path(os.environ["CHECKPOINTS_HOST_DIR"])
  checkpoints = {p.name for p in checkpoints_host_dir.glob("*.safetensors")}
  for model in os.environ["TRT_MODELS"].split(':'):
    enqueue_engine(model, checkpoints)
