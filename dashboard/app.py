"""
app.py - Moodle Activity Dashboard (MongoDB)
UnB + OULAD dengan ML Analytics
"""

import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime, timezone
from pymongo import MongoClient
import sys

sys.path.append(".")
from config import CONFIG
from ml_unb import run_unb_regression
from ml_oulad import run_oulad_classification


# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Moodle Activity Dashboard",
    page_icon="📊",
    layout="wide"
)


# ============================================================
# MONGODB CONNECTION
# ============================================================
@st.cache_resource
def get_mongo_client():
    return MongoClient(CONFIG["mongo_uri"])


def get_collection(name):
    client = get_mongo_client()
    db = client[CONFIG["mongo_db"]]
    return db[name]


@st.cache_data(ttl=CONFIG["refresh_seconds"])
def load_events(limit: int = 50000) -> pd.DataFrame:
    try:
        collection = get_collection(CONFIG["collection_events"])
        cursor = collection.find({}, {"_id": 0}).limit(limit)
        records = list(cursor)
        if not records:
            return pd.DataFrame()
        df = pd.DataFrame(records)
        if "event_time" in df.columns:
            df["event_time"] = pd.to_datetime(df["event_time"], errors="coerce")
        return df
    except Exception as e:
        st.error(f"Error load events: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=CONFIG["refresh_seconds"])
def load_notes() -> pd.DataFrame:
    """Load notes dari MongoDB (nilai UnB)."""
    try:
        collection = get_collection("notes")
        cursor = collection.find({}, {"_id": 0}).limit(50000)
        records = list(cursor)
        if not records:
            return pd.DataFrame()
        return pd.DataFrame(records)
    except Exception as e:
        st.error(f"Error load notes: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=CONFIG["refresh_seconds"])
def load_oulad_collection(name: str, limit: int = 50000) -> pd.DataFrame:
    """Load OULAD collection dari MongoDB."""
    try:
        collection = get_collection(name)
        cursor = collection.find({}, {"_id": 0}).limit(limit)
        records = list(cursor)
        if not records:
            return pd.DataFrame()
        return pd.DataFrame(records)
    except Exception as e:
        st.error(f"Error load {name}: {e}")
        return pd.DataFrame()


def get_collection_count(name: str) -> int:
    try:
        return get_collection(name).count_documents({})
    except:
        return 0


# ============================================================
# HEADER
# ============================================================
st.title("📊 Moodle Activity Real-Time Dashboard")
st.caption(
    f"MongoDB: `{CONFIG['mongo_db']}` | "
    f"Refresh: every **{CONFIG['refresh_seconds']}s** | "
    f"Last update: {datetime.now().strftime('%H:%M:%S')}"
)

try:
    client = get_mongo_client()
    client.admin.command("ping")
    st.success("✅ MongoDB connected")
except Exception as e:
    st.error(f"❌ MongoDB connection failed: {e}")
    st.stop()


# ============================================================
# KPI CARDS
# ============================================================
events_count = get_collection_count(CONFIG["collection_events"])
df_events = load_events()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("📥 Total Events", f"{events_count:,}")
with col2:
    if not df_events.empty and "user_hash" in df_events.columns:
        st.metric("👥 Unique Users", f"{df_events['user_hash'].nunique():,}")
    else:
        st.metric("👥 Unique Users", "0")
with col3:
    if not df_events.empty and "courseid" in df_events.columns:
        st.metric("📚 Courses", f"{df_events['courseid'].nunique():,}")
    else:
        st.metric("📚 Courses", "0")
with col4:
    if not df_events.empty and "eventname" in df_events.columns:
        st.metric("⚡ Event Types", f"{df_events['eventname'].nunique():,}")
    else:
        st.metric("⚡ Event Types", "0")

st.divider()


# ============================================================
# EVENT TIMELINE
# ============================================================
st.subheader("📈 Event Timeline (per minute)")

if not df_events.empty and "event_time" in df_events.columns:
    df_time = df_events.dropna(subset=["event_time"]).copy()
    if not df_time.empty:
        timeline = df_time.set_index("event_time").resample("1min").size()
        if not timeline.empty:
            st.line_chart(timeline)
        else:
            st.info("No timeline data")
    else:
        st.info("No valid timestamp")
else:
    st.info("⏳ Menunggu data...")

st.divider()


# ============================================================
# ACTIVITY HEATMAP
# ============================================================
st.subheader("🔥 Activity Heatmap (Hour × Day)")

if not df_events.empty and "event_time" in df_events.columns:
    df_time = df_events.dropna(subset=["event_time"]).copy()
    if not df_time.empty:
        df_time["hour"] = df_time["event_time"].dt.hour
        df_time["day"] = df_time["event_time"].dt.day_name()
        
        day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        heatmap_data = df_time.groupby(["day", "hour"]).size().unstack(fill_value=0)
        heatmap_data = heatmap_data.reindex([d for d in day_order if d in heatmap_data.index])
        
        st.write("**Aktivitas per Jam × Hari**")
        st.dataframe(
            heatmap_data.style.background_gradient(cmap="YlOrRd", axis=None),
            use_container_width=True
        )
        
        st.write("**Aktivitas per Jam (agregat)**")
        hourly = df_time.groupby("hour").size()
        st.bar_chart(hourly)
    else:
        st.info("No valid timestamp data")
else:
    st.info("⏳ Menunggu data...")

st.divider()


# ============================================================
# USER ENGAGEMENT DISTRIBUTION
# ============================================================
st.subheader("📊 User Engagement Distribution")
st.caption("Histogram: total events per user")

if not df_events.empty and "user_hash" in df_events.columns:
    user_events = df_events.groupby("user_hash").size()
    
    col_e1, col_e2, col_e3, col_e4 = st.columns(4)
    with col_e1:
        st.metric("Total Users", f"{len(user_events):,}")
    with col_e2:
        st.metric("Mean Events/User", f"{user_events.mean():.1f}")
    with col_e3:
        st.metric("Median Events/User", f"{user_events.median():.0f}")
    with col_e4:
        st.metric("Max Events/User", f"{user_events.max():,}")
    
    st.write("**Histogram Distribusi**")
    hist, bin_edges = np.histogram(user_events, bins=20)
    df_hist = pd.DataFrame({
        "Bin": [f"{int(bin_edges[i])}-{int(bin_edges[i+1])}" for i in range(len(hist))],
        "Users": hist
    })
    df_hist = df_hist.set_index("Bin")
    st.bar_chart(df_hist)
    
    st.write("**Distribusi per Kategori**")
    categories = {
        "Low (1-5 events)": (user_events <= 5).sum(),
        "Medium (6-20 events)": ((user_events > 5) & (user_events <= 20)).sum(),
        "High (21-50 events)": ((user_events > 20) & (user_events <= 50)).sum(),
        "Very High (>50 events)": (user_events > 50).sum(),
    }
    df_cat = pd.DataFrame({
        "Kategori": list(categories.keys()),
        "Users": list(categories.values())
    })
    df_cat["Persentase"] = (df_cat["Users"] / len(user_events) * 100).round(2)
    st.dataframe(df_cat, use_container_width=True, hide_index=True)
else:
    st.info("⏳ Menunggu data...")

st.divider()


# ============================================================
# TOP USERS
# ============================================================
st.subheader("🏆 Top Users (Paling Aktif)")

if not df_events.empty and "user_hash" in df_events.columns:
    top_users = (
        df_events.groupby("user_hash")
        .agg(
            total_events=("eventname", "count"),
            unique_events=("eventname", "nunique"),
            unique_courses=("courseid", "nunique"),
        )
        .sort_values("total_events", ascending=False)
        .head(10)
        .reset_index()
    )
    
    top_users["user_hash"] = top_users["user_hash"].str[:16] + "..."
    top_users = top_users.rename(columns={
        "user_hash": "User",
        "total_events": "Total Events",
        "unique_events": "Event Types",
        "unique_courses": "Courses",
    })
    
    st.dataframe(top_users, use_container_width=True, hide_index=True)
    
    st.write("**Top 10 Users — Total Events**")
    df_top_chart = top_users.set_index("User")["Total Events"]
    st.bar_chart(df_top_chart)
else:
    st.info("⏳ Menunggu data...")

st.divider()


# ============================================================
# TOP 10 LAST ACTIVITY
# ============================================================
st.subheader("🕐 Top 10 Last Activity")
st.caption("10 aktivitas terbaru")

if not df_events.empty:
    df_last = df_events.copy()
    if "event_time" in df_last.columns:
        df_last = df_last.sort_values("event_time", ascending=False)
    df_last = df_last.head(10)
    
    last_cols = [c for c in [
        "event_time", "user_hash", "courseid", "eventname", "action"
    ] if c in df_last.columns]
    
    df_display = df_last[last_cols].copy()
    if "user_hash" in df_display.columns:
        df_display["user_hash"] = df_display["user_hash"].str[:12] + "..."
    if "eventname" in df_display.columns:
        df_display["eventname"] = df_display["eventname"].apply(
            lambda x: x.split("\\")[-1] if "\\" in x else x
        )
    
    df_display = df_display.rename(columns={
        "event_time": "Time",
        "user_hash": "User",
        "courseid": "Course",
        "eventname": "Event",
        "action": "Action",
    })
    
    st.dataframe(df_display, use_container_width=True, hide_index=True)
else:
    st.info("⏳ Menunggu events...")


# ============================================================
# MACHINE LEARNING ANALYTICS — UNB + OULAD
# ============================================================
st.divider()
st.header("🧠 Machine Learning Analytics")
st.caption("UnB: Regression (avg_grade) • OULAD: Classification (final_result)")

tab_ml1, tab_ml2 = st.tabs([
    "📊 UnB — Regression (avg_grade)",
    "🎓 OULAD — Classification (final_result)",
])

# ------------------------------------------------------------
# TAB 1: UNB REGRESSION
# ------------------------------------------------------------
with tab_ml1:
    st.subheader("UnB — Prediksi Nilai Mahasiswa")
    st.caption("Model: Random Forest Regressor | Target: avg_grade")
    
    if not df_events.empty:
        with st.spinner("Training Random Forest Regression..."):
            df_notes = load_notes()
            result = run_unb_regression(df_events, df_notes)
        
        if "error" in result:
            st.warning(result["error"])
        else:
            st.info(f"📊 {result['note']}")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("R² Score", f"{result['metrics']['r2_score']:.4f}")
            with col2:
                st.metric("MAE", f"{result['metrics']['mae']:.4f}")
            with col3:
                st.metric("RMSE", f"{result['metrics']['rmse']:.4f}")
            with col4:
                st.metric("Samples", f"{result['n_samples']}")
            
            st.caption(
                f"CV R²: {result['metrics']['cv_r2_mean']:.4f} "
                f"(±{result['metrics']['cv_r2_std']:.4f}) | "
                f"Train: {result['n_train']} | Test: {result['n_test']}"
            )
            
            st.divider()
            
            st.write("**Feature Importance**")
            if result["feature_importance"]:
                df_imp = pd.DataFrame(result["feature_importance"])
                df_imp = df_imp.set_index("feature")["importance"].sort_values(ascending=True)
                st.bar_chart(df_imp)
            
            st.write("**Sample Predictions**")
            df_pred = pd.DataFrame(result["sample_predictions"])
            st.dataframe(df_pred, use_container_width=True, hide_index=True)
    else:
        st.info("⏳ Menunggu data UnB...")

# ------------------------------------------------------------
# TAB 2: OULAD CLASSIFICATION
# ------------------------------------------------------------
with tab_ml2:
    st.subheader("OULAD — Prediksi Kelulusan Mahasiswa")
    st.caption("Model: Random Forest Classifier | Target: final_result")
    
    df_oulad_vle = load_oulad_collection("oulad_vle", limit=100000)
    df_oulad_assess = load_oulad_collection("oulad_assessment", limit=100000)
    df_oulad_students = load_oulad_collection("oulad_students", limit=50000)
    
    if not df_oulad_students.empty:
        with st.spinner("Training Random Forest Classification..."):
            result = run_oulad_classification(df_oulad_vle, df_oulad_assess, df_oulad_students)
        
        if "error" in result:
            st.warning(result["error"])
        else:
            st.info(f"🎯 Kelas: {', '.join(result['classes'])}")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Accuracy", f"{result['metrics']['accuracy']:.2%}")
            with col2:
                st.metric("Precision", f"{result['metrics']['precision']:.2%}")
            with col3:
                st.metric("Recall", f"{result['metrics']['recall']:.2%}")
            with col4:
                st.metric("F1 Score", f"{result['metrics']['f1_score']:.2%}")
            
            st.caption(
                f"CV Accuracy: {result['metrics']['cv_accuracy_mean']:.2%} "
                f"(±{result['metrics']['cv_accuracy_std']:.2%}) | "
                f"Samples: {result['n_samples']} | "
                f"Train: {result['n_train']} | Test: {result['n_test']}"
            )
            
            st.divider()
            
            st.write("**Feature Importance**")
            if result["feature_importance"]:
                df_imp = pd.DataFrame(result["feature_importance"])
                df_imp = df_imp.set_index("feature")["importance"].sort_values(ascending=True)
                st.bar_chart(df_imp)
            
            st.write("**Confusion Matrix**")
            cm = np.array(result["confusion_matrix"])
            df_cm = pd.DataFrame(
                cm,
                index=[f"Actual: {c}" for c in result["classes"]],
                columns=[f"Predicted: {c}" for c in result["classes"]],
            )
            st.dataframe(df_cm, use_container_width=True)
            
            st.write("**Sample Predictions**")
            df_pred = pd.DataFrame(result["sample_predictions"])
            st.dataframe(df_pred, use_container_width=True, hide_index=True)
    else:
        st.info("⏳ Menunggu data OULAD...")


# ============================================================
# AUTO REFRESH
# ============================================================
time.sleep(CONFIG["refresh_seconds"])
st.rerun()