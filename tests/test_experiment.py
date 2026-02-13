"""Tests for the experiment runner."""

import pytest

from neg_env.agents.base import Agent
from neg_env.agents.random_agent import RandomAgent
from neg_env.experiment.runner import ExperimentConfig, ExperimentResult, ExperimentRunner
from neg_env.types import Action, AgentResponse, TurnState


def test_experiment_single_match_completes():
    """Two RandomAgents play split100 — match should complete."""
    config = ExperimentConfig(game_id="split100", num_matches=1)
    agents = [RandomAgent(agent_id="a", seed=1), RandomAgent(agent_id="b", seed=2)]
    result = ExperimentRunner(config).run(agents)
    assert result.num_matches == 1
    assert len(result.match_results) == 1
    mr = result.match_results[0]
    assert mr.status == "finished"
    assert mr.outcome is not None
    assert mr.num_turns > 0


def test_experiment_multiple_matches():
    """Run 5 matches; verify 5 results."""
    config = ExperimentConfig(game_id="split100", num_matches=5)
    agents = [RandomAgent(agent_id="a", seed=10), RandomAgent(agent_id="b", seed=20)]
    result = ExperimentRunner(config).run(agents)
    assert result.num_matches == 5
    assert len(result.match_results) == 5
    for mr in result.match_results:
        assert mr.game_id == "split100"


def test_experiment_result_payoff_matrix():
    """payoff_matrix returns agent_id -> list of payoffs."""
    config = ExperimentConfig(game_id="split100", num_matches=3)
    agents = [RandomAgent(agent_id="a", seed=42), RandomAgent(agent_id="b", seed=43)]
    result = ExperimentRunner(config).run(agents)
    matrix = result.payoff_matrix
    # Both agents should have payoff entries for completed matches
    completed = sum(1 for mr in result.match_results if mr.outcome and "payoffs" in mr.outcome)
    if completed > 0:
        assert "a" in matrix
        assert "b" in matrix
        assert len(matrix["a"]) == completed
        assert len(matrix["b"]) == completed


def test_experiment_result_mean_payoffs():
    """mean_payoffs returns agent_id -> mean payoff."""
    config = ExperimentConfig(game_id="split100", num_matches=10)
    agents = [RandomAgent(agent_id="alice", seed=1), RandomAgent(agent_id="bob", seed=2)]
    result = ExperimentRunner(config).run(agents)
    means = result.mean_payoffs
    if means:
        for aid, mean in means.items():
            assert isinstance(mean, float)
            assert mean >= 0


def test_experiment_result_completion_rate():
    """completion_rate is between 0 and 1."""
    config = ExperimentConfig(game_id="split100", num_matches=5)
    agents = [RandomAgent(agent_id="a", seed=7), RandomAgent(agent_id="b", seed=8)]
    result = ExperimentRunner(config).run(agents)
    assert 0 <= result.completion_rate <= 1


class AlwaysFailAgent(Agent):
    """Agent that always picks an invalid action."""

    def __init__(self, agent_id: str) -> None:
        self._agent_id = agent_id

    @property
    def agent_id(self) -> str:
        return self._agent_id

    def act(self, state: TurnState) -> AgentResponse:
        return AgentResponse(action=Action(action_type="invalid_action", payload={}))


def test_experiment_max_turns_aborts_match():
    """Match aborts when max_turns is reached (agent always fails)."""
    config = ExperimentConfig(game_id="split100", num_matches=1, max_turns_per_match=5)
    agents = [AlwaysFailAgent("a"), AlwaysFailAgent("b")]
    result = ExperimentRunner(config).run(agents)
    mr = result.match_results[0]
    assert mr.num_turns == 5
    # Match should still be running (never finished naturally)
    assert mr.status == "running"


def test_experiment_logs_to_directory(tmp_path):
    """When log_directory is set, JSON log files are written."""
    config = ExperimentConfig(game_id="split100", num_matches=2, log_directory=tmp_path)
    agents = [RandomAgent(agent_id="a", seed=1), RandomAgent(agent_id="b", seed=2)]
    result = ExperimentRunner(config).run(agents)
    json_files = list(tmp_path.glob("*.json"))
    assert len(json_files) == 2
    for mr in result.match_results:
        assert (tmp_path / f"{mr.match_id}.json").exists()


def test_experiment_unknown_game_raises():
    """ExperimentRunner raises ValueError for unknown game_id."""
    config = ExperimentConfig(game_id="nonexistent_game", num_matches=1)
    agents = [RandomAgent(agent_id="a")]
    with pytest.raises(ValueError, match="Unknown game"):
        ExperimentRunner(config).run(agents)


def test_experiment_too_few_agents_raises():
    """ExperimentRunner raises ValueError when not enough agents."""
    config = ExperimentConfig(game_id="split100", num_matches=1)
    agents = [RandomAgent(agent_id="a")]
    with pytest.raises(ValueError, match="requires at least"):
        ExperimentRunner(config).run(agents)


class LifecycleTracker(Agent):
    """Agent that tracks lifecycle hooks."""

    def __init__(self, agent_id: str) -> None:
        self._agent_id = agent_id
        self.starts: list[str] = []
        self.ends: list[str] = []

    @property
    def agent_id(self) -> str:
        return self._agent_id

    def act(self, state: TurnState) -> AgentResponse:
        if state.allowed_actions:
            return AgentResponse(action=Action(action_type=state.allowed_actions[0].action_type, payload=self._payload(state.allowed_actions[0].action_type)))
        return AgentResponse(action=Action(action_type="noop", payload={}))

    def _payload(self, action_type: str) -> dict:
        if action_type == "submit_offer":
            return {"my_share": 50}
        return {}

    def on_match_start(self, match_id, game_id, agent_ids):
        self.starts.append(match_id)

    def on_match_end(self, match_id, outcome):
        self.ends.append(match_id)


def test_experiment_agent_lifecycle_hooks_called():
    """on_match_start and on_match_end are called for each match."""
    config = ExperimentConfig(game_id="split100", num_matches=3)
    a = LifecycleTracker("a")
    b = LifecycleTracker("b")
    result = ExperimentRunner(config).run([a, b])
    assert len(a.starts) == 3
    assert len(a.ends) == 3
    assert len(b.starts) == 3
    assert len(b.ends) == 3
