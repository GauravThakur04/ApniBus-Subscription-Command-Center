import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os
from utils import load_data, inject_custom_css, render_metric_card

st.set_page_config(
    page_title="Recovery Queue",
    layout="wide"
)

# Inject styling
inject_custom_css()

# Load data
df = load_data()

st.markdown('<div class="dashboard-title">🚨 Recovery Queue</div>', unsafe_allow_html=True)
st.markdown('<div class="dashboard-subtitle">Prioritize and manage critical churn-risk subscriptions (Red & Orange status).</div>', unsafe_allow_html=True)

# -------------------------------------------------
# Persistent CRM Logs DB Handling
# -------------------------------------------------
LOG_FILE = "data/bd_interaction_logs.csv"

def merge_crm_outcomes(recovery_df):
    if os.path.exists(LOG_FILE):
        try:
            logs = pd.read_csv(LOG_FILE)
            if not logs.empty:
                # get latest entry per DSN
                latest_logs = logs.sort_values("timestamp").groupby("dsn_number").last().reset_index()
                # Cast DSNs as string for robust matching
                latest_logs["dsn_number"] = latest_logs["dsn_number"].astype(str)
                recovery_df["dsn_number"] = recovery_df["dsn_number"].astype(str)
                
                merged = recovery_df.merge(
                    latest_logs[["dsn_number", "outcome"]],
                    on="dsn_number",
                    how="left"
                )
                merged["crm_status"] = merged["outcome"].fillna("Pending Call")
                merged.drop(columns=["outcome"], inplace=True)
                return merged
        except Exception:
            pass
    recovery_df["crm_status"] = "Pending Call"
    return recovery_df

# -------------------------------------------------
# Filter for Red & Orange status only
# -------------------------------------------------
recovery = df[df["active_status"].isin(["Red", "Orange"])].copy()

# Robust priority score function
def calculate_priority_score(row):
    score = 100 if row["active_status"] == "Red" else 50
    
    last_7_sum = 0
    for day in ["d1", "d2", "d3", "d4", "d5", "d6", "d7"]:
        val = row[day]
        if pd.notna(val):
            last_7_sum += float(val)
            
    score += min(int(last_7_sum), 100)
    return score

recovery["priority_score"] = recovery.apply(calculate_priority_score, axis=1)
recovery = recovery.sort_values("priority_score", ascending=False)
recovery = merge_crm_outcomes(recovery)

# Tabs structure
tab1, tab2 = st.tabs(["📋 Priority List", "📊 Recovery Analytics"])

