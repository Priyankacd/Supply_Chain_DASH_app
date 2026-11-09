"""
Supply Chain KPI Workbench
Dash + Plotly + Pandas + Databricks SQL Connector
Runs in demo mode without credentials; set environment variables for Databricks mode.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, dash_table, dcc, html, no_update
import dash_bootstrap_components as dbc

try:
    from databricks import sql as databricks_sql
except ImportError:
    databricks_sql = None

APP_TITLE = "Supply Chain KPI Workbench"
DATA_TABLE = os.getenv("DATABRICKS_DATA_TABLE", "main.supply_chain.otd_cases")
AUDIT_TABLE = os.getenv("DATABRICKS_AUDIT_TABLE", "main.supply_chain.otd_case_audit")
USER_NAME = os.getenv("APP_USER_NAME", "demo.user")

# Deliberately fictional sample data. Do not use this data for business decisions.
DEMO_ROWS = [
    {"CASE_ID": "OTD-1001", "PLANT": "Pune", "CUSTOMER": "Northstar Auto", "PART_NUMBER": "PN-4012", "PROMISED_DATE": "2026-10-02", "SHIP_DATE": "2026-10-04", "ORDER_QTY": 120, "ROOT_CAUSE": "Capacity", "ACTION_OWNER": "A. Shah", "STATUS": "Open", "COMMENTS": "Review next production slot"},
    {"CASE_ID": "OTD-1002", "PLANT": "Chennai", "CUSTOMER": "Atlas Mobility", "PART_NUMBER": "PN-2280", "PROMISED_DATE": "2026-10-03", "SHIP_DATE": "2026-10-03", "ORDER_QTY": 80, "ROOT_CAUSE": "None", "ACTION_OWNER": "R. Iyer", "STATUS": "Closed", "COMMENTS": "Shipped on time"},
    {"CASE_ID": "OTD-1003", "PLANT": "Pune", "CUSTOMER": "Vertex Motors", "PART_NUMBER": "PN-1187", "PROMISED_DATE": "2026-10-05", "SHIP_DATE": "2026-10-08", "ORDER_QTY": 45, "ROOT_CAUSE": "Supplier", "ACTION_OWNER": "M. Joshi", "STATUS": "In Progress", "COMMENTS": "Supplier recovery plan requested"},
    {"CASE_ID": "OTD-1004", "PLANT": "Nashik", "CUSTOMER": "Northstar Auto", "PART_NUMBER": "PN-9021", "PROMISED_DATE": "2026-10-06", "SHIP_DATE": "2026-10-06", "ORDER_QTY": 210, "ROOT_CAUSE": "None", "ACTION_OWNER": "S. Patil", "STATUS": "Closed", "COMMENTS": "No action required"},
    {"CASE_ID": "OTD-1005", "PLANT": "Chennai", "CUSTOMER": "Summit Commercial", "PART_NUMBER": "PN-3310", "PROMISED_DATE": "2026-10-07", "SHIP_DATE": "2026-10-10", "ORDER_QTY": 60, "ROOT_CAUSE": "Logistics", "ACTION_OWNER": "K. Rao", "STATUS": "Open", "COMMENTS": "Carrier escalation pending"},
    {"CASE_ID": "OTD-1006", "PLANT": "Nashik", "CUSTOMER": "Atlas Mobility", "PART_NUMBER": "PN-5521", "PROMISED_DATE": "2026-10-08", "SHIP_DATE": "2026-10-07", "ORDER_QTY": 150, "ROOT_CAUSE": "None", "ACTION_OWNER": "P. Kulkarni", "STATUS": "Closed", "COMMENTS": "Early shipment"},
    {"CASE_ID": "OTD-1007", "PLANT": "Pune", "CUSTOMER": "Summit Commercial", "PART_NUMBER": "PN-7781", "PROMISED_DATE": "2026-10-09", "SHIP_DATE": None, "ORDER_QTY": 95, "ROOT_CAUSE": "Planning", "ACTION_OWNER": "A. Shah", "STATUS": "In Progress", "COMMENTS": "Reconfirm plan date"},
    {"CASE_ID": "OTD-1008", "PLANT": "Chennai", "CUSTOMER": "Vertex Motors", "PART_NUMBER": "PN-6112", "PROMISED_DATE": "2026-10-10", "SHIP_DATE": "2026-10-10", "ORDER_QTY": 35, "ROOT_CAUSE": "None", "ACTION_OWNER": "R. Iyer", "STATUS": "Closed", "COMMENTS": "Shipped on time"},
    {"CASE_ID": "OTD-1009", "PLANT": "Nashik", "CUSTOMER": "Northstar Auto", "PART_NUMBER": "PN-7750", "PROMISED_DATE": "2026-10-11", "SHIP_DATE": "2026-10-14", "ORDER_QTY": 70, "ROOT_CAUSE": "Supplier", "ACTION_OWNER": "S. Patil", "STATUS": "Open", "COMMENTS": "Alternate source under review"},
    {"CASE_ID": "OTD-1010", "PLANT": "Pune", "CUSTOMER": "Atlas Mobility", "PART_NUMBER": "PN-8890", "PROMISED_DATE": "2026-10-12", "SHIP_DATE": "2026-10-11", "ORDER_QTY": 105, "ROOT_CAUSE": "None", "ACTION_OWNER": "M. Joshi", "STATUS": "Closed", "COMMENTS": "Shipped ahead of schedule"},
]
demo_df = pd.DataFrame(DEMO_ROWS)
demo_audit: list[dict[str, Any]] = []


def databricks_configured() -> bool:
    return bool(os.getenv("DATABRICKS_SERVER_HOSTNAME") and os.getenv("DATABRICKS_HTTP_PATH") and os.getenv("DATABRICKS_TOKEN"))


def get_connection():
    if not databricks_sql:
        raise RuntimeError("databricks-sql-connector is not installed.")
    return databricks_sql.connect(
        server_hostname=os.environ["DATABRICKS_SERVER_HOSTNAME"],
        http_path=os.environ["DATABRICKS_HTTP_PATH"],
        access_token=os.environ["DATABRICKS_TOKEN"],
    )


def load_data() -> pd.DataFrame:
    if not databricks_configured():
        return demo_df.copy()
    query = f"""SELECT CASE_ID, PLANT, CUSTOMER, PART_NUMBER, PROMISED_DATE, SHIP_DATE,
                       ORDER_QTY, ROOT_CAUSE, ACTION_OWNER, STATUS, COMMENTS
                FROM {DATA_TABLE}
                ORDER BY PROMISED_DATE DESC
                LIMIT 2000"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
            cols = [c[0] for c in cur.description]
    return pd.DataFrame(rows, columns=cols)


