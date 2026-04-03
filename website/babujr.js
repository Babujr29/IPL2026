/**
 * babujr.js — BABUJR Offline Cricket Analyst Chatbot
 *
 * Fully rule-based — no API key needed.
 * Answers are generated dynamically from the loaded JSON data.
 */

(function () {
  'use strict';

  let DATA = { teams: [], players: [], squads: {} };
  let panelOpen = false;
  let conversationHistory = [];

  const STARTER_QUESTIONS = [
    "Which team has the strongest squad?",
    "Who is the best all-rounder?",
    "Compare MI and CSK",
    "Top 3 bowlers this season?",
  ];

  // ── Team abbreviation aliases ──────────────────────────────────────────
  const TEAM_ALIASES = {
    'csk':'CSK','chennai':'CSK','super kings':'CSK',
    'mi':'MI','mumbai':'MI','mumbai indians':'MI',
    'kkr':'KKR','kolkata':'KKR','knight riders':'KKR',
    'rcb':'RCB','bangalore':'RCB','bengaluru':'RCB','royal challengers':'RCB',
    'pbks':'PBKS','punjab':'PBKS','punjab kings':'PBKS',
    'gt':'GT','gujarat':'GT','gujarat titans':'GT',
    'rr':'RR','rajasthan':'RR','rajasthan royals':'RR',
    'srh':'SRH','hyderabad':'SRH','sunrisers':'SRH',
    'lsg':'LSG','lucknow':'LSG','lucknow super giants':'LSG',
    'dc':'DC','delhi':'DC','delhi capitals':'DC',
  };

  function resolveTeam(text) {
    const t = text.toLowerCase();
    for (const [alias, code] of Object.entries(TEAM_ALIASES)) {
      if (t.includes(alias)) return code;
    }
    return null;
  }

  function resolvePlayer(text) {
    const lower = text.toLowerCase();
    return DATA.players.find(p => lower.includes(p.player_name.toLowerCase().split(' ').pop()) ||
                                   lower.includes(p.player_name.toLowerCase()));
  }

  function scoreKey(p) {
    if (p.role === 'bowler')    return 'bowler_score';
    if (p.role === 'allrounder') return 'ar_score';
    return 'batter_score';
  }

  function fmt(v) { return (+v || 0).toFixed(2); }

  function ordinal(n) {
    const s = ['th','st','nd','rd'];
    const v = n % 100;
    return n + (s[(v - 20) % 10] || s[v] || s[0]);
  }

  // ── Answer Engine ──────────────────────────────────────────────────────
  function answer(raw) {
    const q = raw.toLowerCase().trim();

    // ── Team rankings ──────────────────────────────────────────────────
    if (/\b(strongest|best|top|rank|strongest|powerful|overall)\b.*team/.test(q) ||
        /team.*\b(rank|strong|best|powerful|overall)\b/.test(q) ||
        /which team.*wins|who.*win(s)? ipl/.test(q)) {
      const sorted = [...DATA.teams].sort((a,b) => b.team_score - a.team_score);
      const top3 = sorted.slice(0,3).map((t,i) =>
        `${['🥇','🥈','🥉'][i]} **${t.full_name||t.team}** — ${fmt(t.team_score)}`
      ).join('\n');
      return `Based on the Squad Strength Index, here are the top 3:\n${top3}\n\n${sorted[0].full_name||sorted[0].team} leads the pack! 💪`;
    }

    // ── Batting strength ───────────────────────────────────────────────
    if (/best.*batting|batting.*best|strongest.*bat|bat.*strength|batting attack/.test(q)) {
      const sorted = [...DATA.teams].sort((a,b) => b.bat_avg - a.bat_avg);
      const top3 = sorted.slice(0,3).map((t,i) =>
        `${['🥇','🥈','🥉'][i]} ${t.team} — ${fmt(t.bat_avg)}`
      ).join('\n');
      return `Best batting units this season:\n${top3}`;
    }

    // ── Bowling strength ───────────────────────────────────────────────
    if (/best.*bowl|bowl.*best|strongest.*bowl|bowl.*strength|bowling attack/.test(q)) {
      const sorted = [...DATA.teams].sort((a,b) => b.bowl_avg - a.bowl_avg);
      const top3 = sorted.slice(0,3).map((t,i) =>
        `${['🥇','🥈','🥉'][i]} ${t.team} — ${fmt(t.bowl_avg)}`
      ).join('\n');
      return `Strongest bowling attacks:\n${top3}`;
    }

    // ── All-rounder strength ───────────────────────────────────────────
    if (/best.*all.?round|all.?round.*best|ar.*strength/.test(q)) {
      const sorted = [...DATA.teams].sort((a,b) => b.ar_avg - a.ar_avg);
      const top3 = sorted.slice(0,3).map((t,i) =>
        `${['🥇','🥈','🥉'][i]} ${t.team} — ${fmt(t.ar_avg)}`
      ).join('\n');
      return `Teams with the best all-rounder depth:\n${top3}`;
    }

    // ── Worst team ─────────────────────────────────────────────────────
    if (/weak|worst|bottom|last|poor/.test(q) && /team/.test(q)) {
      const sorted = [...DATA.teams].sort((a,b) => a.team_score - b.team_score);
      const t = sorted[0];
      return `The lowest-ranked team right now is **${t.full_name||t.team}** with an overall score of ${fmt(t.team_score)}. But hey, fortunes change fast in the IPL! 🏏`;
    }

    // ── Full rankings ──────────────────────────────────────────────────
    if (/all.*team.*rank|rank.*all|full.*ranking|show.*ranking/.test(q)) {
      const sorted = [...DATA.teams].sort((a,b) => b.team_score - a.team_score);
      return 'Full IPL 2026 Squad Strength Rankings:\n' +
        sorted.map(t => `#${t.rank} ${t.team} — ${fmt(t.team_score)}`).join('\n');
    }

    // ── Two-team comparison ────────────────────────────────────────────
    const compareMatch = q.match(/compare\s+(\w+)\s+(?:and|vs|versus)\s+(\w+)/) ||
                         q.match(/(\w+)\s+vs\s+(\w+)/);
    if (compareMatch) {
      const t1 = resolveTeam(compareMatch[1]);
      const t2 = resolveTeam(compareMatch[2]);
      if (t1 && t2) {
        const d1 = DATA.teams.find(t => t.team === t1);
        const d2 = DATA.teams.find(t => t.team === t2);
        if (d1 && d2) {
          const wins = [
            +d1.bat_avg  > +d2.bat_avg  ? t1 : t2,
            +d1.bowl_avg > +d2.bowl_avg ? t1 : t2,
            +d1.ar_avg   > +d2.ar_avg   ? t1 : t2,
          ];
          const overall = +d1.team_score >= +d2.team_score ? t1 : t2;
          return `**${t1} vs ${t2}** Head-to-Head:\n` +
            `🏏 Batting:     ${t1} ${fmt(d1.bat_avg)} vs ${t2} ${fmt(d2.bat_avg)} → **${wins[0]}**\n` +
            `🎳 Bowling:     ${t1} ${fmt(d1.bowl_avg)} vs ${t2} ${fmt(d2.bowl_avg)} → **${wins[1]}**\n` +
            `⚡ All-rounders: ${t1} ${fmt(d1.ar_avg)} vs ${t2} ${fmt(d2.ar_avg)} → **${wins[2]}**\n` +
            `🏆 Overall:     ${t1} ${fmt(d1.team_score)} vs ${t2} ${fmt(d2.team_score)} → **${overall} wins!**`;
        }
      }
    }

    // ── Top N batters ──────────────────────────────────────────────────
    const batMatch = q.match(/top\s*(\d+)?\s*(batter|bat)/);
    if (batMatch) {
      const n = Math.min(+(batMatch[1]||3), 10);
      const top = [...DATA.players]
        .filter(p => ['batter','keeper'].includes(p.role))
        .sort((a,b) => b.batter_score - a.batter_score).slice(0, n);
      return `Top ${n} Batters:\n` +
        top.map((p,i) => `${ordinal(i+1)} ${p.player_name} (${p.team}) — ${fmt(p.batter_score)}`).join('\n');
    }

    // ── Top N bowlers ──────────────────────────────────────────────────
    const bowlMatch = q.match(/top\s*(\d+)?\s*(bowler|bowl)/);
    if (bowlMatch) {
      const n = Math.min(+(bowlMatch[1]||3), 10);
      const top = [...DATA.players]
        .filter(p => p.role === 'bowler')
        .sort((a,b) => b.bowler_score - a.bowler_score).slice(0, n);
      return `Top ${n} Bowlers:\n` +
        top.map((p,i) => `${ordinal(i+1)} ${p.player_name} (${p.team}) — ${fmt(p.bowler_score)}`).join('\n');
    }

    // ── Top N all-rounders ─────────────────────────────────────────────
    const arMatch = q.match(/top\s*(\d+)?\s*all.?round/);
    if (arMatch || /best all.?round/.test(q)) {
      const n = Math.min(+(arMatch && arMatch[1] || 3), 10);
      const top = [...DATA.players]
        .filter(p => p.role === 'allrounder')
        .sort((a,b) => b.ar_score - a.ar_score).slice(0, n);
      return `Top ${n} All-rounders:\n` +
        top.map((p,i) => `${ordinal(i+1)} ${p.player_name} (${p.team}, ${p.ar_type||'balanced'}) — ${fmt(p.ar_score)}`).join('\n');
    }

    // ── Team-specific squad query ──────────────────────────────────────
    const teamCode = resolveTeam(q);
    if (teamCode) {
      const teamD   = DATA.teams.find(t => t.team === teamCode);
      const members = DATA.players.filter(p => p.team === teamCode);

      // "best batter in [team]"
      if (/bat/.test(q)) {
        const top = members.filter(p=>['batter','keeper'].includes(p.role))
          .sort((a,b)=>b.batter_score-a.batter_score).slice(0,3);
        return `${teamCode}'s top batters:\n` +
          top.map((p,i)=>`${ordinal(i+1)} ${p.player_name} — ${fmt(p.batter_score)}`).join('\n');
      }
      // "best bowler in [team]"
      if (/bowl/.test(q)) {
        const top = members.filter(p=>p.role==='bowler')
          .sort((a,b)=>b.bowler_score-a.bowler_score).slice(0,3);
        return `${teamCode}'s top bowlers:\n` +
          top.map((p,i)=>`${ordinal(i+1)} ${p.player_name} — ${fmt(p.bowler_score)}`).join('\n');
      }
      // "all-rounders in [team]"
      if (/all.?round/.test(q)) {
        const top = members.filter(p=>p.role==='allrounder')
          .sort((a,b)=>b.ar_score-a.ar_score).slice(0,3);
        return `${teamCode}'s all-rounders:\n` +
          (top.length ? top.map((p,i)=>`${ordinal(i+1)} ${p.player_name} (${p.ar_type}) — ${fmt(p.ar_score)}`).join('\n')
                      : 'No pure all-rounders found.');
      }
      // General team query
      if (teamD) {
        const best = [...members].sort((a,b)=>b.final_score-a.final_score)[0];
        return `**${teamD.full_name||teamCode}**\n` +
          `📊 Rank: #${teamD.rank}\n` +
          `🏏 Batting: ${fmt(teamD.bat_avg)}\n` +
          `🎳 Bowling: ${fmt(teamD.bowl_avg)}\n` +
          `⚡ All-rounders: ${fmt(teamD.ar_avg)}\n` +
          `🏆 Overall: ${fmt(teamD.team_score)}\n` +
          (best ? `⭐ Key player: ${best.player_name} (${fmt(best.final_score)})` : '');
      }
    }

    // ── Individual player query ────────────────────────────────────────
    const player = resolvePlayer(q);
    if (player) {
      const sk = scoreKey(player);
      const formScore = player.role==='bowler' ? player.bowl_form_norm : player.bat_form_norm;
      const auraScore = player.role==='bowler' ? player.bowl_aura_norm : player.bat_aura_norm;
      const teamD = DATA.teams.find(t => t.team === player.team);

      // Just aura
      if (/aura/.test(q)) return `${player.player_name}'s Aura Score: **${fmt(auraScore)}** (last 3 IPL seasons).`;
      // Just form
      if (/form/.test(q)) return `${player.player_name}'s Form Score: **${fmt(formScore)}** (post-IPL 2025).`;
      // Just score/rating
      return `**${player.player_name}** (${player.team})\n` +
        `Role: ${player.role} · Type: ${player.player_type}` +
        (player.ar_type && player.ar_type!=='N/A' ? ` · AR: ${player.ar_type}` : '') + '\n' +
        `📈 Form Score:  ${fmt(formScore)}\n` +
        `📚 Aura Score:  ${fmt(auraScore)}\n` +
        `🏆 Final Score: **${fmt(+player[sk]||0)}**\n` +
        (teamD ? `Team rank: #${teamD.rank}` : '');
    }

    // ── Established players ────────────────────────────────────────────
    if (/established/.test(q)) {
      const top = [...DATA.players].filter(p=>p.player_type==='established')
        .sort((a,b)=>b.final_score-a.final_score).slice(0,5);
      return `Top established players:\n` +
        top.map((p,i)=>`${ordinal(i+1)} ${p.player_name} (${p.team}) — ${fmt(p.final_score)}`).join('\n');
    }

    // ── Debutants / young players ──────────────────────────────────────
    if (/debut|newcomer|young|new player/.test(q)) {
      const top = [...DATA.players]
        .filter(p=>p.player_type==='debutant'||p.player_type==='young_established')
        .sort((a,b)=>b.final_score-a.final_score).slice(0,5);
      return `Exciting debutants & young guns:\n` +
        top.map((p,i)=>`${ordinal(i+1)} ${p.player_name} (${p.team}, ${p.player_type}) — ${fmt(p.final_score)}`).join('\n');
    }

    // ── Inactive players ───────────────────────────────────────────────
    if (/inactive|no form|rusty/.test(q)) {
      const top = [...DATA.players].filter(p=>p.player_type==='inactive')
        .sort((a,b)=>b.final_score-a.final_score).slice(0,5);
      return `Players classified as inactive (no recent T20 form since start of 2024):\n` +
        top.map((p,i)=>`${ordinal(i+1)} ${p.player_name} (${p.team})`).join('\n');
    }

    // ── Scoring system explanation ─────────────────────────────────────
    if (/how.*scor|formula|calcul|rating|system|methodology|how.*work/.test(q)) {
      return `The Squad Strength Index uses a two-component system:\n` +
        `📈 **FORM** — T20 performances from 2024 onwards\n` +
        `📚 **AURA** — Last 3 IPL seasons career stats\n\n` +
        `Metrics: Batting avg, Strike rate, Boundary % · Economy, Bowl SR, Dot %\n` +
        `Opposition quality weights: International 1.2× · Domestic 1.0×\n` +
        `TeamScore = 33% Batting + 39% Bowling + 28% All-rounders\n` +
        `All scores normalised to a 0–10 scale.`;
    }

    // ── Fun / general ──────────────────────────────────────────────────
    if (/hello|hi|hey|sup|what.*up|namaste/.test(q)) {
      return `Hey! 🏏 I'm BABUJR, your IPL 2026 analyst. Ask me about team rankings, player stats, comparisons — I've got all the numbers! What do you want to know?`;
    }
    if (/who are you|what (are|can) you/.test(q)) {
      return `I'm BABUJR — your dedicated IPL 2026 Squad Strength analyst. I can tell you:\n• Team rankings (overall, batting, bowling, AR)\n• Top player lists by role\n• Any player's scores\n• Head-to-head team comparisons\n• How the rating system works\n\nJust ask! 🏏`;
    }
    if (/thank|great|nice|good|awesome|cool|brilliant/.test(q)) {
      return `Straight down the ground! 🏏 Anything else you want to know?`;
    }
    if (/who.*score|highest.*score|max score/.test(q)) {
      const top = [...DATA.players].sort((a,b)=>b.final_score-a.final_score)[0];
      return top
        ? `The highest-rated player overall is **${top.player_name}** (${top.team}) with a final score of **${fmt(top.final_score)}**! 🌟`
        : `Data still loading — try again in a moment!`;
    }
    if (/ipl 2026|this season|2026/.test(q)) {
      const top = DATA.teams.sort((a,b)=>b.team_score-a.team_score)[0];
      return top
        ? `IPL 2026 is shaping up brilliantly! On paper, **${top.full_name||top.team}** looks the strongest based on squad depth. But cricket — as always — has other plans! Ask me for full rankings.`
        : `The analysis is based on all squads registered for IPL 2026. Ask about any team!`;
    }

    // ── Fallback ───────────────────────────────────────────────────────
    return `Hmm, I'm not quite sure how to answer that one! 🤔 Try asking me:\n• "Top 5 batters"\n• "Best bowling team"\n• "Compare MI and CSK"\n• "[Player name] score"\n• "How does the rating work?"`;
  }

  // ── Build & inject UI ──────────────────────────────────────────────────
  function renderBabujr() {
    const btn = document.createElement('div');
    btn.id = 'babujr-btn';
    btn.title = 'Chat with BABUJR';
    btn.innerHTML = `<svg viewBox="0 0 28 28" fill="none">
      <circle cx="14" cy="14" r="12" fill="rgba(0,0,0,0.3)"/>
      <circle cx="14" cy="14" r="7" fill="rgba(255,255,255,0.9)"/>
      <line x1="7" y1="14" x2="14" y2="7" stroke="rgba(0,0,0,0.7)" stroke-width="1.5"/>
      <line x1="14" y1="7" x2="21" y2="14" stroke="rgba(0,0,0,0.7)" stroke-width="1.5"/>
      <circle cx="14" cy="14" r="2.5" fill="#FFD700"/>
    </svg>`;

    const panel = document.createElement('div');
    panel.id = 'babujr-panel';
    panel.innerHTML = `
      <div class="babujr-header">
        <div class="babujr-avatar">🏏</div>
        <div class="info">
          <h4>BABUJR</h4>
          <span>● Analysis by SHIVAM</span>
        </div>
        <span class="babujr-close" id="babujr-close">✕</span>
      </div>
      <div id="babujr-messages"></div>
      <div class="chips-row" id="babujr-chips"></div>
      <div class="babujr-input-row">
        <input id="babujr-input" type="text" placeholder="Ask about teams, players, rankings..." autocomplete="off"/>
        <button id="babujr-send" title="Send">
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <path d="M2 9l14-7-7 14V9H2z" fill="currentColor"/>
          </svg>
        </button>
      </div>`;

    document.body.appendChild(btn);
    document.body.appendChild(panel);

    btn.addEventListener('click', togglePanel);
    document.getElementById('babujr-close').addEventListener('click', closePanel);
    document.getElementById('babujr-send').addEventListener('click', () => sendMessage());
    document.getElementById('babujr-input').addEventListener('keydown', e => {
      if (e.key === 'Enter') { e.preventDefault(); sendMessage(); }
    });
  }

  function togglePanel() { panelOpen ? closePanel() : openPanel(); }
  function openPanel() {
    panelOpen = true;
    document.getElementById('babujr-panel').classList.add('open');
    document.getElementById('babujr-btn').classList.add('opened');
    if (conversationHistory.length === 0) showWelcome();
    document.getElementById('babujr-input').focus();
  }
  function closePanel() {
    panelOpen = false;
    document.getElementById('babujr-panel').classList.remove('open');
    document.getElementById('babujr-btn').classList.remove('opened');
  }

  function showWelcome() {
    addMessage('assistant', `Hey there! 🏏 I'm <strong>BABUJR</strong>, your IPL 2026 analyst. I have all the squad strength data loaded — ask me anything!`);
    const container = document.getElementById('babujr-chips');
    container.innerHTML = STARTER_QUESTIONS.map(q =>
      `<span class="chip" data-q="${q}">${q}</span>`
    ).join('');
    container.querySelectorAll('.chip').forEach(c => {
      c.addEventListener('click', () => {
        container.innerHTML = '';
        sendMessage(c.dataset.q);
      });
    });
  }

  function addMessage(role, html) {
    const msgs = document.getElementById('babujr-messages');
    const div  = document.createElement('div');
    div.className = `msg ${role}`;
    div.innerHTML = role === 'assistant'
      ? `<span class="msg-avatar">🏏</span><span>${html.replace(/\*\*(.*?)\*\*/g,'<strong>$1</strong>').replace(/\n/g,'<br>')}</span>`
      : html;
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
  }

  function sendMessage(overrideText) {
    const input = document.getElementById('babujr-input');
    const text  = (overrideText || input.value).trim();
    if (!text) return;
    document.getElementById('babujr-chips').innerHTML = '';
    input.value = '';
    addMessage('user', text);
    // Small delay for natural feel
    setTimeout(() => {
      const reply = answer(text);
      addMessage('assistant', reply);
    }, 180);
  }

  // ── Init ───────────────────────────────────────────────────────────────
  async function init() {
    renderBabujr();
    try {
      const d = await loadData();
      DATA.teams   = d.teams   || [];
      DATA.players = d.players || [];
      DATA.squads  = d.squads  || {};
    } catch (e) {
      console.warn('BABUJR: data not yet available', e.message);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
