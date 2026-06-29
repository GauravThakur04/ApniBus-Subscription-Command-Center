import streamlit as st
import pandas as pd
import plotly.express as px
from utils import load_data, inject_custom_css, render_metric_card

st.set_page_config(
    page_title="State Dashboard",
    layout="wide"
)

# Inject styling
inject_custom_css()

# Load data
df = load_data()

st.markdown('<div class="dashboard-title">🗺️ State Analytics</div>', unsafe_allow_html=True)
st.markdown('<div class="dashboard-subtitle">Geographic subscription performance, health status distribution, and vehicle mapping status.</div>', unsafe_allow_html=True)

# -------------------------------------------------
# Sidebar Filters
# -------------------------------------------------
st.sidebar.header("🎯 State Filters")
selected_bds = st.sidebar.multiselect(
    "Filter by BD Name",
    options=sorted(df["bd_name"].dropna().astype(str).unique()),
    placeholder="All BDs"
)
selected_activation_types = st.sidebar.multiselect(
    "Activation Type",
    options=sorted(df["activation_type"].dropna().unique()),
    placeholder="All Types"
)

filtered_df = df.copy()
if selected_bds:
    filtered_df = filtered_df[filtered_df["bd_name"].isin(selected_bds)]
if selected_activation_types:
    filtered_df = filtered_df[filtered_df["activation_type"].isin(selected_activation_types)]

# -------------------------------------------------
# State Summary Calculations
# -------------------------------------------------
state_summary = (
    filtered_df.groupby("state")
    .agg(
        Total_DSNs=("dsn_number", "nunique"),
        Active=("active_status", lambda x: (x == "Active").sum()),
        Yellow=("active_status", lambda x: (x == "Yellow").sum()),
        Orange=("active_status", lambda x: (x == "Orange").sum()),
        Red=("active_status", lambda x: (x == "Red").sum()),
        Missing_Bus=("bus_number", lambda x: x.isna().sum()),
        Total_Recharge=("total_recharge", "sum"),
        Total_Debt=("current_wallet", lambda x: x[x < 0].sum())
    )
    .reset_index()
)
state_summary["Active_Rate"] = (state_summary["Active"] / state_summary["Total_DSNs"]) * 100
state_summary = state_summary.sort_values("Total_DSNs", ascending=False)

