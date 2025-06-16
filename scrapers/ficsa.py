# scrapers/ficsa.py
# ──────────────────────────────────────────────────────────────
"""
Scraper FICSA
Paso 1: WordPress REST API  → /wp-json/wp/v2/promociones
Paso 2: Si la API no da datos válidos, parsea el HTML listado.
Filtros: localidad ∈ LOCALIZACIONES_DESEADAS
"""

import time, unicodedata, re, sys, requests
from bs4 import BeautifulSoup
from utils import HEADERS, LOCALIZACIONES_DESEADAS

API_URL   = "https://www.ficsa.es/wp-json/wp/v2/promociones?per_page=100&_fields=title,acf,link"
HTML_URL  = "https://www.ficsa.es/promociones-valencia"

def _norm(t: str) -> str:
    return unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower().strip()

def _loc_ok(texto: str) -> bool:
    return any(_norm(l) in _norm(texto) for l in LOCALIZACIONES_DESEADAS)

# ──────────────────────────────────────────────────────────────
def _via_api() -> list[str]:
    try:
        promos = requests.get(API_URL, headers=HEADERS, timeout=30).json()
    except Exception as exc:
        print(f"⚠️  FICSA API error → {exc}", file=sys.stderr)
        return []

    if isinstance(promos, dict):  # a veces WP devuelve objeto
        promos = [promos]

    resultados = []
    for p in promos:
        if not isinstance(p, dict):
            continue
        nombre = (p.get("title") or {}).get("rendered", "").strip()
        ubic   = (p.get("acf")   or {}).get("localizacion", "").strip()
        if not nombre or not ubic or not _loc_ok(ubic):
            continue
        url = p.get("link") or HTML_URL
        resultados.append(
            f"\n*{nombre} (FICSA)*"
            f"\n📍 {ubic.title()}"
            f"\n🔗 [Ver promoción]({url})"
        )
    print(f"[DEBUG] FICSA API filtradas → {len(resultados)}", flush=True)
    return resultados

# ──────────────────────────────────────────────────────────────
def _via_html() -> list[str]:
    try:
        html = requests.get(HTML_URL, headers=HEADERS, timeout=30).text
    except Exception as exc:
        print(f"⚠️  FICSA HTML error → {exc}", file=sys.stderr)
        return []

    soup  = BeautifulSoup(html, "html.parser")
    cards = soup.select("div.tilter")
    print(f"[DEBUG] FICSA HTML → {len(cards)} tarjetas", flush=True)

    resultados = []
    for c in cards:
        nombre = (c.find("h3", class_="tilter__title") or "").get_text(" ", strip=True)
        ubic   = (c.find("p",  class_="tilter__description") or "").get_text(" ", strip=True)
        if not nombre or not ubic or not _loc_ok(ubic):
            continue
        a = c.find_parent("a", href=True) or c.find("a", href=True)
        url = ("https://www.ficsa.es" + a["href"]) if (a and a["href"].startswith("/")) else (a["href"] if a else HTML_URL)
        resultados.append(
            f"\n*{nombre} (FICSA)*"
            f"\n📍 {ubic.title()}"
            f"\n🔗 [Ver promoción]({url})"
        )
        time.sleep(0.1)
    print(f"[DEBUG] FICSA HTML filtradas → {len(resultados)}", flush=True)
    return resultados

# ──────────────────────────────────────────────────────────────
def scrape() -> list[str]:
    res_api = _via_api()
    if res_api:
        return res_api          # éxito con la API

    # Si la API no devolvió nada útil, usa el HTML
    return _via_html()
