# config.py
CSV_PATH = "data/logs_interacoes_anon.csv"
OUTPUT_JSONL = "output/stream_buffer.jsonl"
SPEED_FACTOR = 1000
BATCH_SIZE = 100
MAX_RECORDS = None
ENABLE_HTTP = False
HTTP_ENDPOINT = "http://localhost:5000/api/ingest"