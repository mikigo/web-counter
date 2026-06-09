# web-counter

一个开源、可自托管的网站访问计数服务。一行命令部署，一行 `<script>` 接入，数据完全由你掌控。

## 统计指标

| 指标 | 含义 |
|------|------|
| 今日访问量 (PV Today) | 今天所有页面的总访问次数 |
| 今日访客数 (UV Today) | 今天的独立访客数（IP + salt 哈希去重） |
| 总访问量 (PV Site) | 建站以来所有页面的累计访问次数 |
| 总访客数 (UV Site) | 建站以来的累计独立访客数 |
| 页面阅读量 (PV Page) | 当前页面的累计访问次数 |

## 快速开始

```bash
# 1. 安装
pip install web-counter

# 2. 设置 salt（必填，用于哈希访客 IP 保护隐私）
export COUNTER_SALT="$(openssl rand -hex 16)"

# 3. 启动
web-counter start

# 4. 创建管理员（用于访问统计看板）
web-counter createsuperuser

# 5. 将终端输出的代码粘贴到网页 </body> 前，完成接入
```

## 前端接入

在网页 `</body>` 前添加以下代码：

```html
<script async src="https://你的域名/counter.js"></script>

<!-- 显示计数（放在 display:none 容器中，JS 加载后自动显示） -->
<span style="display:none" class="counter-container" data-counter-style="card">
  本站访问次数 <span data-pv-site></span> 次 ·
  今日访问量 <span data-pv-today></span> 次 ·
  今日访客 <span data-uv-today></span> 人 ·
  总访客 <span data-uv-site></span> 人
</span>
```

### 数据属性一览

| 属性 | 含义 |
|------|------|
| `data-pv-today` | 今日访问量 |
| `data-uv-today` | 今日访客数 |
| `data-pv-site` | 总访问量 |
| `data-uv-site` | 总访客数 |
| `data-pv-page` | 当前页面阅读量 |
| `data-pv-top` | 热门排行列表，属性值为显示条数（如 `<ol data-pv-top="10">`） |
| `data-counter-style` | 展示风格：`default` / `badge` / `card` / `bordered` |
| `data-counter-api` | 手动指定 API 基地址（JS 独立部署时使用） |

### SPA 支持

v0.2.0 起 counter.js 内置 MutationObserver，自动检测客户端路由切换导致 DOM 变化并重新填充计数器，无需手动处理。

如需在路由切换时上报访问（不影响计数器显示），可在路由守卫中手动调用：

```js
fetch('/api/visit', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ path: window.location.pathname })
})
```

### 页面阅读量

在文章内容区放置 `<span data-pv-page></span>` 即可显示当前页面阅读量。**注意**：在 JSX/TSX 中必须显式写为空字符串 `<span data-pv-page=""></span>`，否则 React 会渲染为 `data-pv-page="true"` 导致路径错误。

## CLI 命令

```bash
web-counter start           # 后台启动服务
web-counter restart         # 重启服务
web-counter stop            # 停止服务
web-counter createsuperuser # 创建管理员账号
web-counter export-js       # 导出 counter.js 到 stdout
```

## 配置

优先级：**CLI 参数 > 环境变量 > .env 文件**

| 参数 | 环境变量 | 默认值 | 说明 |
|------|------|--------|------|
| `--salt` | `COUNTER_SALT` | 无（必填） | IP 哈希盐值 |
| `--host` | `COUNTER_HOST` | `0.0.0.0` | 监听地址 |
| `--port` | `COUNTER_PORT` | `8000` | 监听端口 |
| `--db-path` | `COUNTER_DB_PATH` | `./data/counter.db` | 数据库路径 |
| `--pid-file` | `COUNTER_PID_FILE` | `./data/counter.pid` | PID 文件路径 |
| `--allowed-origins` | `COUNTER_ALLOWED_ORIGINS` | `*` | CORS 允许域名 |
| `--rate-limit` | `COUNTER_RATE_LIMIT` | `60` | 每 IP 每分钟限流 |

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/visit` | 记录访问 |
| GET | `/api/count?paths=/page1,/page2` | 批量查询计数 |
| GET | `/counter.js` | 获取前端 JS 脚本 |
| GET | `/api/health` | 健康检查 |
| GET | `/dashboard` | 统计看板（需登录） |
| POST | `/api/admin/login` | 管理员登录（JSON） |
| POST | `/api/admin/logout` | 退出登录 |
| POST | `/api/admin/reset` | 重置数据（需登录） |
| GET/POST | `/api/admin/offset` | 查看/设置起始值（需登录） |
| GET | `/api/top?limit=10` | 阅读量排行榜 |

## 生产环境部署

### 使用反代 (Caddy)

```
your-domain.com {
    reverse_proxy localhost:8000
}
```

### 使用 systemd

```ini
[Unit]
Description=web-counter
After=network.target

[Service]
Type=forking
PIDFile=/opt/web-counter/data/counter.pid
Environment="COUNTER_SALT=your-random-salt"
ExecStart=/usr/bin/web-counter start
ExecStop=/usr/bin/web-counter stop
ExecReload=/usr/bin/web-counter restart
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

### 使用 Docker

```bash
docker compose up -d
```

## 阅读量排行榜

### 嵌入式组件

在页面中放置 `<ol data-pv-top="10"></ol>` 即可显示热门文章排行。

### API 接口

```bash
curl https://你的域名/api/top?limit=10
# → [{"path":"/blog/hello","title":"文章标题","count":123}, ...]
```

支持 `?exclude=/` 排除指定路径，`*` 通配符匹配（如 `*/index.html`）。

排行榜中的文章标题自动从页面 `<title>` 采集。

### Dashboard 管理

后台 Dashboard 排行榜区域支持配置显示数量、排除路径，设置持久化存储。

## 数据管理

后台登录 `/dashboard` 后可进行：

- **数据重置**：支持重置今日/全部/指定页面的访问数据
- **起始值设置**：为累计指标设置偏移量，适用于从其他统计工具迁移

## 隐私设计

- 不存储原始 IP 地址
- 不设置 Cookie（后台 session cookie 除外）
- 不做浏览器指纹
- 访客唯一性通过 `SHA256(IP + salt)` 标识
- salt 由部署者自行设置，无法被外部反向破解

> **注意**：salt 设定后不要更换，否则历史访客标识失联，UV 统计将清零重来。

## License

MIT
