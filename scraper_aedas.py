from requests_html import HTMLSession
from urllib.parse import urljoin
import csv, json, time, os, requests, textwrap
from typing import List, Dict

BASE = "https://www.aedashomes.com"
LIST_URL = f"{BASE}/viviendas-obra-nueva"

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
    # Modern selector
    for link in page.html.find('a[data-automation="development-card-link"]'):
        cards.append({
            "title": link.find("h3, h4", first=True).text,
            "url": urljoin(BASE, link.attrs["href"]),
            "location": link.find('[data-automation="development-card-city"]', first=True).text,
            "price_from": link.find('[data-automation="development-card-price-from"]', first=True).text,
        })
    # Fallback legacy
    if not cards:
        for a in page.html.find('a.card-promo, a.card-promo.card'):
            img = a.find("img", first=True)
            cards.append({
                "title": img.attrs.get("alt", "Sin título").strip() if img else "—",
                "url": urljoin(BASE, a.attrs.get("href", "")),
                "location": "—",
                "price_from": "—",
            })
    return cards

def scrape_all(offset_step: int = 30) -> List[Dict[str, str]]:
    session = HTMLSession()
    master: List[Dict[str, str]] = []

    first = fetch_page(session, LIST_URL)
    master.extend(extract_cards(first))

    offset = offset_step
    while True:
        api = f"{BASE}/api/developments?offset={offset}&limit={offset_step}&sort=relevance_desc&lang=es"
        res = session.get(api, headers=HEADERS)
        if res.status_code != 200 or not res.json().get("items"):
            break
        for item in res.json()["items"]:
            master.append(
                {
                    "title": item["title"],
                    "url": urljoin(BASE, item["seoUrl"]),
                    "location": item["city"]["name"],
                    "price_from": item.get("priceFrom", "—"),
                }
            )
        offset += offset_step
        time.sleep(0.4)  # Be polite with server
    session.close()
    return master

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
