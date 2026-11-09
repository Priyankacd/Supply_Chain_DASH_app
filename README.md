# Supply Chain KPI Workbench

A portfolio-ready Dash application aligned to the Python Analytics Dashboard & Application Developer JD:
- Multi-page style navigation (Overview, Case Management, Audit History)
- Plotly delivery-status and root-cause visualisations
- Pandas KPI calculations and filtering
- Editable table with backend validation
- Databricks SQL Warehouse connector and Delta-table MERGE writeback
- Audit record per successful save
- Databricks Apps / Gunicorn launch configuration
- Demo mode with fictional sample data when Databricks credentials are not set

## 1. Run locally in demo mode

Python 3.10+ recommended.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:8050`.

Demo writes are held in process memory only and disappear when the app restarts. This is intentional; it is not durable storage.

## 2. Connect to Databricks SQL Warehouse

Set these environment variables in your local shell or Databricks App configuration. Never hard-code tokens in source code or commit them to Git.

- `DATABRICKS_SERVER_HOSTNAME` — workspace hostname, without `https://`
- `DATABRICKS_HTTP_PATH` — SQL Warehouse HTTP path
- `DATABRICKS_TOKEN` — personal access token or approved service principal token
- `DATABRICKS_DATA_TABLE` — trusted three-part table name, default `main.supply_chain.otd_cases`
- `DATABRICKS_AUDIT_TABLE` — trusted three-part table name, default `main.supply_chain.otd_case_audit`
- `APP_USER_NAME` — actor label recorded in audit rows

Run `sql/setup.sql` in Databricks SQL first. Ensure the identity used by the app has `USE CATALOG`, `USE SCHEMA`, `SELECT`, `MODIFY` on the data table and `MODIFY` on the audit table, with the relevant privileges on the catalog/schema. Use your organization's approved secret mechanism for tokens.

## 3. Deploy to Databricks Apps

1. Upload this project to a Git repository or your Databricks workspace.
2. Create a Databricks App and link/select this source.
3. Confirm `app.yaml` uses the correct table names for your catalog/schema.
4. Add connection values as app environment variables / secrets in the Databricks Apps configuration. Do not put the token in `app.yaml`.
5. Deploy, open the app, and test read, edit, writeback, and audit flows using a non-production table.
6. Review the app logs if the deployment fails.

The app launch command is configured in `app.yaml` using Gunicorn and the Dash Flask server (`app:server`).

## 4. Expected table contract

The configured data table should expose these columns:
`CASE_ID, PLANT, CUSTOMER, PART_NUMBER, PROMISED_DATE, SHIP_DATE, ORDER_QTY, ROOT_CAUSE, ACTION_OWNER, STATUS, COMMENTS`

The audit table should expose:
`CASE_ID, CHANGED_FIELDS, CHANGED_BY, CHANGED_AT_UTC, CHANGE_SOURCE`

The application reads at most 2,000 cases and the audit view reads at most 500 rows. Adjust for your use case.

## 5. Design / architecture

```text
Dash UI (navigation, filters, editable table)
        |
        +-- Pandas KPI / delivery-status logic
        |
        +-- Databricks SQL connector
                 |
                 +-- Delta OTD case table (SELECT / MERGE)
                 +-- Delta audit table (INSERT)
```

## 6. Production hardening before real business use

This is an interview/portfolio starter, not a certified production system. Before production:
- Replace `APP_USER_NAME` with authenticated identity from your approved identity provider; a static label is not user-level authentication.
- Restrict editable columns server-side and verify the selected row is authorized for the user.
- Use a service principal or approved OAuth flow if required by policy; rotate secrets and least-privilege grants.
- Add transaction/compensation handling for data-write and audit-write failures, plus robust concurrency/version checks.
- Confirm Databricks SQL connector parameter behaviour in your runtime and run integration tests against a development table.
- Add automated tests, structured logging, rate limits, and error monitoring.
- Validate KPI definitions with business stakeholders; this sample defines OTD as shipped on or before promised date.
