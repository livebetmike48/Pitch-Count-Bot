"""
Aggregate stats over a pitcher's recent starts (ERA, K/9, WHIP, etc),
computed from the raw per-game splits returned by mlb_api.get_pitcher_game_log.
"""

# Thresholds for the hot/cold tags. Deliberately conservative (requires at
# least 3 starts in the window) so a single great/bad outing doesn't swing it.
HOT_ERA_THRESHOLD = 2.50
COLD_ERA_THRESHOLD = 6.00
MIN_STARTS_FOR_TAG = 3


def parse_ip(ip_str: str) -> float:
    """
    MLB's innings-pitched notation uses .1 = one out (1/3 inning) and
    .2 = two outs (2/3 inning) -- NOT decimal tenths. "6.1" means 6 and
    1/3 innings, not 6.1 innings. This converts to a true float.
    """
    if not ip_str:
        return 0.0
    whole_str, _, frac_str = str(ip_str).partition(".")
    whole = int(whole_str) if whole_str else 0
    thirds = {"0": 0.0, "1": 1 / 3, "2": 2 / 3}.get(frac_str, 0.0)
    return whole + thirds


def summarize_outings(splits: list[dict], n: int, starts_only: bool = True) -> dict | None:
    """
    splits: chronological (oldest-first) list of appearance dicts from
            get_pitcher_game_log.
    n: how many most recent starts (or appearances) to summarize.
    Returns None if there's nothing to summarize, else aggregate stats.
    """
    pool = [s for s in splits if s.get("is_start")] if starts_only else splits
    recent = pool[-n:]
    if not recent:
        return None

    total_ip = sum(parse_ip(s["ip"]) for s in recent)
    total_er = sum(s["er"] for s in recent)
    total_so = sum(s["so"] for s in recent)
    total_bb = sum(s["bb"] for s in recent)
    total_h = sum(s["hits"] for s in recent)
    total_pitches = sum(s["pitches"] for s in recent)

    era = (total_er * 9 / total_ip) if total_ip > 0 else None
    k9 = (total_so * 9 / total_ip) if total_ip > 0 else None
    whip = ((total_bb + total_h) / total_ip) if total_ip > 0 else None

    return {
        "count": len(recent),
        "total_ip": round(total_ip, 1),
        "era": round(era, 2) if era is not None else None,
        "k9": round(k9, 2) if k9 is not None else None,
        "whip": round(whip, 2) if whip is not None else None,
        "avg_pitches": round(total_pitches / len(recent), 1),
        "total_er": total_er,
        "total_so": total_so,
    }


def hot_cold_tag(summary: dict | None) -> str | None:
    """Returns a tag string or None. Only fires with enough starts to matter."""
    if not summary or summary["count"] < MIN_STARTS_FOR_TAG or summary["era"] is None:
        return None
    if summary["era"] <= HOT_ERA_THRESHOLD:
        return "🔥 Hot"
    if summary["era"] >= COLD_ERA_THRESHOLD:
        return "🥶 Cold"
    return None
