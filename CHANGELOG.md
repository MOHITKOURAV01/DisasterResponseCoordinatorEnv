# Changelog

## v1.0.0 — Grand Finale Release (April 2026)

### Environment
- 8-agent multi-agent disaster response coordination
- 4 India-specific tasks spanning easy → expert difficulty:
  - village_flood_rescue (Bihar, 50 people, 12 hours)
  - multi_district_cyclone (Odisha, 500 people, 36 hours)
  - earthquake_aftershock (Gujarat, 2000 people, 48 hours)
  - full_72hr_operation (Tamil Nadu, 5200 people, 72 hours)
- NetworkX graph-based crisis zone with 15-20 nodes
- 8 dynamic event types (aftershock, hospital overflow, comms down)
- 12-signal reward function with self-adaptive shaping
- Grader scores strictly in (0.001, 0.999) — deterministic

### Agents
- 8 specialized agents: Coordinator, Logistics, Medical,
  Air Support, Communications, Ground Rescue,
  Supply Chain, Field Assessment
- CurriculumEngine: failure-pattern analysis → adaptive scenarios
- Strategy memory: learned heuristics from past episodes

### Training
- Model: Qwen2.5-0.5B-Instruct (Unsloth 4-bit quantization)
- Method: GRPO via HuggingFace TRL
- Reward: live environment HTTP calls (no synthetic dataset)
- Results: Random 0.480 → GRPO Trained 0.776 (+62%)
- Rescue rate: 100% (50/50 people) with trained agent

### API
- 11 REST endpoints: /reset, /step, /state, /health,
  /agents, /graph, /metrics, /curriculum, /tasks,
  /plots, /
- Deployed on HuggingFace Spaces (Docker)
