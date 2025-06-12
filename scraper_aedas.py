from requests_html import HTMLSession
from urllib.parse import urljoin
import csv, json, time, os, requests, textwrap
from typing import List, Dict

BASE = "https://www.aedashomes.com"
LIST_URL = f"{BASE}/viviendas-obra-nueva"

CITY_MAP = {
    "2599951": "Quart de Poblet",
    "2599943": "Valencia",
    "2599950": "Mislata",
    "2599953": "Paterna",
    "2599956": "Torrent",
    "2599945": "Manises",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

def fetch_page(session: HTMLSession, url: str):
    r = session.get(url, headers=HEADERS, timeout=30)
    r.html.render(timeout=30, sleep=1)
    return r

def extract_cards(page) -> List[Dict[str, str]]:
    cards = []
    for a in page.html.find('a.card-promo.card'):
        title = a.attrs.get("title", "").replace("Ir a promoción", "").strip()
        href = a.attrs.get("href", "")
        url = urljoin(BASE, href)
        city_id = ""
        if "city=" in href:
            city_id = href.split("city=")[-1].split("&")[0].strip()
        location = CITY_MAP.get(city_id, "Desconocido")
        cards.append({
            "title": title,
            "url": url,
            "location": location,
            "price_from": "—",
        })
    return cards

def scrape_all() -> List[Dict[str, str]]:
    session = HTMLSession()
    first = fetch_page(session, LIST_URL)
    cards = extract_cards(first)
    session.close()
    return cards

def save_csv(rows: List[Dict[str, str]], path="promociones_aedas.csv"):
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)

def notify_telegram(file_path: str, total: int):
    token = os.environ.get("TG_BOT_TOKEN")
    chat_id = os.environ.get("TG_CHAT_ID")
    if not token or not chat_id:
        print("Telegram env vars not set; skipping notification.")
        return
    msg = textwrap.dedent(f"""
    🏘️  Scraping AEDAS terminado.
    • Promociones extraídas: {total}
    • Archivo CSV: {file_path}
    """).strip()
    resp = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={"chat_id": chat_id, "text": msg},
        timeout=30,
    )
    resp.raise_for_status()
    print("Telegram notification sent.")

def main():
    data = scrape_all()
    csv_path = "promociones_aedas.csv"
    save_csv(data, csv_path)
    with open("promociones_aedas.json", "w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)
    notify_telegram(csv_path, len(data))
    print(f"Extraídas {len(data)} promociones.")

if __name__ == "__main__":
    main()