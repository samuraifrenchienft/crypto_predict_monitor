# Webhook Queue RLS Implementation Documentation

## Overview
Row Level Security (RLS) has been implemented on the `public.webhook_queue` table to ensure users can only access their own webhook queue entries while allowing backend services to manage all entries.

## Access Model

### User Access (Authenticated Role)
- **Read**: Can only view their own webhook queue entries (`user_id = auth.uid()`)
- **Insert**: Can only create entries for themselves (`user_id = auth.uid()`)
- **Update**: Can only update their own entries (`user_id = auth.uid()`)
- **Delete**: Can only delete their own entries (`user_id = auth.uid()`)

### Service Access (Service Role)
- **Full Access**: Backend services can perform all operations on all entries
- **Webhook Processing**: Special function `process_webhook_queue()` for secure processing

### Anonymous Access (Anon Role)
- **No Access**: Anonymous users have no access to webhook queue data

## Table Structure
```sql
webhook_queue (
    id UUID PRIMARY KEY,
    tx_hash TEXT NOT NULL,
    user_id TEXT NOT NULL,        -- Ownership column
    status TEXT DEFAULT 'pending',
    processed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
)
```

## RLS Policies Implemented

### 1. User Ownership Policies
```sql
-- Users can view own entries
CREATE POLICY "Users can view own webhook queue entries" 
ON webhook_queue FOR SELECT 
USING (auth.uid()::text = user_id);

-- Users can insert own entries
CREATE POLICY "Users can insert own webhook queue entries" 
ON webhook_queue FOR INSERT 
WITH CHECK (auth.uid()::text = user_id);
```

### 2. Service Role Policy
```sql
-- Service role can manage all entries
CREATE POLICY "Service role can manage all webhook queue entries" 
ON webhook_queue FOR ALL 
USING (auth.role() = 'service_role')
WITH CHECK (auth.role() = 'service_role');
```

## Performance Optimizations

### Indexes Created
- `idx_webhook_queue_user_id` - For user-based queries
- `idx_webhook_queue_status` - For status filtering
- `idx_webhook_queue_created_at` - For time-based queries

### Special Functions
- `process_webhook_queue(webhook_id)` - Secure webhook processing with service role privileges

## Views Created

### webhook_queue_stats
Aggregated statistics per user:
- Total entries count
- Pending entries count
- Processed entries count
- Last entry timestamp
- Last processed timestamp

Access to stats view is also RLS-protected:
- Users can only see their own stats
- Service role can see all stats

## Security Features

### 1. Ownership-Based Access
- All user operations are restricted to their own `user_id`
- Prevents cross-user data access

### 2. Service Role Privileges
- Backend services can process webhooks for any user
- Uses `SECURITY DEFINER` functions for elevated privileges

### 3. Performance Considerations
- Indexes on policy columns ensure efficient query planning
- Uses `(SELECT auth.uid())` pattern for complex policies

## Testing

### Test Scenarios Covered
1. **User Access**: Users can only see their own entries
2. **Cross-User Prevention**: Users cannot access other users' data
3. **Service Role Access**: Backend can manage all entries
4. **Webhook Processing**: Secure processing function works correctly
5. **Performance**: Index usage verified with EXPLAIN ANALYZE

### Test Files
- `database/rls_webhook_queue.sql` - RLS implementation
- `database/test_rls_webhook_queue.sql` - Test scripts

## Usage Examples

### Client-Side (Authenticated User)
```sql
-- User can view their own webhooks
SELECT * FROM webhook_queue;

-- User can add new webhook
INSERT INTO webhook_queue (tx_hash, user_id, status) 
VALUES ('0x123...', auth.uid()::text, 'pending');

-- User can update their webhook status
UPDATE webhook_queue 
SET status = 'processed' 
WHERE tx_hash = '0x123...';
```

### Server-Side (Service Role)
```sql
-- Process webhook securely
SELECT * FROM process_webhook_queue(webhook_id);

-- View all webhooks (admin function)
SELECT * FROM webhook_queue ORDER BY created_at DESC;

-- Get statistics
SELECT * FROM webhook_queue_stats;
```

## Deployment Notes

### Maintenance Window
- RLS is enabled immediately after policy creation
- Create policies during the same transaction to avoid access interruption

### Rollback Plan
- Disable RLS: `ALTER TABLE webhook_queue DISABLE ROW LEVEL SECURITY;`
- Drop policies: `DROP POLICY IF EXISTS "policy_name" ON webhook_queue;`

### Monitoring
- Monitor query performance with the new indexes
- Check RLS policy effectiveness with audit logs
- Track webhook processing times

## Security Best Practices Applied

1. **Principle of Least Privilege**: Users get minimum necessary access
2. **Ownership Verification**: All operations verify user ownership
3. **Service Role Separation**: Backend operations use elevated privileges securely
4. **Performance Optimization**: Indexes on policy columns prevent performance issues
5. **Comprehensive Testing**: All access patterns tested and verified

This RLS implementation ensures secure, performant, and maintainable access control for the webhook queue system.
