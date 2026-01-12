-- Enhanced Database Schema for P&L Tracking with Alert Matching
-- Run this in Supabase SQL editor

-- Update executions table to include alert linking
ALTER TABLE executions ADD COLUMN IF NOT EXISTS alert_id UUID;
ALTER TABLE executions ADD COLUMN IF NOT EXISTS alert_spread DECIMAL(10, 4);
ALTER TABLE executions ADD COLUMN IF NOT EXISTS matched_at TIMESTAMP WITH TIME ZONE;

-- Create indexes for alert matching
CREATE INDEX IF NOT EXISTS idx_executions_alert_id ON executions(alert_id) WHERE alert_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_executions_user_market_side ON executions(user_id, market, market_ticker, side) WHERE status = 'open';

-- Create arbitrage_alerts table for storing arbitrage opportunities
CREATE TABLE IF NOT EXISTS arbitrage_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    market TEXT NOT NULL CHECK (market IN ('polymarket', 'kalshi')),
    ticker TEXT NOT NULL,
    spread DECIMAL(10, 4) NOT NULL,
    yes_price DECIMAL(10, 4),
    no_price DECIMAL(10, 4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '2 hours'),
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'expired', 'executed')),
    
    -- Market data at alert time
    market_data JSONB,
    
    -- Alert metadata
    source TEXT DEFAULT 'arbitrage_bot',
    confidence_score DECIMAL(3, 2) DEFAULT 1.0
);

-- Indexes for arbitrage_alerts
CREATE INDEX IF NOT EXISTS idx_arbitrage_alerts_user_id ON arbitrage_alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_arbitrage_alerts_market_ticker ON arbitrage_alerts(market, ticker);
CREATE INDEX IF NOT EXISTS idx_arbitrage_alerts_created_at ON arbitrage_alerts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_arbitrage_alerts_status ON arbitrage_alerts(status);

-- Create leaderboard table with batch processing support
CREATE TABLE IF NOT EXISTS leaderboard (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT UNIQUE NOT NULL,
    total_pnl DECIMAL(15, 4) DEFAULT 0,
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    avg_pnl_per_trade DECIMAL(10, 4) DEFAULT 0,
    best_trade DECIMAL(10, 4) DEFAULT 0,
    worst_trade DECIMAL(10, 4) DEFAULT 0,
    total_gas_spent DECIMAL(10, 4) DEFAULT 0,
    last_trade_time TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    rank_cache INTEGER,  -- Cached rank for performance
    rank_updated_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for leaderboard
CREATE INDEX IF NOT EXISTS idx_leaderboard_total_pnl ON leaderboard(total_pnl DESC);
CREATE INDEX IF NOT EXISTS idx_leaderboard_updated_at ON leaderboard(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_leaderboard_rank_cache ON leaderboard(rank_cache);

-- Create webhook_queue table for batch processing
CREATE TABLE IF NOT EXISTS webhook_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    webhook_id TEXT NOT NULL,
    transaction_hash TEXT NOT NULL,
    alert_id UUID,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'processed', 'error')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3
);

-- Indexes for webhook queue
CREATE INDEX IF NOT EXISTS idx_webhook_queue_status ON webhook_queue(status);
CREATE INDEX IF NOT EXISTS idx_webhook_queue_user_id ON webhook_queue(user_id);
CREATE INDEX IF NOT EXISTS idx_webhook_queue_created_at ON webhook_queue(created_at);

-- Create function to update leaderboard (for batch processing)
CREATE OR REPLACE FUNCTION update_user_leaderboard(p_user_id TEXT)
RETURNS void AS $$
DECLARE
    v_total_pnl DECIMAL;
    v_total_trades INTEGER;
    v_winning_trades INTEGER;
    v_losing_trades INTEGER;
    v_avg_pnl DECIMAL;
    v_best_trade DECIMAL;
    v_worst_trade DECIMAL;
    v_total_gas DECIMAL;
    v_last_trade TIMESTAMP;
