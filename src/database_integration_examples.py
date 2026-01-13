"""
Database Integration Examples for P&L Card Generator
Implement these methods based on your database structure
"""

# Example 1: SQLAlchemy Integration
async def fetch_predictions_sqlalchemy(user_id: str, start_time, end_time, db_session):
    """Fetch predictions using SQLAlchemy ORM"""
    
    from your_models import Prediction  # Replace with your actual model
    
    results = db_session.query(Prediction).filter(
        Prediction.user_id == user_id,
        Prediction.timestamp >= start_time,
        Prediction.timestamp <= end_time,
        Prediction.status.in_(['closed', 'settled', 'open'])
    ).order_by(Prediction.timestamp.desc()).limit(50).all()
    
    from src.social.pnl_card_generator import PredictionResult
    
    return [
        PredictionResult(
            market=result.market_name,
            prediction=result.prediction_type.upper(),  # "YES" or "NO"
            entry_price=float(result.entry_price),
            exit_price=float(result.exit_price) if result.exit_price else None,
            pnl_percentage=calculate_pnl_percentage(result.entry_price, result.exit_price),
            volume=float(result.volume or 0),
            timestamp=result.timestamp,
            is_open=result.status == 'open'
        )
        for result in results
    ]

def calculate_pnl_percentage(entry_price: float, exit_price: float) -> float:
    """Calculate P&L percentage"""
    if not exit_price:
        return 0.0
    return ((exit_price - entry_price) / entry_price) * 100

# Example 2: MongoDB Integration  
import asyncio
from datetime import datetime
from src.social.pnl_card_generator import PredictionResult

async def fetch_predictions_mongodb(user_id: str, start_time, end_time, db):
    """Fetch predictions using MongoDB"""
    
    collection = db.predictions
    
    # Query for user predictions in time range
    cursor = collection.find({
        'user_id': user_id,
        'timestamp': {
            '$gte': start_time,
            '$lte': end_time
        },
        'status': {'$in': ['closed', 'settled', 'open']}
    }).sort('timestamp', -1).limit(50)
    
    results = await cursor.to_list(length=None)
    
    return [
        PredictionResult(
            market=result['market'],
            prediction=result['prediction'].upper(),
            entry_price=float(result['entry_price']),
            exit_price=float(result['exit_price']) if result.get('exit_price') else None,
            pnl_percentage=calculate_pnl_percentage(result['entry_price'], result.get('exit_price')),
            volume=float(result.get('volume', 0)),
            timestamp=result['timestamp'],
            is_open=result['status'] == 'open'
        )
        for result in results
    ]

# Example 3: Supabase Integration
import asyncio
from supabase import create_client
from src.social.pnl_card_generator import PredictionResult

async def fetch_predictions_supabase(user_id: str, start_time, end_time, supabase_client):
    """Fetch predictions using Supabase"""
    
    response = supabase_client.table('predictions').select('*').eq('user_id', user_id).gte('timestamp', start_time.isoformat()).lte('timestamp', end_time.isoformat()).in_('status', ['closed', 'settled', 'open']).order('timestamp', desc=True).limit(50).execute()
    
    results = response.data
    
    return [
        PredictionResult(
            market=result['market'],
            prediction=result['prediction'].upper(),
            entry_price=float(result['entry_price']),
            exit_price=float(result['exit_price']) if result.get('exit_price') else None,
            pnl_percentage=calculate_pnl_percentage(result['entry_price'], result.get('exit_price')),
            volume=float(result.get('volume', 0)),
            timestamp=datetime.fromisoformat(result['timestamp'].replace('Z', '+00:00')),
            is_open=result['status'] == 'open'
        )
        for result in results
    ]

# Example 4: Direct SQL Integration
import asyncpg
from src.social.pnl_card_generator import PredictionResult

async def fetch_predictions_postgresql(user_id: str, start_time, end_time, db_pool):
    """Fetch predictions using direct PostgreSQL connection"""
    
    async with db_pool.acquire() as conn:
        query = """
            SELECT 
                market_name,
                prediction_type,
                entry_price,
                exit_price,
                volume,
                timestamp,
                status
            FROM predictions 
            WHERE user_id = $1 
                AND timestamp >= $2 
                AND timestamp <= $3
                AND status IN ('closed', 'settled', 'open')
            ORDER BY timestamp DESC
            LIMIT 50
        """
        
        rows = await conn.fetch(query, user_id, start_time, end_time)
        
        return [
            PredictionResult(
                market=row['market_name'],
                prediction=row['prediction_type'].upper(),
                entry_price=float(row['entry_price']),
                exit_price=float(row['exit_price']) if row['exit_price'] else None,
                pnl_percentage=calculate_pnl_percentage(row['entry_price'], row['exit_price']),
                volume=float(row['volume'] or 0),
                timestamp=row['timestamp'],
                is_open=row['status'] == 'open'
            )
            for row in rows
        ]

