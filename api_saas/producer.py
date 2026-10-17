"""
producer.py - Continuous streaming simulator untuk Moodle logs
Mode: loop tak terbatas dengan rate-limited output.

Cocok untuk demo panjang / monitoring dashboard seharian.
"""

import pandas as pd
import json
import time
from datetime import datetime, timezone
from pathlib import Path

# ============================================================
# KONFIGURASI
# ============================================================
CONFIG = {
    # Input
    "csv_path": "logs_interacoes_anon.csv",
    "output_jsonl": "output/stream_buffer.jsonl",
    
    # Mode continuous
    "continuous": True,           # True = loop tak terbatas
    "events_per_second": 2,       # Intensitas: 2 event/detik (rendah)
    "max_records_per_cycle": None,  # None = semua record per cycle
    
    # Buffer management
    "max_buffer_lines": 50000,    # Potong file kalau > 50k baris
    "truncate_on_start": False,   # False = append, True = overwrite
    
    # HTTP POST (opsional)
    "enable_http": False,
    "http_endpoint": "http://localhost:5000/api/ingest",
    
    # Logging
    "log_every": 10,              # Print progress tiap N event
}

# ============================================================
# FUNGSI
# ============================================================
def parse_event(row, cycle: int) -> dict:
    """Ubah 1 baris CSV jadi dict JSON."""
    return {
        "user_hash": row["user_hash"],
        "courseid": int(row["courseid"]),
        "component": row["component"],
        "eventname": row["eventname"],
        "action": row["action"],
        "target": row["target"],
        "timecreated": int(row["timecreated"]),
        "event_time": datetime.fromtimestamp(
            int(row["timecreated"]), tz=timezone.utc
        ).isoformat(),
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "cycle": cycle,   # nomor putaran (untuk tracking)
    }


def send_to_output(event: dict, output_file, http_enabled=False):
    """Kirim event ke output. Nanti ganti dengan Kafka producer."""
    output_file.write(json.dumps(event) + "\n")
    output_file.flush()

    if http_enabled:
        try:
            import requests
            requests.post(CONFIG["http_endpoint"], json=event, timeout=1)
        except Exception as e:
            print(f"[WARN] HTTP gagal: {e}")


def trim_buffer(path: str, max_lines: int):
    """Potong file buffer kalau terlalu besar (jaga hanya N baris terakhir)."""
    p = Path(path)
    if not p.exists():
        return
    
    with open(p, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    if len(lines) > max_lines:
        keep = lines[-max_lines:]
        with open(p, "w", encoding="utf-8") as f:
            f.writelines(keep)
        print(f"[BUFFER] Trimmed dari {len(lines):,} → {max_lines:,} baris")


def load_dataframe() -> pd.DataFrame:
    """Load CSV sekali di awal."""
    csv_path = Path(CONFIG["csv_path"]).resolve()
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV tidak ditemukan: {csv_path}")
    
    print(f"[INFO] Membaca {csv_path.name}...")
    df = pd.read_csv(csv_path)
    
    if CONFIG["max_records_per_cycle"]:
        df = df.head(CONFIG["max_records_per_cycle"])
    
    # Urutkan berdasarkan waktu (penting untuk replay yang natural)
    df = df.sort_values("timecreated").reset_index(drop=True)
    return df


def run_continuous():
    """Loop tak terbatas, kirim event dengan rate terkendali."""
    df = load_dataframe()
    total = len(df)
    
    # Siapkan output file
    Path(CONFIG["output_jsonl"]).parent.mkdir(parents=True, exist_ok=True)
    mode = "w" if CONFIG["truncate_on_start"] else "a"
    
    # Hitung interval antar event
    interval = 1.0 / CONFIG["events_per_second"]
    
    # Info
    t_min = datetime.fromtimestamp(df["timecreated"].min(), tz=timezone.utc)
    t_max = datetime.fromtimestamp(df["timecreated"].max(), tz=timezone.utc)
    
    print(f"\n{'='*60}")
    print(f"  CONTINUOUS MODE")
    print(f"{'='*60}")
    print(f"  Total record/cycle : {total:,}")
    print(f"  Rentang waktu      : {t_min} → {t_max}")
    print(f"  Rate               : {CONFIG['events_per_second']} event/detik")
    print(f"  Interval           : {interval*1000:.0f} ms per event")
    print(f"  Output mode        : {'OVERWRITE' if mode == 'w' else 'APPEND'}")
    print(f"  Buffer max         : {CONFIG['max_buffer_lines']:,} baris")
    print(f"  Continuous         : {CONFIG['continuous']}")
    print(f"{'='*60}\n")
    print(f"[INFO] Mulai streaming... (Ctrl+C untuk stop)\n")
    
    cycle = 0
    total_sent = 0
    start_real = time.time()
    
    try:
        with open(CONFIG["output_jsonl"], mode, encoding="utf-8") as out:
            while True:
                cycle += 1
                print(f"\n[CYCLE {cycle}] Mulai putaran baru...")
                
                for i, row in df.iterrows():
                    event = parse_event(row, cycle)
                    send_to_output(event, out, CONFIG["enable_http"])
                    total_sent += 1
                    
                    # Progress log
                    if total_sent % CONFIG["log_every"] == 0:
                        elapsed = time.time() - start_real
                        rate = total_sent / elapsed if elapsed > 0 else 0
                        print(f"[{total_sent:>7,}] cycle={cycle} "
                              f"| {rate:.2f} ev/s "
                              f"| {event['eventname']}")
                    
                    # Rate limiting
                    time.sleep(interval)
                
                # Cycle selesai
                if not CONFIG["continuous"]:
                    break
                
                # Trim buffer sebelum cycle berikutnya
                trim_buffer(CONFIG["output_jsonl"], CONFIG["max_buffer_lines"])
                
                print(f"[CYCLE {cycle}] Selesai. "
                      f"Total sent: {total_sent:,}. Lanjut cycle berikutnya...\n")
    
    except KeyboardInterrupt:
        elapsed = time.time() - start_real
        print(f"\n\n[STOP] Dihentikan oleh user")
        print(f"[STOP] Total event terkirim : {total_sent:,}")
        print(f"[STOP] Total cycle          : {cycle}")
        print(f"[STOP] Durasi               : {elapsed/60:.1f} menit")
        print(f"[STOP] Rate rata-rata       : {total_sent/elapsed:.2f} ev/s")


if __name__ == "__main__":
    run_continuous()