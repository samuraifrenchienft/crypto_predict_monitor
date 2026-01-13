-- Migration 004: Add Triggers
-- Database triggers for P&L tracking database

-- Function to update updated_at timestamp
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

-- Function to update leaderboard stats after execution
CREATE OR REPLACE FUNCTION update_leaderboard_stats()
RETURNS TRIGGER AS $$
BEGIN
    -- Update or create leaderboard entry
    INSERT INTO leaderboard (user_id, total_pnl, total_trades, win_rate, total_volume, updated_at)
    VALUES (
        NEW.user_id,
        COALESCE(NEW.pnl, 0),
        1,
        CASE WHEN NEW.pnl > 0 THEN 100 ELSE 0 END,
        NEW.quantity * NEW.entry_price,
        NOW()
    )
    ON CONFLICT (user_id) 
    DO UPDATE SET
        total_pnl = leaderboard.total_pnl + COALESCE(NEW.pnl, 0),
        total_trades = leaderboard.total_trades + 1,
        total_volume = leaderboard.total_volume + (NEW.quantity * NEW.entry_price),
        win_rate = CASE 
            WHEN NEW.pnl > 0 THEN 
                (leaderboard.win_rate * leaderboard.total_trades + 100) / (leaderboard.total_trades + 1)
            ELSE 
                (leaderboard.win_rate * leaderboard.total_trades) / (leaderboard.total_trades + 1)
        END,
        updated_at = NOW();
    
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for leaderboard updates
CREATE TRIGGER update_leaderboard_on_execution
    AFTER INSERT OR UPDATE ON executions
    FOR EACH ROW
    WHEN (NEW.status = 'closed' AND NEW.pnl IS NOT NULL)
    EXECUTE FUNCTION update_leaderboard_stats();

-- Function to log webhook calls
CREATE OR REPLACE FUNCTION log_webhook_call()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO webhook_logs (webhook_id, transaction_data, status, created_at)
    VALUES (
        COALESCE(NEW.webhook_id, 'unknown'),
        json_build_object(
            'execution_id', NEW.id,
            'user_id', NEW.user_id,
            'market', NEW.market,
            'status', NEW.status,
            'pnl', NEW.pnl
        ),
        'received',
        NOW()
    );
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for webhook logging (if webhook_id column exists)
-- ALTER TABLE executions ADD COLUMN IF NOT EXISTS webhook_id TEXT;
-- CREATE TRIGGER log_webhook_on_execution
--     AFTER INSERT ON executions
--     FOR EACH ROW
--     EXECUTE FUNCTION log_webhook_call();

-- Function to clean up old P&L cards
CREATE OR REPLACE FUNCTION cleanup_old_pnl_cards()
RETURNS void AS $$
BEGIN
    -- Delete cards older than 30 days
    DELETE FROM pnl_cards 
    WHERE generated_at < NOW() - INTERVAL '30 days';
    
    -- Log cleanup
    RAISE NOTICE 'Cleaned up old P&L cards older than 30 days';
END;
$$ language 'plpgsql';

-- Function to calculate user statistics
CREATE OR REPLACE FUNCTION calculate_user_stats(p_user_id TEXT)
RETURNS TABLE(
    total_pnl DECIMAL,
    total_trades INTEGER,
    win_rate DECIMAL,
    total_volume DECIMAL,
    best_trade DECIMAL,
    worst_trade DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COALESCE(SUM(pnl), 0) as total_pnl,
        COUNT(*) as total_trades,
        CASE 
            WHEN COUNT(*) > 0 THEN 
                (COUNT(CASE WHEN pnl > 0 THEN 1 END) * 100.0 / COUNT(*))
            ELSE 0 
        END as win_rate,
        COALESCE(SUM(quantity * entry_price), 0) as total_volume,
        COALESCE(MAX(pnl), 0) as best_trade,
        COALESCE(MIN(pnl), 0) as worst_trade
    FROM executions
    WHERE user_id = p_user_id 
        AND status = 'closed' 
        AND pnl IS NOT NULL;
END;
$$ language 'plpgsql';

-- Function to get top performers
CREATE OR REPLACE FUNCTION get_top_performers(p_limit INTEGER DEFAULT 10)
RETURNS TABLE(
    user_id TEXT,
    username TEXT,
    total_pnl DECIMAL,
    total_trades INTEGER,
    win_rate DECIMAL,
    rank_value INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        l.user_id,
        l.username,
        l.total_pnl,
        l.total_trades,
        l.win_rate,
        ROW_NUMBER() OVER (ORDER BY l.total_pnl DESC, l.win_rate DESC) as rank_value
    FROM leaderboard l
    WHERE l.total_trades >= 5  -- Minimum trades to qualify
    ORDER BY l.total_pnl DESC, l.win_rate DESC
    LIMIT p_limit;
END;
$$ language 'plpgsql';
