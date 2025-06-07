import streamlit as st
import pandas as pd
import mysql.connector
import plotly.express as px
import tempfile

# --- DB Connection ---
def get_connection():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pem") as tmp:
        tmp.write(st.secrets["database"]["ssl_ca"].encode("utf-8"))
        ssl_path = tmp.name
    return mysql.connector.connect(
        host=st.secrets["database"]["host"],
        port=int(st.secrets["database"].get("port", 4000)),
        user=st.secrets["database"]["user"],
        password=st.secrets["database"]["password"],
        database=st.secrets["database"]["database"],
        ssl_ca= ssl_path,
        ssl_verify_cert=True
    )
# --- Fetch Data ---
def fetch_data(query):
    conn = get_connection()
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# --- Streamlit Layout ---
st.set_page_config(page_title="Inventory Dashboard", layout="wide")
st.title("📊 Inventory Optimization system")

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
    google_sheet_url = "https://docs.google.com/spreadsheets/d/1dSjJlPulzodrDRiRtsCR72wZRDH78dyr7iEMUUldAZQ/edit?gid=0#gid=0"
    st.link_button("✏️ Open Google Sheet to Enter Data", google_sheet_url)


with tab2:
    st.subheader("Sales Table")
    st.dataframe(sales)

with tab3:
    st.subheader("Purchases Table")
    st.dataframe(purchases)

with tab4:
    st.subheader("Inventory Table (Updated Live Stock)")

    # Calculate total sold per product
    total_sold = sales.groupby("product_id")["quantity_sold"].sum().reset_index()
    total_sold.columns = ["product_id", "total_sold"]

    # Calculate total purchased per product
    total_purchased = purchases.groupby("product_id")["quantity_purchased"].sum().reset_index()
    total_purchased.columns = ["product_id", "total_purchased"]

    # Merge all data
    inv = pd.merge(inventory, total_sold, on="product_id", how="left")
    inv = pd.merge(inv, total_purchased, on="product_id", how="left")
    inv = pd.merge(inv, products[["product_id", "product_name", "reorder_point"]], on="product_id", how="left")

    # Fill NaNs
    inv["total_sold"] = inv["total_sold"].fillna(0)
    inv["total_purchased"] = inv["total_purchased"].fillna(0)

    # Calculate updated stock
    inv["updated_stock"] = inv["stock_on_hand"] + inv["total_purchased"] - inv["total_sold"]

    # Mark low stock
    inv["status"] = inv.apply(
        lambda row: "🔴 Low Stock" if row["updated_stock"] < row["reorder_point"] else "🟢 Sufficient", axis=1
    )

    # Highlight function
    def highlight_stock(row):
        if row["updated_stock"] < row["reorder_point"]:
            return ['background-color: #ffd6d6'] * len(row)
        return [''] * len(row)

    # Show
    st.dataframe(
        inv[["product_id", "product_name", "stock_on_hand", "total_purchased", "total_sold", "updated_stock", "reorder_point", "status"]]
        .style.apply(highlight_stock, axis=1),
        use_container_width=True
    )

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

from sync_gsheet_mysql import sync_google_sheet_to_mysql

if st.button("🔄 Sync Google Sheets to MySQL", key="sync_btn"):
    sync_google_sheet_to_mysql()
    st.success("✅ Data synced successfully.")

