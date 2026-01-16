-- RLS Testing Script for webhook_queue Table
-- Run these tests in Supabase SQL Editor to verify RLS policies work correctly

-- Test 1: Insert test data (run as service role first)
-- This should succeed with service role
INSERT INTO webhook_queue (tx_hash, user_id, status) 
VALUES 
    ('0x1234567890abcdef', 'user_123', 'pending'),
    ('0xabcdef1234567890', 'user_456', 'pending'),
    ('0x567890abcdef1234', 'user_123', 'processed');

-- Test 2: Verify data was inserted
SELECT * FROM webhook_queue ORDER BY created_at;

-- Test 3: Test user access simulation
-- Simulate user_123 trying to access their own data (should return only their records)
-- Note: In a real test, you'd set auth.uid() to 'user_123' 
-- For now, we'll use a direct query to show the expected behavior

-- Expected result for user_123:
SELECT 'Expected for user_123:' as test_context, * FROM webhook_queue WHERE user_id = 'user_123';

-- Expected result for user_456:
SELECT 'Expected for user_456:' as test_context, * FROM webhook_queue WHERE user_id = 'user_456';

-- Test 4: Test the webhook processing function
SELECT * FROM process_webhook_queue(
    (SELECT id FROM webhook_queue WHERE user_id = 'user_123' AND status = 'pending' LIMIT 1)
);

-- Test 5: Verify the webhook was processed
SELECT * FROM webhook_queue WHERE status = 'processed' ORDER BY processed_at DESC;

-- Test 6: Test the stats view
SELECT * FROM webhook_queue_stats ORDER BY user_id;

-- Test 7: Performance test with indexes
EXPLAIN (ANALYZE, BUFFERS) 
SELECT * FROM webhook_queue 
WHERE user_id = 'user_123' AND status = 'pending'
ORDER BY created_at DESC;

-- Test 8: Test policy violations (these should fail in real context)
-- These queries would fail for regular users but succeed for service_role

-- Test cross-user access (should fail for regular users)
-- SELECT * FROM webhook_queue WHERE user_id != 'user_123'; -- Would fail for user_123

-- Test unauthorized updates (should fail for regular users)  
-- UPDATE webhook_queue SET status = 'processed' WHERE user_id = 'user_456'; -- Would fail for user_123

-- Test unauthorized deletes (should fail for regular users)
-- DELETE FROM webhook_queue WHERE user_id = 'user_456'; -- Would fail for user_123

-- Cleanup test data (run as service role)
-- DELETE FROM webhook_queue WHERE user_id IN ('user_123', 'user_456');
