# scrapers/atica.py
# ────────────────────────────────────────────────────────────────
"""
Scraper Grupo Ática (promociones ≤ 270 000 € en la provincia de Valencia)

• URL ya filtrada por precio (0-270 000 €)
• Extrae:
    – Nombre  (h3 dentro de la tarjeta)
    – Ubicación  (div.row > div.col-md-7 …)
    – Precio  (div.tag.price  → solo informativo)
    – Nº dormitorios si aparece en el texto
• Incluye tarjetas “Nuevo proyecto” (badge con ese texto).
"""

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
    # cloudscraper evita la pantalla de Cloudflare
    scraper = cloudscraper.create_scraper(
        browser={"browser": "firefox", "platform": "windows", "mobile": False}
    )
    try:
        html = scraper.get(LISTADO_URL, headers=HEADERS, timeout=30).text
    except Exception as exc:
        print(f"⚠️  Ática: fallo al descargar la página → {exc}", file=sys.stderr)
        return []

    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("div.item-vivienda")
    print(f"[DEBUG] ÁTICA → {len(cards)} tarjetas totales", flush=True)

    resultados: list[str] = []

    for card in cards:
        # ─ nombre ────────────────────────────────────────────────
        h3 = card.find("h3")
        nombre = h3.get_text(" ", strip=True) if h3 else "SIN NOMBRE"

        # ─ ubicación ─────────────────────────────────────────────
        loc_tag = card.select_one("div.row div.col-md-7")
        ubic = loc_tag.get_text(" ", strip=True).lower() if loc_tag else None
        if not (ubic and any(l in ubic for l in LOCALIZACIONES_DESEADAS)):
            continue  # descarta fuera de tu zona

        # ─ enlace ────────────────────────────────────────────────
        link = card.select_one("a.cont[href]")
        url_promo = link["href"] if link else LISTADO_URL

        # ─ “Nuevo proyecto” flag ────────────────────────────────
        badge = card.find("span", class_=re.compile("badge"))
        es_nuevo = badge and "nuevo proyecto" in badge.get_text(strip=True).lower()

        # ─ precio (solo informativo) ─────────────────────────────
        price_tag = card.select_one("div.tag.price")
        precio_txt = price_tag.get_text(strip=True) if price_tag else None
        precio = limpiar_y_convertir_a_numero(precio_txt)

        # ─ dormitorios (si aparece “dormitorio” en cualquier nodo) ─
        dorm_txt = card.find(string=re.compile("dormitorio", re.I))
        dormitorios = limpiar_y_convertir_a_numero(dorm_txt)

        # ─ bloque “Nuevo proyecto” ───────────────────────────────
        if es_nuevo:
            resultados.append(
                f"\n*{nombre} (Ática – Nuevo proyecto)*"
                f"\n📍 {ubic.title()}"
                f"\n🔗 [Ver promoción]({url_promo})"
            )
            continue

        # ─ bloque en venta ───────────────────────────────────────
        if dormitorios is not None and dormitorios < HABITACIONES_MINIMAS:
            continue  # filtra si sabemos que tiene menos habitaciones

        resultados.append(
            f"\n*{nombre} (Ática)*"
            f"\n📍 {ubic.title()}"
            + (f"\n💶 Desde: {precio:,}€" if precio else "")
            + (f"\n🛏️ Dorms: {dormitorios}" if dormitorios else "")
            + f"\n🔗 [Ver promoción]({url_promo})"
        )

        time.sleep(0.3)   # pausa suave

    print(f"[DEBUG] ÁTICA filtradas → {len(resultados)}", flush=True)
    return resultados