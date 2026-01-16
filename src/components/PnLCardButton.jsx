"""
P&L Card Button - React Component
UI component for generating and sharing P&L cards
"""

import React, { useState } from 'react';
import { Download, Share2, Twitter, MessageCircle, Copy, Loader2 } from 'lucide-react';

const PnLCardButton = ({ userId, currentPnL, predictions }) => {
  const [isGenerating, setIsGenerating] = useState(false);
  const [cardUrl, setCardUrl] = useState(null);
  const [shareData, setShareData] = useState(null);
  const [error, setError] = useState(null);

  const generateCard = async () => {
    setIsGenerating(true);
    setError(null);
    
    try {
      // Generate card
      const response = await fetch(`/api/pnl-card/${userId}/share`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('Failed to generate card');
      }

      const data = await response.json();
      setShareData(data);
      
      // Generate card URL for download
      const cardResponse = await fetch(`/api/pnl-card/${userId}`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (cardResponse.ok) {
        const blob = await cardResponse.blob();
        const url = URL.createObjectURL(blob);
        setCardUrl(url);
      }
      
    } catch (err) {
      setError(err.message);
    } finally {
      setIsGenerating(false);
    }
  };

  const downloadCard = () => {
    if (!cardUrl) return;
    
    const link = document.createElement('a');
    link.href = cardUrl;
    link.download = `pnl_${userId}_${new Date().toISOString().split('T')[0]}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const shareToTwitter = () => {
    if (!shareData) return;
    
    const text = encodeURIComponent(shareData.share_text);
    const url = `https://twitter.com/intent/tweet?text=${text}`;
    window.open(url, '_blank', 'width=550,height=420');
  };

  const shareToDiscord = () => {
    if (!cardUrl) return;
    
    // Copy card to clipboard for Discord
    fetch(cardUrl)
      .then(res => res.blob())
      .then(blob => {
        const item = new ClipboardItem({ 'image/png': blob });
        navigator.clipboard.write([item]);
        alert('Card copied to clipboard! Paste in Discord to share.');
      })
      .catch(() => {
        alert('Failed to copy card. Please download and share manually.');
      });
  };

  const copyShareText = () => {
    if (!shareData) return;
    
    navigator.clipboard.writeText(shareData.share_text);
    alert('Share text copied to clipboard!');
  };

  if (isGenerating) {
    return (
      <div className="flex flex-col items-center p-6 bg-gray-900 rounded-lg border border-blue-500">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin mb-4" />
        <p className="text-gray-300">Generating your P&L card...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 bg-gray-900 rounded-lg border border-red-500">
        <p className="text-red-400 mb-4">Error: {error}</p>
        <button
          onClick={generateCard}
          className="w-full bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium transition"
        >
          Try Again
        </button>
      </div>
    );
  }

  if (shareData && cardUrl) {
    return (
      <div className="p-6 bg-gray-900 rounded-lg border border-blue-500">
        <h3 className="text-xl font-bold text-white mb-4">Your P&L Card is Ready!</h3>
        
        {/* Card Preview */}
        <div className="mb-6 flex justify-center">
          <img 
            src={cardUrl} 
            alt="P&L Card" 
            className="max-w-full h-auto rounded-lg shadow-lg border border-blue-400"
            style={{ maxHeight: '400px' }}
          />
        </div>

        {/* Stats Summary */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="text-center">
            <p className="text-gray-400 text-sm">P&L</p>
            <p className={`text-lg font-bold ${shareData.pnl_percentage >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {shareData.pnl_percentage >= 0 ? '+' : ''}{shareData.pnl_percentage.toFixed(2)}%
            </p>
          </div>
          <div className="text-center">
            <p className="text-gray-400 text-sm">Win Rate</p>
            <p className="text-lg font-bold text-blue-400">{shareData.win_rate.toFixed(0)}%</p>
          </div>
          <div className="text-center">
            <p className="text-gray-400 text-sm">Trades</p>
            <p className="text-lg font-bold text-blue-400">{shareData.trades}</p>
          </div>
          <div className="text-center">
            <p className="text-gray-400 text-sm">Period</p>
            <p className="text-lg font-bold text-blue-400 capitalize">{shareData.period}</p>
          </div>
        </div>

        {/* Share Buttons */}
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={downloadCard}
              className="flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-3 rounded-lg font-medium transition"
            >
              <Download className="w-5 h-5" />
              Download
            </button>
            
            <button
              onClick={shareToTwitter}
              className="flex items-center justify-center gap-2 bg-sky-500 hover:bg-sky-600 text-white px-4 py-3 rounded-lg font-medium transition"
            >
              <Twitter className="w-5 h-5" />
              Twitter
            </button>
            
            <button
              onClick={shareToDiscord}
              className="flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-3 rounded-lg font-medium transition"
            >
              <MessageCircle className="w-5 h-5" />
              Discord
            </button>
            
            <button
              onClick={copyShareText}
              className="flex items-center justify-center gap-2 bg-gray-700 hover:bg-gray-600 text-white px-4 py-3 rounded-lg font-medium transition"
            >
              <Copy className="w-5 h-5" />
              Copy Text
            </button>
          </div>

          {/* Share Text Preview */}
          <div className="p-3 bg-gray-800 rounded-lg border border-gray-700">
            <p className="text-gray-300 text-sm mb-2">Share text:</p>
            <p className="text-gray-400 text-xs italic">"{shareData.share_text}"</p>
          </div>
        </div>

        <button
          onClick={() => {
            setCardUrl(null);
            setShareData(null);
          }}
          className="w-full mt-4 bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-lg font-medium transition"
        >
          Generate New Card
        </button>
      </div>
    );
  }

  // Initial state - show generate button
  return (
    <div className="p-6 bg-gray-900 rounded-lg border border-blue-500">
      <h3 className="text-lg font-semibold text-white mb-4">Share Your Trading Stats</h3>
      <p className="text-gray-400 mb-6">
        Create a viral-ready P&L card to share your trading performance on social media.
        Features your recent predictions, win rate, and total P&L with a sleek blue design.
      </p>
      
      <button
        onClick={generateCard}
        className="w-full bg-[#0001ff] hover:bg-[#0001ff] text-white px-6 py-3 rounded-lg font-medium transition flex items-center justify-center gap-2 neon-glow"
      >
        <Share2 className="w-5 h-5" />
        Generate P&L Card
      </button>
      
      <div className="mt-4 text-center">
        <p className="text-gray-500 text-sm">
          📱 Perfect for Instagram Stories, Twitter, and Discord
        </p>
      </div>
    </div>
  );
};

export default PnLCardButton;
