from typing import Dict, List, Optional, Any
import random
import copy
from server.models import (
    Zone, Hospital, Road, Team, Resource, Observation, Action,
    StepResult, FullState, AgentReport, DynamicEvent, Phase,
    ZoneStatus, RoadStatus, TeamType, TransportType, EventType, AgentStatus
)
from server.graph import CrisisGraph
from server.agents import create_all_agents, BaseAgent
from server.rewards import RewardCalculator
from server.curriculum import CurriculumEngine
from server.tasks import get_task_config, generate_random_event


class DisasterResponseEnv:
    """Core disaster response coordination environment.

    Implements all 4 hackathon themes:
    - Theme 1 (Multi-Agent): 8 agents with competing interests
    - Theme 2 (Long-Horizon): 72-hour 3-phase simulation with sparse delayed rewards
    - Theme 3 (World Modeling): Graph-based map with 6 world layers + dynamic events
    - Theme 4 (Self-Improvement): Adaptive curriculum + strategy memory
    """

    VALID_TOOLS = [
        "dispatch_team", "allocate_resource", "re_route",
        "request_airlift", "order_evacuation", "deploy_scout",
        "setup_comms", "advance_hour"
    ]

    def __init__(self):
        self.graph = CrisisGraph()
        self.agents: Dict[str, BaseAgent] = {}
        self.reward_calc = RewardCalculator()
        self.curriculum = CurriculumEngine()

        # State
        self.zones: List[dict] = []
        self.hospitals: List[dict] = []
        self.teams: List[dict] = []
        self.resources: dict = {}
        self.task_config: dict = {}
        self.task_id: str = ""

        # Timeline
        self.current_hour: int = 0
        self.current_phase: str = "rescue"
        self.step_number: int = 0
        self.max_steps: int = 50
        self.max_hours: int = 72

        # History
        self.action_history: List[dict] = []
        self.dynamic_events_log: List[str] = []
        self.pending_events: List[str] = []

        # Tracking
        self.total_rescued: int = 0
        self.total_deaths: int = 0
        self.episode_number: int = 0
        self.previous_actions: List[str] = []
        self.done: bool = False

    def reset(self, task_id: str = "village_flood_rescue") -> dict:
        """Start a new episode. Load task config, build graph, create agents.
        Returns initial observation as dict.
        """
        self.task_id = task_id
        self.task_config = get_task_config(task_id)
        self.episode_number += 1

        # Check if curriculum should generate harder scenario
        if self.episode_number > 1 and self.curriculum.difficulty > 4:
            self.task_config = self.curriculum.generate_harder_scenario(self.task_config)

        # Build graph
        self.graph = CrisisGraph()
        self.graph.build_from_task(self.task_config)

        # Initialize zones from node data
        self.zones = []
        self.hospitals = []
        for node in self.task_config.get("nodes", []):
            if node.get("type") in ("village", "urban", "coastal"):
                self.zones.append({
                    "zone_id": node["id"],
                    "name": node.get("name", node["id"]),
                    "zone_type": node.get("type", "village"),
                    "population": node.get("population", 0),
                    "injured_critical": node.get("injured_critical", 0),
                    "injured_moderate": node.get("injured_moderate", 0),
                    "rescued": 0,
                    "dead": 0,
                    "status": node.get("status", "safe"),
                    "has_communication": node.get("has_communication", True),
                    "last_contact_hours_ago": node.get("last_contact_hours_ago", 0),
                    "distress_level": 0.0,
                })
            elif node.get("type") == "hospital":
                self.hospitals.append({
                    "hospital_id": node["id"],
                    "name": node.get("name", node["id"]),
                    "capacity": node.get("capacity", 100),
                    "current_patients": node.get("current_patients", 0),
                    "has_power": node.get("has_power", True),
                    "is_damaged": node.get("is_damaged", False),
                    "capacity_pct": round(node.get("current_patients", 0) / max(node.get("capacity", 1), 1) * 100, 1),
                })

        # Initialize teams
        self.teams = []
        for t in self.task_config.get("initial_teams", []):
            self.teams.append({
                "team_id": t["team_id"],
                "team_type": t.get("team_type", "rescue"),
                "transport": t.get("transport", "truck"),
                "current_zone": t.get("current_zone", "BASE"),
                "destination": None,
                "status": "idle",
                "eta_hours": 0.0,
                "assigned_task": None,
            })

        # Initialize resources
        self.resources = copy.deepcopy(self.task_config.get("initial_resources", {}))

        # Reset timeline
        self.current_hour = 0
        self.current_phase = "rescue"
        self.step_number = 0
        self.max_steps = self.task_config.get("max_steps", 50)
        self.max_hours = self.task_config.get("max_hours", 72)

        # Reset tracking
        self.action_history = []
        self.dynamic_events_log = []
        self.pending_events = []
        self.total_rescued = 0
        self.total_deaths = 0
        self.previous_actions = []
        self.done = False

        # Create agents
        self.agents = create_all_agents()

        # Reset reward calculator
        self.reward_calc.reset()
        self.curriculum.reset_episode()

        return self._build_observation_dict()

    def step(self, action: dict) -> dict:
        """Execute one step. Coordinator takes an action.

        Args: action dict with 'tool_name' and 'parameters'
        Returns: {observation, reward, done, info}
        """
        if self.done:
            return {
                "observation": self._build_observation_dict(),
                "reward": 0.0,
                "done": True,
                "info": {"error": "Episode already finished. Call reset()."}
            }

        self.step_number += 1
        tool_name = action.get("tool_name", "")
        params = action.get("parameters", {})

        # Validate action
        if tool_name not in self.VALID_TOOLS:
            result = {"invalid_action": True, "repeated_action": False, "wasted_time": True}
            reward = self.reward_calc.calculate(action, result, self._get_state_for_reward())
            self.action_history.append({
                "step": self.step_number, "tool_name": tool_name,
                "params_short": str(params)[:60], "reward": reward,
                "event": None, "conflict_resolved": None, "hour": self.current_hour,
            })
            obs = self._build_observation_dict()
            self.done = self._check_done()
            return {"observation": obs, "reward": reward, "done": self.done,
                    "info": {"error": f"Invalid tool: {tool_name}", "grader_score": 0.0}}

        # Check repeated action
        action_key = f"{tool_name}:{str(sorted(params.items()))}"
        is_repeated = action_key in self.previous_actions[-3:] if self.previous_actions else False
        self.previous_actions.append(action_key)

        # 1. ALL agents assess current state
        agent_reports = {}
        state_for_agents = self._get_state_for_agents()
        for name, agent in self.agents.items():
            try:
                report = agent.assess(state_for_agents)
                agent_reports[name] = report.model_dump() if hasattr(report, 'model_dump') else report.dict() if hasattr(report, 'dict') else {"agent_name": name}
            except Exception:
                agent_reports[name] = {"agent_name": name, "status": "idle", "current_action": "Error", "recommendation": ""}

        # 2. Execute the action
        exec_result = self._execute_action(tool_name, params)
        exec_result["repeated_action"] = is_repeated

        # 3. ALL agents react to coordinator's decision
        for name, agent in self.agents.items():
            try:
                agent.react(action, state_for_agents)
            except Exception:
                pass

        # 4. Check for dynamic events
        event_text = self._check_dynamic_events()

        # 5. Advance time-dependent state
        self._tick_time_effects()

        # 6. Calculate reward
        reward = self.reward_calc.calculate(action, exec_result, self._get_state_for_reward())

        # 7. Record action
        conflict_resolved = None
        for name, report in agent_reports.items():
            if isinstance(report, dict) and report.get("conflict_with"):
                conflict_resolved = f"{name} vs {report['conflict_with']}: Coordinator chose {tool_name}"
                break

        self.action_history.append({
            "step": self.step_number, "tool_name": tool_name,
            "params_short": str(params)[:60], "reward": reward,
            "event": event_text, "conflict_resolved": conflict_resolved,
            "hour": self.current_hour,
            "long_term_impact": exec_result.get("long_term_impact"),
        })

        # 8. Update pending events
        if event_text:
            self.pending_events = [event_text]
        else:
            self.pending_events = []

        # 9. Check done
        self.done = self._check_done()

        # 10. If done, run curriculum analysis
        info = {"grader_score": 0.0}
        if self.done:
            grader_score = self.reward_calc.grade_episode(self._get_state_for_reward())
            self.curriculum.analyze_episode(self._get_state_for_agents())
            self.curriculum.extract_strategies(self._get_state_for_agents())
            info["grader_score"] = grader_score
            info["episode_number"] = self.episode_number
            info["total_rescued"] = self.total_rescued
            info["total_deaths"] = self.total_deaths
            info["difficulty"] = self.curriculum.difficulty

        obs = self._build_observation_dict()
        return {"observation": obs, "reward": reward, "done": self.done, "info": info}

    def state(self) -> dict:
        """Return full state for debugging and dashboard."""
        return {
            "observation": self._build_observation_dict(),
            "total_reward": round(self.reward_calc.total_reward_this_episode, 4),
            "action_history": self.action_history[-50:],
            "strategy_memory": self.curriculum.strategy_memory,
            "curriculum_difficulty": self.curriculum.difficulty,
            "episode_number": self.episode_number,
            "current_weakness": self.curriculum.current_weakness,
            "total_rescued": self.total_rescued,
            "total_deaths": self.total_deaths,
            "reward_stats": self.reward_calc.get_stats(),
            "grading_config": self.task_config.get("grading_config", {}),
            "max_hours": self.max_hours,
            "resources": self.resources,
            "done": self.done,
        }

    # ==================== ACTION EXECUTORS ====================

    def _execute_action(self, tool_name: str, params: dict) -> dict:
        """Execute a coordinator action. Returns result dict for reward calculation."""

        if tool_name == "dispatch_team":
            return self._action_dispatch_team(params)
        elif tool_name == "allocate_resource":
            return self._action_allocate_resource(params)
        elif tool_name == "re_route":
            return self._action_re_route(params)
        elif tool_name == "request_airlift":
            return self._action_request_airlift(params)
        elif tool_name == "order_evacuation":
            return self._action_order_evacuation(params)
        elif tool_name == "deploy_scout":
            return self._action_deploy_scout(params)
        elif tool_name == "setup_comms":
            return self._action_setup_comms(params)
        elif tool_name == "advance_hour":
            return self._action_advance_hour(params)

        return {"invalid_action": True, "wasted_time": True}

    def _action_dispatch_team(self, params: dict) -> dict:
        """Send a team to a zone."""
        zone_id = params.get("zone_id", "")
        team_type = params.get("team_type", "rescue")
        transport = params.get("transport", "truck")

        # Find idle team of matching type
        team = None
        for t in self.teams:
            if t["status"] == "idle" and t["team_type"] == team_type:
                team = t
                break
        if not team:
            for t in self.teams:
                if t["status"] == "idle":
                    team = t
                    break

        if not team:
            return {"wasted_time": True, "invalid_action": False}

        # Check if route exists
        transport_enum = TransportType(transport) if transport in [e.value for e in TransportType] else TransportType.TRUCK
        path = self.graph.get_shortest_path(team["current_zone"], zone_id, transport_enum)

        if path is None and transport != "helicopter":
            return {"blocked_road_hit": True}

        # Check transport vs terrain
        zone = self._find_zone(zone_id)
        correct_transport = True
        if zone and zone.get("status") == "flooded" and transport == "truck":
            correct_transport = False

        # Dispatch
        travel_time = self.graph.get_travel_time(team["current_zone"], zone_id, transport_enum)
        if travel_time < 0:
            travel_time = 1.0

        team["status"] = "moving"
        team["destination"] = zone_id
        team["transport"] = transport
        team["eta_hours"] = travel_time
        team["assigned_task"] = f"dispatch_to_{zone_id}"

        return {
            "correct_transport": correct_transport,
            "efficient_action": correct_transport,
            "long_term_impact": f"Team {team['team_id']} dispatched via {transport} to {zone_id} — ETA {travel_time}h",
        }

    def _action_allocate_resource(self, params: dict) -> dict:
        """Allocate supplies to a zone."""
        resource_type = params.get("resource_type", "water")
        quantity = params.get("quantity", 10)
        zone_id = params.get("zone_id", "")

        # Check availability
        key_map = {"food": "food_units", "water": "water_units", "medicine": "medicine_units", "tents": "tents"}
        res_key = key_map.get(resource_type, "water_units")
        available = self.resources.get(res_key, 0)

        if available <= 0:
            return {"resource_exhausted": True}

        actual = min(quantity, available)
        self.resources[res_key] = available - actual

        # Check if this helps equity
        equity = self._calculate_equity()

        return {
            "efficient_action": True,
            "equity_score": equity,
        }

    def _action_re_route(self, params: dict) -> dict:
        """Re-route a team that hit a blocked road."""
        team_id = params.get("team_id", "")

        team = None
        for t in self.teams:
            if t["team_id"] == team_id and t["status"] == "moving":
                team = t
                break

        if not team:
            return {"wasted_time": True}

        # Find alternate route
        dest = team.get("destination", "")
        if dest:
            alt_path = self.graph.get_shortest_path(team["current_zone"], dest, TransportType.BOAT)
            if alt_path:
                new_time = self.graph.get_travel_time(team["current_zone"], dest, TransportType.BOAT)
                team["eta_hours"] = max(new_time, 0.5)
                team["transport"] = "boat"
                return {"rerouted": True, "efficient_action": True}

        return {"wasted_time": True}

    def _action_request_airlift(self, params: dict) -> dict:
        """Deploy helicopter for airlift."""
        zone_id = params.get("zone_id", "")

        fuel = self.resources.get("fuel_helicopter", 0)
        if fuel <= 0:
            return {"resource_exhausted": True}

        # Use fuel
        self.resources["fuel_helicopter"] = fuel - 1.0

        # Rescue people via airlift
        zone = self._find_zone(zone_id)
        rescued = 0
        if zone:
            can_rescue = min(zone.get("population", 0) - zone.get("rescued", 0), 15)
            if can_rescue > 0:
                zone["rescued"] = zone.get("rescued", 0) + can_rescue
                self.total_rescued += can_rescue
                rescued = can_rescue
                self.graph.update_node_data(zone_id, rescued=zone["rescued"])

        return {
            "rescued_count": rescued,
            "efficient_action": rescued > 0,
            "correct_transport": True,
            "long_term_impact": f"Helicopter used — fuel now {self.resources['fuel_helicopter']} trips remaining",
        }

    def _action_order_evacuation(self, params: dict) -> dict:
        """Evacuate people from zone to shelter."""
        zone_id = params.get("zone_id", "")
        shelter_id = params.get("shelter_id", "")

        zone = self._find_zone(zone_id)
        if not zone:
            return {"invalid_action": True}

        can_evac = zone.get("population", 0) - zone.get("rescued", 0)
        evacuated = min(can_evac, 50)

        if evacuated > 0:
            zone["rescued"] = zone.get("rescued", 0) + evacuated
            self.total_rescued += evacuated
            self.graph.update_node_data(zone_id, rescued=zone["rescued"])

        return {
            "rescued_count": evacuated,
            "efficient_action": evacuated > 0,
        }

    def _action_deploy_scout(self, params: dict) -> dict:
        """Send drone to scout a zone. May discover new survivors."""
        zone_id = params.get("zone_id", "")

        zone = self._find_zone(zone_id)
        discovered = 0

        if zone and not zone.get("has_communication", True):
            # Restore communication
            zone["has_communication"] = True
            zone["last_contact_hours_ago"] = 0
            self.graph.update_node_data(zone_id, has_communication=True, last_contact_hours_ago=0)

            # Random chance to discover new survivors
            if random.random() < 0.4:
                new_people = random.randint(10, 40)
                zone["population"] = zone.get("population", 0) + new_people
                zone["injured_critical"] = zone.get("injured_critical", 0) + int(new_people * 0.2)
                discovered = new_people
                self.graph.update_node_data(zone_id, population=zone["population"])

        return {
            "discovered_count": discovered,
            "efficient_action": True,
        }

    def _action_setup_comms(self, params: dict) -> dict:
        """Deploy satellite phone to restore communication in a zone."""
        zone_id = params.get("zone_id", "")

        zone = self._find_zone(zone_id)
        if zone:
            zone["has_communication"] = True
            zone["last_contact_hours_ago"] = 0
            self.graph.update_node_data(zone_id, has_communication=True, last_contact_hours_ago=0)
            return {"efficient_action": True}

        return {"wasted_time": True}

    def _action_advance_hour(self, params: dict) -> dict:
        """Advance simulation by 1 hour. Moves teams, updates state."""
        self.current_hour += 1

        # Update phase
        old_phase = self.current_phase
        if self.current_hour < 24:
            self.current_phase = "rescue"
        elif self.current_hour < 48:
            self.current_phase = "relief"
        else:
            self.current_phase = "rehabilitation"

        phase_completed = old_phase != self.current_phase

        # Move teams closer to destination
        teams_arrived = 0
        for team in self.teams:
            if team["status"] == "moving" and team["eta_hours"] > 0:
                team["eta_hours"] = max(0, team["eta_hours"] - 1.0)
                if team["eta_hours"] <= 0:
                    # Team arrived
                    team["status"] = "operating"
                    team["current_zone"] = team["destination"] or team["current_zone"]
                    teams_arrived += 1

                    # Auto-rescue on arrival
                    zone = self._find_zone(team["current_zone"])
                    if zone and team["team_type"] in ("rescue", "medical"):
                        can_rescue = min(zone.get("population", 0) - zone.get("rescued", 0), 20)
                        if can_rescue > 0:
                            zone["rescued"] = zone.get("rescued", 0) + can_rescue
                            self.total_rescued += can_rescue
                            self.graph.update_node_data(team["current_zone"], rescued=zone["rescued"])

        # Increase distress in zones with waiting people
        for zone in self.zones:
            remaining = zone.get("population", 0) - zone.get("rescued", 0)
            if remaining > 0:
                zone["distress_level"] = min(1.0, zone.get("distress_level", 0) + 0.02)
                # Critical patients may die if not helped
                if zone.get("injured_critical", 0) > 0 and zone.get("distress_level", 0) > 0.5:
                    deaths = min(zone["injured_critical"], random.randint(0, 2))
                    if deaths > 0:
                        zone["injured_critical"] -= deaths
                        zone["dead"] = zone.get("dead", 0) + deaths
                        self.total_deaths += deaths

            # Dark zones: increase hours since contact
            if not zone.get("has_communication", True):
                zone["last_contact_hours_ago"] = zone.get("last_contact_hours_ago", 0) + 1

        # Update hospital capacities
        for h in self.hospitals:
            h["capacity_pct"] = round(h.get("current_patients", 0) / max(h.get("capacity", 1), 1) * 100, 1)

        rescued_this_step = sum(1 for t in self.teams if t["status"] == "operating") * 5

        return {
            "phase_completed": phase_completed,
            "rescued_count": max(teams_arrived * 10, 0),
            "efficient_action": True,
            "equity_score": self._calculate_equity(),
        }

    # ==================== DYNAMIC EVENTS ====================

    def _check_dynamic_events(self) -> Optional[str]:
        """Check for scheduled and random dynamic events."""
        event_schedule = self.task_config.get("event_schedule", [])
        event_text = None

        # Check scheduled events
        for event in event_schedule:
            if event.get("hour") == self.current_hour:
                event_text = self._apply_scheduled_event(event)

        # Check random events
        chance = self.task_config.get("random_event_chance", 0)
        if random.random() < chance:
            rand_event = generate_random_event(self._get_state_for_agents())
            if rand_event:
                event_text = self._apply_random_event(rand_event)

        if event_text:
            self.dynamic_events_log.append(f"HOUR {self.current_hour}: {event_text}")

        return event_text

    def _apply_scheduled_event(self, event: dict) -> str:
        """Apply a scheduled event from task config."""
        etype = event.get("type", "")
        desc = event.get("description", "Unknown event")

        if etype == "aftershock":
            for road_id in event.get("roads_blocked", []):
                self.graph.block_road(road_id)
            hosp_id = event.get("hospital_damaged")
            if hosp_id:
                self.graph.damage_hospital(hosp_id)
                for h in self.hospitals:
                    if h["hospital_id"] == hosp_id:
                        h["is_damaged"] = True
                        h["has_power"] = False
            # Add casualties
            if self.zones:
                z = self.zones[0]
                z["injured_critical"] = z.get("injured_critical", 0) + 50
                z["population"] = z.get("population", 0) + 50

        elif etype == "road_floods":
            road_id = event.get("road_id", "")
            self.graph.flood_road(road_id)

        elif etype == "hospital_overflow":
            hosp_id = event.get("hospital_id", "")
            for h in self.hospitals:
                if h["hospital_id"] == hosp_id:
                    h["current_patients"] = h["capacity"]
                    h["capacity_pct"] = 100.0

        elif etype == "comms_down":
            for zone_id in event.get("zones", []):
                zone = self._find_zone(zone_id)
                if zone:
                    zone["has_communication"] = False
                    zone["last_contact_hours_ago"] = 0
                    self.graph.update_node_data(zone_id, has_communication=False)

        elif etype == "road_clears":
            road_id = event.get("road_id", "")
            self.graph.clear_road(road_id)

        elif etype == "new_survivors":
            zone_id = event.get("zone_id", "")
            extra = event.get("extra_population", 30)
            zone = self._find_zone(zone_id)
            if zone:
                zone["population"] = zone.get("population", 0) + extra
                zone["injured_critical"] = zone.get("injured_critical", 0) + int(extra * 0.2)

        elif etype == "supply_delay":
            pass  # just informational for now

        elif etype == "volunteer_arrival":
            extra = event.get("extra_teams", 2)
            for i in range(extra):
                self.teams.append({
                    "team_id": f"Volunteer-{len(self.teams)+1}",
                    "team_type": "supply", "transport": "foot",
                    "current_zone": "BASE", "destination": None,
                    "status": "idle", "eta_hours": 0.0, "assigned_task": None,
                })

        elif etype == "ndrf_reinforcement":
            for i in range(2):
                self.teams.append({
                    "team_id": f"NDRF-Reinforcement-{len(self.teams)+1}",
                    "team_type": "rescue", "transport": "truck",
                    "current_zone": "BASE", "destination": None,
                    "status": "idle", "eta_hours": 0.0, "assigned_task": None,
                })
            self.resources["fuel_helicopter"] = self.resources.get("fuel_helicopter", 0) + 5
            self.resources["helicopters_available"] = self.resources.get("helicopters_available", 0) + 1

        elif etype == "phase_transition":
            new_phase = event.get("new_phase", self.current_phase)
            self.current_phase = new_phase

        return desc

    def _apply_random_event(self, event: dict) -> str:
        """Apply a random event."""
        etype = event.get("type", "")
        desc = event.get("description", "Random event occurred")

        if etype == "road_floods":
            self.graph.flood_road(event.get("road_id", ""))
        elif etype == "road_clears":
            self.graph.clear_road(event.get("road_id", ""))
        elif etype == "comms_down":
            zone = self._find_zone(event.get("zone_id", ""))
            if zone:
                zone["has_communication"] = False
        elif etype == "new_survivors":
            zone = self._find_zone(event.get("zone_id", ""))
            if zone:
                extra = event.get("count", 20)
                zone["population"] += extra
        elif etype == "hospital_overflow":
            for h in self.hospitals:
                if h["hospital_id"] == event.get("hospital_id", ""):
                    h["current_patients"] = h["capacity"]
                    h["capacity_pct"] = 100.0

        return desc

    # ==================== HELPERS ====================

    def _find_zone(self, zone_id: str) -> Optional[dict]:
        for z in self.zones:
            if z.get("zone_id") == zone_id or z.get("id") == zone_id:
                return z
        return None

    def _calculate_equity(self) -> float:
        """Calculate equity score — how evenly resources are distributed."""
        rates = []
        for z in self.zones:
            pop = z.get("population", 0)
            if pop > 0:
                rates.append(z.get("rescued", 0) / pop)
        if not rates or max(rates) == 0:
            return 0.5
        return round(min(rates) / max(max(rates), 0.01), 3)

    def _tick_time_effects(self):
        """Apply time-based effects each step."""
        # Teams that are "operating" auto-return after some time
        for team in self.teams:
            if team["status"] == "operating":
                # After operating, team goes back to idle at current zone
                team["status"] = "idle"
                team["assigned_task"] = None

    def _check_done(self) -> bool:
        """Check if episode is over."""
        if self.step_number >= self.max_steps:
            return True
        if self.current_hour >= self.max_hours:
            return True
        # All people rescued
        total_pop = sum(z.get("population", 0) for z in self.zones)
        if total_pop > 0 and self.total_rescued >= total_pop:
            return True
        return False

    def _get_state_for_agents(self) -> dict:
        """Build state dict that agents use in assess()."""
        return {
            "zones": self.zones,
            "hospitals": self.hospitals,
            "teams": [t for t in self.teams],
            "resources": self.resources,
            "roads": [{"road_id": e.get("id", e.get("road_id", "")), "status": e.get("status", "open")}
                      for _, _, e in self.graph.G.edges(data=True)],
            "current_hour": self.current_hour,
            "current_phase": self.current_phase,
            "total_rescued": self.total_rescued,
            "total_deaths": self.total_deaths,
            "action_history": self.action_history,
            "agent_reports": {},
        }

    def _get_state_for_reward(self) -> dict:
        """Build state dict for reward calculation."""
        state = self._get_state_for_agents()
        state["grading_config"] = self.task_config.get("grading_config", {})
        state["max_hours"] = self.max_hours
        return state

    def _build_observation_dict(self) -> dict:
        """Build observation dict for API response."""
        # Get agent reports
        agent_reports = {}
        state_for_agents = self._get_state_for_agents()
        for name, agent in self.agents.items():
            try:
                report = agent.assess(state_for_agents)
                agent_reports[name] = report.model_dump() if hasattr(report, 'model_dump') else report.dict() if hasattr(report, 'dict') else {}
            except Exception:
                agent_reports[name] = {"agent_name": name, "status": "idle", "current_action": "standby"}

        return {
            "zones": self.zones,
            "hospitals": self.hospitals,
            "roads": [{"road_id": e.get("id", e.get("road_id", "")), "from_zone": u, "to_zone": v,
                        "status": e.get("status", "open"), "travel_time_hours": e.get("travel_time", 1.0)}
                       for u, v, e in self.graph.G.edges(data=True)],
            "resources": self.resources,
            "teams": self.teams,
            "agent_reports": agent_reports,
            "current_hour": self.current_hour,
            "current_phase": self.current_phase,
            "dynamic_events": self.pending_events,
            "step_number": self.step_number,
            "task_id": self.task_id,
            "total_rescued": self.total_rescued,
            "total_deaths": self.total_deaths,
        }

    # ==================== DASHBOARD HELPERS ====================

    def get_graph_data(self) -> dict:
        """Get graph data for SVG crisis map on dashboard."""
        return self.graph.to_dashboard_data(teams=self.teams)

    def get_agent_data(self) -> dict:
        """Get all agent reports for dashboard."""
        state = self._get_state_for_agents()
        result = {}
        for name, agent in self.agents.items():
            try:
                report = agent.assess(state)
                d = report.model_dump() if hasattr(report, 'model_dump') else report.dict() if hasattr(report, 'dict') else {}
                result[name] = d
            except Exception:
                result[name] = {"agent_name": name, "status": "idle", "current_action": "standby"}
        return result

    def get_curriculum_data(self) -> dict:
        """Get self-improvement data for dashboard."""
        return self.curriculum.get_dashboard_data()

    def get_metrics(self) -> dict:
        """Get aggregate metrics for dashboard."""
        total_pop = sum(z.get("population", 0) for z in self.zones)
        return {
            "total_population": total_pop,
            "total_rescued": self.total_rescued,
            "total_deaths": self.total_deaths,
            "rescue_pct": round(self.total_rescued / max(total_pop, 1) * 100, 1),
            "current_hour": self.current_hour,
            "current_phase": self.current_phase,
            "step_number": self.step_number,
            "episode_number": self.episode_number,
            "total_reward": round(self.reward_calc.total_reward_this_episode, 4),
            "resource_history": {
                "fuel_pct": round(self.resources.get("fuel_helicopter", 0) / max(self.resources.get("max_fuel", 1), 1) * 100),
                "water_pct": round(self.resources.get("water_units", 0) / max(self.resources.get("max_water", 1), 1) * 100),
                "food_pct": round(self.resources.get("food_units", 0) / max(self.resources.get("max_food", 1), 1) * 100),
                "medicine_pct": round(self.resources.get("medicine_units", 0) / max(self.resources.get("max_medicine", 1), 1) * 100),
            },
            "teams_active": sum(1 for t in self.teams if t["status"] != "idle"),
            "teams_total": len(self.teams),
            "dynamic_events_count": len(self.dynamic_events_log),
        }
