-- Migration 001: Initial Schema
-- P&L Tracking Database Schema

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create executions table for tracking trades
CREATE TABLE IF NOT EXISTS executions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id TEXT NOT NULL,
    market TEXT NOT NULL,
    market_ticker TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('yes', 'no')),
    entry_price DECIMAL(10, 4) NOT NULL,
    exit_price DECIMAL(10, 4),
    quantity INTEGER NOT NULL DEFAULT 1,
    entry_tx_hash TEXT,
    exit_tx_hash TEXT,
    entry_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    exit_timestamp TIMESTAMP WITH TIME ZONE,
    gas_cost DECIMAL(10, 6) DEFAULT 0,
    status TEXT DEFAULT 'open' CHECK (status IN ('open', 'closed', 'cancelled')),
    pnl DECIMAL(10, 2), -- calculated profit/loss
    alert_id UUID,
    alert_spread DECIMAL(10, 4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create arbitrage_alerts table
CREATE TABLE IF NOT EXISTS arbitrage_alerts (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id TEXT NOT NULL,
    market TEXT NOT NULL,
    ticker TEXT NOT NULL,
    spread DECIMAL(10, 4) NOT NULL,
    yes_price DECIMAL(10, 4),
    no_price DECIMAL(10, 4),
    market_data JSONB,
    confidence_score DECIMAL(3, 2) DEFAULT 1.0,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'executed', 'expired')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    executed_at TIMESTAMP WITH TIME ZONE,
    execution_id UUID REFERENCES executions(id)
);

-- Create leaderboard table
CREATE TABLE IF NOT EXISTS leaderboard (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id TEXT NOT NULL UNIQUE,
    username TEXT,
    avatar_url TEXT,
    total_pnl DECIMAL(12, 2) DEFAULT 0,
    total_trades INTEGER DEFAULT 0,
    win_rate DECIMAL(5, 2) DEFAULT 0,
    total_volume DECIMAL(15, 2) DEFAULT 0,
    best_trade DECIMAL(10, 2),
    worst_trade DECIMAL(10, 2),
    current_streak INTEGER DEFAULT 0,
    best_streak INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create webhook_logs table
CREATE TABLE IF NOT EXISTS webhook_logs (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    webhook_id TEXT NOT NULL,
    transaction_data JSONB,
    status TEXT DEFAULT 'received' CHECK (status IN ('received', 'processed', 'error')),
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE
);

-- Create webhook_queue table
CREATE TABLE IF NOT EXISTS webhook_queue (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    tx_hash TEXT NOT NULL,
    user_id TEXT NOT NULL,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processed', 'failed')),
    processed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create pnl_cards table for tracking generated cards
CREATE TABLE IF NOT EXISTS pnl_cards (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id TEXT NOT NULL,
    card_url TEXT,
    card_data JSONB,
    period TEXT NOT NULL CHECK (period IN ('daily', 'weekly', 'monthly')),
    total_pnl DECIMAL(10, 2),
    total_trades INTEGER,
    win_rate DECIMAL(5, 2),
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
