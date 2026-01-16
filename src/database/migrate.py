"""
Database Migration Scripts
Setup and migration scripts for P&L tracking database
"""

import os
import logging
from pathlib import Path
from supabase import create_client

logger = logging.getLogger(__name__)

def run_supabase_migrations():
    """Run all Supabase database migrations"""
    
    # Read migration files
    migration_dir = Path("src/database/migrations")
    
    migrations = [
        "001_initial_schema.sql",
        "002_add_indexes.sql", 
        "003_add_rls_policies.sql",
        "004_add_triggers.sql"
    ]
    
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')  # Use service key for migrations
    
    if not supabase_url or not supabase_key:
        logger.error("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
        return False
    
    client = create_client(supabase_url, supabase_key)
    
    for migration_file in migrations:
        migration_path = migration_dir / migration_file
        
        if not migration_path.exists():
            logger.warning(f"Migration file not found: {migration_path}")
            continue
        
        try:
            with open(migration_path, 'r') as f:
                sql = f.read()
            
            # Execute migration
            result = client.rpc('exec_sql', {'sql': sql}).execute()
            
            if result.data:
                logger.info(f"Migration {migration_file} executed successfully")
            else:
                logger.error(f"Migration {migration_file} failed")
                return False
                
        except Exception as e:
            logger.error(f"Error running migration {migration_file}: {e}")
            return False
    
    logger.info("All migrations completed successfully")
    return True

def seed_test_data():
    """Seed test data for development/testing"""
    
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
    
    if not supabase_url or not supabase_key:
        logger.error("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
        return False
    
    client = create_client(supabase_url, supabase_key)
    
    # Sample test users and executions
    test_data = [
        {
            'user_id': 'test_user_1',
            'market': 'Bitcoin > $100K End of 2024',
            'market_ticker': 'BTC-100K-2024',
            'side': 'yes',
            'entry_price': 0.65,
            'exit_price': 0.72,
            'quantity': 1000,
            'status': 'closed',
            'pnl': 107.70,
            'entry_timestamp': '2024-01-10T10:00:00Z',
            'exit_timestamp': '2024-01-10T15:30:00Z'
        },
        {
            'user_id': 'test_user_1',
            'market': 'Trump 2024 Election Winner',
            'market_ticker': 'TRUMP-2024',
            'side': 'no',
            'entry_price': 0.45,
            'exit_price': 0.42,
            'quantity': 500,
            'status': 'closed',
            'pnl': 33.33,
            'entry_timestamp': '2024-01-09T14:00:00Z',
            'exit_timestamp': '2024-01-09T18:00:00Z'
        },
        {
            'user_id': 'test_user_2',
            'market': 'Ethereum > $5K End of 2024',
            'market_ticker': 'ETH-5K-2024',
            'side': 'yes',
            'entry_price': 0.35,
            'exit_price': None,
            'quantity': 750,
            'status': 'open',
            'pnl': 0.0,
            'entry_timestamp': '2024-01-11T09:00:00Z',
            'exit_timestamp': None
        }
    ]
    
    try:
        # Insert test executions
        for data in test_data:
            client.table('executions').insert(data).execute()
        
        # Update leaderboard
        leaderboard_data = [
            {
                'user_id': 'test_user_1',
                'total_pnl': 141.03,
                'total_trades': 2,
                'win_rate': 100.0
            },
            {
                'user_id': 'test_user_2', 
                'total_pnl': 0.0,
                'total_trades': 1,
                'win_rate': 0.0
            }
        ]
        
        for data in leaderboard_data:
            client.table('leaderboard').insert(data).execute()
        
        logger.info("Test data seeded successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error seeding test data: {e}")
        return False

if __name__ == "__main__":
    # Run migrations and seed data
    if run_supabase_migrations():
        seed_test_data()
    else:
        logger.error("Migration failed, skipping seed data")