import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os
from utils import load_data, inject_custom_css, render_metric_card

st.set_page_config(
    page_title="Operator 360",
    layout="wide"
)

# Inject CSS styling
inject_custom_css()

# Load data
df = load_data()

st.markdown('<div class="dashboard-title">🎯 Operator 360</div>', unsafe_allow_html=True)
st.markdown('<div class="dashboard-subtitle">Search and inspect detailed operator profiles, booking activity history, and risk diagnostics.</div>', unsafe_allow_html=True)

# -------------------------------------------------
# CRM Interaction Logs Loader
# -------------------------------------------------
LOG_FILE = "data/bd_interaction_logs.csv"

def load_operator_logs(dsn_num):
    if os.path.exists(LOG_FILE):
        try:
            logs = pd.read_csv(LOG_FILE)
            logs["dsn_number"] = logs["dsn_number"].astype(str)
            op_logs = logs[logs["dsn_number"] == str(dsn_num)].copy()
            return op_logs.sort_values("timestamp", ascending=False)
        except Exception:
            pass
    return pd.DataFrame()

def render_custom_alert(title, text, type_alert, icon="⚠️"):
    alert_html = f"""
    <div class="custom-alert alert-{type_alert}">
        <div class="alert-icon">{icon}</div>
        <div class="alert-content">
            <strong>{title}</strong>
            <p>{text}</p>
        </div>
    </div>
    """
    st.markdown(alert_html, unsafe_allow_html=True)

# -------------------------------------------------
# Advanced Search Widget
# -------------------------------------------------
search = st.text_input(
    "🔍 Search Operator Database",
    placeholder="Type DSN, Bus Number, Operator Name, Mobile, Company, or BD Rep...",
    help="Search results will auto-populate the profile picker below."
)

if search:
    search_term = search.strip().lower()
    result = df[
        df["dsn_number"].astype(str).str.lower().str.contains(search_term) |
        df["bus_number"].astype(str).str.lower().str.contains(search_term) |
        df["operator_name"].astype(str).str.lower().str.contains(search_term) |
        df["mobile"].astype(str).str.lower().str.contains(search_term) |
        df["company_name"].astype(str).str.lower().str.contains(search_term) |
        df["bd_name"].astype(str).str.lower().str.contains(search_term)
    ]
else:
    result = df

if len(result) == 0:
    st.warning("⚠️ No operators matched your search query. Please try different keywords.")
