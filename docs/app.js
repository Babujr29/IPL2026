/**
 * app.js — Shared utilities, data loader, navigation, sort/filter engine
 * for the IPL 2026 Squad Strength Index website.
 */

// ── Global data cache ──────────────────────────────────────────────────────
const AppData = {
  teams:   null,   // array of team score objects
  players: null,   // array of player score objects
  squads:  null,   // object { team: [players] }
};

async function loadData() {
  if (AppData.teams && AppData.players && AppData.squads) return AppData;
  const [teams, players, squads] = await Promise.all([
    fetch('data/team_scores.json').then(r => r.json()),
    fetch('data/player_scores.json').then(r => r.json()),
    fetch('data/squad_data.json').then(r => r.json()),
  ]);
  AppData.teams   = teams;
  AppData.players = players;
  AppData.squads  = squads;
  return AppData;
}

// ── Team colors ────────────────────────────────────────────────────────────
const TEAM_COLORS = {
  CSK:'#F9CD1C', MI:'#004BA0', KKR:'#3A225D', RCB:'#D1001C',
  PBKS:'#ED1F27', GT:'#1C1C6E', RR:'#EA1A7F', SRH:'#F7A721',
  LSG:'#A0E00A', DC:'#0078BC',
};
const TEAM_FULL = {
  CSK:'Chennai Super Kings', MI:'Mumbai Indians', KKR:'Kolkata Knight Riders',
  RCB:'Royal Challengers Bengaluru', PBKS:'Punjab Kings', GT:'Gujarat Titans',
  RR:'Rajasthan Royals', SRH:'Sunrisers Hyderabad', LSG:'Lucknow Super Giants',
  DC:'Delhi Capitals',
};

// ── Navbar markup ──────────────────────────────────────────────────────────
function buildNavbar(activePage) {
  const currentFile = window.location.pathname.split('/').pop() || 'index.html';
  return `
  <nav class="navbar">
    <div class="navbar-brand">
      <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
        <circle cx="16" cy="16" r="15" stroke="#FFD700" stroke-width="1.5"/>
        <circle cx="16" cy="16" r="7" fill="#FFD700" opacity="0.15"/>
        <path d="M8 16 Q16 8 24 16 Q16 24 8 16Z" fill="#FFD700" opacity="0.6"/>
      </svg>
      <span class="logo-text">IPL 2026 SSI</span>
    </div>
    <div class="navbar-links">
      <a href="index.html"       class="${activePage==='home'?'active':''}">Home</a>
      <a href="leaderboards.html" class="${activePage==='lead'?'active':''}">Leaderboards</a>
      <a href="compare.html"     class="${activePage==='cmp'?'active':''}">Compare</a>
      <div class="team-dropdown">
        <div class="team-dropdown-btn">
          Teams <svg width="12" height="12" viewBox="0 0 12 12"><path d="M2 4l4 4 4-4" stroke="currentColor" stroke-width="1.5" fill="none"/></svg>
        </div>
        <div class="team-dropdown-menu" id="team-nav-menu">
          <!-- populated by JS -->
        </div>
      </div>
    </div>
  </nav>`;
}

function populateTeamNavMenu(teams) {
  const menu = document.getElementById('team-nav-menu');
  if (!menu || !teams) return;
  menu.innerHTML = teams.map(t =>
    `<a href="team.html?team=${t.team}">${TEAM_FULL[t.team] || t.team}</a>`
  ).join('');
}

// ── Footer ─────────────────────────────────────────────────────────────────
function buildFooter() {
  return `<footer><strong>SHIVAM</strong> | IPL 2026 Squad Strength Index | Data sourced from Cricsheet.org</footer>`;
}

// ── Player photo URL (ESPNcricinfo) ───────────────────────────────────────
function playerPhotoURL(cricinfoKey) {
  if (!cricinfoKey || cricinfoKey === '0' || cricinfoKey === '') return null;
  return `https://img1.hscicdn.com/image/upload/f_auto,t_ds_square_w_160,q_50/lsci/${cricinfoKey}.jpg`;
}

// ── Avatar with initials fallback ─────────────────────────────────────────
function avatarHTML(player, size = 44) {
  const url = playerPhotoURL(player.cricinfo_key);
  const initials = (player.player_name || '??')
    .split(' ').slice(0,2).map(w => w[0]).join('').toUpperCase();
  const color = TEAM_COLORS[player.team] || '#FFD700';
  const id    = `av-${player.cricsheet_id || Math.random().toString(36).slice(2)}`;

  if (url) {
    return `<div class="player-avatar" id="${id}" style="width:${size}px;height:${size}px;">
      <img src="${url}" alt="${player.player_name}"
           onerror="this.parentElement.innerHTML='<span>${initials}</span>';this.parentElement.style.background='${color}22';this.parentElement.style.color='${color}';"/>
    </div>`;
  }
  return `<div class="player-avatar" style="width:${size}px;height:${size}px;background:${color}22;color:${color};">${initials}</div>`;
}

// ── Rank badge HTML ────────────────────────────────────────────────────────
function rankBadge(rank) {
  const cls = rank===1?'gold':rank===2?'silver':rank===3?'bronze':'';
  const medal = rank===1?'🥇':rank===2?'🥈':rank===3?'🥉':'';
  return `<span class="rank-badge ${cls}">${medal||rank}</span>`;
}

