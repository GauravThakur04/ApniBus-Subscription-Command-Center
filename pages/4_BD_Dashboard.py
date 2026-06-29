import streamlit as st
import pandas as pd
import plotly.express as px
from utils import load_data, inject_custom_css, render_metric_card

st.set_page_config(
    page_title="BD Dashboard",
    layout="wide"
)

# Inject styling
inject_custom_css()

# Load data
df = load_data()

st.markdown('<div class="dashboard-title">👨‍💼 BD Performance Command Center</div>', unsafe_allow_html=True)
st.markdown('<div class="dashboard-subtitle">Evaluate Business Development performance rankings, active subscription health, and recovery workloads.</div>', unsafe_allow_html=True)

# -------------------------------------------------
# Sidebar Filters
# -------------------------------------------------
st.sidebar.header("🎯 BD Filters")
selected_states = st.sidebar.multiselect(
    "Filter by State",
    options=sorted(df["state"].dropna().unique()),
    placeholder="All States"
)
selected_activation_types = st.sidebar.multiselect(
    "Activation Type",
    options=sorted(df["activation_type"].dropna().unique()),
    placeholder="All Types"
)

filtered_df = df.copy()
if selected_states:
    filtered_df = filtered_df[filtered_df["state"].isin(selected_states)]
if selected_activation_types:
    filtered_df = filtered_df[filtered_df["activation_type"].isin(selected_activation_types)]

# -------------------------------------------------
# BD Summary Calculations
# -------------------------------------------------
bd_summary = (
    filtered_df.groupby("bd_name")
    .agg(
        Total_DSNs=("dsn_number", "nunique"),
        Active=("active_status", lambda x: (x == "Active").sum()),
        Yellow=("active_status", lambda x: (x == "Yellow").sum()),
        Orange=("active_status", lambda x: (x == "Orange").sum()),
        Red=("active_status", lambda x: (x == "Red").sum()),
        Recovery_Workload=("active_status", lambda x: x.isin(["Red", "Orange"]).sum()),
        Total_Recharge=("total_recharge", "sum"),
        Total_Debt=("current_wallet", lambda x: x[x < 0].sum())
    )
    .reset_index()
)
bd_summary["Active_Rate"] = (bd_summary["Active"] / bd_summary["Total_DSNs"]) * 100
bd_summary = bd_summary.sort_values("Total_DSNs", ascending=False)

