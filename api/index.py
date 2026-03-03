"""FastAPI webhook entry point for Vercel deployment."""

import json
import logging

from fastapi import FastAPI, Request, Response
from telegram import Update

from main import build_app

logger = logging.getLogger(__name__)

app = FastAPI()

# Build the PTB application once at module load (cold start)
_ptb_app = build_app()
_initialized = False


async def _ensure_initialized():
    """Initialize PTB app once (idempotent)."""
    global _initialized
    if not _initialized:
        await _ptb_app.initialize()
        _initialized = True


@app.on_event("startup")
async def startup():
    await _ensure_initialized()


@app.post("/webhook")
async def webhook(request: Request):
    """Receive a Telegram update and process it."""
    await _ensure_initialized()
    try:
        data = await request.json()
        update = Update.de_json(data, _ptb_app.bot)
        await _ptb_app.process_update(update)
    except Exception as e:
        logger.error(f"Error processing update: {e}")
    return Response(status_code=200)


@app.get("/health")
async def health():
    return {"status": "ok"}
