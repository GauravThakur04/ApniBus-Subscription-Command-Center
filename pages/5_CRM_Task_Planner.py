import streamlit as st
import pandas as pd
import numpy as np
import os
import datetime
from utils import load_data, inject_custom_css, render_metric_card

st.set_page_config(
    page_title="BD CRM Planner",
    layout="wide"
)

# Inject custom stylesheet
inject_custom_css()

# Load main dataset
df = load_data()

st.markdown('<div class="dashboard-title">🎯 BD CRM & Task Planner</div>', unsafe_allow_html=True)
st.markdown('<div class="dashboard-subtitle">Select your BD identity to review portfolio alert cases and log call interactions persistently.</div>', unsafe_allow_html=True)

# -------------------------------------------------
# Persistent CRM Logs DB Handling
# -------------------------------------------------
LOG_FILE = "data/bd_interaction_logs.csv"

def load_interaction_logs():
    if os.path.exists(LOG_FILE):
        try:
            return pd.read_csv(LOG_FILE)
        except Exception:
            pass
    # Return empty template if not exists
    return pd.DataFrame(columns=[
        "timestamp", "bd_name", "dsn_number", "operator_name", 
        "contacted_via", "notes", "outcome", "follow_up_date"
    ])

def save_interaction_log(row_dict):
    logs_df = load_interaction_logs()
    new_row = pd.DataFrame([row_dict])
    logs_df = pd.concat([logs_df, new_row], ignore_index=True)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    logs_df.to_csv(LOG_FILE, index=False)

# Load existing logs
logs_df = load_interaction_logs()

# -------------------------------------------------
# BD Selector panel
# -------------------------------------------------
all_bd_names = sorted(df["bd_name"].dropna().astype(str).unique())
selected_bd = st.selectbox(
    "👨‍💼 Identify BD Representative",
    options=all_bd_names,
    placeholder="Choose your name..."
)

