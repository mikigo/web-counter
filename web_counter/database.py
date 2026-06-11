"""Async SQLite database operations using aiosqlite."""

import datetime
import os
from pathlib import Path
from typing import Dict, List, Optional

import aiosqlite


async def _connect(db_path: str) -> aiosqlite.Connection:
    """Create a database connection with WAL mode enabled."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(str(db_path))
    await db.execute("PRAGMA journal_mode=WAL")
    return db


async def init_db(db_path: str):
    """Initialize database tables and indexes."""
    db = await _connect(db_path)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL,
            visitor_hash TEXT NOT NULL,
            visit_date TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS offsets (
            key TEXT PRIMARY KEY,
            value INTEGER NOT NULL DEFAULT 0
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS page_titles (
            path TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)

    await db.execute("CREATE INDEX IF NOT EXISTS idx_visits_path ON visits(path)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_visits_hash ON visits(visitor_hash)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_visits_date ON visits(visit_date)")

    await db.commit()
    await db.close()


async def record_visit(db_path: str, path: str, visitor_hash: str):
    """Record a page visit."""
    today = datetime.date.today().isoformat()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db = await _connect(db_path)
    await db.execute(
        "INSERT INTO visits (path, visitor_hash, visit_date, created_at) VALUES (?, ?, ?, ?)",
        (path, visitor_hash, today, now),
    )
    await db.commit()
    await db.close()


async def get_counts(db_path: str, paths: str = ""):
    """Get today PV/UV, site PV/UV, and per-page counts (with offsets)."""
    today = datetime.date.today().isoformat()
    db = await _connect(db_path)

    # Today PV
    cursor = await db.execute("SELECT COUNT(*) FROM visits WHERE visit_date = ?", (today,))
    row = await cursor.fetchone()
    today_pv = row[0] if row else 0

    # Today UV
    cursor = await db.execute(
        "SELECT COUNT(DISTINCT visitor_hash) FROM visits WHERE visit_date = ?", (today,)
    )
    row = await cursor.fetchone()
    today_uv = row[0] if row else 0

    # Site PV
    cursor = await db.execute("SELECT COUNT(*) FROM visits")
    row = await cursor.fetchone()
    actual_site_pv = row[0] if row else 0

    cursor = await db.execute("SELECT value FROM offsets WHERE key = ?", ("site_pv",))
    row = await cursor.fetchone()
    site_pv_offset = row[0] if row else 0
    site_pv = actual_site_pv + site_pv_offset

    # Site UV
    cursor = await db.execute("SELECT COUNT(DISTINCT visitor_hash) FROM visits")
    row = await cursor.fetchone()
    actual_site_uv = row[0] if row else 0

    cursor = await db.execute("SELECT value FROM offsets WHERE key = ?", ("site_uv",))
    row = await cursor.fetchone()
    site_uv_offset = row[0] if row else 0
    site_uv = actual_site_uv + site_uv_offset

    # Per-page counts
    pages = {}
    if paths:
        for p in paths.split(","):
            p = p.strip()
            if not p:
                continue
            cursor = await db.execute("SELECT COUNT(*) FROM visits WHERE path = ?", (p,))
            row = await cursor.fetchone()
            actual = row[0] if row else 0

            cursor = await db.execute("SELECT value FROM offsets WHERE key = ?", (f"page_{p}",))
            row = await cursor.fetchone()
            offset = row[0] if row else 0
            pages[p] = actual + offset

    await db.close()
    return today_pv, today_uv, site_pv, site_uv, pages


async def save_page_title(db_path: str, path: str, title: str):
    """Save or update the title for a page path."""
    if not title:
        return
    db = await _connect(db_path)
    await db.execute(
        "INSERT OR REPLACE INTO page_titles (path, title, updated_at) VALUES (?, ?, datetime('now','localtime'))",
        (path, title.strip()),
    )
    await db.commit()
    await db.close()


async def reset_data(db_path: str, scope: str, path: str = None):
    """Reset visit data by scope."""
    today = datetime.date.today().isoformat()
    db = await _connect(db_path)

    if scope == "today":
        await db.execute("DELETE FROM visits WHERE visit_date = ?", (today,))
    elif scope == "all":
        await db.execute("DELETE FROM visits")
    elif scope == "page" and path:
        await db.execute("DELETE FROM visits WHERE path = ?", (path,))

    await db.commit()
    await db.close()


async def get_offsets(db_path: str) -> Dict:
    """Get all offset values."""
    db = await _connect(db_path)
    cursor = await db.execute("SELECT key, value FROM offsets")
    rows = await cursor.fetchall()
    result = {}
    for row in rows:
        result[row[0]] = row[1]
    await db.close()
    return result


async def set_offsets(db_path: str, data: Dict):
    """Set offset values."""
    db = await _connect(db_path)

    if data.get("site_pv") is not None:
        await db.execute(
            "INSERT OR REPLACE INTO offsets (key, value) VALUES (?, ?)",
            ("site_pv", data["site_pv"]),
        )
    if data.get("site_uv") is not None:
        await db.execute(
            "INSERT OR REPLACE INTO offsets (key, value) VALUES (?, ?)",
            ("site_uv", data["site_uv"]),
        )
    if data.get("pages"):
        for page_path, value in data["pages"].items():
            await db.execute(
                "INSERT OR REPLACE INTO offsets (key, value) VALUES (?, ?)",
                (f"page_{page_path}", value),
            )

    await db.commit()
    await db.close()


async def create_admin(db_path: str, username: str, password_hash: str):
    """Create or update an admin user."""
    db = await _connect(db_path)
    await db.execute(
        "INSERT OR REPLACE INTO admin_users (username, password_hash) VALUES (?, ?)",
        (username, password_hash),
    )
    await db.commit()
    await db.close()


async def get_admin(db_path: str, username: str) -> Optional[Dict]:
    """Get admin user by username."""
    db = await _connect(db_path)
    cursor = await db.execute(
        "SELECT username, password_hash FROM admin_users WHERE username = ?", (username,)
    )
    row = await cursor.fetchone()
    await db.close()
    if row:
        return {"username": row[0], "password_hash": row[1]}
    return None


async def get_daily_stats(db_path: str, days: int = 30) -> List:
    """Get daily PV/UV stats for the last N days."""
    today = datetime.date.today()
    day_list = [(today - datetime.timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]

    db = await _connect(db_path)
    results = []
    for day in day_list:
        cursor = await db.execute("SELECT COUNT(*) FROM visits WHERE visit_date = ?", (day,))
        pv_row = await cursor.fetchone()

        cursor = await db.execute(
            "SELECT COUNT(DISTINCT visitor_hash) FROM visits WHERE visit_date = ?", (day,)
        )
        uv_row = await cursor.fetchone()

        results.append({
            "date": day,
            "pv": pv_row[0] if pv_row else 0,
            "uv": uv_row[0] if uv_row else 0,
        })
    await db.close()
    return results


async def get_top_pages(db_path: str, limit: int = 0, exclude: str = "") -> List:
    """Get top pages by total view count. exclude supports * wildcards (e.g. */index.html)."""
    from urllib.parse import unquote
    db = await _connect(db_path)

    # If limit not explicitly set, check for stored setting (managed via dashboard)
    if limit <= 0:
        cursor = await db.execute("SELECT value FROM offsets WHERE key = ?", ("top_limit",))
        row = await cursor.fetchone()
        if row and row[0]:
            try:
                limit = int(row[0])
            except (ValueError, TypeError):
                limit = 10
        if limit <= 0:
            limit = 10

    exclude_list = [p.strip() for p in exclude.split(",") if p.strip()]
    if not exclude_list:
        cursor = await db.execute("SELECT value FROM offsets WHERE key = ?", ("top_exclude",))
        row = await cursor.fetchone()
        if row and row[0]:
            exclude_list = [p.strip() for p in row[0].split(",") if p.strip()]
        else:
            exclude_list = ["/", "*/index.html"]

    # Separate wildcard (*) and exact excludes
    wild_excludes = [p.replace("*", "%") for p in exclude_list if "*" in p]
    exact_excludes = [p for p in exclude_list if "*" not in p]

    # Build WHERE clause
    conditions = []
    params = []
    if exact_excludes:
        conditions.append(f"path NOT IN ({','.join('?' * len(exact_excludes))})")
        params.extend(exact_excludes)
    for w in wild_excludes:
        conditions.append("path NOT LIKE ?")
        params.append(w)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    cursor = await db.execute(
        f"SELECT path, COUNT(*) as cnt FROM visits {where} GROUP BY path ORDER BY cnt DESC LIMIT ?",
        (*params, limit)
    )
    rows = await cursor.fetchall()

    # Get all page offsets at once
    cursor = await db.execute("SELECT key, value FROM offsets WHERE key LIKE 'page_%'")
    offset_rows = await cursor.fetchall()
    offsets = {}
    for row in offset_rows:
        page_path = row[0][5:]
        offsets[page_path] = row[1]

    # Get titles for top pages
    title_map = {}
    if rows:
        path_list = [row[0] for row in rows]
        t_placeholders = ",".join(["?"] * len(path_list))
        cursor = await db.execute(
            f"SELECT path, title FROM page_titles WHERE path IN ({t_placeholders})",
            path_list
        )
        for trow in await cursor.fetchall():
            title_map[trow[0]] = trow[1]

    results = []
    for row in rows:
        path = row[0]
        count = row[1] + offsets.get(path, 0)
        decoded = unquote(path)
        results.append({
            "path": decoded,
            "title": title_map.get(path, decoded),
            "count": count,
        })

    await db.close()
    return results
