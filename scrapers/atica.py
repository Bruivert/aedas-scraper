# scrapers/atica.py
# ───────────────────────────────────────────────────────────────
import re, sys, time, unicodedata
import cloudscraper
from bs4 import BeautifulSoup
from utils import (
    HEADERS,
    LOCALIZACIONES_DESEADAS,
    HABITACIONES_MINIMAS,
    limpiar_y_convertir_a_numero,
)

LISTADO_URL = (
    "https://grupo-atica.com/propiedades/public/"
    "?obranueva_viviendas=2&order=&quantity=&disposicion=listado"
    "&tipologia=&comprar_alquilar=&tipo_inmueble=0"
    "&provincia=Valencia&localidad=&habitaciones=&banyos="
    "&price=0%2C270000"
)

# ─── helpers ───────────────────────────────────────────────────
def _norm(txt: str) -> str:
    """Minúsculas sin tildes para comparar localidades."""
    return unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode().lower().strip()

# ─── scraper ───────────────────────────────────────────────────
def scrape() -> list[str]:
    scraper = cloudscraper.create_scraper(browser={"browser": "firefox", "platform": "windows"})
    try:
        html = scraper.get(LISTADO_URL, headers=HEADERS, timeout=30).text
    except Exception as exc:
        print(f"⚠️  Ática: error al descargar la página → {exc}", file=sys.stderr)
        return []

    soup  = BeautifulSoup(html, "html.parser")
    cards = soup.select("div.item-vivienda")
    print(f"[DEBUG] ÁTICA → {len(cards)} tarjetas totales", flush=True)

    resultados = []

    for card in cards:
        # ─── Nombre ────────────────────────────────────────────
        h3 = card.find("h3")
        nombre = h3.get_text(" ", strip=True) if h3 else "SIN NOMBRE"

        # ─── Ubicación (municipio) ─────────────────────────────
        loc_tag = card.find("div", class_=re.compile(r"\bcol-md-7\b"))
        ubic_raw = loc_tag.get_text(" ", strip=True) if loc_tag else ""
        municipio = _norm(ubic_raw.split(".")[0])          # texto antes del punto

        if not any(_norm(l) == municipio for l in LOCALIZACIONES_DESEADAS):
            continue  # descarta si no está en tu lista

        # ─── Enlace ────────────────────────────────────────────
        link = card.select_one("a.cont[href]")
        url_promo = link["href"] if link else LISTADO_URL

        # ─── “Nuevo proyecto” flag ────────────────────────────
        badge = card.find("span", class_=re.compile("badge"))
        es_nuevo = badge and "nuevo proyecto" in badge.get_text(strip=True).lower()

        # ─── Dormitorios ──────────────────────────────────────
        dorms_attr = card.get("data-numhabitaciones")
        dormitorios = limpiar_y_convertir_a_numero(dorms_attr)

        if es_nuevo:
            resultados.append(
                f"\n*{nombre} (Ática – Nuevo proyecto)*"
                f"\n📍 {ubic_raw.title()}"
                f"\n🔗 [Ver promoción]({url_promo})"
            )
            continue

        # ─── Filtrado por dormitorios (precios ya ≤ 270 000) ──
        if dormitorios is not None and dormitorios < HABITACIONES_MINIMAS:
            continue

        resultados.append(
            f"\n*{nombre} (Ática)*"
            f"\n📍 {ubic_raw.title()}"
            f"\n🛏️ Dorms: {dormitorios if dormitorios else '—'}"
            f"\n🔗 [Ver promoción]({url_promo})"
        )

        time.sleep(0.4)  # pequeña pausa

    print(f"[DEBUG] ÁTICA filtradas → {len(resultados)}", flush=True)
    return resultados