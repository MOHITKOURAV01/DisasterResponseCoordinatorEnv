import os
import json
import httpx
import sys
from openai import OpenAI

HF_TOKEN = os.getenv("HF_TOKEN", "")
API_BASE_URL = os.getenv("API_BASE_URL", "https://api-inference.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-1.5B-Instruct")
ENV_URL = os.getenv("ENV_URL", "http://localhost:7860")

SYSTEM_PROMPT = """You are a disaster response coordinator managing 8 specialized agents:
- Logistics (roads/transport), Medical (hospitals/triage), Air Support (helicopters/fuel)
- Communication (signal/satellite), Ground Rescue (foot teams), Supply Chain (inventory)
- Field Assessment (drones/scouting), and you as Coordinator.

You receive agent reports and crisis zone state. Choose ONE tool to call as your next action.

Available tools:
- dispatch_team: Send team to zone. Params: zone_id, team_type (rescue/medical/supply), transport (truck/boat/helicopter/foot)
- allocate_resource: Send supplies. Params: zone_id, resource_type (food/water/medicine/tents), quantity
- re_route: Change team's path. Params: team_id
- request_airlift: Deploy helicopter. Params: zone_id
- order_evacuation: Evacuate zone to shelter. Params: zone_id, shelter_id
- deploy_scout: Send drone to scout. Params: zone_id
- setup_comms: Restore communication. Params: zone_id
- advance_hour: Move time forward 1 hour.

Rules:
- Prioritize critical patients first
- Don't send trucks to flooded roads (use boats)
- Conserve helicopter fuel for emergencies
- Check communication before sending teams to dark zones
- Balance resources across all zones (equity matters)

{strategy_injection}

Respond with ONLY valid JSON: {{"tool_name": "...", "parameters": {{...}}}}
Do NOT include any other text."""


def smart_fallback(obs: dict, step: int) -> dict:
    """Rule-based fallback when LLM fails or is unavailable."""
    zones = obs.get("zones", [])
    teams = obs.get("teams", [])
    resources = obs.get("resources", {})

    # Priority 1: Scout dark zones
    dark_zones = [z for z in zones if not z.get("has_communication", True)]
    if dark_zones and step < 5:
        return {"tool_name": "deploy_scout", "parameters": {"zone_id": dark_zones[0].get("zone_id", dark_zones[0].get("id", "Z1"))}}

    # Priority 2: Setup comms in dark zones
    if dark_zones:
        return {"tool_name": "setup_comms", "parameters": {"zone_id": dark_zones[0].get("zone_id", dark_zones[0].get("id", "Z1"))}}

    # Priority 3: Dispatch to zones with most critical patients
    critical_zones = sorted([z for z in zones if z.get("injured_critical", 0) > 0 and z.get("rescued", 0) < z.get("population", 0)],
                           key=lambda z: z.get("injured_critical", 0), reverse=True)
    idle_teams = [t for t in teams if t.get("status") == "idle"]

    if critical_zones and idle_teams:
        zone = critical_zones[0]
        zone_id = zone.get("zone_id", zone.get("id", "Z1"))
        transport = "boat" if zone.get("status") == "flooded" else "truck"
        if resources.get("fuel_helicopter", 0) > 2 and zone.get("injured_critical", 0) > 15:
            transport = "helicopter"
        return {"tool_name": "dispatch_team", "parameters": {"zone_id": zone_id, "team_type": "rescue", "transport": transport}}

    # Priority 4: Airlift if fuel available and critical patients
    if critical_zones and resources.get("fuel_helicopter", 0) > 0:
        zone_id = critical_zones[0].get("zone_id", critical_zones[0].get("id", "Z1"))
        return {"tool_name": "request_airlift", "parameters": {"zone_id": zone_id}}

    # Priority 5: Allocate resources to needy zones
    needy = [z for z in zones if z.get("population", 0) > z.get("rescued", 0) and z.get("distress_level", 0) > 0.3]
    if needy and resources.get("water_units", 0) > 20:
        zone_id = needy[0].get("zone_id", needy[0].get("id", "Z1"))
        return {"tool_name": "allocate_resource", "parameters": {"zone_id": zone_id, "resource_type": "water", "quantity": 20}}

    # Default: advance time
    return {"tool_name": "advance_hour", "parameters": {}}


