"""Unfair Split — two LLM agents negotiate how to divide a resource.

Each agent has a private reservation value (minimum acceptable share).
If they can't agree within the round limit, both get nothing.

Usage:
    pip install -e ".[langchain]"
    cp .env.example .env   # fill in your OPENAI_API_KEY
    python examples/unfair_split.py
"""

from pathlib import Path

from dotenv import load_dotenv

from neg_env import ExperimentConfig, ExperimentRunner, LangChainNegotiationAgent
from neg_env.games.fair_split import FairSplitGame
from neg_env.prompts import SYSTEM_PROMPT_FAIR, SYSTEM_PROMPT_UNFAIR

load_dotenv()

# --- Agents ----------------------------------------------------------------

agents = [
    LangChainNegotiationAgent(
        agent_id="langchain_fair",
        provider="openai",
        model="gpt-4o-mini",
        system_prompt=SYSTEM_PROMPT_FAIR,
        temperature=1.2,
    ),
    LangChainNegotiationAgent(
        agent_id="langchain_unfair",
        provider="openai",
        model="gpt-4o-mini",
        system_prompt=SYSTEM_PROMPT_UNFAIR,
        temperature=0.7,
    ),
]

# --- Game -------------------------------------------------------------------

game = FairSplitGame(
    total=100,
    max_rounds=25,
    reservation_values={"langchain_fair": 50, "langchain_unfair": 50},
)

# --- Experiment -------------------------------------------------------------

config = ExperimentConfig(
    game_id="unfair-split",
    num_matches=3,
    max_workers=2,                          # parallel matches
    log_directory=Path("./logs/unfair-split"),
    max_turns_per_match=20,
    max_messages_per_turn=10,
    open_dashboard=True,
    dashboard_port=8765,
    # Opik tracing (disabled by default — set to True and provide OPIK_API_KEY)
    opik_enabled=False,
    # opik_project_name="unfair-split",
)

result = ExperimentRunner(config).run(agents, game=game)

# --- Results ----------------------------------------------------------------

print(f"\nDeals: {result.num_matches - result.no_deal_count}/{result.num_matches}")
print(f"Mean utility: {result.mean_payoffs}")
