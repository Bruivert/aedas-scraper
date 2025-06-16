# scrapers/ficsa.py
# ───────────────────────────────────────────────────────────────
"""
Scraper FICSA robusto:
  1) Pide la primera página de resultados vía Ajax:
       https://www.ficsa.es/wp-admin/admin-ajax.php?action=more_post_ajax&paged=1
  2) Repite hasta que la respuesta HTML esté vacía.
  3) De cada bloque extrae:
       – Nombre  (class="tilter__title")
       – Localidad (class="tilter__description"), quitando HTML <br>
  4) Filtra solo por LOCALIZACIONES_DESEADAS (utils.py)
"""

import sys, unicodedata, re, time
import requests
from bs4 import BeautifulSoup
from utils import HEADERS, LOCALIZACIONES_DESEADAS

AJAX_URL = "https://www.ficsa.es/wp-admin/admin-ajax.php"
NUM_RE   = re.compile(r"\d+")

def _norm(t: str) -> str:
    return unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower().strip()

def _ajax_page(page: int) -> str:
    data = {"action": "more_post_ajax", "paged": page}
    r = requests.post(AJAX_URL, data=data, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text

def scrape() -> list[str]:
    page  = 1
    blocks = []
    try:
        while True:
            html = _ajax_page(page)
            if not html.strip():
                break
            blocks.append(html)
            page += 1
            time.sleep(0.5)          # pausa para no saturar
    except Exception as exc:
        print(f"⚠️  FICSA Ajax error → {exc}", file=sys.stderr)

    print(f"[DEBUG] FICSA Ajax pages → {len(blocks)}", flush=True)

    resultados = []
    for chunk in blocks:
        soup  = BeautifulSoup(chunk, "html.parser")
        cards = soup.select("div.tilter")
        for c in cards:
            nombre = (c.find("h3", class_="tilter__title") or "").get_text(" ", strip=True)
            desc   = (c.find("p", class_="tilter__description") or "").get_text(" ", strip=True)
            if not nombre or not desc:
                continue
            if not any(_norm(loc) in _norm(desc) for loc in LOCALIZACIONES_DESEADAS):
                continue
            a = c.find("a", href=True)
            url = (
                "https://www.ficsa.es" + a["href"]
                if (a and a["href"].startswith("/"))
                else (a["href"] if a else "https://www.ficsa.es/")
            )
            resultados.append(
                f"\n*{nombre} (FICSA)*"
                f"\n📍 {desc.title()}"
                f"\n🔗 [Ver promoción]({url})"
            )

    print(f"[DEBUG] FICSA filtradas → {len(resultados)}", flush=True)
    return resultados
