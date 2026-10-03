import time
import logging
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from src.agents.risk_agent import TradeProposal
from src.agents.evolution_agent import AIEvolutionManager
from config.settings import settings

logger = logging.getLogger(__name__)

class TradeBrief(BaseModel):
    line_1: str = Field(description="Core rationale: technical indicator setup summary.")
    line_2: str = Field(description="Risk vs Return dynamics and exact monetary risk.")
    line_3: str = Field(description="Market context, volatility note, or cautionary warning.")

class LLMSynthesizer:
    def __init__(self, evolution_mgr: AIEvolutionManager):
        self.evolution_mgr = evolution_mgr
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an institutional quantitative risk manager. Synthesize raw strategy metrics into exactly 3 punchy, plain-English lines for instant user decision approval."),
            ("user", "Symbol: {symbol}\nAction: {action}\nEntry: ${entry}\nSL: ${sl}\nTP: ${tp}\nMax Dollar Risk: ${risk}\nExpected Return: ${reward}\nR:R Ratio: {rr}\nTechnical Context: {indicators}")
        ])

    def generate_brief(self, proposal: TradeProposal, indicator_context: str) -> TradeBrief:
        current_model = self.evolution_mgr.get_active_model()
        start_time = time.time()

        try:
            llm = ChatOpenAI(
                api_key=settings.openai_api_key,
                model=current_model,
                temperature=0.1,
                max_retries=2
            ).with_structured_output(TradeBrief)

            chain = self.prompt | llm
            brief = chain.invoke({
                "symbol": proposal.symbol,
                "action": proposal.action,
                "entry": proposal.entry_price,
                "sl": proposal.stop_loss,
                "tp": proposal.take_profit,
                "risk": proposal.dollar_risk,
                "reward": proposal.expected_return,
                "rr": proposal.rr_ratio,
                "indicators": indicator_context
            })

            latency = (time.time() - start_time) * 1000
            self.evolution_mgr.record_success(current_model, latency)
            return brief

        except Exception as e:
            logger.error(f"LLM Synthesis failed with model {current_model}: {e}")
            failure_report = self.evolution_mgr.record_failure(current_model, str(e))

            # Rule-based fallback if LLM execution fails completely
            return TradeBrief(
                line_1=f"Technical Setup: {proposal.symbol} {proposal.action} triggered by indicator signals.",
                line_2=f"Risk/Reward: Risking ${proposal.dollar_risk:.2f} to gain ${proposal.expected_return:.2f} (R:R {proposal.rr_ratio}).",
                line_3="⚠️ Automated Fallback Brief: LLM synthesis unavailable or rate-limited. Human verification required."
            )
