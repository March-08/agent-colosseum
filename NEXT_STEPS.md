# Next steps to implement logic

Skeleton is in place: types, spec schema, core (match + runner stubs), two game stubs (split100, auction), MCP server with tool list and stub handlers. Implement in this order.

---

## 1. Core: match creation and turn state (no game logic yet)

- **`create_match`** in `neg_env/core/runner.py`
  - Build a `Match`: `match_id`, `game_id`, `spec`, `agent_ids`, `status=MatchStatus.RUNNING` (or WAITING if the spec requires a minimum number of agents and we don’t have them yet).
  - Copy `spec.initial_game_state` into `match.game_state`.
  - Store the match in `MatchRunner._matches`.
- **`get_turn_state`** in `neg_env/core/runner.py`
  - Load the game implementation with `get_game(match.game_id)`.
  - Call `game.compute_turn_state(match, agent_id)` once that is implemented.
  - For a minimal first pass, you can return a fixed `TurnState` (e.g. `game_over=False`, `allowed_actions=[]`) without delegating to the game, then wire to the game in step 3.

This gives: start a match → get a turn state back (even if placeholder).

---

## 2. Core: messages and actions (delegate to game)

- **`apply_message`** in `neg_env/core/runner.py`
  - Append a `Message` to `match.messages` (generate `message_id`, `timestamp_ns` if needed).
  - If the spec says “sending a message counts as your turn”, advance `current_turn_index` / `current_round` as per spec (or let the game do it in `apply_action` if you treat message as an action).
- **`apply_action`** in `neg_env/core/runner.py`
  - Load the game with `get_game(match.game_id)`.
  - Call `game.apply_action(match, agent_id, action)`.
  - After the call, if the game sets `match.outcome` or `match.status = FINISHED`, leave it as is; otherwise you can call `game.compute_outcome(match)` and set `match.outcome` / `match.status` when the game is over.

This connects the runner to the game’s transition and outcome logic.

---

## 3. One game end-to-end: Split100

Implement in `neg_env/games/split100.py`:

- **`compute_turn_state`**
  - Build `TurnState`: `match_id`, `game_id`, `agent_id`, `phase` from current phase, `is_my_turn` from round-robin (compare `agent_id` to `match.agent_ids[match.current_turn_index]`), `game_state` from `match.game_state`, `messages` filtered to what this agent can see (public + private to/from them), `allowed_actions` from current phase’s `allowed_action_types` (and whether it’s their turn).
  - If `match.status == FINISHED`, set `game_over=True` and `outcome=match.outcome`.
- **`apply_action`**
  - If action is `submit_offer`: validate payload (e.g. `my_share` in 0–100), update `match.game_state["current_offer"]` and `last_offer_by`, then advance turn (e.g. `current_turn_index = (current_turn_index + 1) % 2`).
  - If action is `accept`: set outcome (e.g. split from `current_offer`), set `match.status = FINISHED`, `match.outcome = { "payoffs": [...] }`.
  - If action is `reject`: advance turn (next agent can counter or offer).
  - Enforce `max_rounds`; if exceeded, set outcome (e.g. no deal) and finish.
- **`compute_outcome`**
  - If already finished, return `match.outcome`. Otherwise return None (or compute from current state when both have accepted).

After this, one full game (split100) works with the runner and MCP.

---

## 4. MCP server: wire tools to runner

In `neg_env/server/mcp_server.py`, implement the tool handlers (they currently raise `NotImplementedError`):

- **`start_game`**: generate `match_id` (e.g. uuid), create one agent_id for the creator, call `runner.create_match(match_id, game_id, spec, [agent_id])` (or WAITING and add agent when joining). Return `match_id` and `agent_id` (e.g. as JSON text).
- **`join_game`**: validate `match_id` + `invite_code` (invite can be match_id for now), add a new `agent_id` to `match.agent_ids`, maybe start the match if enough agents. Return `agent_id`.
- **`get_turn_state`**: call `runner.get_turn_state(match_id, agent_id)`, serialize `TurnState` to JSON, return as text.
- **`send_public_message`** / **`send_private_message`**: call `runner.send_public_message` / `runner.send_private_message` with the given args; return success/failure as text.
- **`perform_action`**: call `runner.perform_action(match_id, agent_id, action_type, payload)`; return success/failure as text.

Use a single `MatchRunner` instance (e.g. created in `create_app` and closed over by the handlers) so all tools share the same state.

---

## 5. Second game: simple auction

In `neg_env/games/auction.py`, implement:

- **`compute_turn_state`**: phase “discuss” → allow messages only, any agent can act (FREE); phase “bidding” → allow `place_bid` only, show “discuss” messages and whether the agent has already bid.
- **`apply_action`**: in “discuss”, only messages (handled by `apply_message`); in “bidding”, record `place_bid` in `match.game_state["bids"][agent_id] = amount`. When all agents have bid (or timeout), set `match.game_state["winner"]`, compute payoffs, set `match.outcome` and `match.status = FINISHED`.
- **`compute_outcome`**: highest bid wins; payoffs from your spec (e.g. winner pays second price, or first price).

---

## 6. Optional improvements

- **Invite codes**: store per-match invite codes (or match_id as code), validate in `join_game`.
- **Time limits**: in the runner or per game, check `phase.duration_seconds` and advance phase / end game when time is up.
- **Message IDs and timestamps**: generate in `apply_message` and include in `Message` and in `get_turn_state` so agents see ordered history.
- **Validation**: in `apply_action` and game logic, validate `action_type` and `payload` against the spec’s `action_types` and `payload_schema`.

Implementing 1 → 2 → 3 → 4 gives a minimal end-to-end flow (MCP client plays split100); then 5 adds a second game; then 6 polishes.
