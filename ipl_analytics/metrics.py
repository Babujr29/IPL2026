"""
metrics.py — Compute raw batting, bowling, and fielding metrics per player.

All metrics are derived purely from delivery-level DataFrames produced by
data_loader.py.  No formula weighting or normalisation happens here —
that lives in formulas.py.
"""

import pandas as pd
import numpy as np
from ipl_analytics.config import KEEPER_IDENTIFIERS

# Wicket kinds that are NOT credited to the bowler
_NOT_BOWLER_WICKETS = {"run out", "retired hurt", "obstructing the field",
                       "retired out", "timed out"}

# Wicket kinds that are NOT counted as batting-end dismissals
# (run outs don't reduce batting average)
_NOT_BAT_DISMISSAL = {"run out"}


# ─────────────────────────────────────────────────────────────────────────────
# Helper — count innings from delivery data
# ─────────────────────────────────────────────────────────────────────────────

def _match_innings_key(df: pd.DataFrame) -> pd.Series:
    """Unique key per player innings: (match_date, inning, bat_id)."""
    return df["match_date"].astype(str) + "_" + df["inning"] + "_" + df["bat_id"].fillna("")


# ─────────────────────────────────────────────────────────────────────────────
# 1. Batting metrics
# ─────────────────────────────────────────────────────────────────────────────

