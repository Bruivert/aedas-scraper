# scrapers/viacelere.py
# ─────────────────────────────────────────────────────────────────────────
"""
Scraper Vía Célere:
  • Lee el listado de promociones en venta (provincia de Valencia)
  • Lee el listado de promociones “Próximamente”
  • Filtra por LOCALIZACIONES_DESEADAS; aplica precio y dormitorios
    solo a las tarjetas en comercialización.
"""
import re
import requests
from bs4 import BeautifulSoup
from utils import (
    HEADERS,
    LOCALIZACIONES_DESEADAS,
    PRECIO_MAXIMO,
    HABITACIONES_MINIMAS,
    limpiar_y_convertir_a_numero,
)

LISTADO_URL = "https://www.viacelere.com/promociones?provincia_id=46"
PROX_URL    = "https://www.viacelere.com/promociones/proximamente"


# ───────────────────────── helpers ──────────────────────────
def _extraer_tarjetas(html: str) -> list[BeautifulSoup]:
    """Devuelve la lista de nodos <div class='card-promocion'> que haya en el HTML."""
    soup = BeautifulSoup(html, "html.parser")
    return soup.select("div.card-promocion")


def _procesar_tarjeta(card: BeautifulSoup, es_prox: bool) -> str | None:
    """
    Convierte una tarjeta en bloque Markdown si cumple los filtros.
    Devuelve None si debe descartarse.
    """
    # ─ título ──────────────────────────────────────────────
    h2_tag = card.select_one("h2.title-size-4") or card.select_one("h2")
    if not h2_tag:
        return None  # tarjeta con layout extraño → la saltamos

    raw = h2_tag.get_text(" ", strip=True)
    nombre = re.sub(r"^\s*C[eé]lere\s+", "", raw, flags=re.I).strip()

    # ─ enlace ──────────────────────────────────────────────
    link = card.find_parent("a") or card.select_one("a.button")
    url_promo = link["href"] if (link and link.has_attr("href")) else "SIN URL"

    # ─ ubicación, estado, dormitorios ─────────────────────
    ubic, estado, dorm_txt = None, None, None
    for p in card.select("div.desc p.paragraph-size--2"):
        low = p.get_text(strip=True).lower()
        if "españa" in low and "valencia" in low:
            ubic = low
        elif "dormitorio" in low:
            dorm_txt = low
        elif "comercialización" in low or "próximamente" in low:
            estado = p.get_text(strip=True)

    # Filtrado mínimo por ubicación
    if not (ubic and any(loc in ubic for loc in LOCALIZACIONES_DESEADAS)):
        return None

    # Si viene de /proximamente o el estado contiene “próxim…”
    if es_prox or (estado and "próxim" in estado.lower()):
        return (
            f"\n*{nombre} (Vía Célere ‒ Próximamente)*"
            f"\n📍 {ubic.title()}"
            f"\n🔗 [Ver promoción]({url_promo})"
        )

    # ─ precio + dormitorios (en comercialización) ──────────
    precio_tag = card.select_one("div.precio")
    precio_txt = precio_tag.get_text(strip=True) if precio_tag else None
    precio     = limpiar_y_convertir_a_numero(precio_txt)
    dormitorios = limpiar_y_convertir_a_numero(dorm_txt)

    if dormitorios is None or dormitorios < HABITACIONES_MINIMAS:
        return None
    if precio is not None and precio > PRECIO_MAXIMO:
        return None

    return (
        f"\n*{nombre} (Vía Célere)*"
        f"\n📍 {ubic.title()}"
        f"\n💶 Desde: {precio:,}€" if precio else ""
        f"\n🛏️ Dorms: {dormitorios}"
        f"\n🔗 [Ver promoción]({url_promo})".replace(",", ".")
    )


# ───────────────────────── entrypoint ───────────────────────
def scrape() -> list[str]:
    resultados: list[str] = []

    # 1 ▸ Listado en venta
    html = requests.get(LISTADO_URL, headers=HEADERS, timeout=30).text
    cards = _extraer_tarjetas(html)
    print(f"[DEBUG] VÍA CÉLERE (venta) → {len(cards)} tarjetas", flush=True)
    for c in cards:
        bloque = _procesar_tarjeta(c, es_prox=False)
        if bloque:
            resultados.append(bloque)

    # 2 ▸ Listado Próximamente
    html = requests.get(PROX_URL, headers=HEADERS, timeout=30).text
    cards = _extraer_tarjetas(html)
    print(f"[DEBUG] VÍA CÉLERE (próx.) → {len(cards)} tarjetas", flush=True)
    for c in cards:
        bloque = _procesar_tarjeta(c, es_prox=True)
        if bloque:
            resultados.append(bloque)

    print(f"[DEBUG] VÍA CÉLERE filtradas → {len(resultados)}", flush=True)
    return resultados