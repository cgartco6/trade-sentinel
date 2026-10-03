from datetime import datetime
from sqlalchemy import create_engine, Column, String, Float, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from config.settings import settings

Base = declarative_base()

class TradeLog(Base):
    __tablename__ = "trade_logs"

    id = Column(String, primary_key=True)
    symbol = Column(String, nullable=False)
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
    status = Column(String, default="PENDING")
    order_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    import os
    os.makedirs("./data", exist_ok=True)
    Base.metadata.create_all(bind=engine)
