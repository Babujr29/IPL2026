"""
run_pipeline.py — IPL 2026 Squad Strength Prediction System
============================================================
Orchestrates the full pipeline end-to-end:
  1. Load squad identity from people.csv
  2. Parse all YAML match files
  3. Compute batting / bowling / fielding metrics
  4. Compute IPL aura metrics
  5. Run the 8-step rating formula
  6. Aggregate into team scores
  7. Export JSON files for the website + save CSVs for the notebook
"""

import os
import sys
import time
import pandas as pd

# Ensure project root is on path when run directly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ipl_analytics.data_loader import load_squad_players, load_all_deliveries
from ipl_analytics.metrics import (
    compute_batting_metrics,
    compute_bowling_metrics,
    compute_fielding_metrics,
    compute_ipl_aura_metrics,
)
from ipl_analytics.formulas import compute_all_player_scores
from ipl_analytics.team_aggregation import compute_team_scores
from ipl_analytics.export import export_team_scores, export_player_scores, export_squad_data
from ipl_analytics.config import BASE_DIR


def main():
    t0 = time.time()
    print("=" * 60)
    print("  IPL 2026 Squad Strength Prediction — Pipeline Start")
    print("=" * 60)

    # ── Step 1: Load squad ──────────────────────────────────────────
    print("\n[1/7] Loading squad players from people.csv...")
    squad_df = load_squad_players()

    # ── Step 2: Parse YAML files ────────────────────────────────────
    print("\n[2/7] Parsing YAML match files...")
    form_df, ipl_df = load_all_deliveries(squad_df)

    # ── Step 3: Batting & bowling form metrics ──────────────────────
    print("\n[3/7] Computing form metrics (batting + bowling)...")
    bat_metrics  = compute_batting_metrics(form_df)
    bowl_metrics = compute_bowling_metrics(form_df)

    print(f"  Batting metrics rows  : {len(bat_metrics)}")
    print(f"  Bowling metrics rows  : {len(bowl_metrics)}")

    # ── Step 4: Fielding metrics ────────────────────────────────────
    print("\n[4/7] Computing fielding metrics...")
    # Fielding uses the form window data (same period)
    field_metrics = compute_fielding_metrics(form_df, squad_df)
    print(f"  Fielding metrics rows : {len(field_metrics)}")

    # ── Step 5: IPL aura metrics ────────────────────────────────────
    print("\n[5/7] Computing IPL aura metrics (last 3 seasons)...")
    ipl_metrics = compute_ipl_aura_metrics(ipl_df)
    print(f"  IPL aura metrics rows : {len(ipl_metrics)}")

    if ipl_metrics.empty:
        print("  [WARN] No IPL YAML files found - aura scores will default to 0.")
        print("     Drop IPL YAML files into the data/ folder and re-run.")

    # ── Step 6: Run rating formulas ─────────────────────────────────
    print("\n[6/7] Running player rating formulas (Steps 1–7)...")
    player_df = compute_all_player_scores(
        squad_df, bat_metrics, bowl_metrics, field_metrics, ipl_metrics
    )
    print(f"  Scored {len(player_df)} players")

    # ── Step 7: Team aggregation ────────────────────────────────────
    print("\n[7/7] Aggregating team scores...")
    team_df = compute_team_scores(player_df)

    # ── Print team rankings to console ─────────────────────────────
    print("\n" + "=" * 60)
    print("  TEAM RANKINGS")
    print("=" * 60)
    print(f"  {'Rank':<5} {'Team':<6} {'Bat':>6} {'Bowl':>6} {'AR':>6} {'Score':>7}")
    print("  " + "-" * 40)
    for _, row in team_df.iterrows():
        print(f"  {int(row['rank']):<5} {row['team']:<6} "
              f"{row['bat_avg']:>6.2f} {row['bowl_avg']:>6.2f} "
              f"{row['ar_avg']:>6.2f} {row['team_score']:>7.2f}")

    # ── Export JSON for website ─────────────────────────────────────
    print("\n[Export] Writing JSON data files...")
    export_team_scores(team_df)
    export_player_scores(player_df)
    export_squad_data(player_df)

    # ── Save CSVs for Jupyter Notebook ──────────────────────────────
    out_dir = os.path.join(BASE_DIR, "data_output")
    os.makedirs(out_dir, exist_ok=True)
    player_df.to_csv(os.path.join(out_dir, "player_scores.csv"), index=False)
    team_df.to_csv(os.path.join(out_dir, "team_scores.csv"),  index=False)
    print(f"  [Export] CSVs saved to {out_dir}/")

    elapsed = time.time() - t0
    print(f"[DONE] Pipeline complete in {elapsed:.1f}s")
    print("=" * 60)


if __name__ == "__main__":
    main()
