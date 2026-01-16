"""
Email Notifier - Send notifications via email
"""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from typing import Optional, List
from .notification_manager import AlertPriority

logger = logging.getLogger(__name__)


class EmailNotifier:
    """Send notifications via email"""
    
    def __init__(
        self,
        smtp_server: str,
        smtp_port: int,
        sender_email: str,
        sender_password: str,
        recipient_emails: List[str],
        use_tls: bool = True
    ):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.recipient_emails = recipient_emails
        self.use_tls = use_tls
        self.enabled = True
    
    async def send_message(
        self,
        message: str,
        priority: AlertPriority = AlertPriority.NORMAL
    ) -> bool:
        """Send a text email"""
        if not self.enabled:
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.sender_email
            msg['To'] = ', '.join(self.recipient_emails)
            
            # Subject based on priority
            priority_subjects = {
                AlertPriority.CRITICAL: '[CRITICAL] MT5 Trade Alert',
                AlertPriority.IMPORTANT: '[IMPORTANT] MT5 Trade Alert',
                AlertPriority.NORMAL: 'MT5 Trade Alert'
            }
            msg['Subject'] = priority_subjects.get(priority, 'MT5 Trade Alert')
            
            # Create HTML version
            html_message = f"""
            <html>
              <body>
                <h2>MT5 Trade Alert</h2>
                <pre>{message}</pre>
              </body>
            </html>
            """
            
            # Attach both plain text and HTML
            text_part = MIMEText(message, 'plain')
            html_part = MIMEText(html_message, 'html')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Send email (run in executor to avoid blocking)
            import asyncio
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._send_email_sync, msg)
            
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def _send_email_sync(self, msg):
        """Synchronous email sending (runs in executor)"""
        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            if self.use_tls:
                server.starttls()
            server.login(self.sender_email, self.sender_password)
            server.send_message(msg, to_addrs=self.recipient_emails)
        finally:
            try:
                server.quit()
            except:
                pass
    
    async def send_message_with_image(
        self,
        message: str,
        priority: AlertPriority = AlertPriority.NORMAL,
        title: Optional[str] = None,
        image_data: Optional[bytes] = None,
        image_filename: Optional[str] = None
    ) -> bool:
        """Send an email with image attachment"""
        if not self.enabled:
            return False
        
        try:
            msg = MIMEMultipart('related')
            msg['From'] = self.sender_email
            msg['To'] = ', '.join(self.recipient_emails)
            
            priority_subjects = {
                AlertPriority.CRITICAL: '[CRITICAL] MT5 Trade Alert',
                AlertPriority.IMPORTANT: '[IMPORTANT] MT5 Trade Alert',
                AlertPriority.NORMAL: 'MT5 Trade Alert'
            }
            msg['Subject'] = priority_subjects.get(priority, 'MT5 Trade Alert')
            
            # Create HTML with embedded image
            html_message = f"""
            <html>
              <body>
                <h2>{title or 'MT5 Trade Alert'}</h2>
                <pre>{message}</pre>
                <img src="cid:chart_image" alt="Chart">
              </body>
            </html>
            """
            
            # Attach HTML
            html_part = MIMEText(html_message, 'html')
            msg.attach(html_part)
            
            # Attach image
            if image_data:
                image = MIMEImage(image_data)
                image.add_header('Content-ID', '<chart_image>')
                image.add_header('Content-Disposition', 'inline', filename=image_filename or 'chart.png')
                msg.attach(image)
            
            # Send email (run in executor to avoid blocking)
            import asyncio
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._send_email_sync, msg)
            
            return True
        except Exception as e:
            logger.error(f"Failed to send email with image: {e}")
            return False
