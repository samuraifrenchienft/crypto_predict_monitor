-- Migration 002: Add Indexes
-- Performance indexes for P&L tracking database

-- Executions table indexes
CREATE INDEX IF NOT EXISTS idx_executions_user_id ON executions(user_id);
CREATE INDEX IF NOT EXISTS idx_executions_status ON executions(status);
CREATE INDEX IF NOT EXISTS idx_executions_market ON executions(market);
CREATE INDEX IF NOT EXISTS idx_executions_entry_timestamp ON executions(entry_timestamp);
CREATE INDEX IF NOT EXISTS idx_executions_user_timestamp ON executions(user_id, entry_timestamp);
CREATE INDEX IF NOT EXISTS idx_executions_user_status ON executions(user_id, status);

-- Arbitrage alerts table indexes
CREATE INDEX IF NOT EXISTS idx_arbitrage_alerts_user_id ON arbitrage_alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_arbitrage_alerts_status ON arbitrage_alerts(status);
CREATE INDEX IF NOT EXISTS idx_arbitrage_alerts_market ON arbitrage_alerts(market);
CREATE INDEX IF NOT EXISTS idx_arbitrage_alerts_created_at ON arbitrage_alerts(created_at);
CREATE INDEX IF NOT EXISTS idx_arbitrage_alerts_expires_at ON arbitrage_alerts(expires_at);

-- Leaderboard table indexes
CREATE INDEX IF NOT EXISTS idx_leaderboard_user_id ON leaderboard(user_id);
CREATE INDEX IF NOT EXISTS idx_leaderboard_total_pnl ON leaderboard(total_pnl DESC);
CREATE INDEX IF NOT EXISTS idx_leaderboard_win_rate ON leaderboard(win_rate DESC);
CREATE INDEX IF NOT EXISTS idx_leaderboard_total_trades ON leaderboard(total_trades DESC);
CREATE INDEX IF NOT EXISTS idx_leaderboard_updated_at ON leaderboard(updated_at DESC);

-- Webhook logs table indexes
CREATE INDEX IF NOT EXISTS idx_webhook_logs_webhook_id ON webhook_logs(webhook_id);
CREATE INDEX IF NOT EXISTS idx_webhook_logs_status ON webhook_logs(status);
CREATE INDEX IF NOT EXISTS idx_webhook_logs_created_at ON webhook_logs(created_at);

-- Webhook queue table indexes
CREATE INDEX IF NOT EXISTS idx_webhook_queue_user_id ON webhook_queue(user_id);
CREATE INDEX IF NOT EXISTS idx_webhook_queue_status ON webhook_queue(status);
CREATE INDEX IF NOT EXISTS idx_webhook_queue_created_at ON webhook_queue(created_at);

-- P&L cards table indexes
CREATE INDEX IF NOT EXISTS idx_pnl_cards_user_id ON pnl_cards(user_id);
CREATE INDEX IF NOT EXISTS idx_pnl_cards_period ON pnl_cards(period);
CREATE INDEX IF NOT EXISTS idx_pnl_cards_generated_at ON pnl_cards(generated_at DESC);
CREATE INDEX IF NOT EXISTS idx_pnl_cards_user_period ON pnl_cards(user_id, period);
CREATE INDEX IF NOT EXISTS idx_pnl_cards_expires_at ON pnl_cards(expires_at);

-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_executions_user_status_timestamp ON executions(user_id, status, entry_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_leaderboard_pnl_trades ON leaderboard(total_pnl DESC, total_trades DESC);
CREATE INDEX IF NOT EXISTS idx_pnl_cards_user_generated ON pnl_cards(user_id, generated_at DESC);
