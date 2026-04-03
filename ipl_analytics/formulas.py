"""
formulas.py — All rating formula logic for IPL 2026 strength system.

Steps implemented (matching main.md exactly):
  Step 1  — Confidence multiplier
  Step 2  — Opposition-adjusted metrics
  Step 3  — Fielding score normalisation + modifier
  Step 4  — Player classification
  Step 5  — Batter score
  Step 6  — Bowler score
  Step 7  — All-rounder score (with auto ar_type)
"""

import pandas as pd
import numpy as np
from ipl_analytics.config import (
    CONFIDENCE_INNINGS_CAP,
    INTL_WEIGHT, DOM_WEIGHT,
    FIELD_HIGH_THRESHOLD, FIELD_MID_THRESHOLD,
    FIELD_HIGH_MOD, FIELD_MID_MOD, FIELD_LOW_MOD,
    IPL_LOW_EXP_MAX, IPL_YOUNG_EST_MAX,
    DISCOUNT_LOW_1_2, DISCOUNT_LOW_3_4, DISCOUNT_DEBUTANT, DISCOUNT_INACTIVE,
    FLOOR_DEBUTANT_LOW, FLOOR_INACTIVE,
    FW_YOUNG_EST, AW_YOUNG_EST, FW_ESTABLISHED, AW_ESTABLISHED,
    BAT_AVG_W, BAT_SR_W, BAT_BDRY_W,
    BOWL_ECON_W, BOWL_BSR_W, BOWL_DOT_W,
    AR_BAT_THRESH, AR_BOWL_THRESH,
    AR_BAT_WEIGHTS, AR_BOWL_WEIGHTS, AR_BAL_WEIGHTS,
    NORM_MIDPOINT, KEEPER_IDENTIFIERS,
)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — Confidence Multiplier
# ─────────────────────────────────────────────────────────────────────────────

def confidence_multiplier(form_innings: int) -> float:
    """C = min(form_innings / 15, 1.0)"""
    return min(form_innings / CONFIDENCE_INNINGS_CAP, 1.0)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — Opposition-Adjusted Metrics
# ─────────────────────────────────────────────────────────────────────────────

def opposition_adjusted(intl_m: float, dom_m: float, intl_val: float, dom_val: float) -> float:
    """
    AdjMetric = (intl_m × val × 1.2 + dom_m × val × 1.0)
                / (intl_m × 1.2 + dom_m × 1.0)

    If no matches at all, returns 0.0.
    """
    denom = intl_m * INTL_WEIGHT + dom_m * DOM_WEIGHT
    if denom == 0:
        return 0.0
    numer = intl_m * intl_val * INTL_WEIGHT + dom_m * dom_val * DOM_WEIGHT
    return numer / denom


def apply_batting_adjustments(row: pd.Series) -> dict:
    """
    Given a player's batting metric row (with intl_* and dom_* splits),
    return adjusted AdjAvg, AdjSR, AdjBoundary.
    """
    intl_m = float(row.get("intl_innings", 0) or 0)
    dom_m  = float(row.get("dom_innings",  0) or 0)

    adj_avg    = opposition_adjusted(intl_m, dom_m,
                                     row.get("intl_bat_avg", 0),
                                     row.get("dom_bat_avg",  0))
    adj_sr     = opposition_adjusted(intl_m, dom_m,
                                     row.get("intl_bat_sr", 0),
                                     row.get("dom_bat_sr",  0))
    adj_boundary = opposition_adjusted(intl_m, dom_m,
                                        row.get("intl_boundary_pct", 0),
                                        row.get("dom_boundary_pct",  0))
    return {"adj_avg": adj_avg, "adj_sr": adj_sr, "adj_boundary": adj_boundary}


