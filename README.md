# Kenya Levy Audit Dashboard

A CSV-driven fiscal-transparency dashboard for Kenya's statutory levies. Drop a CSV in `docs/` and it appears in the dashboard on the next page load.

## Tech stack

| Layer    | Choice          |
|----------|-----------------|
| Language | Python 3.11+    |
| UI       | Streamlit       |
| Charts   | Plotly Express  |
| Data     | pandas          |
| Export   | Standalone HTML |

## Project layout

```
levy_audit_tool/
├── app.py                  # Streamlit dashboard
├── requirements.txt
├── .streamlit/
│   └── config.toml         # Theme, light mode, and brand colours
├── docs/                   # Drop CSV files here
└── src/
    ├── data_loader.py      # CSV scanner, schema detector, DataFrame builder
    └── tools/
        └── export.py       # HTML report generator
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Adding Data

Place CSV files anywhere under `docs/`. The loader scans recursively and picks them up automatically.

### Filename conventions

| Filename pattern             | Detected year | Detected source   |
|------------------------------|---------------|-------------------|
| `oag_FY2024-2025.csv`        | `FY2024/25`   | OAG Audit         |
| `qebr_FY2024-2025.csv`       | `FY2024/25`   | QEBR              |
| `estimated_collection_*.csv` | from filename | Budget Estimates  |
| `kra_*.csv`                  | from filename | KRA Collection    |
| `krb_*.csv`                  | from filename | KRB Disbursement  |
| `nhfc_*.csv`                 | from filename | NHFC Housing Levy |
| `epra_*.csv`                 | from filename | EPRA Volumes      |
| `kpa_*.csv`                  | from filename | KPA/RDL           |
| `pac_*.csv`                  | from filename | PAC Committee     |
| `ifmis_*.csv`                | from filename | IFMIS             |

Source is detected from the filename prefix in the order above (first match wins).

### Supported schemas

Schema is detected automatically from column names.

**Financial** — requires `Levy_Type`, `Metric`, `Value_Ksh`:
```
Vote_Code, Entity_Name, Levy_Type, Dimension, Transaction_Category,
Project_or_Specific_Issue, Metric, Value_Ksh, Legal_Compliance, Risk_Factor
```
Default schema — use for OAG, QEBR, and Budget Estimate files.

**KRA remittance** — requires `Levy_Type`, `Declared_Amount`, `Remitted_Amount`

**KRB disbursement** — requires `Agency`, `Allocated_KES`, `Disbursed_KES`

**NHFC housing levy** — requires `Employer_Name`, `Levy_Due`, `Levy_Remitted`

**EPRA volumes** — requires `Expected_PDL`, `Actual_PDL`, `Imported_Litres`

**KPA/RDL** — requires `RDL_Due`, `RDL_Paid`, `CIF_Value_KES`

**IFMIS** — requires `Vote_Code`, `Committed_KES`, `Actual_KES`

**PAC committee** — requires `PAC_Report_Ref`, `OAG_Finding`, `Implementation_Status`

Any CSV that doesn't match a schema is silently skipped.

### Metric values

In the financial schema, what a row counts as depends on its `Metric` value:

| Metric values                                          | Counted as    |
|--------------------------------------------------------|---------------|
| `Target_Revenue`, `Revised_Target`, `Target_Budget`    | Budget target |
| `Actual_Collected`, `Actual_Spend`, `Expected_Revenue` | Actual        |
| `Variance`, `Loss`, `Revenue_Leakage`, `Arrears`, …    | OAG risk      |
