# scrapers/ficsa.py
# ───────────────────────────────────────────────────────────────
"""
Scraper FICSA

• Origen de la lista:  https://www.ficsa.es/promociones-valencia
  (si la versión sin «www» devuelve 404, se prueba la de «www»).

• La página carga las tarjetas con Ajax:
      POST /wp-admin/admin-ajax.php
         action = more_post_ajax
         paged  = 1, 2, 3…
         nonce  = TOKEN                       ← obligatorio

  El token «nonce» aparece siempre en el HTML:
     a) como data-nonce="XXXX"
     b) o dentro de un bloque JS "nonce":"XXXX"

• Se extraen de cada tarjeta <div class="tilter">
     – Nombre (h3.tilter__title)
     – Localización (p.tilter__description)
     – Enlace (href del <a>)
  y se filtra por las localidades definidas en utils.LOCALIZACIONES_DESEADAS.
"""

from __future__ import annotations
import re, sys, time, unicodedata

import requests
from bs4 import BeautifulSoup

from utils import HEADERS, LOCALIZACIONES_DESEADAS

AJAX_PATH = "/wp-admin/admin-ajax.php"


# ───────────────────────────────────────── helpers ─────────────
def _norm(txt: str) -> str:
    """minúsculas sin acentos ni espacios extremos"""
    return (
        unicodedata.normalize("NFKD", txt)
        .encode("ascii", "ignore")
        .decode()
        .lower()
        .strip()
    )


def _get_nonce() -> tuple[str, str] | None:
    """
    Devuelve (nonce, dominio_base).
    ▸ Prueba primero con https://www.ficsa.es/promociones-valencia
      y si recibe 404 prueba https://ficsa.es/promociones-valencia
    ▸ Busca:
        • cualquier data-nonce="XXXX"
        • o "nonce":"XXXX" dentro de un <script>
    """
    for listado in (
        "https://www.ficsa.es/promociones-valencia",
        "https://ficsa.es/promociones-valencia",
    ):
        try:
            html = requests.get(listado, headers=HEADERS, timeout=30).text
        except requests.RequestException:
            continue   # intenta con el siguiente dominio

        #   a) data-nonce="…"
        m = re.search(r'data-nonce\s*=\s*"([a-zA-Z0-9]+)"', html)
        if not m:
            #   b) "nonce":"…"
            m = re.search(r'"nonce"\s*:\s*"([a-zA-Z0-9]+)"', html)

        if m:
            dominio = listado.split("/promociones-")[0]   # «https://www.ficsa.es»
            return m.group(1), dominio
    return None


def _ajax_page(page: int, nonce: str, dominio: str) -> str:
    payload = {"action": "more_post_ajax", "paged": str(page), "nonce": nonce}
    hdrs = {
        **HEADERS,
        "Referer": f"{dominio}/promociones-valencia",
        "X-Requested-With": "XMLHttpRequest",
    }
    resp = requests.post(f"{dominio}{AJAX_PATH}", data=payload, headers=hdrs, timeout=30)
    resp.raise_for_status()
    return resp.text


# ───────────────────────────────────────── scraper ─────────────
def scrape() -> list[str]:
    datos = _get_nonce()
    if not datos:
        print("⚠️  FICSA: no se pudo obtener nonce", file=sys.stderr)
        return []
    nonce, dominio = datos

    # 1. Descargar todos los bloques Ajax
    bloques_html: list[str] = []
    page = 1
    while True:
        chunk = _ajax_page(page, nonce, dominio)
        if not chunk.strip():
            break
        bloques_html.append(chunk)
        page += 1
        time.sleep(0.4)   # pausa suave para no saturar

    print(f"[DEBUG] FICSA Ajax pages → {len(bloques_html)}", flush=True)

    # 2. Parsear y filtrar
    resultados: list[str] = []
    for html in bloques_html:
        soup = BeautifulSoup(html, "html.parser")
        for card in soup.select("div.tilter"):
            title = card.find("h3", class_="tilter__title")
            desc  = card.find("p",  class_="tilter__description")
            if not (title and desc):
                continue

            nombre = title.get_text(" ", strip=True)
            ubic   = desc.get_text(" ", strip=True)

            # filtrado por localidades deseadas
            if not any(_norm(city) in _norm(ubic) for city in LOCALIZACIONES_DESEADAS):
                continue

            a = card.find("a", href=True)
            url = (
                f"{dominio}{a['href']}"
                if a and a["href"].startswith("/")
                else (a["href"] if a else f"{dominio}/promociones-valencia")
            )

            resultados.append(
                f"\n*{nombre} (FICSA)*"
                f"\n📍 {ubic.title()}"
                f"\n🔗 [Ver promoción]({url})"
            )
            time.sleep(0.1)

    print(f"[DEBUG] FICSA filtradas → {len(resultados)}", flush=True)
    return resultados