# scrapers/urbania.py
# ──────────────────────────────────────────────────────────────
import re, time
import requests
from bs4 import BeautifulSoup
from utils import (
    HEADERS, LOCALIZACIONES_DESEADAS,
    PRECIO_MAXIMO, HABITACIONES_MINIMAS,
    limpiar_y_convertir_a_numero,
)

LISTADO_URL = "https://urbania.es/proyectos/valencia/"

def _numero_desde_texto(txt: str) -> int | None:
    """Devuelve el primer número del texto (quita . y ,)."""
    if not txt:
        return None
    m = re.search(r"\d[\d.,]*", txt)
    if not m:
        return None
    return int(m.group(0).replace(".", "").replace(",", ""))

def scrape() -> list[str]:
    html = requests.get(LISTADO_URL, headers=HEADERS, timeout=30).text
    soup = BeautifulSoup(html, "html.parser")

    cards = soup.select("div.vivienda div.row")   # cada ficha tiene este div.row
    print(f"[DEBUG] URBANIA → {len(cards)} tarjetas totales", flush=True)

    resultados = []
    for c in cards:
        # ─ Nombre y ubicación ────────────────────────────────────
        nombre = (c.find("h2") or "").get_text(" ", strip=True)
        ubic   = (c.find("h3") or "").get_text(" ", strip=True).lower()

        if not (nombre and ubic and any(l in ubic for l in LOCALIZACIONES_DESEADAS)):
            continue

        # ─ Dormitorios ───────────────────────────────────────────
        dorm_txt = c.find("p", class_=re.compile("carac"))
        dormitorios = _numero_desde_texto(dorm_txt.get_text()) if dorm_txt else None

        # ─ Precio ───────────────────────────────────────────────
        strong = c.find("strong")
        precio = _numero_desde_texto(strong.get_text()) if strong else None

        # ─ Enlace ───────────────────────────────────────────────
        link = c.find_parent("a", href=True)
        url  = link["href"] if link else LISTADO_URL

        # ─ Lógica de filtrado ───────────────────────────────────
        if precio is None or dormitorios is None:
            # Trata como “Próximamente” sólo si realmente faltan datos
            resultados.append(
                f"\n*{nombre} (Urbania – Próximamente)*"
                f"\n📍 {ubic.title()}"
                f"\n🔗 [Ver promoción]({url})"
            )
            continue

        if precio > PRECIO_MAXIMO or dormitorios < HABITACIONES_MINIMAS:
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
