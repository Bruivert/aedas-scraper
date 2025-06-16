# scrapers/ficsa.py
# ───────────────────────────────────────────────────────────────
"""
Scraper FICSA
– Descarga las tarjetas de promociones mediante las llamadas Ajax
  que usa el scroll infinito de la página:
     https://www.ficsa.es/promociones-valencia
– Extrae nombre, localización y enlace de cada promoción.
– Filtra por LOCALIZACIONES_DESEADAS (utils.py).
"""

import re
import sys
import time
import unicodedata

import requests
from bs4 import BeautifulSoup

from utils import HEADERS, LOCALIZACIONES_DESEADAS

# Ajax endpoint usado por la web
AJAX_URL = "https://www.ficsa.es/wp-admin/admin-ajax.php"
REFERER  = "https://www.ficsa.es/promociones-valencia"


# ── helpers ────────────────────────────────────────────────────
def _norm(texto: str) -> str:
    """Normaliza texto: minúsculas + sin acentos + sin espacios extremos."""
    return (
        unicodedata.normalize("NFKD", texto)
        .encode("ascii", "ignore")
        .decode()
        .lower()
        .strip()
    )


def _ajax_page(page: int) -> str:
    """
    Devuelve el HTML de la página 'page' del scroll infinito.
    Añade las cabeceras que exige el servidor (Referer + X-Requested-With).
    """
    payload = {"action": "more_post_ajax", "paged": str(page)}
    ajax_headers = {
        **HEADERS,
        "Referer": REFERER,
        "X-Requested-With": "XMLHttpRequest",
    }
    resp = requests.post(
        AJAX_URL,
        data=payload,
        headers=ajax_headers,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.text


# ── scraper principal ─────────────────────────────────────────
def scrape() -> list[str]:
    bloques_html: list[str] = []
    page = 1

    # Paso 1-2: descargar todas las páginas Ajax
    try:
        while True:
            chunk = _ajax_page(page)
            if not chunk.strip():        # respuesta vacía ⇒ fin
                break
            bloques_html.append(chunk)
            page += 1
            time.sleep(0.4)              # pequeña pausa
    except Exception as exc:
        print(f"⚠️  FICSA Ajax error → {exc}", file=sys.stderr)

    print(f"[DEBUG] FICSA Ajax pages → {len(bloques_html)}", flush=True)

    resultados: list[str] = []

    # Paso 3-6: parsear tarjetas, filtrar y formatear Markdown
    for chunk in bloques_html:
        soup = BeautifulSoup(chunk, "html.parser")
        for card in soup.select("div.tilter"):
            name_tag = card.find("h3", class_="tilter__title")
            loc_tag  = card.find("p",  class_="tilter__description")
            nombre = name_tag.get_text(" ", strip=True) if name_tag else ""
            ubic   = loc_tag.get_text(" ", strip=True) if loc_tag else ""
            if (
                not nombre
                or not ubic
                or not any(_norm(l) in _norm(ubic) for l in LOCALIZACIONES_DESEADAS)
            ):
                continue

            a = card.find("a", href=True)
            url = (
                "https://www.ficsa.es" + a["href"]
                if a and a["href"].startswith("/")
                else (a["href"] if a else REFERER)
            )

            resultados.append(
                f"\n*{nombre} (FICSA)*"
                f"\n📍 {ubic.title()}"
                f"\n🔗 [Ver promoción]({url})"
            )
            time.sleep(0.1)

    # Paso 7: devolver lista de bloques Markdown
    print(f"[DEBUG] FICSA filtradas → {len(resultados)}", flush=True)
    return resultados