if selected_bd:
    # Get portfolio records
    bd_portfolio = df[df["bd_name"] == selected_bd].copy()
    
    # Filter for critical cases (Red/Orange)
    critical_cases = bd_portfolio[bd_portfolio["active_status"].isin(["Red", "Orange"])].copy()
    
    # Merge latest outcomes from logs to display call status
    if not logs_df.empty:
        # Get the latest entry for each DSN to find its current state
        latest_entries = logs_df.sort_values("timestamp").groupby("dsn_number").last().reset_index()
        critical_cases = critical_cases.merge(
            latest_entries[["dsn_number", "outcome", "timestamp"]],
            on="dsn_number",
            how="left"
        )
    else:
        critical_cases["outcome"] = np.nan
        critical_cases["timestamp"] = np.nan
        
    critical_cases["outcome"] = critical_cases["outcome"].fillna("Pending Call")
    
    # -------------------------------------------------
    # Metrics Header
    # -------------------------------------------------
    st.markdown('<div class="section-header">📌 Portfolio Status Summary</div>', unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    
    with m1:
        render_metric_card(
            title="Total DSN Portfolio",
            value=f"{len(bd_portfolio):,}",
            status="Total",
            icon="📋"
        )
        
    with m2:
        total_risk = len(critical_cases)
        render_metric_card(
            title="Total Risk Cases",
            value=f"{total_risk:,}",
            status="Red" if total_risk > 0 else "Active",
            icon="🚨"
        )
        
    with m3:
        logged_calls = len(logs_df[logs_df["bd_name"] == selected_bd])
        render_metric_card(
            title="Total Logged Calls",
            value=f"{logged_calls:,}",
            status="Active",
            icon="📞"
        )
        
    with m4:
        # Pending cases are those with outcome "Pending Call" or "Needs Callback"
        pending_cases = len(critical_cases[critical_cases["outcome"].isin(["Pending Call", "Needs Callback"])])
        render_metric_card(
            title="Pending Call Backs",
            value=f"{pending_cases:,}",
            status="Orange" if pending_cases > 0 else "Active",
            icon="⏳"
        )
        
    st.write("")
    
    # -------------------------------------------------
    # Form and Grid layout
    # -------------------------------------------------
    col_left, col_right = st.columns([1, 1])
    
    with col_left:
        st.markdown('<div class="section-header">📞 Log Call Interaction</div>', unsafe_allow_html=True)
        
        with st.form("crm_log_form", clear_on_submit=True):
            # Select operator from critical options
            op_choices = []
            for _, r in critical_cases.iterrows():
                op_choices.append(f"{r['dsn_number']} - {r['operator_name']} ({r['active_status']}) [Outcome: {r['outcome']}]")
                
            if op_choices:
                selected_op = st.selectbox(
                    "🎯 Select Target Operator",
                    options=op_choices,
                    help="Only shows active Red and Orange churn-risk accounts."
                )
                
                target_dsn = selected_op.split(" - ")[0]
                target_row = critical_cases[critical_cases["dsn_number"] == target_dsn].iloc[0]
                
                channel = st.selectbox(
                    "📱 Communication Medium",
                    options=["Phone Call", "WhatsApp Message", "In-Person Visit", "SMS Alert"]
                )
                
                notes = st.text_area(
                    "📝 Call Summary & Action Plan",
                    placeholder="Brief details about call conversation, concerns raised, competitor details, or hardware troubleshooting..."
                )
                
                outcome = st.selectbox(
                    "💡 Resolution Outcome",
                    options=[
                        "Needs Callback",
                        "Resolved - GPS Configured",
                        "Resolved - Payment Collected",
                        "Resolved - Hardware Restored",
                        "Refused to Renew - Competitor Switch",
                        "No Response - Left Message"
                    ]
                )
                
                follow_date = st.date_input(
                    "📅 Next Follow-up Scheduled",
                    value=datetime.date.today() + datetime.timedelta(days=3)
                )
                
                submit = st.form_submit_button("💾 Save Call Log Details", use_container_width=True)
                
                if submit:
                    log_data_dict = {
                        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "bd_name": selected_bd,
                        "dsn_number": target_dsn,
                        "operator_name": target_row["operator_name"],
                        "contacted_via": channel,
                        "notes": notes if notes.strip() else "No details provided.",
                        "outcome": outcome,
                        "follow_up_date": follow_date.strftime("%Y-%m-%d")
                    }
                    save_interaction_log(log_data_dict)
                    st.success(f"Successfully recorded update for {target_row['operator_name']}!")
                    st.rerun()
            else:
                st.success("🎉 **Fantastic work!** You have no active Red or Orange cases in your portfolio requiring attention.")
                st.form_submit_button("All Caught Up", disabled=True)
                
    with col_right:
        st.markdown('<div class="section-header">📋 Pending Portfolio Actions List</div>', unsafe_allow_html=True)
        if len(critical_cases) > 0:
            st.dataframe(
                critical_cases[[
                    "active_status", "dsn_number", "operator_name", 
                    "bus_number", "mobile", "outcome"
                ]],
                column_config={
                    "active_status": st.column_config.TextColumn("Status"),
                    "dsn_number": st.column_config.TextColumn("DSN"),
                    "bus_number": st.column_config.TextColumn("Bus"),
                    "mobile": st.column_config.TextColumn("Mobile"),
                    "outcome": st.column_config.TextColumn("Latest Action Outcome")
                },
                use_container_width=True,
                height=350
            )
        else:
            st.info("No active recovery cases to display in your registry.")
            
    # -------------------------------------------------
    # Call Log History registry
    # -------------------------------------------------
    st.markdown('<div class="section-header">📜 Historic BD Interaction Logs Timeline</div>', unsafe_allow_html=True)
    bd_logs = logs_df[logs_df["bd_name"] == selected_bd].sort_values("timestamp", ascending=False)
    
    if not bd_logs.empty:
        st.dataframe(
            bd_logs[[
                "timestamp", "dsn_number", "operator_name", 
                "contacted_via", "notes", "outcome", "follow_up_date"
            ]],
            column_config={
                "timestamp": st.column_config.TextColumn("Logged At"),
                "dsn_number": st.column_config.TextColumn("DSN"),
                "notes": st.column_config.TextColumn("Action Notes"),
                "follow_up_date": st.column_config.DateColumn("Follow-up Schedule")
            },
            use_container_width=True,
            height=300
        )
    else:
        st.info("No interaction logs found for this BD representative yet.")
else:
    st.info("Select your BD representative profile in the input selector above to load your personalized planner.")
