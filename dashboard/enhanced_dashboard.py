"""
Enhanced Dashboard with P&L Tracking System
Integrates real-time P&L tracking with arbitrage monitoring
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import requests
import os
import json
from typing import Dict, List, Optional

# Configuration
API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")
KALSHI_API = os.getenv("KALSHI_API_URL", "https://api.elections.kalshi.com/trade-api/v2")
POLYMARKET_API = os.getenv("POLYMARKET_API_URL", "https://strapi-matic.poly.market.com")
LIMITLESS_API = os.getenv("LIMITLESS_API_URL", "https://api.limitless.com")
# Manifold removed - uses play money (M$), not real crypto

# Custom CSS for consistent design
st.markdown("""
<style>
    /* Main theme colors */
    :root {
        --primary: #0001ff;
        --primary-dark: #0001cc;
        --secondary: #22d3ee;
        --success: #10b981;
        --danger: #ef4444;
        --warning: #f59e0b;
        --dark: #1e293b;
        --light: #f1f5f9;
    }
    
    /* P&L Card Styles */
    .pnl-card {
        background: linear-gradient(135deg, var(--dark) 0%, #334155 100%);
        border: 1px solid #475569;
        border-radius: 12px;
        padding: 20px;
        margin: 10px 0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
        transition: all 0.3s ease;
        cursor: pointer;
    }
    
    .pnl-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.4);
        border-color: var(--primary);
    }
    
    .pnl-positive {
        border-left: 4px solid var(--success);
    }
    
    .pnl-negative {
        border-left: 4px solid var(--danger);
    }
    
    .pnl-neutral {
        border-left: 4px solid var(--warning);
    }
    
    .pnl-value {
        font-size: 2rem;
        font-weight: bold;
        margin: 10px 0;
    }
    
    .pnl-positive .pnl-value {
        color: var(--success);
    }
    
    .pnl-negative .pnl-value {
        color: var(--danger);
    }
    
    .pnl-neutral .pnl-value {
        color: var(--warning);
    }
    
    /* Modal Styles */
    .modal {
        display: none;
        position: fixed;
        z-index: 9999;
        left: 0;
        top: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0,0,0,0.8);
        backdrop-filter: blur(5px);
    }
    
    .modal-content {
        background: var(--dark);
        margin: 5% auto;
        padding: 30px;
        border: 1px solid #475569;
        border-radius: 12px;
        width: 80%;
        max-width: 800px;
        max-height: 80vh;
        overflow-y: auto;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
    }
    
    .close {
        color: #aaa;
        float: right;
        font-size: 28px;
        font-weight: bold;
        cursor: pointer;
    }
    
    .close:hover {
        color: white;
    }
    
    /* Tab Styles */
    .stTabs [data-baseweb="tab-list"] {
        background-color: var(--dark);
        border-radius: 8px;
        padding: 5px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        color: #94a3b8;
        border-radius: 6px;
        padding: 10px 20px;
        font-weight: 500;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: var(--primary);
        color: white;
    }
    
    /* Metric Cards */
    div[data-testid="metric-container"] {
        background-color: var(--dark);
        border: 1px solid #475569;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    
    div[data-testid="metric-container"] > div:first-child {
        color: #94a3b8;
    }
    
    div[data-testid="metric-container"] > div:last-child {
        color: white;
    }
</style>
""", unsafe_allow_html=True)

def get_user_executions(user_address: str, market: str = None, status: str = None, limit: int = 100):
    """Fetch user's execution history"""
    try:
        params = {"limit": limit}
        if market:
            params["market"] = market
        if status:
            params["status"] = status
        
        response = requests.get(f"{API_BASE}/api/executions/{user_address}", params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        st.error(f"Error fetching executions: {e}")
        return []

def get_user_pnl(user_address: str):
    """Fetch user's P&L summary"""
    try:
        response = requests.get(f"{API_BASE}/api/pnl/{user_address}", timeout=10)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        st.error(f"Error fetching P&L: {e}")
        return []

def get_leaderboard(limit: int = 20):
    """Fetch leaderboard data"""
    try:
        response = requests.get(f"{API_BASE}/api/leaderboard?limit={limit}", timeout=10)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        st.error(f"Error fetching leaderboard: {e}")
        return []

def format_currency(amount: float, show_sign: bool = True) -> str:
    """Format currency with color coding"""
    if amount >= 0:
        return f"${amount:,.2f}" if not show_sign else f"+${amount:,.2f}"
    else:
        return f"-${abs(amount):,.2f}"

def get_pnl_class(pnl: float) -> str:
    """Get CSS class for P&L value"""
    if pnl > 0:
        return "pnl-positive"
    elif pnl < 0:
        return "pnl-negative"
    else:
        return "pnl-neutral"

def display_pnl_overview(pnl_data: list, user_address: str = None):
    """Display P&L overview cards with click to expand"""
    if not pnl_data:
        st.info("No P&L data available. Connect your wallet to start tracking trades.")
        return
    
    # Calculate total P&L across all markets
    total_pnl = sum(market.get('total_pnl', 0) for market in pnl_data)
    total_trades = sum(market.get('completed_trades', 0) for market in pnl_data)
    total_gas = sum(market.get('total_gas_spent', 0) for market in pnl_data)
    
    # Main P&L Card
    pnl_class = get_pnl_class(total_pnl)
    
    st.markdown(f"""
    <div class="pnl-card {pnl_class}" onclick="openPnLModal()">
        <h3 style="color: white; margin: 0 0 10px 0;">💰 Total P&L</h3>
        <div class="pnl-value">{format_currency(total_pnl)}</div>
        <div style="color: #94a3b8; font-size: 0.9rem;">
            {total_trades} completed trades • ${total_gas:.4f} in gas fees
        </div>
        <div style="color: #64748b; font-size: 0.8rem; margin-top: 10px;">
            Click to view detailed breakdown →
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Market breakdown cards
    cols = st.columns(len(pnl_data))
    for i, market in enumerate(pnl_data):
        with cols[i]:
            market_pnl = market.get('total_pnl', 0)
            market_class = get_pnl_class(market_pnl)
            
            st.markdown(f"""
            <div class="pnl-card {market_class}" style="padding: 15px;">
                <h4 style="color: white; margin: 0;">{market['market'].upper()}</h4>
                <div style="font-size: 1.2rem; font-weight: bold; margin: 5px 0;">
                    {format_currency(market_pnl)}
                </div>
                <div style="color: #94a3b8; font-size: 0.8rem;">
                    {market.get('completed_trades', 0)} trades
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # Modal for detailed P&L (JavaScript)
    st.markdown("""
    <div id="pnlModal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="closePnLModal()">&times;</span>
            <h2 style="color: white;">📊 Detailed P&L Breakdown</h2>
            <div id="pnlModalContent"></div>
        </div>
    </div>
    
    <script>
        function openPnLModal() {
            document.getElementById('pnlModal').style.display = 'block';
            // Load detailed P&L data
            loadPnLDetails();
        }
        
        function closePnLModal() {
            document.getElementById('pnlModal').style.display = 'none';
        }
        
        function loadPnLDetails() {
            // This would make an API call to get detailed P&L data
            document.getElementById('pnlModalContent').innerHTML = `
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 20px 0;">
                    <div style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px; border: 1px solid #475569;">
                        <h4 style="color: white; margin: 0 0 10px 0;">📈 Performance Metrics</h4>
                        <div style="color: #94a3b8; margin: 5px 0;">Total P&L: <span style="color: #10b981; font-weight: bold;">+$2,456.78</span></div>
                        <div style="color: #94a3b8; margin: 5px 0;">Win Rate: <span style="color: #22d3ee; font-weight: bold;">67.5%</span></div>
                        <div style="color: #94a3b8; margin: 5px 0;">Average Trade Size: <span style="color: #f59e0b; font-weight: bold;">$156.32</span></div>
                    </div>
                    <div style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px; border: 1px solid #475569;">
                        <h4 style="color: white; margin: 0 0 10px 0;">📊 Trading Stats</h4>
                        <div style="color: #94a3b8; margin: 5px 0;">Total Trades: <span style="color: white; font-weight: bold;">142</span></div>
                        <div style="color: #94a3b8; margin: 5px 0;">Winning Trades: <span style="color: #10b981; font-weight: bold;">96</span></div>
                        <div style="color: #94a3b8; margin: 5px 0;">Losing Trades: <span style="color: #ef4444; font-weight: bold;">46</span></div>
                    </div>
                </div>
                <div style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px; border: 1px solid #475569; margin: 20px 0;">
                    <h4 style="color: white; margin: 0 0 10px 0;">🎯 Market Breakdown</h4>
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px;">
                        <div style="text-align: center; padding: 10px; background: rgba(0,1,255,0.1); border-radius: 6px;">
                            <div style="color: white; font-weight: bold;">LIMITLESS</div>
                            <div style="color: #10b981;">+$1,234.56</div>
                            <div style="color: #94a3b8; font-size: 0.8rem;">48 trades</div>
                        </div>
                        <div style="text-align: center; padding: 10px; background: rgba(0,1,255,0.1); border-radius: 6px;">
                            <div style="color: white; font-weight: bold;">POLYMARKET</div>
                            <div style="color: #ef4444;">-$332.00</div>
                            <div style="color: #94a3b8; font-size: 0.8rem;">57 trades</div>
                        </div>
                        <div style="text-align: center; padding: 10px; background: rgba(0,1,255,0.1); border-radius: 6px;">
                            <div style="color: white; font-weight: bold;">AZURO</div>
                            <div style="color: #10b981;">+$567.89</div>
                            <div style="color: #94a3b8; font-size: 0.8rem;">31 trades</div>
                        </div>
                    </div>
                </div>
            `;
        }
        
        // Close modal when clicking outside
        window.onclick = function(event) {
            const modal = document.getElementById('pnlModal');
            if (event.target == modal) {
                modal.style.display = 'none';
            }
        }
    </script>
    """, unsafe_allow_html=True)

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
        line=dict(color='#10b981', width=3),
        marker=dict(size=6)
    ))
    
    # Add zero line
    fig.add_hline(y=0, line_dash="dash", line_color="#64748b")
    
    # Color areas
    fig.add_trace(go.Scatter(
        x=df['entry_timestamp'],
        y=[0] * len(df),
        fill='tonexty',
        fillcolor='rgba(16, 185, 129, 0.1)',
        line=dict(color='rgba(0,0,0,0)'),
        showlegend=False
    ))
    
    fig.update_layout(
        title="💰 Cumulative P&L Over Time",
        xaxis_title="Date",
        yaxis_title="P&L ($)",
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color="white"),
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True)

