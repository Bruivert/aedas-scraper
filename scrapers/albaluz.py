# scrapers/albaluz.py
# ──────────────────────────────────────────────────────────────
"""
Scraper Albaluz (obra nueva en Valencia capital)

URL ya filtrada por localidad = Valencia:
https://www.albaluz.es/promociones-obra-nueva/?_localidad=valencia
Filtros aplicados:
    • localidad debe contener alguna LOCALIZACIONES_DESEADAS
    • precio  ≤  PRECIO_MAXIMO
    • dormitorios ≥ HABITACIONES_MINIMAS
Se descarta cualquier tarjeta si falta alguno de esos datos.
"""
import re, time, unicodedata, requests
from bs4 import BeautifulSoup
from utils import (
    HEADERS, LOCALIZACIONES_DESEADAS,
    PRECIO_MAXIMO, HABITACIONES_MINIMAS,
)

URL = "https://www.albaluz.es/promociones-obra-nueva/?_localidad=valencia"

NUM_RE = re.compile(r"\d[\d.,]*")

def _num(txt: str | None, pick_max=False) -> int | None:
    if not txt: return None
    nums = [int(n.replace(".", "").replace(",", "")) for n in NUM_RE.findall(txt)]
    if not nums:
        return None
    return max(nums) if pick_max else nums[0]

def _norm(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()

def scrape() -> list[str]:
    html = requests.get(URL, headers=HEADERS, timeout=30).text
    soup = BeautifulSoup(html, "html.parser")

    # Las tarjetas suelen estar en <div class="promo-item">; si cambian el
    # layout sólo ajusta este selector.
    cards = soup.select("div.promo-item, div.promocion, div.card")
    print(f"[DEBUG] ALBALUZ → {len(cards)} tarjetas totales", flush=True)

    resultados: list[str] = []
    for card in cards:
        # ── Nombre (titular) ─────────────────────────────────────
        name_tag = card.find(["h2", "h3"])
        nombre = name_tag.get_text(" ", strip=True) if name_tag else "SIN NOMBRE"

        # ── Ubicación ───────────────────────────────────────────
        loc_tag = card.find(string=re.compile("Valencia", re.I))
        ubic_raw = loc_tag.strip() if loc_tag else "Valencia"
        if not any(_norm(l) in _norm(ubic_raw) for l in LOCALIZACIONES_DESEADAS):
            continue

        # ── Dormitorios (máximo si hay rango “2-3 dorm.”) ───────
        dorm_tag = card.find(string=re.compile("dorm", re.I))
        dormitorios = _num(dorm_tag, pick_max=True)
        if dormitorios is None or dormitorios < HABITACIONES_MINIMAS:
            continue

        # ── Precio “Desde …” ───────────────────────────────────
        price_tag = card.find(string=re.compile("€"))
        precio = _num(price_tag)
        if precio is None or precio > PRECIO_MAXIMO:
            continue

        # ── Enlace ─────────────────────────────────────────────
        link = card.find_parent("a", href=True) or card.find("a", href=True)
        url_promo = link["href"] if link else URL

        # ── Construye bloque Markdown ──────────────────────────
        resultados.append(
            f"\n*{nombre} (Albaluz)*"
            f"\n📍 {ubic_raw.title()}"
            f"\n💶 Desde: {precio:,}€"
            f"\n🛏️ Dorms: {dormitorios}"
            f"\n🔗 [Ver promoción]({url_promo})".replace(",", ".")
        )
        time.sleep(0.15)   # pausa suave

    print(f"[DEBUG] ALBALUZ filtradas → {len(resultados)}", flush=True)
    return resultados