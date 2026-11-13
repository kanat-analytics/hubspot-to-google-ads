# HubSpot to Google Ads: offline conversions report

This project takes deals from HubSpot CRM, cleans them, stores them in BigQuery, and writes a report of offline conversions to Google Sheets. It runs every day with GitHub Actions.

**All data in this project is test data. The deals, amounts and click IDs are made up.**

## What the project does

1. Gets all deals from HubSpot with the CRM API (with pagination).
2. Cleans the deals with pandas.
3. Loads the clean table to BigQuery.
4. Reads the rows for the report from BigQuery with SQL.
5. Writes the report to a Google Sheet.

## Cleaning rules

- Keep six columns: id, dealname, dealstage, amount, closedate, gclid.
- Remove spaces at the start and end of text.
- Remove duplicates by gclid. The first deal stays.
- Keep only deals in the stage "closedwon".
- Remove deals without a gclid.
- Change amount to a number.
- Change the close date to the time zone Asia/Almaty.
- Write the conversion time in this format: 2026-11-01 00:00:00+05:00

The test data has 10 deals. After cleaning, 5 deals stay.

## Result

The Google Sheet has one row for each conversion.

| Deal ID | Google Click ID | Conversion Name | Conversion Time | Conversion Value | Conversion Currency |
|---|---|---|---|---|---|
| 538256691424 | test-gclid-0001 | HubSpot Closed Won | 2026-10-15 00:00:00+05:00 | 1500 | USD |
| 538170101960 | test-gclid-0002 | HubSpot Closed Won | 2026-10-18 00:00:00+05:00 | 800 | USD |
| 538245450954 | test-gclid-0004 | HubSpot Closed Won | 2026-10-22 00:00:00+05:00 | 2300 | USD |
| 538122609881 | test-gclid-0007 | HubSpot Closed Won | 2026-10-29 00:00:00+05:00 | 1750 | USD |
| 538118867143 | test-gclid-0008 | HubSpot Closed Won | 2026-11-01 00:00:00+05:00 | 400 | USD |

"HubSpot Closed Won" and "USD" are example values.

## Automation

- GitHub Actions runs the pipeline every day at 02:00 UTC.
- The workflow also has a button for a manual run.
- The HubSpot key and the Google Cloud key are in GitHub Secrets. They are not in the code.
- Each run writes a short log: deals from HubSpot, clean deals, rows from BigQuery, rows in the sheet.

## Files

| File | What it is |
|---|---|
| `hubspot_to_google_ads.py` | The pipeline: HubSpot API, cleaning, BigQuery, Google Sheets |
| `requirements.txt` | The Python libraries for the pipeline |
| `.github/workflows/run.yml` | The schedule and the steps for GitHub Actions |

## Tools

Python, pandas, requests, HubSpot CRM API, Google BigQuery, Google Sheets API (gspread), GitHub Actions.

## Limits

- The data is test data. The click IDs are not real Google click IDs.
- BigQuery works in sandbox mode. In this mode, tables are deleted after 60 days.
- The upload of conversions to Google Ads is not part of this project. The sheet is a report for the client.