def display_recent_trades(executions: list, limit: int = 10):
    """Display recent trades in a compact format"""
    if not executions:
        st.info("No trades found")
        return
    
    # Show recent trades
    recent_trades = executions[:limit]
    
    for trade in recent_trades:
        pnl = trade.get('pnl', 0)
        pnl_class = get_pnl_class(pnl)
        
        with st.container():
            col1, col2, col3, col4, col5 = st.columns([2, 2, 1, 1, 1])
            
            with col1:
                st.write(f"**{trade.get('market', '').upper()}**")
                st.caption(trade.get('market_ticker', ''))
            
            with col2:
                st.write(f"{trade.get('side', '').upper()}")
                st.caption(f"@ ${trade.get('entry_price', 0):.4f}")
            
            with col3:
                if trade.get('status') == 'closed':
                    st.write(format_currency(pnl, False))
                else:
                    st.write("Open")
            
            with col4:
                st.write(f"{trade.get('quantity', 0)}")
            
            with col5:
                ts = pd.to_datetime(trade.get('entry_timestamp'))
                st.write(ts.strftime('%H:%M'))
            
            st.divider()

def display_leaderboard_tab():
    """Display leaderboard in a dedicated tab"""
    st.header("🏆 Trading Leaderboard")
    
    # Time period selector
    col1, col2 = st.columns([1, 3])
    with col1:
        period = st.selectbox(
            "Time Period",
            ["All Time", "This Week", "Today"],
            index=0
        )
    
    # Fetch leaderboard data
    leaderboard = get_leaderboard(limit=50)
    
    if not leaderboard:
        st.info("No leaderboard data available")
        return
    
    # Create leaderboard table
    df = pd.DataFrame(leaderboard)
    
    # Format data
    df['rank'] = range(1, len(df) + 1)
    df['total_pnl_formatted'] = df['total_pnl'].apply(lambda x: format_currency(x))
    df['win_rate'] = ((df['winning_trades'] / df['total_trades']) * 100).round(1)
    
    # Add rank badges
    def get_rank_badge(rank):
        if rank == 1:
            return "🥇"
        elif rank == 2:
            return "🥈"
        elif rank == 3:
            return "🥉"
        else:
            return f"#{rank}"
    
    df['rank_badge'] = df['rank'].apply(get_rank_badge)
    
    # Display top 3 with special styling
    top_traders = df.head(3)
    
    for _, trader in top_traders.iterrows():
        col1, col2, col3, col4, col5 = st.columns([1, 2, 2, 2, 2])
        
        with col1:
            st.markdown(f"<h1 style='text-align: center; margin: 0;'>{trader['rank_badge']}</h1>", unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"<h4 style='margin: 0;'>{trader['user_address'][:8]}...{trader['user_address'][-6:]}</h4>", unsafe_allow_html=True)
            st.caption(f"{trader['total_trades']} trades")
        
        with col3:
            st.markdown(f"<h3 style='color: #10b981; margin: 0;'>{trader['total_pnl_formatted']}</h3>", unsafe_allow_html=True)
        
        with col4:
            st.metric("Win Rate", f"{trader['win_rate']}%")
        
        with col5:
            st.metric("Avg/Trade", f"${trader['avg_pnl_per_trade']:.2f}")
        
        st.divider()
    
    # Show rest of leaderboard
    if len(df) > 3:
        st.subheader(f"Rank 4-{len(df)}")
        rest_df = df.iloc[3:].reset_index(drop=True)
        rest_df['rank'] = range(4, len(rest_df) + 4)
        
        st.dataframe(
            rest_df[['rank', 'user_address', 'total_pnl_formatted', 'total_trades', 'win_rate', 'avg_pnl_per_trade']],
            column_config={
                "rank": "Rank",
                "user_address": "Trader",
                "total_pnl_formatted": "Total P&L",
                "total_trades": "Trades",
                "win_rate": "Win Rate %",
                "avg_pnl_per_trade": "Avg/Trade"
            },
            hide_index=True,
            use_container_width=True
        )

