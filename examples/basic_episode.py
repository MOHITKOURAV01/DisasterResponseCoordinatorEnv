"""
Basic example: Run one complete episode with a simple agent.
Shows how to connect to DisasterResponseCoordinatorEnv.
"""
import httpx
import json

ENV_URL = "https://mohitkourav-disasterresponsecoordinatorenv.hf.space"

def simple_agent(obs):
    """Simple rule-based agent for demonstration."""
    zones = obs.get("zones", [])
    critical = sorted(
        [z for z in zones if z.get("injured_critical", 0) > 0],
        key=lambda z: z.get("injured_critical", 0),
        reverse=True
    )
    if critical:
        return {
            "tool_name": "dispatch_team",
            "parameters": {
                "zone_id": critical[0]["id"],
                "team_type": "medical",
                "transport": "truck"
            }
        }
    return {"tool_name": "advance_hour", "parameters": {}}


def run_basic_episode():
    print("Connecting to environment...")
    health = httpx.get(f"{ENV_URL}/health", timeout=30).json()
    print(f"Status: {health['status']}")
    print(f"Tasks: {[t if isinstance(t,str) else t['id'] for t in health['tasks']]}")

    print("\nStarting episode: village_flood_rescue")
    obs_resp = httpx.post(
        f"{ENV_URL}/reset",
        json={"task_id": "village_flood_rescue"},
        timeout=30
    ).json()
    obs = obs_resp.get("observation", obs_resp)
    print(f"Zones: {len(obs.get('zones', []))}")
    print(f"Total population: {obs.get('total_population', 0)}")

    total_reward = 0.0
    for step in range(20):
        action = simple_agent(obs)
        resp = httpx.post(f"{ENV_URL}/step", json=action, timeout=15).json()
        reward = float(resp.get("reward", 0))
        total_reward += reward
        done = resp.get("done", False)
        rescued = resp.get("observation", {}).get("total_rescued", 0)
        print(f"  Step {step+1}: {action['tool_name']} | "
              f"reward={reward:+.3f} | rescued={rescued} | done={done}")
        obs = resp.get("observation", obs)
        if done:
            break

    state = httpx.get(f"{ENV_URL}/state", timeout=10).json()
    print(f"\nEpisode complete!")
    print(f"Total reward: {total_reward:.3f}")
    print(f"Grader score: {state.get('grader_score', 'N/A')}")
    print(f"People rescued: {state.get('total_rescued', 0)}")


if __name__ == "__main__":
    run_basic_episode()
