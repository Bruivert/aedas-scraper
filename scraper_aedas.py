import requests
import os
import sys   # ← nuevo, para poder salir con error

def enviar_mensaje_telegram(texto):
    """Envía 'texto' a tu chat/canal de Telegram y devuelve la respuesta JSON."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat  = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat:
        # El workflow fallará aquí si se te olvida configurar los secrets
        raise SystemExit("❌ Token o chat ID de Telegram no configurados")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat,
        "text": texto,
        "parse_mode": "Markdown"
    }

    try:
        # ►► usa POST, no GET
        r = requests.post(url, data=payload, timeout=15)
        r.raise_for_status()
        data = r.json()
        if not data.get("ok"):
            raise RuntimeError(data)   # Telegram contestó con error lógico
        print("✅ Mensaje enviado a Telegram")
        return data
    except Exception as exc:
        raise SystemExit(f"❌ Error al enviar a Telegram: {exc}")