def apply_bowling_adjustments(row: pd.Series) -> dict:
    """
    Return AdjEcon, AdjBowlSR, AdjDot.
    """
    intl_m = float(row.get("intl_bowl_matches", 0) or 0)
    dom_m  = float(row.get("dom_bowl_matches",  0) or 0)

    adj_econ   = opposition_adjusted(intl_m, dom_m,
                                     row.get("intl_bowl_economy", 0),
                                     row.get("dom_bowl_economy",  0))
    adj_bsr    = opposition_adjusted(intl_m, dom_m,
                                     row.get("intl_bowl_sr", 0),
                                     row.get("dom_bowl_sr",  0))
    adj_dot    = opposition_adjusted(intl_m, dom_m,
                                     row.get("intl_bowl_dot_pct", 0),
                                     row.get("dom_bowl_dot_pct",  0))
    return {"adj_econ": adj_econ, "adj_bsr": adj_bsr, "adj_dot": adj_dot}


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — Fielding Score
# ─────────────────────────────────────────────────────────────────────────────

def normalise_to_10(series: pd.Series) -> pd.Series:
    """
    N(x) = ((x - min) / (max - min)) × 10
    Edge case: if max == min, all values map to NORM_MIDPOINT (0 by spec,
    so floor rules still dominate).
    """
    mn, mx = series.min(), series.max()
    if mx == mn:
        return pd.Series(NORM_MIDPOINT, index=series.index)
    return ((series - mn) / (mx - mn)) * 10.0


def compute_fielding_modifiers(fielding_df: pd.DataFrame,
                                keeper_ids: set) -> pd.Series:
    """
    Normalise RawField within two pools (keepers / non-keepers).
    Return a Series indexed by player_id with fielding modifier f.
    """
    if fielding_df.empty:
        return pd.Series(dtype=float)

    raw = fielding_df["raw_field_score"]
    norm = pd.Series(NORM_MIDPOINT, index=fielding_df.index)

    keeper_mask    = fielding_df.index.isin(keeper_ids)
    nonkeeper_mask = ~keeper_mask

    if keeper_mask.any():
        norm[keeper_mask] = normalise_to_10(raw[keeper_mask])
    if nonkeeper_mask.any():
        norm[nonkeeper_mask] = normalise_to_10(raw[nonkeeper_mask])

    def _mod(score: float) -> float:
        if score >= FIELD_HIGH_THRESHOLD:
            return FIELD_HIGH_MOD
        elif score >= FIELD_MID_THRESHOLD:
            return FIELD_MID_MOD
        else:
            return FIELD_LOW_MOD

    return norm.map(_mod)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — Player Classification
# ─────────────────────────────────────────────────────────────────────────────

def classify_player(form_innings: int, ipl_matches: int) -> str:
    """
    Return one of: 'debutant', 'low_exp', 'inactive',
                   'young_established', 'established'

    Inactive takes priority: if no form innings at all → inactive.
    """
    if form_innings == 0:
        return "inactive"
    if ipl_matches == 0:
        return "debutant"
    if ipl_matches <= IPL_LOW_EXP_MAX:
        return "low_exp"
    if ipl_matches <= IPL_YOUNG_EST_MAX:
        return "young_established"
    return "established"


def player_type_weights(p_type: str) -> tuple[float, float]:
    """Return (fw, aw) for a player type."""
    if p_type in ("debutant", "low_exp"):
        return (1.0, 0.0)
    if p_type == "inactive":
        return (0.0, 1.0)
    if p_type == "young_established":
        return (FW_YOUNG_EST, AW_YOUNG_EST)
    return (FW_ESTABLISHED, AW_ESTABLISHED)   # established


def low_exp_discount(ipl_matches: int) -> float:
    """Discount rate for debutant and low-exp players."""
    if ipl_matches == 0:
        return DISCOUNT_DEBUTANT
    if ipl_matches <= 2:
        return DISCOUNT_LOW_1_2
    return DISCOUNT_LOW_3_4


# ─────────────────────────────────────────────────────────────────────────────
# Global normalisation (must be run ONCE across ALL players before scoring)
# ─────────────────────────────────────────────────────────────────────────────

