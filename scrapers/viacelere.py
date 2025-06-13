# scrapers/aedas.py  – listado + bloque “Próximamente”
# ─────────────────────────────────────────────────────────────────────
import re, requests
from bs4 import BeautifulSoup
from utils import (
    HEADERS, LOCALIZACIONES_DESEADAS, PRECIO_MAXIMO,
    HABITACIONES_MINIMAS, limpiar_y_convertir_a_numero
)

LISTING_URL = "https://www.aedashomes.com/viviendas-obra-nueva?province=2509951"

def scrape() -> list[str]:
    res = requests.get(LISTING_URL, headers=HEADERS, timeout=30)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

    cards = soup.select("a.card-promo.card")
    print(f"[DEBUG] AEDAS → {len(cards)} tarjetas en el listado", flush=True)

    resultados = []

    for card in cards:
        # ── título ───────────────────────────────────────────────
        title_tag = card.select_one("span.promo-title")
        nombre = title_tag.get_text(strip=True) if title_tag else None

        # ── descripción (ubicación, habs, “Próximamente”…) ───────
        desc_items = [li.get_text(strip=True) for li in card.select("ul.promo-description li")]
        ubic        = next((d.lower() for d in desc_items if "," in d), None)
        dorm_txt    = next((d       for d in desc_items if "dormitorio"  in d.lower()), None)
        soon_txt    = next((d       for d in desc_items if "próxim"      in d.lower()), None)

        # ── precio ───────────────────────────────────────────────
        price_tag = card.select_one("span.promo-price")
        precio = limpiar_y_convertir_a_numero(price_tag.get_text(strip=True) if price_tag else None)

        dormitorios = limpiar_y_convertir_a_numero(dorm_txt)

        # ─┤  1. BLOQUE “PRÓXIMAMENTE” (ignora precio y habs) ├────
        if soon_txt and ubic and any(l in ubic for l in LOCALIZACIONES_DESEADAS):
            url_promo = "https://www.aedashomes.com" + card["href"]
            resultados.append(
                f"\n*{nombre} (AEDAS ‒ Próximamente)*"
                f"\n📍 {ubic.title()}"
                f"\n🔗 [Ver promoción]({url_promo})"
            )
            continue   # pasamos a la siguiente tarjeta

        # ─┤  2. BLOQUE NORMAL (con precio y dorm. mínimos) ├──────
        if all([ubic, precio, dormitorios]):
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