from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.data_loader import LoadedData, _DOCS_ROOT, _kes, csv_fingerprint, load  # type: ignore[attr-defined]
from src.tools.export import build_report_html

# ─────────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Kenya Levy Audit Dashboard",
    page_icon="🇰🇪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# Global CSS — professional audit dashboard theme
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .main .block-container { padding-top: 1rem; padding-bottom: 3rem; }

  /* Hero */
  .hero {
    background: linear-gradient(135deg, #1e3a5f 0%, #0f2a47 55%, #070d1b 100%);
    color: #ffffff; padding: 20px 28px; border-radius: 14px;
    margin-bottom: 18px; border-left: 6px solid #3b82f6;
  }
  .hero h1 { margin: 0; font-size: 1.5rem; font-weight: 700; letter-spacing: -.4px; color: #ffffff; }
  .hero p  { margin: 5px 0 0; opacity: .82; font-size: .87rem; color: #e2e8f0; }

  /* Narrative insight banner */
  .narrative {
    background: #f1f5f9; border: 1px solid #cbd5e1; border-left: 4px solid #1e3a5f;
    border-radius: 10px; padding: 14px 20px; margin-bottom: 16px;
    font-size: .93rem; line-height: 1.65; color: #000000;
  }
  .narrative strong { color: #000000; }

  /* Metric cards */
  [data-testid="stMetric"] {
    background: #ffffff; border: 1px solid #cbd5e1; border-radius: 12px;
    padding: 14px 18px; box-shadow: 0 1px 4px rgba(0,0,0,.08);
  }
  [data-testid="stMetricLabel"] > div { color: #000000 !important; font-size: .8rem; font-weight: 600; }
  [data-testid="stMetricValue"] { font-size: 1.4rem; font-weight: 700; color: #000000 !important; }
  [data-testid="stMetricDelta"] { font-size: .82rem; }

  /* Section labels */
  .section-label {
    font-size: .76rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: .09em; color: #1e3a5f; margin: 22px 0 6px;
    border-left: 3px solid #3b82f6; padding-left: 8px;
  }

  /* Anomaly flag */
  .flag-high { color: #dc2626; font-weight: 700; }

  /* Scorecard table */
  .scorecard-cell-high   { background: #fef2f2; color: #991b1b; font-weight: 600; }
  .scorecard-cell-medium { background: #fefce8; color: #854d0e; }
  .scorecard-cell-low    { background: #f0fdf4; color: #166534; }

  /* Selected value in closed selectbox / multiselect — cover the element and every descendant */
  .stSelectbox div[data-baseweb="select"],
  .stSelectbox div[data-baseweb="select"] *,
  .stSelectbox div[data-baseweb="select"] div,
  .stSelectbox div[data-baseweb="select"] span,
  .stSelectbox div[data-baseweb="select"] p { color: #111111 !important; font-weight: 500 !important; }

  .stMultiSelect div[data-baseweb="select"],
  .stMultiSelect div[data-baseweb="select"] *,
  .stMultiSelect div[data-baseweb="select"] div,
  .stMultiSelect div[data-baseweb="select"] span,
  .stMultiSelect div[data-baseweb="select"] p { color: #111111 !important; font-weight: 500 !important; }
  /* Dropdown popup list (rendered in a portal, outside sidebar) */
  [data-baseweb="popover"] [role="option"],
  [data-baseweb="popover"] [role="option"] span,
  [data-baseweb="menu"] [role="option"],
  [data-baseweb="menu"] [role="option"] span { color: #000000 !important; background: #ffffff; }
  [data-baseweb="popover"] [role="option"]:hover,
  [data-baseweb="menu"] [role="option"]:hover { background: #e2e8f0 !important; }
  [data-baseweb="popover"] [role="option"][aria-selected="true"],
  [data-baseweb="popover"] [role="option"][aria-selected="true"] span,
  [data-baseweb="menu"] [role="option"][aria-selected="true"],
  [data-baseweb="menu"] [role="option"][aria-selected="true"] span { color: #000000 !important; background: #dbeafe !important; }

  /* Main area — ensure light backgrounds on dataframes */
  [data-testid="stDataFrame"] { background: #ffffff; }

  /* Info/warning boxes */
  [data-testid="stAlert"] { color: #000000 !important; }

  /* Expander header + content in main area */
  [data-testid="stExpander"] summary span { color: #000000 !important; }
  [data-testid="stExpander"] .streamlit-expanderContent,
  [data-testid="stExpander"] .streamlit-expanderContent p,
  [data-testid="stExpander"] .streamlit-expanderContent li { color: #000000 !important; }

  /* Sidebar — dark navy */
  [data-testid="stSidebar"] { background: #0f172a !important; }
  [data-testid="stSidebar"] * { color: #94a3b8 !important; }
  [data-testid="stSidebar"] h2,
  [data-testid="stSidebar"] h3 { color: #e2e8f0 !important; }
  [data-testid="stSidebar"] label { color: #cbd5e1 !important; }
  [data-testid="stSidebar"] .stMarkdown p,
  [data-testid="stSidebar"] .stCaption { color: #94a3b8 !important; }
  [data-testid="stSidebar"] [data-testid="stSelectbox"] span,
  [data-testid="stSidebar"] [data-testid="stSelectbox"] div { color: #e2e8f0 !important; }
  /* Expander inside sidebar — header + all content */
  [data-testid="stSidebar"] [data-testid="stExpander"] summary span { color: #94a3b8 !important; }
  [data-testid="stSidebar"] [data-testid="stExpander"] .streamlit-expanderContent,
  [data-testid="stSidebar"] [data-testid="stExpander"] .streamlit-expanderContent p,
  [data-testid="stSidebar"] [data-testid="stExpander"] .streamlit-expanderContent li,
  [data-testid="stSidebar"] [data-testid="stExpander"] .streamlit-expanderContent strong { color: #94a3b8 !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Data load (cached) — fingerprint busts cache when new CSVs are added
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Loading CSV data …")
def _load(fingerprint: str) -> LoadedData:
    return load()


data = _load(csv_fingerprint())
df_fin: pd.DataFrame = data["df_financial"]
df_pac: pd.DataFrame = data["df_pac"]

# Metric sets used across sections
_TARGET_M   = {"Target_Revenue", "Revised_Target", "Target_Budget",
               "KRB_Allocated", "NHFC_Levy_Due", "Expected_PDL", "RDL_Due", "IFMIS_Committed"}
_ACTUAL_M   = {"Actual_Collected", "Actual_Spend", "Expected_Revenue",
               "KRA_Remitted", "KRB_Disbursed", "KRB_Utilised",
               "NHFC_Remitted", "Actual_PDL", "RDL_Paid", "IFMIS_Actual"}
_OAG_RISK_M = {"Variance", "Loss", "Revenue_Leakage", "Arrears", "Liability",
               "Interest_Accrued", "Loan_Principal",
               "KRA_Variance", "KPA_Variance"}

# Source-specific metric groups for scorecard cross-referencing
_KRA_M    = {"KRA_Declared", "KRA_Remitted", "KRA_Variance"}
_KRB_M    = {"KRB_Allocated", "KRB_Disbursed", "KRB_Utilised"}
_NHFC_M   = {"NHFC_Levy_Due", "NHFC_Remitted", "Arrears"}
_EPRA_M   = {"Expected_PDL", "Actual_PDL"}
_KPA_M    = {"RDL_Due", "RDL_Paid", "KPA_Variance"}
_IFMIS_M  = {"IFMIS_Committed", "IFMIS_Actual"}


# ─────────────────────────────────────────────────────────────────────────────
# Cascading sidebar filters
# ─────────────────────────────────────────────────────────────────────────────
def _unique_sorted(series: pd.Series, exclude: set[str] | None = None) -> list[str]:
    exc = exclude or {"Unknown", "N/A", ""}
    return sorted(v for v in series.dropna().unique() if v not in exc)


with st.sidebar:
    st.markdown("## 🇰🇪 Levy Audit")
    st.caption("Kenya Fiscal Transparency Dashboard")
    st.divider()

    # 1 ── Fiscal Year
    year_opts = ["All years"] + data["years"]
    sel_year = st.selectbox("📅 Fiscal Year", year_opts)
    _f1 = df_fin if sel_year == "All years" else df_fin[df_fin["Year"] == sel_year]

    # 2 ── Data Source
    src_available = _unique_sorted(_f1["Source"])
    sel_source = st.selectbox("📂 Data Source", ["All sources"] + src_available)
    _f2 = _f1 if sel_source == "All sources" else _f1[_f1["Source"] == sel_source]

    # 3 ── Levy Type
    levy_available = _unique_sorted(_f2["Levy_Type"])
    sel_levy = st.selectbox("⚖️ Levy Type", ["All levies"] + levy_available)
    _f3 = _f2 if sel_levy == "All levies" else _f2[_f2["Levy_Type"] == sel_levy]

    # 4 ── Entity / Ministry
    entity_available = _unique_sorted(_f3["Entity_Name"])
    sel_entity = st.selectbox("🏛️ Entity / Ministry", ["All entities"] + entity_available)
    _f4 = _f3 if sel_entity == "All entities" else _f3[_f3["Entity_Name"] == sel_entity]

    # 5 ── Risk Factor
    risk_available = _unique_sorted(_f4["Risk_Factor"])
    sel_risk = st.selectbox("⚠️ Risk Factor", ["All risks"] + risk_available)

    st.divider()
    st.markdown("**Dataset**")
    st.caption(f"{len(df_fin):,} rows · {len(data['years'])} fiscal years")
    st.caption(f"Sources: {', '.join(data['sources'])}")
    with st.expander("📁 Loaded CSV files"):
        for p in sorted(_DOCS_ROOT.rglob("*.csv")):
            st.caption(p.name)
    st.divider()

    with st.expander("📖 Glossary"):
        st.markdown("""
**OAG** — Office of the Auditor General; Kenya's supreme audit institution.

**QEBR** — Quarterly Expenditure & Budget Review; National Treasury performance reports.

**KRA** — Kenya Revenue Authority; administers and collects all national levies. KRA_Declared vs KRA_Remitted gaps indicate non-compliance.

**KRB** — Kenya Roads Board; manages allocation and disbursement of the Road Maintenance Levy Fund (RMLF / Fuel Levy) to road agencies (KeNHA, KeRRA, KURA).

**NHFC** — National Housing Finance Corporation / Affordable Housing Board; receives and tracks the 1.5% Affordable Housing Levy remitted by employers.

**EPRA** — Energy & Petroleum Regulatory Authority; tracks petroleum import and sale volumes used to compute PDL and Fuel Levy bases. Gaps between Expected_PDL and Actual_PDL indicate under-declaration.

**KPA** — Kenya Ports Authority; provides import declaration data for the Railway Development Levy (RDL), assessed at 1.5% of CIF import value.

**PAC** — Public Accounts Committee; Parliament's committee that reviews OAG findings and issues recommendations. Implementation_Status shows government follow-through.

**IFMIS** — Integrated Financial Management Information System; National Treasury's commitment and expenditure ledger enabling project-level absorption tracking.

**Levy** — A statutory charge collected from specific sectors by law.

**Risk Exposure** — Total monetary value of audit-flagged risks: losses, irregularities, and funds not properly accounted for.

**Shortfall** — Gap between budgeted and actually collected amounts.

**Arrears** — Overdue levy payments not yet paid.

**Revenue Leakage** — Funds that should have been collected but were lost or diverted.

**Absorption Rate** — Percentage of an allocated budget actually spent (100% = fully used).
        """)

    st.divider()
    export_placeholder = st.empty()


# ─────────────────────────────────────────────────────────────────────────────
# Apply filters
# ─────────────────────────────────────────────────────────────────────────────
def _apply(df: pd.DataFrame, *, skip_source: bool = False,
           skip_risk: bool = False) -> pd.DataFrame:
    if sel_year   != "All years":    df = df[df["Year"]        == sel_year]
    if not skip_source and sel_source != "All sources":
                                     df = df[df["Source"]      == sel_source]
    if sel_levy   != "All levies":   df = df[df["Levy_Type"]   == sel_levy]
    if sel_entity != "All entities": df = df[df["Entity_Name"] == sel_entity]
    if not skip_risk and sel_risk != "All risks":
                                     df = df[df["Risk_Factor"] == sel_risk]
    return df


fin        = _apply(df_fin)
oag_fin    = _apply(df_fin[df_fin["Source"] == "OAG Audit"], skip_source=True)
score_base = _apply(df_fin, skip_source=True, skip_risk=True)


# ─────────────────────────────────────────────────────────────────────────────
# KPI computations
# ─────────────────────────────────────────────────────────────────────────────
total_target  = fin[fin["Metric"].isin(_TARGET_M)]["Value_Ksh_num"].sum()
total_actual  = fin[fin["Metric"].isin(_ACTUAL_M)]["Value_Ksh_num"].sum()
shortfall     = total_target - total_actual
pct_collected = (total_actual / total_target * 100) if total_target > 0 else 0.0
oag_risk_amt  = oag_fin[oag_fin["Metric"].isin(_OAG_RISK_M)]["Value_Ksh_num"].sum()
oag_row_count = len(oag_fin)

active = [v for v in [sel_year, sel_source, sel_levy, sel_entity, sel_risk]
          if not v.startswith("All ")]
filter_desc = " · ".join(active) if active else "All data"


def _md_bold(text: str) -> str:
    """Convert **markdown bold** to <strong> so it renders inside raw HTML divs."""
    return re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)


# ─────────────────────────────────────────────────────────────────────────────
# Narrative builder — template-based, no LLM required.
# Every sentence is derived from already-computed KPI values and conditional
# thresholds. Updates automatically with every filter change.
# Row-level insight (from a "Finding_Summary" CSV column written by an LLM
# during the cleaning step) is surfaced separately in the OAG table below.
# ─────────────────────────────────────────────────────────────────────────────
def _build_narrative() -> str:
    parts: list[str] = []

    ctx = f"In **{sel_year}**" if sel_year != "All years" else "Across all fiscal years"
    levy_ctx   = f" for **{sel_levy}**"   if sel_levy   != "All levies"   else ""
    entity_ctx = f" (**{sel_entity}**)"   if sel_entity != "All entities" else ""

    if total_target > 0 and total_actual > 0:
        if pct_collected >= 100:
            verdict = (f"exceeded its revenue target — collecting **{_kes(total_actual)}** "
                       f"against a **{_kes(total_target)}** budget")
        elif pct_collected >= 80:
            verdict = (f"collected **{pct_collected:.1f}%** of its **{_kes(total_target)}** "
                       f"target (**{_kes(total_actual)}** received)")
        else:
            verdict = (f"significantly under-collected — only **{pct_collected:.1f}%** of "
                       f"the **{_kes(total_target)}** target (**{_kes(total_actual)}** received)")
        parts.append(f"{ctx}{levy_ctx}{entity_ctx}, Kenya's levy system {verdict}.")
        if shortfall > 0:
            parts.append(
                f"The **{_kes(shortfall)} shortfall** represents public revenue that was "
                f"budgeted but not collected — funds that would otherwise support roads, "
                f"housing, and public services."
            )
    elif total_target > 0:
        parts.append(
            f"{ctx}{levy_ctx}{entity_ctx}, the levy budget was set at **{_kes(total_target)}** "
            f"— no actual collection figures are available for this selection."
        )
    elif total_actual > 0:
        parts.append(
            f"{ctx}{levy_ctx}{entity_ctx}, **{_kes(total_actual)}** was collected or spent "
            f"— no budget target is recorded for this selection."
        )

    if oag_risk_amt > 0:
        entity_count = oag_fin["Entity_Name"].nunique() if not oag_fin.empty else 0
        entity_str = f" across **{entity_count} entities**" if entity_count > 1 else ""
        parts.append(
            f"The OAG flagged **{_kes(oag_risk_amt)}** in risk exposure{entity_str}, "
            f"covering losses, arrears, and revenue leakage identified during audit."
        )

    if not parts:
        parts.append(
            "No financial data matches the current filter selection. "
            "Try broadening your Fiscal Year or Levy Type filters."
        )

    return " ".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# Page header
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="hero">
      <h1>🇰🇪 Kenya Levy Audit Dashboard</h1>
      <p>Fuel Levy (RMLF) &nbsp;·&nbsp; Affordable Housing Levy &nbsp;·&nbsp;
         Petroleum Development Levy &nbsp;·&nbsp; Railway Development Levy<br/>
         OAG Audit &nbsp;·&nbsp; QEBR &nbsp;·&nbsp; Budget Estimates &nbsp;·&nbsp;
         KRA Collections &nbsp;·&nbsp; KRB Disbursements &nbsp;·&nbsp;
         NHFC Housing Levy &nbsp;·&nbsp; EPRA Volumes &nbsp;·&nbsp;
         KPA/RDL Customs &nbsp;·&nbsp; PAC Reports &nbsp;·&nbsp; IFMIS</p>
    </div>
    """,
    unsafe_allow_html=True,
)
st.caption(
    f"**Filter:** {filter_desc} &nbsp;·&nbsp; "
    f"{len(fin):,} rows matched &nbsp;·&nbsp; {oag_row_count:,} OAG rows"
)

# Narrative insight banner
st.markdown(
    f'<div class="narrative">{_md_bold(_build_narrative())}</div>',
    unsafe_allow_html=True,
)


# ─────────────────────────────────────────────────────────────────────────────
# KPI row
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">Key Metrics</div>', unsafe_allow_html=True)

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric(
    "Target Revenue",
    _kes(total_target) if total_target else "n/a",
    help="The total levy collection target set by National Treasury in the budget.",
)
k2.metric(
    "Actual Collected / Spent",
    _kes(total_actual) if total_actual else "n/a",
    delta=f"-{_kes(shortfall)}" if shortfall > 0 else (f"+{_kes(abs(shortfall))}" if shortfall < 0 else None),
    delta_color="inverse" if shortfall > 0 else "normal",
    help="Actual amounts collected or disbursed per QEBR reports.",
)
k3.metric(
    "Collection Rate",
    f"{pct_collected:.1f}%" if total_target > 0 else "n/a",
    delta=f"{pct_collected - 100:.1f}pp" if total_target > 0 else None,
    delta_color="inverse" if pct_collected < 100 else "normal",
    help="Percentage of the target actually collected. 100% means the budget target was fully met.",
)
k4.metric(
    "OAG Risk Exposure",
    _kes(oag_risk_amt) if oag_risk_amt else "n/a",
    help="Total monetary value of risks, losses, arrears, and irregularities flagged by the Office of the Auditor General.",
)
k5.metric(
    "OAG Audit Rows",
    f"{oag_row_count:,}",
    help="Number of individual audit findings in the OAG dataset for the current filter selection.",
)

st.divider()


# ─────────────────────────────────────────────────────────────────────────────
# Section 1 — Revenue performance
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">Revenue Performance by Levy Type</div>',
            unsafe_allow_html=True)

col_bar, col_src = st.columns([3, 2])

with col_bar:
    t_by_levy = (
        fin[fin["Metric"].isin(_TARGET_M)]
        .groupby("Levy_Type", as_index=False)["Value_Ksh_num"].sum()
        .rename(columns={"Value_Ksh_num": "Target"})
    )
    a_by_levy = (
        fin[fin["Metric"].isin(_ACTUAL_M)]
        .groupby("Levy_Type", as_index=False)["Value_Ksh_num"].sum()
        .rename(columns={"Value_Ksh_num": "Actual"})
    )
    rev_df = (
        t_by_levy.merge(a_by_levy, on="Levy_Type", how="outer").fillna(0)
        .query("Levy_Type != 'Unknown'")
        .sort_values("Target", ascending=False)
    )
    if rev_df.empty:
        st.info("No target/actual data for current filters.")
    else:
        rev_long = rev_df.melt(
            id_vars="Levy_Type", value_vars=["Target", "Actual"],
            var_name="Category", value_name="KES",
        )
        fig_rev = px.bar(
            rev_long, x="Levy_Type", y="KES", color="Category", barmode="group",
            color_discrete_map={"Target": "#1e3a5f", "Actual": "#0284c7"},
            title="Target vs Actual Revenue by Levy Type",
            labels={"KES": "KES", "Levy_Type": "Levy"},
        )
        fig_rev.update_layout(height=380, margin=dict(l=10, r=10, t=48, b=10),
                               paper_bgcolor="white", plot_bgcolor="white",
                               legend=dict(orientation="h", yanchor="bottom", y=1.02, x=1, xanchor="right"))
        fig_rev.update_yaxes(gridcolor="#e2e8f0")
        fig_rev.update_xaxes(gridcolor="#e2e8f0", tickangle=-15)
        st.plotly_chart(fig_rev, width='stretch', key="fig_rev")
        st.session_state["fig_rev"] = fig_rev

with col_src:
    src_totals = (
        fin.groupby("Source")["Value_Ksh_num"].sum()
        .reset_index().rename(columns={"Value_Ksh_num": "Total_KES"})
    )
    if src_totals.empty or src_totals["Total_KES"].sum() == 0:
        st.info("No source distribution data.")
    else:
        fig_src = px.pie(
            src_totals, values="Total_KES", names="Source",
            title="Data Distribution by Source",
            hole=0.42,
            color_discrete_map={
                "Budget Estimates": "#1e3a5f",
                "OAG Audit":        "#dc2626",
                "QEBR":             "#0284c7",
            },
        )
        fig_src.update_traces(textposition="inside", textinfo="percent+label", textfont_size=12)
        fig_src.update_layout(height=380, margin=dict(l=10, r=10, t=48, b=10),
                               paper_bgcolor="white", showlegend=False)
        st.plotly_chart(fig_src, width='stretch', key="fig_src")
        st.session_state["fig_src"] = fig_src

st.divider()


# ─────────────────────────────────────────────────────────────────────────────
# Section 2 — Year-on-year trend (only shown when multiple fiscal years loaded)
# ─────────────────────────────────────────────────────────────────────────────
if len(data["years"]) > 1:
    st.markdown('<div class="section-label">Year-on-Year Trend</div>', unsafe_allow_html=True)

    yoy_t = (df_fin[df_fin["Metric"].isin(_TARGET_M)]
             .groupby("Year")["Value_Ksh_num"].sum().rename("Target"))
    yoy_a = (df_fin[df_fin["Metric"].isin(_ACTUAL_M)]
             .groupby("Year")["Value_Ksh_num"].sum().rename("Actual"))
    yoy = pd.concat([yoy_t, yoy_a], axis=1).reset_index()
    yoy_long = yoy.melt("Year", var_name="Category", value_name="KES").dropna(subset=["KES"])

    if not yoy_long.empty:
        fig_yoy = px.line(
            yoy_long, x="Year", y="KES", color="Category", markers=True,
            color_discrete_map={"Target": "#1e3a5f", "Actual": "#0284c7"},
            title="Revenue Target vs Actual — All Fiscal Years",
            labels={"KES": "KES", "Year": "Fiscal Year"},
        )
        fig_yoy.update_layout(height=320, margin=dict(l=10, r=10, t=48, b=10),
                               paper_bgcolor="white", plot_bgcolor="white",
                               legend=dict(orientation="h", yanchor="bottom", y=1.02, x=1, xanchor="right"))
        fig_yoy.update_yaxes(gridcolor="#e2e8f0")
        fig_yoy.update_xaxes(gridcolor="#e2e8f0")
        st.plotly_chart(fig_yoy, width='stretch', key="fig_yoy")

    st.divider()


# ─────────────────────────────────────────────────────────────────────────────
# Section 3 — Budget absorption & risk factors
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">Budget Absorption &amp; Risk Exposure</div>',
            unsafe_allow_html=True)

col_abs, col_risk = st.columns([2, 3])

with col_abs:
    budget_df = fin[fin["Metric"].isin({"Target_Budget", "Actual_Spend"})].copy()
    if budget_df.empty:
        st.info("No budget vs actual data for current filters.")
    else:
        bp = (
            budget_df.groupby(["Entity_Name", "Metric"])["Value_Ksh_num"]
            .sum().unstack(fill_value=0).reset_index()
        )
        if "Target_Budget" in bp.columns and "Actual_Spend" in bp.columns:
            bp["Absorption_%"] = (bp["Actual_Spend"] / bp["Target_Budget"] * 100).round(1)
            bp = bp[bp["Target_Budget"] > 0].sort_values("Absorption_%").head(15)
            fig_abs = px.bar(
                bp, x="Absorption_%", y="Entity_Name", orientation="h",
                color="Absorption_%",
                color_continuous_scale=["#dc2626", "#fbbf24", "#0284c7"],
                range_color=[0, 120],
                title="Budget Absorption Rate by Entity (%)",
                labels={"Absorption_%": "Absorption %", "Entity_Name": "Entity"},
            )
            fig_abs.add_vline(x=100, line_dash="dash", line_color="#0284c7", opacity=0.5)
            fig_abs.update_layout(height=420, margin=dict(l=10, r=10, t=48, b=10),
                                   paper_bgcolor="white", plot_bgcolor="white",
                                   coloraxis_showscale=False)
            fig_abs.update_xaxes(gridcolor="#e2e8f0", range=[0, 130])
            st.plotly_chart(fig_abs, width='stretch', key="fig_abs")
            st.session_state["fig_abs"] = fig_abs
        else:
            st.info("Need both Target_Budget and Actual_Spend rows to compute absorption.")

with col_risk:
    risk_df = (
        fin[~fin["Risk_Factor"].isin({"Unknown", "N/A"})]
        .groupby("Risk_Factor")["Value_Ksh_num"].sum()
        .reset_index().rename(columns={"Value_Ksh_num": "KES"})
        .sort_values("KES", ascending=False).head(14)
    )
    if risk_df.empty:
        st.info("No risk factor data for current filters.")
    else:
        fig_risk = px.bar(
            risk_df, x="KES", y="Risk_Factor", orientation="h",
            color="KES", color_continuous_scale=["#f1f5f9", "#dc2626"],
            title="Top Risk Factors by Associated Amount (KES)",
            labels={"KES": "KES", "Risk_Factor": "Risk Factor"},
        )
        fig_risk.update_layout(height=420, margin=dict(l=10, r=10, t=48, b=10),
                                paper_bgcolor="white", plot_bgcolor="white",
                                coloraxis_showscale=False)
        fig_risk.update_xaxes(gridcolor="#e2e8f0")
        st.plotly_chart(fig_risk, width='stretch', key="fig_risk")
        st.session_state["fig_risk"] = fig_risk

st.divider()


# ─────────────────────────────────────────────────────────────────────────────
# Section 4 — OAG Risk Heatmap (entity × levy type)
# ─────────────────────────────────────────────────────────────────────────────
heat_data = (
    oag_fin[oag_fin["Metric"].isin(_OAG_RISK_M)]
    .groupby(["Entity_Name", "Levy_Type"])["Value_Ksh_num"]
    .sum().reset_index()
)
if not heat_data.empty:
    st.markdown('<div class="section-label">OAG Risk Heatmap — Entity × Levy Type</div>',
                unsafe_allow_html=True)
    st.caption(
        "Colour intensity shows the total OAG-flagged risk amount per entity and levy. "
        "Darker red = higher risk. Blank = no audit findings for that combination."
    )
    pivot = (
        heat_data.pivot(index="Entity_Name", columns="Levy_Type", values="Value_Ksh_num")
        .fillna(0)
    )
    # Limit to top-20 entities by total risk to keep the chart readable
    top_entities = heat_data.groupby("Entity_Name")["Value_Ksh_num"].sum().nlargest(20).index
    pivot = pivot.loc[pivot.index.isin(top_entities)]

    fig_heat = px.imshow(
        pivot,
        color_continuous_scale=["#f8fafc", "#fef2f2", "#dc2626"],
        aspect="auto",
        title="OAG Risk Amount by Entity & Levy (KES)",
        labels={"color": "KES"},
    )
    fig_heat.update_layout(
        height=max(300, len(pivot) * 28 + 80),
        margin=dict(l=10, r=10, t=48, b=10),
        paper_bgcolor="white",
        coloraxis_colorbar=dict(title="KES", tickformat=".2s"),
    )
    fig_heat.update_xaxes(tickangle=-20)
    st.plotly_chart(fig_heat, width='stretch', key="fig_heat")
    st.divider()


# ─────────────────────────────────────────────────────────────────────────────
# Section 5 — Cross-Source Levy Scorecard
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">Cross-Source Levy Scorecard</div>',
            unsafe_allow_html=True)
st.caption(
    "Correlates Budget Estimates (targets), QEBR (budget performance), and OAG Audit "
    "findings on the same canonical levy — Year and Levy/Entity filters applied, "
    "Source filter bypassed so all three perspectives always show."
)

_SCORE_METRICS: dict[str, set[str]] = {
    "Budget Estimates":   {"Target_Revenue", "Revised_Target", "Target_Budget"},
    "QEBR":              {"Actual_Collected", "Actual_Spend", "Expected_Revenue"},
    "OAG Audit":         {"Variance", "Loss", "Revenue_Leakage", "Arrears", "Liability",
                          "Interest_Accrued", "Loan_Principal"},
    "KRA Collection":    _KRA_M,
    "KRB Disbursement":  _KRB_M,
    "NHFC Housing Levy": _NHFC_M,
    "EPRA Volumes":      _EPRA_M,
    "KPA/RDL":           _KPA_M,
    "IFMIS":             _IFMIS_M,
}

score_parts: list[pd.DataFrame] = []
for src_name in sorted(score_base["Source"].unique()):
    chunk = score_base[score_base["Source"] == src_name]
    if src_name in _SCORE_METRICS:
        chunk = chunk[chunk["Metric"].isin(_SCORE_METRICS[src_name])]
    else:
        # Unknown source: include all numeric rows except bare percentages
        chunk = chunk[chunk["Metric"] != "Percentage"]
    if chunk.empty:
        continue
    grp = chunk.groupby("Levy_Type")["Value_Ksh_num"].sum().rename(src_name)
    score_parts.append(grp)

if score_parts:
    scorecard = pd.concat(score_parts, axis=1).reset_index().rename(columns={"Levy_Type": "Levy"})
    for col in ["Budget Estimates", "QEBR", "OAG Audit"]:
        if col not in scorecard.columns:
            scorecard[col] = float("nan")

    scorecard["Target"]    = scorecard.get("Budget Estimates", pd.Series(dtype=float))
    scorecard["Actual"]    = scorecard.get("QEBR", pd.Series(dtype=float))
    scorecard["OAG Risk"]  = scorecard.get("OAG Audit", pd.Series(dtype=float))
    scorecard["Shortfall"] = scorecard["Target"] - scorecard["Actual"]
    scorecard["Collect %"] = (scorecard["Actual"] / scorecard["Target"] * 100).round(1)

    disp = scorecard[["Levy", "Budget Estimates", "QEBR", "OAG Audit", "Shortfall", "Collect %"]].copy()
    for c in ["Budget Estimates", "QEBR", "OAG Audit", "Shortfall"]:
        if c in disp.columns:
            disp[c] = disp[c].apply(lambda x: _kes(x) if pd.notna(x) else "—")
    disp["Collect %"] = disp["Collect %"].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "—")
    disp = disp.rename(columns={
        "Budget Estimates": "Budget Target",
        "QEBR": "QEBR Actual",
        "OAG Audit": "OAG Risk Amt",
        "Collect %": "Collection %",
    })

    st.dataframe(disp, width='stretch', hide_index=True, height=210)
    st.session_state["scorecard_df"] = scorecard

    score_plot = scorecard.melt(
        id_vars="Levy",
        value_vars=[c for c in ["Budget Estimates", "QEBR", "OAG Audit"] if c in scorecard.columns],
        var_name="Source", value_name="KES",
    ).dropna(subset=["KES"])
    if not score_plot.empty:
        fig_score = px.bar(
            score_plot, x="Levy", y="KES", color="Source", barmode="group",
            color_discrete_map={
                "Budget Estimates": "#1e3a5f",
                "QEBR":            "#0284c7",
                "OAG Audit":       "#dc2626",
            },
            title="Budget Estimates vs QEBR Actual vs OAG Risk by Levy",
            labels={"KES": "KES", "Levy": "Levy"},
        )
        fig_score.update_layout(
            height=360, margin=dict(l=10, r=10, t=48, b=10),
            paper_bgcolor="white", plot_bgcolor="white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=1, xanchor="right"),
        )
        fig_score.update_yaxes(gridcolor="#e2e8f0")
        fig_score.update_xaxes(gridcolor="#e2e8f0")
        st.plotly_chart(fig_score, width='stretch', key="fig_score")
        st.session_state["fig_score"] = fig_score
else:
    st.info("No scorecard data for current filters. Try broadening Year or Levy selections.")

st.divider()


# ─────────────────────────────────────────────────────────────────────────────
# Section 6 — OAG Audit Findings
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">OAG Audit Findings Detail</div>',
            unsafe_allow_html=True)

if oag_fin.empty:
    st.info("No OAG audit rows match the current Levy / Entity / Risk filters.")
else:
    # Top-10 highest-risk entities — always visible, quick orientation for citizens
    top_risk = (
        oag_fin[oag_fin["Metric"].isin(_OAG_RISK_M)]
        .groupby("Entity_Name")["Value_Ksh_num"].sum()
        .sort_values(ascending=False).head(10)
        .reset_index()
    )
    if not top_risk.empty:
        top_risk["OAG Risk"] = top_risk["Value_Ksh_num"].apply(_kes)
        top_risk["Rank"] = range(1, len(top_risk) + 1)
        top_risk = top_risk[["Rank", "Entity_Name", "OAG Risk"]].rename(
            columns={"Entity_Name": "Entity"}
        )
        st.markdown("**Top entities by OAG risk exposure**")
        st.dataframe(top_risk, width='stretch', hide_index=True, height=min(380, (len(top_risk) + 1) * 36 + 3))

    st.markdown("---")

    # Anomaly threshold: top-quartile risk amount across all OAG rows
    risk_rows = oag_fin[oag_fin["Metric"].isin(_OAG_RISK_M)]["Value_Ksh_num"].dropna()
    anomaly_threshold = risk_rows.quantile(0.75) if not risk_rows.empty else None

    # Metric type filter
    oag_metric_all = sorted(oag_fin["Metric"].dropna().unique())
    oag_metric_sel = st.multiselect(
        "Filter by Metric type (OAG section only)",
        oag_metric_all,
        default=[],
        placeholder="All metric types",
        key="oag_metric_ms",
    )
    oag_view = oag_fin[oag_fin["Metric"].isin(oag_metric_sel)] if oag_metric_sel else oag_fin

    oag_cols = [c for c in [
        "Year", "Audit_Ref", "Entity_Name", "Levy_Type", "Dimension", "Transaction_Category",
        "Project_or_Specific_Issue", "Metric", "Value_Ksh", "Risk_Factor",
        "Legal_Compliance", "Finding_Summary",   # Finding_Summary: LLM-written during CSV cleaning
    ] if c in oag_view.columns]

    oag_display = oag_view[oag_cols].copy().sort_values(
        ["Levy_Type", "Entity_Name"], na_position="last"
    ).rename(columns={"Audit_Ref": "Report Page"})

    # Anomaly flag: mark rows in the top quartile of risk amount
    if anomaly_threshold is not None and "Value_Ksh" in oag_display.columns:
        oag_display.insert(
            0, "⚠",
            oag_view["Value_Ksh_num"].apply(
                lambda v: "HIGH" if pd.notna(v) and v >= anomaly_threshold else ""
            ).values,
        )

    st.dataframe(oag_display, width='stretch', hide_index=True, height=380,
                 key="df_oag_table")
    st.session_state["df_oag_table"] = oag_display

    c_dl, c_info = st.columns([1, 3])
    with c_dl:
        st.download_button(
            "⬇ Download OAG CSV",
            data=oag_display.to_csv(index=False).encode("utf-8"),
            file_name=f"oag_findings_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )
    with c_info:
        st.caption(
            f"{len(oag_view):,} rows · "
            f"Risk exposure: {_kes(oag_view[oag_view['Metric'].isin(_OAG_RISK_M)]['Value_Ksh_num'].sum())}"
        )

st.divider()


# ─────────────────────────────────────────────────────────────────────────────
# Section 7 — PAC Committee Findings
# ─────────────────────────────────────────────────────────────────────────────
if not df_pac.empty:
    st.markdown('<div class="section-label">PAC Committee Findings</div>',
                unsafe_allow_html=True)
    st.caption(
        "Public Accounts Committee recommendations and government implementation status. "
        "Shows whether OAG findings were acted upon or ignored."
    )

    pac_view = df_pac.copy()
    if sel_year != "All years" and "Year" in pac_view.columns:
        pac_view = pac_view[pac_view["Year"] == sel_year]
    if sel_levy != "All levies" and "Levy_Type" in pac_view.columns:
        pac_view = pac_view[pac_view["Levy_Type"] == sel_levy]
    if sel_entity != "All entities" and "Entity_Name" in pac_view.columns:
        pac_view = pac_view[pac_view["Entity_Name"] == sel_entity]

    pac_cols = [c for c in [
        "Year", "PAC_Report_Ref", "Entity_Name", "Levy_Type",
        "OAG_Finding", "PAC_Recommendation", "Gov_Response",
        "Implementation_Status", "Follow_up_Year",
    ] if c in pac_view.columns]

    if pac_view.empty:
        st.info("No PAC findings match the current filters.")
    else:
        # Colour-code by implementation status
        status_counts = pac_view["Implementation_Status"].value_counts() if "Implementation_Status" in pac_view.columns else pd.Series(dtype=int)
        imp_c, not_c, part_c = st.columns(3)
        imp_c.metric("Implemented",     int(status_counts.get("Implemented", 0)))
        not_c.metric("Not Implemented", int(status_counts.get("Not Implemented", 0)))
        part_c.metric("Partially Implemented", int(status_counts.get("Partially Implemented", 0)))

        st.dataframe(pac_view[pac_cols], width='stretch', hide_index=True, height=360)
        st.download_button(
            "⬇ Download PAC CSV",
            data=pac_view[pac_cols].to_csv(index=False).encode("utf-8"),
            file_name=f"pac_findings_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )
    st.divider()


# ─────────────────────────────────────────────────────────────────────────────
# Section 8 — Full financial detail
# ─────────────────────────────────────────────────────────────────────────────
with st.expander("📋 Full Financial Data Table", expanded=False):
    if fin.empty:
        st.info("No data for current filters.")
    else:
        detail_cols = [c for c in [
            "Year", "Source", "Entity_Name", "Levy_Type", "Dimension",
            "Transaction_Category", "Metric", "Value_Ksh",
            "Risk_Factor", "Legal_Compliance",
        ] if c in fin.columns]
        fin_disp = fin[detail_cols].sort_values(["Source", "Levy_Type", "Entity_Name"],
                                                na_position="last")
        st.dataframe(fin_disp, width='stretch', hide_index=True, height=420)
        st.download_button(
            "⬇ Download Financial CSV",
            data=fin_disp.to_csv(index=False).encode("utf-8"),
            file_name=f"financial_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )

st.divider()


# ─────────────────────────────────────────────────────────────────────────────
# HTML export
# ─────────────────────────────────────────────────────────────────────────────
def _build_export() -> bytes:
    figs = {k: st.session_state[k]
            for k in ["fig_rev", "fig_src", "fig_abs", "fig_risk", "fig_score"]
            if k in st.session_state}
    sc_df  = st.session_state.get("scorecard_df")
    oag_df = st.session_state.get("df_oag_table")
    return build_report_html(
        filter_label=filter_desc,
        kpis={
            "Target Revenue":    _kes(total_target),
            "Actual Collected":  _kes(total_actual),
            "Collection Rate":   f"{pct_collected:.1f}%",
            "OAG Risk Exposure": _kes(oag_risk_amt),
            "OAG Audit Rows":    str(oag_row_count),
        },
        figures=figs,
        scorecard_df=sc_df,
        df_findings=oag_df,
    ).encode("utf-8")


export_placeholder.download_button(
    "📄 Export Dashboard (HTML)",
    data=_build_export(),
    file_name=f"levy_audit_{datetime.now().strftime('%Y%m%d_%H%M')}.html",
    mime="text/html",
    width='stretch',
    help="Self-contained HTML. Open in browser → Print → Save as PDF.",
)
