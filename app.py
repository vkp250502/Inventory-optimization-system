import streamlit as st
import pandas as pd
import mysql.connector
import plotly.express as px


# --- DB Connection ---
def get_connection():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pem") as tmp:
    tmp.write(st.secrets["ssl_ca"].encode("utf-8"))
    ssl_path = tmp.name
    return mysql.connector.connect(
        host=st.secrets["database"]["host"],
        port=int(st.secrets["database"].get("port", 4000)),
        user=st.secrets["database"]["user"],
        password=st.secrets["database"]["password"],
        database=st.secrets["database"]["name"],
        
        ssl_ca= st.secrets["database"]["ssl_path"]
    )
# --- Fetch Data ---
def fetch_data(query):
    conn = get_connection()
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# --- Streamlit Layout ---
st.set_page_config(page_title="Inventory Dashboard", layout="wide")
st.title("📊 Inventory Management Dashboard")

# --- Load Data ---
products = fetch_data("SELECT * FROM products")
sales = fetch_data("SELECT * FROM sales")
purchases = fetch_data("SELECT * FROM purchases")
inventory = fetch_data("SELECT * FROM inventory")

# --- Tabs ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📦 Products",
    "📤 Sales",
    "📥 Purchases",
    "🏪 Inventory",
    "📈 Visualizations"
])

with tab1:
    st.subheader("Products Table")
    st.dataframe(products)

with tab2:
    st.subheader("Sales Table")
    st.dataframe(sales)

with tab3:
    st.subheader("Purchases Table")
    st.dataframe(purchases)

with tab4:
    st.subheader("Inventory Table")
    st.dataframe(inventory)

with tab5:
    st.subheader("📈 Key Visualizations")

    col1, col2 = st.columns(2)

    # 📉 Sales Quantity Over Time
    sales["sale_date"] = pd.to_datetime(sales["sale_date"])
    sales_over_time = sales.groupby("sale_date")["quantity_sold"].sum().reset_index()
    fig1 = px.line(sales_over_time, x="sale_date", y="quantity_sold", title="Sales Over Time")
    col1.plotly_chart(fig1, use_container_width=True)

    # 📈 Purchases Over Time
    purchases["purchase_date"] = pd.to_datetime(purchases["purchase_date"])
    purchases_over_time = purchases.groupby("purchase_date")["quantity_purchased"].sum().reset_index()
    fig2 = px.line(purchases_over_time, x="purchase_date", y="quantity_purchased", title="Purchases Over Time")
    col2.plotly_chart(fig2, use_container_width=True)

    # 📊 Stock on Hand by Product
    merged_inventory = pd.merge(inventory, products, on="product_id", how="left")
    stock_chart = px.bar(merged_inventory, x="product_name", y="stock_on_hand", title="Stock on Hand by Product")
    st.plotly_chart(stock_chart, use_container_width=True)

    # 🧮 Top Selling Products
    top_selling = sales.groupby("product_id")["quantity_sold"].sum().reset_index()
    top_selling = pd.merge(top_selling, products, on="product_id")
    top_selling = top_selling.sort_values("quantity_sold", ascending=False).head(10)
    top_chart = px.bar(top_selling, x="product_name", y="quantity_sold", title="Top 10 Selling Products")
    st.plotly_chart(top_chart, use_container_width=True)

import os

if st.button("🔄 Sync Google Sheets to MySQL"):
    os.system("python sync_gsheet_mysql.py")
    st.success("✅ Sync completed.")

