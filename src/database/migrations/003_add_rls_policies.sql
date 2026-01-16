-- Migration 003: Add RLS Policies
-- Row Level Security policies for P&L tracking database

-- Enable Row Level Security
ALTER TABLE executions ENABLE ROW LEVEL SECURITY;
ALTER TABLE arbitrage_alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE leaderboard ENABLE ROW LEVEL SECURITY;
ALTER TABLE pnl_cards ENABLE ROW LEVEL SECURITY;

-- Users can only access their own data
CREATE POLICY "Users can view own executions" ON executions FOR SELECT USING (user_id = current_setting('app.current_user_id', true));
CREATE POLICY "Users can insert own executions" ON executions FOR INSERT WITH CHECK (user_id = current_setting('app.current_user_id', true));
CREATE POLICY "Users can update own executions" ON executions FOR UPDATE USING (user_id = current_setting('app.current_user_id', true));

CREATE POLICY "Users can view own arbitrage alerts" ON arbitrage_alerts FOR SELECT USING (user_id = current_setting('app.current_user_id', true));
CREATE POLICY "Users can insert own arbitrage alerts" ON arbitrage_alerts FOR INSERT WITH CHECK (user_id = current_setting('app.current_user_id', true));
CREATE POLICY "Users can update own arbitrage alerts" ON arbitrage_alerts FOR UPDATE USING (user_id = current_setting('app.current_user_id', true));

CREATE POLICY "Users can view own leaderboard entry" ON leaderboard FOR SELECT USING (user_id = current_setting('app.current_user_id', true));
CREATE POLICY "Users can update own leaderboard entry" ON leaderboard FOR UPDATE USING (user_id = current_setting('app.current_user_id', true));

CREATE POLICY "Users can view own P&L cards" ON pnl_cards FOR SELECT USING (user_id = current_setting('app.current_user_id', true));
CREATE POLICY "Users can insert own P&L cards" ON pnl_cards FOR INSERT WITH CHECK (user_id = current_setting('app.current_user_id', true));

-- Public read access for leaderboard (for ranking display)
CREATE POLICY "Public read access for leaderboard" ON leaderboard FOR SELECT USING (true);

-- Admin access policies
CREATE POLICY "Admin full access to executions" ON executions FOR ALL USING (current_setting('app.user_role', true) = 'admin');
CREATE POLICY "Admin full access to arbitrage alerts" ON arbitrage_alerts FOR ALL USING (current_setting('app.user_role', true) = 'admin');
CREATE POLICY "Admin full access to leaderboard" ON leaderboard FOR ALL USING (current_setting('app.user_role', true) = 'admin');
CREATE POLICY "Admin full access to P&L cards" ON pnl_cards FOR ALL USING (current_setting('app.user_role', true) = 'admin');

-- Webhook logs and queue (service access only)
ALTER TABLE webhook_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE webhook_queue ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service access to webhook logs" ON webhook_logs FOR ALL USING (current_setting('app.user_role', true) = 'service');
CREATE POLICY "Service access to webhook queue" ON webhook_queue FOR ALL USING (current_setting('app.user_role', true) = 'service');
