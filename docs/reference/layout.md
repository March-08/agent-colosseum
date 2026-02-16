# Project Layout

```
src/neg_env/
  __init__.py          Public API exports
  types.py             Core types (Action, TurnState, ActionResult, AgentResponse, ...)
  spec/                Game spec schema (GameSpec, Phase, TurnOrder, ...)
  core/                Match runner and match state
  games/
    base.py            Game base class
    registry.py        Game registry (register_game, get_game, ...)
    builtins.py        Registers built-in games
    utils.py           Shared helpers (_messages_visible_to, _build_allowed_actions)
    fair_split.py      Unfair-split game
    first_price_auction.py  First-price auction game
  agents/
    base.py            Agent base class
    random_agent.py    RandomAgent
    langchain_agent.py LangChainNegotiationAgent
  logging/             Match event logger (JSON logs)
  experiment/
    runner.py          ExperimentRunner, ExperimentConfig, ExperimentResult
    dashboard.py       Live browser dashboard
  prompts/
    fair_split.py      SYSTEM_PROMPT_FAIR, SYSTEM_PROMPT_UNFAIR
    first_price_auction.py  SYSTEM_PROMPT_AUCTION

tests/                 Test suite
docs/                  Documentation (this site)
```
