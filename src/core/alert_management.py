"""
Alert Management - Core classes for rate limiting, grouping, and quiet hours
"""
import logging
from datetime import datetime, time
from collections import defaultdict, deque
from typing import Dict, List

logger = logging.getLogger(__name__)


class AlertRateLimiter:
    """Rate limiter to prevent alert spam"""
    def __init__(self, max_alerts_per_minute: int = 10, max_alerts_per_hour: int = 100):
        self.max_per_minute = max_alerts_per_minute
        self.max_per_hour = max_alerts_per_hour
        self.minute_alerts = deque()  # Timestamps of alerts in last minute
        self.hour_alerts = deque()    # Timestamps of alerts in last hour
    
    def can_send_alert(self) -> bool:
        """Check if an alert can be sent based on rate limits"""
        now = datetime.now()
        
        # Remove old alerts outside the time windows
        while self.minute_alerts and (now - self.minute_alerts[0]).total_seconds() > 60:
            self.minute_alerts.popleft()
        
        while self.hour_alerts and (now - self.hour_alerts[0]).total_seconds() > 3600:
            self.hour_alerts.popleft()
        
        # Check limits
        if len(self.minute_alerts) >= self.max_per_minute:
            return False
        if len(self.hour_alerts) >= self.max_per_hour:
            return False
        
        return True
    
    def record_alert(self):
        """Record that an alert was sent"""
        now = datetime.now()
        self.minute_alerts.append(now)
        self.hour_alerts.append(now)


class AlertGrouper:
    """Groups similar alerts together to batch send"""
    def __init__(self, batch_window_seconds: int = 30, max_batch_size: int = 10):
        self.batch_window = batch_window_seconds
        self.max_batch_size = max_batch_size
        self.pending_alerts = defaultdict(list)  # alert_type -> list of alerts
        self.last_batch_time = defaultdict(lambda: datetime.now())
    
    def add_alert(self, alert_type: str, alert_data: Dict) -> bool:
        """
        Add an alert to the batch
        
        Returns:
            True if batch should be sent, False if waiting for more
        """
        self.pending_alerts[alert_type].append({
            'data': alert_data,
            'timestamp': datetime.now()
        })
        
        now = datetime.now()
        time_since_last_batch = (now - self.last_batch_time[alert_type]).total_seconds()
        
        # Send batch if:
        # 1. Batch window expired
        # 2. Max batch size reached
        if (time_since_last_batch >= self.batch_window or 
            len(self.pending_alerts[alert_type]) >= self.max_batch_size):
            return True
        
        return False
    
    def get_batch(self, alert_type: str) -> List[Dict]:
        """Get and clear the batch for an alert type"""
        batch = self.pending_alerts[alert_type].copy()
        self.pending_alerts[alert_type].clear()
        self.last_batch_time[alert_type] = datetime.now()
        return batch
    
    def clear_old_alerts(self):
        """Clear alerts older than batch window"""
        now = datetime.now()
        for alert_type in list(self.pending_alerts.keys()):
            self.pending_alerts[alert_type] = [
                alert for alert in self.pending_alerts[alert_type]
                if (now - alert['timestamp']).total_seconds() < self.batch_window * 2
            ]


class QuietHours:
    """Manages quiet hours when non-critical alerts are disabled"""
    def __init__(self, enabled: bool = False, start_hour: int = 22, start_minute: int = 0,
                 end_hour: int = 8, end_minute: int = 0):
        self.enabled = enabled
        self.start_time = time(start_hour, start_minute)
        self.end_time = time(end_hour, end_minute)
    
    def is_quiet_time(self) -> bool:
        """Check if current time is within quiet hours"""
        if not self.enabled:
            return False
        
        now = datetime.now().time()
        
        # Handle quiet hours that span midnight
        if self.start_time > self.end_time:
            # Quiet hours span midnight (e.g., 22:00 to 08:00)
            return now >= self.start_time or now <= self.end_time
        else:
            # Quiet hours within same day (e.g., 14:00 to 16:00)
            return self.start_time <= now <= self.end_time
    
    def should_suppress_alert(self, alert_priority: str = 'normal') -> bool:
        """
        Check if an alert should be suppressed during quiet hours
        
        Args:
            alert_priority: 'critical', 'important', or 'normal'
        
        Returns:
            True if alert should be suppressed, False otherwise
        """
        if not self.is_quiet_time():
            return False
        
        # Only suppress non-critical alerts during quiet hours
        return alert_priority != 'critical'