def compute_batting_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute per-player batting metrics from delivery df.

    Returns DataFrame indexed by player_id with columns:
      bat_innings, bat_runs, bat_balls, bat_dismissals,
      bat_avg, bat_sr, bat_boundary_pct,
      intl_innings, dom_innings
    """
    if df.empty:
        return pd.DataFrame()

    # Separate metrics by classification (for opposition-adjustment later)
    results = []
    for pid in df["bat_id"].dropna().unique():
        prows = df[df["bat_id"] == pid]

        for classif in ["international", "domestic"]:
            crow = prows[prows["classification"] == classif]

            # Innings: unique (match_date, inning) combos where player faced ball
            faced_rows = crow[~crow["is_wide"]]   # wides don't count as balls faced
            innings_keys = (faced_rows["match_date"].astype(str) + "_" + faced_rows["inning"])
            innings_count = innings_keys.nunique()

            balls     = len(faced_rows)
            runs      = faced_rows["bat_runs"].sum()

            # Dismissals: wicket fell on this delivery, player_out == bat_id,
            # and it's not a run-out
            dismissal_rows = crow[
                (crow["player_out_id"] == pid) &
                (~crow["wicket_kind"].isin(_NOT_BAT_DISMISSAL)) &
                (crow["wicket_kind"] != "")
            ]
            dismissals = len(dismissal_rows)

            # Boundary % = balls where runs.batsman == 4 or 6
            boundary_balls = faced_rows[faced_rows["bat_runs"].isin([4, 6])]
            boundary_pct = (len(boundary_balls) / balls * 100) if balls > 0 else 0.0

            batting_avg = runs / dismissals if dismissals > 0 else float(runs)
            batting_sr  = (runs / balls * 100) if balls > 0 else 0.0

            results.append({
                "player_id":   pid,
                "classif":     classif,
                "bat_innings": innings_count,
                "bat_runs":    runs,
                "bat_balls":   balls,
                "bat_dismissals": dismissals,
                "bat_avg":     batting_avg,
                "bat_sr":      batting_sr,
                "bat_boundary_pct": boundary_pct,
            })

    if not results:
        return pd.DataFrame()

    raw = pd.DataFrame(results)
    # Pivot intl and dom side by side
    intl = raw[raw["classif"] == "international"].set_index("player_id")
    dom  = raw[raw["classif"] == "domestic"].set_index("player_id")

    all_ids = raw["player_id"].unique()
    out_rows = []
    for pid in all_ids:
        intl_r = intl.loc[pid] if pid in intl.index else None
        dom_r  = dom.loc[pid]  if pid in dom.index  else None

        out_rows.append({
            "player_id":        pid,
            "intl_innings":     intl_r["bat_innings"] if intl_r is not None else 0,
            "dom_innings":      dom_r["bat_innings"]  if dom_r  is not None else 0,
            "bat_innings":      (intl_r["bat_innings"] if intl_r is not None else 0) +
                                (dom_r["bat_innings"]  if dom_r  is not None else 0),
            "bat_runs":         (intl_r["bat_runs"] if intl_r is not None else 0) +
                                (dom_r["bat_runs"]  if dom_r  is not None else 0),
            "bat_balls":        (intl_r["bat_balls"] if intl_r is not None else 0) +
                                (dom_r["bat_balls"]  if dom_r  is not None else 0),
            "bat_dismissals":   (intl_r["bat_dismissals"] if intl_r is not None else 0) +
                                (dom_r["bat_dismissals"]  if dom_r  is not None else 0),
            # Raw (un-adjusted) averages per split (used in adj formula)
            "intl_bat_avg":     intl_r["bat_avg"]          if intl_r is not None else 0.0,
            "dom_bat_avg":      dom_r["bat_avg"]            if dom_r  is not None else 0.0,
            "intl_bat_sr":      intl_r["bat_sr"]            if intl_r is not None else 0.0,
            "dom_bat_sr":       dom_r["bat_sr"]             if dom_r  is not None else 0.0,
            "intl_boundary_pct":intl_r["bat_boundary_pct"] if intl_r is not None else 0.0,
            "dom_boundary_pct": dom_r["bat_boundary_pct"]  if dom_r  is not None else 0.0,
        })

    return pd.DataFrame(out_rows).set_index("player_id")


# ─────────────────────────────────────────────────────────────────────────────
# 2. Bowling metrics
# ─────────────────────────────────────────────────────────────────────────────

def compute_bowling_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute per-player bowling metrics from delivery df.

    Returns DataFrame indexed by player_id with columns:
      bowl_balls, bowl_runs, bowl_wickets, bowl_economy,
      bowl_sr, bowl_dot_pct,
      intl_bowl_matches, dom_bowl_matches,
      + raw per-split versions for opposition adjustment
    """
    if df.empty:
        return pd.DataFrame()

    results = []
    for pid in df["bowler_id"].dropna().unique():
        prows = df[df["bowler_id"] == pid]

        for classif in ["international", "domestic"]:
            crow = prows[prows["classification"] == classif]

            # Legal deliveries: exclude wides AND no-balls for economy denominator
            # BUT no-balls count as balls faced (not as NOT bowled) — only wides excluded
            # Spec: "wides and no-balls are not legal deliveries for the bowler"
            legal = crow[~crow["is_wide"] & ~crow["is_noball"]]
            balls_bowled = len(legal)

            runs_conceded = crow["bowler_conceded"].sum()

            # Wickets: exclude run-outs, retired hurt, etc.
            wicket_rows = legal[
                (legal["player_out_id"].notna()) &
                (legal["player_out_id"] != "") &
                (legal["wicket_kind"] != "") &
                (~legal["wicket_kind"].isin(_NOT_BOWLER_WICKETS))
            ]
            wickets = len(wicket_rows)

            economy = (runs_conceded / balls_bowled * 6) if balls_bowled > 0 else 0.0
            bowl_sr = (balls_bowled / wickets) if wickets > 0 else float(balls_bowled) if balls_bowled > 0 else 0.0

            # Dot balls: legal deliveries with total_runs == 0
            dots = len(legal[legal["total_runs"] == 0])
            dot_pct = (dots / balls_bowled * 100) if balls_bowled > 0 else 0.0

            # Matches: unique match dates where this player bowled legally
            bowl_matches = crow["match_date"].nunique()

            results.append({
                "player_id":    pid,
                "classif":      classif,
                "bowl_balls":   balls_bowled,
                "bowl_runs":    runs_conceded,
                "bowl_wickets": wickets,
                "bowl_economy": economy,
                "bowl_sr":      bowl_sr,
                "bowl_dot_pct": dot_pct,
                "bowl_matches": bowl_matches,
            })

    if not results:
        return pd.DataFrame()

    raw = pd.DataFrame(results)
    intl = raw[raw["classif"] == "international"].set_index("player_id")
    dom  = raw[raw["classif"] == "domestic"].set_index("player_id")

    all_ids = raw["player_id"].unique()
    out_rows = []
    for pid in all_ids:
        intl_r = intl.loc[pid] if pid in intl.index else None
        dom_r  = dom.loc[pid]  if pid in dom.index  else None
        out_rows.append({
            "player_id":        pid,
            "intl_bowl_matches": intl_r["bowl_matches"] if intl_r is not None else 0,
            "dom_bowl_matches":  dom_r["bowl_matches"]  if dom_r  is not None else 0,
            "bowl_balls":       (intl_r["bowl_balls"] if intl_r is not None else 0) +
                                (dom_r["bowl_balls"]  if dom_r  is not None else 0),
            "bowl_wickets":     (intl_r["bowl_wickets"] if intl_r is not None else 0) +
                                (dom_r["bowl_wickets"]  if dom_r  is not None else 0),
            # Per-split for opposition adjustment
            "intl_bowl_economy":  intl_r["bowl_economy"] if intl_r is not None else 0.0,
            "dom_bowl_economy":   dom_r["bowl_economy"]  if dom_r  is not None else 0.0,
            "intl_bowl_sr":       intl_r["bowl_sr"]      if intl_r is not None else 0.0,
            "dom_bowl_sr":        dom_r["bowl_sr"]        if dom_r  is not None else 0.0,
            "intl_bowl_dot_pct":  intl_r["bowl_dot_pct"] if intl_r is not None else 0.0,
            "dom_bowl_dot_pct":   dom_r["bowl_dot_pct"]  if dom_r  is not None else 0.0,
        })

    return pd.DataFrame(out_rows).set_index("player_id")


