#!/bin/bash
# Deploy to HuggingFace Spaces
# Run: bash deploy.sh

echo "=== Deploying DisasterResponseCoordinatorEnv to HuggingFace ==="

# Step 1: Make sure git-lfs is installed
git lfs install

# Step 2: Clone HF Space (first time only)
# git clone https://huggingface.co/spaces/mohitkourav/DisasterResponseCoordinatorEnv hf-space

# Step 3: Copy files to HF Space
cp -r server/ hf-space/server/
cp requirements.txt hf-space/
cp Dockerfile hf-space/
cp openenv.yaml hf-space/
cp pyproject.toml hf-space/
cp inference.py hf-space/
cp README.md hf-space/
cp -r plots/ hf-space/plots/ 2>/dev/null || true
cp .dockerignore hf-space/

# Step 4: Push
cd hf-space
git add .
git commit -m "Deploy complete environment with dashboard"
git push

echo "=== Done! Check https://huggingface.co/spaces/mohitkourav/DisasterResponseCoordinatorEnv ==="
