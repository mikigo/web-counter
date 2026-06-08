"""CLI: start, restart, stop, createsuperuser, export-js."""

import argparse
import asyncio
import os
import signal
import subprocess
import sys
import time
from pathlib import Path


def _read_pid(pid_file: str) -> int | None:
    """Read PID from file."""
    try:
        with open(pid_file, "r") as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return None


def _is_running(pid: int | None) -> bool:
    """Check if a process with given PID is running."""
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def start_command(args):
    """Start the web-counter server in the background."""
    from .config import Config

    config = Config(
        salt=args.salt,
        host=args.host,
        port=args.port,
        db_path=args.db_path,
        pid_file=args.pid_file,
        allowed_origins=args.allowed_origins,
        rate_limit=args.rate_limit,
    )
    config.validate()

    # Check if already running
    pid = _read_pid(config.pid_file)
    if _is_running(pid):
        print(f"✗ web-counter 已在运行中 (PID: {pid})")
        sys.exit(1)

    # Ensure data directory exists
    Path(config.db_path).parent.mkdir(parents=True, exist_ok=True)
    Path(config.pid_file).parent.mkdir(parents=True, exist_ok=True)

    # Build command
    cmd = [
        sys.executable, "-m", "uvicorn", "web_counter.main:app",
        "--host", config.host,
        "--port", str(config.port),
        "--log-level", "info",
    ]

    # Set environment variables for the subprocess
    env = os.environ.copy()
    env["COUNTER_SALT"] = config.salt
    env["COUNTER_HOST"] = config.host
    env["COUNTER_PORT"] = str(config.port)
    env["COUNTER_DB_PATH"] = config.db_path
    env["COUNTER_PID_FILE"] = config.pid_file
    env["COUNTER_ALLOWED_ORIGINS"] = config.allowed_origins
    env["COUNTER_RATE_LIMIT"] = str(config.rate_limit)

    # Start process (background)
    proc = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )

    # Write PID file
    with open(config.pid_file, "w") as f:
        f.write(str(proc.pid))

    origin = f"http://{config.host}:{config.port}"
    print(f"✓ web-counter 已启动，监听 {origin}")
    print()
    print("---------- 复制以下代码到网页 </body> 前 ----------")
    print()
    print(f'<script async src="{origin}/counter.js"></script>')
    print()
    print('<span style="display:none" class="counter-container" data-counter-style="card">')
    print("  本站访问次数 <span data-pv-site></span> 次 ·")
    print("  今日访问量 <span data-pv-today></span> 次 ·")
    print("  今日访客 <span data-uv-today></span> 人 ·")
    print("  总访问量 <span data-pv-site></span> 次 ·")
    print("  总访客 <span data-uv-site></span> 人")
    print("</span>")
    print()
    print("------------------------------------------------------")


def stop_command(args):
    """Stop the running web-counter server."""
    from .config import Config

    config = Config(pid_file=args.pid_file)

    pid = _read_pid(config.pid_file)
    if not _is_running(pid):
        print("✗ web-counter 未在运行")
        if Path(config.pid_file).exists():
            Path(config.pid_file).unlink()
        sys.exit(1)

    # Send SIGTERM for graceful shutdown
    os.kill(pid, signal.SIGTERM)

    # Wait for process to exit (max 10 seconds)
    for _ in range(100):
        if not _is_running(pid):
            break
        time.sleep(0.1)

    if _is_running(pid):
        print(f"✗ 无法停止进程 (PID: {pid})，尝试强制终止...")
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass
        time.sleep(0.5)

    # Clean up PID file
    if Path(config.pid_file).exists():
        Path(config.pid_file).unlink()

    print("✓ web-counter 已停止")


def restart_command(args):
    """Restart the web-counter server."""
    print("正在重启 web-counter...")
    stop_command(args)
    start_command(args)


def createsuperuser_command(args):
    """Create an admin user interactively."""
    from .config import Config
    from .database import init_db, create_admin
    from .auth import hash_password

    config = Config(
        salt="dummy",
        db_path=args.db_path,
    )

    username = input("Username: ").strip()
    if not username:
        print("✗ 用户名不能为空")
        sys.exit(1)

    password = input("Password: ").strip()
    if not password:
        print("✗ 密码不能为空")
        sys.exit(1)

    confirm = input("Confirm password: ").strip()
    if password != confirm:
        print("✗ 两次输入的密码不一致")
        sys.exit(1)

    async def _create():
        await init_db(config.db_path)
        password_hash = hash_password(password)
        await create_admin(config.db_path, username, password_hash)

    asyncio.run(_create())
    print(f"✓ 管理员 {username} 创建成功")


def export_js_command(args):
    """Export counter.js to stdout."""
    js_path = Path(__file__).parent / "static" / "counter.js"
    print(js_path.read_text(encoding="utf-8"))


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="web-counter",
        description="A self-hosted website visit counter",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # start
    p = subparsers.add_parser("start", help="Start the server in background")
    p.add_argument("--salt", default=None, help="IP hash salt (required)")
    p.add_argument("--host", default=None, help="Listen address (default: 0.0.0.0)")
    p.add_argument("--port", type=int, default=None, help="Listen port (default: 8000)")
    p.add_argument("--db-path", default=None, help="SQLite database path")
    p.add_argument("--pid-file", default=None, help="PID file path")
    p.add_argument("--allowed-origins", default=None, help="CORS allowed origins")
    p.add_argument("--rate-limit", type=int, default=None, help="Rate limit per IP per minute")

    # restart
    p = subparsers.add_parser("restart", help="Restart the server")
    p.add_argument("--salt", default=None, help="IP hash salt")
    p.add_argument("--host", default=None, help="Listen address")
    p.add_argument("--port", type=int, default=None, help="Listen port")
    p.add_argument("--db-path", default=None, help="SQLite database path")
    p.add_argument("--pid-file", default=None, help="PID file path")
    p.add_argument("--allowed-origins", default=None, help="CORS allowed origins")
    p.add_argument("--rate-limit", type=int, default=None, help="Rate limit per IP per minute")

    # stop
    p = subparsers.add_parser("stop", help="Stop the server")
    p.add_argument("--pid-file", default=None, help="PID file path")

    # createsuperuser
    p = subparsers.add_parser("createsuperuser", help="Create an admin user")
    p.add_argument("--db-path", default=None, help="SQLite database path")

    # export-js
    subparsers.add_parser("export-js", help="Export counter.js to stdout")

    args = parser.parse_args()

    if args.command == "start":
        start_command(args)
    elif args.command == "restart":
        restart_command(args)
    elif args.command == "stop":
        stop_command(args)
    elif args.command == "createsuperuser":
        createsuperuser_command(args)
    elif args.command == "export-js":
        export_js_command(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
