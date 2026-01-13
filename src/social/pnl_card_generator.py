"""
P&L Card Generator - Backend Service
Creates viral-ready social media cards for sharing trading performance
"""

import asyncio
import io
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import aiohttp

logger = logging.getLogger(__name__)

@dataclass
class PredictionResult:
    """Single prediction/trade result"""
    market: str
    prediction: str  # "YES" or "NO"
    entry_price: float
    exit_price: Optional[float]
    pnl_percentage: float
    volume: float
    timestamp: datetime
    is_open: bool = False

@dataclass
class PnLSnapshot:
    """Complete P&L snapshot for card generation"""
    username: str
    total_pnl_percentage: float
    total_pnl_usd: float
    total_volume: float
    predictions_count: int
    win_rate: float
    prediction_results: List[PredictionResult]
    period: str  # "daily" or "weekly"
    period_start: datetime
    period_end: datetime

class PnLCardGenerator:
    """Generate P&L cards with pure blue (#0001ff) aesthetic"""
    
    # Card dimensions (Instagram story ratio)
    CARD_WIDTH = 1080
    CARD_HEIGHT = 1350
    
    # Pure Blue Theme - DO NOT CHANGE (matches button color)
    COLOR_BG_DARK = (5, 5, 40)             # Very dark blue background
    COLOR_BG_LIGHT = (15, 15, 60)          # Lighter blue for contrast
    COLOR_PRIMARY_BLUE = (0, 1, 255)       # Pure blue (#0001ff)
    COLOR_BLUE_GLOW = (50, 100, 255)       # Glowing blue for effects
    COLOR_BLUE_LIGHT = (100, 150, 255)     # Light blue highlights
    COLOR_TEXT_PRIMARY = (255, 255, 255)    # White text
    COLOR_TEXT_SECONDARY = (200, 200, 230)  # Light gray-blue
    COLOR_POSITIVE = (0, 255, 100)          # Green (winning trades)
    COLOR_NEGATIVE = (255, 80, 80)          # Red (losing trades)
    COLOR_GLASS_WHITE = (255, 255, 255)     # White for glass effect
    
    def __init__(self, background_image_path: Optional[str] = None):
        """Initialize card generator"""
        self.background_image_path = background_image_path
        self._background_image = None
        self._load_background()
        
    def _load_background(self):
        """Load background image"""
        if self.background_image_path and Path(self.background_image_path).exists():
            try:
                self._background_image = Image.open(self.background_image_path)
                self._background_image = self._background_image.resize(
                    (self.CARD_WIDTH, self.CARD_HEIGHT), 
                    Image.Resampling.LANCZOS
                )
                logger.info(f"Loaded background image: {self.background_image_path}")
            except Exception as e:
                logger.error(f"Failed to load background image: {e}")
                self._create_default_background()
        else:
            self._create_default_background()
    
    def _create_default_background(self):
        """Create default cyberpunk background"""
        logger.info("Creating default background")
        img = Image.new('RGB', (self.CARD_WIDTH, self.CARD_HEIGHT), color=self.COLOR_BG_DARK)
        draw = ImageDraw.Draw(img)
        
        # Add gradient effect
        for y in range(self.CARD_HEIGHT):
            # Dark blue to lighter blue gradient
            progress = y / self.CARD_HEIGHT
            r = int(self.COLOR_BG_DARK[0] + (self.COLOR_BG_LIGHT[0] - self.COLOR_BG_DARK[0]) * progress)
            g = int(self.COLOR_BG_DARK[1] + (self.COLOR_BG_LIGHT[1] - self.COLOR_BG_DARK[1]) * progress)
            b = int(self.COLOR_BG_DARK[2] + (self.COLOR_BG_LIGHT[2] - self.COLOR_BG_DARK[2]) * progress)
            draw.line([(0, y), (self.CARD_WIDTH, y)], fill=(r, g, b))
        
        # Add grid pattern
        for x in range(0, self.CARD_WIDTH, 50):
            draw.line([(x, 0), (x, self.CARD_HEIGHT)], fill=(*self.COLOR_PRIMARY_BLUE, 30), width=1)
        for y in range(0, self.CARD_HEIGHT, 50):
            draw.line([(0, y), (self.CARD_WIDTH, y)], fill=(*self.COLOR_PRIMARY_BLUE, 30), width=1)
        
        # Add glow circles
        for _ in range(3):
            x = 200 + _ * 300
            y = 300 + _ * 200
            for radius in range(100, 20, -10):
                alpha = 30 - (radius - 20)
                draw.ellipse([x-radius, y-radius, x+radius, y+radius], 
                           outline=(*self.COLOR_BLUE_GLOW, alpha), width=2)
        
        self._background_image = img
    
    def _load_font(self, size: int) -> ImageFont.ImageFont:
        """Load font with fallback"""
        try:
            # Try custom font first
            return ImageFont.truetype("assets/fonts/Inter-Bold.ttf", size)
        except:
            try:
                # Try system fonts
                return ImageFont.truetype("arial.ttf", size)
            except:
                # Fallback to default
                return ImageFont.load_default()
    
    def _draw_glass_panel(self, draw: ImageDraw.ImageDraw, x: int, y: int, width: int, height: int, radius: int = 20):
        """Draw glass-like panel with blue tint"""
        # Main panel
        draw.rounded_rectangle([x, y, x+width, y+height], radius=radius, 
                              fill=(*self.COLOR_BG_DARK, 180), 
                              outline=(*self.COLOR_PRIMARY_BLUE, 100), width=2)
        
        # Glass effect - top highlight
        highlight_rect = [x+5, y+5, x+width-5, y+height//3]
        draw.rounded_rectangle(highlight_rect, radius=radius-5,
                              fill=(*self.COLOR_GLASS_WHITE, 20))
        
        # Glow effect
        for i in range(3):
            glow_rect = [x-i*2, y-i*2, x+width+i*2, y+height+i*2]
            draw.rounded_rectangle(glow_rect, radius=radius+i*2,
                                  outline=(*self.COLOR_BLUE_GLOW, 20-i*5), width=1)
    
    def _draw_header(self, draw: ImageDraw.ImageDraw, snapshot: PnLSnapshot):
        """Draw header section"""
        # Glass panel for header
        self._draw_glass_panel(draw, 40, 40, self.CARD_WIDTH-80, 150, 25)
        
        # Title
        title_font = self._load_font(48)
        subtitle_font = self._load_font(32)
        
        draw.text((60, 60), "CRYPTO PREDICT", fill=self.COLOR_PRIMARY_BLUE, font=title_font)
        draw.text((60, 110), f"@{snapshot.username}", fill=self.COLOR_TEXT_SECONDARY, font=subtitle_font)
        
        # Branding
        branding_font = self._load_font(24)
        draw.text((self.CARD_WIDTH-200, 60), "P&L REPORT", fill=self.COLOR_BLUE_LIGHT, font=branding_font)
    
    def _draw_main_stats(self, draw: ImageDraw.ImageDraw, snapshot: PnLSnapshot):
        """Draw main P&L statistics"""
        # Glass panel for stats
        panel_y = 210
        panel_height = 280
        self._draw_glass_panel(draw, 40, panel_y, self.CARD_WIDTH-80, panel_height, 25)
        
        # Main P&L percentage
        pnl_font = self._load_font(72)
        pnl_color = self.COLOR_POSITIVE if snapshot.total_pnl_percentage >= 0 else self.COLOR_NEGATIVE
        pnl_text = f"{snapshot.total_pnl_percentage:+.2f}%"
        
        # Center the P&L text
        bbox = draw.textbbox((0, 0), pnl_text, font=pnl_font)
        text_width = bbox[2] - bbox[0]
        x = (self.CARD_WIDTH - text_width) // 2
        draw.text((x, panel_y + 40), pnl_text, fill=pnl_color, font=pnl_font)
        
        # Sub-stats
        stats_font = self._load_font(28)
        stats_y = panel_y + 140
        
        # Win rate
        draw.text((80, stats_y), f"Win Rate", fill=self.COLOR_TEXT_SECONDARY, font=stats_font)
        draw.text((80, stats_y + 35), f"{snapshot.win_rate:.1f}%", fill=self.COLOR_PRIMARY_BLUE, font=self._load_font(36))
        
        # Volume
        draw.text((350, stats_y), "Volume", fill=self.COLOR_TEXT_SECONDARY, font=stats_font)
        volume_text = f"${snapshot.total_volume:,.0f}"
        draw.text((350, stats_y + 35), volume_text, fill=self.COLOR_PRIMARY_BLUE, font=self._load_font(36))
        
        # Trades
        draw.text((620, stats_y), "Trades", fill=self.COLOR_TEXT_SECONDARY, font=stats_font)
        draw.text((620, stats_y + 35), str(snapshot.predictions_count), fill=self.COLOR_PRIMARY_BLUE, font=self._load_font(36))
        
        # Period indicator
        period_font = self._load_font(24)
        period_text = snapshot.period.upper()
        bbox = draw.textbbox((0, 0), period_text, font=period_font)
        text_width = bbox[2] - bbox[0]
        x = (self.CARD_WIDTH - text_width) // 2
        draw.text((x, panel_y + 220), period_text, fill=self.COLOR_BLUE_LIGHT, font=period_font)
    
    def _draw_prediction_results(self, draw: ImageDraw.ImageDraw, snapshot: PnLSnapshot):
        """Draw recent prediction results"""
        if not snapshot.prediction_results:
            return
            
        # Glass panel for predictions
        panel_y = 520
        panel_height = 380
        self._draw_glass_panel(draw, 40, panel_y, self.CARD_WIDTH-80, panel_height, 25)
        
        # Title
        title_font = self._load_font(32)
        draw.text((60, panel_y + 20), "RECENT PREDICTIONS", fill=self.COLOR_PRIMARY_BLUE, font=title_font)
        
        # Draw up to 3 recent predictions
        recent_predictions = snapshot.prediction_results[:3]
        prediction_font = self._load_font(24)
        result_font = self._load_font(28)
        
        for i, pred in enumerate(recent_predictions):
            y_pos = panel_y + 80 + i * 100
            
            # Market name
            market_text = pred.market[:30] + "..." if len(pred.market) > 30 else pred.market
            draw.text((60, y_pos), market_text, fill=self.COLOR_TEXT_SECONDARY, font=prediction_font)
            
            # Prediction type
            pred_type = f"Prediction: {pred.prediction}"
            draw.text((60, y_pos + 25), pred_type, fill=self.COLOR_TEXT_PRIMARY, font=self._load_font(20))
            
            # P&L result
            pnl_color = self.COLOR_POSITIVE if pred.pnl_percentage >= 0 else self.COLOR_NEGATIVE
            pnl_text = f"{pred.pnl_percentage:+.2f}%"
            draw.text((self.CARD_WIDTH - 200, y_pos), pnl_text, fill=pnl_color, font=result_font)
            
            # Entry/exit prices
            if pred.exit_price:
                price_text = f"${pred.entry_price:.3f} → ${pred.exit_price:.3f}"
            else:
                price_text = f"Entry: ${pred.entry_price:.3f}"
            draw.text((60, y_pos + 50), price_text, fill=self.COLOR_BLUE_LIGHT, font=self._load_font(18))
    
    def _draw_footer(self, draw: ImageDraw.ImageDraw, snapshot: PnLSnapshot):
        """Draw footer with timestamp and call-to-action"""
        # Glass panel for footer
        panel_y = 930
        panel_height = 120
        self._draw_glass_panel(draw, 40, panel_y, self.CARD_WIDTH-80, panel_height, 25)
        
        # Timestamp
        timestamp_font = self._load_font(20)
        timestamp_text = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}"
        draw.text((60, panel_y + 25), timestamp_text, fill=self.COLOR_TEXT_SECONDARY, font=timestamp_font)
        
        # Call-to-action
        cta_font = self._load_font(24)
        cta_text = "Share your trading results!"
        bbox = draw.textbbox((0, 0), cta_text, font=cta_font)
        text_width = bbox[2] - bbox[0]
        x = (self.CARD_WIDTH - text_width) // 2
        draw.text((x, panel_y + 55), cta_text, fill=self.COLOR_PRIMARY_BLUE, font=cta_font)
        
        # URL
        url_font = self._load_font(18)
        url_text = "cryptopredict.monitor"
        bbox = draw.textbbox((0, 0), url_text, font=url_font)
        text_width = bbox[2] - bbox[0]
        x = (self.CARD_WIDTH - text_width) // 2
        draw.text((x, panel_y + 85), url_text, fill=self.COLOR_BLUE_LIGHT, font=url_font)
    
    def generate_card(self, snapshot: PnLSnapshot) -> Image.Image:
        """Generate complete P&L card"""
        # Create base image
        card = self._background_image.copy()
        draw = ImageDraw.Draw(card)
        
        # Draw all sections
        self._draw_header(draw, snapshot)
        self._draw_main_stats(draw, snapshot)
        self._draw_prediction_results(draw, snapshot)
        self._draw_footer(draw, snapshot)
        
        return card
    
    def card_to_bytes(self, card: Image.Image) -> bytes:
        """Convert card image to bytes"""
        img_buffer = io.BytesIO()
        card.save(img_buffer, format='PNG', optimize=True)
        return img_buffer.getvalue()

