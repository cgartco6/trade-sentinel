from dataclasses import dataclass

@dataclass
class TradeProposal:
    symbol: str
    action: str
    entry_price: float
    stop_loss: float
    take_profit: float
    qty: float
    dollar_risk: float
    expected_return: float
    rr_ratio: float

class RiskManager:
    def __init__(self, max_risk_per_trade_pct: float = 0.015, min_rr_ratio: float = 1.5):
        self.max_risk_pct = max_risk_per_trade_pct
        self.min_rr = min_rr_ratio

    def evaluate_and_size(
        self,
        symbol: str,
        action: str,
        account_balance: float,
        entry_price: float,
        stop_loss: float,
        take_profit: float
    ) -> TradeProposal:
        if action == "BUY" and (stop_loss >= entry_price or take_profit <= entry_price):
            raise ValueError(f"Invalid price bounds for LONG setup on {symbol}.")
        if action == "SELL" and (stop_loss <= entry_price or take_profit >= entry_price):
            raise ValueError(f"Invalid price bounds for SHORT setup on {symbol}.")

        risk_per_share = abs(entry_price - stop_loss)
        reward_per_share = abs(take_profit - entry_price)

        if risk_per_share == 0:
            raise ValueError("Stop loss cannot be equal to entry price.")

        rr_ratio = reward_per_share / risk_per_share

        if rr_ratio < self.min_rr:
            raise ValueError(f"Setup R:R ({rr_ratio:.2f}) is below the minimum threshold ({self.min_rr}).")

        max_dollar_risk = account_balance * self.max_risk_pct
        shares = max_dollar_risk / risk_per_share

        total_cost = shares * entry_price
        if total_cost > account_balance:
            shares = account_balance / entry_price

        shares = round(shares, 4)
        if shares <= 0:
            raise ValueError("Calculated quantity is zero. Insufficient account balance.")

        actual_dollar_risk = round(shares * risk_per_share, 2)
        expected_return = round(shares * reward_per_share, 2)

        return TradeProposal(
            symbol=symbol,
            action=action,
            entry_price=round(entry_price, 2),
            stop_loss=round(stop_loss, 2),
            take_profit=round(take_profit, 2),
            qty=shares,
            dollar_risk=actual_dollar_risk,
            expected_return=expected_return,
            rr_ratio=round(rr_ratio, 2)
        )
