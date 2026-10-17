"""
config.py - Environment configuration untuk FastAPI
"""

import os
from pathlib import Path

# ============================================================
# ENVIRONMENT
# ============================================================
# Ambil dari environment
_env_url = os.getenv("DATABASE_URL", "").strip()

# 1. Jika kosong, gunakan fallback localhost (untuk testing lokal)
if not _env_url:
    DATABASE_URL = "postgresql://postgres:password@localhost:5432/moodle_analytics"
else:
    # 2. Bersihkan tanda kutip jika tidak sengaja ter-copy
    _env_url = _env_url.strip('"').strip("'")
    
    # 3. PostgreSQL butuh prefix postgresql:// (bukan postgres://)
    if _env_url.startswith("postgres://"):
        DATABASE_URL = _env_url.replace("postgres://", "postgresql://", 1)
    else:
        DATABASE_URL = _env_url

# (Opsional) Tambahkan print agar kita bisa melihatnya di log Railway
print(f"[CONFIG] DB Scheme: {DATABASE_URL.split('://')[0] if DATABASE_URL else 'EMPTY'}")

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