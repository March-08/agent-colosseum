---
name: Negotiation Environment Design
overview: Design a Python framework where games define their own conversation and outcome rules via specs; the environment exposes an MCP server from the start so agents connect as MCP clients to join and play, with no separate SDK phase.
todos: []
isProject: false
---

# Negotiation Environment Framework – Design Plan

## 1. Core idea: game specs define behavior

When a developer adds a new game, they provide a **game spec** that defines:

- **Conversation model** (how and how long agents talk)
- **Outcome resolution** (who/what decides the final result)
- **State and actions** (what agents see and can do)

The framework is generic: it runs any game that implements this spec. Different games can use different conversation and resolution rules.

---

## 2. What goes in the game spec (concrete)

A game spec would include at least:


| Concern          | Defined in spec                                   | Examples                                                                                                               |
| ---------------- | ------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| **Conversation** | Turn structure, limits, phases                    | "Alternating offers, max 10 rounds" / "Free chat until timeout" / "Phase 1: discuss (5 min), Phase 2: sealed bids"     |
| **Outcome**      | How the result is computed and when the game ends | "Valid only if both accept last offer" / "Highest bid wins; ties broken by time" / "Mediator picks from last N offers" |
| **State**        | What each agent observes each step                | Visible game state (e.g. current offer, round, time left) + message history (or summary)                               |
| **Actions**      | What agents can do per turn / phase               | Send message, submit offer, accept/reject, place bid, etc.                                                             |
| **Payoffs**      | How outcomes map to payoffs                       | e.g. (x, 100-x) for split; or auction payment rules                                                                    |


So: **conversation model** and **outcome resolution** are not global framework choices; they are **per-game parameters** in the spec. The framework enforces the spec (e.g. enforces turn order, time limits, and calls the game’s outcome function when the spec says the game is over).

---

## 3. Protocol: MCP from the start

**Choice: the environment exposes an MCP server from the beginning.** Agents connect as MCP clients to join and play; there is no separate Python SDK phase.

- **Core (in Python)**: Game spec schema, match runner (turns, state, outcome resolution), and game implementations. No agent code runs inside the framework — agents are external MCP clients.
- **MCP server**: The main interface. It loads games by spec, exposes the tools (list_games, get_game_rules, start_game, join_game, get_turn_state, send_public_message, send_private_message, perform_action), and translates tool calls into match updates. Any MCP client (Cursor, Claude, custom) can play.
- **A2A**: Can be added later as an optional adapter (same logical game/match model, different transport) if needed.

---

## 4. MCP design: tools, messages, and actions

### 4.1 How the agent reads and answers

- **Reading**: When it's an agent's turn (or when they poll), they call **one** tool that returns everything they need: game rules, current game state, whose turn it is, and **recent messages** (see below). So "attach game state when it's your turn" is implemented by that tool: the environment returns state + messages together. The agent does not need a separate "read messages" step; the turn payload includes the message history (or a summary) the agent is allowed to see.
- **Answering**: The agent then calls one or more tools to **act**: send a message (public or private) and/or perform a game action (submit offer, place bid, accept, etc.). The game spec defines what is allowed in one turn (e.g. "one message and one action" or "exactly one action, which can be a message or an offer").

So the flow is: **get context (state + messages) → then send message and/or perform action**. The environment advances the game and, when it's this agent's turn again, the next call to get context returns updated state and new messages.

### 4.2 Public vs private conversation

- **Public channel**: One shared "room" where every agent sees every message. Good for open discussion, auctions, etc.
- **Private messages**: An agent can send a message **to one or more specific agents** (e.g. "I offer you 60" to agent B only). Only the sender and the specified recipient(s) see it.

**Recommendation**: Support **both**. The game spec can restrict what's allowed (e.g. "public only", or "private only between pairs"). So: **send_public_message** (content visible to all) and **send_private_message** / **send_message_to** (params: `to: [agent_id, ...]`, `content`). Whether a game uses public, private, or both is defined in the game spec.

### 4.3 Does sending a message count as an action?

**Unified model: "action" is the general concept; sending a message is one type of action.**

- The framework treats **everything the agent does in a turn** as **actions**. So: "send public message", "send private message", "submit_offer", "place_bid", "accept", "reject" are all actions.
- The **game spec** defines, per game and per phase: which actions exist; whether a turn is **exactly one action** or **multiple actions** (e.g. "one message and one game action"); whether "send message" is allowed in the same turn as a game action.

So: in a strict alternating-offer game, your turn might be "exactly one action: either send_message (with your offer) or accept/reject" — sending the message counts as your (only) action. In a discuss-then-bid auction, phase 1 might allow only message actions; phase 2 might allow "exactly one action: place_bid". One **perform_action**-style mechanism, with action types (including message types) defined by the game spec.

### 4.4 Minimal MCP tool set


| Tool                                | Purpose                                                                                                                                                |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **list_games** / **get_game_rules** | List available games; get rules and spec (action types, phases) for a game.                                                                            |
| **start_game** / **join_game**      | Create a new match (get match_id + agent_id) or join with invite/code.                                                                                 |
| **get_turn_state**                  | Returns: game state, current phase, whose turn, **recent messages** (public + private this agent can see), allowed actions. Single "read" entry point. |
| **send_public_message**             | Post to public channel (if allowed this turn).                                                                                                         |
| **send_private_message**            | Post to specific agent(s). Params: `to: string[]`, `content: string`.                                                                                  |
| **perform_action**                  | Execute a game action. Params: `action_type: string` (e.g. `submit_offer`, `place_bid`, `accept`), `payload: object`. Action types from game spec.     |


You do **not** need separate `action_a`, `action_b` tools: one **perform_action(action_type, payload)** keeps the server generic; new games add action types in the spec without new MCP tools. **respond_to_message** can be omitted at first; agents refer to previous messages in the content of send_*; add threading later if needed.

**Summary**: One read tool (**get_turn_state** = state + messages + allowed actions). Two message tools (public, private). One generic **perform_action**. Game spec defines what counts as an action and whether a message uses your turn or can be combined with another action.

---

## 5. Other design points (brief)

- **Memory**: Keep it **per-match** by default (state + message history in memory or in a match log). Optional persistent identity/history can be a later extension.
- **Who decides**: Encoded in the game spec’s outcome resolution (agreement, engine, or mediator); the framework just runs that rule.
- **Developer experience**: Clear spec schema (e.g. YAML/JSON or Python dataclasses), 1–2 reference games (e.g. split-$100, simple auction), and a template “add a new game” so new games only fill in the spec and payoff logic.

---

## 6. Suggested next steps (once you want to implement)

1. Define the **game spec schema** (conversation model, outcome resolution, state, actions, payoffs) in Python (e.g. Pydantic or dataclasses).
2. Implement **core** (match runner that advances turns, applies spec, computes outcomes) and **2 reference games** (e.g. split-$100 with alternating offers; simple auction with discuss-then-bid).
3. Implement the **MCP server** that loads games by spec and exposes the tool set (list_games, get_game_rules, start_game, join_game, get_turn_state, send_public_message, send_private_message, perform_action); wire each tool to the match runner.
4. Optionally document how an A2A adapter would plug in later (same game/match model, different transport).

Spec-driven design, MCP-only interface from the start, all in Python.