else:
    # Build selectbox options
    result = result.copy()
    result["selector_label"] = result.apply(
        lambda r: f"[{r['dsn_number']}] {r['operator_name']} - {r['company_name']} ({r['active_status']})",
        axis=1
    )
    
    st.info(f"🔍 Found {len(result):,} matches. Please choose one from the selector below.")
    
    selected_option = st.selectbox(
        "🎯 Select Operator Profile",
        options=result["selector_label"].tolist()
    )
    
    row = result[result["selector_label"] == selected_option].iloc[0]
    
    # Load CRM interaction logs for this operator
    op_logs = load_operator_logs(row["dsn_number"])
    
    # Calculate usage metrics
    days = [f"d{i}" for i in range(30)]
    usage_values = []
    for d in days:
        val = row[d]
        usage_values.append(float(val) if pd.notna(val) else 0.0)
    total_bookings = sum(usage_values)
    avg_bookings = np.mean(usage_values)
    active_days = sum(1 for v in usage_values if v > 0)
    
    # -------------------------------------------------
    # Key Performance Metric Row (Consolidated 4 Cards)
    # -------------------------------------------------
    st.markdown('<div class="section-header">📌 Key Performance Indicators</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        render_metric_card(
            title="Subscription Health",
            value=str(row["active_status"]),
            status=str(row["active_status"]),
            icon="❤️"
        )
        
    with c2:
        wallet_val = row["current_wallet"]
        status_wallet = "Active" if wallet_val >= 0 else "Red"
        render_metric_card(
            title="Current Wallet Balance",
            value=f"₹{wallet_val:,.2f}",
            status=status_wallet,
            icon="💼"
        )
        
    with c3:
        recharge_val = row["total_recharge"]
        render_metric_card(
            title="Total Recharged Amount",
            value=f"₹{recharge_val:,.2f}",
            status="Total",
            icon="🪙"
        )
        
    with c4:
        render_metric_card(
            title="Total Bookings (Last 30d)",
            value=f"{int(total_bookings):,}",
            status="Total",
            icon="📊"
        )
        
    st.write("")
    
    # -------------------------------------------------
    # Two Column Layout: Profile vs Usage Trend
    # -------------------------------------------------
    left_col, right_col = st.columns([1, 1])
    
    with left_col:
        # Styled Profile Box
        bus_str = str(row["bus_number"]) if pd.notna(row["bus_number"]) else "Not Mapped"
        profile_html = f"""
        <div class="profile-card">
            <div class="profile-header">
                <span class="profile-avatar">👤</span>
                <div class="profile-header-text">
                    <h3>{row['operator_name']}</h3>
                    <p>{row['company_name']}</p>
                </div>
            </div>
            <div class="profile-grid">
                <div class="profile-item"><span class="item-label">DSN Number</span><span class="item-value">{row['dsn_number']}</span></div>
                <div class="profile-item"><span class="item-label">Bus Number</span><span class="item-value">{bus_str}</span></div>
                <div class="profile-item"><span class="item-label">Registered Mobile</span><span class="item-value">{row['mobile']}</span></div>
                <div class="profile-item"><span class="item-label">State Location</span><span class="item-value">{row['state']} ({row['location']})</span></div>
                <div class="profile-item"><span class="item-label">BD Representative</span><span class="item-value">{row['bd_name']}</span></div>
                <div class="profile-item"><span class="item-label">Activation Status</span><span class="item-value">{row['activation_type']}</span></div>
                <div class="profile-item"><span class="item-label">DSN Creation Date</span><span class="item-value">{row['dsn_created_date']}</span></div>
            </div>
        </div>
        """
        st.markdown(profile_html, unsafe_allow_html=True)
        
        # -------------------------------------------------
        # Wallet & Action Recommendations Alerts
        # -------------------------------------------------
        st.markdown('<div class="section-header">🔔 Active System & Financial Alerts</div>', unsafe_allow_html=True)
        
        # 1. Financial Status Alert
        if wallet_val < 0:
            render_custom_alert(
                "Outstanding Balance Alert",
                f"This operator has an outstanding wallet balance of <b>₹{abs(wallet_val):,.2f}</b>. Immediate collection callback required.",
                "error",
                "💳"
            )
        elif 0 <= wallet_val < 500:
            render_custom_alert(
                "Low Wallet Balance Advisory",
                f"Wallet balance is low at <b>₹{wallet_val:,.2f}</b>. Remind operator to recharge to avoid blockages.",
                "warning",
                "💳"
            )
        else:
            render_custom_alert(
                "Wallet Status Healthy",
                f"Operator's current wallet balance is healthy at <b>₹{wallet_val:,.2f}</b>.",
                "success",
                "💳"
            )
        
        # 2. CRM Call Action Recommendation Alert
        if not op_logs.empty:
            # Grab latest logged interaction
            latest_log = op_logs.iloc[0]
            outcome = latest_log["outcome"]
            rep_name = latest_log["bd_name"]
            timestamp = latest_log["timestamp"]
            notes = latest_log["notes"]
            channel = latest_log["contacted_via"]
            follow_up = latest_log["follow_up_date"]
            
            if "Resolved" in outcome:
                render_custom_alert(
                    f"CRM Status: Resolved ({outcome})",
                    f"Last call logged on {timestamp} by {rep_name} via {channel}. Notes: {notes}",
                    "success",
                    "✅"
                )
            else:
                render_custom_alert(
                    f"CRM Status: Unresolved ({outcome})",
                    f"Last contacted on {timestamp} by {rep_name} via {channel}.  \n"
                    f"<b>Notes</b>: {notes}  \n"
                    f"📅 <b>Next Follow-up Scheduled</b>: {follow_up}",
                    "warning",
                    "⏳"
                )
        else:
            # Fall back to default recommendations based on health status
            status = row["active_status"]
            if pd.isna(row["bus_number"]):
                render_custom_alert(
                    "Critical Alert: Missing Bus Number",
                    "GPS telemetry cannot track this vehicle. Please coordinate with the BD Rep to verify mobile connection and register the correct Bus Number.",
                    "error",
                    "🚌"
                )
            elif status == "Red":
                render_custom_alert(
                    "Urgent Action: Churn Prevention Call",
                    "Daily usage has dropped to critical lows. Schedule an immediate outbound call. Troubleshoot if they switched to competitors or have device technical failure.",
                    "error",
                    "🔴"
                )
            elif status == "Orange":
                render_custom_alert(
                    "Warning: High Risk of Churn",
                    "Significant booking drop in the last week. Contact the BD to check in on service health, billing renewal issues, or route modifications.",
                    "warning",
                    "🟠"
                )
            elif status == "Yellow":
                render_custom_alert(
                    "Advisory: Moderate Drop Detected",
                    "Usage is showing minor fluctuations. Send a retention check-in text. Ensure hardware and dashboard displays are fully operational.",
                    "info",
                    "🟡"
                )
            else:
                render_custom_alert(
                    "System Healthy: Active Subscription",
                    "Usage pattern is stable and active. Continue routine background tracking.",
                    "success",
                    "🟢"
                )
            
    with right_col:
        # Chronological order: d29 (oldest) to d0 (today)
        days_rev = days[::-1]
        values_rev = usage_values[::-1]
        
        # Human readable timeline labels
        timeline_labels = [f"Day -{i}" if i > 0 else "Today" for i in range(29, -1, -1)]
        
        trend_df = pd.DataFrame({
            "Timeline": timeline_labels,
            "Bookings": values_rev,
            "Index": range(30)
        })
        
        # Plotly Area Chart
        fig_usage = px.area(
            trend_df,
            x="Timeline",
            y="Bookings",
            title="30-Day Chronological Booking Trend",
            labels={"Timeline": "Days Ago", "Bookings": "Daily Bookings"}
        )
        fig_usage.update_traces(
            line_color="#3b82f6",
            fillcolor="rgba(59, 130, 246, 0.15)",
            hovertemplate="<b>%{x}</b><br>Bookings: %{y}<extra></extra>"
        )
        fig_usage.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Outfit"),
            height=300,
            margin=dict(l=20, r=20, t=40, b=20),
            xaxis=dict(showgrid=False, tickmode="linear", dtick=5),
            yaxis=dict(showgrid=True, gridcolor="rgba(120, 120, 120, 0.15)")
        )
        
        st.plotly_chart(fig_usage, use_container_width=True)
        
        # Usage statistics summary cards
        st.markdown('<div class="section-header">📈 Booking Timeline Statistics</div>', unsafe_allow_html=True)
        stat_col1, stat_col2, stat_col3 = st.columns(3)
        with stat_col1:
            st.metric("Total Bookings", f"{int(total_bookings):,}", help="Sum of bookings over past 30 days")
        with stat_col2:
            st.metric("Daily Average", f"{avg_bookings:.1f}", help="Average daily bookings over past 30 days")
        with stat_col3:
            st.metric("Active Days", f"{active_days}/30", help="Number of days with at least 1 booking")

    st.write("")
    st.markdown('<div class="section-header">📜 Support Interaction & Complaints History</div>', unsafe_allow_html=True)
    if not op_logs.empty:
        st.dataframe(
            op_logs[[
                "timestamp", "contacted_via", "notes", "outcome", "follow_up_date", "bd_name"
            ]],
            column_config={
                "timestamp": st.column_config.TextColumn("Logged At"),
                "notes": st.column_config.TextColumn("Complaint / Interaction Notes"),
                "follow_up_date": st.column_config.DateColumn("Scheduled Follow-up"),
                "bd_name": st.column_config.TextColumn("Logged By")
            },
            use_container_width=True
        )
    else:
        st.info("No CRM call interactions or complaint logs exist for this operator profile yet.")

    st.write("")
    st.markdown('<div class="section-header">📄 Full Technical Registry Log</div>', unsafe_allow_html=True)
    st.dataframe(
        pd.DataFrame(row).T.drop(columns=["selector_label"], errors="ignore"),
        use_container_width=True
    )