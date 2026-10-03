import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes
from src.agents.risk_agent import TradeProposal
from src.agents.synthesizer_agent import TradeBrief
from src.execution.alpaca_client import AlpacaBroker
from src.storage.models import SessionLocal, TradeLog

logger = logging.getLogger(__name__)

class TelegramInterface:
    def __init__(self, token: str, allowed_chat_id: str, broker: AlpacaBroker, pending_store: dict):
        self.token = token
        self.chat_id = str(allowed_chat_id)
        self.broker = broker
        self.pending_store = pending_store
        self.app = Application.builder().token(token).build()
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))

    async def send_proposal(self, proposal_id: str, proposal: TradeProposal, brief: TradeBrief):
        text = (
            f"🎯 **TRADE SIGNAL: {proposal.symbol} ({proposal.action})**\n\n"
            f"1️⃣ {brief.line_1}\n"
            f"2️⃣ {brief.line_2}\n"
            f"3️⃣ {brief.line_3}\n\n"
            f"📊 **Entry:** ${proposal.entry_price} | **Qty:** {proposal.qty}\n"
            f"🛑 **SL:** ${proposal.stop_loss} \vert{} 🎯 **TP:** ${proposal.take_profit}\n"
            f"💰 **Risk:** ${proposal.dollar_risk} \vert{} **Return:**${proposal.expected_return} (R:R {proposal.rr_ratio})"
        )
        keyboard = [
            [
                InlineKeyboardButton("✅ APPROVE", callback_data=f"app:{proposal_id}"),
                InlineKeyboardButton("❌ REJECT", callback_data=f"rej:{proposal_id}")
            ]
        ]
        await self.app.bot.send_message(
            chat_id=self.chat_id,
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        if str(update.effective_chat.id) != self.chat_id:
            await query.edit_message_text("🚫 Unauthorized action.")
            return

        action, proposal_id = query.data.split(":")
        if proposal_id not in self.pending_store:
            await query.edit_message_text("⚠️ Proposal expired or already processed.")
            return

        proposal_data = self.pending_store.pop(proposal_id)
        proposal: TradeProposal = proposal_data["proposal"]

        db = SessionLocal()
        db_log = db.query(TradeLog).filter(TradeLog.id == proposal_id).first()

        if action == "app":
            await query.edit_message_text(f"⚡ Executing bracket order for {proposal.symbol}...")
            try:
                order_id = self.broker.execute_bracket_order(proposal)
                if db_log:
                    db_log.status = "EXECUTED"
                    db_log.order_id = order_id
                    db.commit()

                await query.edit_message_text(
                    f"✅ **ORDER EXECUTED**\n\n"
                    f"**Symbol:** {proposal.symbol}\n"
                    f"**Action:** {proposal.action}\n"
                    f"**Qty:** {proposal.qty}\n"
                    f"**Order ID:** `{order_id}`\n\n"
                    f"Bracket Stop-Loss (${proposal.stop_loss}) and Take-Profit (${proposal.take_profit}) set."
                )
            except Exception as e:
                logger.error(f"Execution error: {e}")
                if db_log:
                    db_log.status = f"FAILED: {str(e)}"
                    db.commit()
                await query.edit_message_text(f"❌ **EXECUTION FAILED**: {str(e)}")
        else:
            if db_log:
                db_log.status = "REJECTED"
                db.commit()
            await query.edit_message_text(f"🚫 Trade proposal for {proposal.symbol} rejected.")
        db.close()
