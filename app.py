import streamlit as st
import plotly.express as px
import pandas as pd
from utils import (
    load_data, 
    inject_custom_css, 
    render_metric_card, 
    get_geocoded_data, 
    calculate_churn_velocity, 
    calculate_cohort_retention, 
    export_to_excel
)

st.set_page_config(
    page_title="Subscription Command Center",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject beautiful styles
inject_custom_css()

# Load the raw dataset
df = load_data()

# Header Section
st.markdown('<div class="dashboard-title">🚍 Subscription Command Center</div>', unsafe_allow_html=True)
st.markdown('<div class="dashboard-subtitle">Monitor and manage bus subscription health, status, and activity trends in real-time.</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# Sidebar Filter Section
# ---------------------------------------------------------
st.sidebar.image("https://img.icons8.com/clouds/100/000000/bus.png", width=80)
st.sidebar.header("🎯 Filters Panel")

# Reset button in sidebar
if st.sidebar.button("🔄 Reset Filters", use_container_width=True):
    st.rerun()

st.sidebar.write("---")

# Filter inputs
selected_states = st.sidebar.multiselect(
    "🗺️ Filter by State",
    options=sorted(df["state"].dropna().unique()),
    placeholder="All States"
)

selected_bds = st.sidebar.multiselect(
    "👨‍💼 Filter by BD Name",
    options=sorted(df["bd_name"].dropna().astype(str).unique()),
    placeholder="All BDs"
)

selected_activation_types = st.sidebar.multiselect(
    "⚙️ Activation Type",
    options=sorted(df["activation_type"].dropna().unique()),
    placeholder="All Types"
)

selected_statuses = st.sidebar.multiselect(
    "❤️ Active Status",
    options=["Active", "Yellow", "Orange", "Red"],
    placeholder="All Statuses"
)

# Apply filters
filtered_df = df.copy()

if selected_states:
    filtered_df = filtered_df[filtered_df["state"].isin(selected_states)]
if selected_bds:
    filtered_df = filtered_df[filtered_df["bd_name"].isin(selected_bds)]
if selected_activation_types:
    filtered_df = filtered_df[filtered_df["activation_type"].isin(selected_activation_types)]
if selected_statuses:
    filtered_df = filtered_df[filtered_df["active_status"].isin(selected_statuses)]

# ---------------------------------------------------------
# Excel Exporter Sidebar Section
# ---------------------------------------------------------
st.sidebar.write("---")
st.sidebar.markdown("### 🗂️ Excel Exporter")
view_cols = [
    "active_status",
    "dsn_number",
    "bus_number",
    "operator_name",
    "company_name",
    "mobile",
    "state",
    "location",
    "bd_name",
    "activation_type",
    "current_wallet",
    "total_recharge",
    "recharge_count",
    "last_recharge_date",
    "dsn_created_date"
]

if len(filtered_df) > 0:
    # Prepare sheets for the Excel exporter
    risk_df = calculate_churn_velocity(filtered_df)
    risk_export = risk_df[risk_df["churn_risk_flag"]][[
        "dsn_number", "operator_name", "company_name", 
        "mobile", "state", "bd_name", "drop_rate"
    ]].copy()
    
    state_export = (
        filtered_df.groupby("state")
        .agg(
            Total_DSNs=("dsn_number", "nunique"),
            Active=("active_status", lambda x: (x == "Active").sum()),
            Yellow=("active_status", lambda x: (x == "Yellow").sum()),
            Orange=("active_status", lambda x: (x == "Orange").sum()),
            Red=("active_status", lambda x: (x == "Red").sum())
        )
        .reset_index()
    )
    
    bd_export = (
        filtered_df.groupby("bd_name")
        .agg(
            Total_DSNs=("dsn_number", "nunique"),
            Active=("active_status", lambda x: (x == "Active").sum()),
            Recovery_Load=("active_status", lambda x: x.isin(["Red", "Orange"]).sum())
        )
        .reset_index()
    )
    
    try:
        excel_data = export_to_excel(
            filtered_df[view_cols],
            risk_export,
            state_export,
            bd_export
        )
        st.sidebar.download_button(
            label="📥 Export Excel Dashboard",
            data=excel_data,
            file_name="subscription_dashboard_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    except Exception as e:
        st.sidebar.error(f"Error preparing Excel: {e}")
else:
    st.sidebar.warning("No data to export.")

# ---------------------------------------------------------
# KPI Cards Section
# ---------------------------------------------------------
col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    render_metric_card(
        title="Total DSNs",
        value=f"{filtered_df['dsn_number'].nunique():,}",
        status="Total",
        icon="📋"
    )

with col2:
    active_count = filtered_df[filtered_df["active_status"] == "Active"]["dsn_number"].nunique()
    render_metric_card(
        title="Active",
        value=f"{active_count:,}",
        status="Active",
        icon="🟢"
    )

with col3:
    yellow_count = filtered_df[filtered_df["active_status"] == "Yellow"]["dsn_number"].nunique()
    render_metric_card(
        title="Yellow",
        value=f"{yellow_count:,}",
        status="Yellow",
        icon="🟡"
    )

with col4:
    orange_count = filtered_df[filtered_df["active_status"] == "Orange"]["dsn_number"].nunique()
    render_metric_card(
        title="Orange",
        value=f"{orange_count:,}",
        status="Orange",
        icon="🟠"
    )

with col5:
    red_count = filtered_df[filtered_df["active_status"] == "Red"]["dsn_number"].nunique()
    render_metric_card(
        title="Red",
        value=f"{red_count:,}",
        status="Red",
        icon="🔴"
    )

with col6:
    missing_bus_count = filtered_df["bus_number"].isna().sum()
    render_metric_card(
        title="Missing Bus",
        value=f"{missing_bus_count:,}",
        status="Missing",
        icon="🚌"
    )

# Financial KPI cards row
st.write("")
st.markdown('<div class="section-header">💳 Financial & Wallet Overview</div>', unsafe_allow_html=True)
f_col1, f_col2, f_col3, f_col4 = st.columns(4)

with f_col1:
    total_wallet = filtered_df["current_wallet"].sum()
    status_wallet = "Active" if total_wallet >= 0 else "Red"
    render_metric_card(
        title="Net Wallet Balance",
        value=f"₹{total_wallet:,.0f}",
        status=status_wallet,
        icon="💼"
    )
    
with f_col2:
    total_debt = filtered_df[filtered_df["current_wallet"] < 0]["current_wallet"].sum()
    render_metric_card(
        title="Total Outstanding Debt",
        value=f"₹{abs(total_debt):,.0f}",
        status="Red" if total_debt < 0 else "Active",
        icon="🚨"
    )
    
with f_col3:
    total_recharges_val = filtered_df["total_recharge"].sum()
    render_metric_card(
        title="Total Recharge Revenue",
        value=f"₹{total_recharges_val:,.0f}",
        status="Total",
        icon="🪙"
    )
    
with f_col4:
    total_recharge_count_val = filtered_df["recharge_count"].sum()
    render_metric_card(
        title="Total Recharges Count",
        value=f"{int(total_recharge_count_val):,}",
        status="Total",
        icon="🔄"
    )

st.write("")

# ---------------------------------------------------------
# Multi-Tab Structure
# ---------------------------------------------------------
m_tab1, m_tab2, m_tab3, m_tab4 = st.tabs([
    "📊 Overview Analytics", 
    "🔮 Churn Risk Warnings", 
    "🗺️ GIS Operator Map", 
    "📈 Cohort Lifecycle Heatmap"
])

# ---------------------------------------------------------
# TAB 1: Overview Analytics
# ---------------------------------------------------------
with m_tab1:
    st.markdown('<div class="section-header">📊 Health Analytics & Distribution</div>', unsafe_allow_html=True)
    chart_col1, chart_col2 = st.columns([2, 3])

    with chart_col1:
        if len(filtered_df) > 0:
            fig_status = px.pie(
                filtered_df,
                names="active_status",
                hole=0.6,
                color="active_status",
                color_discrete_map={
                    "Active": "#10b981",
                    "Yellow": "#f59e0b",
                    "Orange": "#f97316",
                    "Red": "#ef4444"
                },
                title="Subscription Health Breakdown"
            )
            fig_status.update_traces(textposition='inside', textinfo='percent+label')
            fig_status.update_layout(
                margin=dict(l=20, r=20, t=40, b=20),
                showlegend=False,
                height=300,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(family="Outfit", size=12)
            )
            st.plotly_chart(fig_status, use_container_width=True)
        else:
            st.info("No data available.")

    with chart_col2:
        if len(filtered_df) > 0:
            state_status = filtered_df.groupby(["state", "active_status"]).size().reset_index(name="count")
            state_totals = filtered_df.groupby("state").size().sort_values(ascending=False).index[:10]
            state_status_top10 = state_status[state_status["state"].isin(state_totals)]
            
            fig_state = px.bar(
                state_status_top10,
                x="state",
                y="count",
                color="active_status",
                color_discrete_map={
                    "Active": "#10b981",
                    "Yellow": "#f59e0b",
                    "Orange": "#f97316",
                    "Red": "#ef4444"
                },
                category_orders={"state": list(state_totals)},
                title="Top 10 States Status Breakdown"
            )
            fig_state.update_layout(
                margin=dict(l=20, r=20, t=40, b=20),
                height=300,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(family="Outfit", size=12),
                xaxis_title=None,
                yaxis_title="DSN Count",
                legend_title=None
            )
            st.plotly_chart(fig_state, use_container_width=True)
        else:
            st.info("No data available.")

    st.markdown('<div class="section-header">🔍 Subscription Registry</div>', unsafe_allow_html=True)
    search_term = st.text_input("🔍 Quick Search by DSN, Bus Number, Operator, Mobile or BD", placeholder="Type to search...")

    final_df = filtered_df.copy()
    if search_term:
        search_term = search_term.strip().lower()
        final_df = final_df[
            final_df["dsn_number"].astype(str).str.lower().str.contains(search_term) |
            final_df["bus_number"].astype(str).str.lower().str.contains(search_term) |
            final_df["operator_name"].astype(str).str.lower().str.contains(search_term) |
            final_df["mobile"].astype(str).str.lower().str.contains(search_term) |
            final_df["bd_name"].astype(str).str.lower().str.contains(search_term) |
            final_df["company_name"].astype(str).str.lower().str.contains(search_term)
        ]

    st.markdown(f"**Showing {len(final_df):,} records** out of **{len(filtered_df):,}** filtered")

    if len(final_df) > 0:
        st.dataframe(
            final_df[view_cols],
            column_config={
                "active_status": st.column_config.TextColumn("Status"),
                "dsn_number": st.column_config.TextColumn("DSN Number"),
                "bus_number": st.column_config.TextColumn("Bus Number"),
                "mobile": st.column_config.TextColumn("Mobile"),
                "current_wallet": st.column_config.NumberColumn("Wallet Balance", format="₹%d"),
                "total_recharge": st.column_config.NumberColumn("Total Recharged", format="₹%d"),
                "recharge_count": st.column_config.NumberColumn("Recharges", format="%d"),
                "last_recharge_date": st.column_config.DateColumn("Last Recharge"),
                "dsn_created_date": st.column_config.DateColumn("Created Date"),
            },
            use_container_width=True,
            height=400
        )
    else:
        st.warning("No records matched search query.")

# ---------------------------------------------------------
# TAB 2: Churn Risk Warnings (Early Warning System)
# ---------------------------------------------------------
with m_tab2:
    st.markdown('<div class="section-header">🔮 Early Warning System (Decline Velocity)</div>', unsafe_allow_html=True)
    
    if len(filtered_df) > 0:
        churn_df = calculate_churn_velocity(filtered_df)
        risk_list = churn_df[churn_df["churn_risk_flag"]].copy()
        
        # Display small info box
        st.markdown(
            """
            <div class="info-banner">
                💡 <b>Methodology</b>: Operates by tracking week-over-week (WoW) booking velocity. 
                DSNs showing a <b>40% or greater decline</b> in bookings over the last 7 days compared to the prior 7 days 
                are flagged here. <i>(Filters out zero-activity or brand new accounts).</i>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        # Risk counters
        rc1, rc2 = st.columns(2)
        with rc1:
            st.metric("Total Operators Monitored", f"{len(filtered_df):,}")
        with rc2:
            st.metric("Decline Flags (High Churn Risk)", f"{len(risk_list):,}", delta=f"{len(risk_list)/len(filtered_df)*100:.1f}% of Active", delta_color="inverse")
            
        st.write("")
        
        if len(risk_list) > 0:
            # Sort risk list by drop rate ascending (worst drop first)
            risk_list = risk_list.sort_values("drop_rate")
            
            st.dataframe(
                risk_list[[
                    "dsn_number", "operator_name", "company_name", 
                    "mobile", "state", "bd_name", "sum_prior_7", "sum_last_7", "drop_rate"
                ]],
                column_config={
                    "dsn_number": st.column_config.TextColumn("DSN"),
                    "mobile": st.column_config.TextColumn("Mobile"),
                    "sum_prior_7": st.column_config.NumberColumn("Prior Week Sum"),
                    "sum_last_7": st.column_config.NumberColumn("Current Week Sum"),
                    "drop_rate": st.column_config.NumberColumn(
                        "Booking Velocity WoW", 
                        format="%.1f%%"
                    ),
                },
                use_container_width=True,
                height=400
            )
        else:
            st.success("🟢 No active operators currently exhibit WoW declines of 40% or more. Retention patterns are stable.")
    else:
        st.info("No data available to compute risks.")

# ---------------------------------------------------------
# TAB 3: GIS Operator Map
# ---------------------------------------------------------
with m_tab3:
    st.markdown('<div class="section-header">🗺️ Interactive GIS Geographic Density Map</div>', unsafe_allow_html=True)
    
    if len(filtered_df) > 0:
        df_geo = get_geocoded_data(filtered_df)
        
        # Draw Mapbox Scatter Plot
        fig_map = px.scatter_mapbox(
            df_geo,
            lat="latitude",
            lon="longitude",
            color="active_status",
            size=df_geo["d0"].fillna(0) + 1,  # size depends on today's bookings
            hover_name="operator_name",
            hover_data={
                "dsn_number": True,
                "company_name": True,
                "state": True,
                "active_status": True,
                "latitude": False,
                "longitude": False
            },
            color_discrete_map={
                "Active": "#10b981",
                "Yellow": "#f59e0b",
                "Orange": "#f97316",
                "Red": "#ef4444"
            },
            zoom=4.2,
            height=550
        )
        
        fig_map.update_layout(
            mapbox_style="carto-positron",
            margin=dict(l=0, r=0, t=10, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Outfit"),
            legend_title=None
        )
        
        st.plotly_chart(fig_map, use_container_width=True)
        st.info("💡 **Tips**: Marker sizes scale based on **today's ($D_0$) booking volume**. Coordinates are jittered slightly at the state center to prevent nodes overlapping.")
    else:
        st.info("No location data to display.")

# ---------------------------------------------------------
# TAB 4: Cohort Lifecycle Heatmap
# ---------------------------------------------------------
with m_tab4:
    st.markdown('<div class="section-header">📈 Cohort Retention Heatmap (Last 30 Days)</div>', unsafe_allow_html=True)
    
    if len(filtered_df) > 0:
        try:
            cohort_matrix = calculate_cohort_retention(filtered_df)
            
            if not cohort_matrix.empty:
                # Plotly Heatmap
                fig_cohort = px.imshow(
                    cohort_matrix * 100,  # Scale to percent
                    labels=dict(x="Timeline", y="Cohort Month", color="Active %"),
                    x=cohort_matrix.columns,
                    y=cohort_matrix.index,
                    color_continuous_scale="Viridis",
                    aspect="auto"
                )
                fig_cohort.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="Outfit"),
                    xaxis_title=None,
                    yaxis_title="Registration Cohort",
                    height=450,
                    margin=dict(l=20, r=20, t=40, b=20)
                )
                
                st.plotly_chart(fig_cohort, use_container_width=True)
                
                st.markdown(
                    """
                    <div class="info-banner">
                        💡 <b>How to read this heatmap</b>:
                        <ul>
                            <li><b>Y-Axis</b>: Cohorts grouped by their registration calendar month.</li>
                            <li><b>X-Axis</b>: Days prior to today (from Day -29 to Today).</li>
                            <li><b>Color</b>: The percentage of operators in that cohort who booked <b>at least 1 ticket</b> on that day. Darker bands represent periods of lower customer activity.</li>
                        </ul>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
            else:
                st.warning("No DSN registry creation dates could be found to partition cohorts.")
        except Exception as e:
            st.error(f"Error drawing cohort retention heatmap: {e}")
    else:
        st.info("No cohort data matching the selected filters.")