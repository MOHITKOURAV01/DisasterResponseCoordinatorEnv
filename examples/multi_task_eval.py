"""
Multi-task evaluation: Run all 4 tasks and compare performance.
"""
import httpx
import json
import time

ENV_URL = "https://mohitkourav-disasterresponsecoordinatorenv.hf.space"
TASKS = [
    "village_flood_rescue",
    "multi_district_cyclone", 
    "earthquake_aftershock",
    "full_72hr_operation"
]

def random_agent(obs):
    import random
    zones = obs.get("zones", [])
    zone_ids = [z["id"] for z in zones if z.get("population", 0) > 0]
    if not zone_ids:
        return {"tool_name": "advance_hour", "parameters": {}}
    zone = random.choice(zone_ids)
    tools = ["dispatch_team", "deploy_scout", "setup_comms", 
             "allocate_resource", "advance_hour"]
    tool = random.choice(tools)
    params = {"zone_id": zone}
    if tool == "dispatch_team":
        params["team_type"] = "rescue"
        params["transport"] = "truck"
    elif tool == "allocate_resource":
        params["resource_type"] = "food"
        params["quantity"] = 20
    return {"tool_name": tool, "parameters": params}


def evaluate_all_tasks():
    print("Multi-Task Evaluation")
    print("=" * 50)
    results = {}
    for task_id in TASKS:
        print(f"\nTask: {task_id}")
        try:
            obs_resp = httpx.post(
                f"{ENV_URL}/reset",
                json={"task_id": task_id},
                timeout=30
            ).json()
            obs = obs_resp.get("observation", obs_resp)
            
            total_reward = 0.0
            for step in range(20):
                action = random_agent(obs)
                resp = httpx.post(
                    f"{ENV_URL}/step", json=action, timeout=15
                ).json()
                total_reward += float(resp.get("reward", 0))
                obs = resp.get("observation", obs)
                if resp.get("done", False):
                    break
            
            state = httpx.get(f"{ENV_URL}/state", timeout=10).json()
            score = state.get("grader_score", 0.0)
            rescued = state.get("total_rescued", 0)
            results[task_id] = {"score": score, "rescued": rescued,
                                 "reward": total_reward}
            print(f"  Score: {score:.3f} | Rescued: {rescued} | "
                  f"Reward: {total_reward:.3f}")
            time.sleep(1)
        except Exception as e:
            print(f"  Error: {e}")
            results[task_id] = {"score": 0, "rescued": 0, "reward": 0}
    
    print("\n" + "=" * 50)
    print("SUMMARY:")
    for task, r in results.items():
        print(f"  {task}: score={r['score']:.3f}")
    return results


if __name__ == "__main__":
    evaluate_all_tasks()
