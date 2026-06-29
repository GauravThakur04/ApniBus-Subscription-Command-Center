import pandas as pd
import requests
from io import StringIO
import streamlit as st
import urllib3
import numpy as np
import io
import random

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SUBSCRIPTION_URL = "https://data.apnibus.com/public/question/67b9b4b3-ef3a-404d-9633-d9929bf79d25.csv"
MAPPING_URL = "https://data.apnibus.com/public/question/0f0c7103-13bc-4f1b-aeda-f579620b71e8.csv"

@st.cache_data(ttl=180)
def load_data():

    subs = pd.read_csv(
        StringIO(
            requests.get(
                SUBSCRIPTION_URL,
                verify=False
            ).text
        )
    )

    mapping = pd.read_csv(
        StringIO(
            requests.get(
                MAPPING_URL,
                verify=False
            ).text
        )
    )

    mapping.columns = mapping.columns.str.lower()

    mapping.rename(
        columns={
            "mobile_number":"mobile"
        },
        inplace=True
    )

    subs["mobile"] = subs["mobile"].astype(str)
    mapping["mobile"] = mapping["mobile"].astype(str)

    mapping = (
        mapping[
            ["mobile","bus_number"]
        ]
        .drop_duplicates(
            subset=["mobile"]
        )
    )

    subs = subs.merge(
        mapping,
        on="mobile",
        how="left",
        suffixes=("","_mapped")
    )

    subs["bus_number"] = subs["bus_number"].fillna(
        subs["bus_number_mapped"]
    )

    subs.drop(
        columns=["bus_number_mapped"],
        inplace=True
    )

    # Ensure financial columns are numeric and clean
    financial_cols = ["current_wallet", "total_recharge", "total_consumption", "recharge_count"]
    for col in financial_cols:
        if col in subs.columns:
            subs[col] = pd.to_numeric(subs[col], errors="coerce").fillna(0.0)

    return subs

