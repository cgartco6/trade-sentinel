import os
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Float, DateTime, Text, Integer, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from config.settings import settings

Base = declarative_base()

class TradeLog(Base):
    __tablename__ = "trade_logs"

    id = Column(String, primary_key=True)
    symbol = Column(String, nullable=False, index=True)
    action = Column(String, nullable=False)
    entry_price = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    take_profit = Column(Float, nullable=False)
    qty = Column(Float, nullable=False)
    dollar_risk = Column(Float, nullable=False)
    expected_return = Column(Float, nullable=False)
    rr_ratio = Column(Float, nullable=False)
    brief_line_1 = Column(Text, nullable=False)
    brief_line_2 = Column(Text, nullable=False)
    brief_line_3 = Column(Text, nullable=False)
    status = Column(String, default="PENDING", index=True)  # PENDING, EXECUTED, REJECTED, EXPIRED, FAILED
    order_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

class AIModelRegistry(Base):
    __tablename__ = "ai_model_registry"

    id = Column(Integer, primary_key=True, autoincrement=True)
    provider = Column(String, nullable=False)  # openai, anthropic, ollama
    model_name = Column(String, nullable=False, unique=True)
    is_active = Column(Boolean, default=True)
    failure_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    avg_latency_ms = Column(Float, default=0.0)
    last_tested_at = Column(DateTime, default=datetime.utcnow)

engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    os.makedirs("./data", exist_ok=True)
    Base.metadata.create_all(bind=engine)
    
    # Bootstrap active models
    db = SessionLocal()
    if not db.query(AIModelRegistry).filter_by(model_name=settings.openai_model).first():
        db.add(AIModelRegistry(provider="openai", model_name=settings.openai_model, is_active=True))
        db.commit()
    db.close()
