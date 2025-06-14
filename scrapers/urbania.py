# scrapers/urbania.py
# ──────────────────────────────────────────────────────────────
"""
Scraper Urbania – sólo promociones EN VENTA (no “Próximamente”)
Filtros: localidad ∈ LOCALIZACIONES_DESEADAS, precio ≤ PRECIO_MAXIMO,
         dormitorios ≥ HABITACIONES_MINIMAS
"""
import re, time, unicodedata, requests
from bs4 import BeautifulSoup
from utils import (
    HEADERS, LOCALIZACIONES_DESEADAS,
    PRECIO_MAXIMO, HABITACIONES_MINIMAS,
)

URL = "https://urbania.es/proyectos/valencia/"
NUM_RE = re.compile(r"\d[\d.,]*")

def _num(txt: str | None, pick_max=False) -> int | None:
    """Devuelve el primer número del texto; si pick_max=True el mayor."""
    if not txt:
        return None
    nums = [int(n.replace(".", "").replace(",", "")) for n in NUM_RE.findall(txt)]
    if not nums:
        return None
    return max(nums) if pick_max else nums[0]

def _norm(s: str) -> str:
    """Minúsculas sin acentos para comparación."""
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()

def scrape() -> list[str]:
    html = requests.get(URL, headers=HEADERS, timeout=30).text
    soup = BeautifulSoup(html, "html.parser")

    cards = soup.select("div.vivienda div.row")
    print(f"[DEBUG] URBANIA → {len(cards)} tarjetas totales", flush=True)

    resultados = []
    for c in cards:
        # Nombre y ubicación
        nombre = (c.find("h2") or "").get_text(" ", strip=True)
        h3_tag = c.find("h3")
        ubic_raw = h3_tag.get_text(" ", strip=True) if h3_tag else ""
        ubic_ok  = any(_norm(l) in _norm(ubic_raw) for l in LOCALIZACIONES_DESEADAS)
        if not (nombre and ubic_ok):
            continue

        # Dormitorios (máximo de la línea)
        dorm_tag = c.find("p", class_=re.compile("carac"))
        dormitorios = _num(dorm_tag.get_text(), pick_max=True) if dorm_tag else None
        if dormitorios is None or dormitorios < HABITACIONES_MINIMAS:
            continue

        # Precio
        precio = _num((c.find("strong") or "").get_text())
        if precio is None or precio > PRECIO_MAXIMO:
            continue

        # Enlace
        link  = c.find_parent("a", href=True)
        url_promo = link["href"] if link else URL

        resultados.append(
            f"\n*{nombre} (Urbania)*"
            f"\n📍 {ubic_raw.title()}"
            f"\n💶 Desde: {precio:,}€"
            f"\n🛏️ Dorms: {dormitorios}"
            f"\n🔗 [Ver promoción]({url_promo})".replace(",", ".")
        )
        time.sleep(0.15)

    print(f"[DEBUG] URBANIA filtradas → {len(resultados)}", flush=True)
    return resultados