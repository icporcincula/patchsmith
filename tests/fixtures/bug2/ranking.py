def rank(players):
    """Return player names ordered from highest points to lowest."""
    return [p["name"] for p in sorted(players, key=lambda p: p["points"])]
