"""
mock_api.py - Mock FastAPI untuk testing bot
Simulasi endpoint FastAPI yang akan di-deploy di Railway.
"""

from flask import Flask, request, jsonify
from datetime import datetime, timezone
from collections import Counter

app = Flask(__name__)

# ============================================================
# IN-MEMORY STORAGE (untuk testing)
# ============================================================
received_events = []
event_counter = Counter()
user_counter = Counter()
course_counter = Counter()


# ============================================================
# ENDPOINTS
# ============================================================
@app.route("/", methods=["GET"])
def root():
    return jsonify({
        "service": "Mock FastAPI (untuk testing bot)",
        "version": "1.0.0",
        "endpoints": [
            "GET  /api/health",
            "POST /api/activities",
            "POST /api/activities/batch",
            "GET  /api/activities/kafka-format/since/{last_id}",
            "GET  /api/stats",
            "GET  /api/events",
        ]
    })


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_received": len(received_events),
    })


@app.route("/api/activities", methods=["POST"])
def post_activity():
    """Terima 1 event."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data"}), 400
        
        # Validasi minimal
        required = ["user_hash", "eventname", "timecreated"]
        for field in required:
            if field not in data:
                return jsonify({"error": f"Missing field: {field}"}), 400
        
        # Simpan
        event = {
            "id": len(received_events) + 1,
            **data,
            "received_at": datetime.now(timezone.utc).isoformat(),
        }
        received_events.append(event)
        
        # Update counters
        event_counter[data.get("eventname", "unknown")] += 1
        user_counter[data.get("user_hash", "unknown")] += 1
        course_counter[data.get("courseid", 0)] += 1
        
        # Log tiap 100 event
        if len(received_events) % 100 == 0:
            print(f"[MOCK] Received {len(received_events):,} events "
                  f"| Last: {data.get('eventname', '')[:50]}")
        
        return jsonify({
            "status": "ok",
            "id": event["id"],
            "total": len(received_events),
        }), 201
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/activities/batch", methods=["POST"])
def post_activity_batch():
    """Terima batch event."""
    try:
        data = request.get_json()
        events = data.get("events", [])
        
        if not events:
            return jsonify({"error": "Empty batch"}), 400
        
        inserted = 0
        for event_data in events:
            event = {
                "id": len(received_events) + 1,
                **event_data,
                "received_at": datetime.now(timezone.utc).isoformat(),
            }
            received_events.append(event)
            event_counter[event_data.get("eventname", "unknown")] += 1
            inserted += 1
        
        print(f"[MOCK] Batch received: {inserted} events "
              f"| Total: {len(received_events):,}")
        
        return jsonify({
            "status": "ok",
            "inserted": inserted,
            "total": len(received_events),
        }), 201
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/activities/kafka-format/since/<int:last_id>", methods=["GET"])
def get_kafka_format(last_id: int):
    """Ambil event dengan ID > last_id (untuk polling producer)."""
    limit = request.args.get("limit", 100, type=int)
    
    events = [e for e in received_events if e["id"] > last_id][:limit]
    
    return jsonify({
        "last_id": last_id,
        "count": len(events),
        "events": events,
        "next_last_id": events[-1]["id"] if events else last_id,
    })


@app.route("/api/stats", methods=["GET"])
def stats():
    """Statistik keseluruhan."""
    return jsonify({
        "total_events": len(received_events),
        "unique_users": len(user_counter),
        "unique_courses": len(course_counter),
        "top_events": event_counter.most_common(10),
        "top_users": user_counter.most_common(10),
        "top_courses": course_counter.most_common(10),
    })


@app.route("/api/events", methods=["GET"])
def list_events():
    """List event (paginasi)."""
    limit = request.args.get("limit", 100, type=int)
    offset = request.args.get("offset", 0, type=int)
    
    events = received_events[offset:offset+limit]
    
    return jsonify({
        "total": len(received_events),
        "offset": offset,
        "limit": limit,
        "count": len(events),
        "events": events,
    })


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print(f"\n{'='*70}")
    print(f"  MOCK FASTAPI (untuk testing bot)")
    print(f"{'='*70}")
    print(f"  URL: http://localhost:8000")
    print(f"  Endpoints:")
    print(f"    GET  /api/health")
    print(f"    POST /api/activities")
    print(f"    POST /api/activities/batch")
    print(f"    GET  /api/activities/kafka-format/since/{{last_id}}")
    print(f"    GET  /api/stats")
    print(f"    GET  /api/events")
    print(f"{'='*70}\n")
    
    app.run(host="0.0.0.0", port=8000, debug=False, threaded=True)