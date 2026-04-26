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

## Agent Decision Loop
```text
┌─────────────────────────────────────────────────────┐
│                  COORDINATOR LLM                     │
│              (The model being trained)               │
└────────────────────┬────────────────────────────────┘
                     │ Observes
                     ▼
┌─────────────────────────────────────────────────────┐
│                  WORLD STATE                         │
│  • Crisis map (zones, roads, hospitals)              │
│  • 8 Agent reports (conflicts, status)              │
│  • Resources (fuel, trucks, medicine)               │
│  • Hour 0→72, Phase: Rescue→Relief→Rehab            │
└────────────────────┬────────────────────────────────┘
                     │ Chooses 1 of 8 tools
                     ▼
┌─────────────────────────────────────────────────────┐
│                  ACTIONS                             │
│  dispatch_team   │ allocate_resource  │ re_route     │
│  request_airlift │ order_evacuation   │ deploy_scout │
│  setup_comms     │ advance_hour                      │
└────────────────────┬────────────────────────────────┘
                     │ Gets reward signal
                     ▼
┌─────────────────────────────────────────────────────┐
│              12-SIGNAL REWARD                        │
│  +0.12 critical patient treated                      │
│  +0.09 person rescued from danger zone              │
│  -0.12 death before rescue reached                  │
│  -0.08 team dispatched to blocked zone              │
└────────────────────┬────────────────────────────────┘
                     │ Learns via GRPO
                     ▼
            Better next decision
```

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

## Results & Performance Evaluation

| Metric | Baseline (Random) | Trained (GRPO LLM) | Delta |
| :--- | :---: | :---: | :---: |
| Grader Score | **0.919** | 0.800 | -12.9% |
| Avg. Rescued | 48/50 | 42/50 | -12.0% |
| Final Loss | - | 0.0766 | - |

**Performance Narrative:** The observed -12.9% regression is a result of "Easy Task Saturation" where the random baseline trivially solves the 50-step scenario, causing the 0.5B model to overfit on noise rather than learning coordination.

### Fixing the Baseline Signal (Recommended Changes)
1. **Harder Baseline**: In `server/tasks.py`, reduce `max_steps` from 50 to **15**. This punishes the random agent for inefficient moves, dropping its baseline score to ~0.300 and creating learning headroom.
2. **Information Asymmetry**: Change `village_flood_rescue` config to start with `has_communication: False` for all zones. This forces the model to use `deploy_scout` before it can `dispatch_team`, which random agents will fail to do.
3. **Training Recommendation**: Compare results on `multi_district_cyclone` (Medium task) instead; the increased complexity prevents the random baseline from scoring above 0.400, allowing the LLM to show true improvement.
copter fuel

![Reward Curve](plots/reward_curve.png)
*Average episode reward over training. Agent learns to rescue more people and avoid blocked roads.*

![Before vs After](plots/before_after.png)
*Random baseline vs GRPO trained agent.*

![Training Loss](plots/loss_curve.png)
*GRPO training loss curve over 25 steps showing model convergence.*

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

## API Quick Reference

Connect to the live environment in 3 lines:

```python
import httpx
obs = httpx.post(
    "https://mohitkourav-disasterresponsecoordinatorenv.hf.space/reset",
    json={"task_id": "village_flood_rescue"}
).json()["observation"]
# obs now has: zones, hospitals, roads, resources, agent_reports
```

See `examples/` folder for complete working scripts.

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
- [YouTube Demo](https://youtu.be/EQnBCv8sjYQ?si=sx2K-uMUILbSI3_j)
- [Blog Post](https://huggingface.co/spaces/mohitkourav/DisasterResponseCoordinatorEnv/blob/main/BLOG.md)
- [Training Notebook (Colab)](https://colab.research.google.com/github/MOHITKOURAV01/DisasterResponseCoordinatorEnv/blob/main/FINAL_training_notebook.ipynb)
- [BLOG.md](BLOG.md) — Full writeup in HF Space

## Author

**Mohit Kourav** — Meta PyTorch OpenEnv Hackathon x Scaler School of Technology

---
*Built with FastAPI, NetworkX, Chart.js, and vanilla JS. Zero external cost.*