def normalise_global(series: pd.Series) -> pd.Series:
    """
    Normalise a raw score series to 0–10 using global min/max.
    Handles: empty series, all-zero, all-equal.
    """
    if series.empty:
        return series
    mn, mx = series.min(), series.max()
    if mx == mn:
        return pd.Series(NORM_MIDPOINT, index=series.index)
    return ((series - mn) / (mx - mn)) * 10.0


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — Batter Score (also used for Keepers)
# ─────────────────────────────────────────────────────────────────────────────

def raw_bat_form(C: float, adj_avg: float, adj_sr: float, adj_boundary: float) -> float:
    """BatForm = C × (0.40×AdjAvg + 0.40×AdjSR + 0.20×AdjBoundary)"""
    return C * (BAT_AVG_W * adj_avg + BAT_SR_W * adj_sr + BAT_BDRY_W * adj_boundary)


def raw_bat_aura(ipl_avg: float, ipl_sr: float, ipl_boundary_pct: float) -> float:
    """BatAura = 0.40×ipl_avg + 0.40×ipl_sr + 0.20×ipl_boundary_pct"""
    return BAT_AVG_W * ipl_avg + BAT_SR_W * ipl_sr + BAT_BDRY_W * ipl_boundary_pct


def batter_score(p_type: str, ipl_matches: int,
                 bat_form_norm: float, bat_aura_norm: float,
                 f: float) -> float:
    """
    Compute final BatterScore.
    bat_form_norm and bat_aura_norm are already normalised to 0–10.
    """
    if p_type in ("debutant", "low_exp"):
        discount = low_exp_discount(ipl_matches)
        raw = bat_form_norm
        score = max(raw * discount, FLOOR_DEBUTANT_LOW)
    elif p_type == "inactive":
        raw = bat_aura_norm
        score = max(raw * DISCOUNT_INACTIVE, FLOOR_INACTIVE)
    else:
        fw, aw = player_type_weights(p_type)
        raw = fw * bat_form_norm + aw * bat_aura_norm
        score = raw

    return score * (1 + f)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 — Bowler Score
# ─────────────────────────────────────────────────────────────────────────────

def invert_metric(value: float, global_max: float) -> float:
    """Inv(x) = GlobalMax(x) − x   (lower economy/SR is better)"""
    return max(global_max - value, 0.0)


def raw_bowl_form(C: float, adj_econ: float, adj_bsr: float, adj_dot: float,
                  global_max_econ: float, global_max_bsr: float) -> float:
    """
    BowlForm = C × (0.35×Inv(AdjEcon) + 0.35×Inv(AdjBowlSR) + 0.30×AdjDot)
    """
    inv_econ = invert_metric(adj_econ, global_max_econ)
    inv_bsr  = invert_metric(adj_bsr,  global_max_bsr)
    return C * (BOWL_ECON_W * inv_econ + BOWL_BSR_W * inv_bsr + BOWL_DOT_W * adj_dot)


def raw_bowl_aura(ipl_economy: float, ipl_bowl_sr: float, ipl_dot_pct: float,
                  global_max_econ: float, global_max_bsr: float) -> float:
    """
    BowlAura = 0.35×Inv(ipl_economy) + 0.35×Inv(ipl_bowl_sr) + 0.30×ipl_dot_pct
    """
    inv_econ = invert_metric(ipl_economy, global_max_econ)
    inv_bsr  = invert_metric(ipl_bowl_sr, global_max_bsr)
    return BOWL_ECON_W * inv_econ + BOWL_BSR_W * inv_bsr + BOWL_DOT_W * ipl_dot_pct


