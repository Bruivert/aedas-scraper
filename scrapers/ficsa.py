# scrapers/ficsa.py
# ───────────────────────────────────────────────────────────────
"""
Scraper FICSA
1) Recorre https://www.ficsa.es/promociones/ y recoge enlaces /promociones/<slug>/
2) Para cada ficha extrae nombre, localización, precio mínimo («Desde»), dormitorios.
3) Filtra por LOCALIZACIONES_DESEADAS, PRECIO_MAXIMO, HABITACIONES_MINIMAS.
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
            continue
        links.append(href if href.startswith("http") else f"https://www.ficsa.es{href}")
    return list(dict.fromkeys(links))

# ───────────────────────────────────────── paso B ──────────────
def _parse_promotion(url: str) -> dict | None:
    try:
        soup = BeautifulSoup(requests.get(url, headers=HEADERS, timeout=30).text, "html.parser")
    except requests.RequestException:
        return None

    h = soup.find(["h1", "h2"])
    nombre = h.get_text(" ", strip=True) if h else None

    ubic = ""
    for tag in soup.find_all(text=re.compile(r"valenc|mislata|poblet|paterna|manises", re.I)):
        ubic = tag.strip()
        if ubic:
            break

    price_tag = soup.find(text=re.compile(r"desde\s+\d", re.I))
    precio = _extract_number(price_tag) if price_tag else None

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

        if not any(_norm(c) in _norm(datos["ubic"]) for c in LOCALIZACIONES_DESEADAS):
            continue
        if datos["precio"] and datos["precio"] > PRECIO_MAXIMO:
            continue
        if datos["dorms"] and datos["dorms"] < HABITACIONES_MINIMAS:
            continue

        # ---------- construir mensaje sin errores de sintaxis ----------
        detalle = []
        if datos["precio"]:
            detalle.append(f"💶 Desde: {datos['precio']:,}€".replace(",", "."))
        if datos["dorms"]:
            detalle.append(f"🛏️ Dorms: {datos['dorms']}")
        detalle_line = " - ".join(detalle) if detalle else ""

        msg = (
            f"\n*{datos['nombre']} (FICSA)*"
            f"\n📍 {datos['ubic'].title() if datos['ubic'] else ''}"
            + (f"\n{detalle_line}" if detalle_line else "")
            f"\n🔗 [Ver promoción]({datos['url']})"
        )
        mensajes.append(msg)
        time.sleep(0.2)

    print(f"[DEBUG] FICSA filtradas → {len(mensajes)}", flush=True)
    return mensajes
