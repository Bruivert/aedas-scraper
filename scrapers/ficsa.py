# scrapers/ficsa.py
# ───────────────────────────────────────────────────────────────
"""
Scraper FICSA

• Origen de datos: scroll infinito de la página
  https://www.ficsa.es/promociones-valencia

  Internamente llama a:
    POST https://www.ficsa.es/wp-admin/admin-ajax.php
         action=more_post_ajax&paged=1 (2, 3, …)

  El endpoint sólo responde si se incluyen los encabezados:
      Referer: https://www.ficsa.es/promociones-valencia
      X-Requested-With: XMLHttpRequest

• Cada bloque HTML devuelto contiene div.tilter con:
      <h3 class="tilter__title">NOMBRE</h3>
      <p  class="tilter__description">LOCALIZACIÓN</p>

  No hay precio ni dormitorios: filtramos sólo por localidad.
"""
from __future__ import annotations

import re
import sys
import time
import unicodedata

import requests
from bs4 import BeautifulSoup

from utils import HEADERS, LOCALIZACIONES_DESEADAS

AJAX_URL = "https://www.ficsa.es/wp-admin/admin-ajax.php"
REFERER  = "https://www.ficsa.es/promociones-valencia"


# ── helpers ────────────────────────────────────────────────────
def _norm(texto: str) -> str:
    """Minúsculas sin tildes ni espacios extremos para comparar."""
    return (
        unicodedata.normalize("NFKD", texto)
        .encode("ascii", "ignore")
        .decode()
        .lower()
        .strip()
    )


def _ajax_page(page: int) -> str:
    """Devuelve el HTML de la página 'page' (o cadena vacía si ya no hay más)."""
    data = {"action": "more_post_ajax", "paged": str(page)}
    ajax_headers = {
        **HEADERS,
        "Referer": REFERER,
        "X-Requested-With": "XMLHttpRequest",
    }
    resp = requests.post(AJAX_URL, data=data, headers=ajax_headers, timeout=30)
    resp.raise_for_status()
    return resp.text


# ── scraper principal ─────────────────────────────────────────
def scrape() -> list[str]:
    bloques_html: list[str] = []
    page = 1

    try:
        while True:
            chunk = _ajax_page(page)
            if not chunk.strip():
                break
            bloques_html.append(chunk)
            page += 1
            time.sleep(0.4)  # pausa para no saturar
    except Exception as exc:  # red, timeout, 4xx
        print(f"⚠️  FICSA Ajax error → {exc}", file=sys.stderr)

    print(f"[DEBUG] FICSA Ajax pages → {len(bloques_html)}", flush=True)

    resultados: list[str] = []

    for chunk in bloques_html:
        soup = BeautifulSoup(chunk, "html.parser")
        for card in soup.select("div.tilter"):
            nombre = (
                card.find("h3", class_="tilter__title")
                .get_text(" ", strip=True)
                if card.find("h3", class_="tilter__title")
                else ""
            )
            ubic = (
                card.find("p", class_="tilter__description")
                .get_text(" ", strip=True)
                if card.find("p", class_="tilter__description")
                else ""
            )

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

    print(f"[DEBUG] FICSA filtradas → {len(resultados)}", flush=True)
    return resultados
