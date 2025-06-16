# scrapers/ficsa.py
# ──────────────────────────────────────────────────────────────
"""
Scraper FICSA via WordPress REST API

Endpoint:
  https://www.ficsa.es/wp-json/wp/v2/promociones?per_page=100
Campos clave por promo (JSON):
  • title.rendered            → Nombre
  • acf.localizacion          → Ej. "Av Constitución 191 · VALENCIA"
  • link                      → URL de la ficha
Filtra solo por LOCALIZACIONES_DESEADAS.
"""
import time, unicodedata, requests
from utils import HEADERS, LOCALIZACIONES_DESEADAS

API = "https://www.ficsa.es/wp-json/wp/v2/promociones?per_page=100"

def _norm(txt: str) -> str:
    return (
        unicodedata.normalize("NFKD", txt)
        .encode("ascii", "ignore")
        .decode()
        .lower()
        .strip()
    )

def scrape() -> list[str]:
    promos = requests.get(API, headers=HEADERS, timeout=30).json()
    print(f"[DEBUG] FICSA API → {len(promos)} promos", flush=True)

    resultados = []
    for p in promos:
        nombre = p["title"]["rendered"].strip()
        ubic   = (p.get("acf", {}).get("localizacion") or "").strip()
        if not nombre or not ubic:
            continue

        if not any(_norm(loc) in _norm(ubic) for loc in LOCALIZACIONES_DESEADAS):
            continue

        url = p.get("link") or "https://www.ficsa.es/"

        resultados.append(
            f"\n*{nombre} (FICSA)*"
            f"\n📍 {ubic.title()}"
            f"\n🔗 [Ver promoción]({url})"
        )
        time.sleep(0.1)

    print(f"[DEBUG] FICSA filtradas → {len(resultados)}", flush=True)
    return resultados
