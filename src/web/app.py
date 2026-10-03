from src.execution.valr_client import VALRBroker

@app.post("/api/approve")
async def approve_trade(payload: ApprovalPayload):
    db = SessionLocal()
    trade = db.query(TradeLog).filter_by(id=payload.proposal_id).first()

    if not trade:
        db.close()
        raise HTTPException(status_code=404, detail="Trade proposal not found")

    if trade.status != "PENDING":
        db.close()
        return {"status": "ignored", "message": f"Trade already in status {trade.status}"}

    if payload.action == "APPROVE":
        try:
            proposal = TradeProposal(
                symbol=trade.symbol,
                action=trade.action,
                entry_price=trade.entry_price,
                stop_loss=trade.stop_loss,
                take_profit=trade.take_profit,
                qty=trade.qty,
                dollar_risk=trade.dollar_risk,
                expected_return=trade.expected_return,
                rr_ratio=trade.rr_ratio
            )

            # Route 1: Crypto / ZAR Pairs -> VALR (or Manual fallback)
            valr = VALRBroker()
            if "BTC" in trade.symbol or "ETH" in trade.symbol or trade.symbol.endswith("ZAR"):
                if valr.is_configured():
                    order_id = valr.execute_limit_order(proposal)
                    trade.status = "EXECUTED (VALR)"
                    trade.order_id = order_id
                else:
                    # Manual Execution Fallback Mode
                    trade.status = "APPROVED (MANUAL EXECUTION REQUIRED)"
                    trade.order_id = "MANUAL_ZAR"
            
            # Route 2: US Stocks -> Alpaca
            else:
                broker = AlpacaBroker()
                order_id = broker.execute_bracket_order(proposal)
                trade.status = "EXECUTED (ALPACA)"
                trade.order_id = order_id

            db.commit()
            db.close()
            return {"status": "success", "trade_status": trade.status}

        except Exception as e:
            trade.status = f"FAILED: {str(e)}"
            db.commit()
            db.close()
            raise HTTPException(status_code=500, detail=str(e))
    else:
        trade.status = "REJECTED"
        db.commit()
        db.close()
        return {"status": "rejected"}
