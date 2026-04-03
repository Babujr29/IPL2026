"""
team_aggregation.py — Aggregate player scores into team-level TeamScore.

Formula (main.md Step 8):
  BatAvg  = mean of all BatterScore in squad (includes keepers)
  BowlAvg = mean of all BowlerScore in squad
  ARAvg   = mean of all ARScore in squad

  TeamScore = 0.33×BatAvg + 0.39×BowlAvg + 0.28×ARAvg

Debutants and inactive players are included in their role group averages.
"""

import pandas as pd
import numpy as np
from ipl_analytics.config import (
    TEAM_BAT_W, TEAM_BOWL_W, TEAM_AR_W,
    IPL_TEAMS, TEAM_COLORS, TEAM_FULL_NAMES,
)


def compute_team_scores(player_df: pd.DataFrame) -> pd.DataFrame:
    """
    Given the full player scores DataFrame (one row per squad member),
    compute and return a team summary DataFrame sorted by TeamScore descending.

    Returns columns:
      team, full_name, rank, bat_avg, bowl_avg, ar_avg, team_score,
      primary_color
    """
    rows = []

    for team in IPL_TEAMS:
        t = player_df[player_df["team"] == team]
        if t.empty:
            continue

        batters     = t[t["role"].isin(["batter", "keeper"])]
        bowlers     = t[t["role"] == "bowler"]
        allrounders = t[t["role"] == "allrounder"]

        bat_avg  = batters["batter_score"].mean() if len(batters) > 0 else 0.0
        bowl_avg = bowlers["bowler_score"].mean() if len(bowlers) > 0 else 0.0
        ar_avg   = allrounders["ar_score"].mean() if len(allrounders) > 0 else 0.0

        team_score = TEAM_BAT_W * bat_avg + TEAM_BOWL_W * bowl_avg + TEAM_AR_W * ar_avg

        rows.append({
            "team":          team,
            "full_name":     TEAM_FULL_NAMES.get(team, team),
            "bat_avg":       round(float(bat_avg),  4),
            "bowl_avg":      round(float(bowl_avg), 4),
            "ar_avg":        round(float(ar_avg),   4),
            "team_score":    round(float(team_score), 4),
            "primary_color": TEAM_COLORS.get(team, "#FFFFFF"),
        })

    team_df = pd.DataFrame(rows)
    team_df = team_df.sort_values("team_score", ascending=False).reset_index(drop=True)
    team_df.insert(0, "rank", range(1, len(team_df) + 1))

    return team_df
