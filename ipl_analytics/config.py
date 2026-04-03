"""
config.py — Central configuration for IPL 2026 Squad Strength System
All constants, paths, and formula parameters live here.
"""

import os
from datetime import date

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YAML_DIR        = BASE_DIR                        # YAMLs sit at project root
PEOPLE_CSV      = os.path.join(BASE_DIR, "people.csv")
SQUAD_CSV       = os.path.join(BASE_DIR, "ipl2026_squads_name_team.csv")
WEBSITE_DATA    = os.path.join(BASE_DIR, "website", "data")

# ── Form window ──────────────────────────────────────────────────────────────
# Form counts from 2024 onwards
FORM_START_DATE = date(2024, 1, 1)

# ── IPL Aura ─────────────────────────────────────────────────────────────────
# Last 3 IPL seasons to include in aura calculation
IPL_AURA_SEASONS        = {2023, 2024, 2025}
IPL_COMPETITION_NAMES   = {"IPL", "Indian Premier League"}   # Cricsheet uses "IPL"

# ── Domestic competition name ────────────────────────────────────────────────
DOMESTIC_COMPETITION    = "Syed Mushtaq Ali Trophy"

# ── Opposition quality weights ───────────────────────────────────────────────
INTL_WEIGHT  = 1.2
DOM_WEIGHT   = 1.0

# ── Confidence multiplier ────────────────────────────────────────────────────
CONFIDENCE_INNINGS_CAP = 15   # C = min(innings / 15, 1)

# ── Fielding score tiers → modifier f ───────────────────────────────────────
FIELD_HIGH_THRESHOLD = 7.0    # ≥ 7.0 → f = +0.03
FIELD_MID_THRESHOLD  = 4.0    # ≥ 4.0 → f = 0.00
FIELD_HIGH_MOD = +0.03
FIELD_MID_MOD  =  0.00
FIELD_LOW_MOD  = -0.02

# ── Player type thresholds ───────────────────────────────────────────────────
IPL_LOW_EXP_MAX       = 4     # 1–4 matches = low experience
IPL_YOUNG_EST_MAX     = 15    # 5–15 matches = young established

# Discounts for low-experience / debutant
DISCOUNT_LOW_1_2      = 0.55  # ipl_matches ≤ 2
DISCOUNT_LOW_3_4      = 0.60  # ipl_matches 3–4
DISCOUNT_DEBUTANT     = 0.50  # ipl_matches == 0
DISCOUNT_INACTIVE     = 0.60  # inactive aura

FLOOR_DEBUTANT_LOW    = 2.5   # floor for debutant / low-exp
FLOOR_INACTIVE        = 3.0   # floor for inactive

# ── Form/Aura blending weights ───────────────────────────────────────────────
FW_YOUNG_EST  = 0.65; AW_YOUNG_EST  = 0.35
FW_ESTABLISHED = 0.55; AW_ESTABLISHED = 0.45

# ── Batting formula weights ──────────────────────────────────────────────────
BAT_AVG_W   = 0.40
BAT_SR_W    = 0.40
BAT_BDRY_W  = 0.20

# ── Bowling formula weights ──────────────────────────────────────────────────
BOWL_ECON_W  = 0.35
BOWL_BSR_W   = 0.35
BOWL_DOT_W   = 0.30

# ── All-rounder auto-classification thresholds ───────────────────────────────
AR_BAT_THRESH  = 0.55   # BatRatio > 0.55 → batting AR
AR_BOWL_THRESH = 0.45   # BatRatio < 0.45 → bowling AR

# α / β weights for each AR type
AR_BAT_WEIGHTS   = (0.60, 0.40)   # (α, β) for batting allrounder
AR_BOWL_WEIGHTS  = (0.40, 0.60)   # bowling allrounder
AR_BAL_WEIGHTS   = (0.50, 0.50)   # balanced allrounder

# ── Team aggregation weights ─────────────────────────────────────────────────
TEAM_BAT_W  = 0.33
TEAM_BOWL_W = 0.39
TEAM_AR_W   = 0.28

# ── Normalisation midpoint (used when all values are identical) ──────────────
NORM_MIDPOINT = 0.0   # 0 so that floor rules still dominate

# ── IPL teams ────────────────────────────────────────────────────────────────
IPL_TEAMS = ["CSK", "MI", "KKR", "RCB", "PBKS", "GT", "RR", "SRH", "LSG", "DC"]

# Franchise primary colours (for website accent)
TEAM_COLORS = {
    "CSK":  "#F9CD1C",
    "MI":   "#004BA0",
    "KKR":  "#3A225D",
    "RCB":  "#D1001C",
    "PBKS": "#ED1F27",
    "GT":   "#1C1C6E",
    "RR":   "#EA1A7F",
    "SRH":  "#F7A721",
    "LSG":  "#A0E00A",
    "DC":   "#0078BC",
}

# Full franchise names for display
TEAM_FULL_NAMES = {
    "CSK":  "Chennai Super Kings",
    "MI":   "Mumbai Indians",
    "KKR":  "Kolkata Knight Riders",
    "RCB":  "Royal Challengers Bengaluru",
    "PBKS": "Punjab Kings",
    "GT":   "Gujarat Titans",
    "RR":   "Rajasthan Royals",
    "SRH":  "Sunrisers Hyderabad",
    "LSG":  "Lucknow Super Giants",
    "DC":   "Delhi Capitals",
}

# ── Known keeper identifiers (cricsheet hex IDs from people.csv) ─────────────
# Players whose catches count in the KEEPER fielding pool (stumpings credited)
KEEPER_IDENTIFIERS = {
    "4a8a2e3b",  # MS Dhoni       CSK
    "a4cc73aa",  # Sanju Samson   CSK
    "cf59b3f0",  # Urvil Patel    CSK
    "372455c4",  # Quinton de Kock MI
    "e66732f8",  # Ryan Rickelton  MI
    "bafd0398",  # Robin Minz      MI
    "4663bd23",  # Tim Seifert     KKR
    "d7cdefa9",  # Sarthak Ranjan  KKR
    "800d2d97",  # Jitesh Sharma   RCB
    "3d284ca3",  # Phil Salt        RCB
    "ff154ecd",  # Jordan Cox       RCB
    "9418198b",  # Prabhsimran Singh PBKS
    "0494fa6e",  # Vishnu Vinod     PBKS
    "57ca01b3",  # Kumar Kushagra   GT
    "c8f5f961",  # Anuj Rawat       GT
    "99b75528",  # Jos Buttler      GT
    "bcf325d2",  # Dhruv Jurel      RR
    "235c2bb6",  # Heinrich Klaasen SRH
    "752f7486",  # Ishan Kishan     SRH
    "919a3be2",  # Rishabh Pant     LSG
    "989889ff",  # Josh Inglis      LSG
    "b17e2f24",  # KL Rahul         DC
    "ad3b6e95",  # Abishek Porel    DC
}

# Role codes in people.csv Type column
ROLE_CODES = {1: "batter", 2: "bowler", 3: "allrounder"}
