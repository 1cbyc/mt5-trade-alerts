"""
Notification Manager - Handles multiple notification channels
Supports: Telegram, Discord, Email, Webhooks
"""
import logging
from typing import Dict, List, Optional, Any
from enum import Enum
import asyncio

logger = logging.getLogger(__name__)


class AlertPriority(Enum):
    """Alert priority levels"""
    CRITICAL = "critical"
    IMPORTANT = "important"
    NORMAL = "normal"


class NotificationManager:
    """Manages notifications across multiple channels"""
    
    def __init__(self):
        self.channels = {}
        self.enabled_channels = set()
    
    def register_channel(self, name: str, channel: Any):
        """Register a notification channel"""
        self.channels[name] = channel
        logger.info(f"Registered notification channel: {name}")
    
    def enable_channel(self, name: str):
        """Enable a notification channel"""
        if name in self.channels:
            self.enabled_channels.add(name)
            logger.info(f"Enabled notification channel: {name}")
        else:
            logger.warning(f"Channel {name} not registered")
    
    def disable_channel(self, name: str):
        """Disable a notification channel"""
        self.enabled_channels.discard(name)
        logger.info(f"Disabled notification channel: {name}")
    
    async def send_notification(
        self,
        message: str,
        priority: AlertPriority = AlertPriority.NORMAL,
        title: Optional[str] = None,
        image_data: Optional[bytes] = None,
        image_filename: Optional[str] = None,
        channels: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """
        Send notification to all enabled channels (or specified channels)
        
        Args:
            message: Message content
            priority: Alert priority level
            title: Optional title for the notification
            image_data: Optional image bytes to attach
            image_filename: Optional filename for the image
            channels: Optional list of specific channels to use (None = all enabled)
        
        Returns:
            Dictionary mapping channel names to success status
        """
        results = {}
        target_channels = channels if channels else list(self.enabled_channels)
        
        for channel_name in target_channels:
            if channel_name not in self.channels:
                logger.warning(f"Channel {channel_name} not registered")
                results[channel_name] = False
                continue
            
            channel = self.channels[channel_name]
            try:
                # Try to send with image if provided
                if image_data and hasattr(channel, 'send_message_with_image'):
                    success = await channel.send_message_with_image(
                        message=message,
                        priority=priority,
                        title=title,
                        image_data=image_data,
                        image_filename=image_filename
                    )
                elif hasattr(channel, 'send_message'):
                    # Fallback to text-only
                    formatted_message = self._format_message_with_priority(
                        message, priority, title, channel_name
                    )
                    success = await channel.send_message(formatted_message, priority=priority)
                else:
                    logger.warning(f"Channel {channel_name} doesn't support send_message")
                    success = False
                
                results[channel_name] = success
            except Exception as e:
                logger.error(f"Error sending notification to {channel_name}: {e}")
                results[channel_name] = False
        
        return results
    
    def _format_message_with_priority(
        self,
        message: str,
        priority: AlertPriority,
        title: Optional[str],
        channel: str
    ) -> str:
        """Format message with priority indicators based on channel"""
        priority_indicators = {
            AlertPriority.CRITICAL: {
                'telegram': '🚨',
                'discord': '🔴',
                'email': '[CRITICAL]',
                'webhook': 'CRITICAL'
            },
            AlertPriority.IMPORTANT: {
                'telegram': '⚠️',
                'discord': '🟡',
                'email': '[IMPORTANT]',
                'webhook': 'IMPORTANT'
            },
            AlertPriority.NORMAL: {
                'telegram': 'ℹ️',
                'discord': '🔵',
                'email': '',
                'webhook': 'NORMAL'
            }
        }
        
        indicator = priority_indicators.get(priority, {}).get(channel, '')
        prefix = f"{indicator} " if indicator else ""
        
        if title:
            return f"{prefix}{title}\n\n{message}"
        return f"{prefix}{message}"