with tab1:
    # -------------------------------------------------
    # Metrics
    # -------------------------------------------------
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    
    with m_col1:
        render_metric_card(
            title="Recovery Cases",
            value=f"{len(recovery):,}",
            status="Total",
            icon="🚨"
        )
        
    with m_col2:
        red_cases = len(recovery[recovery["active_status"] == "Red"])
        render_metric_card(
            title="Red Cases (High Risk)",
            value=f"{red_cases:,}",
            status="Red",
            icon="🔴"
        )
        
    with m_col3:
        orange_cases = len(recovery[recovery["active_status"] == "Orange"])
        render_metric_card(
            title="Orange Cases (Medium Risk)",
            value=f"{orange_cases:,}",
            status="Orange",
            icon="🟠"
        )
        
    with m_col4:
        missing_bus = recovery["bus_number"].isna().sum()
        render_metric_card(
            title="Missing Bus Number",
            value=f"{missing_bus:,}",
            status="Missing",
            icon="🚌"
        )

    # -------------------------------------------------
    # Expandable Filter Panel
    # -------------------------------------------------
    with st.expander("🔍 Filter Recovery Queue", expanded=False):
        f_col1, f_col2, f_col3 = st.columns(3)
        
        with f_col1:
            states = st.multiselect(
                "Filter by State",
                options=sorted(recovery["state"].dropna().unique()),
                key="rq_state"
            )
            
        with f_col2:
            bds = st.multiselect(
                "Filter by BD Name",
                options=sorted(recovery["bd_name"].dropna().astype(str).unique()),
                key="rq_bd"
            )
            
        with f_col3:
            activation_types = st.multiselect(
                "Activation Type",
                options=sorted(recovery["activation_type"].dropna().unique()),
                key="rq_act_type"
            )

    # Apply filters
    filtered_rec = recovery.copy()
    if states:
        filtered_rec = filtered_rec[filtered_rec["state"].isin(states)]
    if bds:
        filtered_rec = filtered_rec[filtered_rec["bd_name"].isin(bds)]
    if activation_types:
        filtered_rec = filtered_rec[filtered_rec["activation_type"].isin(activation_types)]

    # Search Box
    search = st.text_input("🔍 Search Priority Queue", placeholder="Search by DSN, Bus, Operator, Mobile or BD...", key="rq_search")
    if search:
        search = search.strip().lower()
        filtered_rec = filtered_rec[
            filtered_rec["dsn_number"].astype(str).str.lower().str.contains(search) |
            filtered_rec["bus_number"].astype(str).str.lower().str.contains(search) |
            filtered_rec["operator_name"].astype(str).str.lower().str.contains(search) |
            filtered_rec["mobile"].astype(str).str.lower().str.contains(search) |
            filtered_rec["bd_name"].astype(str).str.lower().str.contains(search) |
            filtered_rec["company_name"].astype(str).str.lower().str.contains(search)
        ]

    # Show results info
    st.write(f"**Displaying {len(filtered_rec):,} cases** out of {len(recovery):,} total recovery cases.")

    show_cols = [
        "priority_score",
        "active_status",
        "crm_status",
        "dsn_number",
        "bus_number",
        "current_wallet",
        "last_recharge_date",
        "company_name",
        "operator_name",
        "mobile",
        "state",
        "location",
        "bd_name",
        "d0", "d1", "d2", "d3", "d4", "d5", "d6", "d7"
    ]

    if len(filtered_rec) > 0:
        # CSV Export button
        csv = filtered_rec[show_cols].to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Export Filtered Queue to CSV",
            data=csv,
            file_name="filtered_recovery_queue.csv",
            mime="text/csv",
            use_container_width=True
        )

        st.dataframe(
            filtered_rec[show_cols],
            column_config={
                "priority_score": st.column_config.ProgressColumn(
                    "Priority Score",
                    help="Formula: Status (Red=100, Orange=50) + min(last 7 days usage, 100)",
                    format="%d",
                    min_value=50,
                    max_value=200
                ),
                "active_status": st.column_config.TextColumn("Status"),
                "crm_status": st.column_config.TextColumn("Latest Action Status"),
                "dsn_number": st.column_config.TextColumn("DSN Number"),
                "bus_number": st.column_config.TextColumn("Bus Number"),
                "mobile": st.column_config.TextColumn("Mobile"),
                "current_wallet": st.column_config.NumberColumn("Wallet Balance", format="₹%d"),
                "last_recharge_date": st.column_config.DateColumn("Last Recharge"),
            },
            use_container_width=True,
            height=500
        )
        
        # -------------------------------------------------
        # Top 25 Urgent
        # -------------------------------------------------
        st.markdown('<div class="section-header">🔥 Top 25 Most Urgent Cases</div>', unsafe_allow_html=True)
        st.dataframe(
            filtered_rec.head(25)[show_cols],
            column_config={
                "priority_score": st.column_config.ProgressColumn(
                    "Priority Score",
                    format="%d",
                    min_value=50,
                    max_value=200
                ),
                "active_status": st.column_config.TextColumn("Status"),
                "crm_status": st.column_config.TextColumn("Latest Action Status"),
                "dsn_number": st.column_config.TextColumn("DSN Number"),
                "bus_number": st.column_config.TextColumn("Bus Number"),
                "mobile": st.column_config.TextColumn("Mobile"),
                "current_wallet": st.column_config.NumberColumn("Wallet Balance", format="₹%d"),
                "last_recharge_date": st.column_config.DateColumn("Last Recharge"),
            },
            use_container_width=True
        )
    else:
        st.warning("No recovery cases match the current filter criteria.")

with tab2:
    if len(filtered_rec) > 0:
        st.markdown('<div class="section-header">📈 Recovery Workload Distribution</div>', unsafe_allow_html=True)
        
        c_col1, c_col2 = st.columns(2)
        
        with c_col1:
            # Red vs Orange
            fig_pie = px.pie(
                filtered_rec,
                names="active_status",
                color="active_status",
                color_discrete_map={"Red": "#ef4444", "Orange": "#f97316"},
                title="Status Breakdown in Recovery Queue"
            )
            fig_pie.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Outfit")
            )
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with c_col2:
            # Recovery cases by state
            state_rec = filtered_rec.groupby(["state", "active_status"]).size().reset_index(name="count")
            state_rec_sorted = filtered_rec.groupby("state").size().sort_values(ascending=False).index[:10]
            state_rec_top10 = state_rec[state_rec["state"].isin(state_rec_sorted)]
            
            fig_state_rec = px.bar(
                state_rec_top10,
                x="state",
                y="count",
                color="active_status",
                color_discrete_map={"Red": "#ef4444", "Orange": "#f97316"},
                category_orders={"state": list(state_rec_sorted)},
                title="Top 10 States Recovery Cases"
            )
            fig_state_rec.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Outfit"),
                xaxis_title=None,
                yaxis_title="Cases count"
            )
            st.plotly_chart(fig_state_rec, use_container_width=True)
            
        # Top BDs by workload
        bd_rec = filtered_rec.groupby(["bd_name", "active_status"]).size().reset_index(name="count")
        bd_rec_sorted = filtered_rec.groupby("bd_name").size().sort_values(ascending=False).index[:15]
        bd_rec_top15 = bd_rec[bd_rec["bd_name"].isin(bd_rec_sorted)]
        
        fig_bd_rec = px.bar(
            bd_rec_top15,
            y="bd_name",
            x="count",
            color="active_status",
            color_discrete_map={"Red": "#ef4444", "Orange": "#f97316"},
            category_orders={"bd_name": list(bd_rec_sorted)},
            title="Top 15 BDs Recovery Workload Load",
            orientation="h"
        )
        fig_bd_rec.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Outfit"),
            yaxis_title=None,
            xaxis_title="Cases count",
            height=400
        )
        st.plotly_chart(fig_bd_rec, use_container_width=True)
    else:
        st.info("No data available to show analytics.")