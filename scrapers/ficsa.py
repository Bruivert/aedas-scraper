# scrapers/ficsa.py
# ──────────────────────────────────────────────────────────────
"""
Scraper FICSA (obra nueva en la provincia de Valencia)

Página catálogo:  https://www.ficsa.es/promociones-valencia
Estructura de cada tarjeta
    <h3 class="tilter__title">LARES CONSTITUCIÓN</h3>
    <p  class="tilter__description">Av Constitución 191 · <br>VALÈNCIA</p>
    <a href="/promocion/lares-constitucion" … >
Filtra por LOCALIZACIONES_DESEADAS (utils.py).  No hay precio ni dorms.
"""

import time, unicodedata, re, requests
from bs4 import BeautifulSoup
from utils import HEADERS, LOCALIZACIONES_DESEADAS

URL_LISTADO = "https://www.ficsa.es/promociones-valencia"

def _norm(txt: str) -> str:
    return (
        unicodedata.normalize("NFKD", txt)
        .encode("ascii", "ignore")
        .decode()
        .lower()
        .strip()
    )

def scrape() -> list[str]:
    html = requests.get(URL_LISTADO, headers=HEADERS, timeout=30).text
    soup = BeautifulSoup(html, "html.parser")

    # Cada bloque de promo suele estar dentro de <a class="tilter"> … </a>
    cards = soup.select("a:has(h3.tilter__title)")
    print(f"[DEBUG] FICSA → {len(cards)} tarjetas totales", flush=True)

    resultados: list[str] = []
    for a in cards:
        nombre = (a.find("h3", class_="tilter__title") or "").get_text(" ", strip=True)
        desc   = (a.find("p", class_="tilter__description") or "").get_text(" ", strip=True)
        if not nombre or not desc:
            continue

        if not any(_norm(loc) in _norm(desc) for loc in LOCALIZACIONES_DESEADAS):
            continue

        url_promo = a["href"] if a.has_attr("href") else URL_LISTADO
        if url_promo.startswith("/"):
            url_promo = "https://www.ficsa.es" + url_promo

        resultados.append(
            f"\n*{nombre} (FICSA)*"
            f"\n📍 {desc.title()}"
            f"\n🔗 [Ver promoción]({url_promo})"
        )
        time.sleep(0.15)

    print(f"[DEBUG] FICSA filtradas → {len(resultados)}", flush=True)
    return resultados
