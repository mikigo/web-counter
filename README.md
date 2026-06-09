# web-counter

<div align="center">

**轻量、隐私优先、开箱即用的网站访问计数器**

一行命令部署，一个 `<script>` 接入，一行 HTML 展示。数据完全由你掌控。

[![PyPI](https://img.shields.io/pypi/v/web-counter)](https://pypi.org/project/web-counter/)
[![Python](https://img.shields.io/pypi/pyversions/web-counter)](https://pypi.org/project/web-counter/)
[![License](https://img.shields.io/pypi/l/web-counter)](./LICENSE)

</div>

web-counter 解决的是**静态网站的统计难题**——GitHub Pages、VitePress、Rspress 等没有后端，无法统计访问数据。只需在你的服务器上部署一个轻量服务，所有静态站点就能拥有不输专业平台的访问分析能力。

## 快速开始

```bash
pip install web-counter                                              # 安装
export COUNTER_SALT="$(openssl rand -hex 16)"                       # 生成密钥
web-counter start                                                   # 启动服务
web-counter createsuperuser                                         # 创建管理员
```

终端会直接打印前端接入代码，复制到网页中即可。就这么简单。

### 在线示例

[**mikigo.site**](https://mikigo.site/) 是 web-counter 在生产环境中的实际应用。页面底部展示了全站访问统计，每篇文章底部有阅读量，[排行榜页面](https://mikigo.site/leaderboard.html)展示了热门内容。

```html
<!-- mikigo.site 页脚的计数器代码 -->
<span style="display:none" class="counter-container" data-counter-style="badge">
  本站访问量 <span data-pv-site></span> 次 ·
  今日访问量 <span data-pv-today></span> 次 ·
  访客 <span data-uv-today></span> 人
</span>
```

## 核心特性

### 实时统计指标

| 指标 | 含义 |
|------|------|
| 今日访问量 (PV) | 今日页面总访问次数 |
| 今日访客数 (UV) | 今日独立访客（IP + salt 哈希去重） |
| 累计访问量 | 建站以来总访问次数（支持设定初始值） |
| 累计访客数 | 建站以来独立访客总数（支持设定初始值） |
| 页面阅读量 | 每篇文章的独立阅读次数 |

### 热门排行榜

`<ol data-pv-top="10"></ol>` 一行代码嵌入热门文章排行。文章标题自动采集，排除规则支持 `*` 通配符，Dashboard 可视化配置。

```bash
curl https://你的域名/api/top?limit=10
# → [{"path":"/blog/hello","title":"Redis 入门指南","count":123}, ...]
```

### 统计看板 Dashboard

登录即用的管理后台，包含实时统计卡片、30 天趋势图（Chart.js）、排行榜管理、数据重置和起始值配置。

### 隐私设计

- 不存储 IP、不设追踪 Cookie、不做浏览器指纹
- 访客唯一性 = `SHA256(IP + salt)`，salt 仅部署者持有
- 换 salt 后历史 UV 清零，建议一次设定不再更改

## 前端接入

在页面任意位置插入声明式标签，counter.js 自动填充数据：

```html
<script async src="/counter.js"></script>

<span style="display:none" class="counter-container" data-counter-style="badge">
  本站访问量 <span data-pv-site></span> 次 ·
  访客 <span data-uv-site></span> 人 ·
  今日 <span data-pv-today></span> 次 ·
  访客 <span data-uv-today></span> 人
</span>
```

计数器初始隐藏（`display:none`），数据加载成功后自动显示；后端不可用时完全无感。

### 数据属性

| 属性 | 效果 | 示例 |
|------|------|------|
| `data-pv-today` | 今日 PV | `<span data-pv-today></span>` |
| `data-uv-today` | 今日 UV | `<span data-uv-today></span>` |
| `data-pv-site` | 累计 PV | `<span data-pv-site></span>` |
| `data-uv-site` | 累计 UV | `<span data-uv-site></span>` |
| `data-pv-page` | 页面阅读量 | `<span data-pv-page=""></span>` |
| `data-pv-top="N"` | 热门 Top N | `<ol data-pv-top="10"></ol>` |
| `data-counter-style` | 展示风格 | `badge` / `card` / `bordered` / `default` |
| `data-counter-api` | 自定义 API 地址 | 适用于 JS 部署到 CDN 场景 |

### SPA 客户端路由

VitePress、Rspress、Next.js 等框架的客户端路由切换不会整页刷新。v0.2.0 起内置 `MutationObserver`，自动检测 DOM 变化并刷新计数器，无需任何额外配置。

### JSX/TSX 注意事项

在 React/Rspress MDX 中使用 `data-pv-page` 必须写空字符串：

```tsx
<span data-pv-page=""></span>       // ✅ 正确
<span data-pv-page></span>          // ❌ 渲染为 data-pv-page="true"
```

## Agent Skill（推荐）

内置 Claude Code Skills，涵盖完整集成和部署流程，自动处理框架特有坑点：

| Skill | 适用框架 |
|-------|---------|
| `rspress-web-counter` | Rspress — head 配置、footer 统计、afterDocContent 阅读量、排行榜页面、Caddy/Nginx 反代 |
| `vitepress-web-counter` | VitePress — Vue SFC 组件、`doc-footer-before` 插槽、自定义 theme 布局、部署配置 |

在 Claude Code 对话中包含框架名即可自动加载。

## CLI 命令

```bash
web-counter start              # 后台启动
web-counter stop               # 优雅停止
web-counter restart            # 重启
web-counter createsuperuser    # 创建管理员
web-counter export-js          # 导出 counter.js
```

## 配置

优先级：**CLI 参数 > 环境变量 > .env 文件**

| 参数 | 环境变量 | 默认值 | 说明 |
|------|------|--------|------|
| `--salt` | `COUNTER_SALT` | 必填 | IP 哈希盐值 |
| `--host` | `COUNTER_HOST` | `0.0.0.0` | 监听地址 |
| `--port` | `COUNTER_PORT` | `8000` | 监听端口 |
| `--db-path` | `COUNTER_DB_PATH` | `./data/counter.db` | SQLite 数据文件 |
| `--pid-file` | `COUNTER_PID_FILE` | `./data/counter.pid` | PID 文件 |
| `--allowed-origins` | `COUNTER_ALLOWED_ORIGINS` | `*` | CORS 域名（同域部署无需配置） |
| `--rate-limit` | `COUNTER_RATE_LIMIT` | `60` | 每 IP 每分钟请求上限 |

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/visit` | 记录访问 |
| GET | `/api/count?paths=/a,/b` | 批量查询 |
| GET | `/api/top?limit=10` | 排行榜 |
| GET | `/api/health` | 健康检查 |
| GET | `/dashboard` | 统计看板（需登录） |
| POST | `/api/admin/login` | 管理员登录 |
| POST | `/api/admin/logout` | 退出 |
| POST | `/api/admin/reset` | 重置数据（需登录） |
| GET/POST | `/api/admin/offset` | 起始值（需登录） |

## 生产部署

### Caddy 同域反代（推荐）

```
mysite.site {
    handle /counter.js { reverse_proxy 127.0.0.1:8000 }
    handle /api/*      { reverse_proxy 127.0.0.1:8000 }
    handle /dashboard  { reverse_proxy 127.0.0.1:8000 }
    root * /var/www/mysite
    file_server
}
```

### systemd 守护

```ini
[Service]
Type=simple
Environment="COUNTER_SALT=<密钥>"
Environment="COUNTER_HOST=127.0.0.1"
Environment="COUNTER_PORT=8000"
ExecStart=python3 -m uvicorn web_counter.main:app --host 127.0.0.1 --port 8000
Restart=on-failure
```

> 绑 `127.0.0.1` 确保不直接暴露公网，所有请求经反代进入。

### Docker

```bash
docker compose up -d
```

### 自动部署流水线

```
push main → GitHub Actions 构建
               ↓
       sync-to-gitee 镜像
               ↓
     服务器 cron git pull
               ↓
       Caddy / Nginx 静态 serve
```

完整示例见 [DEPLOY.md](./DEPLOY.md)。

## 数据管理

Dashboard 登录后可进行：

- **数据重置** — 重置今日 / 全部 / 指定页面，全部重置需二次确认
- **起始值** — 为累计 PV/UV 设置偏移量，适用于从其他统计工具迁入
- **排行榜排除** — 支持 `*` 通配符排除首页、目录页等，持久化存储

## License

MIT
