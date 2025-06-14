# scrapers/urbania.py
# ────────────────────────────────────────────────────────────────
"""
Scraper Urbania (provincia de Valencia)

URL: https://urbania.es/proyectos/valencia/

• Nombre  →  <h2>
• Ubicación (municipio)  →  <h3>
• Dormitorios  →  p.carac (texto “Dormitorios: 3 o 4”)
• Precio  →  <strong>240.000 euros</strong>

Filtros
• Ubicación debe contener alguna LOCALIZACIONES_DESEADAS
• Si no hay precio/dorms  ⇒  se marca como “Próximamente” y se incluye
• Si hay datos:
     – dormitorios ≥ HABITACIONES_MINIMAS
     – precio ≤ PRECIO_MAXIMO
"""

import re, time
import requests
from bs4 import BeautifulSoup
from utils import (
    HEADERS,
    LOCALIZACIONES_DESEADAS,
    PRECIO_MAXIMO,
    HABITACIONES_MINIMAS,
    limpiar_y_convertir_a_numero,
)

LISTADO_URL = "https://urbania.es/proyectos/valencia/"


def scrape() -> list[str]:
    r = requests.get(LISTADO_URL, headers=HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    cards = soup.select("div.vivienda")
    print(f"[DEBUG] URBANIA → {len(cards)} tarjetas totales", flush=True)

    resultados = []

    for card in cards:
        # ── título / ubicación ──────────────────────────────────
        h2 = card.find("h2")
        nombre = h2.get_text(" ", strip=True) if h2 else "SIN NOMBRE"

        h3 = card.find("h3")
        ubic = h3.get_text(" ", strip=True).lower() if h3 else None
        if not (ubic and any(l in ubic for l in LOCALIZACIONES_DESEADAS)):
            continue

        # ── enlace ─────────────────────────────────────────────
        link = card.select_one("a.cont[href]")
        url_promo = link["href"] if link else LISTADO_URL

        # ── dormitorios ───────────────────────────────────────
        dorm_tag = card.find("p", class_=re.compile("carac"))
        dorm_txt = dorm_tag.get_text(strip=True) if dorm_tag else None
        dormitorios = limpiar_y_convertir_a_numero(dorm_txt)

        # ── precio ────────────────────────────────────────────
        strong = card.find("strong")
        precio = limpiar_y_convertir_a_numero(strong.get_text(strip=True) if strong else None)

        # ── determina si es “Próximamente” (sin datos) ────────
        es_prox = precio is None or dormitorios is None

        if es_prox:
            resultados.append(
                f"\n*{nombre} (Urbania – Próximamente)*"
                f"\n📍 {ubic.title()}"
                f"\n🔗 [Ver promoción]({url_promo})"
            )
        else:
            if dormitorios < HABITACIONES_MINIMAS:
                continue
            if precio > PRECIO_MAXIMO:
                continue
            resultados.append(
                f"\n*{nombre} (Urbania)*"
                f"\n📍 {ubic.title()}"
                f"\n💶 Desde: {precio:,}€"
                f"\n🛏️ Dorms: {dormitorios}"
                f"\n🔗 [Ver promoción]({url_promo})".replace(",", ".")
            )

        time.sleep(0.3)   # pausa suave

    print(f"[DEBUG] URBANIA filtradas → {len(resultados)}", flush=True)
    return resultados
