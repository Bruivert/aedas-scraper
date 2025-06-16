# scrapers/ficsa.py
# ───────────────────────────────────────────────────────────────
"""
Scraper FICSA (dos saltos)

1) Lista principal → https://www.ficsa.es/promociones/
   • recopila todos los enlaces /promociones/<slug>/
2) Ficha individual:
   • Nombre (h1 / h2)
   • Localización  (<p class="description"> …)
   • Precio mínimo (‘Desde XXX €’ dentro de <p class="value">)
   • Dormitorios   (mínimo antes de la palabra “dormitorio”)
3) Filtra:
   • ciudad ∈ utils.LOCALIZACIONES_DESEADAS
   • precio ≤ utils.PRECIO_MAXIMO  (si existe)
   • dorms  ≥ utils.HABITACIONES_MINIMAS (si existe)
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

# ───────────────────────────── helpers ─────────────────────────
def _norm(txt: str) -> str:
    return (
        unicodedata.normalize("NFKD", txt)
        .encode("ascii", "ignore")
        .decode()
        .lower()
    )

_ciudades = [re.escape(c) for c in LOCALIZACIONES_DESEADAS]
CIUDADES_RE = re.compile(r"\b(" + "|".join(_ciudades) + r")\b", re.I)

def _extract_price(soup: BeautifulSoup) -> int | None:
    """Devuelve el primer número después de ‘Desde’."""
    val_tag = soup.find("p", class_="value") or soup.find(string=re.compile(r"\bdesde\b", re.I))
    if val_tag:
        txt = val_tag.get_text() if hasattr(val_tag, "get_text") else val_tag
        num = re.search(r"\d[\d.]*", html.unescape(txt))
        if num:
            return int(num.group(0).replace(".", ""))
    return None

def _extract_location(soup: BeautifulSoup) -> str:
    """Texto de <p class="description"> o primeros 300 c. del documento."""
    loc_tag = soup.find("p", class_="description")
    texto = loc_tag.get_text(" ", strip=True) if loc_tag else soup.get_text(" ", strip=True)[:300]
    return re.sub(r"\s+", " ", texto).strip()

def _extract_dorms(soup: BeautifulSoup) -> int | None:
    dorm_txt = soup.find(string=re.compile(r"dormitorio", re.I))
    if dorm_txt:
        nums = [int(n) for n in re.findall(r"\d+", dorm_txt)]
        return min(nums) if nums else None
    return None

# ───────────────────────── paso A: enlaces ─────────────────────
def _get_promo_links() -> list[str]:
    resp = requests.get(LIST_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    links = []
    for a in soup.select("a[href*='/promociones/']"):
        href = a["href"]
        if href.endswith("/promociones/"):
            continue
        abs_url = href if href.startswith("http") else f"https://www.ficsa.es{href}"
        links.append(abs_url)
    return list(dict.fromkeys(links))

# ───────────────────────── paso B: ficha ───────────────────────
def _parse_promotion(url: str) -> dict | None:
    try:
        html_page = requests.get(url, headers=HEADERS, timeout=30).text
    except requests.RequestException:
        return None

    soup  = BeautifulSoup(html_page, "html.parser")
    h_tag = soup.find(["h1", "h2"])
    nombre = h_tag.get_text(" ", strip=True) if h_tag else None

    ubic   = _extract_location(soup)
    precio = _extract_price(soup)
    dorms  = _extract_dorms(soup)

    return {"nombre": nombre, "ubic": ubic, "precio": precio, "dorms": dorms, "url": url}

# ───────────────────────── scraper principal ───────────────────
def scrape() -> list[str]:
    enlaces = _get_promo_links()
    print(f"[DEBUG] FICSA enlaces → {len(enlaces)}", flush=True)

    mensajes: list[str] = []
    for link in enlaces:
        d = _parse_promotion(link)
        if not d or not d["nombre"]:
            continue

        # Filtros
        if not CIUDADES_RE.search(_norm(d["ubic"])):
            continue
        if d["precio"] and d["precio"] > PRECIO_MAXIMO:
            continue
        if d["dorms"] and d["dorms"] < HABITACIONES_MINIMAS:
            continue

        # Construir mensaje Markdown
        lineas = [
            f"*{d['nombre']} (FICSA)*",
            f"📍 {d['ubic'].title() if d['ubic'] else ''}",
        ]
        if d["precio"]:
            lineas.append(f"💶 Desde: {d['precio']:,}€".replace(",", "."))
        if d["dorms"]:
            lineas.append(f"🛏️ Dorms: {d['dorms']}")
        lineas.append(f"🔗 [Ver promoción]({d['url']})")

        mensajes.append("\n".join(lineas))
        time.sleep(0.2)

    print(f"[DEBUG] FICSA filtradas → {len(mensajes)}", flush=True)
    return mensajes