class PnLCardService:
    """Service for generating P&L cards with database integration"""
    
    def __init__(self, db_connection=None, background_image_path: Optional[str] = None):
        """Initialize P&L card service"""
        self.db = db_connection
        self.generator = PnLCardGenerator(background_image_path)
        
    async def fetch_predictions_in_period(
        self, 
        user_id: str, 
        start_time: datetime, 
        end_time: datetime
    ) -> List[PredictionResult]:
        """Fetch predictions from database - implement based on your DB"""
        
        # Check database type and use appropriate fetcher
        if hasattr(self.db, 'session'):  # SQLAlchemy
            return await self._fetch_sqlalchemy(user_id, start_time, end_time)
        elif hasattr(self.db, 'table'):  # Supabase
            return await self._fetch_supabase(user_id, start_time, end_time)
        elif hasattr(self.db, 'executions'):  # MongoDB
            return await self._fetch_mongodb(user_id, start_time, end_time)
        else:
            return await self._fetch_mock_data(user_id, start_time, end_time)
    
    async def _fetch_sqlalchemy(
        self, 
        user_id: str, 
        start_time: datetime, 
        end_time: datetime
    ) -> List[PredictionResult]:
        """Fetch predictions from SQLAlchemy ORM"""
        try:
            from sqlalchemy import text
            from datetime import datetime
            
            # Query executions table for user's trades in period
            query = text("""
                SELECT 
                    market,
                    side as prediction_type,
                    entry_price,
                    exit_price,
                    quantity as volume,
                    entry_timestamp as timestamp,
                    status,
                    pnl,
                    CASE 
                        WHEN exit_price IS NOT NULL AND entry_price IS NOT NULL 
                        THEN ((exit_price - entry_price) / entry_price) * 100 
                        ELSE 0 
                    END as pnl_percentage
                FROM executions 
                WHERE user_id = :user_id 
                    AND entry_timestamp >= :start_time 
                    AND entry_timestamp <= :end_time
                    AND status IN ('open', 'closed')
                ORDER BY entry_timestamp DESC
                LIMIT 50
            """)
            
            result = self.db.session.execute(query, {
                'user_id': user_id,
                'start_time': start_time,
                'end_time': end_time
            })
            
            rows = result.fetchall()
            
            return [
                PredictionResult(
                    market=row.market,
                    prediction=row.prediction_type.upper(),
                    entry_price=float(row.entry_price),
                    exit_price=float(row.exit_price) if row.exit_price else None,
                    pnl_percentage=float(row.pnl_percentage),
                    volume=float(row.volume or 0),
                    timestamp=row.timestamp,
                    is_open=row.status == 'open'
                )
                for row in rows
            ]
            
        except Exception as e:
            logger.error(f"SQLAlchemy fetch error: {e}")
            return []
    
    async def _fetch_mongodb(
        self, 
        user_id: str, 
        start_time: datetime, 
        end_time: datetime
    ) -> List[PredictionResult]:
        """Fetch predictions from MongoDB"""
        # TODO: Implement your MongoDB query
        # Example:
        # results = await self.db.predictions.find({
        #     'user_id': user_id,
        #     'timestamp': {'$gte': start_time, '$lte': end_time}
        # }).sort('timestamp', -1).to_list(None)
        return []
    
    async def _fetch_mock_data(
        self, 
        user_id: str, 
        start_time: datetime, 
        end_time: datetime
    ) -> List[PredictionResult]:
        """Mock data for testing"""
        return [
            PredictionResult(
                market="Bitcoin > $100K End of 2024",
                prediction="YES",
                entry_price=0.65,
                exit_price=0.72,
                pnl_percentage=10.77,
                volume=1000,
                timestamp=datetime.utcnow() - timedelta(hours=2),
                is_open=False
            ),
            PredictionResult(
                market="Trump 2024 Election",
                prediction="NO", 
                entry_price=0.45,
                exit_price=0.42,
                pnl_percentage=6.67,
                volume=500,
                timestamp=datetime.utcnow() - timedelta(hours=4),
                is_open=False
            ),
            PredictionResult(
                market="Ethereum > $5K End of 2024",
                prediction="YES",
                entry_price=0.35,
                exit_price=None,
                pnl_percentage=0.0,
                volume=750,
                timestamp=datetime.utcnow() - timedelta(hours=1),
                is_open=True
            )
        ]
    
    def _calculate_pnl(self, entry_price: float, exit_price: Optional[float]) -> float:
        """Calculate P&L percentage"""
        if exit_price is None:
            return 0.0
        return ((exit_price - entry_price) / entry_price) * 100
    
    async def generate_user_snapshot(self, user_id: str) -> Optional[PnLSnapshot]:
        """Generate P&L snapshot for user"""
        
        # Try daily first
        now = datetime.utcnow()
        daily_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        daily_end = daily_start + timedelta(days=1)
        
        predictions = await self.fetch_predictions_in_period(user_id, daily_start, daily_end)
        
        # Fall back to weekly if no daily data
        period = "daily"
        if not predictions:
            period = "weekly"
            weekly_start = now - timedelta(days=7)
            weekly_start = weekly_start.replace(hour=0, minute=0, second=0, microsecond=0)
            predictions = await self.fetch_predictions_in_period(user_id, weekly_start, now)
        
        if not predictions:
            return None
        
        # Calculate stats
        total_pnl = sum(p.pnl_percentage for p in predictions)
        total_volume = sum(p.volume for p in predictions)
        winning_trades = sum(1 for p in predictions if p.pnl_percentage > 0)
        win_rate = (winning_trades / len(predictions)) * 100 if predictions else 0
        
        # Estimate USD P&L (simplified)
        total_pnl_usd = total_volume * (total_pnl / 100) * 0.1  # Rough estimate
        
        return PnLSnapshot(
            username=user_id,  # TODO: Get actual username
            total_pnl_percentage=total_pnl,
            total_pnl_usd=total_pnl_usd,
            total_volume=total_volume,
            predictions_count=len(predictions),
            win_rate=win_rate,
            prediction_results=predictions,
            period=period,
            period_start=daily_start if period == "daily" else now - timedelta(days=7),
            period_end=daily_end if period == "daily" else now
        )
    
    async def generate_card_bytes(self, user_id: str) -> Tuple[Optional[bytes], Optional[PnLSnapshot]]:
        """Generate card bytes for user"""
        try:
            snapshot = await self.generate_user_snapshot(user_id)
            if not snapshot:
                return None, None
            
            card = self.generator.generate_card(snapshot)
            card_bytes = self.generator.card_to_bytes(card)
            
            return card_bytes, snapshot
        except Exception as e:
            logger.error(f"Error generating card for {user_id}: {e}")
            return None, None
