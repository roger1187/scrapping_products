import os

import requests


def telegram(msg: str) -> None:
    """Envía un mensaje al chat configurado; si no hay credenciales no hace nada."""
    tok, chat = os.getenv("TELEGRAM_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not (tok and chat):
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{tok}/sendMessage",
            json={"chat_id": chat, "text": msg, "disable_web_page_preview": True},
            timeout=10,
        )
    except Exception as e:  # nunca abortar la corrida por un aviso
        print(f"[telegram] no se pudo enviar: {e}")
