# HubSpot deals -> BigQuery -> Google Sheets report
# All deals in this project are test data (made up).

import os
import json
import logging

import requests
import pandas as pd
import gspread
from google.cloud import bigquery
from google.oauth2 import service_account

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    force=True,
)

SHEET_ID = '1bQTqfCvpG_unCA4DkXw_b5kuIXLUrWVSAxj4vk-Kqww'
DATASET = 'hubspot_ads'
TABLE = 'clean_deals'


# 1. Get all deals from HubSpot with pagination
def get_all_deals(token):
    url = 'https://api.hubapi.com/crm/v3/objects/deals'
    headers = {'Authorization': f'Bearer {token}'}
    params = {
        'limit': 100,
        'properties': 'dealname,dealstage,amount,closedate,gclid'
    }
    all_deals = []

    while True:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        all_deals.extend(data['results'])

        paging = data.get('paging')
        if paging is None:
            break
        params['after'] = paging['next']['after']

    return all_deals


# 2. Deals -> raw table
def make_raw_df(deals):
    rows = []
    for deal in deals:
        row = deal['properties']
        row['id'] = deal['id']
        rows.append(row)
    return pd.DataFrame(rows)


# 3. Cleaning (the same rules as Cleaning 1-10 in the notebook)
def clean_deals(raw_df):
    df = raw_df.copy()

    # keep only the columns we need
    columns = ['id', 'dealname', 'dealstage', 'amount', 'closedate', 'gclid']
    df = df[columns].copy()

    # remove spaces at the start and end of text
    text_columns = ['dealname', 'dealstage', 'gclid']
    for col in text_columns:
        df[col] = df[col].str.strip()

    # keep only closed won deals
    df = df[df['dealstage'] == 'closedwon'].copy()

    # remove deals without a gclid
    df['gclid'] = df['gclid'].replace('', pd.NA)
    df = df.dropna(subset=['gclid'])

    # remove duplicates by gclid
    df = df.drop_duplicates(subset=['gclid'], keep='first')
    
    # change amount to a number
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')

    # change the date to Astana time
    df['closedate'] = pd.to_datetime(df['closedate'], utc=True)
    df['closedate'] = df['closedate'].dt.tz_convert('Asia/Almaty')

    # write the date in the Google Ads format
    t = df['closedate'].dt.strftime('%Y-%m-%d %H:%M:%S%z')
    df['conversion_time'] = t.str[:-2] + ':' + t.str[-2:]

    return df


# 4. Load the clean table to BigQuery and read the rows for the report
def load_to_bigquery(df, key_info):
    credentials = service_account.Credentials.from_service_account_info(key_info)
    client = bigquery.Client(credentials=credentials, project=key_info['project_id'])

    dataset = bigquery.Dataset(f'{client.project}.{DATASET}')
    dataset.location = 'EU'
    client.create_dataset(dataset, exists_ok=True)

    table_id = f'{client.project}.{DATASET}.{TABLE}'
    job_config = bigquery.LoadJobConfig(write_disposition='WRITE_TRUNCATE')
    job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
    job.result()

    query = f"""
    SELECT id, gclid, conversion_time, amount
    FROM `{table_id}`
    WHERE dealstage = 'closedwon'
      AND gclid IS NOT NULL
    ORDER BY conversion_time
    """
    ads_df = client.query(query).to_dataframe(create_bqstorage_client=False)
    return ads_df


# 5. Write the report rows to the Google Sheet
def write_to_sheet(ads_df, key_info):
    sheets_credentials = service_account.Credentials.from_service_account_info(
        key_info,
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    gc = gspread.authorize(sheets_credentials)
    sheet = gc.open_by_key(SHEET_ID)

    report_df = pd.DataFrame({
        'Deal ID': ads_df['id'].astype(str),
        'Google Click ID': ads_df['gclid'],
        'Conversion Name': 'HubSpot Closed Won',
        'Conversion Time': ads_df['conversion_time'],
        'Conversion Value': ads_df['amount'].astype(float),
        'Conversion Currency': 'USD',
    })
    rows = [report_df.columns.tolist()] + report_df.values.tolist()

    worksheet = sheet.sheet1
    worksheet.clear()
    worksheet.update(values=rows, range_name='A1')
    return len(rows)


# Run all steps in order
def main():
    token = os.environ['HUBSPOT_KEY']
    key_info = json.loads(os.environ['GCP_KEY'])

    deals = get_all_deals(token)
    logging.info(f'Deals from HubSpot: {len(deals)}')

    raw_df = make_raw_df(deals)
    df = clean_deals(raw_df)
    logging.info(f'Clean deals: {len(df)}')

    ads_df = load_to_bigquery(df, key_info)
    logging.info(f'Rows from BigQuery: {len(ads_df)}')

    row_count = write_to_sheet(ads_df, key_info)
    logging.info(f'Rows in the sheet: {row_count}')


if __name__ == '__main__':
    main()
