# scrapers/ficsa.py
# ───────────────────────────────────────────────────────────────
"""
Scraper FICSA

• Página de origen: https://www.ficsa.es/promociones-valencia
• La lista de promociones se carga por Ajax:
      POST /wp-admin/admin-ajax.php
        action=more_post_ajax
        paged = 1, 2, 3…
        nonce = TOKEN   ← obligatorio

  El token “nonce” se puede encontrar:
      A) como atributo data-nonce en el botón #more_posts_ajax
      B) en un bloque <script> que define   var ficsa_ajax = { "nonce":"XXXX" }

• Datos extraídos por promoción:
      – Nombre (h3.tilter__title)
      – Localización (p.tilter__description)
      – Enlace (href del <a> que envuelve la tarjeta)

• Se filtra por LOCALIZACIONES_DESEADAS (utils.py).  No hay precio ni dorms.
"""

from __future__ import annotations
import re, sys, time, unicodedata, requests
from bs4 import BeautifulSoup
from utils import HEADERS, LOCALIZACIONES_DESEADAS

LIST_URL = "https://www.ficsa.es/promociones-valencia"
AJAX_URL = "https://www.ficsa.es/wp-admin/admin-ajax.php"


# ── helpers ────────────────────────────────────────────────────
def _norm(txt: str) -> str:
    """Minúsculas sin tildes ni espacios extremos."""
    return (
        unicodedata.normalize("NFKD", txt)
        .encode("ascii", "ignore")
        .decode()
        .lower()
        .strip()
    )


def _get_nonce() -> str | None:
    """
    Intenta obtener el nonce de dos formas:
      1) Atributo data-nonce del botón #more_posts_ajax
      2) Dentro del bloque JS   var ficsa_ajax = { "nonce":"XXXX" }
    """
    resp = requests.get(LIST_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    html = resp.text

    # A) data-nonce en el botón
    m = re.search(r'id=["\']more_posts_ajax["\'][^>]*data-nonce="([^"]+)"', html)
    if m:
        return m.group(1)

    # B) nonce dentro del script
    m = re.search(r'"nonce"\s*:\s*"([a-zA-Z0-9]+)"', html)
    if m:
        return m.group(1)

    return None  # no encontrado


def _ajax_page(page: int, nonce: str) -> str:
    """Devuelve el HTML de la página Ajax indicada."""
    payload = {"action": "more_post_ajax", "paged": str(page), "nonce": nonce}
    hdrs = {
        **HEADERS,
        "Referer": LIST_URL,
        "X-Requested-With": "XMLHttpRequest",
    }
    resp = requests.post(AJAX_URL, data=payload, headers=hdrs, timeout=30)
    resp.raise_for_status()
    return resp.text


# ── scraper principal ─────────────────────────────────────────
def scrape() -> list[str]:
    nonce = _get_nonce()
    if not nonce:
        print("⚠️  FICSA: no se encontró nonce — no se pueden descargar promociones", file=sys.stderr)
        return []

    bloques_html: list[str] = []
    page = 1
    while True:
        chunk = _ajax_page(page, nonce)
        if not chunk.strip():
            break     # sin más resultados
        bloques_html.append(chunk)
        page += 1
        time.sleep(0.4)   # pausa suave

    print(f"[DEBUG] FICSA Ajax pages → {len(bloques_html)}", flush=True)

    resultados: list[str] = []
    for html in bloques_html:
        soup = BeautifulSoup(html, "html.parser")
        for card in soup.select("div.tilter"):
            name = card.find("h3", class_="tilter__title")
            loc  = card.find("p",  class_="tilter__description")
            if not (name and loc):
                continue

            nombre = name.get_text(" ", strip=True)
            ubic   = loc.get_text(" ", strip=True)

            if not any(_norm(city) in _norm(ubic) for city in LOCALIZACIONES_DESEADAS):
                continue

            a = card.find("a", href=True)
            url = (
                "https://www.ficsa.es" + a["href"]
                if a and a["href"].startswith("/")
                else (a["href"] if a else LIST_URL)
            )

            resultados.append(
                f"\n*{nombre} (FICSA)*"
                f"\n📍 {ubic.title()}"
                f"\n🔗 [Ver promoción]({url})"
            )
            time.sleep(0.1)

    print(f"[DEBUG] FICSA filtradas → {len(resultados)}", flush=True)
    return resultados