import pytest
from src.agents.risk_agent import RiskManager

def test_risk_manager_valid_trade():
    rm = RiskManager(max_risk_per_trade_pct=0.02, min_rr_ratio=1.5)
    proposal = rm.evaluate_and_size(
        symbol="AAPL",
        action="BUY",
        account_balance=10000.0,
        entry_price=100.0,
        stop_loss=98.0,
        take_profit=105.0
    )
    assert proposal.qty == 100.0
    assert proposal.dollar_risk == 200.0
    assert proposal.expected_return == 500.0
    assert proposal.rr_ratio == 2.5

def test_risk_manager_invalid_rr():
    rm = RiskManager(max_risk_per_trade_pct=0.02, min_rr_ratio=2.0)
    with pytest.raises(ValueError, match="below the minimum threshold"):
        rm.evaluate_and_size(
            symbol="AAPL",
            action="BUY",
            account_balance=10000.0,
            entry_price=100.0,
            stop_loss=98.0,
            take_profit=102.0  # R:R is 1.0 < 2.0
        )

def test_risk_manager_invalid_stop_loss():
    rm = RiskManager()
    with pytest.raises(ValueError, match="Invalid price bounds"):
        rm.evaluate_and_size(
            symbol="AAPL",
            action="BUY",
            account_balance=10000.0,
            entry_price=100.0,
            stop_loss=102.0,  # Stop loss higher than entry on BUY
            take_profit=105.0
        )
