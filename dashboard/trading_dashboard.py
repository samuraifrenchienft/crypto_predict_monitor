"""
Dashboard integration for displaying user trade executions and P&L
Integrates with the wallet tracking system to show real-time trading data
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import requests
import os

# Configuration
API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

def get_user_executions(user_address: str, market: str = None, status: str = None):
    """Fetch user's execution history"""
    try:
        params = {}
        if market:
            params["market"] = market
        if status:
            params["status"] = status
        
        response = requests.get(f"{API_BASE}/api/executions/{user_address}", params=params)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        st.error(f"Error fetching executions: {e}")
        return []

def get_user_pnl(user_address: str):
    """Fetch user's P&L summary"""
    try:
        response = requests.get(f"{API_BASE}/api/pnl/{user_address}")
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        st.error(f"Error fetching P&L: {e}")
        return []

def format_currency(amount: float) -> str:
    """Format currency with color coding"""
    if amount >= 0:
        return f"🟢 ${amount:,.2f}"
    else:
        return f"🔴 -${abs(amount):,.2f}"

def display_executions_table(executions: list):
    """Display executions in a formatted table"""
    if not executions:
        st.info("No executions found")
        return
    
    # Convert to DataFrame for easier display
    df = pd.DataFrame(executions)
    
    # Format timestamps
    df['entry_timestamp'] = pd.to_datetime(df['entry_timestamp']).dt.strftime('%Y-%m-%d %H:%M')
    if 'exit_timestamp' in df.columns:
        df['exit_timestamp'] = pd.to_datetime(df['exit_timestamp']).dt.strftime('%Y-%m-%d %H:%M')
    
    # Format prices and P&L
    df['entry_price'] = df['entry_price'].map('${:,.4f}'.format)
    if 'exit_price' in df.columns:
        df['exit_price'] = df['exit_price'].apply(lambda x: f"${x:,.4f}" if x is not None else "-")
    if 'pnl' in df.columns:
        df['pnl'] = df['pnl'].apply(lambda x: format_currency(x) if x is not None else "-")
    
    # Display table
    st.dataframe(
        df[[
            'market', 'market_ticker', 'side', 'entry_price', 'exit_price',
            'quantity', 'pnl', 'status', 'entry_timestamp'
        ]].rename(columns={
            'market': 'Market',
            'market_ticker': 'Ticker',
            'side': 'Side',
            'entry_price': 'Entry',
            'exit_price': 'Exit',
            'quantity': 'Qty',
            'pnl': 'P&L',
            'status': 'Status',
            'entry_timestamp': 'Time'
        }),
        use_container_width=True
    )

def display_pnl_overview(pnl_data: list):
    """Display P&L overview cards"""
    if not pnl_data:
        st.info("No P&L data available")
        return
    
    cols = st.columns(len(pnl_data))
    
    for i, market in enumerate(pnl_data):
        with cols[i]:
            st.markdown(f"### {market['market'].upper()}")
            
            # Total P&L
            total_pnl = market.get('total_pnl', 0)
            st.metric(
                "Total P&L",
                format_currency(total_pnl),
                delta=f"{market.get('completed_trades', 0)} trades"
            )
            
            # Additional stats
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Win Rate:** {market.get('completed_trades', 0)} trades")
                if market.get('avg_pnl_per_trade', 0) != 0:
                    st.write(f"**Avg/Trade:** {format_currency(market['avg_pnl_per_trade'])}")
            with col2:
                st.write(f"**Best:** {format_currency(market.get('best_trade', 0))}")
                st.write(f"**Worst:** {format_currency(market.get('worst_trade', 0))}")

def display_pnl_chart(executions: list):
    """Display P&L over time chart"""
    if not executions:
        st.info("No data to chart")
        return
    
    # Filter only closed trades
    closed_trades = [e for e in executions if e.get('status') == 'closed' and e.get('pnl') is not None]
    
    if not closed_trades:
        st.info("No completed trades to chart")
        return
    
    # Create cumulative P&L chart
    df = pd.DataFrame(closed_trades)
    df['entry_timestamp'] = pd.to_datetime(df['entry_timestamp'])
    df = df.sort_values('entry_timestamp')
    
    # Calculate cumulative P&L
    df['cumulative_pnl'] = df['pnl'].cumsum()
    
    # Create chart
    fig = go.Figure()
    
    # Add line chart
    fig.add_trace(go.Scatter(
        x=df['entry_timestamp'],
        y=df['cumulative_pnl'],
        mode='lines+markers',
        name='Cumulative P&L',
        line=dict(color='green', width=2)
    ))
    
    # Add zero line
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    
    fig.update_layout(
        title="Cumulative P&L Over Time",
        xaxis_title="Date",
        yaxis_title="P&L ($)",
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True)

