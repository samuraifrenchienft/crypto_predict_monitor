-- Supabase Database Schema for P&L Tracking System
-- Run this in your Supabase SQL Editor

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create executions table for tracking trades
CREATE TABLE IF NOT EXISTS executions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id TEXT NOT NULL,
    market TEXT NOT NULL,
    market_ticker TEXT NOT NULL,
    side TEXT NOT NULL, -- 'yes' or 'no'
    entry_price DECIMAL(10, 4),
    exit_price DECIMAL(10, 4),
    quantity INTEGER,
    entry_tx_hash TEXT,
    exit_tx_hash TEXT,
    entry_timestamp TIMESTAMP WITH TIME ZONE,
    exit_timestamp TIMESTAMP WITH TIME ZONE,
    gas_cost DECIMAL(10, 6) DEFAULT 0,
    status TEXT DEFAULT 'open', -- 'open', 'closed'
    pnl DECIMAL(10, 2), -- calculated profit/loss
    alert_id UUID REFERENCES arbitrage_alerts(id),
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
    status TEXT DEFAULT 'active', -- 'active', 'executed', 'expired'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    executed_at TIMESTAMP WITH TIME ZONE,
    execution_id UUID REFERENCES executions(id)
);

-- Create leaderboard table
CREATE TABLE IF NOT EXISTS leaderboard (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id TEXT NOT NULL UNIQUE,
    total_pnl DECIMAL(12, 2) DEFAULT 0,
    total_trades INTEGER DEFAULT 0,
    win_rate DECIMAL(5, 2) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create webhook_logs table
CREATE TABLE IF NOT EXISTS webhook_logs (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    webhook_id TEXT NOT NULL,
    transaction_data JSONB,
    status TEXT DEFAULT 'received', -- 'received', 'processed', 'error'
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE
);

-- Create webhook_queue table
CREATE TABLE IF NOT EXISTS webhook_queue (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    tx_hash TEXT NOT NULL,
    user_id TEXT NOT NULL,
    status TEXT DEFAULT 'pending', -- 'pending', 'processed'
    processed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_executions_user_id ON executions(user_id);
CREATE INDEX IF NOT EXISTS idx_executions_status ON executions(status);
CREATE INDEX IF NOT EXISTS idx_executions_market ON executions(market);
CREATE INDEX IF NOT EXISTS idx_arbitrage_alerts_user_id ON arbitrage_alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_arbitrage_alerts_status ON arbitrage_alerts(status);
CREATE INDEX IF NOT EXISTS idx_leaderboard_user_id ON leaderboard(user_id);
CREATE INDEX IF NOT EXISTS idx_webhook_logs_webhook_id ON webhook_logs(webhook_id);

-- Enable Row Level Security (RLS)
ALTER TABLE executions ENABLE ROW LEVEL SECURITY;
ALTER TABLE arbitrage_alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE leaderboard ENABLE ROW LEVEL SECURITY;

-- Create RLS policies (allow all for now - tighten in production)
CREATE POLICY "Enable all operations on executions" ON executions FOR ALL USING (true);
CREATE POLICY "Enable all operations on arbitrage_alerts" ON arbitrage_alerts FOR ALL USING (true);
CREATE POLICY "Enable all operations on leaderboard" ON leaderboard FOR ALL USING (true);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_executions_updated_at BEFORE UPDATE ON executions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_leaderboard_updated_at BEFORE UPDATE ON leaderboard FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