BEGIN
    -- Calculate user statistics
    SELECT 
        COALESCE(SUM(pnl), 0),
        COUNT(*),
        COUNT(CASE WHEN pnl > 0 THEN 1 END),
        COUNT(CASE WHEN pnl < 0 THEN 1 END),
        CASE WHEN COUNT(*) > 0 THEN COALESCE(AVG(pnl), 0) ELSE 0 END,
        COALESCE(MAX(pnl), 0),
        COALESCE(MIN(pnl), 0),
        COALESCE(SUM(gas_cost), 0),
        MAX(entry_timestamp)
    INTO v_total_pnl, v_total_trades, v_winning_trades, v_losing_trades, 
         v_avg_pnl, v_best_trade, v_worst_trade, v_total_gas, v_last_trade
    FROM executions 
    WHERE user_id = p_user_id AND status = 'closed';
    
    -- Upsert to leaderboard
    INSERT INTO leaderboard (
        user_id, total_pnl, total_trades, winning_trades, losing_trades,
        avg_pnl_per_trade, best_trade, worst_trade, total_gas_spent,
        last_trade_time, updated_at
    ) VALUES (
        p_user_id, v_total_pnl, v_total_trades, v_winning_trades, v_losing_trades,
        v_avg_pnl, v_best_trade, v_worst_trade, v_total_gas, v_last_trade,
        NOW()
    )
    ON CONFLICT (user_id) DO UPDATE SET
        total_pnl = EXCLUDED.total_pnl,
        total_trades = EXCLUDED.total_trades,
        winning_trades = EXCLUDED.winning_trades,
        losing_trades = EXCLUDED.losing_trades,
        avg_pnl_per_trade = EXCLUDED.avg_pnl_per_trade,
        best_trade = EXCLUDED.best_trade,
        worst_trade = EXCLUDED.worst_trade,
        total_gas_spent = EXCLUDED.total_gas_spent,
        last_trade_time = EXCLUDED.last_trade_time,
        updated_at = EXCLUDED.updated_at;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update leaderboard on execution changes
CREATE OR REPLACE FUNCTION trigger_leaderboard_update()
RETURNS TRIGGER AS $$
BEGIN
    -- Only update on closed trades
    IF NEW.status = 'closed' AND (TG_OP = 'INSERT' OR OLD.status != 'closed') THEN
        PERFORM update_user_leaderboard(NEW.user_id);
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger
DROP TRIGGER IF EXISTS update_leaderboard_on_execution ON executions;
CREATE TRIGGER update_leaderboard_on_execution
    AFTER INSERT OR UPDATE ON executions
    FOR EACH ROW
    EXECUTE FUNCTION trigger_leaderboard_update();

-- Create function to clean up old alerts (runs daily)
CREATE OR REPLACE FUNCTION cleanup_old_alerts()
RETURNS void AS $$
BEGIN
    -- Mark alerts as expired if past expiration
    UPDATE arbitrage_alerts 
    SET status = 'expired' 
    WHERE status = 'active' AND expires_at < NOW();
    
    -- Delete alerts older than 7 days
    DELETE FROM arbitrage_alerts 
    WHERE created_at < NOW() - INTERVAL '7 days';
    
    -- Clean up old webhook logs (keep last 1000)
    DELETE FROM webhook_logs 
    WHERE id NOT IN (
        SELECT id FROM webhook_logs 
        ORDER BY processed_at DESC 
        LIMIT 1000
    );
END;
$$ LANGUAGE plpgsql;

-- Create function to update leaderboard ranks (batch operation)
CREATE OR REPLACE FUNCTION update_leaderboard_ranks()
RETURNS void AS $$
DECLARE
    user_record RECORD;
    rank_counter INTEGER := 1;
    prev_pnl DECIMAL := NULL;