// ── Player type pill ───────────────────────────────────────────────────────
function typePill(type) {
  const labels = {
    established:'Established', young_established:'Young',
    debutant:'Debutant', low_exp:'Low Exp', inactive:'Inactive',
  };
  return `<span class="type-pill ${type}">${labels[type]||type}</span>`;
}

// ── Score badge ────────────────────────────────────────────────────────────
function scoreBadge(val, gold=false) {
  return `<span class="score-badge ${gold?'gold-score':''}">${(+val).toFixed(2)}</span>`;
}

// ── Sorting engine for tables ─────────────────────────────────────────────
let _sortState = {};  // { tableId: { col, dir } }

function setupSortableTable(tableId, data, renderFn, initialSort=null) {
  const table = document.getElementById(tableId);
  if (!table) return;
  _sortState[tableId] = initialSort || { col: null, dir: 'desc' };

  table.querySelectorAll('thead th[data-col]').forEach(th => {
    th.addEventListener('click', () => {
      const col = th.dataset.col;
      const st  = _sortState[tableId];
      if (st.col === col) st.dir = st.dir==='desc' ? 'asc' : 'desc';
      else { st.col = col; st.dir = 'desc'; }

      table.querySelectorAll('thead th').forEach(h => h.classList.remove('sort-asc','sort-desc'));
      th.classList.add(st.dir==='desc' ? 'sort-desc' : 'sort-asc');

      const sorted = [...data].sort((a,b) => {
        const va = isNaN(a[col]) ? (a[col]||'') : +a[col];
        const vb = isNaN(b[col]) ? (b[col]||'') : +b[col];
        return st.dir==='desc' ? (vb > va ? 1 : -1) : (va > vb ? 1 : -1);
      });
      renderFn(sorted);
    });
  });
}

// ── Counter animation ─────────────────────────────────────────────────────
function animateCounter(el, target, decimals=2, duration=800) {
  const start = performance.now();
  function step(now) {
    const p = Math.min((now - start) / duration, 1);
    const ease = 1 - Math.pow(1 - p, 3);
    el.textContent = (target * ease).toFixed(decimals);
    if (p < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

function animateAllCounters(selector='.counter') {
  document.querySelectorAll(selector).forEach(el => {
    const val = +el.dataset.val;
    const dec = +(el.dataset.dec||2);
    animateCounter(el, val, dec);
  });
}

// ── Observer for slide-up animation on scroll ─────────────────────────────
function setupScrollAnimations() {
  const obs = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) { e.target.classList.add('fade-in'); obs.unobserve(e.target); }
    });
  }, { threshold: 0.1 });
  document.querySelectorAll('.animate-on-scroll').forEach(el => obs.observe(el));
}

// ── Team accent colour helper ─────────────────────────────────────────────
function teamAccentStyle(team, opacity=0.15) {
  const c = TEAM_COLORS[team] || '#FFD700';
  return `border-left: 3px solid ${c}; background: ${c}${Math.round(opacity*255).toString(16).padStart(2,'0')};`;
}

// ── Mini team logo (SVG placeholder using team colour) ────────────────────
function teamLogoHTML(team, size=32) {
  const color = TEAM_COLORS[team] || '#FFD700';
  return `<div style="width:${size}px;height:${size}px;border-radius:50%;
    background:${color}22;border:2px solid ${color}55;display:flex;
    align-items:center;justify-content:center;font-family:Rajdhani,sans-serif;
    font-weight:700;font-size:${size*0.35}px;color:${color};">${team}</div>`;
}

// ── Strength bar ───────────────────────────────────────────────────────────
function strengthBar(val, maxVal=10) {
  const pct = Math.min((val / maxVal) * 100, 100);
  return `<div class="strength-bar-wrap">
    <div class="strength-bar">
      <div class="strength-bar-fill" style="width:${pct}%"></div>
    </div>
    <span class="strength-val counter" data-val="${val}" data-dec="2">${(+val).toFixed(2)}</span>
  </div>`;
}

// ── URL param helper ─────────────────────────────────────────────────────
function getParam(name) {
  return new URLSearchParams(window.location.search).get(name);
}

// Export (used across pages)
window.AppData   = AppData;
window.loadData  = loadData;
window.TEAM_COLORS = TEAM_COLORS;
window.TEAM_FULL = TEAM_FULL;
window.buildNavbar = buildNavbar;
window.buildFooter = buildFooter;
window.populateTeamNavMenu = populateTeamNavMenu;
window.playerPhotoURL = playerPhotoURL;
window.avatarHTML  = avatarHTML;
window.rankBadge   = rankBadge;
window.typePill    = typePill;
window.scoreBadge  = scoreBadge;
window.setupSortableTable = setupSortableTable;
window.animateAllCounters = animateAllCounters;
window.setupScrollAnimations = setupScrollAnimations;
window.teamAccentStyle = teamAccentStyle;
window.teamLogoHTML = teamLogoHTML;
window.strengthBar = strengthBar;
window.getParam    = getParam;
