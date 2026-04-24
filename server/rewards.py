from typing import Dict, List, Optional


class RewardCalculator:
    """Multi-signal reward function with 12 distinct signals.
    Positive rewards for good actions, negative penalties for bad actions.
    Includes self-adaptive component that evolves based on agent history.
    """

    def __init__(self):
        self.action_success_history: Dict[str, List[bool]] = {}
        self.total_reward_this_episode: float = 0.0
        self.step_rewards: List[float] = []

    def reset(self):
        """Reset for new episode. Keep action_success_history for self-adaptive rewards."""
        self.total_reward_this_episode = 0.0
        self.step_rewards = []

    def calculate(self, action: dict, result: dict, state: dict) -> float:
        """Calculate reward for a single step.

        Args:
            action: {tool_name, parameters} — what coordinator chose
            result: {rescued, triaged, rerouted, discovered, blocked_road_hit,
                     resource_exhausted, zone_ignored, repeated_action,
                     wasted_time, overloaded_hospital, phase_bonus, efficient}
            state: current environment state dict

        Returns: float reward clamped to [-0.5, 1.0]
        """
        reward = 0.0
        tool = action.get("tool_name", "")
        details = {}

        # ===== POSITIVE REWARDS =====

        # 1. Person rescued alive (+0.12 per batch)
        rescued = result.get("rescued_count", 0)
        if rescued > 0:
            r = min(rescued * 0.02, 0.12)  # cap at 0.12 per step
            reward += r
            details["rescued"] = r

        # 2. Critical patient correctly triaged (+0.10)
        triaged = result.get("triaged_critical", 0)
        if triaged > 0:
            r = min(triaged * 0.025, 0.10)
            reward += r
            details["triaged"] = r

        # 3. Successful re-route after road block (+0.07)
        if result.get("rerouted", False):
            reward += 0.07
            details["rerouted"] = 0.07

        # 4. New survivors discovered and responded (+0.09)
        discovered = result.get("discovered_count", 0)
        if discovered > 0:
            reward += 0.09
            details["discovered"] = 0.09

        # 5. Equitable resource distribution (+0.05)
        equity = result.get("equity_score", 0.0)
        if equity > 0.6:
            r = equity * 0.05
            reward += r
            details["equity"] = round(r, 4)

        # 6. Phase transition bonus (+0.06)
        if result.get("phase_completed", False):
            reward += 0.06
            details["phase_bonus"] = 0.06

        # 7. Efficient resource usage (+0.04)
        if result.get("efficient_action", False):
            reward += 0.04
            details["efficient"] = 0.04

        # 8. Correct transport for terrain (+0.03)
        if result.get("correct_transport", False):
            reward += 0.03
            details["correct_transport"] = 0.03

        # ===== NEGATIVE PENALTIES =====

        # 9. Team sent to blocked road (-0.08)
        if result.get("blocked_road_hit", False):
            reward -= 0.08
            details["blocked_penalty"] = -0.08

        # 10. Resource exhausted prematurely (-0.12)
        if result.get("resource_exhausted", False):
            reward -= 0.12
            details["exhausted_penalty"] = -0.12

        # 11. Zone completely ignored (-0.15) — HIGHEST penalty
        ignored = result.get("zones_ignored_count", 0)
        if ignored > 0:
            r = min(ignored * 0.05, 0.15)
            reward -= r
            details["ignored_penalty"] = round(-r, 4)

        # 12. Repeated/invalid action (-0.05)
        if result.get("repeated_action", False) or result.get("invalid_action", False):
            reward -= 0.05
            details["repeated_penalty"] = -0.05

        # 13. Time wasted — no useful action (-0.03)
        if result.get("wasted_time", False):
            reward -= 0.03
            details["wasted_penalty"] = -0.03

        # 14. Hospital overloaded (-0.07)
        if result.get("hospital_overloaded", False):
            reward -= 0.07
            details["overload_penalty"] = -0.07

        # ===== SELF-ADAPTIVE COMPONENT (ICLR 2025 inspired) =====
        # Track action type success rates and give bonus for historically good actions
        if tool:
            if tool not in self.action_success_history:
                self.action_success_history[tool] = []
            was_positive = reward > 0
            self.action_success_history[tool].append(was_positive)

            # If this action type has >70% historical success, give small bonus
            history = self.action_success_history[tool]
            if len(history) >= 3:
                success_rate = sum(history[-10:]) / len(history[-10:])
                if success_rate > 0.7:
                    adaptive_bonus = 0.02
                    reward += adaptive_bonus
                    details["adaptive_bonus"] = adaptive_bonus

        # Clamp reward
        reward = max(-0.5, min(1.0, reward))
        reward = round(reward, 4)

        self.total_reward_this_episode += reward
        self.step_rewards.append(reward)

        return reward

    def grade_episode(self, state: dict) -> float:
        """Final grader score for the episode. Returns 0.001 to 0.999.

        Composite of: rescue rate, equity, time efficiency, resource conservation,
        communication recovery, and protocol compliance.
        """
        zones = state.get("zones", [])
        total_pop = max(sum(z.get("population", 0) for z in zones), 1)
        total_rescued = state.get("total_rescued", 0)
        total_deaths = state.get("total_deaths", 0)
        current_hour = state.get("current_hour", 0)
        max_hours = state.get("max_hours", 72)

        # Component 1: Rescue rate (biggest weight)
        rescue_rate = total_rescued / total_pop

        # Component 2: Death avoidance
        death_rate = total_deaths / total_pop
        death_score = max(0, 1.0 - death_rate * 5)  # heavy penalty for deaths

        # Component 3: Time efficiency (faster = better)
        time_score = max(0, 1.0 - (current_hour / max(max_hours, 1)) * 0.5)

        # Component 4: Equity — did all zones get help?
        zone_rescue_rates = []
        for z in zones:
            pop = z.get("population", 0)
            if pop > 0:
                zone_rescue_rates.append(z.get("rescued", 0) / pop)
        if zone_rescue_rates:
            min_rate = min(zone_rescue_rates)
            max_rate = max(zone_rescue_rates)
            equity_score = min_rate / max(max_rate, 0.01) if max_rate > 0 else 1.0
        else:
            equity_score = 0.5

        # Component 5: Resource conservation
        resources = state.get("resources", {})
        max_fuel = max(resources.get("max_fuel", 1), 1)
        fuel_remaining = resources.get("fuel_helicopter", 0) / max_fuel
        resource_score = min(fuel_remaining * 2, 1.0)  # bonus for not wasting

        # Component 6: Communication recovery
        dark_zones = [z for z in zones if not z.get("has_communication", True)]
        comm_score = 1.0 - (len(dark_zones) / max(len(zones), 1))

        # Get grading weights from task config
        weights = state.get("grading_config", {})
        rescue_w = weights.get("rescue_weight", 0.40)
        time_w = weights.get("time_weight", 0.15)
        resource_w = weights.get("resource_efficiency_weight", 0.10)
        equity_w = weights.get("equity_weight", 0.15)

        # Weighted composite
        score = (
            rescue_rate * rescue_w
            + death_score * 0.10
            + time_score * time_w
            + equity_score * equity_w
            + resource_score * resource_w
            + comm_score * 0.05
            + min(self.total_reward_this_episode / max(len(self.step_rewards), 1), 0.3) * 0.05
        )

        # Clamp to open interval (0, 1) — OpenEnv requirement
        score = max(0.001, min(0.999, round(score, 4)))
        return score

    def get_stats(self) -> dict:
        """Return reward statistics for dashboard."""
        return {
            "total_reward": round(self.total_reward_this_episode, 4),
            "steps": len(self.step_rewards),
            "avg_reward": round(self.total_reward_this_episode / max(len(self.step_rewards), 1), 4),
            "positive_steps": sum(1 for r in self.step_rewards if r > 0),
            "negative_steps": sum(1 for r in self.step_rewards if r < 0),
            "action_success_rates": {
                tool: round(sum(h[-10:]) / max(len(h[-10:]), 1), 2)
                for tool, h in self.action_success_history.items()
            },
        }
