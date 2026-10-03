# Trade Sentinel 🛡️📈

An institutional-grade, human-in-the-loop algorithmic trading sentinel. Combines deterministic technical indicators, strict position sizing guardrails, and LLM-generated trade summaries pushed directly to Telegram for single-tap execution.

## Features
- **Deterministic Technical Scanning**: EMA + RSI breakout detection via `pandas-ta`.
- **Hard Risk Guardrails**: Mathematical position sizing enforcing strict balance percentage caps and minimum Risk-to-Reward (R:R) ratios.
- **LLM Synthesis**: Translates technical context into 3 plain-English decision lines.
- **Interactive Execution**: Telegram notification with inline `[APPROVE]` / `[REJECT]` buttons executing real bracket orders (Market Entry + Stop Loss + Take Profit) via Alpaca.

## Quickstart

1. Copy `.env.example` to `.env` and populate your credentials:
   ```bash
   cp .env.example .env
