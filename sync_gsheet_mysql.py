import pandas as pd
import numpy as np
import mysql.connector
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st

# --- Step 1: Authenticate Google Sheets ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials_dict = {
    "type": st.secrets["google_sheets"]["type"],
    "project_id": st.secrets["google_sheets"]["project_id"],
    "private_key_id": st.secrets["google_sheets"]["private_key_id"],
    "private_key": st.secrets["google_sheets"]["private_key"],
    "client_email": st.secrets["google_sheets"]["client_email"],
    "client_id": st.secrets["google_sheets"]["client_id"],
    "auth_uri": st.secrets["google_sheets"]["auth_uri"],
    "token_uri": st.secrets["google_sheets"]["token_uri"],
    "auth_provider_x509_cert_url": st.secrets["google_sheets"]["auth_provider_x509_cert_url"],
    "client_x509_cert_url": st.secrets["google_sheets"]["client_x509_cert_url"]
}

creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_dict, scope)
client = gspread.authorize(creds)
spreadsheet_id = "1dSjJlPulzodrDRiRtsCR72wZRDH78dyr7iEMUUldAZQ"
spreadsheet =client.open_by_key(spreadsheet_id)


sheet_names = [sheet.title for sheet in spreadsheet.worksheets()]

def get_df_from_sheet(sheet_name):
    worksheet = spreadsheet.worksheet(sheet_name)
    data = worksheet.get_all_records()
    return pd.DataFrame(data)



sheet_dataframes = {}

for name in sheet_names:
    df = get_df_from_sheet(name)
    sheet_dataframes[name] = df
    print(f"✅ Loaded '{name}' with {len(df)} rows.")


products_df = sheet_dataframes["products"]
inventory_df = sheet_dataframes["inventory"]
sales_df = sheet_dataframes["sales"]
purchases_df = sheet_dataframes["purchases"]
sales_df.head(10)


# --- Step 2: Connect to MySQL ---
db = mysql.connector.connect(
    host="127.0.0.1",
    user="root",
    password="Vishu@004",
    database="inventory_system"
)
cursor = db.cursor()
print("connected sucessfully")

#checking for table fatch or not from database
# cursor.execute("select * from inventory")
# # fetch all rows
# rows = cursor.fetchall()

# # display rows
# for row in rows:
#     print(row)



# --- Function: Upsert into Products Table ---
def upsert_products(df):
    for _, row in df.iterrows():
        sql = """
        INSERT INTO products (product_id, product_name, category, supplier, reorder_point, target_stock_level)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            product_name = VALUES(product_name),
            category = VALUES(category),
            supplier = VALUES(supplier),
            reorder_point = VALUES(reorder_point),
            target_stock_level = VALUES(target_stock_level)
        """
        values = (
            row["product_id"], row["product_name"], row["category"],
            row["supplier"], row["reorder_point"], row["target_stock_level"]
        )
        cursor.execute(sql, values)

# --- Function: Upsert into Inventory Table ---
def upsert_inventory(df):
    for _, row in df.iterrows():
        sql = """
        INSERT INTO inventory (inventory_id, product_id, stock_on_hand, warehouse_location, last_updated)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            product_id = VALUES(product_id),
            stock_on_hand = VALUES(stock_on_hand),
            warehouse_location = VALUES(warehouse_location),
            last_updated = VALUES(last_updated)
        """
        values = (
            row["inventory_id"], row["product_id"], row["stock_on_hand"],
            row["warehouse_location"], row["last_updated"]
        )
        cursor.execute(sql, values)

# --- Function: Upsert into Sales Table ---
def upsert_sales(df):
    for _, row in df.iterrows():
        sql = """
        INSERT INTO sales (sale_id, product_id, sale_date, quantity_sold)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            product_id = VALUES(product_id),
            sale_date = VALUES(sale_date),
            quantity_sold = VALUES(quantity_sold)
        """
        values = (
            row["sale_id"], row["product_id"], row["sale_date"],
            row["quantity_sold"]
        )
        cursor.execute(sql, values)

# --- Function: Upsert into Purchases Table ---
def upsert_purchases(df):
    for _, row in df.iterrows():
        sql = """
        INSERT INTO purchases (purchase_id, product_id, purchase_date, quantity_purchased, lead_time_days)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            product_id = VALUES(product_id),
            purchase_date = VALUES(purchase_date),
            quantity_purchased = VALUES(quantity_purchased),
            lead_time_days = VALUES(lead_time_days)
        """
        values = (
            row["purchase_id"], row["product_id"], row["purchase_date"],
            row["quantity_purchased"], row["lead_time_days"]
        )
        cursor.execute(sql, values)
# --- Apply All Insert/Update ---
upsert_products(sheet_dataframes["products"])
upsert_inventory(sheet_dataframes["inventory"])
upsert_sales(sheet_dataframes["sales"])
upsert_purchases(sheet_dataframes["purchases"])


# --- Finalize ---
db.commit()
cursor.close()
db.close()

print("✅ All tables synced successfully with MySQL.")