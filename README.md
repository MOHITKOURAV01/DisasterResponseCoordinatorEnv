---
title: DisasterResponseCoordinatorEnv
emoji: 🚨
colorFrom: red
colorTo: blue
sdk: docker
pinned: false
---
# DisasterResponseCoordinatorEnv

**Autonomous Emergency Management Swarm — 8 AI Agents Coordinating Disaster Response**

[![HuggingFace Space](https://img.shields.io/badge/🤗-HuggingFace%20Space-blue)](https://huggingface.co/spaces/mohitkourav/DisasterResponseCoordinatorEnv)
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/MOHITKOURAV01/DisasterResponseCoordinatorEnv/blob/main/FINAL_training_notebook.ipynb)
[![OpenEnv](https://img.shields.io/badge/OpenEnv-Compatible-green)]()

> *When every second counts, AI must coordinate. This environment trains LLMs to save lives.*

## The Problem

India experiences devastating losses during natural disasters due to fragmented coordination in the critical first 72 hours. While AI helps predict weather, **no standardized RL environment exists to train AI agents for real-time, dynamic resource allocation under chaos.**

## The Environment

DisasterResponseCoordinatorEnv is a graph-based sandbox where **8 AI agents** coordinate rescue operations across a dynamic crisis zone:

| Agent | Role | Unique Decision |
|-------|------|----------------|
| Coordinator | LLM-powered brain | All resource allocation decisions |
| Logistics | Road graph, trucks, boats | Which route? Re-route on block? |
| Medical | Hospitals, triage | Which hospital? Triage priority? |
| Air Support | Helicopters, drones, fuel | Burn limited fuel now or save? |
| Communication | Signal, satellite phones | Act on unconfirmed info or wait? |
| Ground Rescue | Foot teams | Send slow-but-sure or wait for vehicle? |
| Supply Chain | Food, water, medicine | Distribute now or conserve? |
| Field Assessment | Scout drones, map updates | Explore unknown or reinforce known? |

### 4 India-Specific Tasks

| Task | Difficulty | Scenario | Duration |
|------|-----------|----------|----------|
| Village Flood Rescue | Easy | Bihar flooding, 50 people | 12 hours |
| Multi-District Cyclone | Medium | Odisha cyclone, 500 people | 36 hours |
| Earthquake Aftershock | Hard | Gujarat earthquake, 2000 people | 48 hours |
| Full 72hr Operation | Expert | Tamil Nadu super cyclone, 5200 people | 72 hours |

### 8 MCP Tools (Action Space)

`dispatch_team` · `allocate_resource` · `re_route` · `request_airlift` · `order_evacuation` · `deploy_scout` · `setup_comms` · `advance_hour`

## Hackathon Themes Covered

**Theme 1 — Multi-Agent:** 8 agents with competing interests (Medical vs Air Support on fuel, Supply vs Medical on conservation). Conflicts visible on dashboard.

**Theme 2 — Long-Horizon:** 72-hour simulation with 3 phases (Rescue→Relief→Rehabilitation). Sparse delayed rewards. Early decisions affect late outcomes.

**Theme 3 — World Modeling:** NetworkX graph with 15-20 nodes. 8 dynamic event types (aftershock, hospital overflow, comms breakdown, new survivors). 6 world state layers.

**Theme 4 — Self-Improvement:** Adaptive curriculum (auto-generates harder scenarios from failure analysis). Strategy memory (stores learned heuristics). Self-adaptive reward shaping.

## Results

### Reward Improvement

![Reward Curve](plots/reward_curve.png)
*Average episode reward over training. Agent learns to rescue more people and avoid blocked roads.*

![Before vs After](plots/before_after.png)
*Untrained agent: 25% rescue rate. Trained agent: 72%+ rescue rate.*

### Training Pipeline (TRL / GRPO)

Our training pipeline uses HuggingFace TRL's GRPOTrainer with a reward function that connects directly to the live environment via HTTP:

1. Environment generates crisis scenarios on HF Space
2. LLM agent selects actions (8 MCP tools)
3. Environment returns rewards from 12-signal reward function
4. GRPO optimizes policy using reward signals

| Metric | Random Baseline | Smart Agent | Improvement |
|--------|----------------|-------------|-------------|
| Grader Score | ~0.15 | ~0.65+ | +330% |
| People Rescued | ~12/50 | ~38/50 | +217% |
| Resource Efficiency | ~30% | ~70% | +133% |

![Step Rewards](plots/step_rewards.png)
*Step-by-step reward showing positive (rescue) and negative (blocked road) signals.*

![Task Comparison](plots/task_comparison.png)
*Performance across all 4 difficulty levels — trained agent outperforms baseline on all tasks.*

![Curriculum Evolution](plots/curriculum_evolution.png)
*Adaptive curriculum shifts training scenarios to target agent's weaknesses.*

## How to Run

### Try the Dashboard
Visit: https://huggingface.co/spaces/mohitkourav/DisasterResponseCoordinatorEnv

### Run Locally
```bash
git clone https://github.com/MOHITKOURAV01/DisasterResponseCoordinatorEnv.git
cd disaster-response-env
pip install -r requirements.txt
uvicorn server.main:app --port 7860
# Open http://localhost:7860
```

### Training (Colab)
Open the [Training Notebook](https://colab.research.google.com/github/MOHITKOURAV01/DisasterResponseCoordinatorEnv/blob/main/FINAL_training_notebook.ipynb) and click "Run All".

## Research Foundations

This environment combines techniques from:
- Hierarchical MARL for Emergency Responders (ICML 2024)
- ReinforceRouting — Graph-based dynamic routing with RL
- Self-Adaptive Reward Shaping (ICLR 2025)
- Curriculum Learning for RL (JMLR Survey)
- 72-hour PPO Relief Distribution with equity metrics
- Digital Risk Twin for Disaster Management (Nature 2025)

## Links

- [HuggingFace Space](https://huggingface.co/spaces/mohitkourav/DisasterResponseCoordinatorEnv)
- [YouTube Demo Video (90s)](#)
- [HuggingFace Blog Post](#)
- [Training Notebook (Colab)](#)

## Author

**Mohit Kourav** — Meta PyTorch OpenEnv Hackathon x Scaler School of Technology

---
*Built with FastAPI, NetworkX, Chart.js, and vanilla JS. Zero external cost.*
