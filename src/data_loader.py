"""CSV data loader for the Kenya Levy Audit Tool.

Scans docs/ recursively for *.csv files, extracts fiscal year from filenames,
and returns normalised DataFrames for the dashboard.

File categorisation (by schema — checked in order):
  financial  — cols include Levy_Type + Metric + Value_Ksh   (OAG, QEBR, Budget Estimates)
  kra        — KRA remittance: Levy_Type + Declared_Amount + Remitted_Amount
  krb        — KRB disbursement: Agency + Allocated_KES + Disbursed_KES
  nhfc       — Housing levy employer: Employer_Name + Levy_Due + Levy_Remitted
  epra       — EPRA volumes: Expected_PDL + Actual_PDL + Imported_Litres
  kpa        — KPA/RDL customs: RDL_Due + RDL_Paid + CIF_Value_KES
  pac        — PAC committee: PAC_Report_Ref + OAG_Finding + Implementation_Status
  ifmis      — IFMIS commitments: Vote_Code + Committed_KES + Actual_KES
  oag        — legacy OAG schema: Audit_Issue_Title + Amount_Value
  extra_obs  — legacy extra obs: Specific_Observation + Value

Year extraction regex tries (in order):
  FY\\d{4}[-_]\\d{4}  e.g. oag_FY2024-2025.csv  -> "FY2024/25"
  FY\\d{2}[-_]\\d{2}  e.g. audit_FY23_24.csv    -> "FY23/24"
  FY\\d{4}            e.g. third_qebr_FY2025-2026.csv -> "FY2025"
  \\d{4}              e.g. report_2024.csv        -> "2024"
  fallback            current year as string
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import TypedDict

import pandas as pd

_DOCS_ROOT = Path(__file__).parent.parent / "docs"
_CURRENT_YEAR = str(datetime.now().year)

# ─── Canonical levy name map (lower-cased source → canonical display name) ──
# Maps fragmented / variant levy names (especially from QEBR) to a single
# canonical form so cross-file filters and the scorecard align correctly.
_LEVY_CANON: dict[str, str] = {
    "affordable housing (sector)":    "Affordable Housing",
    "affordable housing levy":        "Affordable Housing",
    "fuel levy (rmlf bundled)":       "Fuel Levy (RMLF)",
    "fuel levy (rmlf sector)":        "Fuel Levy (RMLF)",
    "fuel levy (rml & pdl bundled)":  "Fuel Levy (RMLF)",
    "railway levy":                   "Railway Development Levy",
    "railway development levy (rdl)": "Railway Development Levy",
    "roads infrastructure":           "Fuel Levy (RMLF)",
}


def _normalise_levy(levy: str) -> str:
    return _LEVY_CANON.get(levy.lower().strip(), levy)


# ─── Year extraction ─────────────────────────────────────────────────────────

def _extract_year(filename: str) -> str:
    # FY2024-2025 or FY2024_2025 (full 4-digit year range)
    m = re.search(r"FY(20\d{2})[-_](20\d{2})", filename, re.IGNORECASE)
    if m:
        return f"FY{m.group(1)}/{m.group(2)[2:]}"   # "FY2024/25"
    # FY23-24 or FY23_24 (2-digit year range)
    m = re.search(r"FY(\d{2})[-_](\d{2})", filename, re.IGNORECASE)
    if m:
        return f"FY{m.group(1)}/{m.group(2)}"        # "FY23/24"
    # FY2025 (single full year)
    m = re.search(r"FY(20\d{2})", filename, re.IGNORECASE)
    if m:
        return f"FY{m.group(1)}"                     # "FY2025"
    # bare calendar year
    m = re.search(r"(20\d{2})", filename)
    if m:
        return m.group(1)
    return _CURRENT_YEAR


# ─── Source detection ────────────────────────────────────────────────────────

def _detect_source(filename: str) -> str:
    name = filename.lower()
    if "oag" in name:
        return "OAG Audit"
    if "qebr" in name:
        return "QEBR"
    if "collection" in name or "estimate" in name:
        return "Budget Estimates"
    if "kra" in name:
        return "KRA Collection"
    if "krb" in name:
        return "KRB Disbursement"
    if "nhfc" in name or "housing_levy" in name:
        return "NHFC Housing Levy"
    if "epra" in name:
        return "EPRA Volumes"
    if "kpa" in name or "sgr" in name:
        return "KPA/RDL"
    if "pac" in name:
        return "PAC Committee"
    if "ifmis" in name:
        return "IFMIS"
    if "budget" in name:
        return "Budget Estimates"
    return "Other"


# ─── Schema predicates ───────────────────────────────────────────────────────

def _is_financial(cols: set[str]) -> bool:
    return {"Metric", "Value_Ksh", "Levy_Type"}.issubset(cols)

def _is_kra(cols: set[str]) -> bool:
    return {"Levy_Type", "Declared_Amount", "Remitted_Amount"}.issubset(cols)

def _is_krb(cols: set[str]) -> bool:
    return {"Agency", "Allocated_KES", "Disbursed_KES"}.issubset(cols)

def _is_nhfc(cols: set[str]) -> bool:
    return {"Employer_Name", "Levy_Due", "Levy_Remitted"}.issubset(cols)

def _is_epra(cols: set[str]) -> bool:
    return {"Expected_PDL", "Actual_PDL", "Imported_Litres"}.issubset(cols)

def _is_kpa(cols: set[str]) -> bool:
    return {"RDL_Due", "RDL_Paid", "CIF_Value_KES"}.issubset(cols)

def _is_pac(cols: set[str]) -> bool:
    return {"PAC_Report_Ref", "OAG_Finding", "Implementation_Status"}.issubset(cols)

def _is_ifmis(cols: set[str]) -> bool:
    return {"Vote_Code", "Committed_KES", "Actual_KES"}.issubset(cols)

def _is_oag(cols: set[str]) -> bool:
    return {"Audit_Issue_Title", "Amount_Value"}.issubset(cols)

def _is_extra(cols: set[str]) -> bool:
    return {"Specific_Observation", "Value"}.issubset(cols)


# ─── Public types ────────────────────────────────────────────────────────────

class LoadedData(TypedDict):
    years: list[str]
    sources: list[str]
    levy_types: list[str]
    entities: list[str]
    df_financial: pd.DataFrame
    df_pac: pd.DataFrame       # PAC committee findings (qualitative — no Value_Ksh)
    df_oag: pd.DataFrame       # legacy schema; empty when all files use financial schema
    df_extra: pd.DataFrame     # legacy schema; empty when all files use financial schema


# ─── Main loader ─────────────────────────────────────────────────────────────

def csv_fingerprint() -> str:
    """Hash of all CSV paths + mtimes so callers can bust Streamlit's cache on new files."""
    parts: list[str] = []
    for p in sorted(_DOCS_ROOT.rglob("*.csv")):
        try:
            parts.append(f"{p}:{p.stat().st_mtime}")
        except OSError:
            pass
    return hashlib.md5("|".join(parts).encode()).hexdigest()


