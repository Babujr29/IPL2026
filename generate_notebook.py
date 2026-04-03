"""
generate_notebook.py — Creates ipl_2026_analysis.ipynb from CSV output.
Run AFTER run_pipeline.py has completed.
"""

import os
import json
import nbformat as nbf
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR  = os.path.join(BASE_DIR, "data_output")
NB_PATH  = os.path.join(BASE_DIR, "ipl_2026_analysis.ipynb")

nb = nbf.v4.new_notebook()
cells = []

def md(text): return nbf.v4.new_markdown_cell(text)
def code(src): return nbf.v4.new_code_cell(src)

# ── Title ─────────────────────────────────────────────────────────────────
cells.append(md("""# IPL 2026 Squad Strength Prediction System
## Analysis by SHIVAM

> **Data source**: Cricsheet YAML match files (T20) · Form window: 2024 onwards · Aura: last 3 IPL seasons
>
> **Formula**: BABUJR Analytics — Form + Aura blended by player classification, normalised globally, aggregated as
> `TeamScore = 0.33×BatAvg + 0.39×BowlAvg + 0.28×ARAvg`

---
"""))

# ── Setup ─────────────────────────────────────────────────────────────────
cells.append(code("""\
import pandas as pd, numpy as np, os

OUT_DIR = r'""" + OUT_DIR.replace("\\", "\\\\") + r"""'

team_df   = pd.read_csv(os.path.join(OUT_DIR, 'team_scores.csv'))
player_df = pd.read_csv(os.path.join(OUT_DIR, 'player_scores.csv'))

print(f"Teams  : {len(team_df)}")
print(f"Players: {len(player_df)}")
"""))

# ── Section 1 — Team Rankings ─────────────────────────────────────────────
cells.append(md("---\n## Section 1 — Team Strength Overview\n\n`TeamScore = 0.33 × Bat + 0.39 × Bowl + 0.28 × AR`"))

cells.append(code("""\
cols = ['rank','team','bat_avg','bowl_avg','ar_avg','team_score']
display_team = team_df[cols].copy()
display_team.columns = ['Rank','Team','Batting','Bowling','All-rounders','Overall']

def colour_rank(val):
    colors = {1:'background:#FFD70033', 2:'background:#C0C0C033', 3:'background:#CD7F3233'}
    return colors.get(val, '')

styled = (
    display_team.style
    .format({'Batting':'{:.2f}','Bowling':'{:.2f}','All-rounders':'{:.2f}','Overall':'{:.2f}'})
    .applymap(colour_rank, subset=['Rank'])
    .background_gradient(subset=['Batting','Bowling','All-rounders','Overall'],
                         cmap='YlOrRd', axis=0)
    .set_table_styles([
        {'selector':'th','props':[('background','#1a1a3e'),('color','gold'),
                                   ('font-family','Rajdhani,sans-serif'),('font-size','13px')]},
        {'selector':'td','props':[('font-size','12px')]},
    ])
    .set_caption('IPL 2026 Squad Strength Rankings')
    .hide(axis='index')
)
styled
"""))

# ── Section 2 — Top Batters ────────────────────────────────────────────────
cells.append(md("---\n## Section 2 — Top 20 Batters"))

cells.append(code("""\
batters = player_df[player_df['role'].isin(['batter','keeper'])].copy()
batters = batters.nlargest(20, 'batter_score')
bat_display = batters[['player_name','team','player_type','bat_form_norm','bat_aura_norm','batter_score']].copy()
bat_display.columns = ['Player','Team','Type','Form Score','Aura Score','Batter Score']

(bat_display.style
    .format({'Form Score':'{:.2f}','Aura Score':'{:.2f}','Batter Score':'{:.2f}'})
    .background_gradient(subset=['Batter Score'], cmap='Greens')
    .set_caption('Top 20 Batters — IPL 2026')
    .hide(axis='index'))
"""))

# ── Section 3 — Top Bowlers ────────────────────────────────────────────────
cells.append(md("---\n## Section 3 — Top 20 Bowlers"))

cells.append(code("""\
bowlers = player_df[player_df['role']=='bowler'].copy()
bowlers = bowlers.nlargest(20, 'bowler_score')
bowl_display = bowlers[['player_name','team','player_type','bowl_form_norm','bowl_aura_norm','bowler_score']].copy()
bowl_display.columns = ['Player','Team','Type','Form Score','Aura Score','Bowler Score']

(bowl_display.style
    .format({'Form Score':'{:.2f}','Aura Score':'{:.2f}','Bowler Score':'{:.2f}'})
    .background_gradient(subset=['Bowler Score'], cmap='Blues')
    .set_caption('Top 20 Bowlers — IPL 2026')
    .hide(axis='index'))
"""))

# ── Section 4 — Top All-rounders ───────────────────────────────────────────
cells.append(md("---\n## Section 4 — Top 20 All-rounders"))

cells.append(code("""\
ars = player_df[player_df['role']=='allrounder'].copy()
ars = ars.nlargest(20, 'ar_score')
ar_display = ars[['player_name','team','ar_type','ar_bat_component','ar_bowl_component','ar_score']].copy()
ar_display.columns = ['Player','Team','AR Type','Bat Component','Bowl Component','AR Score']

(ar_display.style
    .format({'Bat Component':'{:.2f}','Bowl Component':'{:.2f}','AR Score':'{:.2f}'})
    .background_gradient(subset=['AR Score'], cmap='Purples')
    .set_caption('Top 20 All-rounders — IPL 2026')
    .hide(axis='index'))
"""))

# ── Section 5 — Per-team tables ────────────────────────────────────────────
cells.append(md("---\n## Section 5 — Team Squads Breakdown"))

cells.append(code("""\
teams = team_df['team'].tolist()
for team in teams:
    tdf = player_df[player_df['team']==team].copy()
    tdf = tdf.sort_values('final_score', ascending=False)
    cols = ['player_name','role','player_type','bat_form_norm','bowl_form_norm','final_score']
    disp = tdf[cols].copy()
    disp.columns = ['Player','Role','Type','Bat Form','Bowl Form','Final Score']
    rank = team_df.loc[team_df['team']==team,'rank'].values[0]
    ts   = team_df.loc[team_df['team']==team,'team_score'].values[0]
    print(f"\\n{'='*60}")
    print(f"  {team} — Rank #{int(rank)} — TeamScore: {ts:.2f}")
    print('='*60)
    styled = (
        disp.style
        .format({'Bat Form':'{:.2f}','Bowl Form':'{:.2f}','Final Score':'{:.2f}'})
        .background_gradient(subset=['Final Score'], cmap='YlOrRd')
        .set_caption(f'{team} — Full Squad')
        .hide(axis='index')
    )
    display(styled)
"""))

nb.cells = cells
with open(NB_PATH, 'w', encoding='utf-8') as f:
    nbf.write(nb, f)

print(f"✓ Notebook written to {NB_PATH}")
print("  Open with: jupyter notebook ipl_2026_analysis.ipynb")
