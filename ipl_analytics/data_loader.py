"""
data_loader.py — Load and parse all input data for IPL 2026 analytics.

Responsibilities:
  1. Load people.csv → player identity + cross-platform IDs
  2. Load ipl2026_squads_name_team.csv → squad membership
  3. Parse all YAML match files → raw delivery-level records
  4. Return structured DataFrames for metric computation
"""

import os
import glob
import yaml
import pandas as pd
import numpy as np
from datetime import date
from ipl_analytics.config import (
    YAML_DIR, PEOPLE_CSV, SQUAD_CSV,
    FORM_START_DATE, IPL_AURA_SEASONS, IPL_COMPETITION_NAMES,
    DOMESTIC_COMPETITION, ROLE_CODES, KEEPER_IDENTIFIERS, TEAM_COLORS,
    TEAM_FULL_NAMES, IPL_TEAMS
)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Load squad identity from people.csv
# ─────────────────────────────────────────────────────────────────────────────

def load_squad_players() -> pd.DataFrame:
    """
    Load people.csv which contains IPL 2026 squad members with their
    Cricsheet identifiers and cross-platform keys.

    Returns a DataFrame indexed by 'identifier' (8-char hex) with columns:
      player_name, team, role, key_cricinfo, identifier
    """
    df = pd.read_csv(PEOPLE_CSV, dtype=str)

    # Standardise column names (strip whitespace)
    df.columns = [c.strip() for c in df.columns]

    # Rename for easier access
    rename_map = {
        "Name":          "player_name_raw",
        "team":          "team",
        "Type":          "type_code",
        "identifier":    "identifier",
        "name":          "cricsheet_name",
        "unique_name":   "unique_name",
        "key_cricinfo":  "key_cricinfo",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    # Clean player name
    df["player_name"] = df["player_name_raw"].str.strip()

    # Map role
    df["type_code"] = pd.to_numeric(df["type_code"], errors="coerce").fillna(0).astype(int)
    df["role"] = df["type_code"].map(ROLE_CODES).fillna("allrounder")

    # Override role for keepers
    df.loc[df["identifier"].isin(KEEPER_IDENTIFIERS), "role"] = "keeper"

    # Sanitize cricinfo key
    df["key_cricinfo"] = df.get("key_cricinfo", pd.Series(["0"] * len(df)))
    df["key_cricinfo"] = df["key_cricinfo"].fillna("0").replace("0", "")

    # Keep only IPL team members
    df = df[df["team"].isin(IPL_TEAMS)].copy()
    df = df[df["identifier"].notna() & (df["identifier"] != "")].copy()
    df = df.drop_duplicates(subset="identifier")

    df = df.reset_index(drop=True)
    print(f"  [data_loader] Loaded {len(df)} squad players from people.csv")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# 2. Parse a single YAML match file
# ─────────────────────────────────────────────────────────────────────────────

def _classify_match(competition: str) -> str:
    """Return 'domestic' if SMA, else 'international'."""
    return "domestic" if competition == DOMESTIC_COMPETITION else "international"


def _parse_yaml_file(filepath: str) -> dict | None:
    """
    Parse one YAML file. Returns a dict with:
      meta, date, competition, match_type, registry, innings_data
    or None if the file should be skipped.
    """
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            data = yaml.safe_load(f)
    except Exception:
        return None

    if not data:
        return None

    info = data.get("info", {})
    match_type = info.get("match_type", "")
    if match_type != "T20":
        return None

    dates = info.get("dates", [])
    if not dates:
        return None
    try:
        match_date = date.fromisoformat(str(dates[0]))
    except Exception:
        return None

    competition = info.get("competition", "")  # may be absent → ""
    registry = info.get("registry", {}).get("people", {})

    return {
        "match_date":   match_date,
        "competition":  competition,
        "classification": _classify_match(competition),
        "registry":     registry,          # name → hex_id
        "innings":      data.get("innings", []),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3. Extract delivery records from one match
# ─────────────────────────────────────────────────────────────────────────────

def _extract_deliveries(parsed_match: dict, squad_ids: set) -> list[dict]:
    """
    Walk every delivery in the match and return a list of flat dicts.
    Only emit records where at least one participant (batsman, bowler, or
    fielder) is in the squad_ids set.
    """
    records = []
    registry = parsed_match["registry"]
    match_date   = parsed_match["match_date"]
    competition  = parsed_match["competition"]
    classif      = parsed_match["classification"]

    def resolve(name: str) -> str | None:
        """Map a Cricsheet name to hex identifier, return None if unknown."""
        if not name:
            return None
        raw = name.replace(" (sub)", "").strip()
        hex_id = registry.get(raw)
        return hex_id if hex_id else None

    innings_list = parsed_match["innings"]

    for inning_obj in innings_list:
        # Each element is like {"1st innings": {...}} or {"2nd innings": {...}}
        for inning_label, inning_data in inning_obj.items():
            batting_team = inning_data.get("team", "")
            deliveries   = inning_data.get("deliveries", [])

            for delivery_item in deliveries:
                for over_ball_key, ball in delivery_item.items():
                    if not isinstance(ball, dict):
                        continue

                    batsman_name     = ball.get("batsman", "")
                    non_striker_name = ball.get("non_striker", "")
                    bowler_name      = ball.get("bowler", "")

                    bat_id  = resolve(batsman_name)
                    bowler_id = resolve(bowler_name)

                    runs = ball.get("runs", {})
                    extras_info = ball.get("extras", {})

                    is_wide   = "wides"   in extras_info
                    is_noball = "noballs" in extras_info
                    is_bye    = "byes"    in extras_info
                    is_legbye = "legbyes" in extras_info

                    bat_runs    = runs.get("batsman", 0)
                    total_runs  = runs.get("total", 0)
                    extra_runs  = runs.get("extras", 0)
                    bye_runs    = extras_info.get("byes", 0)
                    legbye_runs = extras_info.get("legbyes", 0)

                    # Runs conceded by bowler = total minus byes and legbyes
                    bowler_conceded = total_runs - bye_runs - legbye_runs

                    # Cricsheet may use 'wicket' (dict) or 'wickets' (list)
                    wicket_info = ball.get("wickets", ball.get("wicket", {}))
                    if isinstance(wicket_info, list):
                        wicket_dict = wicket_info[0] if wicket_info else {}
                    else:
                        wicket_dict = wicket_info

                    player_out    = wicket_dict.get("player_out", "")
                    wicket_kind   = wicket_dict.get("kind", "")
                    fielder_names = wicket_dict.get("fielders", [])

                    # Resolve fielders (strip sub suffix)
                    fielder_ids = [
                        resolve(fn) for fn in fielder_names
                        if resolve(fn) is not None
                    ]

                    player_out_id = resolve(player_out)

                    rec = {
                        "match_date":       match_date,
                        "competition":      competition,
                        "classification":   classif,
                        "inning":           inning_label,
                        "batting_team":     batting_team,
                        # Participants
                        "bat_id":           bat_id,
                        "bowler_id":        bowler_id,
                        "player_out_id":    player_out_id,
                        "fielder_ids":      fielder_ids,   # list
                        # Ball type flags
                        "is_wide":          is_wide,
                        "is_noball":        is_noball,
                        # Runs
                        "bat_runs":         bat_runs,
                        "total_runs":       total_runs,
                        "bowler_conceded":  bowler_conceded,
                        # Dismissal
                        "wicket_kind":      wicket_kind,
                    }
                    records.append(rec)
    return records


# ─────────────────────────────────────────────────────────────────────────────
# 4. Parse ALL YAML files → two DataFrames (form window, IPL aura)
# ─────────────────────────────────────────────────────────────────────────────

def load_all_deliveries(squad_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Parse every YAML in YAML_DIR and split deliveries into:
      - form_df:  matches on/after FORM_START_DATE (T20, any competition)
      - ipl_df:   IPL matches in IPL_AURA_SEASONS

    squad_df must have column 'identifier' so we can filter relevant records.
    Returns (form_df, ipl_df).
    """
    squad_ids = set(squad_df["identifier"].dropna().tolist())

    all_yaml_files = glob.glob(os.path.join(YAML_DIR, "*.yaml"))

    # ── Filter: only parse files with match ID >= 1324624 ─────────────────
    # Filenames are numeric match IDs in ascending order (smaller = older).
    # Files below this cutoff are too old to be relevant for form or aura.
    MIN_MATCH_ID = 1324624
    yaml_files = []
    for p in all_yaml_files:
        stem = os.path.splitext(os.path.basename(p))[0]
        try:
            if int(stem) >= MIN_MATCH_ID:
                yaml_files.append(p)
        except ValueError:
            pass  # non-numeric filename — skip

    print(f"  [data_loader] Found {len(all_yaml_files)} total YAML files.")
    print(f"  [data_loader] Parsing {len(yaml_files)} files (match ID >= {MIN_MATCH_ID})...")

    form_records = []
    ipl_records  = []
    processed    = 0

    for path in yaml_files:
        parsed = _parse_yaml_file(path)
        if parsed is None:
            continue

        processed += 1
        mdate = parsed["match_date"]
        comp  = parsed["competition"]

        is_form_window = (mdate >= FORM_START_DATE)
        is_ipl_aura    = (comp in IPL_COMPETITION_NAMES and
                          mdate.year in IPL_AURA_SEASONS)

        if not (is_form_window or is_ipl_aura):
            continue   # fast-skip matches we don't need

        deliveries = _extract_deliveries(parsed, squad_ids)

        if is_form_window:
            form_records.extend(deliveries)
        if is_ipl_aura:
            ipl_records.extend(deliveries)

    print(f"  [data_loader] Parsed {processed} valid T20 files.")
    print(f"  [data_loader] Form-window deliveries : {len(form_records)}")
    print(f"  [data_loader] IPL-aura   deliveries  : {len(ipl_records)}")

    # Build DataFrames
    form_df = pd.DataFrame(form_records) if form_records else _empty_delivery_df()
    ipl_df  = pd.DataFrame(ipl_records)  if ipl_records  else _empty_delivery_df()

    return form_df, ipl_df


def _empty_delivery_df() -> pd.DataFrame:
    """Return an empty DataFrame with the expected delivery schema."""
    return pd.DataFrame(columns=[
        "match_date", "competition", "classification", "inning",
        "batting_team", "bat_id", "bowler_id", "player_out_id",
        "fielder_ids", "is_wide", "is_noball",
        "bat_runs", "total_runs", "bowler_conceded", "wicket_kind",
    ])
