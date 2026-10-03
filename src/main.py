import asyncio
import logging
from config.settings import settings
from src.storage.models import init_db
from src.execution.alpaca_client import AlpacaBroker
from src.agents.risk_agent import RiskManager
from src.agents.synthesizer_agent import LLMSynthesizer
from src.notifications.telegram_bot import TelegramInterface
from src.agents.scanner_agent import MarketScanner

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("TradeSentinel")

PENDING_PROPOSALS = {}

async def main():
    logger.info("Initializing Trade Sentinel Infrastructure...")
    init_db()

    broker = AlpacaBroker()
    risk_mgr = RiskManager(
        max_risk_per_trade_pct=settings.max_risk_per_trade_pct,
        min_rr_ratio=settings.min_rr_ratio
    )
    synthesizer = LLMSynthesizer()

    tg = TelegramInterface(
        token=settings.telegram_bot_token,
        allowed_chat_id=settings.telegram_chat_id,
        broker=broker,
        pending_store=PENDING_PROPOSALS
    )

    await tg.app.initialize()
    await tg.app.start()
    await tg.app.updater.start_polling()

    logger.info("Telegram Bot Polling Online.")

    scanner = MarketScanner(
        broker=broker,
        risk_mgr=risk_mgr,
        synthesizer=synthesizer,
        tg=tg,
        pending_store=PENDING_PROPOSALS
    )

    await scanner.run(interval_seconds=settings.scan_interval_seconds)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Trade Sentinel shut down successfully.")
