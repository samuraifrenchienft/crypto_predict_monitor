"""
P&L Card Generator - Complete Setup Guide
"""

# P&L Card Generator - Complete Setup Guide

## Overview

Generate viral-ready P&L (Profit & Loss) cards for users to share on social media. The system:
- **Fetches daily P&L** from user's prediction history
- **Falls back to weekly** if no trades today
- **Creates branded cards** with custom background image
- **Shows 3 most recent predictions** with P&L %
- **Provides download & sharing options** (Twitter, Discord, clipboard)
- **Pure Blue (#0001ff) aesthetic** with glow, lighting, and glass-like effects

---

## File Structure

```
src/
├── social/
│   ├── __init__.py
│   └── pnl_card_generator.py        ← Backend card generation
├── components/
│   └── PnLCardButton.jsx            ← React UI component
├── api/
│   └── routes/
│       └── pnl_cards.py             ← Flask/FastAPI endpoints
└── utils/
    └── s3_uploader.py               ← Optional cloud storage

assets/
└── valhalla_viral_bg.png            ← Your viral background image (1080x1350)
```

---

## Step 1: Install Dependencies

```bash
# Backend
pip install Pillow>=9.0.0          # Image processing
pip install boto3>=1.26.0          # AWS S3 (optional)

# Frontend (already in package.json)
# lucide-react for icons
```

---

## Step 2: Background Image

✅ **Already created**: `assets/valhalla_viral_bg.png` (1080x1350)

Features:
- Pure blue (#0001ff) cyberpunk aesthetic
- Grid patterns and glow effects
- Glass-like transparency
- Optimized for social media sharing

---

## Step 3: Initialize Backend Service

Add to your `main.py`:

```python
import asyncio
import logging
from src.social.pnl_card_generator import PnLCardService
from src.api.routes.pnl_cards import init_pnl_service, pnl_bp
from src.utils.s3_uploader import init_s3_uploader

logger = logging.getLogger(__name__)

async def initialize_services(app, db_connection):
    """Initialize all services including P&L card generator"""
    
    # Initialize P&L card service
    init_pnl_service(
        db_connection=db_connection,
        background_image_path="assets/valhalla_viral_bg.png"
    )
    
    # Register Flask routes
    app.register_blueprint(pnl_bp)
    
    # Optional: Initialize S3 for cloud storage
    s3_bucket = os.getenv('AWS_S3_BUCKET')
    if s3_bucket:
        init_s3_uploader(s3_bucket, os.getenv('AWS_REGION', 'us-east-1'))
    
    logger.info("✅ P&L Card Service initialized")

# In your app startup
if __name__ == "__main__":
    app = create_app()
    db_connection = get_db_connection()  # Your existing DB connection
    
    asyncio.run(initialize_services(app, db_connection))
    app.run()
```

---

## Step 4: Database Integration

Choose your database type and implement in `src/social/pnl_card_generator.py`:

### For SQLAlchemy (most common):
```python
async def fetch_predictions_in_period(self, user_id: str, start_time, end_time):
    from your_models import Prediction
    
    results = self.db.session.query(Prediction).filter(
        Prediction.user_id == user_id,
        Prediction.timestamp >= start_time,
        Prediction.timestamp <= end_time,
        Prediction.status.in_(['closed', 'settled', 'open'])
    ).order_by(Prediction.timestamp.desc()).limit(50).all()
    
    return [
        PredictionResult(
            market=r.market_name,
            prediction=r.prediction_type.upper(),
            entry_price=float(r.entry_price),
            exit_price=float(r.exit_price) if r.exit_price else None,
            pnl_percentage=self._calculate_pnl(r.entry_price, r.exit_price),
            volume=float(r.volume or 0),
            timestamp=r.timestamp,
            is_open=r.status == 'open'
        )
        for r in results
    ]
```

### For MongoDB:
```python
async def fetch_predictions_in_period(self, user_id: str, start_time, end_time):
    results = await self.db.predictions.find({
        'user_id': user_id,
        'timestamp': {'$gte': start_time, '$lte': end_time}
    }).sort('timestamp', -1).limit(50).to_list(None)
    
    return [
        PredictionResult(
            market=r['market'],
            prediction=r['prediction'].upper(),
            entry_price=float(r['entry_price']),
            exit_price=float(r.get('exit_price')),
            pnl_percentage=self._calculate_pnl(r['entry_price'], r.get('exit_price')),
            volume=float(r.get('volume', 0)),
            timestamp=r['timestamp'],
            is_open=r['status'] == 'open'
        )
        for r in results
    ]
```

See `src/database_integration_examples.py` for more database options.

---

## Step 5: API Endpoints

✅ **Already created**: `src/api/routes/pnl_cards.py`

Endpoints:
- `GET /api/pnl-card/<user_id>` - Download PNG card
- `GET /api/pnl-card/<user_id>/share` - Get share metadata
- `GET /api/pnl-card/health` - Health check

Features:
- Authentication required
- Rate limiting (5 requests per 5 minutes)
- Error handling
- Share text generation

---

## Step 6: React Integration

Add to your P&L component:

```jsx
import PnLCardButton from '@/components/PnLCardButton';

export function PnLPopup({ user, pnlData }) {
  return (
    <div className="p-6 bg-gray-900 rounded-lg border border-cyan-500">
      <h2 className="text-2xl font-bold mb-6">Your P&L Dashboard</h2>
      
      {/* Existing P&L stats */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div>
          <p className="text-gray-400">Total Return</p>
          <p className="text-3xl font-bold text-green-400">+{pnlData.percentage.toFixed(2)}%</p>
        </div>
        <div>
          <p className="text-gray-400">Total Volume</p>
          <p className="text-3xl font-bold">${pnlData.volume.toLocaleString()}</p>
        </div>
      </div>
      
      {/* P&L Card Generator Button */}
      <div className="border-t border-gray-700 pt-6">
        <h3 className="text-lg font-semibold mb-4">Share Your Stats</h3>
        <PnLCardButton 
          userId={user.id}
          currentPnL={pnlData}
          predictions={user.predictions}
        />
      </div>
    </div>
  );
}
```

---

## Step 7: Customization

### Colors (Pure Blue Theme):
```python
# In PnLCardGenerator class
COLOR_PRIMARY_BLUE = (0, 1, 255)       # Pure blue (#0001ff)
COLOR_BG_DARK = (5, 5, 40)             # Dark blue background
COLOR_BLUE_GLOW = (50, 100, 255)       # Glowing blue
COLOR_POSITIVE = (0, 255, 100)          # Green for wins
COLOR_NEGATIVE = (255, 80, 80)          # Red for losses
```

### Fonts:
Add custom fonts to `assets/fonts/` and update `_load_font()` method.

### Layout:
Modify `_draw_*` methods in `PnLCardGenerator`:
- `_draw_header()` - Title and branding
- `_draw_main_stats()` - P&L, win rate, volume
- `_draw_prediction_results()` - Recent trades
- `_draw_footer()` - Timestamp and CTA

---

## Step 8: Optional S3 Integration

For cloud storage and sharing:

```python
# Set environment variables
AWS_S3_BUCKET=your-bucket-name
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-1

# S3 is automatically initialized if bucket is set
# Cards will be uploaded and public URLs returned
```

---

## Testing

### Backend Test:
```python
# tests/test_pnl_card_generator.py
import pytest
from src.social.pnl_card_generator import PnLCardService

@pytest.mark.asyncio
async def test_card_generation():
    service = PnLCardService()
    
    # Test with mock data
    card_bytes, snapshot = await service.generate_card_bytes("test_user")
    
    assert card_bytes is not None
    assert snapshot is not None
    assert len(card_bytes) > 0
```

### Frontend Test:
```jsx
// Test component renders and generates cards
import { render, screen, fireEvent } from '@testing-library/react';
import PnLCardButton from '@/components/PnLCardButton';

test('generates card on click', async () => {
  render(<PnLCardButton userId="test_user" />);
  
  const button = screen.getByText('Generate P&L Card');
  fireEvent.click(button);
  
  // Should show loading state
  expect(screen.getByText('Generating your P&L card...')).toBeInTheDocument();
});
```

---

## Environment Variables

```bash
# Required for production
DATABASE_URL=your_database_connection
SECRET_KEY=your_app_secret

# Optional for S3 storage
AWS_S3_BUCKET=your-bucket-name
AWS_ACCESS_KEY_ID=your-access-key  
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-1

# Optional for API rate limiting
REDIS_URL=redis://localhost:6379
```

---

## Deployment Checklist

- [x] Background image created (`assets/valhalla_viral_bg.png`)
- [x] Backend service implemented (`src/social/pnl_card_generator.py`)
- [x] API routes created (`src/api/routes/pnl_cards.py`)
- [x] React component ready (`src/components/PnLCardButton.jsx`)
- [x] Database integration examples provided
- [x] S3 uploader utility available
- [ ] Database queries implemented (choose your DB type)
- [ ] Authentication integrated with your existing system
- [ ] Environment variables configured
- [ ] Rate limiting tested
- [ ] Error handling verified
- [ ] Card generation tested with real data

---

## Features Summary

✅ **Pure Blue Aesthetic** - #0001ff color scheme with glow effects
✅ **Glass Morphism** - Modern, premium visual design
✅ **Daily/Weekly Data** - Smart fallback for inactive users
✅ **Social Sharing** - Twitter, Discord, clipboard options
✅ **Cloud Storage** - Optional S3 integration
✅ **Rate Limiting** - Prevents abuse
✅ **Error Handling** - Graceful failure modes
✅ **Mobile Optimized** - 1080x1350 for Instagram Stories
✅ **Performance** - Optimized PNG generation
✅ **Security** - Authentication required

---

## Support

For issues:
1. Check database connection and user has predictions
2. Verify background image path exists
3. Check authentication is working
4. Review logs for error messages
5. Test with mock data first

That's it! Your P&L card sharing system is ready to go viral! 🚀
