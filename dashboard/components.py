import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import streamlit as st
from datetime import datetime, date

# Theme settings
COLORS = {
    'bg': '#0F0F1A',
    'paper': '#1A1A2E',
    'text': '#E2E8F0',
    'purple': '#7C3AED',
    'cyan': '#06B6D4',
    'amber': '#F59E0B',
    'red': '#EF4444',
    'green': '#10B981',
    'grid': '#334155'
}

def apply_dark_theme(fig):
    fig.update_layout(
        plot_bgcolor=COLORS['bg'],
        paper_bgcolor=COLORS['bg'],
        font=dict(color=COLORS['text']),
        xaxis=dict(showgrid=True, gridcolor=COLORS['grid'], zerolinecolor=COLORS['grid']),
        yaxis=dict(showgrid=True, gridcolor=COLORS['grid'], zerolinecolor=COLORS['grid']),
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig

def render_kpi_cards(df_products, df_prices, df_alerts):
    # Compute metrics
    total_products = len(df_products) if not df_products.empty else 0
    avg_price = df_prices['price'].mean() if not df_prices.empty else 0
    
    today = date.today().isoformat()
    if not df_alerts.empty:
        today_alerts = df_alerts[df_alerts['created_at'].str.startswith(today, na=False)]
        price_drops = len(today_alerts[today_alerts['alert_type'] == 'price_drop'])
        active_alerts = len(df_alerts)
    else:
        price_drops = 0
        active_alerts = 0

    return {
        'total_products': total_products,
        'avg_price': avg_price,
        'price_drops_today': price_drops,
        'active_alerts': active_alerts
    }

def render_price_history_chart(df):
    fig = go.Figure()
    if not df.empty and 'price' in df.columns:
        date_col = 'scraped_at' if 'scraped_at' in df.columns else None
        sources = df['competitor_name'].unique() if 'competitor_name' in df.columns else ['Self']
        colors = [COLORS['cyan'], COLORS['purple'], COLORS['amber'], COLORS['green']]
        
        for i, source in enumerate(sources):
            source_df = df[df['competitor_name'] == source] if 'competitor_name' in df.columns else df
            if date_col:
                source_df = source_df.sort_values(date_col)
            
            fig.add_trace(go.Scatter(
                x=source_df[date_col] if date_col else source_df.index,
                y=source_df['price'],
                mode='lines+markers',
                name=source,
                line=dict(color=colors[i % len(colors)], width=3),
                fill='tozeroy',
                fillcolor=f"rgba({int(colors[i%len(colors)][1:3], 16)}, {int(colors[i%len(colors)][3:5], 16)}, {int(colors[i%len(colors)][5:], 16)}, 0.1)",
                hovertemplate="<b>%{x}</b><br>Price: $%{y:.2f}<extra></extra>"
            ))
            
    fig.update_layout(title="Price History", hovermode="x unified")
    return apply_dark_theme(fig)

def render_competitor_comparison(df):
    fig = go.Figure()
    if not df.empty and 'competitor_name' in df.columns and 'price' in df.columns and 'product_name' in df.columns:
        colors = [COLORS['cyan'], COLORS['purple'], COLORS['amber'], COLORS['green']]
        sources = df['competitor_name'].unique()
        
        for i, source in enumerate(sources):
            source_df = df[df['competitor_name'] == source]
            fig.add_trace(go.Bar(
                x=source_df['product_name'],
                y=source_df['price'],
                name=source,
                marker_color=colors[i % len(colors)]
            ))
            
    fig.update_layout(
        title="Competitor Price Comparison",
        barmode='group',
        xaxis_title="Product",
        yaxis_title="Price"
    )
    return apply_dark_theme(fig)

def render_price_alerts_table(df):
    if df.empty:
        st.info("No active alerts.")
        return
        
    def highlight_alert_type(val):
        if val == 'price_increase':
            color = COLORS['red']
        elif val == 'price_drop':
            color = COLORS['green']
        elif val == 'stock_change':
            color = COLORS['cyan']
        else:
            color = COLORS['text']
        return f'color: {color}; font-weight: bold'
    
    st.dataframe(
        df.style.applymap(highlight_alert_type, subset=['alert_type']),
        use_container_width=True,
        hide_index=True
    )

def render_category_distribution(df):
    fig = go.Figure()
    if not df.empty and 'category' in df.columns:
        cat_counts = df['category'].value_counts()
        fig.add_trace(go.Pie(
            labels=cat_counts.index,
            values=cat_counts.values,
            hole=0.6,
            marker=dict(colors=[COLORS['cyan'], COLORS['purple'], COLORS['amber'], COLORS['green'], COLORS['red']])
        ))
        fig.update_layout(title="Products by Category", showlegend=False)
    return apply_dark_theme(fig)

def render_price_distribution(df):
    fig = go.Figure()
    if not df.empty and 'price' in df.columns:
        fig.add_trace(go.Histogram(
            x=df['price'],
            nbinsx=30,
            marker_color=COLORS['purple'],
            opacity=0.8
        ))
        fig.update_layout(title="Price Distribution", xaxis_title="Price", yaxis_title="Count")
    return apply_dark_theme(fig)
