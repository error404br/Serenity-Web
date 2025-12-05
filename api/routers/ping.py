from fastapi import APIRouter
import httpx
import os
from datetime import datetime

router = APIRouter()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

@router.post("/ping")
async def ping():
    if TELEGRAM_TOKEN and CHAT_ID:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        text = f"📈 Nouvelle visite sur Serenity Web — {now}"
        try:
            async with httpx.AsyncClient() as client:
                await client.get(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                    params={"chat_id": CHAT_ID, "text": text}
                )
        except:
            pass

    return {"status": "ok"}