def bowler_score(p_type: str, ipl_matches: int,
                 bowl_form_norm: float, bowl_aura_norm: float,
                 f: float) -> float:
    """Compute final BowlerScore (mirrors batter_score structure)."""
    if p_type in ("debutant", "low_exp"):
        discount = low_exp_discount(ipl_matches)
        raw = bowl_form_norm
        score = max(raw * discount, FLOOR_DEBUTANT_LOW)
    elif p_type == "inactive":
        raw = bowl_aura_norm
        score = max(raw * DISCOUNT_INACTIVE, FLOOR_INACTIVE)
    else:
        fw, aw = player_type_weights(p_type)
        raw = fw * bowl_form_norm + aw * bowl_aura_norm
        score = raw

    return score * (1 + f)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 7 — All-rounder Score
# ─────────────────────────────────────────────────────────────────────────────

def derive_ar_type(p_type: str,
                   bat_form_norm: float, bat_aura_norm: float,
                   bowl_form_norm: float, bowl_aura_norm: float) -> tuple[str, float, float]:
    """
    Auto-derive the AR type (batting/balanced/bowling) and return
    (ar_type, alpha, beta).

    For debutant/low_exp → use form only.
    For inactive → use aura only.
    For others → use fw/aw components.
    """
    fw, aw = player_type_weights(p_type)

    if p_type in ("debutant", "low_exp"):
        bat_comp  = bat_form_norm
        bowl_comp = bowl_form_norm
    elif p_type == "inactive":
        bat_comp  = bat_aura_norm
        bowl_comp = bowl_aura_norm
    else:
        bat_comp  = fw * bat_form_norm + aw * bat_aura_norm
        bowl_comp = fw * bowl_form_norm + aw * bowl_aura_norm

    total = bat_comp + bowl_comp
    if total == 0:
        bat_ratio = 0.5   # perfectly balanced when both zero
    else:
        bat_ratio = bat_comp / total

    if bat_ratio > AR_BAT_THRESH:
        ar_type = "batting"
        alpha, beta = AR_BAT_WEIGHTS
    elif bat_ratio < AR_BOWL_THRESH:
        ar_type = "bowling"
        alpha, beta = AR_BOWL_WEIGHTS
    else:
        ar_type = "balanced"
        alpha, beta = AR_BAL_WEIGHTS

    return ar_type, alpha, beta


def allrounder_score(p_type: str, ipl_matches: int,
                     bat_form_norm: float, bat_aura_norm: float,
                     bowl_form_norm: float, bowl_aura_norm: float,
                     f: float) -> tuple[str, float, float, float, float]:
    """
    Compute ARScore and return:
      (ar_type, bat_component, bowl_component, raw_ar, ar_score)
    """
    ar_type, alpha, beta = derive_ar_type(p_type,
                                           bat_form_norm, bat_aura_norm,
                                           bowl_form_norm, bowl_aura_norm)
    fw, aw = player_type_weights(p_type)

    if p_type in ("debutant", "low_exp"):
        bat_comp  = bat_form_norm
        bowl_comp = bowl_form_norm
        raw_ar    = alpha * bat_comp + beta * bowl_comp
        discount  = low_exp_discount(ipl_matches)
        score     = max(raw_ar * discount, FLOOR_DEBUTANT_LOW) * (1 + f)

    elif p_type == "inactive":
        bat_comp  = bat_aura_norm
        bowl_comp = bowl_aura_norm
        raw_ar    = alpha * bat_comp + beta * bowl_comp
        score     = max(raw_ar * DISCOUNT_INACTIVE, FLOOR_INACTIVE) * (1 + f)

    else:
        bat_comp  = fw * bat_form_norm + aw * bat_aura_norm
        bowl_comp = fw * bowl_form_norm + aw * bowl_aura_norm
        raw_ar    = alpha * bat_comp + beta * bowl_comp
        score     = raw_ar * (1 + f)

    return ar_type, float(bat_comp), float(bowl_comp), float(raw_ar), float(score)


# ─────────────────────────────────────────────────────────────────────────────
# Master function — compute ALL player scores end-to-end
# ─────────────────────────────────────────────────────────────────────────────