# Example 5: REST API Integration
import aiohttp
from src.social.pnl_card_generator import PredictionResult

async def fetch_predictions_rest_api(user_id: str, start_time, end_time, api_base_url: str, api_key: str):
    """Fetch predictions from external REST API"""
    
    async with aiohttp.ClientSession() as session:
        url = f"{api_base_url}/predictions/{user_id}"
        params = {
            'start': start_time.isoformat(),
            'end': end_time.isoformat(),
            'limit': 50
        }
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        async with session.get(url, params=params, headers=headers) as response:
            if response.status != 200:
                raise Exception(f"API request failed: {response.status}")
            
            data = await response.json()
            
            return [
                PredictionResult(
                    market=pred['market'],
                    prediction=pred['prediction'].upper(),
                    entry_price=float(pred['entry_price']),
                    exit_price=float(pred.get('exit_price')) if pred.get('exit_price') else None,
                    pnl_percentage=calculate_pnl_percentage(pred['entry_price'], pred.get('exit_price')),
                    volume=float(pred.get('volume', 0)),
                    timestamp=datetime.fromisoformat(pred['timestamp'].replace('Z', '+00:00')),
                    is_open=pred['status'] == 'open'
                )
                for pred in data.get('predictions', [])
            ]

# Example 6: Mock Data for Testing
from datetime import datetime, timedelta
import random
from src.social.pnl_card_generator import PredictionResult

async def fetch_predictions_mock(user_id: str, start_time, end_time):
    """Generate mock prediction data for testing"""
    
    markets = [
        "Bitcoin > $100K End of 2024",
        "Trump 2024 Election Winner", 
        "Ethereum > $5K End of 2024",
        "S&P 500 > 5000 End of 2024",
        "COVID-19 Restrictions End 2024",
        "AI AGI Before 2030",
        "Tesla Stock > $500 End of 2024",
        "Gold > $3000 End of 2024"
    ]
    
    predictions = []
    num_predictions = random.randint(3, 12)
    
    for i in range(num_predictions):
        # Random timestamp within range
        time_diff = (end_time - start_time).total_seconds()
        random_seconds = random.randint(0, int(time_diff))
        timestamp = start_time + timedelta(seconds=random_seconds)
        
        # Random market
        market = random.choice(markets)
        
        # Random prediction
        prediction = random.choice(["YES", "NO"])
        
        # Random prices
        entry_price = round(random.uniform(0.1, 0.9), 3)
        
        # 70% chance of being closed
        if random.random() < 0.7:
            # Generate realistic exit price
            price_change = random.uniform(-0.3, 0.4)
            exit_price = round(max(0.01, entry_price * (1 + price_change)), 3)
            is_open = False
        else:
            exit_price = None
            is_open = True
        
        # Calculate P&L
        pnl = calculate_pnl_percentage(entry_price, exit_price) if exit_price else 0.0
        
        # Random volume
        volume = round(random.uniform(100, 5000), 0)
        
        predictions.append(
            PredictionResult(
                market=market,
                prediction=prediction,
                entry_price=entry_price,
                exit_price=exit_price,
                pnl_percentage=pnl,
                volume=volume,
                timestamp=timestamp,
                is_open=is_open
            )
        )
    
    # Sort by timestamp (most recent first)
    predictions.sort(key=lambda p: p.timestamp, reverse=True)
    
    return predictions

# Integration Helper
class DatabaseAdapter:
    """Adapter to integrate with your existing database"""
    
    def __init__(self, db_connection, db_type='sqlalchemy'):
        self.db = db_connection
        self.db_type = db_type
    
    async def fetch_predictions(self, user_id: str, start_time, end_time):
        """Fetch predictions using the configured database type"""
        
        if self.db_type == 'sqlalchemy':
            return await fetch_predictions_sqlalchemy(user_id, start_time, end_time, self.db.session)
        elif self.db_type == 'mongodb':
            return await fetch_predictions_mongodb(user_id, start_time, end_time, self.db)
        elif self.db_type == 'supabase':
            return await fetch_predictions_supabase(user_id, start_time, end_time, self.db)
        elif self.db_type == 'postgresql':
            return await fetch_predictions_postgresql(user_id, start_time, end_time, self.db)
        elif self.db_type == 'rest_api':
            return await fetch_predictions_rest_api(
                user_id, start_time, end_time, 
                self.db['base_url'], self.db['api_key']
            )
        else:
            # Fallback to mock data
            return await fetch_predictions_mock(user_id, start_time, end_time)

# Usage in your PnLCardGenerator:
# 
# In src/social/pnl_card_generator.py, update the fetch_predictions_in_period method:
#
# async def fetch_predictions_in_period(self, user_id: str, start_time: datetime, end_time: datetime):
#     adapter = DatabaseAdapter(self.db, self.db_type)
#     return await adapter.fetch_predictions(user_id, start_time, end_time)
