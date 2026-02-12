"""Tests for Split100 game: submit_offer, accept, reject, outcome."""

from neg_env.core.match import MatchStatus
from neg_env.core.runner import MatchRunner, apply_action, create_match, get_turn_state
from neg_env.games import get_game, get_game_spec
from neg_env.types import Action


def test_split100_submit_offer_updates_game_state():
    """submit_offer sets current_offer and last_offer_by, advances turn."""
    spec = get_game_spec("split100")
    assert spec is not None
    match = create_match("m1", "split100", spec, ["a", "b"])
    apply_action(match, "a", Action(action_type="submit_offer", payload={"my_share": 60}))
    assert match.game_state["current_offer"] == 60
    assert match.game_state["last_offer_by"] == "a"
    assert match.current_turn_index == 1
    ts = get_turn_state(match, "b")
    assert ts is not None
    assert ts.is_my_turn is True


def test_split100_accept_sets_outcome_and_finishes():
    """After submit_offer, accept sets payoffs and status FINISHED."""
    spec = get_game_spec("split100")
    assert spec is not None
    match = create_match("m1", "split100", spec, ["a", "b"])
    apply_action(match, "a", Action(action_type="submit_offer", payload={"my_share": 60}))
    apply_action(match, "b", Action(action_type="accept", payload={}))
    assert match.status == MatchStatus.FINISHED
    assert match.outcome is not None
    payoffs = {p["agent_id"]: p["value"] for p in match.outcome["payoffs"]}
    assert payoffs["a"] == 60.0
    assert payoffs["b"] == 40.0


def test_split100_reject_advances_turn():
    """reject advances turn so the other agent can offer."""
    spec = get_game_spec("split100")
    assert spec is not None
    match = create_match("m1", "split100", spec, ["a", "b"])
    apply_action(match, "a", Action(action_type="submit_offer", payload={"my_share": 60}))
    apply_action(match, "b", Action(action_type="reject", payload={}))
    assert match.status == MatchStatus.RUNNING
    assert match.current_turn_index == 0
    ts = get_turn_state(match, "a")
    assert ts is not None
    assert ts.is_my_turn is True


def test_split100_invalid_offer_rejected():
    """submit_offer with my_share out of range returns False and does not advance."""
    spec = get_game_spec("split100")
    assert spec is not None
    match = create_match("m1", "split100", spec, ["a", "b"])
    game = get_game("split100")
    assert game is not None
    ok = game.apply_action(match, "a", Action(action_type="submit_offer", payload={"my_share": 150}))
    assert ok is False
    assert match.game_state["current_offer"] is None
    assert match.current_turn_index == 0


def test_split100_accept_without_offer_invalid():
    """accept when there is no current_offer returns False."""
    spec = get_game_spec("split100")
    assert spec is not None
    match = create_match("m1", "split100", spec, ["a", "b"])
    game = get_game("split100")
    assert game is not None
    ok = game.apply_action(match, "a", Action(action_type="accept", payload={}))
    assert ok is False
    assert match.status == MatchStatus.RUNNING


def test_split100_runner_perform_action_flow():
    """MatchRunner.perform_action: offer then accept -> outcome."""
    spec = get_game_spec("split100")
    assert spec is not None
    runner = MatchRunner()
    runner.create_match("m1", "split100", spec, ["alice", "bob"])
    ok1 = runner.perform_action("m1", "alice", "submit_offer", {"my_share": 70})
    assert ok1 is True
    ts = runner.get_turn_state("m1", "bob")
    assert ts is not None
    assert ts.is_my_turn is True
    ok2 = runner.perform_action("m1", "bob", "accept", {})
    assert ok2 is True
    match = runner.get_match("m1")
    assert match is not None
    assert match.status == MatchStatus.FINISHED
    payoffs = {p["agent_id"]: p["value"] for p in match.outcome["payoffs"]}
    assert payoffs["alice"] == 70.0
    assert payoffs["bob"] == 30.0
