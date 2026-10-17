"""
config.py - Environment configuration untuk FastAPI
"""

import os
from pathlib import Path

# ============================================================
# ENVIRONMENT & DATABASE URL
# ============================================================
# Ambil dari environment dan bersihkan spasi tersembunyi
_env_url = os.getenv("DATABASE_URL", "").strip()

# Cek apakah kita sedang berjalan di Railway
IS_RAILWAY = os.getenv("RAILWAY_ENVIRONMENT") is not None

if not _env_url:
    if IS_RAILWAY:
        # Jika di Railway tapi URL kosong, JANGAN pakai localhost! Langsung error.
        raise ValueError("CRITICAL: DATABASE_URL is empty in Railway! Please check your Variables Reference.")
    else:
        # Hanya gunakan localhost jika Anda menjalankan kode di laptop/PC sendiri
        DATABASE_URL = "postgresql://postgres:password@localhost:5432/moodle_analytics"
        print("[CONFIG] Warning: Using localhost fallback for local testing.")
else:
    # Bersihkan tanda kutip jika tidak sengaja ter-copy
    _env_url = _env_url.strip('"').strip("'")
    
    # PostgreSQL butuh prefix postgresql:// (bukan postgres://)
    if _env_url.startswith("postgres://"):
        DATABASE_URL = _env_url.replace("postgres://", "postgresql://", 1)
    else:
        DATABASE_URL = _env_url

# Print untuk debugging di Railway Logs
# (Hanya menampilkan skema, tidak menampilkan password/host rahasia)
_scheme = DATABASE_URL.split('://')[0] if DATABASE_URL else 'EMPTY'
print(f"[CONFIG] DB Scheme Detected: {_scheme}")

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