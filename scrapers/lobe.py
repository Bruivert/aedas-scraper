# scrapers/lobe.py
# ──────────────────────────────────────────────────────────────
"""
Scraper Grupo LOBE
- URL raíz : https://www.grupolobe.com/promociones   (lista todas)
- Cada ficha está en un <label class="container-check">   e incluye:
      <span class="promo">NOMBRE</span>
      <span class="zona">LOCALIZACIÓN</span>
 - Se considera válida si la LOCALIZACIÓN contiene alguna de
  LOCALIZACIONES_DESEADAS (definidas en utils.py).
"""
import re, time, unicodedata, requests
from bs4 import BeautifulSoup
from utils import HEADERS, LOCALIZACIONES_DESEADAS

URL = "https://www.grupolobe.com/pisos-obra-nueva-valencia/"

def _norm(txt: str) -> str:
    """Minúsculas sin tildes ni espacios extremos."""
    return (
        unicodedata.normalize("NFKD", txt)
        .encode("ascii", "ignore")
        .decode()
        .lower()
        .strip()
    )

def scrape() -> list[str]:
    html = requests.get(URL, headers=HEADERS, timeout=30).text
    soup = BeautifulSoup(html, "html.parser")

    cards = soup.select("label.container-check")
    print(f"[DEBUG] LOBE → {len(cards)} tarjetas totales", flush=True)

    resultados: list[str] = []

    for c in cards:
        nombre_tag = c.find("span", class_="promo")
        nombre = nombre_tag.get_text(" ", strip=True) if nombre_tag else "SIN NOMBRE"

        zona_tag = c.find("span", class_="zona")
        ubic_raw = zona_tag.get_text(" ", strip=True) if zona_tag else ""
        if not any(_norm(l) in _norm(ubic_raw) for l in LOCALIZACIONES_DESEADAS):
            continue

        # enlace: la web usa checkboxes; construimos URL por slug de value
        value = c.find("input", {"value": True})["value"]
        url_promo = f"https://www.grupolobe.com/{value}" if value else URL

        resultados.append(
            f"\n*{nombre} (LOBE)*"
            f"\n📍 {ubic_raw.title()}"
            f"\n🔗 [Ver promoción]({url_promo})"
        )
        time.sleep(0.15)

    print(f"[DEBUG] LOBE filtradas → {len(resultados)}", flush=True)
    return resultados
