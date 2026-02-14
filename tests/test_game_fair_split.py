"""Tests for unfair-split game: submit_offer, accept, reject, outcome."""

from neg_env.core.match import MatchStatus
from neg_env.core.runner import apply_action, create_match, get_turn_state
from neg_env.games import get_game, get_game_spec
from neg_env.types import Action


def test_unfair_split_submit_offer_updates_game_state():
    """submit_offer sets current_offer and last_offer_by, advances turn."""
    spec = get_game_spec("unfair-split")
    assert spec is not None
    match = create_match("m1", "unfair-split", spec, ["a", "b"])
    result = apply_action(match, "a", Action(action_type="submit_offer", payload={"my_share": 60}))
    assert result.ok is True
    assert match.game_state["current_offer"] == 60
    assert match.game_state["last_offer_by"] == "a"
    assert match.current_turn_index == 1
    ts = get_turn_state(match, "b")
    assert ts is not None
    assert ts.is_my_turn is True


def test_unfair_split_accept_sets_outcome_and_finishes():
    """After submit_offer, accept sets payoffs (u = x - v) and status FINISHED."""
    spec = get_game_spec("unfair-split")
    assert spec is not None
    match = create_match("m1", "unfair-split", spec, ["a", "b"])
    get_turn_state(match, "a")
    rv = match.game_state["reservation_values"]
    apply_action(match, "a", Action(action_type="submit_offer", payload={"my_share": 60}))
    result = apply_action(match, "b", Action(action_type="accept", payload={}))
    assert result.ok is True
    assert match.status == MatchStatus.FINISHED
    assert match.outcome is not None
    payoffs = {p["agent_id"]: p["utility"] for p in match.outcome["payoffs"]}
    assert payoffs["a"] == round(60.0 - rv["a"], 2)
    assert payoffs["b"] == round(40.0 - rv["b"], 2)


def test_unfair_split_reject_advances_turn():
    """reject advances turn so the other agent can offer."""
    spec = get_game_spec("unfair-split")
    assert spec is not None
    match = create_match("m1", "unfair-split", spec, ["a", "b"])
    apply_action(match, "a", Action(action_type="submit_offer", payload={"my_share": 60}))
    result = apply_action(match, "b", Action(action_type="reject", payload={}))
    assert result.ok is True
    assert match.status == MatchStatus.RUNNING
    assert match.current_turn_index == 0
    ts = get_turn_state(match, "a")
    assert ts is not None
    assert ts.is_my_turn is True


def test_unfair_split_invalid_offer_rejected():
    """submit_offer with my_share out of range returns error with invalid_payload."""
    spec = get_game_spec("unfair-split")
    assert spec is not None
    match = create_match("m1", "unfair-split", spec, ["a", "b"])
    game = get_game("unfair-split")
    assert game is not None
    result = game.apply_action(match, "a", Action(action_type="submit_offer", payload={"my_share": 150}))
    assert result.ok is False
    assert result.error == "invalid_payload"
    assert match.game_state["current_offer"] is None
    assert match.current_turn_index == 0


def test_unfair_split_accept_without_offer_invalid():
    """accept when there is no current_offer returns error."""
    spec = get_game_spec("unfair-split")
    assert spec is not None
    match = create_match("m1", "unfair-split", spec, ["a", "b"])
    game = get_game("unfair-split")
    assert game is not None
    result = game.apply_action(match, "a", Action(action_type="accept", payload={}))
    assert result.ok is False
    assert result.error == "game_rule_violation"
    assert match.status == MatchStatus.RUNNING


def test_unfair_split_cannot_accept_own_offer():
    """Agent cannot accept their own offer."""
    spec = get_game_spec("unfair-split")
    assert spec is not None
    match = create_match("m1", "unfair-split", spec, ["a", "b"])
    apply_action(match, "a", Action(action_type="submit_offer", payload={"my_share": 60}))
    # Manually set turn back to "a" to test the guard
    match.current_turn_index = 0
    game = get_game("unfair-split")
    assert game is not None
    result = game.apply_action(match, "a", Action(action_type="accept", payload={}))
    assert result.ok is False
    assert result.error == "game_rule_violation"
    assert "Cannot accept your own offer" in result.error_detail


def test_unfair_split_not_your_turn_error():
    """Attempting action when it's not your turn returns NOT_YOUR_TURN error."""
    spec = get_game_spec("unfair-split")
    assert spec is not None
    match = create_match("m1", "unfair-split", spec, ["a", "b"])
    result = apply_action(match, "b", Action(action_type="submit_offer", payload={"my_share": 50}))
    assert result.ok is False
    assert result.error == "not_your_turn"
