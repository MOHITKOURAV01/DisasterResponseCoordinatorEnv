from typing import Dict, List, Optional
import random

class CurriculumEngine:
    """
    Real self-improvement: analyzes WHY episodes failed 
    and generates harder scenarios targeting those weaknesses.
    """
    def __init__(self):
        self.episode_history = []
        self.failure_patterns = {}
        self.strategy_memory = []
        self.generation = 0
        self.difficulty = 3.0 # keep difficulty tracking for backward compatibility
    
    def record_episode(self, episode_data: dict):
        """Called after every episode completes."""
        self.episode_history.append(episode_data)
        self._analyze_failure(episode_data)
        if len(self.episode_history) % 3 == 0:
            self._extract_strategy()
    
    def _analyze_failure(self, ep: dict):
        """Identify what caused low score."""
        score = ep.get("grader_score", 0)
        if score >= 0.7:
            return  # Success — no failure to analyze
        
        obs = ep.get("final_obs", {})
        
        # Pattern 1: Communication failures
        dark_zones = sum(1 for z in obs.get("zones",[]) 
                        if not z.get("has_communication", True))
        if dark_zones > 2:
            self.failure_patterns["comms_blackout"] = \
                self.failure_patterns.get("comms_blackout", 0) + 1
        
        # Pattern 2: Resource exhaustion
        fuel = obs.get("resources", {}).get("fuel_helicopter", 5)
        if fuel <= 0:
            self.failure_patterns["fuel_exhaustion"] = \
                self.failure_patterns.get("fuel_exhaustion", 0) + 1
        
        # Pattern 3: Road blockage
        steps = ep.get("action_history", [])
        blocked_hits = sum(1 for s in steps 
                          if s.get("reward", 0) < -0.05)
        if blocked_hits > 3:
            self.failure_patterns["road_blocks"] = \
                self.failure_patterns.get("road_blocks", 0) + 1
        
        # Pattern 4: Late evacuation
        deaths = obs.get("total_deaths", 0)
        if deaths > 5:
            self.failure_patterns["late_evacuation"] = \
                self.failure_patterns.get("late_evacuation", 0) + 1
    
    def _extract_strategy(self):
        """Convert failure patterns into learned strategies."""
        if self.failure_patterns.get("comms_blackout", 0) >= 2:
            rule = "Always setup_comms in dark zones before dispatching teams"
            if not any(s["rule"] == rule for s in self.strategy_memory):
                self.strategy_memory.append({"rule": rule, 
                                             "confidence": 0.85})
        
        if self.failure_patterns.get("fuel_exhaustion", 0) >= 2:
            rule = "Reserve minimum 2 helicopter fuel for critical extractions"
            if not any(s["rule"] == rule for s in self.strategy_memory):
                self.strategy_memory.append({"rule": rule,
                                             "confidence": 0.90})
        
        if self.failure_patterns.get("road_blocks", 0) >= 2:
            rule = "Use boats for flooded zones, re_route before dispatching"
            if not any(s["rule"] == rule for s in self.strategy_memory):
                self.strategy_memory.append({"rule": rule,
                                             "confidence": 0.80})
        
        if self.failure_patterns.get("late_evacuation", 0) >= 2:
            rule = "Prioritize evacuation of critical patients in first 6 hours"
            if not any(s["rule"] == rule for s in self.strategy_memory):
                self.strategy_memory.append({"rule": rule,
                                             "confidence": 0.88})
    
    def generate_next_scenario(self, base_task: str) -> dict:
        """
        Generate harder scenario targeting agent's weaknesses.
        This is the actual self-improvement — not random difficulty.
        """
        self.generation += 1
        overrides = {}
        
        # Target the most frequent failure pattern
        if self.failure_patterns:
            worst = max(self.failure_patterns, 
                       key=self.failure_patterns.get)
            
            if worst == "comms_blackout":
                # Force more dark zones in next scenario
                overrides["extra_dark_zones"] = min(
                    self.failure_patterns["comms_blackout"], 4)
            
            elif worst == "fuel_exhaustion":
                # Reduce starting fuel
                overrides["fuel_penalty"] = 0.6  # 40% less fuel
            
            elif worst == "road_blocks":
                # More flooded roads
                overrides["flood_severity"] = min(
                    1.0, 0.4 + self.failure_patterns["road_blocks"]*0.1)
            
            elif worst == "late_evacuation":
                # More critical patients, faster deterioration
                overrides["critical_multiplier"] = 1.5
        
        return {
            "base_task": base_task,
            "generation": self.generation,
            "targeting_weakness": max(self.failure_patterns, 
                                     key=self.failure_patterns.get) 
                                  if self.failure_patterns else "none",
            "overrides": overrides,
            "strategy_count": len(self.strategy_memory)
        }
    
    def generate_harder_scenario(self, base_task_config: dict) -> dict:
        """Compatibility method for env.py."""
        import copy
        config = copy.deepcopy(base_task_config)
        self.generation += 1
        
        # Target the most frequent failure pattern
        if self.failure_patterns:
            worst = max(self.failure_patterns, key=self.failure_patterns.get)
            if worst == "comms_blackout":
                for node in config.get("nodes", []):
                    if node.get("type") == "village" and random.random() < 0.4:
                        node["has_communication"] = False
            elif worst == "fuel_exhaustion":
                if "initial_resources" in config:
                    config["initial_resources"]["fuel_helicopter"] = max(1.0, config["initial_resources"].get("fuel_helicopter", 5) * 0.6)
            elif worst == "road_blocks":
                for edge in config.get("edges", []):
                    if random.random() < 0.3:
                        edge["status"] = "flooded"
            elif worst == "late_evacuation":
                for node in config.get("nodes", []):
                    if node.get("type") == "village":
                        node["injured_critical"] = int(node.get("injured_critical", 0) * 1.5)
        
        return config

    def get_status(self) -> dict:
        return {
            "generation": self.generation,
            "episodes_analyzed": len(self.episode_history),
            "failure_patterns": self.failure_patterns,
            "strategy_memory": self.strategy_memory[-5:],
            "next_scenario_targets": max(
                self.failure_patterns, 
                key=self.failure_patterns.get
            ) if self.failure_patterns else "exploring"
        }
    
    def get_dashboard_data(self) -> dict:
        """Compatibility method for env.py."""
        status = self.get_status()
        status["difficulty"] = self.difficulty
        status["current_weakness"] = status["next_scenario_targets"]
        return status

# Singleton instance
curriculum_engine = CurriculumEngine()
