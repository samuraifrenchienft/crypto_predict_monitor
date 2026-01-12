"""
Alchemy Webhook Management Utility
Creates and manages webhooks for real-time transaction monitoring
"""

import os
import httpx
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class AlchemyWebhookManager:
    """Manages Alchemy webhooks for transaction monitoring"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("ALCHEMY_API_KEY")
        self.base_url = "https://dashboard.alchemy.com/api"
        self.webhook_url = os.getenv("WEBHOOK_URL", "https://your-domain.com/api/webhooks/wallet-activity")
        
        if not self.api_key:
            raise ValueError("Alchemy API key is required")
    
    async def create_address_activity_webhook(
        self,
        user_id: str,
        wallet_address: str,
        network: str = "eth_mainnet"
    ) -> Dict[str, any]:
        """
        Create a webhook to monitor address activity
        
        Args:
            user_id: User identifier for tracking
            wallet_address: Ethereum address to monitor
            network: Network to monitor (eth_mainnet, polygon_mainnet, etc.)
        
        Returns:
            Webhook creation response
        """
        webhook_data = {
            "name": f"Trade Tracker - {user_id}",
            "url": self.webhook_url,
            "type": "ADDRESS_ACTIVITY",
            "network": network,
            "addresses": [wallet_address.lower()],
            "activity_types": [
                "EXTERNAL",
                "INTERNAL",
                "ERC20",
                "ERC721",
                "ERC1155"
            ],
            "is_active": True
        }
        
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "X-Alchemy-API-Key": self.api_key
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/webhooks",
                    headers=headers,
                    json=webhook_data
                )
                
                if response.status_code == 201:
                    webhook = response.json()
                    logger.info(f"Created webhook {webhook['id']} for address {wallet_address}")
                    
                    # Store webhook mapping in database
                    await self.store_webhook_mapping(user_id, wallet_address, webhook['id'])
                    
                    return webhook
                else:
                    logger.error(f"Failed to create webhook: {response.text}")
                    raise Exception(f"Webhook creation failed: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Error creating webhook: {e}")
            raise
    
    async def update_webhook_addresses(
        self,
        webhook_id: str,
        addresses: List[str]
    ) -> Dict[str, any]:
        """Update webhook to monitor additional addresses"""
        
        update_data = {
            "addresses": [addr.lower() for addr in addresses]
        }
        
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "X-Alchemy-API-Key": self.api_key
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{self.base_url}/webhooks/{webhook_id}",
                    headers=headers,
                    json=update_data
                )
                
                if response.status_code == 200:
                    webhook = response.json()
                    logger.info(f"Updated webhook {webhook_id} with {len(addresses)} addresses")
                    return webhook
                else:
                    logger.error(f"Failed to update webhook: {response.text}")
                    raise Exception(f"Webhook update failed: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Error updating webhook: {e}")
            raise
    
    async def delete_webhook(self, webhook_id: str) -> bool:
        """Delete a webhook"""
        
        headers = {
            "accept": "application/json",
            "X-Alchemy-API-Key": self.api_key
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.base_url}/webhooks/{webhook_id}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    logger.info(f"Deleted webhook {webhook_id}")
                    return True
                else:
                    logger.error(f"Failed to delete webhook: {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error deleting webhook: {e}")
            return False
    
    async def list_webhooks(self) -> List[Dict[str, any]]:
        """List all webhooks for the API key"""
        
        headers = {
            "accept": "application/json",
            "X-Alchemy-API-Key": self.api_key
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/webhooks",
                    headers=headers
                )
                
                if response.status_code == 200:
                    return response.json().get("webhooks", [])
                else:
                    logger.error(f"Failed to list webhooks: {response.text}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error listing webhooks: {e}")
            return []
    
    async def get_webhook(self, webhook_id: str) -> Optional[Dict[str, any]]:
        """Get webhook details"""
        
        headers = {
            "accept": "application/json",
            "X-Alchemy-API-Key": self.api_key
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/webhooks/{webhook_id}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Failed to get webhook: {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting webhook: {e}")
            return None
    
    async def store_webhook_mapping(
        self,
        user_id: str,
        wallet_address: str,
        webhook_id: str
    ):
        """Store webhook mapping in database"""
        # This would integrate with your database (Supabase, etc.)
        # For now, just log it
        logger.info(f"Stored mapping: user={user_id}, wallet={wallet_address}, webhook={webhook_id}")
        
        # Example Supabase implementation:
        """
        from supabase import create_client
        
        supabase = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_SERVICE_KEY")
        )
        
        supabase.table("webhook_mappings").insert({
            "user_id": user_id,
            "wallet_address": wallet_address,
            "webhook_id": webhook_id,
            "created_at": datetime.utcnow().isoformat()
        }).execute()
        """
    
    async def get_user_webhook(self, user_id: str) -> Optional[str]:
        """Get webhook ID for a user"""
        # This would query your database
        # For now, return None
        return None
    
    async def create_or_update_user_webhook(
        self,
        user_id: str,
        wallet_address: str,
        network: str = "eth_mainnet"
    ) -> Dict[str, any]:
        """
        Create webhook for user or update existing one
        """
        # Check if user already has a webhook
        existing_webhook_id = await self.get_user_webhook(user_id)
        
        if existing_webhook_id:
            # Get existing webhook details
            webhook = await self.get_webhook(existing_webhook_id)
            if webhook:
                # Add new address to existing webhook
                addresses = webhook.get("addresses", [])
                if wallet_address.lower() not in [addr.lower() for addr in addresses]:
                    addresses.append(wallet_address)
                    return await self.update_webhook_addresses(existing_webhook_id, addresses)
                else:
                    logger.info(f"Address {wallet_address} already monitored by webhook {existing_webhook_id}")
                    return webhook
        
        # Create new webhook
        return await self.create_address_activity_webhook(user_id, wallet_address, network)

# Utility functions for webhook processing
def parse_alchemy_webhook(data: Dict[str, any]) -> List[Dict[str, any]]:
    """Parse Alchemy webhook data into transaction activities"""
    
    activities = []
    
    # Handle different webhook types
    if data.get("type") == "ADDRESS_ACTIVITY":
        for activity in data.get("activity", []):
            parsed_activity = {
                "from": activity.get("fromAddress"),
                "to": activity.get("toAddress"),
                "value": activity.get("value"),
                "hash": activity.get("hash"),
                "timestamp": activity.get("timestamp"),
                "block_number": activity.get("blockNumber"),
                "gas": activity.get("gas"),
                "gas_price": activity.get("gasPrice"),
                "input": activity.get("input"),
                "asset": activity.get("asset"),
                "category": activity.get("category"),
                "erc1155_metadata": activity.get("erc1155Metadata"),
                "tokenId": activity.get("tokenId"),
                "amount": activity.get("amount")
            }
            activities.append(parsed_activity)
    
    return activities

def is_market_transaction(activity: Dict[str, any]) -> bool:
    """Check if transaction is related to supported markets"""
    
    # Check known market addresses
    market_addresses = {
        "polymarket": [
            "0x4bF53B9B888197B09A09e6dC3fea0837eBBdF5aB",  # CTF Exchange
            "0x8b6f69c4297e3461e1c0d3643e639c444c4af642",  # CTF Exchange 2
            # Add more as needed
        ],
        "kalshi": [
            # Add Kalshi contract addresses when available
        ]
    }
    
    to_address = activity.get("to", "").lower()
    
    for market, addresses in market_addresses.items():
        if to_address in [addr.lower() for addr in addresses]:
            return True
    
    # Could also check transaction input data for market-specific patterns
    input_data = activity.get("input", "")
    if input_data and len(input_data) > 10:
        # Add logic to parse function selectors
        pass
    
    return False

def detect_market_from_transaction(activity: Dict[str, any]) -> Optional[str]:
    """Detect which market a transaction belongs to"""
    
    market_addresses = {
        "polymarket": [
            "0x4bF53B9B888197B09A09e6dC3fea0837eBBdF5aB",
            "0x8b6f69c4297e3461e1c0d3643e639c444c4af642",
        ],
        "kalshi": [
            # Add Kalshi addresses
        ]
    }
    
    to_address = activity.get("to", "").lower()
    
    for market, addresses in market_addresses.items():
        if to_address in [addr.lower() for addr in addresses]:
            return market
    
    return None

# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def main():
        manager = AlchemyWebhookManager()
        
        # Create webhook for a user
        webhook = await manager.create_address_activity_webhook(
            user_id="user123",
            wallet_address="0x742d3586634E2c6c0a9E6e4e4e4e4e4e4e4e4e4e4",
            network="eth_mainnet"
        )
        
        print(f"Created webhook: {webhook['id']}")
        
        # List all webhooks
        webhooks = await manager.list_webhooks()
        print(f"Total webhooks: {len(webhooks)}")
    
    asyncio.run(main())
