-- Row Level Security (RLS) Implementation for webhook_queue Table
-- Run this in your Supabase SQL Editor

-- Step 1: Enable RLS on webhook_queue table
ALTER TABLE webhook_queue ENABLE ROW LEVEL SECURITY;

-- Step 2: Create indexes on policy columns for performance
CREATE INDEX IF NOT EXISTS idx_webhook_queue_user_id ON webhook_queue(user_id);
CREATE INDEX IF NOT EXISTS idx_webhook_queue_status ON webhook_queue(status);
CREATE INDEX IF NOT EXISTS idx_webhook_queue_created_at ON webhook_queue(created_at);

-- Step 3: Create RLS Policies

-- Policy 1: Users can read their own webhook queue entries
CREATE POLICY "Users can view own webhook queue entries" 
ON webhook_queue FOR SELECT 
USING (auth.uid()::text = user_id);

-- Policy 2: Users can insert their own webhook queue entries
CREATE POLICY "Users can insert own webhook queue entries" 
ON webhook_queue FOR INSERT 
WITH CHECK (auth.uid()::text = user_id);

-- Policy 3: Users can update their own webhook queue entries
CREATE POLICY "Users can update own webhook queue entries" 
ON webhook_queue FOR UPDATE 
USING (auth.uid()::text = user_id)
WITH CHECK (auth.uid()::text = user_id);

-- Policy 4: Users can delete their own webhook queue entries
CREATE POLICY "Users can delete own webhook queue entries" 
ON webhook_queue FOR DELETE 
USING (auth.uid()::text = user_id);

-- Policy 5: Service role (backend) can manage all webhook queue entries
-- This allows your backend services to process webhooks for any user
CREATE POLICY "Service role can manage all webhook queue entries" 
ON webhook_queue FOR ALL 
USING (auth.role() = 'service_role')
WITH CHECK (auth.role() = 'service_role');

-- Step 4: Create a function for webhook processing (optional optimization)
CREATE OR REPLACE FUNCTION process_webhook_queue(webhook_id UUID)
RETURNS TABLE(id UUID, tx_hash TEXT, user_id TEXT, status TEXT, processed_at TIMESTAMP WITH TIME ZONE) 
LANGUAGE plpgsql
SECURITY DEFINER -- Run with service role privileges
AS $$
BEGIN
    -- Update webhook status to processed
    UPDATE webhook_queue 
    SET status = 'processed', processed_at = NOW()
    WHERE id = webhook_id;
    
    -- Return the updated record
    RETURN QUERY
    SELECT wq.id, wq.tx_hash, wq.user_id, wq.status, wq.processed_at
    FROM webhook_queue wq
    WHERE wq.id = webhook_id;
END;
$$;

-- Step 5: Grant necessary permissions
GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT SELECT ON webhook_queue TO authenticated;
GRANT INSERT, UPDATE, DELETE ON webhook_queue TO authenticated;
GRANT ALL ON webhook_queue TO service_role;

-- Step 6: Create a view for webhook queue monitoring (admin view)
CREATE OR REPLACE VIEW webhook_queue_stats AS
SELECT 
    user_id,
    COUNT(*) as total_entries,
    COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_entries,
    COUNT(CASE WHEN status = 'processed' THEN 1 END) as processed_entries,
    MAX(created_at) as last_entry,
    MAX(processed_at) as last_processed
FROM webhook_queue
GROUP BY user_id;

-- Grant access to the stats view for authenticated users (only their own stats)
CREATE POLICY "Users can view own webhook queue stats" 
ON webhook_queue_stats FOR SELECT 
USING (auth.uid()::text = user_id);

-- Grant service role full access to stats
CREATE POLICY "Service role can view all webhook queue stats" 
ON webhook_queue_stats FOR SELECT 
USING (auth.role() = 'service_role');

GRANT SELECT ON webhook_queue_stats TO authenticated, service_role;
