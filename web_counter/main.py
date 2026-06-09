"""FastAPI application with all routes."""

import hashlib
import logging
from pathlib import Path

from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse, Response

from .auth import (
    create_session,
    destroy_session,
    validate_session,
    verify_password,
)
from .config import Config
from .dashboard import get_dashboard_html, get_login_html
from .database import (
    get_admin,
    get_counts,
    get_daily_stats,
    get_offsets,
    get_top_pages,
    init_db,
    record_visit,
    reset_data,
    save_page_title,
    set_offsets,
)
from .models import LoginRequest, OffsetRequest, ResetRequest, VisitRequest
from .rate_limit import RateLimiter

logger = logging.getLogger("web-counter")


def create_app(config: Config | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    if config is None:
        config = Config()

    config.validate()

    app = FastAPI(title="web-counter")
    limiter = RateLimiter(config.rate_limit)

    # CORS
    origins = [o.strip() for o in config.allowed_origins.split(",")]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.on_event("startup")
    async def startup():
        await init_db(config.db_path)

    # --- Static file: counter.js ---
    @app.get("/counter.js")
    async def counter_js():
        js_path = Path(__file__).parent / "static" / "counter.js"
        content = js_path.read_text(encoding="utf-8")
        return Response(content, media_type="application/javascript")

    # --- Health check ---
    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    # --- Record visit ---
    @app.post("/api/visit")
    async def visit(request: Request, body: VisitRequest, background_tasks: BackgroundTasks):
        ip = request.client.host if request.client else "127.0.0.1"
        if not limiter.check(ip):
            raise HTTPException(429, "Too many requests")

        visitor_hash = hashlib.sha256(
            (ip + config.salt).encode("utf-8")
        ).hexdigest()

        background_tasks.add_task(record_visit, config.db_path, body.path, visitor_hash)
        if body.title:
            background_tasks.add_task(save_page_title, config.db_path, body.path, body.title)
        logger.info("Visit: path=%s visitor=%s", body.path, visitor_hash[:8])
        return {"status": "ok"}

    # --- Get counts ---
    @app.get("/api/count")
    async def count(paths: str = ""):
        today_pv, today_uv, site_pv, site_uv, pages = await get_counts(config.db_path, paths)
        return {
            "today_pv": today_pv,
            "today_uv": today_uv,
            "site_pv": site_pv,
            "site_uv": site_uv,
            "pages": pages,
        }

    # --- Get top pages ---
    @app.get("/api/top")
    async def top_pages(limit: int = 10, exclude: str = ""):
        return await get_top_pages(config.db_path, limit, exclude)

    # --- Auth helper ---
    def _get_user(request: Request) -> str | None:
        token = request.cookies.get("session")
        if not token:
            return None
        return validate_session(token)

    # --- Dashboard ---
    @app.get("/dashboard")
    async def dashboard(request: Request):
        user = _get_user(request)
        if not user:
            return HTMLResponse(get_login_html())

        today_pv, today_uv, site_pv, site_uv, _ = await get_counts(config.db_path, "")
        offsets = await get_offsets(config.db_path)
        daily_stats = await get_daily_stats(config.db_path, 30)

        return HTMLResponse(get_dashboard_html(
            today_pv=today_pv,
            today_uv=today_uv,
            site_pv=site_pv,
            site_uv=site_uv,
            offsets=offsets,
            daily_stats=daily_stats,
        ))

    # --- Admin: Login (JSON API) ---
    @app.post("/api/admin/login")
    async def admin_login(body: LoginRequest):
        admin = await get_admin(config.db_path, body.username)
        if not admin or not verify_password(body.password, admin["password_hash"]):
            raise HTTPException(401, "Invalid username or password")

        token = create_session(body.username)
        resp = JSONResponse({"status": "ok", "username": body.username})
        resp.set_cookie(
            "session", token,
            httponly=True, samesite="lax", max_age=86400, path="/",
        )
        return resp

    # --- Admin: Login page POST ---
    @app.post("/dashboard")
    async def dashboard_login(request: Request):
        form = await request.form()
        username = form.get("username", "")
        password = form.get("password", "")
        admin = await get_admin(config.db_path, username)
        if not admin or not verify_password(password, admin["password_hash"]):
            return HTMLResponse(get_login_html("用户名或密码错误"), status_code=401)

        token = create_session(username)
        resp = RedirectResponse(url="/dashboard", status_code=302)
        resp.set_cookie(
            "session", token,
            httponly=True, samesite="lax", max_age=86400, path="/",
        )
        return resp

    # --- Admin: Logout ---
    @app.post("/api/admin/logout")
    async def admin_logout(request: Request):
        token = request.cookies.get("session")
        if token:
            destroy_session(token)
        resp = JSONResponse({"status": "ok"})
        resp.delete_cookie("session", path="/")
        return resp

    # --- Admin: Reset data ---
    @app.post("/api/admin/reset")
    async def admin_reset(body: ResetRequest, request: Request):
        user = _get_user(request)
        if not user:
            raise HTTPException(401, "Not authenticated")
        await reset_data(config.db_path, body.scope, body.path)
        return {"status": "ok"}

    # --- Admin: Get offsets ---
    @app.get("/api/admin/offset")
    async def admin_get_offset(request: Request):
        user = _get_user(request)
        if not user:
            raise HTTPException(401, "Not authenticated")
        return await get_offsets(config.db_path)

    # --- Admin: Set offsets ---
    @app.post("/api/admin/offset")
    async def admin_set_offset(body: OffsetRequest, request: Request):
        user = _get_user(request)
        if not user:
            raise HTTPException(401, "Not authenticated")
        await set_offsets(config.db_path, body.model_dump())
        return {"status": "ok"}

    # --- Admin: Get top exclude ---
    @app.get("/api/admin/top-exclude")
    async def admin_get_top_exclude(request: Request):
        user = _get_user(request)
        if not user:
            raise HTTPException(401, "Not authenticated")
        offsets = await get_offsets(config.db_path)
        val = offsets.get("top_exclude", "")
        limit_val = offsets.get("top_limit", "20")
        return {
            "paths": [p.strip() for p in val.split(",") if p.strip()],
            "limit": int(limit_val) if limit_val.isdigit() else 20,
        }

    # --- Admin: Set top exclude ---
    @app.post("/api/admin/top-exclude")
    async def admin_set_top_exclude(request: Request):
        user = _get_user(request)
        if not user:
            raise HTTPException(401, "Not authenticated")
        body = await request.json()
        paths = body.get("paths", [])
        limit = str(body.get("limit", 20))
        import aiosqlite
        db = await aiosqlite.connect(config.db_path)
        await db.execute("INSERT OR REPLACE INTO offsets (key, value) VALUES (?, ?)",
                         ("top_exclude", ",".join(paths)))
        await db.execute("INSERT OR REPLACE INTO offsets (key, value) VALUES (?, ?)",
                         ("top_limit", limit))
        await db.commit()
        await db.close()
        return {"status": "ok"}

    return app


# Module-level app instance (configured from environment)
app = create_app()
