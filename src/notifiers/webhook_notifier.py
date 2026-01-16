"""
Webhook Notifier - Send notifications to custom webhooks
"""
import logging
import aiohttp
import json
from typing import Optional, Dict, Any
from .notification_manager import AlertPriority

logger = logging.getLogger(__name__)


class WebhookNotifier:
    """Send notifications to custom webhooks"""
    
    def __init__(self, webhook_url: str, headers: Optional[Dict[str, str]] = None):
        self.webhook_url = webhook_url
        self.headers = headers or {'Content-Type': 'application/json'}
        self.enabled = True
    
    async def send_message(
        self,
        message: str,
        priority: AlertPriority = AlertPriority.NORMAL
    ) -> bool:
        """Send a JSON payload to webhook"""
        if not self.enabled:
            return False
        
        try:
            payload = {
                "priority": priority.value,
                "message": message,
                "source": "mt5-trade-alerts"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    headers=self.headers
                ) as response:
                    if response.status in [200, 201, 204]:
                        return True
                    else:
                        logger.error(f"Webhook returned status {response.status}")
                        return False
        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")
            return False
    
    async def send_message_with_image(
        self,
        message: str,
        priority: AlertPriority = AlertPriority.NORMAL,
        title: Optional[str] = None,
        image_data: Optional[bytes] = None,
        image_filename: Optional[str] = None
    ) -> bool:
        """Send webhook notification with image (base64 encoded)"""
        if not self.enabled:
            return False
        
        try:
            import base64
            
            payload = {
                "priority": priority.value,
                "title": title or "MT5 Trade Alert",
                "message": message,
                "source": "mt5-trade-alerts"
            }
            
            # Add image as base64 if provided
            if image_data:
                image_b64 = base64.b64encode(image_data).decode('utf-8')
                payload["image"] = {
                    "data": image_b64,
                    "filename": image_filename or "chart.png",
                    "content_type": "image/png"
                }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    headers=self.headers
                ) as response:
                    if response.status in [200, 201, 204]:
                        return True
                    else:
                        logger.error(f"Webhook returned status {response.status}")
                        return False
        except Exception as e:
            logger.error(f"Failed to send webhook notification with image: {e}")
            return False
