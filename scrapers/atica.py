# scrapers/atica.py
# ───────────────────────────────────────────────────────────────
import re, sys, time, unicodedata
import cloudscraper
from bs4 import BeautifulSoup
from utils import (
    HEADERS,
    LOCALIZACIONES_DESEADAS,
    PRECIO_MAXIMO,
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

# ── helpers ────────────────────────────────────────────────────
def _norm(s: str) -> str:
    return (
        unicodedata.normalize("NFKD", s)
        .encode("ascii", "ignore")
        .decode()
        .lower()
        .strip()
    )

def _municipio(ubic: str) -> str:
    sin_prov = re.sub(r"\bvalencia\b", "", ubic, flags=re.I)
    limpio   = re.sub(r"[.\-·|]", " ", sin_prov)
    limpio   = re.sub(r"\s+", " ", limpio)
    return _norm(limpio)

def _precio_desde_card(card: BeautifulSoup) -> int | None:
    """Devuelve el primer número seguido de ‘€’ dentro de la tarjeta."""
    m = re.search(r"\d[\d.]*\s*€", card.get_text(" ", strip=True))
    return limpiar_y_convertir_a_numero(m.group(0)) if m else None

# ── scraper ────────────────────────────────────────────────────
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

    resultados = []

    for card in cards:
        # ─ Nombre ───────────────────────────────────────────────
        h3 = card.find("h3")
        nombre = h3.get_text(" ", strip=True) if h3 else "SIN NOMBRE"

        # ─ Ubicación (municipio) ────────────────────────────────
        loc_tag   = card.find("div", class_=re.compile(r"\bcol-md-7\b"))
        ubic_raw = loc_tag.get_text(" ", strip=True) if loc_tag else ""
ubic_raw = re.sub(r"^[\s.\-·|]+", "", ubic_raw)   # quita separadores iniciales
        municipio = _municipio(ubic_raw)

        if not any(_norm(loc) in municipio for loc in LOCALIZACIONES_DESEADAS):
            continue

        # ─ Enlace ───────────────────────────────────────────────
        link = card.select_one("a.cont[href]")
        url_promo = link["href"] if link else LISTADO_URL

        # ─ “Nuevo proyecto” flag ───────────────────────────────
        badge = card.find("span", class_=re.compile("badge"))
        es_nuevo = badge and "nuevo proyecto" in badge.get_text(strip=True).lower()

        # ─ Dormitorios ──────────────────────────────────────────
        dormitorios = limpiar_y_convertir_a_numero(card.get("data-numhabitaciones"))
        if dormitorios is None:
            hab_tag = card.find("span", class_=re.compile("habitaciones", re.I))
            dormitorios = limpiar_y_convertir_a_numero(hab_tag.get_text() if hab_tag else None)

        # ─ Precio ───────────────────────────────────────────────
        precio = _precio_desde_card(card)

        # ─ Bloque “Nuevo proyecto” ──────────────────────────────
        if es_nuevo:
            resultados.append(
                f"\n*{nombre} (Ática – Nuevo proyecto)*"
                f"\n📍 {ubic_raw.title()}"
                f"\n🔗 [Ver promoción]({url_promo})"
            )
            continue

        # ─ Filtros en venta ─────────────────────────────────────
        if precio is None or precio > PRECIO_MAXIMO:
            continue
        if dormitorios is not None and dormitorios < HABITACIONES_MINIMAS:
            continue

        resultados.append(
            f"\n*{nombre} (Ática)*"
            f"\n📍 {ubic_raw.title()}"
            f"\n💶 Desde: {precio:,}€"
            f"\n🛏️ Dorms: {dormitorios if dormitorios else '—'}"
            f"\n🔗 [Ver promoción]({url_promo})".replace(",", ".")
        )
        time.sleep(0.3)

    print(f"[DEBUG] ÁTICA filtradas → {len(resultados)}", flush=True)
    return resultados