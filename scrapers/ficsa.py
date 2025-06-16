# scrapers/ficsa.py
# ───────────────────────────────────────────────────────────────
"""
Scraper FICSA

1) Visita https://www.ficsa.es/promociones/
   → recoge todos los enlaces que apuntan a /promociones/<slug>/
2) Entra en cada ficha, extrae:
     • Nombre (h1 / h2)
     • Localización (primer texto que contenga “València”, “Mislata”…)
     • Precio mínimo (primer “Desde XXX €”)
     • Dormitorios (mínimo número citado antes de “dormitori…”)
3) Filtra:
     • localidad ∈ LOCALIZACIONES_DESEADAS
     • precio ≤ PRECIO_MAXIMO  (si existe)
     • dormitorios ≥ HABITACIONES_MINIMAS (si existe)
4) Devuelve bloques Markdown listos para Telegram.
"""

from __future__ import annotations
import html
import re
import time
import unicodedata
import requests
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
    return (
        unicodedata.normalize("NFKD", txt)
        .encode("ascii", "ignore")
        .decode()
        .lower()
    )

def _clean_html(raw: str) -> str:
    txt = html.unescape(raw)
    return re.sub(r"<[^>]+>", " ", txt)

def _extract_number(txt: str) -> int | None:
    m = re.search(r"\d[\d.]*", txt)
    return int(m.group(0).replace(".", "")) if m else None

# ───────────────────────────────────────── paso A ──────────────
def _get_promo_links() -> list[str]:
    soup = BeautifulSoup(
        requests.get(LIST_URL, headers=HEADERS, timeout=30).text, "html.parser"
    )
    links: list[str] = []
    for a in soup.select("a[href*='/promociones/']"):
        href = a["href"]
        if href.endswith("/promociones/"):
            continue  # descarta el propio listado
        abs_url = href if href.startswith("http") else f"https://www.ficsa.es{href}"
        links.append(abs_url)
    return list(dict.fromkeys(links))  # quita duplicados

# ───────────────────────────────────────── paso B ──────────────
def _parse_promotion(url: str) -> dict | None:
    try:
        html_page = requests.get(url, headers=HEADERS, timeout=30).text
    except requests.RequestException:
        return None

    soup = BeautifulSoup(html_page, "html.parser")

    # Nombre
    h = soup.find(["h1", "h2"])
    nombre = h.get_text(" ", strip=True) if h else None

    # Localización: primer texto que contenga alguna ciudad valenciana
    ubic = ""
    for tag in soup.find_all(string=True):
        txt = tag.strip()
        if any(city in _norm(txt) for city in ["valenc", "mislata", "poblet", "paterna", "manises"]):
            ubic = txt
            break

    # Precio “Desde”
    price_tag = soup.find(string=re.compile(r"desde\s+\d", re.I))
    precio = _extract_number(price_tag) if price_tag else None

    # Dormitorios: mínimo citado
    dorm_txt = soup.find(string=re.compile(r"dormitorio", re.I))
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
    enlaces = _get_promo_links()
    print(f"[DEBUG] FICSA lista → {len(enlaces)} enlaces", flush=True)

    mensajes: list[str] = []
    for link in enlaces:
        datos = _parse_promotion(link)
        if not datos or not datos["nombre"]:
            continue

        # 1. Localidad
        if not any(_norm(ciudad) in _norm(datos["ubic"]) for ciudad in LOCALIZACIONES_DESEADAS):
            continue
        # 2. Precio
        if datos["precio"] and datos["precio"] > PRECIO_MAXIMO:
            continue
        # 3. Dormitorios
        if datos["dorms"] and datos["dorms"] < HABITACIONES_MINIMAS:
            continue

        # ---------- construir mensaje Markdown ----------
        detalle = []
        if datos["precio"]:
            detalle.append(f"💶 Desde: {datos['precio']:,}€".replace(",", "."))
        if datos["dorms"]:
            detalle.append(f"🛏️ Dorms: {datos['dorms']}")
        detalle_line = " - ".join(detalle) if detalle else ""

        msg = (
            f"\n*{datos['nombre']} (FICSA)*"
            f"\n📍 {datos['ubic'].title() if datos['ubic'] else ''}"
            f"{f'\n{detalle_line}' if detalle_line else ''}"
            f"\n🔗 [Ver promoción]({datos['url']})"
        )
        mensajes.append(msg)
        time.sleep(0.2)

    print(f"[DEBUG] FICSA filtradas → {len(mensajes)}", flush=True)
    return mensajes
