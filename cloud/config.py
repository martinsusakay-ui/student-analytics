"""
config.py - Environment configuration untuk FastAPI
"""

import os
from pathlib import Path

# ============================================================
# ENVIRONMENT
# ============================================================
# Railway akan inject DATABASE_URL secara otomatis
# Format: postgresql://user:password@host:port/dbname
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/moodle_analytics"
)

# PostgreSQL butuh prefix postgresql:// (bukan postgres://)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# ============================================================
# APP CONFIG
# ============================================================
APP_NAME = "Moodle Activity API"
APP_VERSION = "1.0.0"

# ============================================================
# CORS
# ============================================================
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8501",
    "http://127.0.0.1:8501",
]

# Kalau di Railway, tambahkan domain publik
RAILWAY_DOMAIN = os.getenv("RAILWAY_PUBLIC_DOMAIN")
if RAILWAY_DOMAIN:
    CORS_ORIGINS.append(f"https://{RAILWAY_DOMAIN}")