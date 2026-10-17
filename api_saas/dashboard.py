"""
dashboard.py - Real-time monitoring dashboard + ML Analytics
Konsumsi backend Flask API (port 5000)
Auto-refresh: 10 detik
"""

import streamlit as st
import requests
import time
import pandas as pd
from datetime import datetime

# ============================================================
# KONFIGURASI
# ============================================================
API_BASE = "http://127.0.0.1:5000"
REFRESH_SECONDS = 10
REQUEST_TIMEOUT = 20

st.set_page_config(
    page_title="Moodle Activity Monitor",
    page_icon="📊",
    layout="wide"
)

# ============================================================
# API HELPER
# ============================================================
@st.cache_data(ttl=REFRESH_SECONDS)
def api_get(endpoint: str):
    try:
        r = requests.get(f"{API_BASE}{endpoint}", timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        return {"_error": "Backend tidak dapat dihubungi"}
    except requests.exceptions.Timeout:
        return {"_error": "Request timeout"}
    except Exception as e:
        return {"_error": str(e)}


# ============================================================
# HEADER
# ============================================================
st.title("📊 Moodle Activity Real-Time Monitor")
st.caption(
    f"API: `{API_BASE}` | "
    f"Refresh: every **{REFRESH_SECONDS}s** | "
    f"Last update: {datetime.now().strftime('%H:%M:%S')}"
)

# ============================================================
# CEK BACKEND
# ============================================================
health = api_get("/api/health")
if health is None or "_error" in health:
    error_msg = health.get("_error", "Unknown error") if health else "No response"
    st.error(f"❌ Backend tidak dapat dihubungi: {error_msg}")
    st.info("Pastikan `python backend.py` sedang berjalan.")
    time.sleep(REFRESH_SECONDS)
    st.rerun()

st.success(f"✅ Backend API online — {health.get('timestamp', '')}")

# ============================================================
# KPI CARDS
# ============================================================
kpi = api_get("/api/kpi")
if kpi and "_error" not in kpi:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📥 Total Events", f"{kpi['total_events']:,}")
    with col2:
        st.metric("👥 Active Users", f"{kpi['active_users']:,}")
    with col3:
        st.metric("📚 Courses", f"{kpi['courses']:,}")
    with col4:
        st.metric("⏱️ Duration", f"{kpi['duration_hours']:.1f} hours")

st.divider()

# ============================================================
# CHARTS
# ============================================================
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("🔥 Top 10 Events")
    top_events = api_get("/api/events/top")
    if top_events and "_error" not in top_events and len(top_events) > 0:
        df_events = pd.DataFrame(top_events)
        df_events["eventname"] = df_events["eventname"].apply(
            lambda x: x.split("\\")[-1] if "\\" in x else x
        )
        df_events = df_events.set_index("eventname")["count"]
        st.bar_chart(df_events)

with col_right:
    st.subheader("📈 Event Timeline (per minute)")
    timeline = api_get("/api/events/timeline")
    if timeline and "_error" not in timeline and len(timeline) > 0:
        df_tl = pd.DataFrame(timeline)
        df_tl["time"] = pd.to_datetime(df_tl["time"])
        df_tl = df_tl.set_index("time")["count"]
        st.line_chart(df_tl)

st.divider()

# ============================================================
# TOP COURSES & QUICK STATS
# ============================================================
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("🏫 Top 10 Courses")
    top_courses = api_get("/api/courses/top")
    if top_courses and "_error" not in top_courses and len(top_courses) > 0:
        df_courses = pd.DataFrame(top_courses)
        df_courses["courseid"] = df_courses["courseid"].astype(str)
        df_courses = df_courses.set_index("courseid")["count"]
        st.bar_chart(df_courses)

with col_b:
    st.subheader("📊 Quick Stats")
    if kpi and "_error" not in kpi:
        st.metric("Avg events/user", f"{kpi['total_events']/max(kpi['active_users'],1):.1f}")
        st.metric("Avg events/course", f"{kpi['total_events']/max(kpi['courses'],1):.0f}")
        st.metric("Events/hour", f"{kpi['total_events']/max(kpi['duration_hours'],1):.0f}")

st.divider()

# ============================================================
# RECENT EVENTS
# ============================================================
st.subheader("🕐 Recent Events (last 20)")
recent = api_get("/api/events/recent")
if recent and "_error" not in recent and len(recent) > 0:
    df_recent = pd.DataFrame(recent)
    st.dataframe(df_recent, use_container_width=True, hide_index=True)

# ============================================================
# MACHINE LEARNING ANALYTICS
# ============================================================
st.divider()
st.header("🧠 Machine Learning Analytics")
st.caption("K-Means Clustering • Random Forest • Isolation Forest")

tab1, tab2, tab3 = st.tabs(["👥 Clustering", "🎯 Prediction", "🚨 Anomaly Detection"])

# ------------------------------------------------------------
# TAB 1: CLUSTERING
# ------------------------------------------------------------
with tab1:
    st.subheader("Behavioral Profiling (K-Means)")

    n_clusters = st.slider("Jumlah cluster", 2, 6, 3, key="n_clusters_slider")
    clustering = api_get(f"/api/analytics/clustering?n_clusters={n_clusters}")

    if clustering and "_error" not in clustering and "clusters" in clustering:
        col_c1, col_c2 = st.columns([1, 2])

        with col_c1:
            st.write("**Distribusi Cluster**")
            df_clusters = pd.DataFrame(clustering["clusters"])
            df_pie = df_clusters.set_index("cluster_id")["size"]
            st.bar_chart(df_pie)
            st.metric("Total Users", f"{clustering['n_users']:,}")
            st.metric("Inertia", f"{clustering['inertia']:,.2f}")

        with col_c2:
            st.write("**Profil Cluster**")
            profiles = []
            for c in clustering["clusters"]:
                profiles.append({
                    "Cluster": f"#{c['cluster_id']}",
                    "Label": c["label"],
                    "Size": c["size"],
                    "%": f"{c['percentage']}%",
                    "Avg Events": c["centroid"]["avg_total_events"],
                    "Avg Login": c["centroid"]["avg_login_count"],
                    "Avg Msg": c["centroid"]["avg_message_count"],
                    "Avg Graded": c["centroid"]["avg_graded_count"],
                })
            st.dataframe(pd.DataFrame(profiles), use_container_width=True, hide_index=True)
    else:
        st.info("Data clustering belum tersedia")

# ------------------------------------------------------------
# TAB 2: PREDICTION
# ------------------------------------------------------------
with tab2:
    st.subheader("Performance Prediction (Random Forest)")
    st.caption("Fitur: perilaku + akademik | Target: nilai asli (avg_grade)")

    prediction = api_get("/api/analytics/prediction")

    if prediction and "_error" not in prediction and "classification" in prediction:
        # Data source info
        ds = prediction.get("data_source", {})
        st.info(
            f"📊 **Data Source**: "
            f"Fitur perilaku ({ds.get('n_behavioral_features', 0)}) dari `{ds.get('features_behavioral', 'N/A')}` • "
            f"Fitur akademik ({ds.get('n_academic_features', 0)}) dari `{ds.get('features_academic', 'N/A')}` • "
            f"**{ds.get('n_users_matched', 0)} user matched**"
        )

        # === Classification ===
        st.write("**1. Classification: Lulus vs Tidak Lulus**")
        clf_metrics = prediction["classification"]["metrics"]

        col_p1, col_p2, col_p3, col_p4 = st.columns(4)
        with col_p1:
            st.metric("Accuracy", f"{clf_metrics['accuracy']:.2%}")
        with col_p2:
            st.metric("Precision", f"{clf_metrics['precision']:.2%}")
        with col_p3:
            st.metric("Recall", f"{clf_metrics['recall']:.2%}")
        with col_p4:
            st.metric("F1 Score", f"{clf_metrics['f1_score']:.2%}")

        st.caption(
            f"CV Accuracy: {clf_metrics['cv_accuracy_mean']:.2%} "
            f"(±{clf_metrics['cv_accuracy_std']:.2%}) | "
            f"Positive: {clf_metrics['n_positive']} | "
            f"Negative: {clf_metrics['n_negative']} | "
            f"Threshold: {clf_metrics['threshold']}"
        )

        st.divider()

        # === Regression ===
        reg = prediction["regression"]
        if "metrics" in reg and "r2_score" in reg["metrics"]:
            st.write("**2. Regression: Prediksi Nilai (avg_grade)**")
            reg_metrics = reg["metrics"]

            col_r1, col_r2, col_r3, col_r4 = st.columns(4)
            with col_r1:
                st.metric("R² Score", f"{reg_metrics['r2_score']:.4f}")
            with col_r2:
                st.metric("MAE", f"{reg_metrics['mae']:.2f}")
            with col_r3:
                st.metric("RMSE", f"{reg_metrics['rmse']:.2f}")
            with col_r4:
                st.metric("Samples", f"{reg_metrics['n_samples']}")

            st.caption(
                f"CV R²: {reg_metrics['cv_r2_mean']:.4f} "
                f"(±{reg_metrics['cv_r2_std']:.4f}) | "
                f"Grade range: {reg_metrics['grade_stats']['min']}–"
                f"{reg_metrics['grade_stats']['max']} "
                f"(mean: {reg_metrics['grade_stats']['mean']}, "
                f"median: {reg_metrics['grade_stats']['median']})"
            )

            st.divider()

            # Feature importance
            st.write("**Feature Importance**")
            if reg["feature_importance"]:
                df_imp = pd.DataFrame(reg["feature_importance"])
                df_imp = df_imp.set_index("feature")["importance"].sort_values(ascending=True)
                st.bar_chart(df_imp)

            st.divider()

            # Sample predictions + scatter plot
            st.write("**Sample Predictions & Scatter Plot**")
            if reg.get("sample_predictions"):
                df_pred = pd.DataFrame(reg["sample_predictions"])
                df_pred = df_pred.rename(columns={
                    "user_hash": "User",
                    "predicted_grade": "Predicted",
                    "actual_grade": "Actual",
                })
                df_pred["Error"] = (df_pred["Actual"] - df_pred["Predicted"]).abs().round(2)

                col_t1, col_t2 = st.columns([1, 1])

                with col_t1:
                    st.dataframe(df_pred, use_container_width=True, hide_index=True)

                with col_t2:
                    # Scatter plot Actual vs Predicted
                    import altair as alt
                    chart = alt.Chart(df_pred).mark_circle(size=120, color="#4C78A8").encode(
                        x=alt.X("Actual:Q", title="Actual Grade", scale=alt.Scale(domain=[0, 50])),
                        y=alt.Y("Predicted:Q", title="Predicted Grade", scale=alt.Scale(domain=[0, 50])),
                        tooltip=["User", "Actual", "Predicted", "Error"]
                    ).properties(height=350, title="Actual vs Predicted")

                    # Diagonal line
                    line_df = pd.DataFrame({"x": [0, 50], "y": [0, 50]})
                    line = alt.Chart(line_df).mark_line(
                        strokeDash=[5, 5], color="red", size=2
                    ).encode(x="x:Q", y="y:Q")

                    st.altair_chart(chart + line, use_container_width=True)

                st.caption("🔴 Garis merah = prediksi sempurna. Semakin dekat titik ke garis, semakin akurat.")

        st.divider()

        # Model Interpretation
        with st.expander("📖 Interpretasi Hasil Model"):
            st.markdown(f"""
            **Setup Model:**
            - **Fitur perilaku** ({ds.get('n_behavioral_features', 0)}): dari log LMS (`stream_buffer.jsonl`)
            - **Fitur akademik** ({ds.get('n_academic_features', 0)}): dari dataset nilai (`notas_atividades_anon.csv`)
            - **Target**: `avg_grade` (nilai rata-rata mahasiswa)
            - **Samples**: {ds.get('n_users_matched', 0)} mahasiswa match
            - **Catatan**: Fitur akademik bebas leakage (tidak termasuk `finalgrade`)
            
            **Hasil:**
            - Classification Accuracy: **{clf_metrics['accuracy']:.1%}** (F1: {clf_metrics['f1_score']:.3f})
            - Regression R²: **{reg_metrics['r2_score']:.3f}**
            - Cross-Validation R²: **{reg_metrics['cv_r2_mean']:.3f}** (±{reg_metrics['cv_r2_std']:.3f})
            - MAE: **{reg_metrics['mae']:.2f} poin**
            
            **Temuan Kunci:**
            1. **Fitur akademik** (`activity_span_days`, `completion_rate`) adalah prediktor terkuat
            2. **Perilaku sosial** (chat, login) **tidak prediktif** untuk nilai akademik
            3. Model berhasil membedakan mahasiswa berperforma tinggi vs rendah
            4. **Tidak ada data leakage** — hasil valid dan dapat dipertanggungjawabkan
            
            **Metodologi:**
            - Fitur dan target dari **sumber berbeda** (log perilaku vs dataset nilai)
            - Cross-validation 5-fold untuk memastikan hasil robust
            - Threshold median untuk class balance 50/50
            """)

    else:
        error = prediction.get("error", "Data prediksi belum tersedia") if prediction else "No response"
        st.warning(f"⚠️ {error}")
        if prediction and "hint" in prediction:
            st.info(prediction["hint"])

# ------------------------------------------------------------
# TAB 3: ANOMALY DETECTION
# ------------------------------------------------------------
with tab3:
    st.subheader("Anomaly Detection (Isolation Forest)")

    anomaly = api_get("/api/analytics/anomaly")

    if anomaly and "_error" not in anomaly and "anomalies" in anomaly:
        col_a1, col_a2, col_a3 = st.columns(3)
        with col_a1:
            st.metric("Total Users", f"{anomaly['n_users']:,}")
        with col_a2:
            st.metric("Anomali Terdeteksi", f"{anomaly['n_anomalies']:,}")
        with col_a3:
            st.metric("Persentase", f"{anomaly['anomaly_percentage']}%")

        st.divider()

        st.write("**Top Anomali (Aktivitas Tidak Wajar)**")
        df_anom = pd.DataFrame(anomaly["anomalies"])
        if not df_anom.empty:
            df_anom["reasons"] = df_anom["reasons"].apply(
                lambda x: ", ".join(x) if isinstance(x, list) else x
            )
            df_anom = df_anom.rename(columns={
                "user_hash": "User",
                "total_events": "Events",
                "unique_courses": "Courses",
                "anomaly_score": "Score",
                "reasons": "Alasan",
            })
            st.dataframe(df_anom, use_container_width=True, hide_index=True)

        with st.expander("📖 Interpretasi Anomali"):
            st.markdown(f"""
            **Model:** Isolation Forest dengan contamination = {anomaly['contamination']}
            
            **Hasil:**
            - {anomaly['n_anomalies']} anomali dari {anomaly['n_users']} user ({anomaly['anomaly_percentage']}%)
            - Threshold: 5% dianggap anomali
            
            **Alasan Anomali:**
            - **Sangat aktif**: total event di atas persentil 95
            - **Sangat pasif**: total event di bawah persentil 5
            - **Aktivitas burst**: events per menit sangat tinggi (kemungkinan bot/automated)
            - **Dominan chat**: >80% event adalah chat
            
            **Kegunaan:**
            - Deteksi akun bot/automated
            - Identifikasi mahasiswa yang butuh perhatian (sangat pasif)
            - Monitoring keamanan platform
            """)
    else:
        st.info("Data anomaly belum tersedia")

# ============================================================
# AUTO REFRESH
# ============================================================
time.sleep(REFRESH_SECONDS)
st.rerun()