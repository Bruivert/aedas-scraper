# scrapers/viacelere.py  – versión 100 % adaptada al markup actual
# ───────────────────────────────────────────────────────────────────
import re, requests
from bs4 import BeautifulSoup
from utils import (
    HEADERS, LOCALIZACIONES_DESEADAS, PRECIO_MAXIMO,
    HABITACIONES_MINIMAS, limpiar_y_convertir_a_numero
)

URL_LISTADO = "https://www.viacelere.com/promociones?provincia_id=46"

def scrape() -> list[str]:
    res = requests.get(URL_LISTADO, headers=HEADERS, timeout=30)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

    cards = soup.select("div.card-promocion")
    print(f"[DEBUG] VÍA CÉLERE → {len(cards)} tarjetas totales", flush=True)

    resultados: list[str] = []

    for card in cards:
        # ── título (quitamos “Célere ”) ────────────────────────────────
        h2   = card.select_one("h2.title-size-4")
        raw  = h2.get_text(" ", strip=True) if h2 else ""
        nombre = re.sub(r"^\s*C[eé]lere\s+", "", raw, flags=re.I).strip()

        # ── enlace a la ficha ─────────────────────────────────────────
        link = card.find_parent("a") or card.select_one("a.button")
        url_promo = link["href"] if (link and link.has_attr("href")) else "SIN URL"

        # ── descripción: ubicación, estado y dormitorios ─────────────
        ubic, status, dorm_txt = None, None, None
        for p in card.select("div.desc p.paragraph-size--2"):
            low = p.get_text(strip=True).lower()
            if "españa, valencia" in low:
                ubic = low
            elif "dormitorio" in low:
                dorm_txt = low
            elif "comercialización" in low or "próximamente" in low:
                status = p.get_text(strip=True)

        # ── precio (si existe) ────────────────────────────────────────
        precio_tag = card.select_one("div.precio")
        precio_txt = precio_tag.get_text(strip=True) if precio_tag else None
        precio     = limpiar_y_convertir_a_numero(precio_txt)

        dormitorios = limpiar_y_convertir_a_numero(dorm_txt)

        # ── filtro de ubicación (imprescindible) ─────────────────────
        if not (ubic and any(l in ubic for l in LOCALIZACIONES_DESEADAS)):
            continue

        # ── lógica por estado ────────────────────────────────────────
        if status and "próximamente" in status.lower():
            resultados.append(
                f"\n*{nombre} (Vía Célere ‒ Próximamente)*"
                f"\n📍 {ubic.title()}"
                f"\n🛏️ {dormitorios or '—'} dormitorios"
                f"\n🔗 [Ver promoción]({url_promo})"
            )

        elif status and "comercialización" in status.lower():
            # precio puede faltar; solo se filtra si existe
            if (dormitorios is not None and dormitorios >= HABITACIONES_MINIMAS
                    and (precio is None or precio <= PRECIO_MAXIMO)):
                resultados.append(
                    f"\n*{nombre} (Vía Célere)*"
                    f"\n📍 {ubic.title()}"
                    f"\n💶 Desde: {precio:,}€" if precio else ""
                    f"\n🛏️ Dorms: {dormitorios}"
                    f"\n🔗 [Ver promoción]({url_promo})".replace(",", ".")
                )

    print(f"[DEBUG] VÍA CÉLERE filtradas → {len(resultados)}", flush=True)
    return resultados