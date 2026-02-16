"""Register built-in games (idempotent)."""

_registered = False


def ensure_builtins_registered() -> None:
    """Register all built-in games. Safe to call multiple times."""
    global _registered
    if _registered:
        return
    from neg_env.games import register_game
    from neg_env.games.fair_split import FairSplitGame
    from neg_env.games.first_price_auction import FirstPriceAuctionGame

    register_game(FairSplitGame())
    register_game(FirstPriceAuctionGame())
    _registered = True
