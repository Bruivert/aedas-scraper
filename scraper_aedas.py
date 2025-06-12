
# scraper_aedas.py
"""Scraper simple para AEDAS Homes.

Filtra promociones por ciudad, habitaciones y precio,
envía avisos a Telegram y evita duplicados con SQLite.
"""

import os
import re
import sqlite3
import sys
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from unidecode import unidecode

BASE_URL = "https://www.aedashomes.com"
START_URL = "https://www.aedashomes.com/viviendas-obra-nueva-valencia"

ALLOWED_CITIES = {
    "valencia", "quart de poblet", "manises", "paterna", "mislata",
}
MIN_ROOMS = 2
MAX_PRICE = 270_000  # € 270 000

DB_PATH = "seen.db"

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def notify_telegram(promo: dict) -> None:
    """Envía mensaje a Telegram."""
    if not (TELEGRAM_TOKEN and TELEGRAM_CHAT_ID):
        print("✘ TELEGRAM_TOKEN o TELEGRAM_CHAT_ID no configurados", file=sys.stderr)
        return
    text = (
        f"🏡 <b>{promo['title']}</b>\n"
        f"Ciudad: {promo['city'].title()}\n"
        f"Habitaciones: {promo['rooms']}\n"
        f"Precio: {promo['price']:,} €\n"
        f"{promo['href']}"
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(
            url,
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=20,
        ).raise_for_status()
        print(f"✓ Enviado a Telegram: {promo['title']}")
    except Exception as exc:
        print(f"✘ Error enviando Telegram: {exc}", file=sys.stderr)

def seen_before(db: sqlite3.Connection, href: str) -> bool:
    """True si ya estaba en la BD; False si es nuevo y se inserta."""
    try:
        db.execute("INSERT INTO promos(href) VALUES (?)", (href,))
        db.commit()
        return False
    except sqlite3.IntegrityError:
        return True

def scrape() -> list:
    """Scrapea la página y devuelve lista de promos (dict)."""
    res = requests.get(START_URL, timeout=30)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

    promos = []
    for card in soup.select("a.card-promo.card"):
        href = urljoin(BASE_URL, card.get("href", ""))
        title_elem = card.select_one(".dvpromo-title") or card
        title = title_elem.get_text(strip=True)

        # Ciudad: última parte del título después de "–" o del slug
        if "–" in title:
            city = title.split("–")[-1].strip().lower()
        else:
            city = href.rstrip("/").split("/")[-1].split("-")[-1]
        city = unidecode(city)

        if city not in ALLOWED_CITIES:
            continue

        rooms_elem = card.select_one(".dvpromo-info__rooms")
        rooms = int(re.search(r"\d+", rooms_elem.get_text()).group()) if rooms_elem else 0
        if rooms < MIN_ROOMS:
            continue

        price_elem = card.select_one(".dvpromo-info__price")
        if not price_elem:
            continue
        price = int(re.sub(r"[^0-9]", "", price_elem.get_text()))
        if price > MAX_PRICE or price == 0:
            continue

        promos.append(
            dict(href=href, title=title, city=city, rooms=rooms, price=price)
        )
    return promos

def main() -> None:
    db = sqlite3.connect(DB_PATH)
    db.execute("CREATE TABLE IF NOT EXISTS promos(href TEXT PRIMARY KEY)")
    new_count = 0

    for promo in scrape():
        if seen_before(db, promo["href"]):
            continue
        notify_telegram(promo)
        new_count += 1

    print(f"Nuevas promociones enviadas: {new_count}")

if __name__ == "__main__":
    main()
