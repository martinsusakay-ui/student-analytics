"""
kafka_producer_oulad.py - Polling OULAD dari Railway, kirim ke Kafka
"""

import requests
import json
import time
from pathlib import Path
from kafka import KafkaProducer
from kafka.errors import KafkaTimeoutError

API_BASE = "https://web-production-97daa8.up.railway.app"
KAFKA_BOOTSTRAP = "localhost:9092"
STATE_FILE = "pipeline_state_oulad.json"

SOURCES = [
    {"name": "oulad_vle", "endpoint": "/api/oulad/vle/kafka-format/since/{last_id}", "topic": "oulad-vle"},
    {"name": "oulad_assessment", "endpoint": "/api/oulad/assessment/kafka-format/since/{last_id}", "topic": "oulad-assessment"},
    {"name": "oulad_students", "endpoint": "/api/oulad/students/kafka-format/since/{last_id}", "topic": "oulad-students"},
    {"name": "oulad_courses", "endpoint": "/api/oulad/courses/kafka-format/since/{last_id}", "topic": "oulad-courses"},
    {"name": "oulad_registration", "endpoint": "/api/oulad/registration/kafka-format/since/{last_id}", "topic": "oulad-registration"},
]

POLL_INTERVAL = 5
POLL_LIMIT = 100


def load_state():
    if Path(STATE_FILE).exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {s["name"]: 0 for s in SOURCES}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def create_producer():
    return KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        acks="all", retries=3,
    )


def main():
    print("=" * 70)
    print("  OULAD KAFKA PRODUCER")
    print("=" * 70)
    for s in SOURCES:
        print(f"  {s['name']:20} → {s['topic']}")
    print("=" * 70 + "\n")
    
    producer = create_producer()
    state = load_state()
    
    while True:
        for source in SOURCES:
            name = source["name"]
            last_id = state.get(name, 0)
            url = f"{API_BASE}{source['endpoint'].format(last_id=last_id)}"
            
            try:
                r = requests.get(url, params={"limit": POLL_LIMIT}, timeout=30)
                if r.status_code == 200:
                    data = r.json()
                    events = data.get("events", [])
                    count = data.get("count", 0)
                    next_id = data.get("next_last_id", last_id)
                    
                    if count > 0:
                        for event in events:
                            producer.send(source["topic"], value=event)
                        producer.flush()
                        state[name] = next_id
                        print(f"[{name:20}] +{count:>3} events | last_id={next_id:>6}")
            except Exception as e:
                print(f"[ERROR] {name}: {e}")
        
        save_state(state)
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()