def compute_all_player_scores(squad_df: pd.DataFrame,
                               bat_metrics: pd.DataFrame,
                               bowl_metrics: pd.DataFrame,
                               field_metrics: pd.DataFrame,
                               ipl_metrics: pd.DataFrame) -> pd.DataFrame:
    """
    Assemble squad_df with all metric tables, run Steps 1–7,
    and return a flat DataFrame with one row per player and all scores.

    Steps:
      1. Merge all metric tables onto squad_df
      2. Classify each player
      3. Compute raw BatForm and BatAura for every player
      4. Compute raw BowlForm and BowlAura for every player
      5. Normalise GLOBALLY (batters+keepers+allrounders for bat;
                             bowlers+allrounders for bowl)
      6. Score each player by role
    """

    df = squad_df.copy().set_index("identifier")

    # ── Merge metrics (left join so all squad players appear) ─────────────────
    if not bat_metrics.empty:
        df = df.join(bat_metrics, how="left")
    if not bowl_metrics.empty:
        df = df.join(bowl_metrics, how="left")
    if not field_metrics.empty:
        df = df.join(field_metrics, how="left")
    if not ipl_metrics.empty:
        df = df.join(ipl_metrics, how="left")

    df = df.fillna(0.0)

    # ── Step 1: Confidence Multiplier ────────────────────────────────────────
    df["C"] = df["bat_innings"].apply(lambda x: confidence_multiplier(int(x)))

    # ── Step 2: Opposition-adjusted batting metrics ──────────────────────────
    adj_bat = df.apply(apply_batting_adjustments, axis=1, result_type="expand")
    df[["adj_avg", "adj_sr", "adj_boundary"]] = adj_bat

    adj_bowl = df.apply(apply_bowling_adjustments, axis=1, result_type="expand")
    df[["adj_econ", "adj_bsr", "adj_dot"]] = adj_bowl

    # ── Step 3: Fielding modifier ────────────────────────────────────────────
    if not field_metrics.empty:
        field_mod = compute_fielding_modifiers(
            df[["raw_field_score"]].rename(columns={"raw_field_score": "raw_field_score"}),
            KEEPER_IDENTIFIERS
        )
        df["f"] = df.index.map(field_mod).fillna(FIELD_MID_MOD)
    else:
        df["f"] = FIELD_MID_MOD

    # ── Step 4: Player classification ───────────────────────────────────────
    df["player_type"] = df.apply(
        lambda r: classify_player(int(r.get("bat_innings", 0)),
                                  int(r.get("ipl_matches", 0))),
        axis=1
    )

    # ── Global maximums for bowling inversion ────────────────────────────────
    all_econ_vals = list(df["adj_econ"]) + list(df.get("ipl_economy", [0.0]))
    all_bsr_vals  = list(df["adj_bsr"])  + list(df.get("ipl_bowl_sr",  [0.0]))
    global_max_econ = max(all_econ_vals) if any(v > 0 for v in all_econ_vals) else 1.0
    global_max_bsr  = max(all_bsr_vals)  if any(v > 0 for v in all_bsr_vals)  else 1.0

    # ── Step 5 & 6: Raw form/aura scores (pre-normalisation) ─────────────────
    def _row_bat_form(r):
        return raw_bat_form(r["C"], r["adj_avg"], r["adj_sr"], r["adj_boundary"])

    def _row_bat_aura(r):
        return raw_bat_aura(r.get("ipl_avg", 0), r.get("ipl_sr", 0),
                             r.get("ipl_boundary_pct", 0))

    def _row_bowl_form(r):
        return raw_bowl_form(r["C"], r["adj_econ"], r["adj_bsr"], r["adj_dot"],
                              global_max_econ, global_max_bsr)

    def _row_bowl_aura(r):
        return raw_bowl_aura(r.get("ipl_economy", 0),
                              r.get("ipl_bowl_sr", 0),
                              r.get("ipl_dot_pct", 0),
                              global_max_econ, global_max_bsr)

    df["bat_form_raw"]  = df.apply(_row_bat_form,  axis=1)
    df["bat_aura_raw"]  = df.apply(_row_bat_aura,  axis=1)
    df["bowl_form_raw"] = df.apply(_row_bowl_form, axis=1)
    df["bowl_aura_raw"] = df.apply(_row_bowl_aura, axis=1)

    # ── Global normalisation ──────────────────────────────────────────────────
    # Batting pool: batters + keepers + allrounders
    bat_pool_mask  = df["role"].isin(["batter", "keeper", "allrounder"])
    # Bowling pool: bowlers + allrounders
    bowl_pool_mask = df["role"].isin(["bowler", "allrounder"])

    df["bat_form_norm"]  = normalise_global(df.loc[bat_pool_mask,  "bat_form_raw"])
    df["bat_aura_norm"]  = normalise_global(df.loc[bat_pool_mask,  "bat_aura_raw"])
    df["bowl_form_norm"] = normalise_global(df.loc[bowl_pool_mask, "bowl_form_raw"])
    df["bowl_aura_norm"] = normalise_global(df.loc[bowl_pool_mask, "bowl_aura_raw"])

    # Fill non-pool players with midpoint (so floor rules apply cleanly)
    for col in ["bat_form_norm", "bat_aura_norm"]:
        df[col] = df[col].fillna(NORM_MIDPOINT)
    for col in ["bowl_form_norm", "bowl_aura_norm"]:
        df[col] = df[col].fillna(NORM_MIDPOINT)

    # ── Step 5/6/7: Compute final scores per role ──────────────────────────
    bs_list, ws_list, ar_type_list, ar_bat_comp, ar_bowl_comp, ar_list = [], [], [], [], [], []

    for idx, row in df.iterrows():
        role     = row["role"]
        p_type   = row["player_type"]
        ipl_m    = int(row.get("ipl_matches", 0))
        f        = float(row["f"])
        bfn      = float(row["bat_form_norm"])
        ban      = float(row["bat_aura_norm"])
        wfn      = float(row["bowl_form_norm"])
        wan      = float(row["bowl_aura_norm"])

        if role in ("batter", "keeper"):
            bs = batter_score(p_type, ipl_m, bfn, ban, f)
            ws = bowler_score(p_type, ipl_m, wfn, wan, f)   # calculated but not used
            ar_t, bcomp, wcomp, _, ar = "N/A", bfn, 0.0, 0.0, 0.0

        elif role == "bowler":
            ws = bowler_score(p_type, ipl_m, wfn, wan, f)
            bs = batter_score(p_type, ipl_m, bfn, ban, f)   # calculated but not used
            ar_t, bcomp, wcomp, _, ar = "N/A", 0.0, wfn, 0.0, 0.0

        else:  # allrounder
            bs = batter_score(p_type, ipl_m, bfn, ban, f)
            ws = bowler_score(p_type, ipl_m, wfn, wan, f)
            ar_t, bcomp, wcomp, _, ar = allrounder_score(
                p_type, ipl_m, bfn, ban, wfn, wan, f)

        bs_list.append(bs)
        ws_list.append(ws)
        ar_type_list.append(ar_t)
        ar_bat_comp.append(bcomp)
        ar_bowl_comp.append(wcomp)
        ar_list.append(ar)

    df["batter_score"]    = bs_list
    df["bowler_score"]    = ws_list
    df["ar_type"]         = ar_type_list
    df["ar_bat_component"]= ar_bat_comp
    df["ar_bowl_component"]= ar_bowl_comp
    df["ar_score"]        = ar_list

    # ── Determine the "final_score" column per role ───────────────────────────
    def _final_score(row):
        role = row["role"]
        if role in ("batter", "keeper"):
            return row["batter_score"]
        if role == "bowler":
            return row["bowler_score"]
        return row["ar_score"]

    df["final_score"] = df.apply(_final_score, axis=1)

    df = df.reset_index()
    df = df.rename(columns={"identifier": "player_id"})
    return df
