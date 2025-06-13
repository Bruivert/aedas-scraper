# -*- coding: utf-8 -*-
import requests, re
from bs4 import BeautifulSoup
from utils import (
    HEADERS, LOCALIZACIONES_DESEADAS, PRECIO_MAXIMO,
    HABITACIONES_MINIMAS, limpiar_y_convertir_a_numero
)

def scrape():
    """Devuelve una lista de strings Markdown con las promos filtradas."""
    url = "https://www.aedashomes.com/viviendas-obra-nueva?province=2509951"
    res = requests.get(url, headers=HEADERS, timeout=30)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

    resultados = []
    for card in soup.select("a[data-testid='development-card']"):
        titulo = card.select_one(".development-card__title")
        precio = card.select_one(".development-card__price")
        ubic   = card.select_one(".development-card__location")
        hab_txt = card.find(string=lambda t: "dorm" in t.lower())

        # normaliza
        nombre = titulo.get_text(strip=True) if titulo else None
        precio = limpiar_y_convertir_a_numero(precio.get_text(strip=True)) if precio else None
        ubic   = ubic.get_text(strip=True).lower() if ubic else None
        habs   = limpiar_y_convertir_a_numero(hab_txt)

        if all([nombre, precio, ubic, habs]):
            if (any(l in ubic for l in LOCALIZACIONES_DESEADAS)
                    and precio <= PRECIO_MAXIMO
                    and habs >= HABITACIONES_MINIMAS):
                url_promo = "https://www.aedashomes.com" + card["href"]
                resultados.append(
                    f"\n*{nombre} (AEDAS)*"
                    f"\n📍 {ubic.title()}"
                    f"\n💶 Desde: {precio:,}€"
                    f"\n🛏️ Dorms: {habs}"
                    f"\n🔗 [Ver promoción]({url_promo})".replace(",", ".")
                )
    return resultados