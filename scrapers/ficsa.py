# scrapers/ficsa.py
# ───────────────────────────────────────────────────────────────
"""
Scraper FICSA (dos saltos)
  1) https://www.ficsa.es/promociones/
     → recoge todos los enlaces /promociones/<slug>/
  2) entra en cada URL y extrae nombre, localización, precio 'Desde', dormitorios.
  3) filtra por LOCALIZACIONES_DESEADAS, PRECIO_MAXIMO, HABITACIONES_MINIMAS.
"""

from __future__ import annotations
import html, re, time, unicodedata, requests
from bs4 import BeautifulSoup
from utils import (
    HEADERS,
    LOCALIZACIONES_DESEADAS,
    PRECIO_MAXIMO,
    HABITACIONES_MINIMAS,
)

LIST_URL = "https://www.ficsa.es/promociones/"

# ───────────────────────────────────────── helpers ─────────────
def _norm(txt: str) -> str:
    return unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode().lower()

def _clean_html(raw: str) -> str:
    txt = html.unescape(raw)
    return re.sub(r"<[^>]+>", " ", txt)

def _extract_number(txt: str) -> int | None:
    m = re.search(r"\d[\d.]*", txt)
    return int(m.group(0).replace(".", "")) if m else None

# ───────────────────────────────────────── paso A ──────────────
def _get_promo_links() -> list[str]:
    soup = BeautifulSoup(requests.get(LIST_URL, headers=HEADERS, timeout=30).text, "html.parser")
    links = []
    for a in soup.select("a[href*='/promociones/']"):
        href = a["href"]
        if href.endswith("/promociones/"):
            continue  # la página de listado
        links.append(href if href.startswith("http") else f"https://www.ficsa.es{href}")
    return list(dict.fromkeys(links))  # quita duplicados

# ───────────────────────────────────────── paso B ──────────────
def _parse_promotion(url: str) -> dict | None:
    try:
        soup = BeautifulSoup(requests.get(url, headers=HEADERS, timeout=30).text, "html.parser")
    except requests.RequestException:
        return None

    # Nombre
    h = soup.find(["h1", "h2"])
    nombre = h.get_text(" ", strip=True) if h else None

    # Localización (primer texto con 'Valencia', 'Mislata', etc.)
    ubic = ""
    for tag in soup.find_all(text=re.compile(r"valenc", re.I)):
        ubic = tag.strip()
        if ubic:
            break

    # Precio mínimo
    price_txt = soup.find(text=re.compile(r"desde\s+\d", re.I))
    precio = _extract_number(price_txt) if price_txt else None

    # Dormitorios (mínimo mencionado)
    dorm_txt = soup.find(text=re.compile(r"dormitorio", re.I))
    dormitorios = None
    if dorm_txt:
        nums = [int(n) for n in re.findall(r"\d+", dorm_txt)]
        dormitorios = min(nums) if nums else None

    return {
        "nombre": nombre,
        "ubic": ubic,
        "precio": precio,
        "dorms": dormitorios,
        "url": url,
    }

# ───────────────────────────────────────── scraper ─────────────
def scrape() -> list[str]:
    mensajes = []
    enlaces = _get_promo_links()
    print(f"[DEBUG] FICSA lista → {len(enlaces)} enlaces", flush=True)

    for link in enlaces:
        datos = _parse_promotion(link)
        if not datos or not datos["nombre"]:
            continue

        # Filtro por localidad
        if not any(_norm(city) in _norm(datos["ubic"]) for city in LOCALIZACIONES_DESEADAS):
            continue
        # Filtro precio
        if datos["precio"] and datos["precio"] > PRECIO_MAXIMO:
            continue
        # Filtro dormitorios
        if datos["dorms"] and datos["dorms"] < HABITACIONES_MINIMAS:
            continue

        # Formatea Markdown
        detalle = []
        if datos["precio"]:
            detalle.append(f"💶 Desde: {datos['precio']:,}€".replace(",", "."))
        if datos["dorms"]:
            detalle.append(f"🛏️ Dorms: {datos['dorms']}")
        mensajes.append(
            f"\n*{datos['nombre']} (FICSA)*"
            f"\n📍 {datos['ubic'].title() if datos['ubic'] else ''}"
            f"\n" + (" - ".join(detalle) if detalle else "")
            f"\n🔗 [Ver promoción]({datos['url']})"
        )
        time.sleep(0.2)

    print(f"[DEBUG] FICSA filtradas → {len(mensajes)}", flush=True)
    return mensajes
