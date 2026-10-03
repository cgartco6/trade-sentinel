import os
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from src.storage.models import SessionLocal, TradeLog, AIModelRegistry
from src.execution.alpaca_client import AlpacaBroker
from src.agents.risk_agent import TradeProposal

logger = logging.getLogger(__name__)
app = FastAPI(title="Trade Sentinel OS -- Command Center")

templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)

class ApprovalPayload(BaseModel):
    proposal_id: str
    action: str  # APPROVE or REJECT

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    db = SessionLocal()
    trades = db.query(TradeLog).order_by(TradeLog.created_at.desc()).limit(50).all()
    models = db.query(AIModelRegistry).all()
    db.close()
    return templates.TemplateResponse("index.html", {"request": request, "trades": trades, "models": models})

@app.get("/api/trades")
async def get_trades():
    db = SessionLocal()
    trades = db.query(TradeLog).order_by(TradeLog.created_at.desc()).limit(50).all()
    db.close()
    return [
        {
            "id": t.id,
            "symbol": t.symbol,
            "action": t.action,
            "entry_price": t.entry_price,
            "stop_loss": t.stop_loss,
            "take_profit": t.take_profit,
            "qty": t.qty,
            "dollar_risk": t.dollar_risk,
            "expected_return": t.expected_return,
            "status": t.status,
            "brief": [t.brief_line_1, t.brief_line_2, t.brief_line_3],
            "created_at": t.created_at.strftime("%Y-%m-%d %H:%M:%S") if t.created_at else ""
        }
        for t in trades
    ]

@app.post("/api/approve")
async def approve_trade(payload: ApprovalPayload):
    db = SessionLocal()
    trade = db.query(TradeLog).filter_by(id=payload.proposal_id).first()

    if not trade:
        db.close()
        raise HTTPException(status_code=404, detail="Trade proposal not found")

    if trade.status != "PENDING":
        db.close()
        return JSONResponse({"status": "ignored", "message": f"Trade already in status {trade.status}"})

    if payload.action == "APPROVE":
        try:
            broker = AlpacaBroker()
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
            order_id = broker.execute_bracket_order(proposal)
            trade.status = "EXECUTED"
            trade.order_id = order_id
            db.commit()
            db.close()
            return {"status": "success", "order_id": order_id}
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