def inject_custom_css():
    css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
    
    /* Global Typography */
    html, body, [data-testid="stAppViewContainer"], .stWidgetLabel {
        font-family: 'Outfit', sans-serif !important;
    }
    
    /* Styled Title & Subtitle */
    .dashboard-title {
        font-size: 2.4rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
        background: linear-gradient(135deg, #3b82f6, #8b5cf6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .dashboard-subtitle {
        font-size: 1rem;
        color: var(--text-color, #555555);
        opacity: 0.8;
        margin-bottom: 1.8rem;
    }
    
    /* Card Container */
    .kpi-card {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 16px 20px;
        display: flex;
        align-items: center;
        gap: 16px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.15);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        margin-bottom: 12px;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.25);
        border-color: #475569;
    }
    .kpi-icon {
        font-size: 24px;
        padding: 10px;
        border-radius: 10px;
        background: #0f172a;
        display: flex;
        align-items: center;
        justify-content: center;
        width: 44px;
        height: 44px;
    }
    .kpi-content {
        display: flex;
        flex-direction: column;
    }
    .kpi-title {
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.7px;
        color: #94a3b8;
        font-weight: 600;
    }
    .kpi-value {
        font-size: 24px;
        font-weight: 700;
        color: #f8fafc;
        margin-top: 2px;
        line-height: 1.1;
    }
    
    /* Status Borders */
    .status-card-Active { border-left: 5px solid #10b981; }
    .status-card-Yellow { border-left: 5px solid #f59e0b; }
    .status-card-Orange { border-left: 5px solid #f97316; }
    .status-card-Red { border-left: 5px solid #ef4444; }
    .status-card-Missing { border-left: 5px solid #8b5cf6; }
    .status-card-Total { border-left: 5px solid #3b82f6; }
    
    /* Section headers */
    .section-header {
        font-size: 1.4rem;
        font-weight: 600;
        margin-top: 1.5rem;
        margin-bottom: 0.8rem;
        border-bottom: 2px solid rgba(120, 120, 120, 0.15);
        padding-bottom: 0.3rem;
    }
    
    /* Custom Info banner styling */
    .info-banner {
        background-color: var(--secondary-background-color, rgba(120, 120, 120, 0.05));
        border-left: 4px solid #3b82f6;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 15px;
    }
    
    /* Modern Profile Details Card */
    .profile-card {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.15);
        margin-bottom: 20px;
    }
    .profile-header {
        display: flex;
        align-items: center;
        gap: 14px;
        border-bottom: 1px solid #334155;
        padding-bottom: 14px;
        margin-bottom: 16px;
    }
    .profile-avatar {
        font-size: 26px;
        background: #0f172a;
        padding: 8px;
        border-radius: 50%;
        width: 48px;
        height: 48px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .profile-header-text h3 {
        margin: 0;
        font-size: 1.15rem;
        color: #f8fafc;
        font-weight: 700;
    }
    .profile-header-text p {
        margin: 0;
        font-size: 0.85rem;
        color: #94a3b8;
        font-weight: 400;
    }
    .profile-grid {
        display: flex;
        flex-direction: column;
        gap: 12px;
    }
    .profile-item {
        display: flex;
        justify-content: space-between;
        font-size: 0.85rem;
        border-bottom: 1px solid rgba(51, 65, 85, 0.4);
        padding-bottom: 8px;
    }
    .profile-item:last-child {
        border-bottom: none;
        padding-bottom: 0;
    }
    .item-label {
        color: #94a3b8;
        font-weight: 500;
    }
    .item-value {
        color: #f1f5f9;
        font-weight: 600;
        text-align: right;
    }
    
    /* Modern Custom Alerts */
    .custom-alert {
        padding: 14px 16px;
        border-radius: 8px;
        display: flex;
        align-items: flex-start;
        gap: 12px;
        margin-bottom: 16px;
        font-size: 0.85rem;
    }
    .custom-alert.alert-success {
        background-color: rgba(16, 185, 129, 0.08);
        border: 1px solid rgba(16, 185, 129, 0.25);
        color: #34d399;
    }
    .custom-alert.alert-warning {
        background-color: rgba(245, 158, 11, 0.08);
        border: 1px solid rgba(245, 158, 11, 0.25);
        color: #fbbf24;
    }
    .custom-alert.alert-error {
        background-color: rgba(239, 68, 68, 0.08);
        border: 1px solid rgba(239, 68, 68, 0.25);
        color: #f87171;
    }
    .custom-alert.alert-info {
        background-color: rgba(59, 130, 246, 0.08);
        border: 1px solid rgba(59, 130, 246, 0.25);
        color: #60a5fa;
    }
    .alert-icon {
        font-size: 1.15rem;
        line-height: 1;
    }
    .alert-content strong {
        display: block;
        margin-bottom: 3px;
        font-weight: 600;
    }
    .alert-content p {
        margin: 0;
        opacity: 0.9;
        line-height: 1.35;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

def render_metric_card(title, value, status, icon="📊"):
    html_content = f"""
    <div class="kpi-card status-card-{status}">
        <div class="kpi-icon">{icon}</div>
        <div class="kpi-content">
            <div class="kpi-title">{title}</div>
            <div class="kpi-value">{value}</div>
        </div>
    </div>
    """
    st.markdown(html_content, unsafe_allow_html=True)

STATE_COORDINATES = {
    "Rajasthan": [27.0238, 74.2179],
    "Punjab": [31.1471, 75.3412],
    "Uttar Pradesh": [26.8467, 80.9462],
    "Bihar": [25.0961, 85.3131],
    "Madhya Pradesh": [22.9734, 78.6569],
    "Gujarat": [22.2587, 71.1924],
    "Maharashtra": [19.7515, 75.7139],
    "Haryana": [29.0588, 76.0856],
    "Delhi": [28.6139, 77.2090],
    "Himachal Pradesh": [31.1048, 77.1734],
    "Uttarakhand": [30.0668, 79.0193],
    "Jammu & Kashmir": [33.7780, 76.5762],
    "Chhattisgarh": [21.2787, 81.8661],
    "Jharkhand": [23.6102, 85.2799],
    "Odisha": [20.9517, 85.0985],
    "West Bengal": [22.9868, 87.8550],
    "Assam": [26.2006, 92.9376],
    "Tamil Nadu": [11.1271, 78.6569],
    "Kerala": [10.8505, 76.2711]
}

def get_geocoded_data(df):
    df_geo = df.dropna(subset=["state"]).copy()
    
    lats = []
    lons = []
    for state in df_geo["state"]:
        coords = STATE_COORDINATES.get(state, [20.5937, 78.9629])
        lats.append(coords[0] + random.uniform(-0.4, 0.4))
        lons.append(coords[1] + random.uniform(-0.4, 0.4))
        
    df_geo["latitude"] = lats
    df_geo["longitude"] = lons
    return df_geo

def calculate_churn_velocity(df):
    df_risk = df.copy()
    
    last_7_cols = [f"d{i}" for i in range(7)]
    prior_7_cols = [f"d{i}" for i in range(7, 14)]
    
    df_risk["sum_last_7"] = df_risk[last_7_cols].fillna(0).sum(axis=1)
    df_risk["sum_prior_7"] = df_risk[prior_7_cols].fillna(0).sum(axis=1)
    
    def get_drop_rate(row):
        last = row["sum_last_7"]
        prior = row["sum_prior_7"]
        if prior == 0:
            return 0.0 if last == 0 else 1.0
        return (last - prior) / prior

    df_risk["drop_rate"] = df_risk.apply(get_drop_rate, axis=1)
    df_risk["churn_risk_flag"] = (df_risk["drop_rate"] <= -0.4) & (df_risk["sum_prior_7"] >= 3)
    return df_risk

def calculate_cohort_retention(df):
    df_cohort = df.copy()
    df_cohort["dsn_created_date"] = pd.to_datetime(df_cohort["dsn_created_date"], errors="coerce")
    df_cohort = df_cohort.dropna(subset=["dsn_created_date"])
    df_cohort["cohort_month"] = df_cohort["dsn_created_date"].dt.to_period("M").astype(str)
    
    def calc_daily_retention(group):
        res = {}
        for i in range(29, -1, -1):
            day_col = f"d{i}"
            res[f"Day -{i}"] = (group[day_col].fillna(0) > 0).mean()
        return pd.Series(res)
        
    retention_matrix = df_cohort.groupby("cohort_month").apply(calc_daily_retention)
    return retention_matrix

def export_to_excel(df, velocity_df, state_df, bd_df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="All Subscriptions", index=False)
        velocity_df.to_excel(writer, sheet_name="Churn Risk Warning", index=False)
        state_df.to_excel(writer, sheet_name="State Metrics", index=False)
        bd_df.to_excel(writer, sheet_name="BD Leaderboard", index=False)
    return output.getvalue()