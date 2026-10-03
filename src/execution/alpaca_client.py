import pandas as pd
from datetime import datetime, timedelta
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, TakeProfitRequest, StopLossRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from src.agents.risk_agent import TradeProposal
from config.settings import settings

class AlpacaBroker:
    def __init__(self):
        self.trading_client = TradingClient(
            settings.alpaca_api_key,
            settings.alpaca_secret_key,
            paper=settings.alpaca_paper
        )
        self.data_client = StockHistoricalDataClient(
            settings.alpaca_api_key,
            settings.alpaca_secret_key
        )

    def get_account_balance(self) -> float:
        account = self.trading_client.get_account()
        return float(account.buying_power)

    def fetch_recent_bars(self, symbol: str, limit: int = 100) -> pd.DataFrame:
        end = datetime.now()
        start = end - timedelta(days=7)
        request_params = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Minute,
            start=start,
            end=end
        )
        bars = self.data_client.get_stock_bars(request_params)
        df = bars.df
        if isinstance(df.index, pd.MultiIndex):
            df = df.loc[symbol]
        return df.tail(limit)

    def execute_bracket_order(self, proposal: TradeProposal) -> str:
        side = OrderSide.BUY if proposal.action == "BUY" else OrderSide.SELL

        order_request = MarketOrderRequest(
            symbol=proposal.symbol,
            qty=proposal.qty,
            side=side,
            time_in_force=TimeInForce.GTC,
            take_profit=TakeProfitRequest(limit_price=proposal.take_profit),
            stop_loss=StopLossRequest(stop_price=proposal.stop_loss)
        )

        order = self.trading_client.submit_order(order_data=order_request)
        return str(order.id)