def run_episode(task_id: str, use_llm: bool = True):
    """Run a single episode on the environment."""
    print(f"\n{'='*60}")
    print(f"[START] Task: {task_id}")
    print(f"{'='*60}")

    # Reset environment
    resp = httpx.post(f"{ENV_URL}/reset", json={"task_id": task_id}, timeout=30)
    if resp.status_code != 200:
        print(f"[ERROR] Reset failed: {resp.text}")
        return
    obs = resp.json()

    # Get strategy injection from curriculum
    strategy_injection = ""
    try:
        cur = httpx.get(f"{ENV_URL}/curriculum", timeout=10).json()
        strategies = cur.get("strategy_memory", [])
        if strategies:
            lines = ["Learned strategies from past episodes:"]
            for s in strategies[:5]:
                lines.append(f"- {s.get('rule', '')}")
            strategy_injection = "\n".join(lines)
    except Exception:
        pass

    # Setup LLM client
    client = None
    if use_llm and HF_TOKEN:
        try:
            client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)
        except Exception:
            client = None

    step = 0
    total_reward = 0
    done = False

    while not done and step < 100:
        step += 1
        action = None

        # Try LLM first
        if client:
            try:
                prompt = SYSTEM_PROMPT.format(strategy_injection=strategy_injection)
                state_summary = json.dumps({
                    "hour": obs.get("current_hour", 0),
                    "phase": obs.get("current_phase", "rescue"),
                    "zones": [{k: z[k] for k in ("zone_id", "name", "population", "injured_critical", "rescued", "status", "has_communication") if k in z} for z in obs.get("zones", [])[:5]],
                    "resources": {k: obs.get("resources", {}).get(k, 0) for k in ("fuel_helicopter", "water_units", "food_units", "boats_available")},
                    "agent_reports": {name: {"recommendation": r.get("recommendation", ""), "urgency": r.get("urgency", "normal"), "conflict_with": r.get("conflict_with")}
                                     for name, r in list(obs.get("agent_reports", {}).items())[:4]},
                }, indent=None)

                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[{"role": "system", "content": prompt}, {"role": "user", "content": f"Current state:\n{state_summary}\n\nChoose your next action:"}],
                    max_tokens=150, temperature=0.3,
                )
                raw = response.choices[0].message.content.strip()
                # Parse JSON from response
                if "{" in raw:
                    json_str = raw[raw.index("{"):raw.rindex("}")+1]
                    action = json.loads(json_str)
            except Exception as e:
                pass

        # Fallback to rule-based
        if not action:
            action = smart_fallback(obs, step)

        # Send action to environment
        try:
            resp = httpx.post(f"{ENV_URL}/step", json=action, timeout=30)
            result = resp.json()
            obs = result.get("observation", obs)
            reward = result.get("reward", 0)
            done = result.get("done", False)
            total_reward += reward

            event = ""
            events = obs.get("dynamic_events", [])
            if events:
                event = f" | EVENT: {events[0]}"

            print(f"[STEP {step:3d}] {action['tool_name']:20s} reward={reward:+.3f} total={total_reward:.3f}{event}")

            if done:
                grader = result.get("info", {}).get("grader_score", 0)
                print(f"\n[END] Episode complete!")
                print(f"  Grader score: {grader:.4f}")
                print(f"  Total reward: {total_reward:.4f}")
                print(f"  Steps taken: {step}")
                print(f"  Rescued: {obs.get('total_rescued', 0)}")
                print(f"  Deaths: {obs.get('total_deaths', 0)}")
        except Exception as e:
            print(f"[ERROR] Step failed: {e}")
            break

    return total_reward


def main():
    """Run all 4 tasks."""
    print("DisasterResponseCoordinatorEnv - Agent Runner")
    print(f"Environment: {ENV_URL}")
    print(f"LLM: {MODEL_NAME if HF_TOKEN else 'FALLBACK (no HF_TOKEN)'}")

    tasks = ["village_flood_rescue", "multi_district_cyclone", "earthquake_aftershock", "full_72hr_operation"]

    for task in tasks:
        try:
            run_episode(task, use_llm=bool(HF_TOKEN))
        except Exception as e:
            print(f"[ERROR] Task {task} failed: {e}")


if __name__ == "__main__":
    main()
