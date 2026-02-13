"""Prompt templates for agent games. Add new games as separate modules (e.g. prompts/auction.py)."""

from neg_env.prompts.fair_split import SYSTEM_PROMPT_FAIR, SYSTEM_PROMPT_UNFAIR

__all__ = ["SYSTEM_PROMPT_FAIR", "SYSTEM_PROMPT_UNFAIR"]
