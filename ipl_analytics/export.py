"""
export.py — Write final computed scores to JSON files for the website.

Produces three files (schemas defined in OUTPUT.md):
  website/data/team_scores.json
  website/data/player_scores.json
  website/data/squad_data.json
"""

import os
import json
import math
import pandas as pd
from ipl_analytics.config import WEBSITE_DATA, IPL_TEAMS


def _safe(val):
    """Convert numpy types and NaN to JSON-safe Python types."""
    if val is None:
        return None
    if isinstance(val, float) and math.isnan(val):
        return None
    if hasattr(val, "item"):   # numpy scalar
        return val.item()
    return val


def export_team_scores(team_df: pd.DataFrame) -> None:
    """Write team_scores.json."""
    os.makedirs(WEBSITE_DATA, exist_ok=True)
    records = []
    for _, row in team_df.iterrows():
        records.append({
            "team":          _safe(row["team"]),
            "full_name":     _safe(row.get("full_name", row["team"])),
            "rank":          _safe(row["rank"]),
            "bat_avg":       round(_safe(row["bat_avg"]),  2),
            "bowl_avg":      round(_safe(row["bowl_avg"]), 2),
            "ar_avg":        round(_safe(row["ar_avg"]),   2),
            "team_score":    round(_safe(row["team_score"]), 2),
            "primary_color": _safe(row["primary_color"]),
        })
    path = os.path.join(WEBSITE_DATA, "team_scores.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)
    print(f"  [export] Wrote {path}")


def export_player_scores(player_df: pd.DataFrame) -> None:
    """Write player_scores.json."""
    os.makedirs(WEBSITE_DATA, exist_ok=True)
    records = []
    for _, row in player_df.iterrows():
        role = _safe(row.get("role", ""))
        ar_t = _safe(row.get("ar_type", None))
        # For non-allrounders set ar_type to null
        if role != "allrounder":
            ar_t = None

        records.append({
            "player_name":   _safe(row.get("player_name", "")),
            "cricsheet_id":  _safe(row.get("player_id", "")),
            "cricinfo_key":  _safe(row.get("key_cricinfo", "")),
            "team":          _safe(row.get("team", "")),
            "role":          role,
            "player_type":   _safe(row.get("player_type", "")),
            "ar_type":       ar_t,
            "form_score":    round(float(_safe(row.get("bat_form_norm", 0)) or 0), 2)
                             if role in ("batter", "keeper") else
                             round(float(_safe(row.get("bowl_form_norm", 0)) or 0), 2)
                             if role == "bowler" else
                             round(float(_safe(row.get("bat_form_norm", 0)) or 0), 2),
            "aura_score":    round(float(_safe(row.get("bat_aura_norm", 0)) or 0), 2)
                             if role in ("batter", "keeper") else
                             round(float(_safe(row.get("bowl_aura_norm", 0)) or 0), 2)
                             if role == "bowler" else
                             round(float(_safe(row.get("bat_aura_norm", 0)) or 0), 2),
            "final_score":   round(float(_safe(row.get("final_score", 0)) or 0), 2),
            # Raw metrics
            "bat_avg":       round(float(_safe(row.get("adj_avg", 0)) or 0), 2),
            "bat_sr":        round(float(_safe(row.get("adj_sr", 0)) or 0), 2),
            "boundary_pct":  round(float(_safe(row.get("adj_boundary", 0)) or 0), 2),
            "economy":       round(float(_safe(row.get("adj_econ", 0)) or 0), 2),
            "bowl_sr":       round(float(_safe(row.get("adj_bsr", 0)) or 0), 2),
            "dot_pct":       round(float(_safe(row.get("adj_dot", 0)) or 0), 2),
            # Extra fields for leaderboard
            "batter_score":  round(float(_safe(row.get("batter_score", 0)) or 0), 2),
            "bowler_score":  round(float(_safe(row.get("bowler_score", 0)) or 0), 2),
            "ar_score":      round(float(_safe(row.get("ar_score", 0)) or 0), 2),
            "bat_form_norm":  round(float(_safe(row.get("bat_form_norm", 0)) or 0), 2),
            "bat_aura_norm":  round(float(_safe(row.get("bat_aura_norm", 0)) or 0), 2),
            "bowl_form_norm": round(float(_safe(row.get("bowl_form_norm", 0)) or 0), 2),
            "bowl_aura_norm": round(float(_safe(row.get("bowl_aura_norm", 0)) or 0), 2),
            "ar_bat_component":  round(float(_safe(row.get("ar_bat_component", 0)) or 0), 2),
            "ar_bowl_component": round(float(_safe(row.get("ar_bowl_component", 0)) or 0), 2),
        })

    path = os.path.join(WEBSITE_DATA, "player_scores.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)
    print(f"  [export] Wrote {path}")


def export_squad_data(player_df: pd.DataFrame) -> None:
    """Write squad_data.json — grouped by team."""
    os.makedirs(WEBSITE_DATA, exist_ok=True)
    squad = {}
    for team in IPL_TEAMS:
        t = player_df[player_df["team"] == team]
        squad[team] = []
        for _, row in t.iterrows():
            squad[team].append({
                "player_name": _safe(row.get("player_name", "")),
                "role":        _safe(row.get("role", "")),
                "player_type": _safe(row.get("player_type", "")),
                "final_score": round(float(_safe(row.get("final_score", 0)) or 0), 2),
                "ar_type":     _safe(row.get("ar_type", None)),
                "cricinfo_key": _safe(row.get("key_cricinfo", "")),
            })

    path = os.path.join(WEBSITE_DATA, "squad_data.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(squad, f, indent=2)
    print(f"  [export] Wrote {path}")
