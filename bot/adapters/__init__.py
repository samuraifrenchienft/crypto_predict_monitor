"""
Bot Adapters Package
Contains adapters for different prediction market platforms
"""

from .base import Adapter
from .polymarket import PolymarketAdapter
from .azuro import AzuroAdapter

__all__ = [
    "Adapter",
    "PolymarketAdapter", 
    "AzuroAdapter"
]