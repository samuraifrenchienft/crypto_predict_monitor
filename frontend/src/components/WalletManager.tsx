"""
Client-side wallet connection and webhook management
Handles MetaMask connection and creates Alchemy webhooks for trade tracking
"""

import { useState, useEffect } from 'react';
import { ethers } from 'ethers';
import axios from 'axios';

const ALCHEMY_API_KEY = process.env.NEXT_PUBLIC_ALCHEMY_API_KEY;
const WEBHOOK_URL = process.env.NEXT_PUBLIC_WEBHOOK_URL || 'https://your-domain.com/api/webhooks/wallet-activity';

export interface WalletState {
  address: string | null;
  isConnected: boolean;
  provider: ethers.BrowserProvider | null;
  signer: ethers.JsonRpcSigner | null;
  webhookId: string | null;
  isLoading: boolean;
  error: string | null;
}

export interface Execution {
  id: string;
  market: 'polymarket' | 'kalshi';
  market_ticker: string;
  side: 'yes' | 'no';
  entry_price: number;
  exit_price: number | null;
  quantity: number;
  entry_tx_hash: string;
  exit_tx_hash: string | null;
  pnl: number | null;
  gas_cost: number;
  entry_timestamp: string;
  exit_timestamp: string | null;
  status: 'open' | 'closed';
}

export interface PnLSummary {
  user_id: string;
  market: string;
  total_trades: number;
  completed_trades: number;
  total_pnl: number;
  avg_pnl_per_trade: number;
  best_trade: number;
  worst_trade: number;
  total_gas_spent: number;
  last_trade_time: string;
}

class WalletManager {
  private state: WalletState;
  private setState: React.Dispatch<React.SetStateAction<WalletState>>;
  private eventListeners: Map<string, Function> = new Map();

  constructor(setState: React.Dispatch<React.SetStateAction<WalletState>>) {
    this.state = {
      address: null,
      isConnected: false,
      provider: null,
      signer: null,
      webhookId: null,
      isLoading: false,
      error: null
    };
    this.setState = setState;
  }

  // Connect to MetaMask
  async connectWallet(): Promise<boolean> {
    this.setState(prev => ({ ...prev, isLoading: true, error: null }));
    
    try {
      if (!window.ethereum) {
        throw new Error('MetaMask is not installed');
      }

      // Request account access
      await window.ethereum.request({
        method: 'eth_requestAccounts'
      });

      const provider = new ethers.BrowserProvider(window.ethereum);
      const signer = await provider.getSigner();
      const address = await signer.getAddress();

      this.setState({
        address,
        isConnected: true,
        provider,
        signer,
        isLoading: false,
        error: null
      });

      // Create webhook for this address
      await this.createWebhook(address);

      return true;
    } catch (error) {
      this.setState({
        isLoading: false,
        error: error instanceof Error ? error.message : 'Failed to connect wallet'
      });
      return false;
    }
  }

  // Disconnect wallet
  disconnectWallet() {
    this.setState({
      address: null,
      isConnected: false,
      provider: null,
      signer: null,
      webhookId: null,
      isLoading: false,
      error: null
    });

    // Remove event listeners
    this.eventListeners.clear();
  }

  // Create Alchemy webhook for address monitoring
  private async createWebhook(address: string): Promise<void> {
    try {
      const response = await axios.post('/api/webhooks/create', {
        user_id: address,
        wallet_address: address
      });

      const { webhook_id } = response.data;
      
      this.setState(prev => ({ ...prev, webhookId: webhook_id }));
      
      console.log(`Webhook created for ${address}: ${webhook_id}`);
    } catch (error) {
      console.error('Failed to create webhook:', error);
      // Don't throw error - wallet can still work without webhook
    }
  }

  // Get user's execution history
  async getExecutions(market?: 'polymarket' | 'kalshi', status?: 'open' | 'closed'): Promise<Execution[]> {
    if (!this.state.address) return [];

    try {
      const params = new URLSearchParams();
      if (market) params.append('market', market);
      if (status) params.append('status', status);

      const response = await axios.get(`/api/executions/${this.state.address}?${params}`);
      return response.data;
    } catch (error) {
      console.error('Failed to fetch executions:', error);
      return [];
    }
  }

  // Get user's P&L summary
  async getPnLSummary(): Promise<PnLSummary[]> {
    if (!this.state.address) return [];

    try {
      const response = await axios.get(`/api/pnl/${this.state.address}`);
      return response.data;
    } catch (error) {
      console.error('Failed to fetch P&L summary:', error);
      return [];
    }
  }

  // Get current state
  getState(): WalletState {
    return { ...this.state };
  }
}

