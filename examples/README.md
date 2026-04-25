# Examples

## basic_episode.py
Runs one complete episode with a simple rule-based agent.
Shows how to connect, reset, step, and get grader score.

```bash
pip install httpx
python examples/basic_episode.py
```

## multi_task_eval.py  
Evaluates performance across all 4 tasks.
Useful for comparing different agent strategies.

```bash
python examples/multi_task_eval.py
```

## Quick API Reference

```python
import httpx
ENV_URL = "https://mohitkourav-disasterresponsecoordinatorenv.hf.space"

# Start episode
obs = httpx.post(f"{ENV_URL}/reset", 
                  json={"task_id": "village_flood_rescue"}).json()

# Take action
result = httpx.post(f"{ENV_URL}/step",
                     json={"tool_name": "dispatch_team",
                           "parameters": {"zone_id": "Z1",
                                         "team_type": "rescue",
                                         "transport": "truck"}}).json()

# Get full state
state = httpx.get(f"{ENV_URL}/state").json()
print(f"Score: {state['grader_score']}")
```