def main():
    """Main dashboard with tabs"""
    st.set_page_config(
        page_title="Limitless & Manifold Trading Dashboard",
        page_icon="💰",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Sidebar for wallet connection
    with st.sidebar:
        st.header("🔗 Wallet Connection")
        
        # Wallet address input
        user_address = st.text_input(
            "Your Wallet Address",
            placeholder="0x...",
            help="Enter your wallet address to track P&L"
        )
        
        if user_address:
            st.success(f"Connected: {user_address[:6]}...{user_address[-4:]}")
            
            # Quick stats
            with st.spinner("Loading your data..."):
                executions = get_user_executions(user_address, limit=50)
                pnl_data = get_user_pnl(user_address)
            
            # Quick metrics
            if executions:
                total_trades = len(executions)
                open_positions = len([e for e in executions if e.get('status') == 'open'])
                completed = len([e for e in executions if e.get('status') == 'closed'])
                
                st.metric("Total Trades", total_trades)
                st.metric("Open Positions", open_positions)
                st.metric("Completed", completed)
    
    # Main content with tabs
    tab1, tab2, tab3 = st.tabs([
        "🎯 Limitless",
        "💰 P&L Tracking", 
        "🏆 Leaderboard"
    ])
    
    with tab1:
        st.header("🎯 Limitless Markets")
        st.info("Limitless trading opportunities will appear here when detected")
        # Limitless-specific content would go here
    
    with tab2:
        st.header("💰 Your P&L")
        
        if not user_address:
            st.warning("Please connect your wallet to view P&L data")
        else:
            # P&L Overview
            display_pnl_overview(pnl_data, user_address)
            
            # Recent trades
            st.subheader("📈 Recent Trades")
            display_recent_trades(executions)
            
            # P&L Chart
            if executions:
                st.subheader("📊 P&L Chart")
                display_pnl_chart(executions)
    
    with tab4:
        display_leaderboard_tab()

if __name__ == "__main__":
    main()
