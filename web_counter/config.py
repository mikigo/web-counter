"""Configuration management.

Priority (highest to lowest): CLI arguments > environment variables > .env file.
"""

import os
from pathlib import Path


def _load_dotenv():
    """Load .env file from current working directory if it exists."""
    env_path = Path.cwd() / ".env"
    if not env_path.exists():
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


_load_dotenv()


class Config:
    """Application configuration."""

    def __init__(self, **kwargs):
        self.salt = kwargs.get("salt") or os.environ.get("COUNTER_SALT", "")
        self.host = kwargs.get("host") or os.environ.get("COUNTER_HOST", "0.0.0.0")
        self.port = int(kwargs.get("port") or os.environ.get("COUNTER_PORT", "8000"))
        self.db_path = kwargs.get("db_path") or os.environ.get("COUNTER_DB_PATH", "./data/counter.db")
        self.pid_file = kwargs.get("pid_file") or os.environ.get("COUNTER_PID_FILE", "./data/counter.pid")
        self.allowed_origins = kwargs.get("allowed_origins") or os.environ.get("COUNTER_ALLOWED_ORIGINS", "*")
        self.rate_limit = int(kwargs.get("rate_limit") or os.environ.get("COUNTER_RATE_LIMIT", "60"))

    def validate(self):
        """Validate required configuration."""
        if not self.salt:
            raise ValueError(
                "COUNTER_SALT is required. Set it via --salt, COUNTER_SALT env var, "
                "or .env file.\nGenerate one with: openssl rand -hex 16"
            )
