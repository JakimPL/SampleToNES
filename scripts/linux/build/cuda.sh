#!/usr/bin/env bash

set -e

# CUDA runtime libraries required by cupy-cuda12x (the [gpu] extra).
# Provides libcudart.so (cuda-cudart-12-0) and libnvrtc.so (cuda-nvrtc-12-0).
#
# These packages are served from NVIDIA's CUDA apt repository. If apt cannot
# locate them, set up the repository first: https://developer.nvidia.com/cuda-downloads
CUDA_PACKAGES="cuda-cudart-12-0 cuda-nvrtc-12-0"

echo "Installing CUDA runtime libraries for GPU support: ${CUDA_PACKAGES}"
sudo apt-get update
if ! sudo apt-get install -y ${CUDA_PACKAGES}; then
    echo
    echo "ERROR: Failed to install CUDA runtime libraries (${CUDA_PACKAGES})."
    echo "These packages come from NVIDIA's CUDA apt repository. Set it up first:"
    echo "  https://developer.nvidia.com/cuda-downloads"
    exit 1
fi
echo "CUDA runtime libraries installed."
