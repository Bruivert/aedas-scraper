# scrapers/aedas.py  · listado directo (sin saltar a la página de detalle)
# ────────────────────────────────────────────────────────────────────────
import re, requests
from bs4 import BeautifulSoup
from utils import (
    HEADERS, LOCALIZACIONES_DESEADAS, PRECIO_MAXIMO,
    HABITACIONES_MINIMAS, limpiar_y_convertir_a_numero
)

LISTING_URL = "https://www.aedashomes.com/viviendas-obra-nueva?province=2509951"

def scrape() -> list[str]:
    r = requests.get(LISTING_URL, headers=HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    cards = soup.select("a.card-promo.card")
    print(f"[DEBUG] AEDAS → {len(cards)} tarjetas en el listado", flush=True)

    resultados = []
    for card in cards:
        # ── título ───────────────────────────────────────────────────────
        title_tag = card.select_one("span.promo-title")
        nombre = title_tag.get_text(strip=True) if title_tag else None

        # ── ubicación y dormitorios ─────────────────────────────────────
        desc_items = card.select("ul.promo-description li")
        ubic = desc_items[0].get_text(strip=True).lower() if desc_items else None
        dorm_txt = desc_items[1].get_text(strip=True) if len(desc_items) > 1 else None

        # ── precio ──────────────────────────────────────────────────────
        price_tag = card.select_one("span.promo-price")
        precio = limpiar_y_convertir_a_numero(price_tag.get_text(strip=True) if price_tag else None)

        dormitorios = limpiar_y_convertir_a_numero(dorm_txt)

        # ── filtrado ────────────────────────────────────────────────────
        if all([nombre, ubic, precio, dormitorios]):
            if (any(l in ubic for l in LOCALIZACIONES_DESEADAS)
                    and precio <= PRECIO_MAXIMO
                    and dormitorios >= HABITACIONES_MINIMAS):
                url_promo = "https://www.aedashomes.com" + card["href"]
                resultados.append(
                    f"\n*{nombre} (AEDAS)*"
                    f"\n📍 {ubic.title()}"
                    f"\n💶 Desde: {precio:,}€"
                    f"\n🛏️ Dorms: {dormitorios}"
                    f"\n🔗 [Ver promoción]({url_promo})".replace(",", ".")
                )

    print(f"[DEBUG] AEDAS filtradas → {len(resultados)}", flush=True)
    return resultados