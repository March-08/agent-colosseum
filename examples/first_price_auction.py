"""First-Price Auction — two LLM bidders submit sealed bids.

The highest bidder wins and pays their own bid.
Each bidder has a private valuation for the item.

Usage:
    pip install -e ".[langchain]"
    cp .env.example .env   # fill in your OPENAI_API_KEY
    python examples/first_price_auction.py
"""

from pathlib import Path

from dotenv import load_dotenv

from neg_env import ExperimentConfig, ExperimentRunner, LangChainNegotiationAgent
from neg_env.games.first_price_auction import FirstPriceAuctionGame
from neg_env.prompts import SYSTEM_PROMPT_AUCTION

load_dotenv()

# --- Agents ----------------------------------------------------------------

agents = [
    LangChainNegotiationAgent(
        agent_id="bidder_a",
        provider="openai",
        model="gpt-4o-mini",
        system_prompt=SYSTEM_PROMPT_AUCTION,
        temperature=0.7,
    ),
    LangChainNegotiationAgent(
        agent_id="bidder_b",
        provider="openai",
        model="gpt-4o-mini",
        system_prompt=SYSTEM_PROMPT_AUCTION,
        temperature=0.7,
    ),
]

# --- Game -------------------------------------------------------------------

game = FirstPriceAuctionGame(
    max_rounds=25,
    valuations={"bidder_a": 60, "bidder_b": 80},
)

# --- Experiment -------------------------------------------------------------

config = ExperimentConfig(
    game_id="first-price-auction",
    num_matches=5,
    max_workers=2,                          # parallel matches
    log_directory=Path("./logs/first-price-auction"),
    max_turns_per_match=20,
    max_messages_per_turn=10,
    open_dashboard=True,
    dashboard_port=8765,
    # Opik tracing (disabled by default — set to True and provide OPIK_API_KEY)
    opik_enabled=False,
    # opik_project_name="first-price-auction",
)

result = ExperimentRunner(config).run(agents, game=game)

# --- Results ----------------------------------------------------------------

print(f"\nMatches played: {result.num_matches}")
print(f"Mean bids: {result.mean_bids}")