BEGIN
    -- Reset all ranks
        UPDATE leaderboard SET rank_cache = NULL, rank_updated_at = NULL;
    
    -- Update ranks based on total P&L
    FOR user_record IN 
        SELECT user_id, total_pnl 
        FROM leaderboard 
        WHERE total_pnl != 0 
        ORDER BY total_pnl DESC
    LOOP
        -- Handle ties (same P&L gets same rank)
        IF prev_pnl IS NOT NULL AND user_record.total_pnl = prev_pnl THEN
            -- Same rank as previous
            UPDATE leaderboard 
            SET rank_cache = (
                SELECT rank_cache FROM leaderboard 
                WHERE user_id = (
                    SELECT user_id FROM leaderboard 
                    WHERE total_pnl = user_record.total_pnl 
                    AND rank_cache IS NOT NULL 
                    LIMIT 1
                )
            ),
            rank_updated_at = NOW()
            WHERE user_id = user_record.user_id;
        ELSE
            -- New rank
            UPDATE leaderboard 
            SET rank_cache = rank_counter, rank_updated_at = NOW()
            WHERE user_id = user_record.user_id;
            rank_counter := rank_counter + 1;
        END IF;
        
        prev_pnl := user_record.total_pnl;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Create improved view for user P&L summary
CREATE OR REPLACE VIEW user_pnl_summary_enhanced AS
SELECT 
    e.user_id,
    e.market,
    COUNT(*) as total_trades,
    COUNT(CASE WHEN e.status = 'closed' THEN 1 END) as completed_trades,
    COUNT(CASE WHEN e.status = 'open' THEN 1 END) as open_positions,
    COALESCE(SUM(CASE WHEN e.status = 'closed' THEN e.pnl ELSE 0 END), 0) as total_pnl,
    CASE 
        WHEN COUNT(CASE WHEN e.status = 'closed' THEN 1 END) > 0 
        THEN COALESCE(AVG(CASE WHEN e.status = 'closed' THEN e.pnl ELSE NULL END), 0)
        ELSE 0 
    END as avg_pnl_per_trade,
    COALESCE(MAX(CASE WHEN e.status = 'closed' THEN e.pnl ELSE NULL END), 0) as best_trade,
    COALESCE(MIN(CASE WHEN e.status = 'closed' THEN e.pnl ELSE NULL END), 0) as worst_trade,
    COALESCE(SUM(e.gas_cost), 0) as total_gas_spent,
    MAX(e.entry_timestamp) as last_trade_time,
    COUNT(CASE WHEN e.status = 'closed' AND e.pnl > 0 THEN 1 END) as winning_trades,
    COUNT(CASE WHEN e.status = 'closed' AND e.pnl < 0 THEN 1 END) as losing_trades,
    CASE 
        WHEN COUNT(CASE WHEN e.status = 'closed' THEN 1 END) > 0 
        THEN (COUNT(CASE WHEN e.status = 'closed' AND e.pnl > 0 THEN 1 END) * 100.0 / COUNT(CASE WHEN e.status = 'closed' THEN 1 END))
        ELSE 0 
    END as win_rate_percentage,
    -- Alert matching stats
    COUNT(e.alert_id) as alert_matched_trades,
    COALESCE(AVG(e.alert_spread), 0) as avg_alert_spread
FROM executions e
GROUP BY e.user_id, e.market;

-- Row Level Security (RLS) policies
ALTER TABLE arbitrage_alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE leaderboard ENABLE ROW LEVEL SECURITY;
ALTER TABLE webhook_queue ENABLE ROW LEVEL SECURITY;

-- Users can only see their own data
CREATE POLICY "Users can view own alerts" ON arbitrage_alerts
    FOR SELECT USING (auth.uid()::text = user_id);

CREATE POLICY "Users can view own leaderboard" ON leaderboard
    FOR SELECT USING (auth.uid()::text = user_id);

-- Service role full access
CREATE POLICY "Service role full access to alerts" ON arbitrage_alerts
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access to leaderboard" ON leaderboard
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access to webhook queue" ON webhook_queue
    FOR ALL USING (auth.role() = 'service_role');

-- Create scheduled job for cleanup (requires pg_cron extension)
-- SELECT cron.schedule('cleanup-old-alerts', '0 2 * * *', 'SELECT cleanup_old_alerts();');
-- SELECT cron.schedule('update-leaderboard-ranks', '*/5 * * * *', 'SELECT update_leaderboard_ranks();');
