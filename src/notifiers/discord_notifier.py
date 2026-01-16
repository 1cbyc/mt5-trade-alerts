"""
Discord Notifier - Send notifications to Discord webhooks
"""
import logging
import aiohttp
from typing import Optional
from .notification_manager import AlertPriority

logger = logging.getLogger(__name__)


class DiscordNotifier:
    """Send notifications to Discord via webhook"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.enabled = True
    
    async def send_message(
        self,
        message: str,
        priority: AlertPriority = AlertPriority.NORMAL
    ) -> bool:
        """Send a text message to Discord"""
        if not self.enabled:
            return False
        
        try:
            # Discord color codes based on priority
            color_map = {
                AlertPriority.CRITICAL: 15158332,  # Red
                AlertPriority.IMPORTANT: 16776960,  # Yellow
                AlertPriority.NORMAL: 3447003       # Blue
            }
            
            color = color_map.get(priority, 3447003)
            
            # Discord embed format
            embed = {
                "title": "MT5 Trade Alert",
                "description": message,
                "color": color,
                "timestamp": None  # Will be set by Discord
            }
            
            payload = {
                "embeds": [embed]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status == 204:
                        return True
                    else:
                        logger.error(f"Discord webhook returned status {response.status}")
                        return False
        except Exception as e:
            logger.error(f"Failed to send Discord message: {e}")
            return False
    
    async def send_message_with_image(
        self,
        message: str,
        priority: AlertPriority = AlertPriority.NORMAL,
        title: Optional[str] = None,
        image_data: Optional[bytes] = None,
        image_filename: Optional[str] = None
    ) -> bool:
        """Send a message with image attachment to Discord"""
        if not self.enabled:
            return False
        
        try:
            color_map = {
                AlertPriority.CRITICAL: 15158332,
                AlertPriority.IMPORTANT: 16776960,
                AlertPriority.NORMAL: 3447003
            }
            
            color = color_map.get(priority, 3447003)
            
            embed = {
                "title": title or "MT5 Trade Alert",
                "description": message,
                "color": color
            }
            
            # For images, we need to use multipart/form-data
            if image_data:
                import io
                files = {
                    'file': (image_filename or 'chart.png', io.BytesIO(image_data), 'image/png')
                }
                
                payload = {
                    "embeds": [embed]
                }
                
                # Discord requires form-data for file uploads
                import json
                data = aiohttp.FormData()
                data.add_field('payload_json', json.dumps(payload))
                data.add_field('file', image_data, filename=image_filename or 'chart.png', content_type='image/png')
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(self.webhook_url, data=data) as response:
                        if response.status == 204:
                            return True
                        else:
                            logger.error(f"Discord webhook returned status {response.status}")
                            return False
            else:
                # No image, send as regular message
                return await self.send_message(message, priority)
        except Exception as e:
            logger.error(f"Failed to send Discord message with image: {e}")
            return False
