# scrapers/atica.py
# ────────────────────────────────────────────────────────────────
import re, time, sys
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

def scrape() -> list[str]:
    scraper = cloudscraper.create_scraper(
        browser={"browser": "firefox", "platform": "windows", "mobile": False}
    )
    try:
        html = scraper.get(LISTADO_URL, headers=HEADERS, timeout=30).text
    except Exception as exc:
        print(f"⚠️  Ática: error al descargar la página → {exc}", file=sys.stderr)
        return []

    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("div.card[data-provincia]")
    print(f"[DEBUG] ÁTICA → {len(cards)} tarjetas totales", flush=True)

    resultados = []

    for card in cards:
        # Nombre
        name_tag = card.find("p", class_=re.compile("title-rel"))
        nombre = name_tag.get_text(" ", strip=True) if name_tag else "SIN NOMBRE"

        # Ubicación
        loc_tag = card.find("p", class_=re.compile("text-prov"))
        ubic = loc_tag.get_text(" ", strip=True).lower() if loc_tag else None
        if not (ubic and any(l in ubic for l in LOCALIZACIONES_DESEADAS)):
            continue

        # Enlace
        link = card.select_one("a[href]")
        url_promo = link["href"] if link else LISTADO_URL

        # Nuevo proyecto
        badge = card.find("span", class_=re.compile("badge"))
        es_nuevo = badge and "nuevo proyecto" in badge.get_text(strip=True).lower()

        # Dormitorios
        dorms = limpiar_y_convertir_a_numero(card.get("data-numhabitaciones"))

        if es_nuevo:
            resultados.append(
                f"\n*{nombre} (Ática – Nuevo proyecto)*"
                f"\n📍 {ubic.title()}"
                f"\n🔗 [Ver promoción]({url_promo})"
            )
        else:
            if dorms is not None and dorms < HABITACIONES_MINIMAS:
                continue
            resultados.append(
                f"\n*{nombre} (Ática)*"
                f"\n📍 {ubic.title()}"
                f"\n🛏️ Dorms: {dorms if dorms else '—'}"
                f"\n🔗 [Ver promoción]({url_promo})"
            )

        time.sleep(0.4)   # pequeña pausa

    print(f"[DEBUG] ÁTICA filtradas → {len(resultados)}", flush=True)
    return resultados