def load() -> LoadedData:
    """Scan docs/**/*.csv and return categorised, year-tagged DataFrames."""
    financial_parts: list[pd.DataFrame] = []
    pac_parts: list[pd.DataFrame] = []
    oag_parts: list[pd.DataFrame] = []
    extra_parts: list[pd.DataFrame] = []

    for csv_path in sorted(_DOCS_ROOT.rglob("*.csv")):
        year = _extract_year(csv_path.name)
        source = _detect_source(csv_path.name)
        try:
            df = pd.read_csv(csv_path, dtype=str, on_bad_lines="skip")
        except Exception:
            try:
                df = pd.read_csv(csv_path, dtype=str, on_bad_lines="skip", engine="python")
            except Exception:
                continue
        df["_year"] = year
        df["_source"] = source
        df["_source_file"] = csv_path.name

        cols = set(df.columns)
        if _is_financial(cols):
            financial_parts.append(df)
        elif _is_kra(cols):
            financial_parts.append(_convert_kra(df, year, source))
        elif _is_krb(cols):
            financial_parts.append(_convert_krb(df, year, source))
        elif _is_nhfc(cols):
            financial_parts.append(_convert_nhfc(df, year, source))
        elif _is_epra(cols):
            financial_parts.append(_convert_epra(df, year, source))
        elif _is_kpa(cols):
            financial_parts.append(_convert_kpa(df, year, source))
        elif _is_ifmis(cols):
            financial_parts.append(_convert_ifmis(df, year, source))
        elif _is_pac(cols):
            pac_parts.append(df)
        elif _is_oag(cols):
            oag_parts.append(df)
        elif _is_extra(cols):
            extra_parts.append(df)

    df_financial = _build_financial(financial_parts)
    df_pac       = _build_pac(pac_parts)
    df_oag       = _build_oag(oag_parts)
    df_extra     = _build_extra(extra_parts)

    years = sorted(
        set(df_financial["Year"].tolist()) | set(df_oag["Year"].tolist())
    )
    if not years:
        years = [_CURRENT_YEAR]

    sources = sorted(
        v for v in df_financial["Source"].unique() if v and v != "Unknown"
    )

    levy_types = sorted(
        v for v in df_financial["Levy_Type"].unique()
        if v and v not in ("Unknown",)
    )

    entities = sorted(
        v for v in df_financial["Entity_Name"].unique()
        if v and v not in ("Unknown",)
    )

    return LoadedData(
        years=years,
        sources=sources,
        levy_types=levy_types,
        entities=entities,
        df_financial=df_financial,
        df_pac=df_pac,
        df_oag=df_oag,
        df_extra=df_extra,
    )


