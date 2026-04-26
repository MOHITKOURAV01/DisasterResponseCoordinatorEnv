# Changelog

## v1.0.0 — Grand Finale Release (April 2026)

### Added
- 8-agent multi-agent disaster response environment
- 4 India-specific tasks: Bihar flood, Odisha cyclone, 
  Gujarat earthquake, Tamil Nadu 72hr operation
- NetworkX graph-based crisis zone with 15-20 nodes
- 12-signal reward function with self-adaptive shaping
- CurriculumEngine: failure-analysis-based adaptive difficulty
- GRPO training pipeline via HuggingFace TRL + Unsloth
- Live environment reward function (no synthetic dataset)
- 11 REST API endpoints including /curriculum and /metrics
- Real-time dashboard with crisis map and agent monitoring
- Training results: Random 0.480 \u2192 GRPO Trained 0.776 (+62%)

### Environment
- Model: Qwen2.5-0.5B-Instruct via Unsloth 4-bit quantization
- Training: GRPO with live environment reward function
- Rescue rate: 100% (50/50 people) with trained agent
