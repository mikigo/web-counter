# web-counter 部署示例

本文以真实场景为例，演示如何将 web-counter 部署到云服务器，并为静态网站接入访问统计。

## 场景概述

- **服务器**：Ubuntu 22.04，已安装 Caddy 作为 Web 服务器
- **网站**：Rspress 静态站点，部署在 `/var/www/mysite`
- **域名**：`mysite.site`，已配置 DNS 并开启 HTTPS
- **目标**：同域部署 web-counter，通过 `/counter.js` 和 `/api/*` 提供服务

最终效果：

```
https://mysite.site              → 静态网站
https://mysite.site/counter.js   → web-counter JS 脚本
https://mysite.site/api/*        → web-counter API
https://mysite.site/dashboard    → 统计看板（内网或认证访问）
```

## 第一步：安装 web-counter

SSH 登录服务器，安装依赖和 web-counter：

```bash
pip3 install web-counter
```

## 第二步：生成 salt 并创建管理员

```bash
# 生成随机 salt（务必保存好，更换后 UV 数据会丢失）
export COUNTER_SALT="$(openssl rand -hex 16)"
echo "COUNTER_SALT=$COUNTER_SALT"  # 记下来，后续要用

# 初始化数据库并创建管理员
export COUNTER_DB_PATH="/opt/web-counter/data/counter.db"
web-counter createsuperuser
# 按提示输入用户名和密码
```

## 第三步：配置 systemd 服务

创建 `/etc/systemd/system/web-counter.service`：

```ini
[Unit]
Description=web-counter
After=network.target

[Service]
Type=simple
Environment="COUNTER_SALT=<你的salt>"
Environment="COUNTER_DB_PATH=/opt/web-counter/data/counter.db"
Environment="COUNTER_HOST=127.0.0.1"
Environment="COUNTER_PORT=8001"
WorkingDirectory=/opt/web-counter
ExecStart=/usr/bin/python3 -m uvicorn web_counter.main:app --host 127.0.0.1 --port 8001
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
```

> **安全说明**：`COUNTER_HOST=127.0.0.1` 确保 web-counter 仅监听本地回环地址，不暴露到公网。外部请求通过 Caddy/Nginx 反代进入。

启动并启用开机自启：

```bash
systemctl daemon-reload
systemctl start web-counter
systemctl enable web-counter
systemctl status web-counter   # 确认 active (running)
```

验证本地服务：

```bash
curl http://127.0.0.1:8001/api/health
# → {"status":"ok"}
```

## 第四步：配置反向代理

### 方案 A：Caddy

编辑 `/etc/caddy/Caddyfile`，在站点配置中添加反代规则：

```
mysite.site, www.mysite.site {
    handle /counter.js {
        reverse_proxy 127.0.0.1:8001
    }
    handle /api/* {
        reverse_proxy 127.0.0.1:8001
    }
    handle /dashboard {
        reverse_proxy 127.0.0.1:8001
    }
    root * /var/www/mysite
    file_server
}
```

重载配置：

```bash
caddy fmt --overwrite /etc/caddy/Caddyfile
caddy reload --config /etc/caddy/Caddyfile
```

### 方案 B：Nginx

```nginx
server {
    listen 443 ssl http2;
    server_name mysite.site www.mysite.site;

    ssl_certificate     /etc/ssl/mysite.site.pem;
    ssl_certificate_key /etc/ssl/mysite.site.key;

    root /var/www/mysite;

    # web-counter 接口转发
    location /counter.js  { proxy_pass http://127.0.0.1:8001; }
    location /api/        { proxy_pass http://127.0.0.1:8001; }
    location /dashboard   { proxy_pass http://127.0.0.1:8001; }

    # 其余走静态文件
    location / {
        try_files $uri $uri.html $uri/ =404;
    }
}

server {
    listen 80;
    server_name mysite.site www.mysite.site;
    return 301 https://$host$request_uri;
}
```

重载 Nginx：

```bash
nginx -t && nginx -s reload
```

## 第五步：验证部署

```bash
# 健康检查
curl https://mysite.site/api/health
# → {"status":"ok"}

# JS 脚本
curl https://mysite.site/counter.js
# → /** web-counter frontend script ... */

# 记录一次访问
curl -X POST https://mysite.site/api/visit \
  -H 'Content-Type: application/json' \
  -d '{"path":"/test"}'
# → {"status":"ok"}

# 查询计数
curl https://mysite.site/api/count?paths=/test
# → {"today_pv":1,"today_uv":1,"site_pv":1,"site_uv":1,"pages":{"/test":1}}
```

浏览器访问 `https://mysite.site/dashboard`，用创建的管理员账号登录，查看统计看板。

## 第六步：接入网站前端