# ─────────────────────────────────────────────────────────────────────────────
# 3. Fielding metrics
# ─────────────────────────────────────────────────────────────────────────────

def compute_fielding_metrics(df: pd.DataFrame, squad_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute fielding metrics per player.

    For non-keepers: catches exclude wicketkeeper's dismissals in the regular
                     catch pool (they go to the keeper pool).
    For keepers:     stumpings and all catches count.

    Returns DataFrame indexed by player_id with columns:
      fielding_matches, catches, runouts, stumpings, raw_field_score
    """
    if df.empty:
        return pd.DataFrame()

    # Only count unique matches where player was in the lineup
    # Proxy: count distinct match_dates where player appears as bat or bowler
    bat_matches  = df.groupby("bat_id")["match_date"].nunique().rename("bat_matches")
    bowl_matches = df.groupby("bowler_id")["match_date"].nunique().rename("bowl_matches")

    # Rows with dismissals
    dism_df = df[df["wicket_kind"] != ""].copy()

    all_ids = set(squad_df["identifier"].dropna().tolist())
    rows = []

    for pid in all_ids:
        is_keeper = pid in KEEPER_IDENTIFIERS

        # Matches played (approximation from batting or bowling appearances)
        matches = max(
            bat_matches.get(pid, 0),
            bowl_matches.get(pid, 0)
        )

        # Catches
        if is_keeper:
            # All caught dismissals where this player in fielder_ids
            caught_rows = dism_df[dism_df["wicket_kind"] == "caught"]
            catches = caught_rows["fielder_ids"].apply(lambda fids: pid in fids).sum()
        else:
            # Exclude stumped (keeper only); include caught except stumpings
            caught_rows = dism_df[dism_df["wicket_kind"] == "caught"]
            catches = caught_rows["fielder_ids"].apply(lambda fids: pid in fids).sum()

        # Run outs (any player can be credited)
        ro_rows = dism_df[dism_df["wicket_kind"] == "run out"]
        runouts = ro_rows["fielder_ids"].apply(lambda fids: pid in fids).sum()

        # Stumpings (keeper only; non-keepers get 0)
        stump_rows = dism_df[dism_df["wicket_kind"] == "stumped"]
        stumpings = stump_rows["fielder_ids"].apply(lambda fids: pid in fids).sum() if is_keeper else 0

        raw_field = ((catches * 2 + runouts * 1 + stumpings * 3) / matches
                     if matches > 0 else 0.0)

        rows.append({
            "player_id":        pid,
            "fielding_matches":  matches,
            "catches":          int(catches),
            "runouts":          int(runouts),
            "stumpings":        int(stumpings),
            "raw_field_score":  raw_field,
        })

    out = pd.DataFrame(rows).set_index("player_id")
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 4. IPL Aura metrics (same functions, just called on ipl_df)
# ─────────────────────────────────────────────────────────────────────────────

def compute_ipl_aura_metrics(ipl_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute IPL-specific career stats (no form-window, no opposition adjustment).
    Returns a DataFrame indexed by player_id with columns:
      ipl_matches, ipl_innings, ipl_avg, ipl_sr, ipl_boundary_pct,
      ipl_economy, ipl_bowl_sr, ipl_dot_pct
    """
    if ipl_df.empty:
        return pd.DataFrame()

    bat  = _compute_raw_batting(ipl_df)
    bowl = _compute_raw_bowling(ipl_df)

    all_ids = set(list(bat.index) + list(bowl.index))
    rows = []
    for pid in all_ids:
        b = bat.loc[pid]  if pid in bat.index  else None
        w = bowl.loc[pid] if pid in bowl.index else None

        ipl_matches = ipl_df[
            (ipl_df["bat_id"] == pid) | (ipl_df["bowler_id"] == pid)
        ]["match_date"].nunique()

        rows.append({
            "player_id":      pid,
            "ipl_matches":    ipl_matches,
            "ipl_innings":    b["innings"]       if b is not None else 0,
            "ipl_avg":        b["avg"]           if b is not None else 0.0,
            "ipl_sr":         b["sr"]            if b is not None else 0.0,
            "ipl_boundary_pct": b["boundary_pct"] if b is not None else 0.0,
            "ipl_economy":    w["economy"]       if w is not None else 0.0,
            "ipl_bowl_sr":    w["bowl_sr"]       if w is not None else 0.0,
            "ipl_dot_pct":    w["dot_pct"]       if w is not None else 0.0,
        })

    return pd.DataFrame(rows).set_index("player_id")


def _compute_raw_batting(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for pid in df["bat_id"].dropna().unique():
        prows = df[df["bat_id"] == pid]
        faced = prows[~prows["is_wide"]]
        balls = len(faced)
        runs  = faced["bat_runs"].sum()
        dims  = len(prows[
            (prows["player_out_id"] == pid) &
            (~prows["wicket_kind"].isin(_NOT_BAT_DISMISSAL)) &
            (prows["wicket_kind"] != "")
        ])
        inn_keys = (faced["match_date"].astype(str) + "_" + faced["inning"])
        innings  = inn_keys.nunique()
        avg      = runs / dims if dims > 0 else float(runs)
        sr       = (runs / balls * 100) if balls > 0 else 0.0
        bdry_pct = (len(faced[faced["bat_runs"].isin([4,6])]) / balls * 100) if balls > 0 else 0.0
        rows.append({"player_id": pid, "innings": innings, "avg": avg,
                     "sr": sr, "boundary_pct": bdry_pct})
    return pd.DataFrame(rows).set_index("player_id") if rows else pd.DataFrame()


def _compute_raw_bowling(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for pid in df["bowler_id"].dropna().unique():
        prows = df[df["bowler_id"] == pid]
        legal = prows[~prows["is_wide"] & ~prows["is_noball"]]
        balls = len(legal)
        runs  = prows["bowler_conceded"].sum()
        wkts  = len(legal[
            (legal["player_out_id"].notna()) &
            (legal["wicket_kind"] != "") &
            (~legal["wicket_kind"].isin(_NOT_BOWLER_WICKETS))
        ])
        economy = (runs / balls * 6) if balls > 0 else 0.0
        bsr     = (balls / wkts) if wkts > 0 else float(balls) if balls > 0 else 0.0
        dots    = len(legal[legal["total_runs"] == 0])
        dot_pct = (dots / balls * 100) if balls > 0 else 0.0
        rows.append({"player_id": pid, "economy": economy,
                     "bowl_sr": bsr, "dot_pct": dot_pct})
    return pd.DataFrame(rows).set_index("player_id") if rows else pd.DataFrame()
