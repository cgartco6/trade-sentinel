from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from src.agents.risk_agent import TradeProposal
from config.settings import settings

class TradeBrief(BaseModel):
    line_1: str = Field(description="Core rationale: technical indicator setup summary.")
    line_2: str = Field(description="Risk vs Return dynamics and exact monetary risk.")
    line_3: str = Field(description="Market context, volatility note, or cautionary warning.")

class LLMSynthesizer:
    def __init__(self):
        self.llm = ChatOpenAI(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            temperature=0.1
        ).with_structured_output(TradeBrief)

        self.prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are an institutional quantitative risk manager. "
                "Synthesize raw strategy metrics into exactly 3 punchy, plain-English lines for instant user decision approval."
            ),
            (
                "user",
                "Symbol: {symbol}\nAction: {action}\nEntry: ${entry}\nSL: ${sl}\nTP: ${tp}\n"
                "Max Dollar Risk: ${risk}\nExpected Return: ${reward}\nR:R Ratio: {rr}\n"
                "Technical Context: {indicators}"
            )
        ])

    def generate_brief(self, proposal: TradeProposal, indicator_context: str) -> TradeBrief:
        chain = self.prompt | self.llm
        return chain.invoke({
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
