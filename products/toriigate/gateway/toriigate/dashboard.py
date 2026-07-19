"""Single-file HTML dashboard, served at /_torii/dashboard.

Polls /_torii/stats every 3 seconds. No external assets.
"""

from __future__ import annotations

_PAGE = """<!doctype html>
<html lang="ja">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ToriiGate — {tenant}</title>
<style>
  :root {{ --bg:#0b1020; --card:#131a30; --line:#233052; --txt:#e8ecf8;
          --dim:#7d89a8; --accent:#e0483e; --ok:#3fb27f; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--txt);
         font-family: system-ui, sans-serif; }}
  header {{ display:flex; align-items:center; gap:.75rem;
           padding:1rem 1.5rem; border-bottom:1px solid var(--line); }}
  header .logo {{ font-size:1.6rem; }}
  header h1 {{ font-size:1.05rem; margin:0; font-weight:600; }}
  header .tenant {{ color:var(--dim); font-size:.85rem; margin-left:auto; }}
  main {{ padding:1.5rem; max-width:1100px; margin:0 auto; }}
  .tiles {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr));
           gap:1rem; }}
  .tile {{ background:var(--card); border:1px solid var(--line);
          border-radius:10px; padding:1rem; }}
  .tile .n {{ font-size:1.8rem; font-weight:700; }}
  .tile .l {{ color:var(--dim); font-size:.8rem; }}
  .cols {{ display:grid; grid-template-columns:1fr 1fr; gap:1rem;
          margin-top:1rem; }}
  @media (max-width:800px) {{ .cols {{ grid-template-columns:1fr; }} }}
  .card {{ background:var(--card); border:1px solid var(--line);
          border-radius:10px; padding:1rem; }}
  .card h2 {{ font-size:.9rem; margin:0 0 .75rem; color:var(--dim);
             text-transform:uppercase; letter-spacing:.05em; }}
  .bar {{ display:flex; align-items:center; gap:.5rem; margin:.3rem 0;
         font-size:.85rem; }}
  .bar .track {{ flex:1; height:8px; background:var(--line);
                border-radius:4px; overflow:hidden; }}
  .bar .fill {{ height:100%; background:var(--accent); }}
  .bar.ok .fill {{ background:var(--ok); }}
  .tbl-wrap {{ overflow-x:auto; margin-top:1rem; }}
  table {{ width:100%; border-collapse:collapse; font-size:.8rem; }}
  th, td {{ text-align:left; padding:.4rem .6rem;
           border-bottom:1px solid var(--line); white-space:nowrap; }}
  th {{ color:var(--dim); font-weight:500; }}
  .pill {{ padding:.1rem .5rem; border-radius:99px; font-size:.72rem; }}
  .pill.block, .pill.throttle {{ background:#3d1a22; color:#ff8a80; }}
  .pill.challenge, .pill.monetize, .pill.tarpit {{ background:#3a2f14; color:#ffd54f; }}
  .pill.allow, .pill.log_only {{ background:#14321f; color:#80e27e; }}
</style>
<header>
  <span class="logo">&#x26E9;&#xFE0F;</span>
  <h1>ToriiGate — AI Access Gateway</h1>
  <span class="tenant">tenant: {tenant}</span>
</header>
<main>
  <div class="tiles">
    <div class="tile"><div class="n" id="total">–</div>
      <div class="l">総リクエスト</div></div>
    <div class="tile"><div class="n" id="actions">–</div>
      <div class="l">制御したアクセス</div></div>
    <div class="tile"><div class="n" id="uptime">–</div>
      <div class="l">稼働時間</div></div>
  </div>
  <div class="cols">
    <div class="card"><h2>カテゴリ別</h2><div id="cats"></div></div>
    <div class="card"><h2>検知したボット Top10</h2><div id="bots"></div></div>
  </div>
  <div class="card tbl-wrap">
    <h2>直近のイベント</h2>
    <table><thead><tr><th>時刻</th><th>IP</th><th>パス</th><th>分類</th>
      <th>スコア</th><th>アクション</th></tr></thead>
      <tbody id="events"></tbody></table>
  </div>
</main>
<script>
const esc = s => String(s).replace(/[&<>"]/g,
    c => ({{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}})[c]);
async function tick() {{
  const r = await fetch("/_torii/stats");
  if (!r.ok) return;
  const s = await r.json();
  document.getElementById("total").textContent = s.total_requests;
  document.getElementById("actions").textContent = s.actions_taken;
  document.getElementById("uptime").textContent =
      Math.round(s.uptime_seconds / 60) + "分";
  const mkBars = (obj, max) => Object.entries(obj)
    .sort((a, b) => b[1] - a[1])
    .map(([k, v]) => `<div class="bar ${{k === "human" ? "ok" : ""}}">
        <span style="width:11rem">${{esc(k)}}</span>
        <span class="track"><span class="fill"
          style="width:${{Math.min(100, v / max * 100)}}%"></span></span>
        <span>${{v}}</span></div>`).join("");
  const catMax = Math.max(1, ...Object.values(s.by_category));
  document.getElementById("cats").innerHTML = mkBars(s.by_category, catMax);
  const bots = Object.fromEntries(s.top_bots);
  const botMax = Math.max(1, ...Object.values(bots));
  document.getElementById("bots").innerHTML =
      mkBars(bots, botMax) || '<span style="color:var(--dim)">なし</span>';
  document.getElementById("events").innerHTML = s.recent_events.map(e =>
    `<tr><td>${{new Date(e.ts * 1000).toLocaleTimeString()}}</td>
     <td>${{esc(e.client_ip)}}</td><td>${{esc(e.path)}}</td>
     <td>${{esc(e.category)}}</td><td>${{e.score}}</td>
     <td><span class="pill ${{esc(e.action)}}">${{esc(e.action)}}</span></td></tr>`
  ).join("");
}}
tick(); setInterval(tick, 3000);
</script>
</html>
"""


def dashboard_page(tenant: str) -> bytes:
    return _PAGE.format(tenant=tenant).encode()
