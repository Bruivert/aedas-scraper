# scrapers/urbania.py  – solo “en venta”, filtros corregidos
import re, time, unicodedata, requests
from bs4 import BeautifulSoup
from utils import (
    HEADERS, LOCALIZACIONES_DESEADAS,
    PRECIO_MAXIMO, HABITACIONES_MINIMAS,
)

URL = "https://urbania.es/proyectos/valencia/"

NUM_RE = re.compile(r"\d[\d.,]*")

def normalizar(texto: str) -> str:
    """Minúsculas sin tildes para comparar localidades."""
    txt = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return txt.lower()

def max_numero(texto: str | None) -> int | None:
    """Devuelve el número MÁS ALTO que aparezca (para '1, 2, 3 y 4')."""
    if not texto:
        return None
    numeros = [int(t.replace(".", "").replace(",", "")) for t in NUM_RE.findall(texto)]
    return max(numeros) if numeros else None

def scrape() -> list[str]:
    soup = BeautifulSoup(requests.get(URL, headers=HEADERS, timeout=30).text, "html.parser")
    cards = soup.select("div.vivienda div.row")
    print(f"[DEBUG] URBANIA → {len(cards)} tarjetas totales", flush=True)

    resultados = []
    for c in cards:
        nombre = (c.find("h2") or "").get_text(" ", strip=True)
        ubic_raw = (c.find("h3") or "").get_text(" ", strip=True)
        ubic = normalizar(ubic_raw)

        if not nombre or not any(normalizar(l) in ubic for l in LOCALIZACIONES_DESEADAS):
            continue

        dorm_txt = (c.find("p", class_=re.compile("carac")) or "").get_text()
        dormitorios = max_numero(dorm_txt)

        precio = max_numero((c.find("strong") or "").get_text())
        if None in (precio, dormitorios):
            continue            # descarta si falta algún dato
        if dormitorios < HABITACIONES_MINIMAS or precio > PRECIO_MAXIMO:
            continue

        link = c.find_parent("a", href=True)
        url  = link["href"] if link else URL

        resultados.append(
            f"\n*{nombre} (Urbania)*"
            f"\n📍 {ubic_raw.title()}"
            f"\n💶 Desde: {precio:,}€"
            f"\n🛏️ Dorms: {dormitorios}"
            f"\n🔗 [Ver promoción]({url})".replace(",", ".")
        )
        time.sleep(0.15)

    print(f"[DEBUG] URBANIA filtradas → {len(resultados)}", flush=True)
    return resultados