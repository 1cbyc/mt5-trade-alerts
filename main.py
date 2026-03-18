"""
MT5 Trade Alerts - Main Entry Point
"""
import argparse
import asyncio
import logging
import signal
import sys
from src.services.alert_service import MT5AlertService
from src.utils.config import Config

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
    parser = argparse.ArgumentParser(description='MT5 Trade Alerts Bot')
    parser.add_argument('--config', default='config.env', help='Path to config file (default: config.env)')
    args = parser.parse_args()

    logger.info(f"Loading config from: {args.config}")
    config = Config(config_path=args.config)

    service = MT5AlertService(config=config)

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