def write_case(row: dict[str, Any], changed_fields: list[str]) -> None:
    """Persist a validated case edit and its audit record in Databricks, or demo memory."""
    now = datetime.now(timezone.utc).isoformat()
    actor = os.getenv("APP_USER_NAME", USER_NAME)
    if not databricks_configured():
        global demo_df
        idx = demo_df.index[demo_df["CASE_ID"].astype(str) == str(row["CASE_ID"])]
        if len(idx):
            for key in changed_fields:
                demo_df.loc[idx[0], key] = row.get(key)
        demo_audit.append({
            "CASE_ID": row["CASE_ID"], "CHANGED_FIELDS": ", ".join(changed_fields),
            "CHANGED_BY": actor, "CHANGED_AT_UTC": now,
        })
        return

    # Use a MERGE keyed on CASE_ID to keep updates idempotent. Table names are env-configured
    # identifiers; only configure them with trusted catalog.schema.table values.
    merge_sql = f"""
      MERGE INTO {DATA_TABLE} AS target
      USING (SELECT ? AS CASE_ID, ? AS ROOT_CAUSE, ? AS ACTION_OWNER,
                    ? AS STATUS, ? AS COMMENTS) AS source
      ON target.CASE_ID = source.CASE_ID
      WHEN MATCHED THEN UPDATE SET
        target.ROOT_CAUSE = source.ROOT_CAUSE,
        target.ACTION_OWNER = source.ACTION_OWNER,
        target.STATUS = source.STATUS,
        target.COMMENTS = source.COMMENTS
    """
    audit_sql = f"""INSERT INTO {AUDIT_TABLE}
      (CASE_ID, CHANGED_FIELDS, CHANGED_BY, CHANGED_AT_UTC, CHANGE_SOURCE)
      VALUES (?, ?, ?, current_timestamp(), 'Dash UI')"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(merge_sql, (
                str(row["CASE_ID"]), str(row.get("ROOT_CAUSE") or ""),
                str(row.get("ACTION_OWNER") or ""), str(row.get("STATUS") or ""),
                str(row.get("COMMENTS") or ""),
            ))
            cur.execute(audit_sql, (str(row["CASE_ID"]), ", ".join(changed_fields), actor))


def card(label, value, note, icon):
    return dbc.Card(
        dbc.CardBody([
            html.Div([html.Span(icon, className="metric-icon"), html.Span(label, className="metric-label")]),
            html.H2(value, className="metric-value"),
            html.Div(note, className="metric-note"),
        ]),
        className="metric-card h-100",
    )


def make_layout():
    return dbc.Container(fluid=True, className="app-shell", children=[
        dcc.Store(id="source-store", data=""),
        dbc.Row([
            dbc.Col(html.Div([
                html.Div("SC", className="brand-mark"),
                html.Div([html.Div("SUPPLY CHAIN", className="eyebrow"), html.H4("KPI Workbench", className="brand-title")]),
            ], className="brand"), width=12),
        ], className="topbar"),
        dbc.Row([
            dbc.Col([
                html.Div("WORKSPACE", className="nav-caption"),
                dbc.Nav([
                    dbc.NavLink([html.Span("▦", className="nav-icon"), "Overview"], href="#", id="nav-overview", active=True),
                    dbc.NavLink([html.Span("✎", className="nav-icon"), "Case management"], href="#", id="nav-cases"),
                    dbc.NavLink([html.Span("↺", className="nav-icon"), "Audit history"], href="#", id="nav-audit"),
                ], vertical=True, pills=True, className="side-nav"),
                html.Div(className="sidebar-bottom", children=[
                    html.Div(className="status-dot"),
                    html.Div([html.Div("DATA CONNECTION", className="eyebrow"), html.Div(id="connection-label", className="connection-label")]),
                ]),
            ], md=2, className="sidebar"),
            dbc.Col([
                html.Div([
                    html.Div([html.Div("ANALYTICS / OPERATIONS", className="eyebrow"), html.H2("On-time delivery control tower", className="page-title"),
                              html.P("Spot delivery risk, assign root causes, and track corrective action in one workspace.", className="page-subtitle")]),
                    dbc.Badge("DEMO DATA", id="mode-badge", color="light", className="mode-badge"),
                ], className="page-heading"),
                html.Div(id="alert-area"),
                html.Div(id="overview-page", children=[
                    dbc.Row([
                        dbc.Col([html.Label("Plant", className="filter-label"), dcc.Dropdown(id="plant-filter", options=[], multi=True, placeholder="All plants", className="filter-dropdown")], md=4),
                        dbc.Col([html.Label("Delivery status", className="filter-label"), dcc.Dropdown(id="delivery-filter", options=[
                            {"label": "All deliveries", "value": "All"}, {"label": "Late", "value": "Late"},
                            {"label": "On time", "value": "On time"}, {"label": "Not shipped", "value": "Not shipped"}
                        ], value="All", clearable=False, className="filter-dropdown")], md=4),
                        dbc.Col([html.Label("Search", className="filter-label"), dbc.Input(id="search-filter", placeholder="Customer, part, case ID…", type="search", className="search-input")], md=4),
                    ], className="filter-row"),
                    dbc.Row([
                        dbc.Col(html.Div(id="kpi-cases"), md=3),
                        dbc.Col(html.Div(id="kpi-otd"), md=3),
                        dbc.Col(html.Div(id="kpi-late"), md=3),
                        dbc.Col(html.Div(id="kpi-open"), md=3),
                    ], className="g-3 metric-row"),
                    dbc.Row([
                        dbc.Col(dbc.Card([dbc.CardBody([
                            html.Div([html.Div("DELIVERY PERFORMANCE", className="eyebrow"), html.H5("On-time vs late", className="chart-title")]),
                            dcc.Graph(id="status-chart", config={"displayModeBar": False}, className="chart"),
                        ])], className="panel-card"), md=5),
                        dbc.Col(dbc.Card([dbc.CardBody([
                            html.Div([html.Div("ROOT CAUSE ANALYSIS", className="eyebrow"), html.H5("Cases by root cause", className="chart-title")]),
                            dcc.Graph(id="cause-chart", config={"displayModeBar": False}, className="chart"),
                        ])], className="panel-card"), md=7),
                    ], className="g-3 chart-row"),
                    dbc.Card([dbc.CardBody([
                        html.Div([html.Div([html.Div("CASE REGISTER", className="eyebrow"), html.H5("Delivery exceptions", className="chart-title")]),
                                  dbc.Button("Manage cases →", id="go-cases", color="primary", outline=True, size="sm", className="action-button")], className="section-head"),
                        dash_table.DataTable(id="overview-table", columns=[], data=[], page_size=7,
                            sort_action="native", style_table={"overflowX": "auto"},
                            style_header={"backgroundColor": "#f4f6fa", "color": "#667085", "fontWeight": "700", "fontSize": "11px", "border": "0", "textTransform": "uppercase"},
                            style_cell={"fontFamily": "Inter, Arial", "fontSize": "12px", "padding": "12px", "border": "0", "borderBottom": "1px solid #edf0f5", "textAlign": "left", "minWidth": "95px"},
                            style_data_conditional=[
                                {"if": {"filter_query": '{DELIVERY_STATUS} = "Late"', "column_id": "DELIVERY_STATUS"}, "color": "#c2413a", "fontWeight": "700"},
                                {"if": {"filter_query": '{DELIVERY_STATUS} = "On time"', "column_id": "DELIVERY_STATUS"}, "color": "#16805d", "fontWeight": "700"},
                            ]),
                    ])], className="panel-card table-panel"),
                ], style={}),
                html.Div(id="cases-page", children=[
                    dbc.Card([dbc.CardBody([
                        html.Div([html.Div("CORRECTIVE ACTION", className="eyebrow"), html.H5("Editable exception register", className="chart-title"),
                                  html.P("Edit root cause, owner, status, and comments. Save changes to write back and create an audit record.", className="helper-text")]),
                        dash_table.DataTable(id="cases-table", columns=[], data=[], editable=True, row_selectable="single",
                            page_size=10, sort_action="native", filter_action="native",
                            style_table={"overflowX": "auto"},
                            style_header={"backgroundColor": "#f4f6fa", "color": "#667085", "fontWeight": "700", "fontSize": "11px", "border": "0"},
                            style_cell={"fontFamily": "Inter, Arial", "fontSize": "12px", "padding": "11px", "border": "0", "borderBottom": "1px solid #edf0f5", "textAlign": "left", "minWidth": "100px", "maxWidth": "260px", "whiteSpace": "normal"},
                            dropdown={
                                "ROOT_CAUSE": {"options": [{"label": x, "value": x} for x in ["None", "Capacity", "Supplier", "Logistics", "Planning", "Quality", "Other"]]},
                                "STATUS": {"options": [{"label": x, "value": x} for x in ["Open", "In Progress", "Closed"]]},
                            }),
                        html.Div([
                            dbc.Button("Save selected row", id="save-case", color="primary", className="save-button"),
                            html.Div(id="save-message", className="save-message"),
                        ], className="save-row"),
                    ])], className="panel-card"),
                    dbc.Alert("Tip: use the Overview page to filter exceptions, then manage records here.", color="light", className="mt-3 helper-alert"),
                ], style={"display": "none"}),
                html.Div(id="audit-page", children=[
                    dbc.Card([dbc.CardBody([
                        html.Div([html.Div("GOVERNANCE", className="eyebrow"), html.H5("Change audit history", className="chart-title"),
                                  html.P("Each saved edit records the case, changed fields, actor, and UTC timestamp.", className="helper-text")]),
                        dash_table.DataTable(id="audit-table", columns=[], data=[], page_size=10,
                            style_table={"overflowX": "auto"},
                            style_header={"backgroundColor": "#f4f6fa", "color": "#667085", "fontWeight": "700", "fontSize": "11px", "border": "0"},
                            style_cell={"fontFamily": "Inter, Arial", "fontSize": "12px", "padding": "12px", "border": "0", "borderBottom": "1px solid #edf0f5", "textAlign": "left"}),
                    ])], className="panel-card"),
                ], style={"display": "none"}),
                html.Footer("SUPPLY CHAIN KPI WORKBENCH  •  Portfolio prototype  •  Verify all writeback schemas before production use", className="app-footer"),
            ], md=10, className="main-content"),
        ], className="g-0"),
    ])


app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], title=APP_TITLE, suppress_callback_exceptions=True)
server = app.server
app.layout = make_layout()


def with_delivery_status(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in ["PROMISED_DATE", "SHIP_DATE"]:
        if col in out.columns:
            out[col] = pd.to_datetime(out[col], errors="coerce")
    out["DELIVERY_STATUS"] = "Not shipped"
    shipped = out["SHIP_DATE"].notna()
    out.loc[shipped & (out["SHIP_DATE"].dt.date <= out["PROMISED_DATE"].dt.date), "DELIVERY_STATUS"] = "On time"
    out.loc[shipped & (out["SHIP_DATE"].dt.date > out["PROMISED_DATE"].dt.date), "DELIVERY_STATUS"] = "Late"
    return out


def fmt_date(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in ["PROMISED_DATE", "SHIP_DATE"]:
        if col in out.columns:
            out[col] = pd.to_datetime(out[col], errors="coerce").dt.strftime("%Y-%m-%d").fillna("")
    return out


def filtered_df(plant_values, delivery, search) -> pd.DataFrame:
    df = with_delivery_status(load_data())
    if plant_values:
        df = df[df["PLANT"].isin(plant_values)]
    if delivery and delivery != "All":
        df = df[df["DELIVERY_STATUS"] == delivery]
    if search:
        needle = str(search).strip().lower()
        cols = ["CASE_ID", "CUSTOMER", "PART_NUMBER", "PLANT"]
        mask = df[cols].fillna("").astype(str).apply(lambda c: c.str.lower().str.contains(needle, regex=False)).any(axis=1)
        df = df[mask]
    return df


@app.callback(
    Output("connection-label", "children"), Output("mode-badge", "children"), Output("mode-badge", "color"),
    Output("plant-filter", "options"), Output("overview-table", "columns"), Output("overview-table", "data"),
    Output("cases-table", "columns"), Output("cases-table", "data"),
    Output("audit-table", "columns"), Output("audit-table", "data"),
    Input("nav-overview", "n_clicks"), Input("nav-cases", "n_clicks"), Input("nav-audit", "n_clicks"),
    Input("plant-filter", "value"), Input("delivery-filter", "value"), Input("search-filter", "value"),
    prevent_initial_call=False,
)
def refresh_data(*_):
    try:
        df = with_delivery_status(load_data())
        source = "Databricks SQL Warehouse" if databricks_configured() else "Local sample data"
        badge = "DATABRICKS CONNECTED" if databricks_configured() else "DEMO DATA"
        badge_color = "success" if databricks_configured() else "light"
        plants = [{"label": x, "value": x} for x in sorted(df["PLANT"].dropna().unique())]
        overview_cols = [{"name": c.replace("_", " ").title(), "id": c} for c in ["CASE_ID", "PLANT", "CUSTOMER", "PART_NUMBER", "PROMISED_DATE", "SHIP_DATE", "DELIVERY_STATUS", "ROOT_CAUSE", "STATUS"]]
        edit_cols = [{"name": c.replace("_", " ").title(), "id": c, "editable": c in ["ROOT_CAUSE", "ACTION_OWNER", "STATUS", "COMMENTS"], "presentation": "dropdown" if c in ["ROOT_CAUSE", "STATUS"] else "input"} for c in df.columns]
        display_df = fmt_date(df)
        audit_rows = demo_audit.copy()
        if databricks_configured():
            try:
                with get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(f"SELECT CASE_ID, CHANGED_FIELDS, CHANGED_BY, CHANGED_AT_UTC, CHANGE_SOURCE FROM {AUDIT_TABLE} ORDER BY CHANGED_AT_UTC DESC LIMIT 500")
                        rows = cur.fetchall()
                        audit_rows = [dict(zip([c[0] for c in cur.description], r)) for r in rows]
            except Exception:
                audit_rows = [{"INFO": "Audit table unavailable. Run sql/setup.sql and verify the configured table name."}]
        audit_df = pd.DataFrame(audit_rows)
        audit_cols = [{"name": c.replace("_", " ").title(), "id": c} for c in audit_df.columns] if not audit_df.empty else [{"name": "Info", "id": "INFO"}]
        return source, badge, badge_color, plants, overview_cols, display_df[ [c["id"] for c in overview_cols] ].to_dict("records"), edit_cols, display_df.to_dict("records"), audit_cols, audit_df.to_dict("records")
    except Exception as exc:
        return f"Connection error: {str(exc)[:100]}", "CHECK CONNECTION", "danger", [], [], [], [], [], [{"name":"Info","id":"INFO"}], [{"INFO": str(exc)[:250]}]


@app.callback(
    Output("kpi-cases", "children"), Output("kpi-otd", "children"), Output("kpi-late", "children"), Output("kpi-open", "children"),
    Output("status-chart", "figure"), Output("cause-chart", "figure"),
    Output("overview-table", "data", allow_duplicate=True),
    Input("plant-filter", "value"), Input("delivery-filter", "value"), Input("search-filter", "value"),
    prevent_initial_call=True,
)
def update_overview(plants, delivery, search):
    df = filtered_df(plants, delivery, search)
    total = len(df)
    shipped = df[df["DELIVERY_STATUS"].isin(["Late", "On time"])]
    otd = (100 * (shipped["DELIVERY_STATUS"] == "On time").mean()) if len(shipped) else 0
    late = int((df["DELIVERY_STATUS"] == "Late").sum())
    open_cases = int(df["STATUS"].isin(["Open", "In Progress"]).sum())
    fig_status = px.pie(df, names="DELIVERY_STATUS", hole=.72,
                        color="DELIVERY_STATUS",
                        color_discrete_map={"On time":"#17866a", "Late":"#d85b52", "Not shipped":"#e9ad48"})
    fig_status.update_layout(margin=dict(t=8,b=8,l=8,r=8), legend=dict(orientation="h",y=-.12), paper_bgcolor="white", plot_bgcolor="white", font=dict(family="Inter, Arial", size=11))
    fig_status.update_traces(textposition="inside", textinfo="percent")
    causes = df[df["ROOT_CAUSE"].fillna("None") != "None"].groupby("ROOT_CAUSE", as_index=False).agg(CASES=("CASE_ID","count"), QTY=("ORDER_QTY","sum")).sort_values("CASES", ascending=True)
    fig_cause = px.bar(causes, x="CASES", y="ROOT_CAUSE", orientation="h", text="CASES", color_discrete_sequence=["#4769d8"])
    fig_cause.update_layout(margin=dict(t=8,b=8,l=8,r=8), paper_bgcolor="white", plot_bgcolor="white", font=dict(family="Inter, Arial", size=11), xaxis_title="Cases", yaxis_title="", showlegend=False)
    fig_cause.update_traces(textposition="outside", cliponaxis=False)
    display_df = fmt_date(df)
    cols = ["CASE_ID", "PLANT", "CUSTOMER", "PART_NUMBER", "PROMISED_DATE", "SHIP_DATE", "DELIVERY_STATUS", "ROOT_CAUSE", "STATUS"]
    return (card("Cases in view", f"{total:,}", "Filtered exception records", "▦"),
            card("On-time delivery", f"{otd:.1f}%", f"{len(shipped):,} shipped cases", "↗"),
            card("Late shipments", f"{late:,}", "Past promised date", "◷"),
            card("Open actions", f"{open_cases:,}", "Open or in progress", "◎"),
            fig_status, fig_cause, display_df[cols].to_dict("records"))


@app.callback(
    Output("overview-page", "style"), Output("cases-page", "style"), Output("audit-page", "style"),
    Output("nav-overview", "active"), Output("nav-cases", "active"), Output("nav-audit", "active"),
    Input("nav-overview", "n_clicks"), Input("nav-cases", "n_clicks"), Input("nav-audit", "n_clicks"), Input("go-cases", "n_clicks"),
)
def navigate(n_overview, n_cases, n_audit, go_cases):
    from dash import ctx
    trigger = ctx.triggered_id
    page = "cases" if trigger in ("nav-cases", "go-cases") else "audit" if trigger == "nav-audit" else "overview"
    return (
        {"display": "block" if page == "overview" else "none"},
        {"display": "block" if page == "cases" else "none"},
        {"display": "block" if page == "audit" else "none"},
        page == "overview", page == "cases", page == "audit"
    )


@app.callback(
    Output("save-message", "children"), Output("save-message", "className"),
    Input("save-case", "n_clicks"), State("cases-table", "data"), State("cases-table", "selected_rows"),
    State("cases-table", "data_previous"), prevent_initial_call=True,
)
def save_selected(n_clicks, rows, selected_rows, previous):
    if not selected_rows:
        return "Select a row first, then save.", "save-message error"
    idx = selected_rows[0]
    if idx >= len(rows):
        return "Selected row is no longer available. Refresh and try again.", "save-message error"
    row = rows[idx]
    old_rows = previous or []
    old = next((r for r in old_rows if r.get("CASE_ID") == row.get("CASE_ID")), None)
    editable = ["ROOT_CAUSE", "ACTION_OWNER", "STATUS", "COMMENTS"]
    changed = [c for c in editable if old is None or str(old.get(c, "")) != str(row.get(c, ""))]
    if not changed:
        return "No changes detected. Edit a field before saving.", "save-message warning"
    if not row.get("CASE_ID"):
        return "CASE_ID is required.", "save-message error"
    if row.get("STATUS") not in ["Open", "In Progress", "Closed"]:
        return "Status must be Open, In Progress, or Closed.", "save-message error"
    if row.get("ROOT_CAUSE") not in ["None", "Capacity", "Supplier", "Logistics", "Planning", "Quality", "Other"]:
        return "Choose a valid root cause.", "save-message error"
    if not str(row.get("COMMENTS") or "").strip():
        return "Comments cannot be blank. Enter a short action note.", "save-message error"
    try:
        write_case(row, changed)
        return f"Saved {row['CASE_ID']} • audit entry created • {', '.join(changed)}", "save-message success"
    except Exception as exc:
        return f"Save failed: {str(exc)[:220]}", "save-message error"


if __name__ == "__main__":
    app.run(debug=os.getenv("DASH_DEBUG", "false").lower() == "true", host="0.0.0.0", port=int(os.getenv("PORT", "8050")))
