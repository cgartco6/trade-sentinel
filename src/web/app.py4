import os
import logging
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config.settings import settings
from src.storage.models import Base, TradeLog, AIModelRegistry
from src.agents.risk_agent import RiskManager, TradeProposal
from src.agents.synthesizer_agent import LLMSynthesizer
from src.agents.evolution_agent import AIEvolutionManager
from src.execution.alpaca_client import AlpacaBroker

logger = logging.getLogger(__name__)

app = FastAPI(title="Trade Sentinel OS — Vercel Engine")

# Setup database connection (Support Vercel Postgres / Neon / Supabase)
db_url = os.getenv("POSTGRES_URL", settings.database_url)
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(db_url, pool_pre_ping=True, pool_size=5, max_overflow=10)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Auto-migrate schema on cold start
Base.metadata.create_all(bind=engine)

templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)

class ApprovalPayload(BaseModel):
    proposal_id: str
    action: str

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

# Vercel Cron Scheduled Scanner Trigger
@app.get("/api/cron/scan")
async def cron_scan(authorization: str = Header(None)):
    # Verify Cron Secret if set in Vercel
    cron_secret = os.getenv("CRON_SECRET")
    if cron_secret and authorization != f"Bearer {cron_secret}":
        raise HTTPException(status_code=401, detail="Unauthorized Cron Execution")

    broker = AlpacaBroker()
    risk_mgr = RiskManager(
        max_risk_per_trade_pct=settings.max_risk_per_trade_pct,
        min_rr_ratio=settings.min_rr_ratio
    )
    evolution_mgr = AIEvolutionManager()
    synthesizer = LLMSynthesizer(evolution_mgr)

    watchlist = ["AAPL", "NVDA", "TSLA", "MSFT", "AMZN"]
    signals_generated = 0

    try:
        balance = broker.get_account_balance()
        for symbol in watchlist:
            df = broker.fetch_recent_bars(symbol)
            if df.empty or len(df) < 30:
                continue

            df.ta.rsi(length=14, append=True)
            df.ta.ema(length=20, append=True)

            latest = df.iloc[-1]
            prev = df.iloc[-2]

            rsi_col = [c for c in df.columns if c.startswith("RSI")][0]
            ema_col = [c for c in df.columns if c.startswith("EMA")][0]

            rsi_oversold = prev[rsi_col] < 35 and latest[rsi_col] >= 35
            price_above_ema = latest["close"] > latest[ema_col]

            if rsi_oversold and price_above_ema:
                entry = float(latest["close"])
                stop_loss = entry * 0.99
                take_profit = entry * 1.025

                try:
                    proposal = risk_mgr.evaluate_and_size(
                        symbol=symbol,
                        action="BUY",
                        account_balance=balance,
                        entry_price=entry,
                        stop_loss=stop_loss,
                        take_profit=take_profit
                    )

                    indicator_ctx = f"RSI 14 moved from {prev[rsi_col]:.1f} to {latest[rsi_col]:.1f}. Price (${entry:.2f}) above EMA (${latest[ema_col]:.2f})."
                    brief = synthesizer.generate_brief(proposal, indicator_ctx)

                    import uuid
                    proposal_id = str(uuid.uuid4())[:8]

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

                    signals_generated += 1
                except ValueError:
                    pass

    except Exception as e:
        logger.error(f"Cron scanning error: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

    return {"status": "success", "signals_generated": signals_generated}

# Web Approval Endpoint
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
