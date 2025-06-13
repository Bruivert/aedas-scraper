# scrapers/metrovacesa.py
# ─────────────────────────────────────────────────────────────────────
"""
Scraper Metrovacesa (provincia de Valencia)

• URL listada: https://metrovacesa.com/promociones/valencia
• Extrae:
    - Nombre de la promoción
    - Ubicación (p. ej. “VALENCIA / SAGUNTO/SAGUNT”)
    - Precio mínimo (si existe)
    - Nº dormitorios (si existe)
• Filtros:
    · Ubicación debe contener cualquiera de LOCALIZACIONES_DESEADAS
    · Si NO es “Nuevo proyecto”:
         – precio ≤ PRECIO_MAXIMO  (si hay precio)
         – dormitorios ≥ HABITACIONES_MINIMAS
    · Si ES “Nuevo proyecto”:
         – se incluyen aunque no haya precio ni dormitorios
"""

import re, requests
from bs4 import BeautifulSoup
from utils import (
    HEADERS,
    LOCALIZACIONES_DESEADAS,
    PRECIO_MAXIMO,
    HABITACIONES_MINIMAS,
    limpiar_y_convertir_a_numero,
)

LISTADO_URL = "https://metrovacesa.com/promociones/valencia"


def scrape() -> list[str]:
    res = requests.get(LISTADO_URL, headers=HEADERS, timeout=30)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

    # Cada tarjeta lleva el atributo data-provincia == "Valencia"
    cards = soup.select("div.card[data-provincia]")
    print(f"[DEBUG] METROVACESA → {len(cards)} tarjetas totales", flush=True)

    resultados = []

    for card in cards:
        # ───── nombre ──────────────────────────────────────────────
        name_tag = card.select_one("p.card-text.title-rel")
        nombre = name_tag.get_text(" ", strip=True) if name_tag else "SIN NOMBRE"

        # ───── ubicación ───────────────────────────────────────────
        loc_tag = card.select_one("p.card-text.mb-0")
        ubic = loc_tag.get_text(" ", strip=True).lower() if loc_tag else None

        # ───── precio (atributo data-preciomin) ────────────────────
        precio_attr = card.attrs.get("data-preciomin") or card.attrs.get("data-preciomax")
        precio = limpiar_y_convertir_a_numero(precio_attr)

        # ───── dormitorios (atributo data-numhabitaciones) ─────────
        dorm_attr = card.attrs.get("data-numhabitaciones")
        dormitorios = limpiar_y_convertir_a_numero(dorm_attr)

        # ───── “Nuevo proyecto” flag ───────────────────────────────
        badge = card.select_one("span.badge")
        es_nuevo = badge and "nuevo proyecto" in badge.get_text(strip=True).lower()

        # ───── enlace a la ficha ───────────────────────────────────
        link = card.select_one("a[href]")
        url_promo = link["href"] if link else LISTADO_URL

        # ————— FILTRO POR LOCALIZACIÓN (común a ambos casos) —————
        if not (ubic and any(l in ubic for l in LOCALIZACIONES_DESEADAS)):
            continue

        # ——— A) NUEVO PROYECTO ——————————————————————————————
        if es_nuevo:
            resultados.append(
                f"\n*{nombre} (Metrovacesa – Nuevo proyecto)*"
                f"\n📍 {ubic.title()}"
                f"\n🔗 [Ver promoción]({url_promo})"
            )
            continue

        # ——— B) EN COMERCIALIZACIÓN ————————————————­­———
        if dormitorios is None or dormitorios < HABITACIONES_MINIMAS:
            continue
        if precio is not None and precio > PRECIO_MAXIMO:
            continue

        resultados.append(
            f"\n*{nombre} (Metrovacesa)*"
            f"\n📍 {ubic.title()}"
            f"\n💶 Desde: {precio:,}€" if precio else ""
            f"\n🛏️ Dorms: {dormitorios}"
            f"\n🔗 [Ver promoción]({url_promo})".replace(",", ".")
        )

    print(f"[DEBUG] METROVACESA filtradas → {len(resultados)}", flush=True)
    return resultados