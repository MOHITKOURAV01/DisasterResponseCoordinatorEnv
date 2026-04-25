"""
Basic environment tests. Run with: pytest tests/
"""
import httpx
import pytest
import time

ENV_URL = "https://mohitkourav-disasterresponsecoordinatorenv.hf.space"
TIMEOUT = 30

class TestEnvironmentAPI:
    """Tests for DisasterResponseCoordinatorEnv API compliance."""
    
    def test_health_returns_ok(self):
        resp = httpx.get(f"{ENV_URL}/health", timeout=TIMEOUT)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "tasks" in data
    
    def test_reset_with_task_id(self):
        resp = httpx.post(
            f"{ENV_URL}/reset",
            json={"task_id": "village_flood_rescue"},
            timeout=TIMEOUT
        )
        assert resp.status_code == 200
        obs = resp.json()
        assert "zones" in obs or "observation" in obs
    
    def test_reset_empty_body(self):
        """Validator sends empty body — must work."""
        resp = httpx.post(f"{ENV_URL}/reset", timeout=TIMEOUT)
        assert resp.status_code == 200
    
    def test_step_valid_action(self):
        httpx.post(f"{ENV_URL}/reset",
                   json={"task_id": "village_flood_rescue"},
                   timeout=TIMEOUT)
        resp = httpx.post(
            f"{ENV_URL}/step",
            json={"tool_name": "advance_hour", "parameters": {}},
            timeout=TIMEOUT
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "reward" in data
        assert "done" in data
        assert isinstance(data["reward"], (int, float))
        assert isinstance(data["done"], bool)
    
    def test_state_returns_data(self):
        resp = httpx.get(f"{ENV_URL}/state", timeout=TIMEOUT)
        assert resp.status_code == 200
        data = resp.json()
        assert "current_hour" in data or "observation" in data
    
    def test_reward_in_valid_range(self):
        httpx.post(f"{ENV_URL}/reset",
                   json={"task_id": "village_flood_rescue"},
                   timeout=TIMEOUT)
        resp = httpx.post(
            f"{ENV_URL}/step",
            json={"tool_name": "dispatch_team",
                  "parameters": {"zone_id": "Z1",
                                 "team_type": "rescue",
                                 "transport": "truck"}},
            timeout=TIMEOUT
        )
        data = resp.json()
        reward = float(data["reward"])
        assert -0.5 <= reward <= 1.0, f"Reward {reward} out of range"
    
    def test_all_4_tasks_work(self):
        tasks = ["village_flood_rescue", "multi_district_cyclone",
                 "earthquake_aftershock", "full_72hr_operation"]
        for task_id in tasks:
            resp = httpx.post(
                f"{ENV_URL}/reset",
                json={"task_id": task_id},
                timeout=TIMEOUT
            )
            assert resp.status_code == 200, f"Task {task_id} failed"
    
    def test_grader_score_in_range(self):
        httpx.post(f"{ENV_URL}/reset",
                   json={"task_id": "village_flood_rescue"},
                   timeout=TIMEOUT)
        for _ in range(5):
            httpx.post(f"{ENV_URL}/step",
                       json={"tool_name": "advance_hour",
                             "parameters": {}},
                       timeout=TIMEOUT)
        state = httpx.get(f"{ENV_URL}/state", timeout=TIMEOUT).json()
        score = state.get("grader_score", 0.5)
        assert 0.0 < score < 1.0, f"Grader score {score} not in (0,1)"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
