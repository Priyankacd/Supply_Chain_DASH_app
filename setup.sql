-- Run in a Databricks SQL Warehouse after choosing your catalog/schema.
-- Update the three-part table names in app.yaml / environment to match your workspace.
CREATE SCHEMA IF NOT EXISTS main.supply_chain;

CREATE TABLE IF NOT EXISTS main.supply_chain.otd_cases (
  CASE_ID STRING NOT NULL,
  PLANT STRING,
  CUSTOMER STRING,
  PART_NUMBER STRING,
  PROMISED_DATE DATE,
  SHIP_DATE DATE,
  ORDER_QTY BIGINT,
  ROOT_CAUSE STRING,
  ACTION_OWNER STRING,
  STATUS STRING,
  COMMENTS STRING
) USING DELTA;

CREATE TABLE IF NOT EXISTS main.supply_chain.otd_case_audit (
  CASE_ID STRING,
  CHANGED_FIELDS STRING,
  CHANGED_BY STRING,
  CHANGED_AT_UTC TIMESTAMP,
  CHANGE_SOURCE STRING
) USING DELTA;

-- Optional fictional seed data. Do not load production/customer-sensitive data for a demo.
MERGE INTO main.supply_chain.otd_cases AS t
USING (
  SELECT * FROM VALUES
  ('OTD-1001','Pune','Northstar Auto','PN-4012',DATE'2026-10-02',DATE'2026-10-04',120,'Capacity','A. Shah','Open','Review next production slot'),
  ('OTD-1002','Chennai','Atlas Mobility','PN-2280',DATE'2026-10-03',DATE'2026-10-03',80,'None','R. Iyer','Closed','Shipped on time'),
  ('OTD-1003','Pune','Vertex Motors','PN-1187',DATE'2026-10-05',DATE'2026-10-08',45,'Supplier','M. Joshi','In Progress','Supplier recovery plan requested'),
  ('OTD-1004','Nashik','Northstar Auto','PN-9021',DATE'2026-10-06',DATE'2026-10-06',210,'None','S. Patil','Closed','No action required'),
  ('OTD-1005','Chennai','Summit Commercial','PN-3310',DATE'2026-10-07',DATE'2026-10-10',60,'Logistics','K. Rao','Open','Carrier escalation pending')
  AS v(CASE_ID,PLANT,CUSTOMER,PART_NUMBER,PROMISED_DATE,SHIP_DATE,ORDER_QTY,ROOT_CAUSE,ACTION_OWNER,STATUS,COMMENTS)
) AS s
ON t.CASE_ID = s.CASE_ID
WHEN NOT MATCHED THEN INSERT *;
