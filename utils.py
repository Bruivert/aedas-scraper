# utils.py
# ────────────────────────────────────────────────────────────────
# Funciones y constantes compartidas por todos los scrapers
# ────────────────────────────────────────────────────────────────
import os
import re
import requests

# Cabecera genérica para engañar al servidor y que no bloquee los requests
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/123.0 Safari/537.36"
    )
}

# Filtros globales
LOCALIZACIONES_DESEADAS = [
    "mislata",
    "valencia",
    "quart de poblet",
    "paterna",
    "manises",
]
PRECIO_MAXIMO        = 270_000         # euros
HABITACIONES_MINIMAS = 2               # dormitorios mínimos


# ────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────
def limpiar_y_convertir_a_numero(texto: str | None) -> int | None:
    """
    Extrae el primer número entero de 'texto' (acepta separador de miles con
    puntos) y lo devuelve como int. Devuelve None si no hay números.
    """
    if not texto:
        return None
    nums = re.findall(r"[\d.]+", texto)
    return int(nums[0].replace(".", "")) if nums else None


def enviar_mensaje_telegram(texto: str) -> None:
    """
    Envía 'texto' al chat definido en las variables de entorno:
      • TELEGRAM_BOT_TOKEN
      • TELEGRAM_CHAT_ID
    Finaliza el programa con exit(1) si la llamada falla.
    """
    token   = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        raise SystemExit("❌ Falta TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID")

    # Telegram permite 4 096 caracteres por mensaje
    if len(texto) > 4_096:
        texto = texto[:3_900] + "\n\n[Mensaje truncado…]"

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": texto,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }

    try:
        res = requests.post(url, data=payload, timeout=20)
        res.raise_for_status()
        print("✅ Mensaje enviado a Telegram", flush=True)
    except Exception as exc:
        raise SystemExit(f"❌ Error al enviar mensaje a Telegram: {exc}")