### Rspress 等静态站点生成器

全局脚本通过 `head` 配置加载（注意不要带 `async: true`，Rspress 布尔属性序列化有 bug 会导致属性粘连）：

```ts
// rspress.config.ts
export default defineConfig({
  head: [
    ['script', { src: '/counter.js' }],  // 不加 async/defer 避免序列化 bug
  ],
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
});
```

页面阅读量（`data-pv-page`）应在主题布局的 `afterDocContent` 插槽中添加，这样只出现在文章页而非首页：

```tsx
// theme/index.tsx
const Layout = () => (
  <BasicLayout
    afterDocContent={
      <div>
        <span style={{ display: "none" }} className="counter-container">
          阅读量 <span data-pv-page=""></span> 次
        </span>
        {/* 其他内容 */}
      </div>
    }
  />
);
```

> **JSX 注意**：`data-pv-page` 必须显式写为空字符串 `data-pv-page=""`，否则 React 渲染为 `data-pv-page="true"` 导致路径错误。

> **已知问题**：Rspress `head` 配置中 `{ async: true, src: '...' }` 会渲染为 `<script asyncsrc="...">`（属性粘连）。去掉布尔属性即可正常渲染。

### 普通 HTML 网站

在 `</body>` 前添加：

```html
<script async src="/counter.js"></script>

<span style="display:none" class="counter-container" data-counter-style="card">
  本站访问次数 <span data-pv-site></span> 次 ·
  今日访问量 <span data-pv-today></span> 次 ·
  今日访客 <span data-uv-today></span> 人
</span>
```

> **要点**：使用相对路径 `/counter.js` 同域加载，无需配置 `data-counter-api`，counter.js 会自动推断 API 地址。

### SPA（Vue / React）

路由切换时手动上报：

```js
router.afterEach(() => {
  fetch('/api/visit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path: window.location.pathname })
  });
});
```

## 第七步：数据备份（推荐）

SQLite 数据文件为单文件，直接复制即可备份：

```bash
# 手动备份
cp /opt/web-counter/data/counter.db /backup/counter-$(date +%Y%m%d).db

# 或添加 crontab 定时任务
0 3 * * * cp /opt/web-counter/data/counter.db /backup/counter-$(date +\%Y\%m\%d).db
```

## 自动化部署流程（可选）

如果静态站点通过 GitHub Actions 构建，可用以下流程实现 push 后自动上线：

```
push main → GitHub Actions 构建 → gh-pages 分支
                                      ↓
                        sync-to-gitee（全分支镜像）
                                      ↓
                        服务器 crontab git pull
                                      ↓
                              Web 服务器直接 serve
```

**GitHub Actions deploy.yml**（构建并部署到 gh-pages）：

```yaml
name: Deploy
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pnpm install && pnpm build   # 替换为你的构建命令
      - uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: doc_build
```

**GitHub Actions sync-to-gitee.yml**（镜像到 Gitee）：

```yaml
name: Sync to Gitee
on:
  workflow_run:
    workflows: ["Deploy"]
    types: [completed]
jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: wearerequired/git-mirror-action@v1
        with:
          source-repo: https://github.com/${{ github.repository }}.git
          destination-repo: https://gitee.com/<你的用户名>/<仓库名>.git
```

**服务器 crontab**（每小时拉取）：

```bash
0 8-20 * * * cd /var/www/mysite && git pull
```

服务器首次设置时需要克隆 gh-pages 分支：

```bash
git clone -b gh-pages https://gitee.com/<用户名>/<仓库名>.git /var/www/mysite
```

## 可选：限制 Dashboard 访问

如果不想公开 Dashboard，可通过 IP 白名单或 basic auth 限制：

### Caddy IP 白名单

```
handle /dashboard {
    @allowed remote_ip 10.0.0.0/8 172.16.0.0/12
    handle @allowed {
        reverse_proxy 127.0.0.1:8001
    }
    respond "Access Denied" 403
}
```

## 常见问题

**Q: 更换 salt 后 UV 数据不准确？**

A: salt 是访客去重的关键。更换 salt 后所有访客标识会重新计算，UV 计数从零开始。设定 salt 后请勿更改。

**Q: 计数器不显示？**

A: 检查浏览器控制台 Network 面板，确认 `/counter.js` 和 `/api/count` 请求正常返回 200。计数器容器初始为 `display:none`，仅在成功获取数据后才显示，后端不可用时自动隐藏。

**Q: 数据量大了性能如何？**

A: SQLite WAL 模式在百万级数据量下查询仍在毫秒级。如需更大规模，可考虑定期归档旧数据。

**Q: 端口被占用怎么办？**

A: 修改 `COUNTER_PORT` 环境变量更换端口，同时更新反向代理配置中的端口号。