# ─── Numeric coercion ────────────────────────────────────────────────────────

def _coerce_numeric(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.str.replace(",", "").str.strip(), errors="coerce")


# ─── DataFrame builders ──────────────────────────────────────────────────────

def _build_financial(parts: list[pd.DataFrame]) -> pd.DataFrame:
    if not parts:
        return pd.DataFrame(columns=[
            "Year", "Source", "Entity_Name", "Levy_Type", "Dimension",
            "Transaction_Category", "Metric", "Value_Ksh", "Value_Ksh_num",
            "Legal_Compliance", "Risk_Factor",
        ])
    df = pd.concat(parts, ignore_index=True).drop_duplicates()
    df["Year"] = df["_year"]
    df["Source"] = df["_source"]
    df["Value_Ksh_num"] = _coerce_numeric(df["Value_Ksh"])

    # Normalise levy names so cross-file filters align
    df["Levy_Type"] = df["Levy_Type"].fillna("Unknown").str.strip().apply(_normalise_levy)

    # Drop rows that are pure garbage from malformed CSV narrative text:
    # (a) both Levy_Type and Metric resolved to Unknown
    # (b) Value_Ksh has no numeric content at all (non-parseable narrative text)
    df = df[~((df["Levy_Type"] == "Unknown") & (df["Metric"].fillna("Unknown") == "Unknown"))]
    df = df[df["Value_Ksh_num"].notna()]

    for col in [
        "Entity_Name", "Dimension", "Transaction_Category",
        "Metric", "Legal_Compliance", "Risk_Factor",
    ]:
        if col not in df.columns:
            df[col] = "Unknown"
        df[col] = df[col].fillna("Unknown").str.strip()

    return df.drop(columns=["_year", "_source", "_source_file"], errors="ignore")


# ─── Wide-to-long converters for new source schemas ──────────────────────────

def _melt_amounts(df: pd.DataFrame, id_vars: list[str],
                  amount_cols: list[str], metric_names: list[str],
                  year: str, source: str,
                  levy_col: str | None = None,
                  fixed_levy: str = "Unknown",
                  entity_col: str | None = None) -> pd.DataFrame:
    """Generic melt: wide amount columns → Metric/Value_Ksh rows in financial schema."""
    rows: list[dict] = []
    for _, row in df.iterrows():
        levy = row[levy_col].strip() if levy_col and levy_col in row.index else fixed_levy
        entity = row[entity_col].strip() if entity_col and entity_col in row.index else "Unknown"
        for col, metric in zip(amount_cols, metric_names):
            rows.append({
                "_year": year, "_source": source,
                "Levy_Type": levy,
                "Entity_Name": entity,
                "Metric": metric,
                "Value_Ksh": row.get(col, ""),
                "Dimension": "Unknown",
                "Transaction_Category": "Unknown",
                "Risk_Factor": "Unknown",
                "Legal_Compliance": "Unknown",
            })
    return pd.DataFrame(rows)


def _convert_kra(df: pd.DataFrame, year: str, source: str) -> pd.DataFrame:
    entity_col = "Sector" if "Sector" in df.columns else None
    return _melt_amounts(
        df, [], ["Declared_Amount", "Remitted_Amount", "Variance"],
        ["KRA_Declared", "KRA_Remitted", "KRA_Variance"],
        year, source, levy_col="Levy_Type", entity_col=entity_col,
    )


def _convert_krb(df: pd.DataFrame, year: str, source: str) -> pd.DataFrame:
    rows = _melt_amounts(
        df, [], ["Allocated_KES", "Disbursed_KES", "Utilised_KES"],
        ["KRB_Allocated", "KRB_Disbursed", "KRB_Utilised"],
        year, source, fixed_levy="Fuel Levy (RMLF)", entity_col="Agency",
    )
    if "Programme" in df.columns and not rows.empty:
        rows["Transaction_Category"] = (
            df["Programme"].fillna("Unknown").tolist() * 3
        )[:len(rows)]
    return rows


def _convert_nhfc(df: pd.DataFrame, year: str, source: str) -> pd.DataFrame:
    rows = _melt_amounts(
        df, [], ["Levy_Due", "Levy_Remitted", "Arrears"],
        ["NHFC_Levy_Due", "NHFC_Remitted", "Arrears"],
        year, source, fixed_levy="Affordable Housing", entity_col="Employer_Name",
    )
    if "Compliance_Status" in df.columns:
        n = len(df)
        rows["Risk_Factor"] = (
            df["Compliance_Status"].fillna("Unknown").tolist() * 3
        )[:len(rows)]
    return rows


