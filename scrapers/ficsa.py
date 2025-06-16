from __future__ import annotations
import re, sys, time, unicodedata, requests
from bs4 import BeautifulSoup
from utils import HEADERS, LOCALIZACIONES_DESEADAS

LIST_URL = "https://www.ficsa.es/promociones-valencia"
AJAX_URL = "https://www.ficsa.es/wp-admin/admin-ajax.php"

def _norm(txt: str) -> str:
    return unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode().lower().strip()

def _get_nonce() -> str | None:
    """Descarga la página principal y devuelve el data-nonce del botón 'Ver más'."""
    html = requests.get(LIST_URL, headers=HEADERS, timeout=30).text
    m = re.search(r'id="more_posts_ajax"[^>]*data-nonce="([^"]+)"', html)
    return m.group(1) if m else None

def _ajax_page(page: int, nonce: str) -> str:
    payload = {"action": "more_post_ajax", "paged": str(page), "nonce": nonce}
    hdrs = {**HEADERS,
            "Referer": LIST_URL,
            "X-Requested-With": "XMLHttpRequest"}
    r = requests.post(AJAX_URL, data=payload, headers=hdrs, timeout=30)
    r.raise_for_status()
    return r.text

def scrape() -> list[str]:
    nonce = _get_nonce()
    if not nonce:
        print("⚠️  FICSA: no se encontró nonce; aborto", file=sys.stderr)
        return []

    bloques, page = [], 1
    while True:
        chunk = _ajax_page(page, nonce)
        if not chunk.strip():
            break
        bloques.append(chunk)
        page += 1
        time.sleep(0.4)

    print(f"[DEBUG] FICSA Ajax pages → {len(bloques)}", flush=True)

    resultados: list[str] = []
    for html in bloques:
        soup = BeautifulSoup(html, "html.parser")
        for card in soup.select("div.tilter"):
            nombre = (card.find("h3", class_="tilter__title") or "").get_text(" ", strip=True)
            ubic   = (card.find("p", class_="tilter__description") or "").get_text(" ", strip=True)
            if not nombre or not ubic:
                continue
            if not any(_norm(l) in _norm(ubic) for l in LOCALIZACIONES_DESEADAS):
                continue
            a = card.find("a", href=True)
            url = ("https://www.ficsa.es"+a["href"]) if a and a["href"].startswith("/") else (a["href"] if a else LIST_URL)
            resultados.append(
                f"\n*{nombre} (FICSA)*"
                f"\n📍 {ubic.title()}"
                f"\n🔗 [Ver promoción]({url})"
            )
            time.sleep(0.1)

    print(f"[DEBUG] FICSA filtradas → {len(resultados)}", flush=True)
    return resultados