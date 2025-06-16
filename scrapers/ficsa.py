# scrapers/ficsa.py
# ───────────────────────────────────────────────────────────────
"""
Scraper FICSA
• Obtiene el token nonce (necesario para Ajax) probando con
  https://www.ficsa.es/promociones-valencia   y, si falla, sin subdominio.
• Descarga todas las páginas Ajax (scroll infinito).
• Extrae nombre, localización y enlace de cada tarjeta <div class="tilter">.
• Filtra sólo las promociones cuya localización contenga alguna ciudad
  definida en utils.LOCALIZACIONES_DESEADAS.
"""

from __future__ import annotations
import re, sys, time, unicodedata, requests
from bs4 import BeautifulSoup
from utils import HEADERS, LOCALIZACIONES_DESEADAS

# ————————————————————————————————————————————————————————
URLS_BASE = (
    "https://www.ficsa.es/promociones-valencia",  # preferido
    "https://ficsa.es/promociones-valencia",       # respaldo
)
AJAX_PATH = "/wp-admin/admin-ajax.php"

# ————————————————————————————————————————————————————————
def _norm(texto: str) -> str:
    return (
        unicodedata.normalize("NFKD", texto)
        .encode("ascii", "ignore")
        .decode()
        .lower()
        .strip()
    )

def _get_nonce() -> tuple[str, str] | None:
    """
    Devuelve (nonce, dominio_base). Prueba con www y sin www.
    Busca el token tanto en data-nonce del botón como en el bloque JS.
    """
    for listado in URLS_BASE:
        try:
            html = requests.get(listado, headers=HEADERS, timeout=30).text
        except requests.HTTPError:
            continue

        m = re.search(r'id=["\']more_posts_ajax["\'][^>]*data-nonce="([^"]+)"', html, re.I)
        if not m:
            m = re.search(r'"nonce"\s*:\s*"([a-zA-Z0-9]+)"', html)
        if m:
            nonce = m.group(1)
            dominio = listado.split("/promociones-")[0]  # https://www.ficsa.es
            return nonce, dominio
    return None

def _ajax_page(page: int, nonce: str, dominio: str) -> str:
    payload = {"action": "more_post_ajax", "paged": str(page), "nonce": nonce}
    hdrs = {**HEADERS,
            "Referer": f"{dominio}/promociones-valencia",
            "X-Requested-With": "XMLHttpRequest"}
    resp = requests.post(f"{dominio}{AJAX_PATH}", data=payload, headers=hdrs, timeout=30)
    resp.raise_for_status()
    return resp.text

# ————————————————————————————————————————————————————————
def scrape() -> list[str]:
    datos_nonce = _get_nonce()
    if not datos_nonce:
        print("⚠️  FICSA: no se pudo obtener nonce", file=sys.stderr)
        return []
    nonce, dominio = datos_nonce

    # Descargar bloques Ajax
    bloques_html = []
    page = 1
    while True:
        chunk = _ajax_page(page, nonce, dominio)
        if not chunk.strip():
            break
        bloques_html.append(chunk)
        page += 1
        time.sleep(0.4)

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

            if not any(_norm(c) in _norm(ubic) for c in LOCALIZACIONES_DESEADAS):
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