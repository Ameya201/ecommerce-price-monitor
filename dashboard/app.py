import streamlit as st
import pandas as pd
import sqlite3
import sys
from pathlib import Path
import components as cp

# Configure page
st.set_page_config(
    page_title="E-Commerce Price Monitor",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium Dark Theme
st.markdown("""
<style>
    .stApp {
        background-color: #0F0F1A;
        color: #E2E8F0;
    }
    .main-header {
        background: -webkit-linear-gradient(45deg, #7C3AED, #06B6D4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem;
        font-weight: 800;
        margin-bottom: 0;
        padding-bottom: 0;
    }
    .sub-header {
        color: #94A3B8;
        font-size: 1.2rem;
        margin-bottom: 2rem;
    }
    /* Glassmorphism Metric Cards */
    [data-testid="stMetric"] {
        background: rgba(26, 26, 46, 0.7);
        backdrop-filter: blur(10px);
        border-radius: 15px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 1.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1), 0 0 15px rgba(124, 58, 237, 0.1);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    [data-testid="stMetric"]:hover {
        transform: translateY(-5px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.2), 0 0 20px rgba(6, 182, 212, 0.2);
    }
    [data-testid="stMetricValue"] {
        color: #FFFFFF;
        font-weight: 700;
    }
    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        height: 3rem;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 5px 5px 0 0;
        color: #94A3B8;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        color: #06B6D4 !important;
        border-bottom-color: #06B6D4 !important;
    }
    
    /* Table styling */
    .dataframe {
        background-color: #1A1A2E !important;
        color: #E2E8F0 !important;
    }
</style>
""", unsafe_allow_html=True)

# Database Setup
DB_PATH = Path(__file__).resolve().parent.parent / 'data' / 'price_monitor.db'

@st.cache_data(ttl=60)
def load_data():
    if not DB_PATH.exists():
        return None, None, None, None
        
    try:
        conn = sqlite3.connect(str(DB_PATH))
        
        # Check if tables exist
        tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table';", conn)['name'].tolist()
        if not tables:
            return None, None, None, None

        # Products: JOIN categories to get category name
        if 'products' in tables:
            df_products = pd.read_sql('''
                SELECT p.*, c.name AS category
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
            ''', conn)
        else:
            df_products = pd.DataFrame()

        # Price history: JOIN competitors to get competitor_name
        if 'price_history' in tables:
            df_prices = pd.read_sql('''
                SELECT ph.*, comp.name AS competitor_name
                FROM price_history ph
                LEFT JOIN competitors comp ON ph.competitor_id = comp.id
            ''', conn)
        else:
            df_prices = pd.DataFrame()

        # Alerts table is named price_alerts in the schema
        alerts_table = 'price_alerts' if 'price_alerts' in tables else ('alerts' if 'alerts' in tables else None)
        if alerts_table:
            df_alerts = pd.read_sql(f'SELECT * FROM {alerts_table}', conn)
        else:
            df_alerts = pd.DataFrame()

        # Runs table is named scrape_runs in the schema
        runs_table = 'scrape_runs' if 'scrape_runs' in tables else ('scraper_runs' if 'scraper_runs' in tables else None)
        if runs_table:
            df_runs = pd.read_sql(f'SELECT * FROM {runs_table}', conn)
        else:
            df_runs = pd.DataFrame()
        
        conn.close()
        
        # Convert date columns
        if not df_prices.empty and 'scraped_at' in df_prices.columns:
            df_prices['scraped_at'] = pd.to_datetime(df_prices['scraped_at'])
            
        return df_products, df_prices, df_alerts, df_runs
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None, None, None, None

def main():
    st.markdown('<h1 class="main-header">🛍️ E-Commerce Price Monitor</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Real-time competitor intelligence & price tracking</p>', unsafe_allow_html=True)
    
    df_products, df_prices, df_alerts, df_runs = load_data()
    
    if df_products is None or (df_products.empty and df_prices.empty):
        st.warning("Database is empty or missing. Please run `python run_pipeline.py` to initialize data.")
        st.stop()
        
    # Sidebar Filters
    st.sidebar.markdown("### 📊 Filters")
    
    if not df_products.empty and 'category' in df_products.columns:
        categories = ['All'] + list(df_products['category'].dropna().unique())
        selected_category = st.sidebar.multiselect("Category", categories, default=['All'])
    else:
        selected_category = ['All']
        
    if not df_prices.empty and 'competitor_name' in df_prices.columns:
        competitors = ['All'] + list(df_prices['competitor_name'].dropna().unique())
        selected_competitor = st.sidebar.multiselect("Competitor", competitors, default=['All'])
    else:
        selected_competitor = ['All']

    # Apply filters
    filtered_products = df_products
    if 'All' not in selected_category and 'category' in filtered_products.columns:
        filtered_products = filtered_products[filtered_products['category'].isin(selected_category)]
        
    filtered_prices = df_prices
    if 'All' not in selected_competitor and 'competitor_name' in filtered_prices.columns:
        filtered_prices = filtered_prices[filtered_prices['competitor_name'].isin(selected_competitor)]
        
    if not filtered_products.empty and 'id' in filtered_products.columns and 'product_id' in filtered_prices.columns:
        filtered_prices = filtered_prices[filtered_prices['product_id'].isin(filtered_products['id'])]

    # KPI Row
    kpis = cp.render_kpi_cards(filtered_products, filtered_prices, df_alerts)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Products", kpis['total_products'])
    with col2:
        st.metric("Avg Price", f"${kpis['avg_price']:.2f}")
    with col3:
        st.metric("Price Drops Today", kpis['price_drops_today'], delta=kpis['price_drops_today'], delta_color="normal")
    with col4:
        st.metric("Active Alerts", kpis['active_alerts'], delta=-1 if kpis['active_alerts']==0 else 0, delta_color="inverse")
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Price Trends", 
        "⚔️ Competitor Comparison", 
        "🔔 Alerts Feed", 
        "📦 Product Explorer",
        "⚙️ Pipeline Health"
    ])
    
    with tab1:
        st.markdown("### Price History")
        if not filtered_products.empty and 'name' in filtered_products.columns:
            product_list = filtered_products['name'].unique()
            selected_product = st.selectbox("Select Product to Analyze", product_list)
            
            product_id = filtered_products[filtered_products['name'] == selected_product]['id'].iloc[0]
            product_prices = filtered_prices[filtered_prices['product_id'] == product_id]
            
            st.plotly_chart(cp.render_price_history_chart(product_prices), use_container_width=True)
            
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(cp.render_price_distribution(filtered_prices), use_container_width=True)
            with col2:
                st.plotly_chart(cp.render_category_distribution(filtered_products), use_container_width=True)
        else:
            st.info("No product data available.")
            
    with tab2:
        st.markdown("### Cross-Competitor Analysis")
        if not filtered_prices.empty and not filtered_products.empty:
            merged = pd.merge(filtered_prices, filtered_products, left_on='product_id', right_on='id', suffixes=('', '_prod'))
            
            # Get latest price per competitor per product
            if 'scraped_at' in merged.columns:
                latest_prices = merged.sort_values('scraped_at').groupby(['product_id', 'competitor_name']).last().reset_index()
            else:
                latest_prices = merged

            # Rename 'name' to 'product_name' for chart compatibility
            if 'name' in latest_prices.columns and 'product_name' not in latest_prices.columns:
                latest_prices = latest_prices.rename(columns={'name': 'product_name'})
                
            st.plotly_chart(cp.render_competitor_comparison(latest_prices), use_container_width=True)
            
            st.markdown("#### Detailed Comparison Table")
            display_cols = ['product_name', 'competitor_name', 'price', 'in_stock', 'scraped_at']
            display_cols = [c for c in display_cols if c in latest_prices.columns]
            st.dataframe(latest_prices[display_cols].sort_values('price'), use_container_width=True, hide_index=True)
        else:
            st.info("No competitor data available.")
            
    with tab3:
        st.markdown("### Recent Alerts")
        if not df_alerts.empty:
            sort_col = 'created_at' if 'created_at' in df_alerts.columns else df_alerts.columns[0]
            sorted_alerts = df_alerts.sort_values(sort_col, ascending=False)
            cp.render_price_alerts_table(sorted_alerts)
        else:
            st.info("No alerts generated yet.")
            
    with tab4:
        st.markdown("### Product Catalog")
        if not filtered_products.empty:
            search_query = st.text_input("🔍 Search Products")
            
            display_df = filtered_products
            if search_query and 'name' in display_df.columns:
                display_df = display_df[display_df['name'].str.contains(search_query, case=False, na=False)]
                
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No products found.")
            
    with tab5:
        st.markdown("### Scraper Runs & Pipeline Status")
        if df_runs is not None and not df_runs.empty:
            sort_col = 'started_at' if 'started_at' in df_runs.columns else df_runs.columns[0]
            st.dataframe(df_runs.sort_values(sort_col, ascending=False), use_container_width=True, hide_index=True)
        else:
            st.info("No pipeline run history available.")

if __name__ == "__main__":
    main()
