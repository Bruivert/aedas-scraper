# scrapers/aedas.py
# Scraper AEDAS (provincia de Valencia) con salto a la página de detalle
# ---------------------------------------------------------------------
import re, requests, time
from bs4 import BeautifulSoup
from utils import (
    HEADERS, LOCALIZACIONES_DESEADAS, PRECIO_MAXIMO,
    HABITACIONES_MINIMAS, limpiar_y_convertir_a_numero
)

LISTING_URL = "https://www.aedashomes.com/viviendas-obra-nueva?province=2509951"

def _parse_detalle(url_detalle: str) -> tuple[str, str, int | None, int | None]:
    """
    Devuelve (nombre, ubicacion, precio, dormitorios) a partir de la URL de detalle.
    """
    res = requests.get(url_detalle, headers=HEADERS, timeout=30)
    res.raise_for_status()
    s = BeautifulSoup(res.text, "html.parser")

    # 1. Nombre de la promo  ─────────────────────────────────────────────
    h1 = s.find("h1")
    nombre = h1.get_text(" ", strip=True) if h1 else "SIN NOMBRE"

    # 2. Ubicación (en el breadcrumb: <li><span>Valencia</span> …) ───────
    ubic = None
    crumb = s.select_one("nav.breadcrumb li:last-child span")
    if crumb:
        ubic = crumb.get_text(strip=True).lower()

    # 3. Bloque <div class="features-item"> … <span class="title">Precio desde</span>
    precio, dormitorios = None, None
    for div in s.select("div.features-item"):
        title = div.select_one("span.title")
        info  = div.select_one("span.info")
        if not (title and info):
            continue
        t = title.get_text(strip=True).lower()
        if "precio" in t:
            precio = limpiar_y_convertir_a_numero(info.get_text())
        elif "dormitorio" in t:
            dormitorios = limpiar_y_convertir_a_numero(info.get_text())

    return nombre, ubic, precio, dormitorios


def scrape() -> list[str]:
    """
    Recorre el listing de AEDAS, entra a cada promoción y filtra por los
    criterios definidos en utils.py. Devuelve una lista de strings Markdown.
    """
    res = requests.get(LISTING_URL, headers=HEADERS, timeout=30)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

    # Cada promo está en <li class="card_item"> (si cambian la clase, cámbiala aquí)
    cards = soup.select("li.card_item a.card_link")
    print(f"[DEBUG] AEDAS → {len(cards)} tarjetas en el listado", flush=True)

    resultados = []
    for a in cards:
        url_detalle = "https://www.aedashomes.com" + a["href"]
        try:
            nombre, ubic, precio, dormitorios = _parse_detalle(url_detalle)
            time.sleep(0.8)               # pausa suave para no saturar el servidor
        except Exception as exc:
            print(f"⚠️  Error al parsear {url_detalle}: {exc}", flush=True)
            continue

        if not all([ubic, precio, dormitorios]):
            continue

        if (any(l in ubic for l in LOCALIZACIONES_DESEADAS)
                and precio <= PRECIO_MAXIMO
                and dormitorios >= HABITACIONES_MINIMAS):
            resultados.append(
                f"\n*{nombre} (AEDAS)*"
                f"\n📍 {ubic.title()}"
                f"\n💶 Desde: {precio:,}€"
                f"\n🛏️ Dorms: {dormitorios}"
                f"\n🔗 [Ver promoción]({url_detalle})".replace(",", ".")
            )

    print(f"[DEBUG] AEDAS filtradas → {len(resultados)}", flush=True)
    return resultados