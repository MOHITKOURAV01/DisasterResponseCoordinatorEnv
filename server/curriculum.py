from typing import Dict, List, Optional
import random


class CurriculumEngine:
    """Self-improvement engine with 3 mechanisms:
    A) Adaptive curriculum — auto-generates harder scenarios from failure analysis
    B) Strategy memory — stores successful patterns for future episodes
    C) Difficulty scaling — increases difficulty based on performance

    Implements Theme 4: Self-Improvement for the hackathon.
    """

    def __init__(self):
        self.episode_history: List[dict] = []
        self.strategy_memory: List[dict] = []
        self.difficulty: float = 3.0  # starts at 3/10
        self.current_weakness: str = "none"
        self.failure_counts: Dict[str, int] = {}
        self.zone_type_performance: Dict[str, List[float]] = {}

    def reset_episode(self):
        """Called at start of new episode. Does NOT reset history/strategies."""
        pass

    def analyze_episode(self, state: dict) -> dict:
        """Post-episode analysis. Identifies what went wrong and where.

        Returns: {failures: {zone_id: {type, rescue_rate, reason}},
                  overall_score: float, weakness: str}
        """
        zones = state.get("zones", [])
        failures = {}
        zone_scores = {}

        for zone in zones:
            zone_id = zone.get("zone_id", zone.get("id", ""))
            pop = zone.get("population", 0)
            if pop <= 0:
                continue

            rescued = zone.get("rescued", 0)
            rescue_rate = rescued / pop
            zone_type = zone.get("zone_type", zone.get("status", "unknown"))
            zone_scores[zone_id] = rescue_rate

            # Track per zone-type performance
            if zone_type not in self.zone_type_performance:
                self.zone_type_performance[zone_type] = []
            self.zone_type_performance[zone_type].append(rescue_rate)

            if rescue_rate < 0.5:
                reason = self._diagnose_failure(zone, state)
                failures[zone_id] = {
                    "zone_type": zone_type,
                    "rescue_rate": round(rescue_rate, 2),
                    "reason": reason,
                    "population": pop,
                    "rescued": rescued,
                }
                # Count failure types
                if reason not in self.failure_counts:
                    self.failure_counts[reason] = 0
                self.failure_counts[reason] += 1

        # Find weakest zone type
        weakness = "none"
        worst_rate = 1.0
        for ztype, rates in self.zone_type_performance.items():
            avg = sum(rates[-5:]) / max(len(rates[-5:]), 1)
            if avg < worst_rate:
                worst_rate = avg
                weakness = ztype
        self.current_weakness = weakness

        overall = sum(zone_scores.values()) / max(len(zone_scores), 1)

        episode_record = {
            "episode": len(self.episode_history) + 1,
            "score": round(overall, 3),
            "failures": failures,
            "weakness": weakness,
            "difficulty": self.difficulty,
        }
        self.episode_history.append(episode_record)

        return episode_record

    def _diagnose_failure(self, zone: dict, state: dict) -> str:
        """Determine WHY a zone had low rescue rate."""
        if not zone.get("has_communication", True):
            return "communication_failure"

        zone_status = zone.get("status", "safe")
        if zone_status == "flooded":
            return "flood_access"
        elif zone_status == "destroyed":
            return "structural_damage"
        elif zone_status == "damaged":
            return "road_damage"

        if zone.get("injured_critical", 0) > 20:
            return "medical_overwhelm"

        return "resource_shortage"

    def generate_harder_scenario(self, base_task_config: dict) -> dict:
        """Auto-generate a harder version of the task targeting agent's weaknesses.
        Modifies the base task config to increase difficulty in weak areas.

        Returns: modified task config dict
        """
        import copy
        config = copy.deepcopy(base_task_config)

        # Increase difficulty
        self.difficulty = min(10.0, self.difficulty + 0.5)

        # If weakness is flood_access, add more flooded roads
        if self.current_weakness in ("flooded", "flood_access"):
            for edge in config.get("edges", []):
                if edge.get("status") == "open" and random.random() < 0.3:
                    edge["status"] = "flooded"

        # If weakness is communication_failure, add more dark zones
        elif self.current_weakness in ("communication_failure",):
            for node in config.get("nodes", []):
                if node.get("has_communication", True) and node.get("type") == "village":
                    if random.random() < 0.3:
                        node["has_communication"] = False
                        node["last_contact_hours_ago"] = random.randint(3, 12)

        # If weakness is medical_overwhelm, increase critical patients
        elif self.current_weakness in ("medical_overwhelm",):
            for node in config.get("nodes", []):
                if node.get("type") == "village":
                    node["injured_critical"] = int(node.get("injured_critical", 0) * 1.5)

        # If weakness is road_damage, block more roads
        elif self.current_weakness in ("damaged", "road_damage"):
            for edge in config.get("edges", []):
                if edge.get("status") == "open" and random.random() < 0.25:
                    edge["status"] = "blocked"

        # General difficulty: increase population
        if self.difficulty > 5:
            for node in config.get("nodes", []):
                if node.get("type") == "village":
                    node["population"] = int(node.get("population", 0) * 1.2)
                    node["injured_critical"] = int(node.get("injured_critical", 0) * 1.1)

        # Add more random events at higher difficulty
        config["random_event_chance"] = min(0.15, config.get("random_event_chance", 0) + 0.02)

        return config

    def extract_strategies(self, state: dict) -> List[dict]:
        """Learn from successful episodes. Extract what WORKED as reusable rules.
        Only extracts from episodes with score > 0.5.

        Returns: list of new strategies added
        """
        if not self.episode_history:
            return []

        latest = self.episode_history[-1]
        if latest["score"] < 0.5:
            return []

        new_strategies = []
        action_history = state.get("action_history", [])

        # Analyze action patterns from successful episode
        tool_counts = {}
        tool_rewards = {}
        for entry in action_history:
            tool = entry.get("tool_name", "")
            reward = entry.get("reward", 0)
            if tool not in tool_counts:
                tool_counts[tool] = 0
                tool_rewards[tool] = []
            tool_counts[tool] += 1
            tool_rewards[tool].append(reward)

        # Strategy: tools with consistently positive rewards
        for tool, rewards in tool_rewards.items():
            if len(rewards) >= 2:
                avg_reward = sum(rewards) / len(rewards)
                success_rate = sum(1 for r in rewards if r > 0) / len(rewards)

                if success_rate >= 0.7 and avg_reward > 0.03:
                    rule = self._generate_rule_description(tool, success_rate, state)

                    # Check if we already have this strategy
                    existing_rules = [s["rule"] for s in self.strategy_memory]
                    if rule not in existing_rules:
                        strategy = {
                            "rule": rule,
                            "learned_after": latest["episode"],
                            "success_rate": round(success_rate, 2),
                            "avg_reward": round(avg_reward, 4),
                            "tool": tool,
                        }
                        self.strategy_memory.append(strategy)
                        new_strategies.append(strategy)

        # Keep only top 10 strategies by success rate
        self.strategy_memory.sort(key=lambda s: s["success_rate"], reverse=True)
        self.strategy_memory = self.strategy_memory[:10]

        return new_strategies

    def _generate_rule_description(self, tool: str, success_rate: float, state: dict) -> str:
        """Generate human-readable strategy description."""
        rules = {
            "dispatch_team": f"Dispatch rescue teams early to highest-population zones (success {success_rate:.0%})",
            "allocate_resource": f"Allocate resources proportional to zone population (success {success_rate:.0%})",
            "re_route": f"Immediately re-route teams when roads are blocked (success {success_rate:.0%})",
            "request_airlift": f"Use helicopter for rooftop rescues in flooded zones (success {success_rate:.0%})",
            "order_evacuation": f"Evacuate zones before hospital capacity fills up (success {success_rate:.0%})",
            "deploy_scout": f"Scout dark zones before sending rescue teams (success {success_rate:.0%})",
            "setup_comms": f"Restore communication in dark zones first for better intel (success {success_rate:.0%})",
            "advance_hour": f"Advance time only after all available actions are taken (success {success_rate:.0%})",
        }
        return rules.get(tool, f"Use {tool} strategically (success {success_rate:.0%})")

    def get_system_prompt_injection(self) -> str:
        """Generate text to inject into LLM system prompt with learned strategies.
        Used by inference.py to make agent smarter over episodes.
        """
        if not self.strategy_memory:
            return ""

        lines = ["Based on past experience, these strategies work well:"]
        for s in self.strategy_memory[:5]:
            lines.append(f"- {s['rule']}")

        if self.current_weakness != "none":
            lines.append(f"\nKnown weakness to work on: {self.current_weakness}")

        return "\n".join(lines)

    def get_dashboard_data(self) -> dict:
        """Return data for the self-improvement dashboard panel."""
        return {
            "difficulty": round(self.difficulty, 1),
            "current_weakness": self.current_weakness,
            "episode_history": self.episode_history[-25:],  # last 25 episodes
            "strategy_memory": self.strategy_memory,
            "failure_counts": self.failure_counts,
            "zone_type_performance": {
                k: round(sum(v[-5:]) / max(len(v[-5:]), 1), 2)
                for k, v in self.zone_type_performance.items()
            },
            "total_episodes": len(self.episode_history),
            "avg_score": round(
                sum(e["score"] for e in self.episode_history[-10:])
                / max(len(self.episode_history[-10:]), 1),
                3,
            ) if self.episode_history else 0,
        }
