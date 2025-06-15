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
def _norm(texto: str) -> str:
    """Minúsculas sin acentos, sin espacios de extremos."""
    return (
        unicodedata.normalize("NFKD", texto)
        .encode("ascii", "ignore")
        .decode()
        .lower()
        .strip()
    )

# ─── scraper ───────────────────────────────────────────────────
def scrape() -> list[str]:
    scraper = cloudscraper.create_scraper(
        browser={"browser": "firefox", "platform": "windows", "mobile": False}
    )
    try:
        html = scraper.get(LISTADO_URL, headers=HEADERS, timeout=30).text
    except Exception as exc:
        print(f"⚠️  Ática: error al descargar la página → {exc}", file=sys.stderr)
        return []

    soup  = BeautifulSoup(html, "html.parser")
    cards = soup.select("div.item-vivienda")
    print(f"[DEBUG] ÁTICA → {len(cards)} tarjetas totales", flush=True)

    resultados: list[str] = []

    for card in cards:
        # ─ Nombre ───────────────────────────────────────────────
        name_tag = card.find("h3")
        nombre = name_tag.get_text(" ", strip=True) if name_tag else "SIN NOMBRE"

        # ─ Ubicación ────────────────────────────────────────────
        loc_tag = card.find("div", class_=re.compile(r"\bcol-md-7\b"))
        ubic_raw = loc_tag.get_text(" ", strip=True) if loc_tag else ""
        #   Cortamos en el primer separador (.,·,-,|)
        municipio_raw = re.split(r"[.\-·|]", ubic_raw, maxsplit=1)[0]
        municipio_norm = _norm(municipio_raw)

        #   ¿está en la lista de deseos?
        if not any(_norm(loc) in municipio_norm for loc in LOCALIZACIONES_DESEADAS):
            continue

        # ─ Enlace ───────────────────────────────────────────────
        link = card.select_one("a.cont[href]")
        url_promo = link["href"] if link else LISTADO_URL

        # ─ “Nuevo proyecto” flag ───────────────────────────────
        badge = card.find("span", class_=re.compile("badge"))
        es_nuevo = badge and "nuevo proyecto" in badge.get_text(strip=True).lower()

        # ─ Dormitorios (atributo data-numhabitaciones) ─────────
        dormitorios = limpiar_y_convertir_a_numero(card.get("data-numhabitaciones"))

        if es_nuevo:
            resultados.append(
                f"\n*{nombre} (Ática – Nuevo proyecto)*"
                f"\n📍 {municipio_raw.title()}"
                f"\n🔗 [Ver promoción]({url_promo})"
            )
            continue

        if dormitorios is not None and dormitorios < HABITACIONES_MINIMAS:
            continue  # precios ya están ≤ 270 000 € gracias al filtro de la URL

        resultados.append(
            f"\n*{nombre} (Ática)*"
            f"\n📍 {municipio_raw.title()}"
            f"\n🛏️ Dorms: {dormitorios if dormitorios else '—'}"
            f"\n🔗 [Ver promoción]({url_promo})"
        )

        time.sleep(0.35)  # pausa suave para no saturar

    print(f"[DEBUG] ÁTICA filtradas → {len(resultados)}", flush=True)
    return resultados