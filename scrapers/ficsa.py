# scrapers/ficsa.py
# ───────────────────────────────────────────────────────────────
"""
Scraper FICSA

Página pública .......... https://www.ficsa.es/promociones-valencia
Ajax interno ............ POST https://www.ficsa.es/wp-admin/admin-ajax.php
                          parámetros: action=more_post_ajax, paged, nonce

Datos que se extraen por promoción:
  • Nombre        (h3.tilter__title)
  • Localización  (p.tilter__description)
  • Enlace        (href del <a> que envuelve la tarjeta)

Solo se conservan las promociones cuya localización contenga
alguna de las localidades definidas en utils.LOCALIZACIONES_DESEADAS.
"""

from __future__ import annotations

import re
import sys
import time
import unicodedata

import requests
from bs4 import BeautifulSoup

from utils import HEADERS, LOCALIZACIONES_DESEADAS

# --- URLs base -------------------------------------------------
LIST_URL = "https://www.ficsa.es/promociones-valencia"
AJAX_URL = "https://www.ficsa.es/wp-admin/admin-ajax.php"


# --- helpers ---------------------------------------------------
def _norm(txt: str) -> str:
    """minúsculas + sin acentos + sin espacios extremos"""
    return (
        unicodedata.normalize("NFKD", txt)
        .encode("ascii", "ignore")
        .decode()
        .lower()
        .strip()
    )


def _get_nonce() -> str | None:
    """
    Busca el token 'nonce' necesario para la petición Ajax.
    1) data-nonce del botón #more_posts_ajax
    2) variable JS   var ficsa_ajax = { "nonce":"XXXX" }
    """
    resp = requests.get(LIST_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    html = resp.text

    # A) atributo data-nonce
    m = re.search(
        r'id=["\']more_posts_ajax["\'][^>]*data-nonce="([^"]+)"', html, re.I
    )
    if m:
        return m.group(1)

    # B) bloque <script> con ficsa_ajax.nonce
    m = re.search(r'"nonce"\s*:\s*"([a-zA-Z0-9]+)"', html)
    if m:
        return m.group(1)

    return None


def _ajax_page(page: int, nonce: str) -> str:
    """Devuelve el HTML de la página `paged=page` del scroll infinito."""
    payload = {"action": "more_post_ajax", "paged": str(page), "nonce": nonce}
    hdrs = {
        **HEADERS,
        "Referer": LIST_URL,
        "X-Requested-With": "XMLHttpRequest",
    }
    r = requests.post(AJAX_URL, data=payload, headers=hdrs, timeout=30)
    r.raise_for_status()
    return r.text


# --- scraper principal ----------------------------------------
def scrape() -> list[str]:
    nonce = _get_nonce()
    if not nonce:
        print("⚠️  FICSA: nonce no encontrado – abortando", file=sys.stderr)
        return []

    bloques_html: list[str] = []
    page = 1
    while True:
        chunk = _ajax_page(page, nonce)
        if not chunk.strip():  # sin más resultados
            break
        bloques_html.append(chunk)
        page += 1
        time.sleep(0.4)        # pausa para no saturar

    print(f"[DEBUG] FICSA Ajax pages → {len(bloques_html)}", flush=True)

    resultados: list[str] = []
    for html in bloques_html:
        soup = BeautifulSoup(html, "html.parser")
        for card in soup.select("div.tilter"):
            name_tag = card.find("h3", class_="tilter__title")
            loc_tag  = card.find("p",  class_="tilter__description")
            if not (name_tag and loc_tag):
                continue

            nombre = name_tag.get_text(" ", strip=True)
            ubic   = loc_tag.get_text(" ", strip=True)

            # Filtrado por localidad
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