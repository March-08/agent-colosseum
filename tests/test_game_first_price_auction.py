"""Tests for first-price sealed-bid auction game."""

from neg_env.core.match import MatchStatus
from neg_env.core.runner import apply_action, create_match, get_turn_state
from neg_env.games import get_game, get_game_spec
from neg_env.types import Action


def test_auction_submit_bid_stores_bid():
    """submit_bid stores the bid and does not reveal it to opponent."""
    spec = get_game_spec("first-price-auction")
    assert spec is not None
    match = create_match("m1", "first-price-auction", spec, ["a", "b"])
    result = apply_action(match, "a", Action(action_type="submit_bid", payload={"bid": 40}))
    assert result.ok is True
    assert match.game_state["bids"]["a"] == 40.0
    assert match.status == MatchStatus.RUNNING
    # Opponent cannot see bid amount
    ts_b = get_turn_state(match, "b")
    assert ts_b is not None
    assert ts_b.game_state["opponent_has_bid"] is True
    assert "my_bid" not in ts_b.game_state or ts_b.game_state["my_bid"] is None


def test_auction_both_bids_resolves():
    """When both bids are in, winner is determined and utilities computed."""
    spec = get_game_spec("first-price-auction")
    assert spec is not None
    match = create_match("m1", "first-price-auction", spec, ["a", "b"])
    # Ensure valuations are set
    get_turn_state(match, "a")
    valuations = match.game_state["valuations"]
    apply_action(match, "a", Action(action_type="submit_bid", payload={"bid": 40}))
    apply_action(match, "b", Action(action_type="submit_bid", payload={"bid": 35}))
    assert match.status == MatchStatus.FINISHED
    assert match.outcome is not None
    assert match.outcome["winner"] == "a"
    assert match.outcome["reason"] == "auction_resolved"
    payoffs = {p["agent_id"]: p for p in match.outcome["payoffs"]}
    assert payoffs["a"]["utility"] == round(valuations["a"] - 40, 2)
    assert payoffs["a"]["bid"] == 40.0
    assert payoffs["b"]["utility"] == 0.0
    assert payoffs["b"]["bid"] == 35.0


def test_auction_tie_resolved():
    """Tied bids are broken deterministically by match_id seed."""
    spec = get_game_spec("first-price-auction")
    assert spec is not None
    match = create_match("tie-test", "first-price-auction", spec, ["a", "b"])
    get_turn_state(match, "a")
    apply_action(match, "a", Action(action_type="submit_bid", payload={"bid": 50}))
    apply_action(match, "b", Action(action_type="submit_bid", payload={"bid": 50}))
    assert match.status == MatchStatus.FINISHED
    assert match.outcome["winner"] in ("a", "b")
    # Run again with same match_id → same winner (deterministic)
    match2 = create_match("tie-test", "first-price-auction", spec, ["a", "b"])
    get_turn_state(match2, "a")
    apply_action(match2, "a", Action(action_type="submit_bid", payload={"bid": 50}))
    apply_action(match2, "b", Action(action_type="submit_bid", payload={"bid": 50}))
    assert match2.outcome["winner"] == match.outcome["winner"]


def test_auction_cannot_bid_twice():
    """Agent cannot submit a second bid."""
    spec = get_game_spec("first-price-auction")
    assert spec is not None
    match = create_match("m1", "first-price-auction", spec, ["a", "b"])
    get_turn_state(match, "a")
    apply_action(match, "a", Action(action_type="submit_bid", payload={"bid": 40}))
    # Force turn back to "a" to test the guard
    match.current_turn_index = 0
    game = get_game("first-price-auction")
    assert game is not None
    result = game.apply_action(match, "a", Action(action_type="submit_bid", payload={"bid": 45}))
    assert result.ok is False
    assert result.error == "game_rule_violation"


def test_auction_invalid_bid_rejected():
    """Negative bid is rejected."""
    spec = get_game_spec("first-price-auction")
    assert spec is not None
    match = create_match("m1", "first-price-auction", spec, ["a", "b"])
    game = get_game("first-price-auction")
    assert game is not None
    result = game.apply_action(match, "a", Action(action_type="submit_bid", payload={"bid": -5}))
    assert result.ok is False
    assert result.error == "invalid_payload"
    assert "bids" not in match.game_state or "a" not in match.game_state.get("bids", {})


def test_auction_max_rounds_no_bids():
    """If max_rounds exceeded without both bids, both get utility 0."""
    from neg_env.games.first_price_auction import FirstPriceAuctionGame

    game = FirstPriceAuctionGame(max_rounds=1)
    spec = game.spec()
    match = create_match("m1", "first-price-auction", spec, ["a", "b"])
    game._ensure_valuations(match)
    # a passes, b passes → round advances, hits max_rounds
    game.apply_action(match, "a", Action(action_type="pass", payload={}))
    game.apply_action(match, "b", Action(action_type="pass", payload={}))
    assert match.status == MatchStatus.FINISHED
    assert match.outcome["reason"] == "max_rounds_exceeded"
    for p in match.outcome["payoffs"]:
        assert p["utility"] == 0.0


def test_auction_action_history_tracks_bids():
    """action_history records submit_bid without revealing the bid amount."""
    spec = get_game_spec("first-price-auction")
    assert spec is not None
    match = create_match("m1", "first-price-auction", spec, ["a", "b"])
    get_turn_state(match, "a")
    apply_action(match, "a", Action(action_type="submit_bid", payload={"bid": 40}))
    history = match.game_state["action_history"]
    assert len(history) == 1
    entry = history[0]
    assert entry["agent_id"] == "a"
    assert entry["action"] == "submit_bid"
    assert "bid" not in entry  # bid amount is sealed


def test_auction_visible_state_hides_opponent_bid():
    """_visible_game_state shows own bid but hides opponent's bid amount."""
    from neg_env.games.first_price_auction import FirstPriceAuctionGame

    game = FirstPriceAuctionGame(valuations={"a": 60, "b": 80})
    spec = game.spec()
    match = create_match("m1", "first-price-auction", spec, ["a", "b"])
    game._ensure_valuations(match)
    match.game_state["bids"]["a"] = 40.0
    visible_a = game._visible_game_state(match, "a")
    visible_b = game._visible_game_state(match, "b")
    # a can see own bid
    assert visible_a["my_bid"] == 40.0
    assert visible_a["my_valuation"] == 60
    # b cannot see a's bid amount, only that a has bid
    assert visible_b["my_bid"] is None
    assert visible_b["opponent_has_bid"] is True
    assert visible_b["my_valuation"] == 80


def test_auction_custom_valuations():
    """Fixed valuations are applied correctly."""
    from neg_env.games.first_price_auction import FirstPriceAuctionGame

    game = FirstPriceAuctionGame(valuations={"a": 60, "b": 80})
    spec = game.spec()
    match = create_match("m1", "first-price-auction", spec, ["a", "b"])
    game._ensure_valuations(match)
    assert match.game_state["valuations"] == {"a": 60, "b": 80}
    # Play through: a bids 40, b bids 35 → a wins
    game.apply_action(match, "a", Action(action_type="submit_bid", payload={"bid": 40}))
    match.current_turn_index = 1  # ensure b's turn
    game.apply_action(match, "b", Action(action_type="submit_bid", payload={"bid": 35}))
    assert match.outcome["winner"] == "a"
    payoffs = {p["agent_id"]: p for p in match.outcome["payoffs"]}
    assert payoffs["a"]["utility"] == 20.0  # 60 - 40
    assert payoffs["b"]["utility"] == 0.0