def display_market_distribution(executions: list):
    """Display trade distribution by market"""
    if not executions:
        return
    
    # Count trades by market
    market_counts = {}
    market_pnl = {}
    
    for exec in executions:
        market = exec.get('market', 'unknown')
        if market not in market_counts:
            market_counts[market] = 0
            market_pnl[market] = 0
        
        market_counts[market] += 1
        if exec.get('pnl') is not None:
            market_pnl[market] += exec.get('pnl', 0)
    
    # Create pie chart for trade distribution
    fig = px.pie(
        values=list(market_counts.values()),
        names=list(market_counts.keys()),
        title="Trade Distribution by Market"
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Create bar chart for P&L by market
    fig = go.Figure(data=[
        go.Bar(
            x=list(market_pnl.keys()),
            y=list(market_pnl.values()),
            marker_color=['green' if v >= 0 else 'red' for v in market_pnl.values()]
        )
    ])
    
    fig.update_layout(
        title="P&L by Market",
        xaxis_title="Market",
        yaxis_title="P&L ($)"
    )
    
    st.plotly_chart(fig, use_container_width=True)

def main():
    """Main dashboard page"""
    st.title("📊 Your Trading Dashboard")
    
    # Sidebar for wallet connection
    with st.sidebar:
        st.header("Wallet Connection")
        
        # Wallet address input (for demo)
        user_address = st.text_input(
            "Enter your wallet address",
            placeholder="0x...",
            help="Enter the wallet address you want to track"
        )
        
        if user_address:
            st.success(f"Tracking: {user_address[:6]}...{user_address[-4:]}")
            
            # Fetch data
            with st.spinner("Loading your trading data..."):
                executions = get_user_executions(user_address)
                pnl_data = get_user_pnl(user_address)
            
            # Filters
            st.subheader("Filters")
            market_filter = st.selectbox(
                "Market",
                ["All", "polymarket", "kalshi"],
                index=0
            )
            status_filter = st.selectbox(
                "Status",
                ["All", "open", "closed"],
                index=0
            )
            
            # Apply filters
            filtered_executions = executions
            if market_filter != "All":
                filtered_executions = [e for e in filtered_executions if e.get('market') == market_filter]
            if status_filter != "All":
                filtered_executions = [e for e in filtered_executions if e.get('status') == status_filter]
            
            st.write(f"Showing {len(filtered_executions)} trades")
    
    if not user_address:
        st.warning("Please enter a wallet address to view your trading dashboard")
        st.info("""
        **How to use this dashboard:**
        
        1. Connect your wallet using MetaMask
        2. Execute trades on Polymarket or Kalshi
        3. Your trades will be automatically tracked
        4. View your P&L and trading statistics here
        
        **Note:** Make sure webhooks are properly configured for real-time tracking.
        """)
        return
    
    # Main content
    # P&L Overview
    st.header("📈 P&L Overview")
    display_pnl_overview(pnl_data)
    
    # Charts
    st.header("📊 Analytics")
    col1, col2 = st.columns(2)
    
    with col1:
        display_pnl_chart(executions)
    
    with col2:
        display_market_distribution(executions)
    
    # Recent Trades
    st.header("💼 Recent Trades")
    display_executions_table(filtered_executions)
    
    # Statistics
    if executions:
        st.header("📋 Trading Statistics")
        
        # Calculate statistics
        total_trades = len(executions)
        completed_trades = len([e for e in executions if e.get('status') == 'closed'])
        total_gas = sum(e.get('gas_cost', 0) for e in executions)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Trades", total_trades)
        
        with col2:
            st.metric("Completed", completed_trades)
        
        with col3:
            st.metric("Open Positions", total_trades - completed_trades)
        
        with col4:
            st.metric("Total Gas Spent", f"${total_gas:.4f}")
        
        # Success rate
        if completed_trades > 0:
            profitable_trades = len([
                e for e in executions 
                if e.get('status') == 'closed' and e.get('pnl', 0) > 0
            ])
            win_rate = (profitable_trades / completed_trades) * 100
            
            st.metric("Win Rate", f"{win_rate:.1f}%")

if __name__ == "__main__":
    main()
