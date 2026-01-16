"""
S3 Uploader Utility
Optional cloud storage for P&L card sharing
"""

import boto3
import logging
from datetime import datetime
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class S3Uploader:
    """Upload P&L cards to AWS S3 for public sharing"""
    
    def __init__(self, bucket_name: str, aws_region: str = 'us-east-1'):
        """Initialize S3 uploader"""
        self.bucket_name = bucket_name
        self.aws_region = aws_region
        
        try:
            self.s3_client = boto3.client('s3')
            logger.info(f"S3 uploader initialized for bucket: {bucket_name}")
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            self.s3_client = None
    
    async def upload_card_to_s3(self, card_bytes: bytes, user_id: str) -> Optional[str]:
        """Upload card image to S3 and return public URL"""
        
        if not self.s3_client:
            logger.error("S3 client not initialized")
            return None
        
        try:
            # Generate unique key
            timestamp = datetime.utcnow().isoformat().replace(':', '-')
            key = f"pnl-cards/{user_id}/{timestamp}.png"
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=card_bytes,
                ContentType='image/png',
                ACL='public-read',  # Make publicly accessible
                Metadata={
                    'user_id': user_id,
                    'generated_at': datetime.utcnow().isoformat()
                }
            )
            
            # Return public URL
            url = f"https://{self.bucket_name}.s3.{self.aws_region}.amazonaws.com/{key}"
            logger.info(f"Uploaded card to S3: {url}")
            return url
            
        except Exception as e:
            logger.error(f"Failed to upload card to S3: {e}")
            return None
    
    async def delete_card(self, user_id: str, timestamp: str) -> bool:
        """Delete a card from S3"""
        
        if not self.s3_client:
            return False
        
        try:
            key = f"pnl-cards/{user_id}/{timestamp}.png"
            
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
            
            logger.info(f"Deleted card from S3: {key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete card from S3: {e}")
            return False
    
    async def list_user_cards(self, user_id: str, limit: int = 10) -> list:
        """List all cards for a user"""
        
        if not self.s3_client:
            return []
        
        try:
            prefix = f"pnl-cards/{user_id}/"
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=limit
            )
            
            cards = []
            for obj in response.get('Contents', []):
                url = f"https://{self.bucket_name}.s3.{self.aws_region}.amazonaws.com/{obj['Key']}"
                cards.append({
                    'key': obj['Key'],
                    'url': url,
                    'size': obj['Size'],
                    'last_modified': obj['LastModified']
                })
            
            return cards
            
        except Exception as e:
            logger.error(f"Failed to list user cards: {e}")
            return []

# Global instance (will be initialized if S3 is configured)
s3_uploader: Optional[S3Uploader] = None

def init_s3_uploader(bucket_name: str, aws_region: str = 'us-east-1'):
    """Initialize S3 uploader"""
    global s3_uploader
    s3_uploader = S3Uploader(bucket_name, aws_region)
    return s3_uploader

def is_s3_available() -> bool:
    """Check if S3 uploader is available"""
    return s3_uploader is not None and s3_uploader.s3_client is not None
