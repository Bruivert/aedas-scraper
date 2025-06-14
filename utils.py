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


# ——— util para escapar Markdown ————————————————————————
MD_SPECIALS = r"[_*~`>#+\-=|{}.!]"

def escapar_markdown(texto: str) -> str:
    """Escapa todos los caracteres especiales de Markdown v2."""
    return re.sub(MD_SPECIALS, lambda m: f"\\{m.group(0)}", texto)


# ——— envío robusto a Telegram ——————————————————————————
def enviar_mensaje_telegram(texto: str) -> None:
    """
    Envía 'texto' al chat definido en las variables de entorno:
      • TELEGRAM_BOT_TOKEN
      • TELEGRAM_CHAT_ID

    • Divide el mensaje en bloques ≤ 3 500 chars (margen sobre 4 096).
    • Escapa caracteres Markdown problemáticos.
    • Si Telegram devuelve 400, reenvía el bloque como texto plano.
    """
    token   = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise SystemExit("❌ Falta TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID")

    texto = escapar_markdown(texto)
    url   = f"https://api.telegram.org/bot{token}/sendMessage"

    while texto:
        bloque = texto[:3500]                      # margen de seguridad
        corte  = bloque.rfind("\n")
        if 0 < corte < 3200:                       # corta en línea completa
            bloque = bloque[:corte]
        texto = texto[len(bloque):]

        payload = {
            "chat_id": chat_id,
            "text": bloque,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }

        try:
            r = requests.post(url, data=payload, timeout=20)
            r.raise_for_status()
        except requests.exceptions.HTTPError as http_exc:
            # 400 Bad Request normalmente por Markdown mal escapado
            print(f"⚠️  Telegram 400: reenvío bloque sin Markdown → {http_exc}")
            payload.pop("parse_mode", None)
            requests.post(url, data=payload, timeout=20).raise_for_status()
        except Exception as exc:
            raise SystemExit(f"❌ Error al enviar a Telegram: {exc}")

    print("✅ Mensajes enviados a Telegram", flush=True)
