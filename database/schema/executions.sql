-- Database schema for tracking user executions
-- Run this in Supabase SQL editor

-- Create executions table (combined for both markets)
CREATE TABLE IF NOT EXISTS executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    market TEXT NOT NULL CHECK (market IN ('polymarket', 'kalshi')),
    market_ticker TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('yes', 'no')),
    entry_price DECIMAL(10, 4) NOT NULL,
    exit_price DECIMAL(10, 4), -- null until exit
    quantity INTEGER NOT NULL,
    entry_tx_hash TEXT NOT NULL,
    exit_tx_hash TEXT,
    pnl DECIMAL(15, 4) GENERATED ALWAYS AS (
        CASE 
            WHEN exit_price IS NOT NULL THEN 
                (exit_price - entry_price) * quantity - COALESCE(gas_cost, 0)
            ELSE NULL 
        END
    ) STORED,
    gas_cost DECIMAL(10, 4) DEFAULT 0,
    entry_timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    exit_timestamp TIMESTAMP WITH TIME ZONE,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'closed')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_executions_user_id ON executions(user_id);
CREATE INDEX idx_executions_market ON executions(market);
CREATE INDEX idx_executions_entry_tx_hash ON executions(entry_tx_hash);
CREATE INDEX idx_executions_exit_tx_hash ON executions(exit_tx_hash) WHERE exit_tx_hash IS NOT NULL;
CREATE INDEX idx_executions_status ON executions(status);
CREATE INDEX idx_executions_entry_timestamp ON executions(entry_timestamp DESC);

-- Create webhook_logs table for debugging
CREATE TABLE IF NOT EXISTS webhook_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    webhook_id TEXT NOT NULL,
    transaction_data JSONB NOT NULL,
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status TEXT DEFAULT 'received' CHECK (status IN ('received', 'processed', 'error')),
    error_message TEXT
);

-- Create indexes for webhook logs
CREATE INDEX idx_webhook_logs_user_id ON webhook_logs(user_id);
CREATE INDEX idx_webhook_logs_processed_at ON webhook_logs(processed_at DESC);
CREATE INDEX idx_webhook_logs_status ON webhook_logs(status);

-- Create or update user_pnl_summary view for leaderboard
CREATE OR REPLACE VIEW user_pnl_summary AS
SELECT 
    user_id,
    market,
    COUNT(*) as total_trades,
    COUNT(CASE WHEN status = 'closed' THEN 1 END) as completed_trades,
    SUM(CASE WHEN status = 'closed' THEN pnl ELSE 0 END) as total_pnl,
    AVG(CASE WHEN status = 'closed' THEN pnl ELSE NULL END) as avg_pnl_per_trade,
    MAX(CASE WHEN status = 'closed' THEN pnl ELSE NULL END) as best_trade,
    MIN(CASE WHEN status = 'closed' THEN pnl ELSE NULL END) as worst_trade,
    SUM(gas_cost) as total_gas_spent,
    MAX(entry_timestamp) as last_trade_time
FROM executions
GROUP BY user_id, market;

-- Row Level Security (RLS) policies
ALTER TABLE executions ENABLE ROW LEVEL SECURITY;
ALTER TABLE webhook_logs ENABLE ROW LEVEL SECURITY;

-- Users can only see their own executions
CREATE POLICY "Users can view own executions" ON executions
    FOR SELECT USING (auth.uid()::text = user_id);

CREATE POLICY "Users can insert own executions" ON executions
    FOR INSERT WITH CHECK (auth.uid()::text = user_id);

-- Only service role can update (for webhook processing)
CREATE POLICY "Service role can update executions" ON executions
    FOR UPDATE USING (auth.role() = 'service_role');

-- Webhook logs are service role only
CREATE POLICY "Service role full access to webhook_logs" ON webhook_logs
    FOR ALL USING (auth.role() = 'service_role');
