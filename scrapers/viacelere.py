# scrapers/viacelere.py  – versión corregida
# --------------------------------------------------------------
import re, requests
from bs4 import BeautifulSoup
from utils import (
    HEADERS, LOCALIZACIONES_DESEADAS, PRECIO_MAXIMO,
    HABITACIONES_MINIMAS, limpiar_y_convertir_a_numero
)

def scrape():
    url = "https://www.viacelere.com/promociones?provincia_id=46"
    res = requests.get(url, headers=HEADERS, timeout=30)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

    cards = soup.select("div.card-promocion")
    print(f"[DEBUG] VÍA CÉLERE → {len(cards)} tarjetas totales", flush=True)

    resultados = []
    for card in cards:
        # — título  (quitamos “Célere ”) —
        h2   = card.select_one("div.title h2")
        raw  = h2.get_text(" ", strip=True) if h2 else ""
        nombre = re.sub(r"^\s*C[eé]lere\s+", "", raw, flags=re.I).strip()

        # — enlace —
        a = card.find_parent("a")
        url_promo = a["href"] if (a and a.has_attr("href")) else "SIN URL"

        # — descripción —
        ubic, status, dorm_txt = None, None, None
        for p in card.select("div.desc p"):
            low = p.get_text(strip=True).lower()
            if "españa, valencia" in low:
                ubic = low
            elif "dormitorio" in low:
                dorm_txt = low
            elif "comercialización" in low or "próximamente" in low:
                status = p.get_text(strip=True)

        precio_tag = card.select_one("div.precio p.paragraph-size--2:last-child")
        precio_txt = precio_tag.get_text(strip=True) if precio_tag else None

        # — filtrado —
        if ubic and any(l in ubic for l in LOCALIZACIONES_DESEADAS):
            if status and "próximamente" in status.lower():
                resultados.append(
                    f"\n*{nombre} (Vía Célere ‒ Próximamente)*"
                    f"\n📍 {ubic.title()}\n🔗 [Ver promoción]({url_promo})"
                )
            elif status and "comercialización" in status.lower():
                precio = limpiar_y_convertir_a_numero(precio_txt)
                dorm   = limpiar_y_convertir_a_numero(dorm_txt)
                if (precio is not None and dorm is not None and
                    precio <= PRECIO_MAXIMO and dorm >= HABITACIONES_MINIMAS):
                    resultados.append(
                        f"\n*{nombre} (Vía Célere)*"
                        f"\n📍 {ubic.title()}"
                        f"\n💶 Desde: {precio:,}€"
                        f"\n🛏️ Dorms: {dorm}"
                        f"\n🔗 [Ver promoción]({url_promo})".replace(",", ".")
                    )
    print(f"[DEBUG] VÍA CÉLERE filtradas → {len(resultados)}", flush=True)
    return resultados