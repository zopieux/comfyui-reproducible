#!/usr/bin/env nix-shell
#!nix-shell -p bash -i bash

# This self-referential horror adds a trailing `\` to all lines so that the
# Dockerfile is not polluted with backslashes on every single fucking line.
# It then builds the image with '.' as context. Name can be customized ($1).

set -Eeuo pipefail
NAME=${1:-${IMAGE_NAME}}
exec podman build -t "$NAME" --file <( sed -n '/^exec /,$p' "$0" | tail -n +2 | awk '{if(NR>1){if(p!~/^$/&&$0!~/^$/){print p" \\"}else{print p}}p=$0}END{if(NR>0)print p}' ) .

ARG CUDA_SHORT_VERSION=12.8

ARG CUDA_IMAGE="${CUDA_SHORT_VERSION}.1-devel-ubuntu24.04"

FROM nvidia/cuda:${CUDA_IMAGE}

ARG
  PYTHON_VERSION=3.12
  COMFYUI_VERSION=0.3.44
  NUNCHAKU_VERSION=0.3.1
  TORCH_VERSION=2.7
  TORCHVISION_VERSION=0.22
  TORCHAUDIO_VERSION=2.7

ENV
  DEBIAN_FRONTEND=noninteractive
  TZ=Europe/Zurich
  VENV=/venv
  COMFYUI_PATH=/ComfyUI

ENV
  PATH=/root/.local/bin:$PATH

WORKDIR /

RUN
  --mount=target=/var/lib/apt/lists,type=cache,sharing=locked
  --mount=target=/var/cache/apt,type=cache,sharing=locked
  apt-get update -yqq
  && apt-get install -y --no-install-recommends build-essential ca-certificates ninja-build strace ncdu curl g++-11 gcc-11 git ibverbs-providers libgl1 libglib2.0-bin libibumad3 libibverbs1 libibverbs-dev libnl-3-200 libnl-route-3-200 librdmacm1 ncdu python${PYTHON_VERSION}-dev software-properties-common tzdata wget
  && update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-11 1
  && update-alternatives --set gcc /usr/bin/gcc-11
  && update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-11 1
  && update-alternatives --set g++ /usr/bin/g++-11
  && apt-get clean

RUN
  --mount=type=cache,target=/root/.cache
  curl -LsSf https://astral.sh/uv/install.sh | sh
  && uv venv --python ${PYTHON_VERSION} --seed ${VENV}

RUN
  sc() { echo "#!/bin/bash\n$1" >$2 && chmod +x $2 ; }
  && mkdir -p /root/.local/bin
  && sc 'exec "$@"' /entrypoint
  && sc 'uv pip install --python /venv "$@"' /root/.local/bin/pyinstall
  && sc 'uv run --python /venv "$@"' /root/.local/bin/pyrun
  && sc 'pyrun /ComfyUI/custom_nodes/ComfyUI-Manager/cm-cli.py "$@"' /root/.local/bin/cmcli

RUN
  --mount=type=cache,target=/root/.cache
  pyinstall wheel
  && PYV=$(bash -c 'v=${PYTHON_VERSION}; echo ${v//.}')
  && CUDAV=$(bash -c 'v=$(ls -1 /usr/local/ | grep -oE "cuda-[0-9]+\.[0-9]+" | cut -d- -f2); echo ${v//.}')
  && pyinstall --index-url https://download.pytorch.org/whl/cu${CUDAV}
    torch==${TORCH_VERSION} torchvision==${TORCHVISION_VERSION} torchaudio==${TORCHAUDIO_VERSION}
  && pyinstall numpy ninja diffusers transformers accelerate sentencepiece protobuf huggingface_hub onnxruntime onnxruntime-gpu
  && pyinstall "https://huggingface.co/mit-han-lab/nunchaku/resolve/main/nunchaku-${NUNCHAKU_VERSION}%2Btorch${TORCH_VERSION}-cp${PYV}-cp${PYV}-linux_x86_64.whl?download=true"

RUN
  --mount=type=cache,target=/root/.cache
  cd /
  && git clone --depth=1 --branch=v${COMFYUI_VERSION} https://github.com/comfyanonymous/ComfyUI
  && git clone --depth=1 https://github.com/ltdrdata/ComfyUI-Manager.git /ComfyUI/custom_nodes/ComfyUI-Manager
  && pyinstall
    -r /ComfyUI/requirements.txt
    -r /ComfyUI/custom_nodes/ComfyUI-Manager/requirements.txt

# --mount=type=cache,target=/root/.cache
RUN
  mkdir -p /ComfyUI/user/default/ComfyUI-Manager
  && printf '[default]\nnetwork_mode = offline\nuse_uv = true\n' > /ComfyUI/user/default/ComfyUI-Manager/config.ini
  && cmcli install --exit-on-fail
    ComfyMath
    comfyui_controlnet_aux
    comfyui_essentials
    ComfyUI_IPAdapter_plus
    comfyui_layerstyle
    ComfyUI_LayerStyle_Advance
    comfyui_tensorrt
    ComfyUI_UltimateSDUpscale
    comfyui-advancedliveportrait
    ComfyUI-Chibi-Nodes
    ComfyUI-Crystools
    comfyui-custom-scripts
    comfyui-impact-pack
    comfyui-impact-subpack
    comfyui-inspire-pack
    comfyui-kjnodes
    comfyui-layerdiffuse
    ComfyUI-nunchaku
    ComfyUI-segment-anything-2
    comfyui-various
    comfyui-wd14-tagger
    efficiency-nodes-comfyui
    https://github.com/laksjdjf/Batch-Condition-ComfyUI
    https://github.com/zopieux/ComfyUI-zopi
    rgthree-comfy
    was-node-suite-comfyui
  && rm -rf /root/.cache

# No idea why pip is needed, but uv doesn't do the right thing.
RUN
  --mount=type=cache,target=/root/.cache
  pyrun python -m pip install -I onnxruntime-gpu opencv-contrib-python

COPY ./paths_to_delete ./unfuck.sh /

RUN /unfuck.sh

RUN
  while IFS= read -r line; do rm -rf "$line"; done < /paths_to_delete
  && rm -rf /paths_to_delete /unfuck.sh /root/.cache /tmp/**
  && mkdir -p /ComfyUI/models /ComfyUI/user/default

ENTRYPOINT ["/entrypoint"]
