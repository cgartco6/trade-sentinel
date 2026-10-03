import time
import hmac
import hashlib
import requests
import logging
from config.settings import settings
from src.agents.risk_agent import TradeProposal

logger = logging.getLogger(__name__)

class VALRBroker:
    """VALR API v1 Client with HMAC SHA512 Authentication."""

    def __init__(self):
        self.api_key = getattr(settings, "VALR_API_KEY", None)
        self.api_secret = getattr(settings, "VALR_API_SECRET", None)
        self.base_url = "https://api.valr.com"

    def _sign_request(self, timestamp: str, method: str, path: str, body: str = "") -> str:
        payload = f"{timestamp}{method.upper()}{path}{body}"
        return hmac.new(
            self.api_secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha512
        ).hexdigest()

    def _get_headers(self, method: str, path: str, body: str = "") -> dict:
        timestamp = str(int(time.time() * 1000))
        signature = self._sign_request(timestamp, method, path, body)
        return {
            "X-VALR-API-KEY": self.api_key,
            "X-VALR-SIGNATURE": signature,
            "X-VALR-TIMESTAMP": timestamp,
            "Content-Type": "application/json"
        }

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_secret)

    def execute_limit_order(self, proposal: TradeProposal) -> str:
        """Submits a limit order on VALR (e.g. BTCZAR, ETHZAR)."""
        if not self.is_configured():
            raise ValueError("VALR credentials missing. Switch to manual mode.")

        # Format VALR pair symbol (e.g. BTC/ZAR -> BTCZAR)
        pair_symbol = proposal.symbol.replace("/", "").replace("-", "").upper()
        if not pair_symbol.endswith("ZAR") and not pair_symbol.endswith("USDT"):
            pair_symbol += "ZAR"

        path = "/v1/orders/limit"
        body_data = {
            "side": proposal.action.upper(),
            "quantity": f"{proposal.qty:.6f}",
            "price": f"{proposal.entry_price:.2f}",
            "pair": pair_symbol,
            "postOnly": False,
            "customerOrderId": f"TS-{int(time.time())}"
        }

        import json
        body_str = json.dumps(body_data)
        headers = self._get_headers("POST", path, body_str)

        response = requests.post(f"{self.base_url}{path}", headers=headers, data=body_str, timeout=10)
        res_json = response.json()

        if response.status_code in [200, 201, 202]:
            logger.info(f"✅ VALR Order Executed: {res_json.get('id')}")
            return res_json.get("id", "VALR_ORDER_SUCCESS")
        else:
            raise RuntimeError(f"VALR Order Execution Error: {res_json.get('message', response.text)}")
