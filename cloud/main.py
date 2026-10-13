# ============================================================
# KAFKA POLLING ENDPOINTS (UnB + OULAD)
# ============================================================

@app.get("/api/activities/kafka-format/since/{last_id}")
def get_events_kafka(last_id: int, limit: int = Query(100, ge=1, le=1000),
                     db: Session = Depends(get_db)):
    events = (db.query(Event)
              .filter(Event.id > last_id)
              .order_by(Event.id.asc())
              .limit(limit).all())
    next_last_id = events[-1].id if events else last_id
    return {
        "source": "events",
        "last_id": last_id,
        "count": len(events),
        "next_last_id": next_last_id,
        "events": [e.to_dict() for e in events],
    }

@app.get("/api/oulad/vle/kafka-format/since/{last_id}")
def get_oulad_vle_kafka(last_id: int, limit: int = Query(100, ge=1, le=1000),
                        db: Session = Depends(get_db)):
    events = (db.query(OuladVle)
              .filter(OuladVle.id > last_id)
              .order_by(OuladVle.id.asc())
              .limit(limit).all())
    next_last_id = events[-1].id if events else last_id
    return {
        "source": "oulad_vle",
        "last_id": last_id,
        "count": len(events),
        "next_last_id": next_last_id,
        "events": [e.to_dict() for e in events],
    }

@app.get("/api/oulad/assessment/kafka-format/since/{last_id}")
def get_oulad_assessment_kafka(last_id: int, limit: int = Query(100, ge=1, le=1000),
                               db: Session = Depends(get_db)):
    events = (db.query(OuladAssessment)
              .filter(OuladAssessment.id > last_id)
              .order_by(OuladAssessment.id.asc())
              .limit(limit).all())
    next_last_id = events[-1].id if events else last_id
    return {
        "source": "oulad_assessment",
        "last_id": last_id,
        "count": len(events),
        "next_last_id": next_last_id,
        "events": [e.to_dict() for e in events],
    }

@app.get("/api/oulad/students/kafka-format/since/{last_id}")
def get_oulad_students_kafka(last_id: int, limit: int = Query(100, ge=1, le=1000),
                              db: Session = Depends(get_db)):
    events = (db.query(OuladStudent)
              .filter(OuladStudent.id > last_id)
              .order_by(OuladStudent.id.asc())
              .limit(limit).all())
    next_last_id = events[-1].id if events else last_id
    return {
        "source": "oulad_students",
        "last_id": last_id,
        "count": len(events),
        "next_last_id": next_last_id,
        "events": [e.to_dict() for e in events],
    }

@app.get("/api/oulad/courses/kafka-format/since/{last_id}")
def get_oulad_courses_kafka(last_id: int, limit: int = Query(100, ge=1, le=1000),
                             db: Session = Depends(get_db)):
    events = (db.query(OuladCourse)
              .filter(OuladCourse.id > last_id)
              .order_by(OuladCourse.id.asc())
              .limit(limit).all())
    next_last_id = events[-1].id if events else last_id
    return {
        "source": "oulad_courses",
        "last_id": last_id,
        "count": len(events),
        "next_last_id": next_last_id,
        "events": [e.to_dict() for e in events],
    }

@app.get("/api/oulad/registration/kafka-format/since/{last_id}")
def get_oulad_registration_kafka(last_id: int, limit: int = Query(100, ge=1, le=1000),
                                  db: Session = Depends(get_db)):
    events = (db.query(OuladRegistration)
              .filter(OuladRegistration.id > last_id)
              .order_by(OuladRegistration.id.asc())
              .limit(limit).all())
    next_last_id = events[-1].id if events else last_id
    return {
        "source": "oulad_registration",
        "last_id": last_id,
        "count": len(events),
        "next_last_id": next_last_id,
        "events": [e.to_dict() for e in events],
    }