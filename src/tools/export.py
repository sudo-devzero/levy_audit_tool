"""Dashboard → self-contained HTML export.

build_report_html captures the current filter state, KPI values, Plotly
figures, and OAG findings table, then emits a single HTML file the user can
save and print to PDF from any browser.
"""
from __future__ import annotations

import base64
import html
from datetime import datetime
from typing import Any

import pandas as pd


# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────
_CSS = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body {
  font-family: 'Inter', -apple-system, 'Segoe UI', Roboto, sans-serif;
  color: #0f172a; background: #f4f6f8;
  margin: 0; padding: 32px 40px; line-height: 1.55;
}
.hero {
  background: linear-gradient(135deg, #1e3a5f 0%, #0f2a47 60%, #070d1b 100%);
  color: white; padding: 20px 26px; border-radius: 14px;
  margin-bottom: 24px; border-left: 6px solid #3b82f6;
}
.hero h1 { margin: 0; font-size: 1.5rem; }
.hero .meta { opacity: 0.85; font-size: 0.85rem; margin-top: 6px; }
.section-label {
  font-size: 0.75rem; font-weight: 700; text-transform: uppercase;
  letter-spacing: .08em; color: #1e3a5f; margin: 24px 0 8px 0;
}
.kpi-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 12px; margin-bottom: 24px;
}
.kpi-card {
  background: white; border: 1px solid #e2e8f0; border-radius: 12px;
  padding: 14px 16px; box-shadow: 0 1px 3px rgba(0,0,0,.06);
}
.kpi-label { font-size: 0.72rem; text-transform: uppercase; color: #64748b; margin-bottom: 4px; }
.kpi-value { font-size: 1.3rem; font-weight: 700; color: #0f172a; }
.chart-block {
  background: white; border: 1px solid #e2e8f0; border-radius: 12px;
  padding: 16px; margin-bottom: 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,.06);
}
.chart-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }
table.df { border-collapse: collapse; font-size: 0.82rem; width: 100%; }
table.df th, table.df td {
  border: 1px solid #e2e8f0; padding: 6px 10px;
  text-align: left; vertical-align: top;
}
table.df thead { background: #f1f5f9; }
table.df tbody tr:nth-child(odd) { background: #fafafa; }
code { background: #f1f5f9; padding: 1px 5px; border-radius: 4px; font-size: .85em; }
h2 { color: #1e3a5f; }
.footer { color: #94a3b8; font-size: 0.78rem; margin-top: 32px; text-align: center; }
@media print {
  body { background: white; padding: 0; }
  .hero { border-radius: 0; }
}
"""


def build_report_html(
    *,
    filter_label: str = "All data",
    kpis: dict[str, str] | None = None,
    figures: dict[str, Any] | None = None,
    scorecard_df: pd.DataFrame | None = None,
    df_findings: pd.DataFrame | None = None,
    title: str = "Kenya Levy Audit — Dashboard Export",
) -> str:
    """Render the current dashboard state into a self-contained HTML document."""
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    kpis = kpis or {}
    figures = figures or {}
    plotly_idx = [0]

    # ── KPI cards ────────────────────────────────────────────────────────────
    kpi_html = "<div class='kpi-grid'>"
    for label, value in kpis.items():
        kpi_html += (
            f"<div class='kpi-card'>"
            f"<div class='kpi-label'>{html.escape(label)}</div>"
            f"<div class='kpi-value'>{html.escape(value)}</div>"
            f"</div>"
        )
    kpi_html += "</div>"

    # ── Plotly figures ────────────────────────────────────────────────────────
    def _fig_to_html(fig: Any) -> str:
        include_js = "inline" if plotly_idx[0] == 0 else False
        plotly_idx[0] += 1
        return fig.to_html(
            include_plotlyjs=include_js,
            full_html=False,
            default_height="400px",
            config={"displayModeBar": False, "responsive": True},
        )

    # Pair charts into rows of 2
    fig_keys = list(figures.keys())
    chart_html = ""
    i = 0
    while i < len(fig_keys):
        pair = fig_keys[i : i + 2]
        chart_html += "<div class='chart-row'>"
        for k in pair:
            chart_html += f"<div class='chart-block'>{_fig_to_html(figures[k])}</div>"
        chart_html += "</div>"
        i += 2

    # ── Cross-source scorecard ────────────────────────────────────────────────
    scorecard_html = ""
    if scorecard_df is not None and not scorecard_df.empty:
        from src.data_loader import _kes

        disp_cols = [c for c in [
            "Levy", "Budget Estimates", "QEBR", "OAG Audit", "Shortfall", "Collect %",
        ] if c in scorecard_df.columns]

        def _fmt(val: Any, col: str) -> str:
            if pd.isna(val):
                return "—"
            if col in ("Budget Estimates", "QEBR", "OAG Audit", "Shortfall"):
                return _kes(float(val))
            if col == "Collect %":
                return f"{float(val):.1f}%"
            return html.escape(str(val))

        rows_html = ""
        for _, row in scorecard_df.iterrows():
            rows_html += "<tr>"
            for col in disp_cols:
                rows_html += f"<td>{_fmt(row.get(col), col)}</td>"
            rows_html += "</tr>"

        scorecard_html = (
            "<div class='section-label'>Cross-Source Levy Scorecard</div>"
            "<table class='df'><thead><tr>"
            + "".join(f"<th>{html.escape(c)}</th>" for c in disp_cols)
            + "</tr></thead><tbody>"
            + rows_html
            + "</tbody></table>"
        )

    # ── OAG findings table ───────────────────────────────────────────────────
    findings_html = ""
    if df_findings is not None and not df_findings.empty:
        findings_html = (
            f"<div class='section-label'>OAG Audit Findings ({len(df_findings):,} rows)</div>"
            + df_findings.to_html(index=False, classes="df", border=0, escape=True)
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>{html.escape(title)}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="hero">
  <h1>{html.escape(title)}</h1>
  <div class="meta">Generated {generated} &nbsp;·&nbsp; Filter: {html.escape(filter_label)}</div>
</div>

<div class="section-label">Key Metrics</div>
{kpi_html}

<div class="section-label">Charts</div>
{chart_html}

{scorecard_html}

{findings_html}

<div class="footer">
  Kenya Levy Audit Tool &nbsp;·&nbsp; Data sourced from OAG audit reports &amp; National Treasury
</div>
</body>
</html>
"""
