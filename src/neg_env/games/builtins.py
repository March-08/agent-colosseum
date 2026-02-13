"""Register built-in games (idempotent)."""

_registered = False


def ensure_builtins_registered() -> None:
    """Register all built-in games. Safe to call multiple times."""
    global _registered
    if _registered:
        return
    from neg_env.games import register_game
    from neg_env.games.auction import SimpleAuctionGame
    from neg_env.games.split100 import Split100Game

    register_game(Split100Game())
    register_game(SimpleAuctionGame())
    _registered = True
