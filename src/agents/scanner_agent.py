import asyncio
import logging
import pandas_ta as ta
from src.agents.risk_agent import RiskManager, TradeProposal
from src.agents.synthesizer_agent import LLMSynthesizer, TradeBrief
from src.execution.alpaca_client import AlpacaBroker
from src.notifications.telegram_bot import TelegramInterface
from src.storage.models import SessionLocal, TradeLog

logger = logging.getLogger(__name__)

class MarketScanner:
    def __init__(
        self,
        broker: AlpacaBroker,
        risk_mgr: RiskManager,
        synthesizer: LLMSynthesizer,
        tg: TelegramInterface,
        pending_store: dict,
        watchlist: list[str] = None
    ):
        self.broker = broker
        self.risk_mgr = risk_mgr
        self.synthesizer = synthesizer
        self.tg = tg
        self.pending_store = pending_store
        self.watchlist = watchlist or ["AAPL", "NVDA", "TSLA", "MSFT", "AMZN"]

    async def run(self, interval_seconds: int = 60):
        logger.info("🔍 Market scanner started. Scanning symbols: %s", self.watchlist)
        while True:
            try:
                balance = self.broker.get_account_balance()
                for symbol in self.watchlist:
                    df = self.broker.fetch_recent_bars(symbol)
                    if df.empty or len(df) < 30:
                        continue

                    # Calculate quantitative indicators
                    df.ta.rsi(length=14, append=True)
                    df.ta.ema(length=20, append=True)

                    latest = df.iloc[-1]
                    prev = df.iloc[-2]

                    # Strategy Setup: RSI crossing up from oversold (<35) + Price above 20 EMA
                    rsi_col = [c for c in df.columns if c.startswith("RSI")][0]
                    ema_col = [c for c in df.columns if c.startswith("EMA")][0]

                    rsi_oversold = prev[rsi_col] < 35 and latest[rsi_col] >= 35
                    price_above_ema = latest["close"] > latest[ema_col]

                    if rsi_oversold and price_above_ema:
                        entry = float(latest["close"])
                        stop_loss = entry * 0.99
                        take_profit = entry * 1.025

                        try:
                            proposal = self.risk_mgr.evaluate_and_size(
                                symbol=symbol,
                                action="BUY",
                                account_balance=balance,
                                entry_price=entry,
                                stop_loss=stop_loss,
                                take_profit=take_profit
                            )

                            indicator_ctx = (
                                f"RSI 14 moved from {prev[rsi_col]:.1f} to {latest[rsi_col]:.1f}. "
                                f"Close price (${entry:.2f}) above 20 EMA (${latest[ema_col]:.2f})."
                            )
                            brief = self.synthesizer.generate_brief(proposal, indicator_ctx)

                            import uuid
                            proposal_id = str(uuid.uuid4())[:8]

                            self.pending_store[proposal_id] = {
                                "proposal": proposal,
                                "brief": brief
                            }

                            # Log to DB
                            db = SessionLocal()
                            log_entry = TradeLog(
                                id=proposal_id,
                                symbol=proposal.symbol,
                                action=proposal.action,
                                entry_price=proposal.entry_price,
                                stop_loss=proposal.stop_loss,
                                take_profit=proposal.take_profit,
                                qty=proposal.qty,
                                dollar_risk=proposal.dollar_risk,
                                expected_return=proposal.expected_return,
                                rr_ratio=proposal.rr_ratio,
                                brief_line_1=brief.line_1,
                                brief_line_2=brief.line_2,
                                brief_line_3=brief.line_3,
                                status="PENDING"
                            )
                            db.add(log_entry)
                            db.commit()
                            db.close()

                            await self.tg.send_proposal(proposal_id, proposal, brief)
                            logger.info(f"Generated proposal {proposal_id} for {symbol}")

                        except ValueError as ve:
                            logger.debug(f"Risk rejection for {symbol}: {ve}")

            except Exception as e:
                logger.error(f"Error in scan loop: {e}", exc_info=True)

            await asyncio.sleep(interval_seconds)
