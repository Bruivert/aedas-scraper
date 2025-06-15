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
def _norm(s: str) -> str:
    """Minúsculas sin tildes ni espacios extremos."""
    return (
        unicodedata.normalize("NFKD", s)
        .encode("ascii", "ignore")
        .decode()
        .lower()
        .strip()
    )

def _municipio(cadena_ubic: str) -> str:
    """
    Devuelve el municipio sin la palabra 'valencia' ni separadores
    '.', '·', '-', '|'.
    """
    sin_prov = re.sub(r"\bvalencia\b", "", cadena_ubic, flags=re.I)
    limpio   = re.sub(r"[.\-·|]", " ", sin_prov)
    limpio   = re.sub(r"\s+", " ", limpio)
    return _norm(limpio)

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

    resultados = []

    for card in cards:
        # ─ Nombre ───────────────────────────────────────────────
        h3 = card.find("h3")
        nombre = h3.get_text(" ", strip=True) if h3 else "SIN NOMBRE"

        # ─ Ubicación (municipio) ────────────────────────────────
        loc_tag = card.find("div", class_=re.compile(r"\bcol-md-7\b"))
        ubic_raw = loc_tag.get_text(" ", strip=True) if loc_tag else ""
        municipio = _municipio(ubic_raw)

        if not any(_norm(l) in municipio for l in LOCALIZACIONES_DESEADAS):
            continue  # fuera de tu lista

        # ─ Enlace ───────────────────────────────────────────────
        link = card.select_one("a.cont[href]")
        url_promo = link["href"] if link else LISTADO_URL

        # ─ “Nuevo proyecto” flag ───────────────────────────────
        badge = card.find("span", class_=re.compile("badge"))
        es_nuevo = badge and "nuevo proyecto" in badge.get_text(strip=True).lower()

        # ─ Dormitorios (atributo o span.habitaciones) ──────────
        dormitorios = limpiar_y_convertir_a_numero(card.get("data-numhabitaciones"))
        if dormitorios is None:
            hab_tag = card.find("span", class_=re.compile("habitaciones", re.I))
            dormitorios = limpiar_y_convertir_a_numero(hab_tag.get_text() if hab_tag else None)

        if es_nuevo:
            resultados.append(
                f"\n*{nombre} (Ática – Nuevo proyecto)*"
                f"\n📍 {ubic_raw.title()}"
                f"\n🔗 [Ver promoción]({url_promo})"
            )
            continue

        if dormitorios is not None and dormitorios < HABITACIONES_MINIMAS:
            continue  # precios ya ≤ 270 000 € gracias a la URL

        resultados.append(
            f"\n*{nombre} (Ática)*"
            f"\n📍 {ubic_raw.title()}"
            f"\n🛏️ Dorms: {dormitorios if dormitorios else '—'}"
            f"\n🔗 [Ver promoción]({url_promo})"
        )
        time.sleep(0.3)

    print(f"[DEBUG] ÁTICA filtradas → {len(resultados)}", flush=True)
    return resultados