# scrapers/viacelere.py
# ─────────────────────────────────────────────────────────────────────────
import re, requests
from bs4 import BeautifulSoup
from utils import (
    HEADERS, LOCALIZACIONES_DESEADAS, HABITACIONES_MINIMAS,
    PRECIO_MAXIMO, limpiar_y_convertir_a_numero
)

LISTADO_URL      = "https://www.viacelere.com/promociones?provincia_id=46"
PROXIMAMENTE_URL = "https://www.viacelere.com/promociones/proximamente"

# ─────────────────────────────────────────────────────────────────────────
def _extraer_tarjetas(html: str) -> list[BeautifulSoup]:
    """Devuelve la lista de nodos <div class='card-promocion'> que haya en el HTML."""
    soup = BeautifulSoup(html, "html.parser")
    return soup.select("div.card-promocion")


def _procesar_tarjeta(card: BeautifulSoup, es_proximamente: bool) -> str | None:
    """Parsea una tarjeta y devuelve el bloque Markdown si pasa los filtros."""
    # — título —
    raw  = card.select_one("h2.title-size-4").get_text(" ", strip=True)
    nombre = re.sub(r"^\s*C[eé]lere\s+", "", raw, flags=re.I).strip()

    # — enlace —
    link = card.find_parent("a") or card.select_one("a.button")
    url  = link["href"] if (link and link.has_attr("href")) else "SIN URL"

    # — ubicación, estado, dormitorios —
    ubic, dorm_txt = None, None
    estado_txt     = "Próximamente" if es_proximamente else None

    for p in card.select("div.desc p.paragraph-size--2"):
        txt_low = p.get_text(strip=True).lower()
        if "españa" in txt_low:
            ubic = txt_low
        elif "dormitorio" in txt_low:
            dorm_txt = txt_low
        elif "comercialización" in txt_low or "próximamente" in txt_low:
            estado_txt = p.get_text(strip=True)

    # Filtrado por ubicación
    if not (ubic and any(loc in ubic for loc in LOCALIZACIONES_DESEADAS)):
        return None

    # Si es “Próximamente”, no exigimos precio ni dormitorios
    if "próximamente" in (estado_txt or "").lower():
        return (
            f"\n*{nombre} (Vía Célere – Próximamente)*"
            f"\n📍 {ubic.title()}"
            f"\n🔗 [Ver promoción]({url})"
        )

    # — precio + dormitorios (estado = En comercialización) —
    precio_tag = card.select_one("div.precio")
    precio_txt = precio_tag.get_text(strip=True) if precio_tag else None
    precio     = limpiar_y_convertir_a_numero(precio_txt)
    dorms      = limpiar_y_convertir_a_numero(dorm_txt)

    if dorms is None or dorms < HABITACIONES_MINIMAS:
        return None
    if precio is not None and precio > PRECIO_MAXIMO:
        return None

    return (
        f"\n*{nombre} (Vía Célere)*"
        f"\n📍 {ubic.title()}"
        f"\n💶 Desde: {precio:,}€" if precio else ""
        f"\n🛏️ Dorms: {dorms}"
        f"\n🔗 [Ver promoción]({url})".replace(",", ".")
    )


def scrape() -> list[str]:
    resultados: list[str] = []

    # 1 ▸ Listado normal (comercialización)
    html = requests.get(LISTADO_URL, headers=HEADERS, timeout=30).text
    cards = _extraer_tarjetas(html)
    print(f"[DEBUG] VÍA CÉLERE (venta) → {len(cards)} tarjetas", flush=True)

    for card in cards:
        bloque = _procesar_tarjeta(card, es_proximamente=False)
        if bloque:
            resultados.append(bloque)

    # 2 ▸ Listado “Próximamente”
    html = requests.get(PROXIMAMENTE_URL, headers=HEADERS, timeout=30).text
    cards = _extraer_tarjetas(html)
    print(f"[DEBUG] VÍA CÉLERE (próx.) → {len(cards)} tarjetas", flush=True)

    for card in cards:
        bloque = _procesar_tarjeta(card, es_proximamente=True)
        if bloque:
            resultados.append(bloque)

    print(f"[DEBUG] VÍA CÉLERE filtradas → {len(resultados)}", flush=True)
    return resultados