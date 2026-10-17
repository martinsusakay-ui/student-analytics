"""
backend.py - REST API untuk Moodle Activity Monitor + Analytics
Versi 5.0 — Prediksi dengan fitur akademik (bebas leakage)
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timezone
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest, RandomForestRegressor, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (
    mean_absolute_error, r2_score,
    accuracy_score, precision_score, recall_score, f1_score
)
import warnings
warnings.filterwarnings("ignore")

app = Flask(__name__)
CORS(app)

BUFFER_FILE = "output/stream_buffer.jsonl"
GRADES_FILE = "notas_atividades_anon.csv"
MAX_READ_LINES = 100_000


# ============================================================
# HELPER
# ============================================================
def load_dataframe() -> pd.DataFrame:
    p = Path(BUFFER_FILE)
    if not p.exists():
        return pd.DataFrame()
    with open(p, "r", encoding="utf-8") as f:
        lines = f.readlines()[-MAX_READ_LINES:]
    records = []
    for line in lines:
        line = line.strip()
        if line:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    df["event_time"] = pd.to_datetime(df["event_time"])
    return df


def build_user_features(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    grouped = df.groupby("user_hash")
    features = pd.DataFrame({
        "total_events": grouped.size(),
        "unique_events": grouped["eventname"].nunique(),
        "unique_courses": grouped["courseid"].nunique(),
        "unique_actions": grouped["action"].nunique(),
        "active_minutes": grouped["event_time"].apply(
            lambda x: (x.max() - x.min()).total_seconds() / 60
        ),
    })
    features["login_count"] = grouped.apply(
        lambda x: (x["eventname"].str.contains("loggedin")).sum()
    )
    features["message_count"] = grouped.apply(
        lambda x: (x["eventname"].str.contains("message_sent")).sum()
    )
    features["graded_count"] = grouped.apply(
        lambda x: (x["eventname"].str.contains("user_graded")).sum()
    )
    features["quiz_count"] = grouped.apply(
        lambda x: (x["eventname"].str.contains("quiz")).sum()
    )
    features["forum_count"] = grouped.apply(
        lambda x: (x["eventname"].str.contains("forum")).sum()
    )
    features["assign_count"] = grouped.apply(
        lambda x: (x["eventname"].str.contains("assign")).sum()
    )
    features["events_per_minute"] = features["total_events"] / features["active_minutes"].clip(lower=1)
    features["login_ratio"] = features["login_count"] / features["total_events"].clip(lower=1)
    features["message_ratio"] = features["message_count"] / features["total_events"].clip(lower=1)
    return features.fillna(0).reset_index()


# ============================================================
# ENDPOINTS DASAR
# ============================================================
@app.route("/", methods=["GET"])
def root():
    return jsonify({
        "service": "Moodle Activity Monitor API + Analytics",
        "version": "5.0",
        "endpoints": [
            "/api/health", "/api/kpi", "/api/events/top",
            "/api/events/timeline", "/api/courses/top", "/api/events/recent",
            "/api/analytics/clustering", "/api/analytics/prediction",
            "/api/analytics/anomaly",
        ]
    })


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })


@app.route("/api/kpi", methods=["GET"])
def kpi():
    df = load_dataframe()
    if df.empty:
        return jsonify({"total_events": 0, "active_users": 0, "courses": 0, "duration_hours": 0})
    duration = (df["event_time"].max() - df["event_time"].min()).total_seconds() / 3600
    return jsonify({
        "total_events": len(df),
        "active_users": int(df["user_hash"].nunique()),
        "courses": int(df["courseid"].nunique()),
        "duration_hours": round(duration, 2)
    })


@app.route("/api/events/top", methods=["GET"])
def top_events():
    df = load_dataframe()
    if df.empty:
        return jsonify([])
    counts = df["eventname"].value_counts().head(10)
    return jsonify([{"eventname": k, "count": int(v)} for k, v in counts.items()])


@app.route("/api/events/timeline", methods=["GET"])
def timeline():
    df = load_dataframe()
    if df.empty:
        return jsonify([])
    ts = df.set_index("event_time").resample("1min").size()
    return jsonify([{"time": str(idx), "count": int(val)} for idx, val in ts.items()])


@app.route("/api/courses/top", methods=["GET"])
def top_courses():
    df = load_dataframe()
    if df.empty:
        return jsonify([])
    counts = df["courseid"].value_counts().head(10)
    return jsonify([{"courseid": int(k), "count": int(v)} for k, v in counts.items()])


@app.route("/api/events/recent", methods=["GET"])
def recent_events():
    df = load_dataframe()
    if df.empty:
        return jsonify([])
    recent = df.sort_values("event_time", ascending=False).head(20)
    return jsonify(
        recent[["event_time", "user_hash", "courseid", "eventname", "action"]]
        .assign(event_time=lambda x: x["event_time"].astype(str))
        .to_dict(orient="records")
    )


# ============================================================
# ANALYTICS — CLUSTERING
# ============================================================
@app.route("/api/analytics/clustering", methods=["GET"])
def clustering():
    n_clusters = int(request.args.get("n_clusters", 3))
    n_clusters = max(2, min(n_clusters, 6))

    df = load_dataframe()
    if df.empty or len(df) < 50:
        return jsonify({"error": "Data belum cukup", "current": len(df)}), 400

    features = build_user_features(df)
    if len(features) < n_clusters:
        return jsonify({"error": "User terlalu sedikit"}), 400

    feature_cols = [
        "total_events", "unique_events", "unique_courses",
        "unique_actions", "active_minutes",
        "login_count", "message_count", "graded_count",
        "quiz_count", "forum_count", "assign_count",
    ]
    feature_cols = [c for c in feature_cols if c in features.columns]
    X = features[feature_cols].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_scaled)
    features["cluster"] = labels

    cluster_profiles = []
    for cid in range(n_clusters):
        cd = features[features["cluster"] == cid]
        profile = {
            "cluster_id": cid,
            "size": len(cd),
            "percentage": round(len(cd) / len(features) * 100, 2),
            "centroid": {
                "avg_total_events": round(cd["total_events"].mean(), 1),
                "avg_unique_courses": round(cd["unique_courses"].mean(), 1),
                "avg_login_count": round(cd["login_count"].mean(), 1),
                "avg_message_count": round(cd["message_count"].mean(), 1),
                "avg_graded_count": round(cd["graded_count"].mean(), 1),
            }
        }
        avg_events = profile["centroid"]["avg_total_events"]
        if avg_events > features["total_events"].quantile(0.75):
            profile["label"] = "Highly Active"
        elif avg_events > features["total_events"].quantile(0.25):
            profile["label"] = "Moderately Active"
        else:
            profile["label"] = "Low Activity"
        cluster_profiles.append(profile)

    return jsonify({
        "n_clusters": n_clusters,
        "n_users": len(features),
        "features_used": feature_cols,
        "inertia": round(float(kmeans.inertia_), 2),
        "clusters": cluster_profiles,
    })


# ============================================================
# ANALYTICS — PREDICTION (v5: fitur akademik bebas leakage)
# ============================================================
@app.route("/api/analytics/prediction", methods=["GET"])
def prediction():
    """
    Prediksi performa mahasiswa dengan fitur gabungan:
    - Perilaku dari stream_buffer.jsonl
    - Akademik dari notas_atividades_anon.csv (bebas leakage)
    
    Target: avg_grade
    Fitur: perilaku + aktivitas akademik (TANPA finalgrade)
    """
    # ========================================================
    # 1. LOAD FITUR PERILAKU
    # ========================================================
    df = load_dataframe()
    if df.empty or len(df) < 100:
        return jsonify({"error": "Data log belum cukup", "current": len(df)}), 400

    behavioral = build_user_features(df)

    behavioral_cols = [
        "total_events", "unique_events", "unique_courses",
        "unique_actions", "active_minutes",
        "login_count", "message_count", "forum_count",
    ]
    behavioral_cols = [c for c in behavioral_cols if c in behavioral.columns]

    # ========================================================
    # 2. LOAD TARGET + FITUR AKADEMIK
    # ========================================================
    grades_path = Path(GRADES_FILE)
    if not grades_path.exists():
        return jsonify({"error": f"File {GRADES_FILE} tidak ditemukan"}), 400

    try:
        df_grades = pd.read_csv(grades_path)

        if "timemodified" in df_grades.columns:
            df_grades["datetime"] = pd.to_datetime(
                df_grades["timemodified"], unit="s", errors="coerce"
            )

        item_lower = df_grades["itemname"].str.lower()
        df_grades["is_quiz"] = item_lower.str.contains("question", na=False)
        df_grades["is_forum"] = item_lower.str.contains("fórum|forum", na=False)
        df_grades["is_assignment"] = item_lower.str.contains("tarefa", na=False)

        # Target
        df_graded = df_grades.dropna(subset=["finalgrade"])
        user_target = df_graded.groupby("user_hash").agg(
            avg_grade=("finalgrade", "mean"),
            n_graded=("finalgrade", "count"),
        ).reset_index()

        # Fitur akademik
        user_academic = df_grades.groupby("user_hash").agg(
            n_activities=("itemname", "count"),
            n_unique_items=("itemname", "nunique"),
            n_quiz=("is_quiz", "sum"),
            n_forum=("is_forum", "sum"),
            n_assignment=("is_assignment", "sum"),
            first_activity=("datetime", "min"),
            last_activity=("datetime", "max"),
        ).reset_index()

        user_academic["activity_span_days"] = (
            (user_academic["last_activity"] - user_academic["first_activity"])
            .dt.total_seconds() / 86400
        ).clip(lower=0.01)

        user_academic["submission_frequency"] = (
            user_academic["n_activities"] / user_academic["activity_span_days"]
        )

        user_academic["quiz_ratio"] = (
            user_academic["n_quiz"] / user_academic["n_activities"].clip(lower=1)
        )
        user_academic["forum_ratio"] = (
            user_academic["n_forum"] / user_academic["n_activities"].clip(lower=1)
        )
        user_academic["assignment_ratio"] = (
            user_academic["n_assignment"] / user_academic["n_activities"].clip(lower=1)
        )

        user_academic = user_academic.merge(
            user_target[["user_hash", "n_graded"]],
            on="user_hash", how="left"
        )
        user_academic["n_graded"] = user_academic["n_graded"].fillna(0)
        user_academic["completion_rate"] = (
            user_academic["n_graded"] / user_academic["n_activities"].clip(lower=1)
        )

        user_grades = user_target.merge(
            user_academic.drop(columns=["n_graded"]),
            on="user_hash", how="left"
        )
        user_grades = user_grades.drop(
            columns=["first_activity", "last_activity"], errors="ignore"
        )

    except Exception as e:
        return jsonify({"error": f"Gagal proses nilai: {str(e)}"}), 500

    # ========================================================
    # 3. MERGE PERILAKU + AKADEMIK
    # ========================================================
    data = behavioral.merge(user_grades, on="user_hash", how="inner")
    if len(data) < 30:
        return jsonify({
            "error": "User dengan nilai terlalu sedikit",
            "n_users_with_grades": len(user_grades),
            "n_users_matched": len(data),
        }), 400

    academic_cols = [
        "n_activities", "n_unique_items", "n_quiz", "n_forum", "n_assignment",
        "activity_span_days", "submission_frequency",
        "quiz_ratio", "forum_ratio", "assignment_ratio",
        "completion_rate",
    ]
    academic_cols = [c for c in academic_cols if c in data.columns]

    all_features = behavioral_cols + academic_cols
    X = data[all_features].fillna(0).values
    y = data["avg_grade"].values

    # ========================================================
    # 4. THRESHOLD
    # ========================================================
    grade_min = float(y.min())
    grade_max = float(y.max())
    grade_mean = float(y.mean())
    grade_median = float(np.median(y))
    grade_q75 = float(np.percentile(y, 75))
    grade_q90 = float(np.percentile(y, 90))

    PASS_THRESHOLD = round(grade_median, 2)
    threshold_method = "median (class balance)"

    y_binary = (y >= PASS_THRESHOLD).astype(int)

    # ========================================================
    # 5. CLASSIFICATION
    # ========================================================
    classification_metrics = {}
    if len(np.unique(y_binary)) >= 2:
        X_train, X_test, y_train_bin, y_test_bin = train_test_split(
            X, y_binary, test_size=0.25, random_state=42, stratify=y_binary
        )

        clf = RandomForestClassifier(
            n_estimators=200, max_depth=8,
            min_samples_split=5, min_samples_leaf=3,
            random_state=42, n_jobs=-1,
            class_weight="balanced"
        )
        clf.fit(X_train, y_train_bin)
        y_pred_bin = clf.predict(X_test)

        cv_scores = cross_val_score(clf, X, y_binary, cv=5, scoring="accuracy")

        clf_importance = sorted(
            [{"feature": f, "importance": round(float(i), 4)}
             for f, i in zip(all_features, clf.feature_importances_)],
            key=lambda x: -x["importance"]
        )

        classification_metrics = {
            "accuracy": round(float(accuracy_score(y_test_bin, y_pred_bin)), 4),
            "precision": round(float(precision_score(y_test_bin, y_pred_bin, zero_division=0)), 4),
            "recall": round(float(recall_score(y_test_bin, y_pred_bin, zero_division=0)), 4),
            "f1_score": round(float(f1_score(y_test_bin, y_pred_bin, zero_division=0)), 4),
            "cv_accuracy_mean": round(float(cv_scores.mean()), 4),
            "cv_accuracy_std": round(float(cv_scores.std()), 4),
            "n_positive": int(y_binary.sum()),
            "n_negative": int(len(y_binary) - y_binary.sum()),
            "threshold": PASS_THRESHOLD,
            "threshold_method": threshold_method,
            "feature_importance": clf_importance,
        }
    else:
        classification_metrics = {"error": "Hanya 1 kelas"}

    # ========================================================
    # 6. REGRESSION
    # ========================================================
    X_train_r, X_test_r, y_train_r, y_test_r = train_test_split(
        X, y, test_size=0.25, random_state=42
    )

    reg = RandomForestRegressor(
        n_estimators=200, max_depth=8,
        min_samples_split=5, min_samples_leaf=3,
        random_state=42, n_jobs=-1
    )
    reg.fit(X_train_r, y_train_r)
    y_pred_r = reg.predict(X_test_r)

    mae = float(mean_absolute_error(y_test_r, y_pred_r))
    r2 = float(r2_score(y_test_r, y_pred_r))
    rmse = float(np.sqrt(((y_test_r - y_pred_r) ** 2).mean()))
    cv_r2 = cross_val_score(reg, X, y, cv=5, scoring="r2")

    regression_metrics = {
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "r2_score": round(r2, 4),
        "cv_r2_mean": round(float(cv_r2.mean()), 4),
        "cv_r2_std": round(float(cv_r2.std()), 4),
        "n_samples": len(data),
        "n_train": len(X_train_r),
        "n_test": len(X_test_r),
        "grade_stats": {
            "min": round(grade_min, 2),
            "max": round(grade_max, 2),
            "mean": round(grade_mean, 2),
            "median": round(grade_median, 2),
            "q75": round(grade_q75, 2),
            "q90": round(grade_q90, 2),
        }
    }

    importances = reg.feature_importances_
    feature_importance = sorted(
        [{"feature": f, "importance": round(float(i), 4)}
         for f, i in zip(all_features, importances)],
        key=lambda x: -x["importance"]
    )

    sample = data.head(10)[["user_hash"]].copy()
    sample["predicted_grade"] = reg.predict(data.head(10)[all_features].fillna(0).values).round(2)
    sample["actual_grade"] = data.head(10)["avg_grade"].round(2).values
    sample["user_hash"] = sample["user_hash"].str[:12] + "..."
    sample_predictions = sample[["user_hash", "predicted_grade", "actual_grade"]].to_dict(orient="records")

    return jsonify({
        "data_source": {
            "features_behavioral": "stream_buffer.jsonl",
            "features_academic": f"{GRADES_FILE} (tanpa finalgrade)",
            "target": f"{GRADES_FILE} (avg_grade)",
            "n_users_matched": len(data),
            "n_behavioral_features": len(behavioral_cols),
            "n_academic_features": len(academic_cols),
            "note": "Fitur akademik bebas leakage — tidak termasuk finalgrade",
        },
        "classification": {
            "model": "RandomForestClassifier",
            "target": f"lulus (>= {PASS_THRESHOLD})",
            "metrics": classification_metrics,
        },
        "regression": {
            "model": "RandomForestRegressor",
            "target": "avg_grade",
            "metrics": regression_metrics,
            "feature_importance": feature_importance,
            "sample_predictions": sample_predictions,
        },
    })


# ============================================================
# ANALYTICS — ANOMALY
# ============================================================
@app.route("/api/analytics/anomaly", methods=["GET"])
def anomaly():
    df = load_dataframe()
    if df.empty or len(df) < 100:
        return jsonify({"error": "Data belum cukup", "current": len(df)}), 400

    features = build_user_features(df)
    if len(features) < 20:
        return jsonify({"error": "User terlalu sedikit"}), 400

    feature_cols = [
        "total_events", "unique_events", "unique_courses",
        "unique_actions", "active_minutes",
        "login_count", "message_count",
        "events_per_minute", "login_ratio", "message_ratio",
    ]
    feature_cols = [c for c in feature_cols if c in features.columns]
    X = features[feature_cols].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    contamination = 0.05
    iso = IsolationForest(contamination=contamination, random_state=42, n_jobs=-1)
    labels = iso.fit_predict(X_scaled)
    scores = iso.decision_function(X_scaled)

    features["is_anomaly"] = labels == -1
    features["anomaly_score"] = -scores

    anomalies = features[features["is_anomaly"]].sort_values("anomaly_score", ascending=False)

    anomaly_list = []
    for _, row in anomalies.head(20).iterrows():
        reason = []
        if row["total_events"] > features["total_events"].quantile(0.95):
            reason.append("Sangat aktif")
        if row["total_events"] < features["total_events"].quantile(0.05):
            reason.append("Sangat pasif")
        if row["events_per_minute"] > features["events_per_minute"].quantile(0.95):
            reason.append("Aktivitas burst")
        if row["message_ratio"] > 0.8:
            reason.append("Dominan chat")
        if not reason:
            reason.append("Pola tidak biasa")

        anomaly_list.append({
            "user_hash": row["user_hash"][:16] + "...",
            "total_events": int(row["total_events"]),
            "unique_courses": int(row["unique_courses"]),
            "anomaly_score": round(float(row["anomaly_score"]), 4),
            "reasons": reason,
        })

    return jsonify({
        "model": "IsolationForest",
        "contamination": contamination,
        "n_users": len(features),
        "n_anomalies": int(features["is_anomaly"].sum()),
        "anomaly_percentage": round(features["is_anomaly"].mean() * 100, 2),
        "anomalies": anomaly_list,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)