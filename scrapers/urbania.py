# scrapers/urbania.py
# ──────────────────────────────────────────────────────────────
"""
Scraper Urbania (provincia de Valencia)

• URL: https://urbania.es/proyectos/valencia/
• Saca:
    – Nombre  (h2)
    – Ubicación / municipio  (h3)
    – Dormitorios  (“Dormitorios: 2 y 3”)
    – Precio  (<strong>240.900€</strong>)
• Filtros:
    · Ubicación debe contener alguna LOCALIZACIONES_DESEADAS
    · Si falta precio o dormitorios → se considera “Próximamente”
    · Si hay ambos:
        – dormitorios ≥ HABITACIONES_MINIMAS
        – precio ≤ PRECIO_MAXIMO
"""
import re, time
import requests
from bs4 import BeautifulSoup
from utils import (
    HEADERS, LOCALIZACIONES_DESEADAS,
    PRECIO_MAXIMO, HABITACIONES_MINIMAS,
    limpiar_y_convertir_a_numero,
)

LISTADO_URL = "https://urbania.es/proyectos/valencia/"


def _numero_desde_texto(txt: str | None) -> int | None:
    """Devuelve el primer número entero del texto (quita . y ,)."""
    if not txt:
        return None
    m = re.search(r"\d[\d.,]*", txt)
    if not m:
        return None
    return int(m.group(0).replace(".", "").replace(",", ""))


def scrape() -> list[str]:
    html = requests.get(LISTADO_URL, headers=HEADERS, timeout=30).text
    soup = BeautifulSoup(html, "html.parser")

    cards = soup.select("div.vivienda div.row")
    print(f"[DEBUG] URBANIA → {len(cards)} tarjetas totales", flush=True)

    resultados: list[str] = []

    for c in cards:
        # ─── Nombre y ubicación ─────────────────────────────────
        h2_tag = c.find("h2")
        nombre = h2_tag.get_text(" ", strip=True) if h2_tag else "SIN NOMBRE"

        h3_tag = c.find("h3")
        ubic = h3_tag.get_text(" ", strip=True).lower() if h3_tag else None
        if not (ubic and any(l in ubic for l in LOCALIZACIONES_DESEADAS)):
            continue

        # ─── Enlace ────────────────────────────────────────────
        link = c.find_parent("a", href=True)
        url  = link["href"] if link else LISTADO_URL

        # ─── Dormitorios ───────────────────────────────────────
        dorm_tag = c.find("p", class_=re.compile("carac"))
        dormitorios = _numero_desde_texto(dorm_tag.get_text() if dorm_tag else None)

        # ─── Precio ────────────────────────────────────────────
        strong = c.find("strong")
        precio = _numero_desde_texto(strong.get_text() if strong else None)

        # ─── Lógica de filtrado ────────────────────────────────
        es_prox = precio is None or dormitorios is None

        if es_prox:
            resultados.append(
                f"\n*{nombre} (Urbania – Próximamente)*"
                f"\n📍 {ubic.title()}"
                f"\n🔗 [Ver promoción]({url})"
            )
            continue

        if dormitorios < HABITACIONES_MINIMAS or precio > PRECIO_MAXIMO:
            continue

        resultados.append(
            f"\n*{nombre} (Urbania)*"
            f"\n📍 {ubic.title()}"
            f"\n💶 Desde: {precio:,}€"
            f"\n🛏️ Dorms: {dormitorios}"
            f"\n🔗 [Ver promoción]({url})".replace(",", ".")
        )
        time.sleep(0.2)

    print(f"[DEBUG] URBANIA filtradas → {len(resultados)}", flush=True)
    return resultados
