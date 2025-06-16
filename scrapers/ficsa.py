# scrapers/ficsa.py
# ──────────────────────────────────────────────────────────────
"""
Scraper FICSA via WordPress REST API
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
    try:
        promos = requests.get(API, headers=HEADERS, timeout=30).json()
    except Exception as exc:
        print(f"⚠️  FICSA: error API → {exc}")
        return []

    print(f"[DEBUG] FICSA API → {len(promos)} items", flush=True)

    resultados = []
    for p in promos:
        if not isinstance(p, dict):          # ← ① salta elementos que no son dict
            continue

        nombre = (p.get("title") or {}).get("rendered", "").strip()
        ubic   = (p.get("acf") or {}).get("localizacion", "").strip()
        if not nombre or not ubic:
            continue

        if not any(_norm(l) in _norm(ubic) for l in LOCALIZACIONES_DESEADAS):
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
