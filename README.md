# 🏏 IPL 2026 Squad Strength Prediction System

> **Analysis by SHIVAM** · Data-driven team & player ratings for IPL 2026 built entirely from ball-by-ball Cricsheet data.

---

## 📌 What Is This?

This project is a **sports analytics engine** that quantifies the strength of all 10 IPL 2026 franchises using a custom rating formula applied to real match data. It produces:

- A **ranked leaderboard** of all 10 IPL teams by squad strength
- Individual **player scores** for every squad member (216 players)
- An interactive **website** with team pages, player comparisons, and a chatbot
- A **Jupyter Notebook** with styled analytical tables

Everything is powered by ball-by-ball YAML data from [Cricsheet.org](https://cricsheet.org) — no third-party APIs, no subscriptions.

---

## 🏆 Current Rankings (as of latest pipeline run)

| Rank | Team | Overall Score |
|------|------|--------------|
| 🥇 1 | Rajasthan Royals | 6.26 |
| 🥈 2 | Royal Challengers Bengaluru | 5.81 |
| 🥉 3 | Punjab Kings | 5.77 |
| 4 | Delhi Capitals | 5.76 |
| 5 | Sunrisers Hyderabad | 5.47 |
| 6 | Mumbai Indians | 5.46 |
| 7 | Chennai Super Kings | 5.35 |
| 8 | Kolkata Knight Riders | 5.31 |
| 9 | Gujarat Titans | 5.30 |
| 10 | Lucknow Super Giants | 5.05 |

> Scores are on a normalised 0–10 scale. Scores update every time the pipeline is re-run against fresh data.

---

## ⚙️ How the Rating Formula Works

Each player receives a **Final Score (0–10)** built from two components:

### 1. Form Score
Computed from all T20 matches played from **January 2024 onwards** (including IPL 2026).

**Batting metrics** — Average (40%) · Strike Rate (40%) · Boundary % (20%)  
**Bowling metrics** — Economy (35%) · Bowling Strike Rate (35%) · Dot Ball % (30%)

### 2. Aura Score
Computed from **IPL seasons 2024, 2025, 2026** — capturing a player's track record at the highest domestic T20 level.

### 3. Blending (by Player Classification)

| Classification | Form Weight | Aura Weight |
|---|---|---|
| Established (>15 IPL matches) | 55% | 45% |
| Young Established (5–15 matches) | 65% | 35% |
| Low Experience (1–4 matches) | Discounted aura | — |
| Debutant (0 IPL matches) | Floor score | — |
| Inactive (no recent form) | Floor score (3.0) | — |

A **Fielding Modifier (f)** adjusts the final score: +0.03 for top fielders, −0.02 for poor fielders, based on catches/run-outs relative to peers.

### 4. Team Score
```
TeamScore = 0.33 × BatAvg + 0.39 × BowlAvg + 0.28 × ARAvg
```
Bowling is weighted highest (0.39) reflecting its greater match-winning impact in T20 cricket.

---

## 📁 Project Structure

```
IPL 2026/
│
├── data/                        # Raw Cricsheet YAML match files (7300+ files)
├── docs/                        # The live website (open index.html in browser)
│   ├── index.html               # Home — Team Rankings
│   ├── leaderboards.html        # Player Leaderboards (Bat / Bowl / AR tabs)
│   ├── compare.html             # Head-to-head Player Comparison
│   ├── team.html                # Team Deep Dive (gauges, squad table)
│   ├── fantasy.html             # Fantasy XI helper
│   ├── app.js                   # Shared data loader & UI utilities
│   ├── babujr.js                # Offline AI chatbot (rule-based, no API key)
│   ├── style.css                # Full dark-theme CSS (glassmorphism)
│   └── data/                   # ← Pipeline writes JSON here
│       ├── team_scores.json
│       ├── player_scores.json
│       └── squad_data.json
│
├── ipl_analytics/               # Python analytics engine
│   ├── config.py                # All constants, paths, formula weights
│   ├── data_loader.py           # YAML parser → delivery-level DataFrame
│   ├── metrics.py               # Batting / bowling / fielding metric computation
│   ├── formulas.py              # 8-step rating formula for every player
│   ├── team_aggregation.py      # Aggregate player scores → team scores
│   └── export.py                # Write JSON files to docs/data/
│
├── run_pipeline.py              # ← Run this to refresh all scores
├── generate_notebook.py         # Generates ipl_2026_analysis.ipynb
├── ipl_2026_analysis.ipynb      # Jupyter Notebook with styled tables
│
├── people.csv                   # Squad list — player names, teams, Cricsheet IDs
├── ipl2026_squads_name_team.csv # IPL 2026 squad assignments
└── requirements.txt             # Python dependencies
```

---

## 🚀 How to Run It

### Prerequisites
```bash
pip install -r requirements.txt
```

### Step 1 — Add match data
Place Cricsheet YAML files into the `data/` folder.  
Download from: https://cricsheet.org/downloads/

### Step 2 — Run the pipeline
```bash
python run_pipeline.py
```

This will:
1. Load 216 squad players from `people.csv`
2. Parse all YAML files (only match IDs ≥ 1324624 for performance)
3. Compute batting, bowling, and fielding metrics
4. Compute IPL aura metrics (2024–2026 seasons)
5. Apply the 8-step rating formula to every player
6. Aggregate into team scores
7. Export 3 JSON files to `docs/data/`

### Step 3 — View the website
Open `docs/index.html` in any modern browser and **refresh** to see updated scores.

### Step 4 — (Optional) Generate the Jupyter Notebook
```bash
python generate_notebook.py
jupyter notebook ipl_2026_analysis.ipynb
```

---

## 🌐 Website Features

| Page | What It Shows |
|------|--------------|
| **Home** (`index.html`) | All 10 teams ranked by overall strength with sortable columns and strength bars |
| **Leaderboards** (`leaderboards.html`) | Top 30 batters, bowlers, and all-rounders with filters by team and player type |
| **Compare** (`compare.html`) | Select any two players for a side-by-side stat breakdown and radar chart |
| **Team** (`team.html?team=XX`) | Full squad breakdown — animated gauges, top-3 cards, full squad table |
| **Fantasy** (`fantasy.html`) | Fantasy XI builder based on squad strength scores |

**BABUJR Chatbot** — Click the gold cricket-ball button (bottom-right) to ask questions like:
- *"Which team has the strongest batting?"*
- *"Who is the best all-rounder?"*
- *"Compare RR and RCB"*
- *"Top 3 bowlers?"*

No API key required — the chatbot runs entirely offline using the same JSON data as the website.

---

## 📊 Data Sources

| Source | What It Provides |
|--------|-----------------|
| [Cricsheet.org](https://cricsheet.org) | Ball-by-ball YAML match files (T20) |
| `people.csv` | Player identities, Cricsheet hex IDs, team assignments |
| `ipl2026_squads_name_team.csv` | IPL 2026 official squad lists |

> **Performance note:** The pipeline skips match files with IDs below 1,324,624 (pre-2022 matches). This cuts parsing time by ~60% while retaining all relevant form and aura data.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Analytics Engine | Python (pandas, PyYAML, numpy) |
| Notebook | Jupyter + nbformat |
| Website | Vanilla HTML / CSS / JavaScript — no frameworks |
| Fonts | Google Fonts (Rajdhani + Inter) |
| Charts | Pure Canvas API (radar chart) |
| Chatbot | Rule-based JS pattern matcher |

---

## 📄 Formula Reference Files

- `main.md` — Complete formula specification, all weights and classification rules
- `OUTPUT.md` — Output schema definitions for all 3 JSON files
- `RAW.md` — Raw data field reference for Cricsheet YAML parsing

---

*Built by **Babujr29** | Analysis by SHIVAM*
