import logging
from typing import List
from sqlalchemy.orm import Session
from src.storage.models import SessionLocal, AIModelRegistry
from config.settings import settings

logger = logging.getLogger(__name__)

class AIEvolutionManager:
    """Manages AI provider fallbacks, tracks API health, and orchestrates model migration with human approval."""
    
    FALLBACK_CANDIDATE_MODELS = [
        {"provider": "openai", "model_name": "gpt-4o-mini"},
        {"provider": "openai", "model_name": "gpt-4o"},
        {"provider": "openai", "model_name": "gpt-3.5-turbo"},
        {"provider": "ollama", "model_name": "llama3:latest"}
    ]

    def __init__(self):
        self.active_model = settings.openai_model
        self.active_provider = "openai"

    def record_success(self, model_name: str, latency_ms: float):
        db: Session = SessionLocal()
        record = db.query(AIModelRegistry).filter_by(model_name=model_name).first()
        if record:
            record.success_count += 1
            record.avg_latency_ms = (record.avg_latency_ms * 0.8) + (latency_ms * 0.2)
            db.commit()
        db.close()

    def record_failure(self, model_name: str, error_msg: str) -> dict:
        db: Session = SessionLocal()
        record = db.query(AIModelRegistry).filter_by(model_name=model_name).first()
        
        fallback_required = False
        suggested_model = None

        if record:
            record.failure_count += 1
            if record.failure_count >= 3:  # Threshold for triggering fallback
                record.is_active = False
                fallback_required = True
                logger.warning(f"⚠️ Model '{model_name}' marked inactive due to consecutive failures: {error_msg}")
            db.commit()

        if fallback_required:
            # Select next best candidate
            for candidate in self.FALLBACK_CANDIDATE_MODELS:
                if candidate["model_name"] != model_name:
                    suggested_model = candidate
                    break

        db.close()
        return {
            "fallback_required": fallback_required,
            "failed_model": model_name,
            "suggested_model": suggested_model
        }

    def get_active_model() -> str:
        db: Session = SessionLocal()
        active = db.query(AIModelRegistry).filter_by(is_active=True).first()
        model_name = active.model_name if active else settings.openai_model
        db.close()
        return model_name
