"""
ml_unb.py - Machine Learning untuk dataset UnB
Model: Random Forest Regression
Target: avg_grade (nilai rata-rata mahasiswa)
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import warnings
warnings.filterwarnings("ignore")


def build_unb_features(df_events):
    """Bangun fitur dari log interaksi UnB."""
    if df_events.empty or "user_hash" not in df_events.columns:
        return pd.DataFrame()
    
    grouped = df_events.groupby("user_hash")
    
    features = pd.DataFrame({
        "total_events": grouped.size(),
        "unique_events": grouped["eventname"].nunique(),
        "unique_courses": grouped["courseid"].nunique(),
        "unique_actions": grouped["action"].nunique(),
    })
    
    # Fitur perilaku
    features["login_count"] = grouped.apply(
        lambda x: x["eventname"].str.contains("loggedin", case=False).sum()
    )
    features["message_count"] = grouped.apply(
        lambda x: x["eventname"].str.contains("message_sent", case=False).sum()
    )
    features["graded_count"] = grouped.apply(
        lambda x: x["eventname"].str.contains("user_graded", case=False).sum()
    )
    features["quiz_count"] = grouped.apply(
        lambda x: x["eventname"].str.contains("quiz", case=False).sum()
    )
    features["forum_count"] = grouped.apply(
        lambda x: x["eventname"].str.contains("forum", case=False).sum()
    )
    features["assign_count"] = grouped.apply(
        lambda x: x["eventname"].str.contains("assign", case=False).sum()
    )
    
    return features.fillna(0).reset_index()


def run_unb_regression(df_events, df_notes=None):
    """
    Random Forest Regression untuk prediksi avg_grade.
    
    Args:
        df_events: DataFrame dari MongoDB collection 'events'
        df_notes: DataFrame dari MongoDB collection 'notes' (opsional)
    
    Returns:
        dict dengan metrics, feature_importance, sample_predictions
    """
    # Build features
    features = build_unb_features(df_events)
    if features.empty or len(features) < 30:
        return {"error": "Data tidak cukup untuk regression (min 30 users)"}
    
    # Target: avg_grade dari notes
    if df_notes is not None and not df_notes.empty and "user_hash" in df_notes.columns:
        # Pakai nilai asli dari collection notes
        user_grades = df_notes.groupby("user_hash").agg(
            avg_grade=("finalgrade", "mean")
        ).reset_index()
        
        data = features.merge(user_grades, on="user_hash", how="inner")
        target_col = "avg_grade"
        note = "Target: avg_grade (dari notes)"
    else:
        # Fallback: pakai proxy performance_score dari aktivitas akademik
        features["academic_events"] = (
            features.get("graded_count", 0) +
            features.get("quiz_count", 0) +
            features.get("assign_count", 0)
        )
        max_academic = features["academic_events"].max()
        if max_academic > 0:
            features["performance_score"] = (
                features["academic_events"] / max_academic * 100
            ).round(2)
        else:
            features["performance_score"] = 0
        
        data = features
        target_col = "performance_score"
        note = "Target: proxy performance_score (dari aktivitas akademik)"
    
    if len(data) < 30:
        return {"error": "User dengan nilai terlalu sedikit"}
    
    # Fitur untuk regression
    feature_cols = [
        "total_events", "unique_events", "unique_courses",
        "login_count", "message_count", "forum_count",
    ]
    feature_cols = [c for c in feature_cols if c in data.columns]
    
    X = data[feature_cols].fillna(0).values
    y = data[target_col].values
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42
    )
    
    # Train Random Forest
    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=8,
        min_samples_split=5,
        min_samples_leaf=3,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)
    
    # Predict
    y_pred = model.predict(X_test)
    
    # Metrics
    mae = float(mean_absolute_error(y_test, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
    r2 = float(r2_score(y_test, y_pred))
    
    # Cross-validation
    cv_scores = cross_val_score(model, X, y, cv=5, scoring="r2")
    
    # Feature importance
    importances = model.feature_importances_
    feature_importance = sorted(
        [{"feature": f, "importance": round(float(i), 4)}
         for f, i in zip(feature_cols, importances)],
        key=lambda x: -x["importance"]
    )
    
    # Sample predictions
    sample_data = data.head(10)
    sample_pred = model.predict(sample_data[feature_cols].fillna(0).values)
    
    sample_predictions = []
    for i, (_, row) in enumerate(sample_data.iterrows()):
        sample_predictions.append({
            "user_hash": row["user_hash"][:16] + "...",
            "actual": round(float(row[target_col]), 2),
            "predicted": round(float(sample_pred[i]), 2),
            "error": round(abs(float(row[target_col]) - float(sample_pred[i])), 2),
        })
    
    return {
        "dataset": "UnB",
        "model": "RandomForestRegressor",
        "target": target_col,
        "note": note,
        "n_samples": len(data),
        "n_train": len(X_train),
        "n_test": len(X_test),
        "metrics": {
            "mae": round(mae, 4),
            "rmse": round(rmse, 4),
            "r2_score": round(r2, 4),
            "cv_r2_mean": round(float(cv_scores.mean()), 4),
            "cv_r2_std": round(float(cv_scores.std()), 4),
        },
        "feature_importance": feature_importance,
        "sample_predictions": sample_predictions,
    }