# -------------------------------------------------
# Metric KPI Row
# -------------------------------------------------
if len(state_summary) > 0:
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        render_metric_card(
            title="Total Active States",
            value=str(state_summary["state"].nunique()),
            status="Total",
            icon="🗺️"
        )
        
    with c2:
        top_state = state_summary.iloc[0]
        render_metric_card(
            title="Top Volume State",
            value=f"{top_state['state']} ({top_state['Total_DSNs']} DSNs)",
            status="Active",
            icon="🏆"
        )
        
    with c3:
        # Filter for states with reasonable volume (e.g. top 50% percentile DSN size) to avoid 100% active on 1 DSN state
        median_dsns = state_summary["Total_DSNs"].median()
        vol_states = state_summary[state_summary["Total_DSNs"] >= max(median_dsns, 5)]
        if len(vol_states) > 0:
            healthiest = vol_states.sort_values("Active_Rate", ascending=False).iloc[0]
            val_str = f"{healthiest['state']} ({healthiest['Active_Rate']:.1f}%)"
        else:
            val_str = "N/A"
        render_metric_card(
            title="Healthiest State",
            value=val_str,
            status="Active",
            icon="🟢"
        )
        
    with c4:
        critical_state = state_summary.sort_values(by=["Red", "Orange"], ascending=False).iloc[0]
        render_metric_card(
            title="Most Critical State",
            value=f"{critical_state['state']} ({critical_state['Red'] + critical_state['Orange']} Alert Cases)",
            status="Red",
            icon="🚨"
        )
        
    st.write("")
    
    # -------------------------------------------------
    # Stacked Status Chart
    # -------------------------------------------------
    st.markdown('<div class="section-header">📊 Status Distribution by State</div>', unsafe_allow_html=True)
    
    state_melted = state_summary.melt(
        id_vars=["state"],
        value_vars=["Active", "Yellow", "Orange", "Red"],
        var_name="Status",
        value_name="Count"
    )
    
    fig_state_status = px.bar(
        state_melted,
        x="state",
        y="Count",
        color="Status",
        color_discrete_map={
            "Active": "#10b981",
            "Yellow": "#f59e0b",
            "Orange": "#f97316",
            "Red": "#ef4444"
        },
        category_orders={"state": state_summary["state"].tolist()},
        title="DSN Health Proportions per State"
    )
    fig_state_status.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Outfit"),
        xaxis_title=None,
        yaxis_title="DSN Volume",
        legend_title=None,
        height=380
    )
    st.plotly_chart(fig_state_status, use_container_width=True)

    # -------------------------------------------------
    # Grid details
    # -------------------------------------------------
    st.markdown('<div class="section-header">📋 State Registry Performance Metrics</div>', unsafe_allow_html=True)
    st.dataframe(
        state_summary,
        column_config={
            "state": st.column_config.TextColumn("State"),
            "Total_DSNs": st.column_config.NumberColumn("Total DSNs", format="%d"),
            "Active": st.column_config.NumberColumn("Active", format="%d"),
            "Yellow": st.column_config.NumberColumn("Yellow", format="%d"),
            "Orange": st.column_config.NumberColumn("Orange", format="%d"),
            "Red": st.column_config.NumberColumn("Red", format="%d"),
            "Missing_Bus": st.column_config.NumberColumn("Missing Bus", format="%d"),
            "Total_Recharge": st.column_config.NumberColumn("Total Recharges", format="₹%d"),
            "Total_Debt": st.column_config.NumberColumn("Outstanding Debt", format="₹%d"),
            "Active_Rate": st.column_config.ProgressColumn(
                "Active Rate (%)",
                format="%.1f%%",
                min_value=0.0,
                max_value=100.0
            )
        },
        use_container_width=True,
        height=400
    )
    
    # -------------------------------------------------
    # State Drilldown Section
    # -------------------------------------------------
    st.markdown('<div class="section-header">🔍 State-wise Deep Dive</div>', unsafe_allow_html=True)
    drill_state = st.selectbox(
        "🗺️ Choose State for Detailed Breakdown",
        options=state_summary["state"].tolist()
    )
    
    state_detail = filtered_df[filtered_df["state"] == drill_state]
    
    d_col1, d_col2 = st.columns([1, 1])
    
    with d_col1:
        st.markdown(f"### BD Performance in {drill_state}")
        bd_performance = (
            state_detail.groupby("bd_name")
            .agg(
                Total_DSNs=("dsn_number", "nunique"),
                Active=("active_status", lambda x: (x == "Active").sum()),
                Red_Orange=("active_status", lambda x: x.isin(["Red", "Orange"]).sum())
            )
            .reset_index()
            .sort_values("Total_DSNs", ascending=False)
        )
        
        st.dataframe(
            bd_performance,
            column_config={
                "bd_name": st.column_config.TextColumn("BD Name"),
                "Total_DSNs": st.column_config.NumberColumn("Total DSNs", format="%d"),
                "Active": st.column_config.NumberColumn("Active", format="%d"),
                "Red_Orange": st.column_config.NumberColumn("Risk Cases", format="%d")
            },
            use_container_width=True
        )
        
    with d_col2:
        st.markdown(f"### Operator Distribution in {drill_state}")
        # Pie chart of Operator statuses inside this state
        fig_drill_pie = px.pie(
            state_detail,
            names="active_status",
            color="active_status",
            color_discrete_map={
                "Active": "#10b981",
                "Yellow": "#f59e0b",
                "Orange": "#f97316",
                "Red": "#ef4444"
            },
            hole=0.4,
            title=f"Health Breakdown inside {drill_state}"
        )
        fig_drill_pie.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Outfit"),
            height=280,
            margin=dict(l=10, r=10, t=30, b=10)
        )
        st.plotly_chart(fig_drill_pie, use_container_width=True)
else:
    st.warning("No data matches the selected filters.")