// React Hook for wallet management
export function useWalletManager() {
  const [state, setState] = useState<WalletState>({
    address: null,
    isConnected: false,
    provider: null,
    signer: null,
    webhookId: null,
    isLoading: false,
    error: null
  });

  const walletManager = new WalletManager(setState);

  // Auto-connect if previously connected
  useEffect(() => {
    const checkConnection = async () => {
      if (window.ethereum) {
        try {
          const provider = new ethers.BrowserProvider(window.ethereum);
          const accounts = await provider.send('eth_accounts', []);
          
          if (accounts.length > 0) {
            await walletManager.connectWallet();
          }
        } catch (error) {
          console.error('Auto-connection failed:', error);
        }
      }
    };

    checkConnection();
  }, []);

  // Listen for account changes
  useEffect(() => {
    if (window.ethereum) {
      const handleAccountsChanged = (accounts: string[]) => {
        if (accounts.length === 0) {
          walletManager.disconnectWallet();
        } else if (accounts[0] !== state.address) {
          walletManager.connectWallet();
        }
      };

      window.ethereum.on('accountsChanged', handleAccountsChanged);

      return () => {
        window.ethereum.removeListener('accountsChanged', handleAccountsChanged);
      };
    }
  }, [state.address]);

  return {
    ...state,
    connectWallet: () => walletManager.connectWallet(),
    disconnectWallet: () => walletManager.disconnectWallet(),
    getExecutions: (market?: 'polymarket' | 'kalshi', status?: 'open' | 'closed') => 
      walletManager.getExecutions(market, status),
    getPnLSummary: () => walletManager.getPnLSummary()
  };
}

// React component for wallet connection UI
export function WalletConnector({ onConnect }: { onConnect?: (address: string) => void }) {
  const {
    address,
    isConnected,
    isLoading,
    error,
    connectWallet,
    disconnectWallet,
    webhookId
  } = useWalletManager();

  useEffect(() => {
    if (isConnected && address && onConnect) {
      onConnect(address);
    }
  }, [isConnected, address, onConnect]);

  if (isConnected && address) {
    return (
      <div className="wallet-connected">
        <div className="wallet-info">
          <span className="address">
            {address.slice(0, 6)}...{address.slice(-4)}
          </span>
          {webhookId && (
            <span className="webhook-status" title={`Webhook ID: ${webhookId}`}>
              ✓ Tracking Active
            </span>
          )}
        </div>
        <button onClick={disconnectWallet} className="disconnect-btn">
          Disconnect
        </button>
      </div>
    );
  }

  return (
    <div className="wallet-connector">
      {error && <div className="error">{error}</div>}
      <button 
        onClick={connectWallet} 
        disabled={isLoading}
        className="connect-btn"
      >
        {isLoading ? 'Connecting...' : 'Connect Wallet'}
      </button>
    </div>
  );
}

// Component to display user's P&L
export function UserPnLDisplay({ userId }: { userId: string }) {
  const [pnlData, setPnlData] = useState<PnLSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const { getExecutions } = useWalletManager();

  useEffect(() => {
    const fetchData = async () => {
      try {
        const executions = await getExecutions();
        // Calculate P&L from executions
        const pnlByMarket = executions.reduce((acc, exec) => {
          if (!acc[exec.market]) {
            acc[exec.market] = {
              user_id: userId,
              market: exec.market,
              total_trades: 0,
              completed_trades: 0,
              total_pnl: 0,
              avg_pnl_per_trade: 0,
              best_trade: -Infinity,
              worst_trade: Infinity,
              total_gas_spent: 0,
              last_trade_time: ''
            };
          }
          
          const market = acc[exec.market];
          market.total_trades++;
          
          if (exec.status === 'closed' && exec.pnl !== null) {
            market.completed_trades++;
            market.total_pnl += exec.pnl;
            market.best_trade = Math.max(market.best_trade, exec.pnl);
            market.worst_trade = Math.min(market.worst_trade, exec.pnl);
          }
          
          market.total_gas_spent += exec.gas_cost;
          
          return acc;
        }, {} as Record<string, PnLSummary>);

        // Calculate averages
        Object.values(pnlByMarket).forEach(market => {
          if (market.completed_trades > 0) {
            market.avg_pnl_per_trade = market.total_pnl / market.completed_trades;
          }
          if (market.best_trade === -Infinity) market.best_trade = 0;
          if (market.worst_trade === Infinity) market.worst_trade = 0;
        });

        setPnlData(Object.values(pnlByMarket));
      } catch (error) {
        console.error('Failed to fetch P&L data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [userId, getExecutions]);

  if (loading) return <div>Loading P&L data...</div>;

  return (
    <div className="pnl-display">
      <h3>Your Trading Performance</h3>
      {pnlData.map(market => (
        <div key={market.market} className="market-pnl">
          <h4>{market.market.toUpperCase()}</h4>
          <div className="pnl-stats">
            <div className="stat">
              <span>Total P&L:</span>
              <span className={market.total_pnl >= 0 ? 'positive' : 'negative'}>
                ${market.total_pnl.toFixed(2)}
              </span>
            </div>
            <div className="stat">
              <span>Completed Trades:</span>
              <span>{market.completed_trades}</span>
            </div>
            <div className="stat">
              <span>Avg P&L per Trade:</span>
              <span className={market.avg_pnl_per_trade >= 0 ? 'positive' : 'negative'}>
                ${market.avg_pnl_per_trade.toFixed(2)}
              </span>
            </div>
            <div className="stat">
              <span>Best Trade:</span>
              <span className="positive">${market.best_trade.toFixed(2)}</span>
            </div>
            <div className="stat">
              <span>Gas Spent:</span>
              <span>${market.total_gas_spent.toFixed(4)}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
