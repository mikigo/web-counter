"""Dashboard and login page server-rendered HTML."""

import json


def get_login_html(error: str = "") -> str:
    """Return the login page HTML."""
    error_html = f'<p style="color:#e74c3c;text-align:center;margin-bottom:16px;">{error}</p>' if error else ""
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>web-counter - Login</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: #f5f5f5;
    display: flex; align-items: center; justify-content: center;
    min-height: 100vh;
  }}
  .login-box {{
    background: #fff; border-radius: 8px; box-shadow: 0 2px 12px rgba(0,0,0,0.08);
    padding: 40px; width: 360px; max-width: 90vw;
  }}
  h1 {{ text-align:center; font-size:20px; margin-bottom:24px; color:#333; }}
  label {{ display:block; font-size:14px; color:#666; margin-bottom:6px; }}
  input[type="text"], input[type="password"] {{
    width:100%; padding:10px 12px; border:1px solid #ddd; border-radius:4px;
    font-size:14px; margin-bottom:16px; outline:none;
  }}
  input:focus {{ border-color:#4a90d9; }}
  button {{
    width:100%; padding:10px; background:#4a90d9; color:#fff; border:none;
    border-radius:4px; font-size:15px; cursor:pointer;
  }}
  button:hover {{ background:#357abd; }}
</style>
</head>
<body>
<div class="login-box">
  <h1>web-counter 管理后台</h1>
  {error_html}
  <form method="POST" action="/dashboard">
    <label for="username">用户名</label>
    <input type="text" id="username" name="username" required autofocus>
    <label for="password">密码</label>
    <input type="password" id="password" name="password" required>
    <button type="submit">登 录</button>
  </form>
</div>
</body>
</html>"""


def get_dashboard_html(
    today_pv: int = 0,
    today_uv: int = 0,
    site_pv: int = 0,
    site_uv: int = 0,
    offsets: dict | None = None,
    daily_stats: list | None = None,
) -> str:
    """Return the dashboard page HTML with embedded data."""
    if offsets is None:
        offsets = {}
    if daily_stats is None:
        daily_stats = []

    stats_json = json.dumps({
        "today_pv": today_pv,
        "today_uv": today_uv,
        "site_pv": site_pv,
        "site_uv": site_uv,
        "offsets": offsets,
        "daily": daily_stats,
    })

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>web-counter - Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: #f5f5f5; color:#333;
  }}
  .header {{
    background:#fff; border-bottom:1px solid #e0e0e0; padding:12px 24px;
    display:flex; align-items:center; justify-content:space-between;
  }}
  .header h1 {{ font-size:18px; }}
  .header a {{ color:#e74c3c; text-decoration:none; font-size:14px; }}
  .container {{ max-width:960px; margin:0 auto; padding:24px; }}
  .cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:16px; margin-bottom:24px; }}
  .card {{
    background:#fff; border-radius:8px; box-shadow:0 1px 4px rgba(0,0,0,0.06);
    padding:20px;
  }}
  .card .label {{ font-size:13px; color:#999; margin-bottom:8px; }}
  .card .value {{ font-size:28px; font-weight:600; }}
  .card.today {{ border-left:3px solid #4a90d9; }}
  .card.site {{ border-left:3px solid #27ae60; }}
  .section {{ background:#fff; border-radius:8px; box-shadow:0 1px 4px rgba(0,0,0,0.06); padding:20px; margin-bottom:24px; }}
  .section h2 {{ font-size:16px; margin-bottom:16px; color:#333; }}
  .chart-wrap {{ position:relative; width:100%; height:300px; }}
  form.manage {{ display:flex; flex-direction:column; gap:12px; }}
  .row {{ display:flex; gap:12px; align-items:flex-end; flex-wrap:wrap; }}
  .field {{ display:flex; flex-direction:column; gap:4px; }}
  .field label {{ font-size:13px; color:#666; }}
  .field input, .field select {{
    padding:8px 10px; border:1px solid #ddd; border-radius:4px; font-size:14px;
  }}
  button.btn {{
    padding:8px 16px; border:none; border-radius:4px; font-size:14px; cursor:pointer; color:#fff;
  }}
  .btn-primary {{ background:#4a90d9; }}
  .btn-danger {{ background:#e74c3c; }}
  .btn-primary:hover {{ background:#357abd; }}
  .btn-danger:hover {{ background:#c0392b; }}
  pre {{ background:#f8f8f8; border:1px solid #eee; border-radius:4px; padding:16px; font-size:13px; overflow-x:auto; white-space:pre-wrap; word-break:break-all; }}
  .toast {{ position:fixed; top:20px; right:20px; padding:12px 20px; border-radius:4px; color:#fff; font-size:14px; z-index:999; display:none; }}
  .toast.success {{ background:#27ae60; }}
  .toast.error {{ background:#e74c3c; }}
  .top-table {{ width:100%; border-collapse:collapse; font-size:14px; }}
  .top-table th {{ text-align:left; padding:10px 12px; border-bottom:2px solid #eee; color:#999; font-weight:500; }}
  .top-table td {{ padding:10px 12px; border-bottom:1px solid #f0f0f0; }}
  .top-table .rank {{ width:40px; color:#999; }}
  .top-table .rank.top3 {{ color:#e67e22; font-weight:600; }}
  .top-table .count {{ width:80px; text-align:right; font-weight:500; }}
  .top-table .path {{ word-break:break-all; }}
  .top-table tr:hover {{ background:#fafafa; }}
</style>
</head>
<body>
<div class="header">
  <h1>web-counter 统计看板</h1>
  <a href="#" onclick="logout();return false;">退出登录</a>
</div>
<div class="container">
  <div class="cards">
    <div class="card today"><div class="label">今日 PV</div><div class="value" id="todayPv">{today_pv}</div></div>
    <div class="card today"><div class="label">今日 UV</div><div class="value" id="todayUv">{today_uv}</div></div>
    <div class="card site"><div class="label">累计 PV</div><div class="value" id="sitePv">{site_pv}</div></div>
    <div class="card site"><div class="label">累计 UV</div><div class="value" id="siteUv">{site_uv}</div></div>
  </div>

  <div class="section">
    <h2>30 天趋势</h2>
    <div class="chart-wrap"><canvas id="trendChart"></canvas></div>
  </div>

  <div class="section">
    <h2>阅读量排行</h2>
    <table class="top-table">
      <thead><tr><th class="rank">#</th><th>页面</th><th class="count">阅读量</th></tr></thead>
      <tbody id="topPagesBody"><tr><td colspan="3" style="text-align:center;color:#999">加载中...</td></tr></tbody>
    </table>
    <div style="margin-top:16px; padding-top:12px; border-top:1px solid #eee;">
      <div class="row">
        <div class="field" style="flex:1">
          <label>排除路径（逗号分隔）</label>
          <input type="text" id="excludeInput" placeholder="如: /, /index.html, /about">
        </div>
        <button class="btn btn-primary" onclick="saveExclude()" style="margin-top:20px">保存排除项</button>
      </div>
    </div>
  </div>

  <div class="section">
    <h2>接入代码</h2>
    <p style="font-size:13px;color:#666;margin-bottom:8px;">将以下代码复制到网页 &lt;/body&gt; 前即可接入统计：</p>
    <pre id="embedCode">&lt;script async src="{_get_origin()}/counter.js"&gt;&lt;/script&gt;

&lt;span style="display:none" class="counter-container" data-counter-style="card"&gt;
  本站访问次数 &lt;span data-pv-site&gt;&lt;/span&gt; 次 ·
  今日访问量 &lt;span data-pv-today&gt;&lt;/span&gt; 次 ·
  今日访客 &lt;span data-uv-today&gt;&lt;/span&gt; 人 ·
  总访客 &lt;span data-uv-site&gt;&lt;/span&gt; 人
&lt;/span&gt;</pre>
  </div>

  <div class="section">
    <h2>数据重置</h2>
    <form class="manage" id="resetForm" onsubmit="resetData(event)">
      <div class="row">
        <div class="field">
          <label>重置范围</label>
          <select id="resetScope">
            <option value="today">今日数据</option>
            <option value="all">全部数据 (不可逆)</option>
            <option value="page">指定页面</option>
          </select>
        </div>
        <div class="field" id="resetPathField" style="display:none;">
          <label>页面路径</label>
          <input type="text" id="resetPath" placeholder="/blog/hello">
        </div>
        <button type="submit" class="btn btn-danger">执行重置</button>
      </div>
    </form>
  </div>

  <div class="section">
    <h2>起始值设置</h2>
    <form class="manage" id="offsetForm" onsubmit="setOffset(event)">
      <div class="row">
        <div class="field"><label>累计 PV 起始值</label><input type="number" id="offsetSitePv" value="{offsets.get('site_pv', 0)}"></div>
        <div class="field"><label>累计 UV 起始值</label><input type="number" id="offsetSiteUv" value="{offsets.get('site_uv', 0)}"></div>
        <button type="submit" class="btn btn-primary">保存起始值</button>
      </div>
    </form>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
  var INITIAL_DATA = {stats_json};

  function fmt(n) {{ return n.toString().replace(/\\B(?=(\\d{{3}})+(?!\\d))/g, ','); }}

  // Trend chart
  (function() {{
    var daily = INITIAL_DATA.daily || [];
    var labels = daily.map(function(d) {{ return d.date.slice(5); }});
    var pvData = daily.map(function(d) {{ return d.pv; }});
    var uvData = daily.map(function(d) {{ return d.uv; }});

    new Chart(document.getElementById('trendChart'), {{
      type: 'line',
      data: {{
        labels: labels,
        datasets: [
          {{ label: 'PV', data: pvData, borderColor: '#4a90d9', tension:0.3, pointRadius:1 }},
          {{ label: 'UV', data: uvData, borderColor: '#27ae60', tension:0.3, pointRadius:1 }}
        ]
      }},
      options: {{
        responsive:true, maintainAspectRatio:false,
        scales: {{ y: {{ beginAtZero:true, ticks:{{precision:0}} }} }}
      }}
    }});
  }})();

  // Show/hide path field for page reset
  document.getElementById('resetScope').addEventListener('change', function() {{
    document.getElementById('resetPathField').style.display = this.value === 'page' ? '' : 'none';
  }});

  function toast(msg, type) {{
    var t = document.getElementById('toast');
    t.textContent = msg;
    t.className = 'toast ' + (type || 'success');
    t.style.display = 'block';
    setTimeout(function() {{ t.style.display = 'none'; }}, 3000);
  }}

  async function resetData(e) {{
    e.preventDefault();
    var scope = document.getElementById('resetScope').value;
    var body = {{scope: scope}};
    if (scope === 'page') body.path = document.getElementById('resetPath').value;
    if (scope === 'all' && !confirm('确定要删除全部数据吗？此操作不可逆！')) return;
    var resp = await fetch('/api/admin/reset', {{
      method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify(body)
    }});
    if (resp.ok) {{ toast('重置成功'); setTimeout(function(){{ location.reload(); }}, 500); }}
    else toast('重置失败: ' + (await resp.text()), 'error');
  }}

  async function setOffset(e) {{
    e.preventDefault();
    var body = {{
      site_pv: parseInt(document.getElementById('offsetSitePv').value) || 0,
      site_uv: parseInt(document.getElementById('offsetSiteUv').value) || 0,
    }};
    var resp = await fetch('/api/admin/offset', {{
      method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify(body)
    }});
    if (resp.ok) {{ toast('起始值已保存'); setTimeout(function(){{ location.reload(); }}, 500); }}
    else toast('保存失败: ' + (await resp.text()), 'error');
  }}

  async function logout() {{
    await fetch('/api/admin/logout', {{method:'POST'}});
    location.reload();
  }}

  // Leaderboard
  function loadTopPages() {{
    fetch('/api/top?limit=20').then(function(r){{ return r.json(); }}).then(function(pages) {{
      var html = '';
      if (pages.length === 0) {{
        html = '<tr><td colspan="3" style="text-align:center;color:#999">暂无数据</td></tr>';
      }} else {{
        pages.forEach(function(p, i) {{
          var rankClass = i < 3 ? ' top3' : '';
          html += '<tr><td class="rank' + rankClass + '">' + (i + 1) + '</td><td class="path">' + p.path + '</td><td class="count">' + fmt(p.count) + '</td></tr>';
        }});
      }}
      document.getElementById('topPagesBody').innerHTML = html;
    }}).catch(function(){{}});
  }}
  loadTopPages();

  // Exclude management
  function loadExclude() {{
    fetch('/api/admin/top-exclude').then(function(r){{ return r.json(); }}).then(function(d) {{
      document.getElementById('excludeInput').value = (d.paths || []).join(', ');
    }}).catch(function(){{}});
  }}
  loadExclude();

  async function saveExclude() {{
    var paths = document.getElementById('excludeInput').value.split(',').map(function(p){{ return p.trim(); }}).filter(Boolean);
    var resp = await fetch('/api/admin/top-exclude', {{
      method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{paths: paths}})
    }});
    if (resp.ok) {{ toast('排除项已保存'); loadTopPages(); }}
    else toast('保存失败', 'error');
  }}

  // Auto-refresh every 30s
  setInterval(function() {{
    fetch('/api/count').then(function(r){{ return r.json(); }}).then(function(d) {{
      document.getElementById('todayPv').textContent = fmt(d.today_pv);
      document.getElementById('todayUv').textContent = fmt(d.today_uv);
      document.getElementById('sitePv').textContent = fmt(d.site_pv);
      document.getElementById('siteUv').textContent = fmt(d.site_uv);
    }}).catch(function(){{}});
    loadTopPages();
  }}, 30000);
</script>
</body>
</html>"""


def _get_origin() -> str:
    """Get the origin from environment for embed code display."""
    import os
    host = os.environ.get("COUNTER_HOST", "0.0.0.0")
    port = os.environ.get("COUNTER_PORT", "8000")
    if host == "0.0.0.0":
        host = "your-domain.com"
    if port == "80" or port == "443":
        return f"http://{host}"
    return f"http://{host}:{port}"
