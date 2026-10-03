import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from src.storage.models import SessionLocal, TradeLog

app = FastAPI(title="Trade Sentinel OS")

templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    db = SessionLocal()
    trades = db.query(TradeLog).order_by(TradeLog.created_at.desc()).all()
    db.close()
    return templates.TemplateResponse("index.html", {"request": request, "trades": trades})

@app.get("/api/trades")
async def get_trades():
    db = SessionLocal()
    trades = db.query(TradeLog).order_by(TradeLog.created_at.desc()).all()
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
            "created_at": t.created_at.strftime("%Y-%m-%d %H:%M:%S") if t.created_at else ""
        }
        for t in trades
    ]
