import os
import requests
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_TOPIK_ID = os.getenv("TELEGRAM_TOPIK_ID")


def send_telegram_alert(message: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logging.warning("Telegram Bot Token atau Chat ID belum di-set di .env")
        return

    now = datetime.now()
    waktu = now.strftime("%H:%M:%S")
    tanggal = now.strftime("%d %B %Y")

    text = (
        "‼️ STT SERVER RADIO 1 ‼️\n\n"
        f"Detail : \n\n"
        f"{message}\n\n"
        f"⏰ : {waktu}\n"
        f"📅 : {tanggal}"
    )

    apiURL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text
    }

    # kalau pakai topic group (forum)
    if TELEGRAM_TOPIK_ID:
        payload["message_thread_id"] = int(TELEGRAM_TOPIK_ID)

    try:
        response = requests.post(apiURL, json=payload)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to send Telegram alert: {e} | response={getattr(e.response, 'text', None)}")