# -------------------------------------------------
# Metric KPI Row
# -------------------------------------------------
if len(bd_summary) > 0:
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        render_metric_card(
            title="Total BD Reps",
            value=str(bd_summary["bd_name"].nunique()),
            status="Total",
            icon="👨‍💼"
        )
        
    with c2:
        top_vol = bd_summary.iloc[0]
        render_metric_card(
            title="Highest Volume BD",
            value=f"{top_vol['bd_name']} ({top_vol['Total_DSNs']} DSNs)",
            status="Active",
            icon="📊"
        )
        
    with c3:
        # Filter for BDs with a representative minimum volume (e.g. median DSN count) to keep it fair
        median_dsns = bd_summary["Total_DSNs"].median()
        fair_bds = bd_summary[bd_summary["Total_DSNs"] >= max(median_dsns, 3)]
        if len(fair_bds) > 0:
            top_health = fair_bds.sort_values("Active_Rate", ascending=False).iloc[0]
            health_val = f"{top_health['bd_name']} ({top_health['Active_Rate']:.1f}%)"
        else:
            health_val = "N/A"
        render_metric_card(
            title="Top Health Rate BD",
            value=health_val,
            status="Active",
            icon="🟢"
        )
        
    with c4:
        top_load = bd_summary.sort_values(by="Recovery_Workload", ascending=False).iloc[0]
        render_metric_card(
            title="Highest Recovery Load",
            value=f"{top_load['bd_name']} ({top_load['Recovery_Workload']} Cases)",
            status="Red",
            icon="🚨"
        )
        
    st.write("")

    # -------------------------------------------------
    # Stacked Proportions Chart
    # -------------------------------------------------
    st.markdown('<div class="section-header">📊 Status Distribution for Top 20 BDs (by Volume)</div>', unsafe_allow_html=True)
    
    top20_bd_names = bd_summary["bd_name"].head(20).tolist()
    bd_summary_top20 = bd_summary[bd_summary["bd_name"].isin(top20_bd_names)]
    
    bd_melted = bd_summary_top20.melt(
        id_vars=["bd_name"],
        value_vars=["Active", "Yellow", "Orange", "Red"],
        var_name="Status",
        value_name="Count"
    )
    
    fig_bd_status = px.bar(
        bd_melted,
        x="bd_name",
        y="Count",
        color="Status",
        color_discrete_map={
            "Active": "#10b981",
            "Yellow": "#f59e0b",
            "Orange": "#f97316",
            "Red": "#ef4444"
        },
        category_orders={"bd_name": top20_bd_names},
        title="DSN Status Breakdown per BD"
    )
    fig_bd_status.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Outfit"),
        xaxis_title=None,
        yaxis_title="DSN Volume",
        legend_title=None,
        height=380
    )
    st.plotly_chart(fig_bd_status, use_container_width=True)

    # -------------------------------------------------
    # Leaderboard Grid
    # -------------------------------------------------
    st.markdown('<div class="section-header">🏆 BD Performance Leaderboard</div>', unsafe_allow_html=True)
    st.dataframe(
        bd_summary,
        column_config={
            "bd_name": st.column_config.TextColumn("BD Name"),
            "Total_DSNs": st.column_config.NumberColumn("Total DSNs", format="%d"),
            "Active": st.column_config.NumberColumn("Active", format="%d"),
            "Yellow": st.column_config.NumberColumn("Yellow", format="%d"),
            "Orange": st.column_config.NumberColumn("Orange", format="%d"),
            "Red": st.column_config.NumberColumn("Red", format="%d"),
            "Recovery_Workload": st.column_config.NumberColumn("Recovery Load", format="%d"),
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
    # BD Portfolio Drilldown
    # -------------------------------------------------
    st.markdown('<div class="section-header">🔍 Individual BD Portfolio Drilldown</div>', unsafe_allow_html=True)
    
    drill_bd = st.selectbox(
        "👨‍💼 Select BD Representative to Inspect",
        options=sorted(bd_summary["bd_name"].tolist())
    )
    
    bd_detail = filtered_df[filtered_df["bd_name"] == drill_bd]
    
    d_col1, d_col2 = st.columns([2, 1])
    
    with d_col1:
        st.markdown(f"### DSN Registry for {drill_bd}")
        st.dataframe(
            bd_detail[[
                "active_status",
                "dsn_number",
                "bus_number",
                "current_wallet",
                "last_recharge_date",
                "operator_name",
                "company_name",
                "mobile",
                "state"
            ]],
            column_config={
                "active_status": st.column_config.TextColumn("Status"),
                "dsn_number": st.column_config.TextColumn("DSN"),
                "bus_number": st.column_config.TextColumn("Bus"),
                "mobile": st.column_config.TextColumn("Mobile"),
                "current_wallet": st.column_config.NumberColumn("Wallet Balance", format="₹%d"),
                "last_recharge_date": st.column_config.DateColumn("Last Recharge"),
            },
            use_container_width=True,
            height=300
        )
        
    with d_col2:
        st.markdown("### Portfolio Status Breakdown")
        fig_drill_bd_pie = px.pie(
            bd_detail,
            names="active_status",
            color="active_status",
            color_discrete_map={
                "Active": "#10b981",
                "Yellow": "#f59e0b",
                "Orange": "#f97316",
                "Red": "#ef4444"
            },
            hole=0.45,
            title=f"Health Breakdown for {drill_bd}"
        )
        fig_drill_bd_pie.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Outfit"),
            height=280,
            margin=dict(l=10, r=10, t=30, b=10)
        )
        st.plotly_chart(fig_drill_bd_pie, use_container_width=True)
else:
    st.warning("No data matches the selected filters.")