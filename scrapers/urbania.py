# scrapers/urbania.py
# ──────────────────────────────────────────────────────────────
"""
Scraper Urbania – solo promociones EN VENTA

Filtros:
    • localidad ∈ LOCALIZACIONES_DESEADAS
    • (precio ≤ PRECIO_MAXIMO 𝚘 ‘ÚLTIMAS UNIDADES’)
    • dormitorios ≥ HABITACIONES_MINIMAS
"""
import re, time, unicodedata, requests
from bs4 import BeautifulSoup
from utils import (
    HEADERS, LOCALIZACIONES_DESEADAS,
    PRECIO_MAXIMO, HABITACIONES_MINIMAS,
)

URL     = "https://urbania.es/proyectos/valencia/"
NUM_RE  = re.compile(r"\d[\d.,]*")

def _num(txt: str | None, pick_max=False) -> int | None:
    if not txt: return None
    nums = [int(n.replace(".", "").replace(",", "")) for n in NUM_RE.findall(txt)]
    return max(nums) if (pick_max and nums) else (nums[0] if nums else None)

def _norm(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()

def scrape() -> list[str]:
    html  = requests.get(URL, headers=HEADERS, timeout=30).text
    soup  = BeautifulSoup(html, "html.parser")
    cards = soup.select("div.vivienda div.row")
    print(f"[DEBUG] URBANIA → {len(cards)} tarjetas totales", flush=True)

    resultados = []

    for c in cards:
        # ── nombre y ubicación ─────────────────────────────────
        h2 = c.find("h2")
        nombre = h2.get_text(" ", strip=True) if h2 else "SIN NOMBRE"

        h3 = c.find("h3")
        ubic_raw = h3.get_text(" ", strip=True) if h3 else ""
        if not any(_norm(l) in _norm(ubic_raw) for l in LOCALIZACIONES_DESEADAS):
            continue

        # ── dormitorios (máx. de la línea) ─────────────────────
        dorm_tag = c.find("p", class_=re.compile("carac"))
        dormitorios = _num(dorm_tag.get_text(), pick_max=True) if dorm_tag else None
        if dormitorios is None or dormitorios < HABITACIONES_MINIMAS:
            continue

        # ── precio 𝚘 “últimas unidades” ───────────────────────
        strong = c.find("strong")
        ultimas = False
        precio  = None
        if strong:
            s_txt  = strong.get_text(" ", strip=True)
            ultimas = "ultima" in _norm(s_txt)
            if not ultimas:
                precio = _num(s_txt)

        # requiere precio válido o flag “últimas unidades”
        if not ultimas and (precio is None or precio > PRECIO_MAXIMO):
            continue

        # ── enlace ────────────────────────────────────────────
        link = c.find_parent("a", href=True)
        url  = link["href"] if link else URL

        # ── bloque markdown ───────────────────────────────────
        titulo = f"{nombre} (Urbania{' – Últimas unidades' if ultimas else ''})"
        linea_precio = "Últimas unidades" if ultimas else f"Desde: {precio:,}€"
        resultados.append(
            f"\n*{titulo}*"
            f"\n📍 {ubic_raw.title()}"
            f"\n💶 {linea_precio}"
            f"\n🛏️ Dorms: {dormitorios}"
            f"\n🔗 [Ver promoción]({url})".replace(",", ".")
        )
        time.sleep(0.15)

    print(f"[DEBUG] URBANIA filtradas → {len(resultados)}", flush=True)
    return resultados
