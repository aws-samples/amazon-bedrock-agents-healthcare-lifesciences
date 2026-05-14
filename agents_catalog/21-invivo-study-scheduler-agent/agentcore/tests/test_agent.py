import json
import unittest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent.agent_config.agent import (
    optimize_schedule,
    _find_best_day,
    create_agent,
)

SAMPLE_STUDIES = [
    {"study_id": "Study_A", "animals_required": 150, "preferred_start_day": 5, "duration_days": 3, "priority": 4},
    {"study_id": "Study_B", "animals_required": 200, "preferred_start_day": 10, "duration_days": 2, "priority": 3},
    {"study_id": "Study_C", "animals_required": 100, "preferred_start_day": 8, "duration_days": 1, "priority": 5},
    {"study_id": "Study_D", "animals_required": 300, "preferred_start_day": 15, "duration_days": 4, "priority": 2},
    {"study_id": "Study_E", "animals_required": 175, "preferred_start_day": 20, "duration_days": 2, "priority": 3},
]


class TestOptimizeSchedule(unittest.TestCase):
    def test_successful_optimization(self):
        result = json.loads(optimize_schedule(studies=json.dumps(SAMPLE_STUDIES)))
        assert result["status"] == "success"
        assert len(result["schedule"]) == 5
        assert result["total_animals"] == 925

    def test_respects_max_animals_per_day(self):
        result = json.loads(optimize_schedule(studies=json.dumps(SAMPLE_STUDIES), max_animals_per_day=500))
        for day in result["daily_usage"]:
            assert day["animal_count"] <= 500

    def test_invalid_json_returns_error(self):
        result = json.loads(optimize_schedule(studies="not valid json"))
        assert result["status"] == "error"
        assert "Invalid JSON" in result["message"]

    def test_balance_studies_objective(self):
        result = json.loads(optimize_schedule(
            studies=json.dumps(SAMPLE_STUDIES), optimization_objective="balance_studies"
        ))
        assert result["status"] == "success"
        assert result["std_dev_studies"] >= 0

    def test_empty_studies_list(self):
        result = json.loads(optimize_schedule(studies="[]"))
        assert result["status"] == "success"
        assert len(result["schedule"]) == 0

    def test_preferred_start_day_respected_when_possible(self):
        studies = [{"study_id": "S1", "animals_required": 50, "preferred_start_day": 10, "duration_days": 1}]
        result = json.loads(optimize_schedule(studies=json.dumps(studies)))
        assert result["schedule"][0]["assigned_start_day"] == 10


class TestFindBestDay(unittest.TestCase):
    def test_uses_preferred_day_when_feasible(self):
        daily_animals = [0] * 30
        daily_studies = [0] * 30
        day = _find_best_day(daily_animals, daily_studies, 100, 1, 1000, 5, "balance_animals")
        assert day == 4  # 0-indexed

    def test_avoids_exceeding_capacity(self):
        daily_animals = [900] * 30
        daily_studies = [1] * 30
        daily_animals[15] = 0  # Only day 16 (0-indexed 15) has capacity
        day = _find_best_day(daily_animals, daily_studies, 200, 1, 1000, 1, "balance_animals")
        assert day == 15


class TestCreateAgent(unittest.TestCase):
    @patch("agent.agent_config.agent.BedrockModel")
    @patch("agent.agent_config.agent.Agent")
    def test_creates_agent(self, mock_agent_cls, mock_model_cls):
        mock_model_cls.return_value = MagicMock()
        mock_agent_cls.return_value = MagicMock()

        agent = create_agent()

        mock_model_cls.assert_called_once_with(
            model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
            streaming=True,
        )
        mock_agent_cls.assert_called_once()
        call_kwargs = mock_agent_cls.call_args[1]
        assert len(call_kwargs["tools"]) == 1
        assert "scheduler" in call_kwargs["system_prompt"].lower()


if __name__ == "__main__":
    unittest.main()
