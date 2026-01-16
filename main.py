"""
MT5 Trade Alerts - Main Entry Point
"""
import asyncio
import logging
import signal
import sys
from src.services.alert_service import MT5AlertService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mt5_alerts.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def signal_handler(service):
    """Handle shutdown signals"""
    def handler(signum, frame):
        logger.info(f"Received signal {signum}")
        service.running = False
    return handler


async def main():
    service = MT5AlertService()
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler(service))
    signal.signal(signal.SIGTERM, signal_handler(service))
    
    await service.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Service stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
