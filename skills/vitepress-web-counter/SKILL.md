---
name: vitepress-web-counter
description: Integrate web-counter into VitePress sites. Covers head config, footer stats (all-page), custom theme for doc-page counters, leaderboard widget, and deployment. VitePress footer renders on all pages unlike Rspress, simplifying site-wide stats. Uses Vue SFC or h() for custom layout components.
---

# VitePress web-counter Integration

Integrate web-counter into a VitePress documentation site.

Key difference from Rspress: VitePress `themeConfig.footer` renders on **all pages**, so site-wide counter stats work universally. Per-page counters (reading count) need a custom theme slot.

## Prerequisites

- web-counter service running, accessible via same-domain reverse proxy
- VitePress site with `.vitepress/config.ts`

## Step 1: Load counter.js on All Pages

VitePress `head` config handles boolean attributes correctly. Add script to `.vitepress/config.ts`:

```ts
export default defineConfig({
  head: [
    ['script', { src: '/counter.js' }],
  ],
  // ...
});
```

Unlike Rspress, VitePress has no boolean attr concatenation bug — `async` works fine if desired.

## Step 2: Site-wide Stats in Footer

VitePress `themeConfig.footer.message` renders on **every page** (homepage + all docs). Add counter spans directly:

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
    `,
    copyright: 'Copyright © 2024',
  },
},
```

Available data attributes: `data-pv-today`, `data-uv-today`, `data-pv-site`, `data-uv-site`.

Display styles (on container via `data-counter-style`): `badge`, `card`, `bordered`, `default`.

## Step 3: Page View Counter (Doc Pages Only)

VitePress doesn't have a built-in `afterDocContent` slot like Rspress. Use a custom theme layout.

### Approach A: Simple wrapper (recommended)

Create `.vitepress/theme/index.ts`:

```ts
import DefaultTheme from 'vitepress/theme'
import { h } from 'vue'

export default {
  extends: DefaultTheme,
  Layout() {
    return h(DefaultTheme.Layout, null, {
      // Insert before doc footer (only on doc pages, not homepage)
      'doc-footer-before': () => h('div', {
        style: 'font-size:0.8em;color:gray;margin-top:32px;'
      }, [
        h('span', {
          style: 'display:none',
          class: 'counter-container'
        }, [
          '阅读量 ',
          h('span', { 'data-pv-page': '' }),
          ' 次'
        ])
      ])
    })
  }
}
```

### Approach B: Vue SFC component

Create `.vitepress/theme/CounterBadge.vue`:

```vue
<template>
  <span style="display:none" class="counter-container" data-counter-style="badge">
    本站访问量 <span data-pv-site></span> 次 ·
    本站访客数 <span data-uv-site></span> 人 ·
    今日访问量 <span data-pv-today></span> 次 ·
    今日访客数 <span data-uv-today></span> 人
  </span>
</template>
```

Register in `.vitepress/theme/index.ts` and use in footer message or layout slots.

### VitePress Layout Slots

VitePress provides these layout slots for counter placement:

| Slot | Appears On | Use For |
|------|-----------|---------|
| `doc-before` | Doc pages only | Page view counter (top) |
| `doc-after` | Doc pages only | Page view counter (bottom) |
| `doc-footer-before` | Doc pages only | Page view counter (before prev/next) |
| `home-hero-after` | Homepage only | Site stats (alternative to footer) |
| `layout-top` | All pages | Wrapper for global elements |
| `layout-bottom` | All pages | Wrapper for global elements |

## Step 4: Leaderboard

### Dedicated Page

Create `docs/leaderboard.md`:

```md
# 阅读量排行榜

<ClientOnly>
  <div id="top-table">
    <table>
      <thead><tr><th>#</th><th>文章</th><th>阅读量</th></tr></thead>
      <tbody id="top-body"><tr><td colspan="3">加载中...</td></tr></tbody>
    </table>
  </div>

  <script>
  (function() {
    fetch(window.location.origin + '/api/top?limit=50')
      .then(r => r.json())
      .then(pages => {
        var medals = ['🥇','🥈','🥉'];
        document.getElementById('top-body').innerHTML = pages.map((p, i) =>
          '<tr><td>' + (i < 3 ? medals[i] : i + 1) + '</td>' +
          '<td><a href="' + p.path + '">' + (p.title || p.path) + '</a></td>' +
          '<td>' + p.count.toLocaleString() + '</td></tr>'
        ).join('');
      });
  })();
  </script>
</ClientOnly>
```

Add to `.vitepress/config.ts` sidebar or nav:

```ts
themeConfig: {
  nav: [
    { text: '排行榜', link: '/leaderboard' },
  ],
}
```

### Embedded Widget

Place anywhere: `<ol data-pv-top="10"></ol>`

## Step 5: Server Deployment

### Caddy Reverse Proxy

```
mysite.site {
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

Bind to `127.0.0.1` — never expose web-counter directly to the internet.

### Production Tips

- VitePress builds to `.vitepress/dist/`, deploy that directory
- Use GitHub Actions to build and deploy to gh-pages
- Server pulls from Gitee mirror via crontab
- SQLite data at `/opt/web-counter/data/counter.db` — back up regularly

## VitePress vs Rspress

| Aspect | VitePress | Rspress |
|--------|-----------|---------|
| Footer visibility | **All pages** | Homepage only |
| Head boolean attrs | Works correctly | Bug: `async:true` → `asyncsrc` |
| Templating | Vue (`.vue` SFC or `h()`) | React (TSX) |
| Per-page counter | Custom theme + `doc-footer-before` slot | `afterDocContent` prop |
| `data-pv-page` value | No special handling needed | Must use `""` (empty string) |
| Client wrapper | `<ClientOnly>` | Built-in (React) |

## Verification

```bash
curl https://mysite.site/api/health     # → {"status":"ok"}
curl https://mysite.site/counter.js     # → JS script
curl https://mysite.site/api/top?limit=5  # → leaderboard
```

## Admin

```bash
web-counter createsuperuser
# Dashboard: https://mysite.site/dashboard
```
