---
name: rspress-web-counter
description: Integrate web-counter into Rspress sites. Handles head config (avoiding boolean attr bug), footer stats, afterDocContent page views, leaderboard widget, and deployment. Covers JSX caveats (data-pv-page=""), MutationObserver SPA support, Caddy/Nginx reverse proxy config, and GitHub Actions → Gitee → cron auto-deploy.
---

# Rspress web-counter Integration

Integrate the web-counter visit tracking service into a Rspress static site.

## Prerequisites

- web-counter service running on the same server (or accessible via reverse proxy)
- Rspress site with `theme/index.tsx` layout override

## Step 1: Load counter.js on All Pages

In `rspress.config.ts`, add the script via `head` config. **Do NOT use boolean attributes** (`async: true`) — Rspress serialization bug concatenates attributes (e.g., `asyncsrc`).

```ts
export default defineConfig({
  head: [
    ['script', { src: '/counter.js' }],  // No async/defer — avoids attr concatenation bug
  ],
  // ...
});
```

## Step 2: Site-wide Stats in Footer

Add counter spans in `themeConfig.footer.message`. **Note**: Rspress `footer.message` only renders on the homepage.

```ts
themeConfig: {
  footer: {
    message: `
      <span style="display:none" class="counter-container" data-counter-style="badge">
        本站访问量 <span data-pv-site></span> 次 ·
        本站访客数 <span data-uv-site></span> 人 ·
        今日访问量 <span data-pv-today></span> 次 ·
        今日访客数 <span data-uv-today></span> 人
      </span>
      <br>
      版权所有 © 2024 mysite
    `,
  },
},
```

Available data attributes: `data-pv-today`, `data-uv-today`, `data-pv-site`, `data-uv-site`.

Available display styles (on container): `badge`, `card`, `bordered`, `default`.

## Step 3: Page View Counter for Articles

Use `afterDocContent` in `theme/index.tsx` for per-page counters (appears on all doc pages, not homepage).

**CRITICAL JSX caveat**: Write `data-pv-page=""` (empty string), NOT `<span data-pv-page></span>`. React renders the latter as `data-pv-page="true"`, causing counter.js to use `"true"` as the page path.

```tsx
// theme/index.tsx
import { Layout as BasicLayout } from '@rspress/core/theme-original';

const Layout = () => (
  <BasicLayout
    afterDocContent={
      <div align="left" style={{ fontSize: "0.8em", color: "gray" }}>
        <span style={{ display: "none" }} className="counter-container">
          阅读量 <span data-pv-page=""></span> 次
        </span>
        <br />
        {/* other after-content */}
      </div>
    }
  />
);
```

## Step 4: Leaderboard

### Option A: Dedicated Page

Create `docs/leaderboard.md` with a self-contained table:

```html
<div id="top-table-container" style="max-width:900px;margin:0 auto;">
  <table style="width:100%;border-collapse:collapse;font-size:15px;">
    <thead>
      <tr style="background:#f8f9fa;">
        <th>#</th><th>文章标题</th><th>阅读量</th>
      </tr>
    </thead>
    <tbody id="top-table-body">
      <tr><td colspan="3">加载中...</td></tr>
    </tbody>
  </table>
</div>
<script>
(function() {
  var xhr = new XMLHttpRequest();
  xhr.open('GET', window.location.origin + '/api/top?limit=50', true);
  xhr.onload = function() {
    var pages = JSON.parse(xhr.responseText);
    var html = '';
    var medals = ['\uD83E\uDD47', '\uD83E\uDD48', '\uD83E\uDD49'];
    pages.forEach(function(p, i) {
      var rank = i < 3 ? medals[i] : (i + 1);
      html += '<tr><td>' + rank + '</td><td><a href="' + p.path + '">' + (p.title || p.path) + '</a></td><td>' + p.count.toLocaleString() + '</td></tr>';
    });
    document.getElementById('top-table-body').innerHTML = html;
  };
  xhr.send();
})();
</script>
```

Add to `docs/_nav.json`:

```json
{ "text": "\uD83D\uDCCA排行榜", "link": "/leaderboard", "activeMatch": "/leaderboard" }
```

### Option B: Embedded Widget

Place `<ol data-pv-top="10"></ol>` anywhere in a page for a simple list widget.

### Dashboard Management

Dashboard (`/dashboard`) provides:
- Exclude list with wildcard support (`*/index.html`, `/about/*`)
- Configurable display limit
- Settings persist in database

API: `GET/POST /api/admin/top-exclude`

## Step 5: Server Deployment

### Caddy Reverse Proxy (same-domain)

```
mysite.site, www.mysite.site {
    handle /counter.js { reverse_proxy 127.0.0.1:8001 }
    handle /api/*      { reverse_proxy 127.0.0.1:8001 }
    handle /dashboard  { reverse_proxy 127.0.0.1:8001 }
    root * /var/www/mysite
    file_server
}
```

### Nginx

```nginx
location /counter.js  { proxy_pass http://127.0.0.1:8001; }
location /api/        { proxy_pass http://127.0.0.1:8001; }
location /dashboard   { proxy_pass http://127.0.0.1:8001; }
```

### systemd Service

```ini
[Service]
Type=simple
Environment="COUNTER_SALT=<random-hex>"
Environment="COUNTER_HOST=127.0.0.1"
Environment="COUNTER_PORT=8001"
ExecStart=/usr/bin/python3 -m uvicorn web_counter.main:app --host 127.0.0.1 --port 8001
Restart=on-failure
```

**Security**: Bind to `127.0.0.1` only, never expose directly to internet.

### Auto-Deploy Flow

```
push main → GitHub Actions build → gh-pages branch
                                       ↓
                         sync-to-gitee (mirror all branches)
                                       ↓
                          server crontab git pull
                                       ↓
                           Caddy serves static files
```

Server crontab: `0 8-20 * * * cd /var/www/site && git pull`

Initial clone: `git clone -b gh-pages https://gitee.com/<user>/<repo>.git /var/www/site`

## Common Pitfalls

| Issue | Cause | Fix |
|-------|-------|-----|
| Script doesn't load | `head: [{ async: true, src: '...' }]` renders as `asyncsrc` | Remove `async: true` from head config |
| Counter shows "true" | JSX `<span data-pv-page></span>` renders as `data-pv-page="true"` | Use `<span data-pv-page=""></span>` |
| Footer only on homepage | Rspress footer.message only renders on `/` | Use `afterDocContent` in theme for article pages |
| Page view same on all pages | `data-pv-page` attribute value used as path | Use empty string + `window.location.pathname` fallback |
| Counter not visible on SPA nav | Script doesn't re-execute on client-side routing | counter.js uses MutationObserver (v0.2.0+) |
| Login refresh shows form resubmit | POST /dashboard returns HTML, not redirect | Server uses PRG pattern (POST → 302 → GET) |

## Verification

```bash
curl https://mysite.site/api/health     # → {"status":"ok"}
curl https://mysite.site/counter.js     # → JS script
curl https://mysite.site/api/top?limit=5  # → leaderboard data
```

## Admin

```bash
web-counter createsuperuser    # Create admin account
# Dashboard: https://mysite.site/dashboard
# Login as admin to manage data, offsets, excludes, and view charts
```