def _convert_epra(df: pd.DataFrame, year: str, source: str) -> pd.DataFrame:
    return _melt_amounts(
        df, [], ["Expected_PDL", "Actual_PDL"],
        ["Expected_PDL", "Actual_PDL"],
        year, source, fixed_levy="Petroleum Development Levy", entity_col="Company",
    )


def _convert_kpa(df: pd.DataFrame, year: str, source: str) -> pd.DataFrame:
    entity_col = "Importer_PIN" if "Importer_PIN" in df.columns else None
    return _melt_amounts(
        df, [], ["RDL_Due", "RDL_Paid", "Variance"],
        ["RDL_Due", "RDL_Paid", "KPA_Variance"],
        year, source, fixed_levy="Railway Development Levy", entity_col=entity_col,
    )


def _convert_ifmis(df: pd.DataFrame, year: str, source: str) -> pd.DataFrame:
    entity_col = "Programme" if "Programme" in df.columns else None
    rows = _melt_amounts(
        df, [], ["Committed_KES", "Actual_KES"],
        ["IFMIS_Committed", "IFMIS_Actual"],
        year, source, fixed_levy="General (IFMIS)", entity_col=entity_col,
    )
    if "Project_Name" in df.columns and not rows.empty:
        rows["Transaction_Category"] = (
            df["Project_Name"].fillna("Unknown").tolist() * 2
        )[:len(rows)]
    return rows


def _build_pac(parts: list[pd.DataFrame]) -> pd.DataFrame:
    """PAC committee findings — qualitative, no Value_Ksh."""
    if not parts:
        return pd.DataFrame(columns=[
            "Year", "Source", "PAC_Report_Ref", "Entity_Name", "Levy_Type",
            "OAG_Finding", "PAC_Recommendation", "Gov_Response",
            "Implementation_Status", "Follow_up_Year",
        ])
    df = pd.concat(parts, ignore_index=True).drop_duplicates()
    df["Year"] = df["_year"]
    df["Source"] = df["_source"]
    for col in [
        "PAC_Report_Ref", "Entity_Name", "Levy_Type", "OAG_Finding",
        "PAC_Recommendation", "Gov_Response", "Implementation_Status", "Follow_up_Year",
    ]:
        if col not in df.columns:
            df[col] = "Unknown"
        df[col] = df[col].fillna("Unknown").str.strip()
    df["Levy_Type"] = df["Levy_Type"].apply(_normalise_levy)
    return df.drop(columns=["_year", "_source", "_source_file"], errors="ignore")


def _build_oag(parts: list[pd.DataFrame]) -> pd.DataFrame:
    """Legacy OAG schema (Audit_Issue_Title / Amount_Value columns)."""
    if not parts:
        return pd.DataFrame(columns=[
            "Year", "Entity_Name", "Levy_Category", "Audit_Issue_Title",
            "Amount_Value_num", "Legal_Provision_Breached", "Audit_Observation_Summary",
        ])
    df = pd.concat(parts, ignore_index=True).drop_duplicates()
    df["Year"] = df["_year"]
    df["Amount_Value_num"] = _coerce_numeric(df["Amount_Value"])

    for col in [
        "Entity_Name", "Levy_Category", "Audit_Issue_Title",
        "Legal_Provision_Breached", "Audit_Observation_Summary",
    ]:
        if col not in df.columns:
            df[col] = "Unknown"
        df[col] = df[col].fillna("Unknown").str.strip()

    return df.drop(columns=["_year", "_source", "_source_file"], errors="ignore")


def _build_extra(parts: list[pd.DataFrame]) -> pd.DataFrame:
    """Legacy extra-observations schema (Specific_Observation / Value columns)."""
    if not parts:
        return pd.DataFrame(columns=[
            "Year", "Entity_Name", "Category", "Specific_Observation",
            "Value_num", "Risk_Factor",
        ])
    df = pd.concat(parts, ignore_index=True).drop_duplicates()
    df["Year"] = df["_year"]
    df["Value_num"] = _coerce_numeric(df["Value"])

    for col in ["Entity_Name", "Category", "Specific_Observation", "Metric", "Risk_Factor"]:
        if col not in df.columns:
            df[col] = "Unknown"
        df[col] = df[col].fillna("Unknown").str.strip()

    return df.drop(columns=["_year", "_source", "_source_file"], errors="ignore")


# ─── KES formatter (shared with app) ────────────────────────────────────────

def _kes(n: float | None) -> str:
    if n is None or (isinstance(n, float) and pd.isna(n)):
        return "n/a"
    if abs(n) >= 1e12:
        return f"KES {n / 1e12:,.2f}T"
    if abs(n) >= 1e9:
        return f"KES {n / 1e9:,.2f}B"
    if abs(n) >= 1e6:
        return f"KES {n / 1e6:,.2f}M"
    return f"KES {n:,.0f}"
