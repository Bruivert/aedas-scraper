# scrapers/aedas.py
import re, requests
from bs4 import BeautifulSoup
from utils import (
    HEADERS, LOCALIZACIONES_DESEADAS, PRECIO_MAXIMO,
    HABITACIONES_MINIMAS, limpiar_y_convertir_a_numero
)

def scrape():
    url = "https://www.aedashomes.com/viviendas-obra-nueva?province=2509951"
    res = requests.get(url, headers=HEADERS, timeout=30)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

    # 🔎 nuevo selector: cada desarrollo va en <li class="card_item">
    cards = soup.select("li.card_item")
    print(f"[DEBUG] AEDAS → {len(cards)} tarjetas totales", flush=True)

    resultados = []
    for card in cards:
        # título = texto del <h3>
        h3 = card.find("h3")
        nombre = h3.get_text(strip=True) if h3 else None

        # ubicación = <span class="localidad">
        loc = card.select_one("span.localidad")
        ubic = loc.get_text(strip=True).lower() if loc else None

        # dormitorios = texto que contenga “bedroom”
        hab_tag = card.find(string=re.compile("bedroom", re.I))
        habs = limpiar_y_convertir_a_numero(hab_tag)

        # precio = “From 234.000 €”
        prec_tag = card.find(string=re.compile("€"))
        precio = limpiar_y_convertir_a_numero(prec_tag)

        if all([nombre, ubic, habs, precio]):
            if (any(l in ubic for l in LOCALIZACIONES_DESEADAS) and
                precio <= PRECIO_MAXIMO and
                habs >= HABITACIONES_MINIMAS):
                url_promo = card.find("a")["href"]
                resultados.append(
                    f"\n*{nombre} (AEDAS)*"
                    f"\n📍 {ubic.title()}"
                    f"\n💶 Desde: {precio:,}€"
                    f"\n🛏️ Dorms: {habs}"
                    f"\n🔗 [Ver promoción](https://www.aedashomes.com{url_promo})".replace(",", ".")
                )
    return resultados