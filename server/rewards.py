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
        """
        Deterministic grader. Score based on:
        - rescue_rate: % people rescued (0-0.6 weight)
        - efficiency: reward per step (0-0.2 weight)  
        - phase_completion: did agent complete all 3 phases (0-0.1 weight)
        - no_deaths: bonus for zero deaths (0.1 weight)
        """
        try:
            total_pop = state.get("total_population", 0)
            total_rescued = state.get("total_rescued", 0)
            total_steps = max(state.get("current_hour", 1), 1)
            deaths = state.get("total_deaths", 0)
            current_phase = state.get("current_phase", "rescue")
            total_reward = self.total_reward_this_episode
            
            if total_pop <= 0:
                return 0.001
            
            # 1. Rescue rate (60% weight)
            rescue_rate = min(total_rescued / total_pop, 1.0)
            rescue_score = rescue_rate * 0.60
            
            # 2. Efficiency (20% weight)
            reward_per_step = total_reward / total_steps
            efficiency = min(max(reward_per_step / 0.5, 0), 1.0)
            efficiency_score = efficiency * 0.20
            
            # 3. Phase progression (10% weight)
            phase_scores = {"rescue": 0.33, "relief": 0.66, "rehabilitation": 1.0}
            phase_score = phase_scores.get(current_phase, 0.33) * 0.10
            
            # 4. Death penalty (10% weight)
            death_rate = deaths / max(total_pop, 1)
            death_score = max(0, 1.0 - death_rate * 2) * 0.10
            
            raw_score = rescue_score + efficiency_score + phase_score + death_score
            
            # Clamp to strictly open interval (0.001, 0.999)
            return max(0.001, min(raw_score, 0.999))
            
        except Exception:
            return 0.001

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
