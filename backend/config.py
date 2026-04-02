"""
Configuration module. Reads API keys from .env file or environment.
"""

import os
from pathlib import Path

env_path = Path(__file__).parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

# AI Engine API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# SERP API
SERP_API_KEY = os.getenv("SERP_API_KEY", "")

# Desactivar motores opcionales (1/true/yes = activo; 0/false/no = desactivado)
def _env_flag(name: str, default: bool = True) -> bool:
    v = os.getenv(name)
    if v is None or v.strip() == "":
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


ENABLE_PERPLEXITY = _env_flag("ENABLE_PERPLEXITY", True)
ENABLE_SERP = _env_flag("ENABLE_SERP", True)

# MySQL Database
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "cleexs_tools")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")

# Monitoring notifications
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")

# Omitir DB (para pruebas; luego se puede cambiar a PostgreSQL)
SKIP_DB = os.getenv("SKIP_DB", "").lower() in ("1", "true", "yes")
