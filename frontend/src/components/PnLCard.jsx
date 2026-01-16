import React, { useState, useEffect } from 'react';
import './PnLCard.css';

const PnLCard = ({ userId }) => {
  const [userStats, setUserStats] = useState(null);
  const [cardData, setCardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchPnLData = async () => {
      try {
        setLoading(true);
        setError(null);

        // Fetch user stats
        const statsResponse = await fetch(`http://localhost:5000/api/user/${userId}/stats`);
        if (!statsResponse.ok) throw new Error('Failed to fetch user stats');
        const stats = await statsResponse.json();
        setUserStats(stats);

        // Fetch card data
        const cardResponse = await fetch(`http://localhost:5000/api/pnl-card/${userId}/share`);
        if (!cardResponse.ok) throw new Error('Failed to fetch card data');
        const card = await cardResponse.json();
        setCardData(card);

      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    if (userId) {
      fetchPnLData();
    }
  }, [userId]);

  const handleShare = async () => {
    if (navigator.share && cardData) {
      try {
        await navigator.share({
          title: 'My P&L Card',
          text: cardData.share_text,
          url: cardData.card_url
        });
      } catch (err) {
        console.log('Share cancelled or failed:', err);
      }
    } else {
      // Fallback: copy to clipboard
      if (cardData) {
        navigator.clipboard.writeText(`${cardData.share_text} ${cardData.card_url}`);
      }
    }
  };

  const handleDownload = async () => {
    try {
      const response = await fetch(`http://localhost:5000/api/pnl-card/${userId}`);
      const data = await response.json();
      
      // Create download link
      const link = document.createElement('a');
      link.href = data.download_url;
      link.download = `pnl-card-${userId}.png`;
      link.click();
    } catch (err) {
      console.error('Download failed:', err);
    }
  };

  if (loading) {
    return (
      <div className="pnl-card loading">
        <div className="loading-spinner"></div>
        <p>Loading P&L data...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="pnl-card error">
        <div className="error-icon">⚠️</div>
        <p>Failed to fetch user stats</p>
        <p className="error-details">{error}</p>
      </div>
    );
  }

  if (!userStats || !cardData) {
    return (
      <div className="pnl-card empty">
        <p>No data available</p>
      </div>
    );
  }

  return (
    <div className="pnl-card">
      <div className="card-header">
        <div className="user-info">
          <h3>@{userId}</h3>
          <span className="timestamp">Last updated: {new Date(cardData.generated_at || userStats.last_updated).toLocaleDateString()}</span>
        </div>
        <div className="card-actions">
          <button onClick={handleShare} className="share-btn">
            📤 Share Card
          </button>
          <button onClick={handleDownload} className="download-btn">
            💾 Download
          </button>
        </div>
      </div>

      <div className="pnl-metrics">
        <div className="metric primary">
          <div className="metric-value">${userStats.total_pnl.toFixed(2)}</div>
          <div className="metric-label">Total P&L</div>
        </div>
        
        <div className="metrics-grid">
          <div className="metric">
            <div className="metric-value">{userStats.total_trades}</div>
            <div className="metric-label">Trades</div>
          </div>
          
          <div className="metric">
            <div className="metric-value">{userStats.win_rate.toFixed(1)}%</div>
            <div className="metric-label">Win Rate</div>
          </div>
          
          <div className="metric">
            <div className="metric-value">${(userStats.avg_trade_size || 0).toFixed(2)}</div>
            <div className="metric-label">Avg/Trade</div>
          </div>
        </div>
      </div>

      <div className="card-preview">
        <img src={cardData.card_url} alt="P&L Card" onError={(e) => {
          e.target.src = '/api/placeholder/400/200';
        }} />
      </div>
    </div>
  );
};

export default PnLCard;
