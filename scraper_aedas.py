#!/usr/bin/env python3
"""
Scraper AEDAS + Vía Célere para Telegram
---------------------------------------

• Filtra por localización, precio y nº de dormitorios
• Envía un único mensaje al bot con todas las coincidencias
"""

import os
import re
import sys
import requests
from bs4 import BeautifulSoup


# ────────────────────────────────────────────────────────────────
# CONFIGURACIÓN DE FILTROS
# ────────────────────────────────────────────────────────────────
LOCALIZACIONES_DESEADAS = [
    "mislata", "valencia", "quart de poblet", "paterna", "manises"
]
PRECIO_MAXIMO       = 270_000          # €  (guión bajo = separador visual)
HABITACIONES_MINIMAS = 2               # dormitorios


# ────────────────────────────────────────────────────────────────
# UTILIDADES
# ────────────────────────────────────────────────────────────────
def enviar_mensaje_telegram(texto: str) -> None:
    """Manda 'texto' a tu bot de Telegram usando token y chat ID en secrets."""
    token   = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("❌ Secrets de Telegram no encontrados.", flush=True)
        raise SystemExit(1)

    # Evita romper el límite de 4 096 caracteres
    if len(texto) > 4_096:
        texto = texto[:3_900] + "\n\n[Mensaje truncado…]"

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": texto,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }

    try:
        r = requests.post(url, data=payload, timeout=20)
        r.raise_for_status()
        print("✅ Mensaje enviado a Telegram", flush=True)
    except Exception as exc:
        print(f"❌ Error crítico al enviar a Telegram: {exc}", flush=True)
        raise SystemExit(1)


def limpiar_y_convertir_a_numero(texto: str | None) -> int | None:
    """Extrae el primer número entero de 'texto'. Devuelve None si no hay."""
    if not texto:
        return None
    numeros = re.findall(r"[\d.]+", texto)
    if not numeros:
        return None
    try:
        return int(numeros[0].replace(".", ""))
    except ValueError:
        return None


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}


# ────────────────────────────────────────────────────────────────
# SCRAPER 1 · AEDAS
# ────────────────────────────────────────────────────────────────
def scrape_aedas() -> list[str]:
    print("\n——— Iniciando scraper de AEDAS ———", flush=True)
    resultados: list[str] = []

    try:
        # Obra nueva en la provincia de Valencia
        url = "https://www.aedashomes.com/viviendas-obra-nueva?province=2509951"
        res = requests.get(url, headers=HEADERS, timeout=30)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        tarjetas = soup.select("a[data-testid='development-card']")
        print(f"AEDAS: {len(tarjetas)} tarjetas encontradas", flush=True)

        for card in tarjetas:
            nombre_tag   = card.select_one(".development-card__title")
            precio_tag   = card.select_one(".development-card__price")
            ubicacion_tag = card.select_one(".development-card__location")
            hab_tag      = card.find(string=lambda t: "dorm" in t.lower())

            # Limpieza de campos
            nombre     = nombre_tag.get_text(strip=True) if nombre_tag else None
            precio     = limpiar_y_convertir_a_numero(precio_tag.get_text(strip=True) if precio_tag else None)
            ubicacion  = ubicacion_tag.get_text(strip=True).lower() if ubicacion_tag else None
            habitaciones = limpiar_y_convertir_a_numero(hab_tag) if hab_tag else None

            if all([nombre, precio, ubicacion, habitaciones]):
                if (any(loc in ubicacion for loc in LOCALIZACIONES_DESEADAS)
                        and precio <= PRECIO_MAXIMO
                        and habitaciones >= HABITACIONES_MINIMAS):
                    print(f"  → MATCH en AEDAS: {nombre}", flush=True)
                    url_promo = "https://www.aedashomes.com" + card["href"]
                    resultados.append(
                        f"\n*{nombre} (AEDAS)*"
                        f"\n📍 {ubicacion.title()}"
                        f"\n💶 Desde: {precio:,}€"
                        f"\n🛏️ Dorms: {habitaciones}"
                        f"\n🔗 [Ver promoción]({url_promo})".replace(",", ".")
                    )
    except Exception as exc:
        print(f"❌ ERROR en el scraper de AEDAS: {exc}", flush=True)

    return resultados


# ────────────────────────────────────────────────────────────────
# SCRAPER 2 · VÍA CÉLERE
# ────────────────────────────────────────────────────────────────
def scrape_viacelere() -> list[str]:
    print("\n——— Iniciando scraper de VÍA CÉLERE ———", flush=True)
    resultados: list[str] = []

    try:
        url = "https://www.viacelere.com/promociones?provincia_id=46"
        res = requests.get(url, headers=HEADERS, timeout=30)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        tarjetas = soup.select("div.card-promocion")
        print(f"VÍA CÉLERE: {len(tarjetas)} tarjetas encontradas", flush=True)

        for idx, card in enumerate(tarjetas, start=1):
            # ── TÍTULO (quita “Célere ” del principio) ─────────────────────
            h2_tag = card.select_one("div.title h2")
            if h2_tag:
                raw   = h2_tag.get_text(" ", strip=True)
                nombre = re.sub(r"^\s*C[eé]lere\s+", "", raw, flags=re.I).strip()
            else:
                nombre = "SIN NOMBRE"

            # ── URL de la tarjeta ─────────────────────────────────────────
            a_tag = card.find_parent("a")
            url_promo = a_tag["href"] if (a_tag and a_tag.has_attr("href")) else "SIN URL"

            # ── Descripción: ubicación, estado, habitaciones ─────────────
            ubicacion, status, habitaciones_txt = None, None, None
            for p in card.select("div.desc p"):
                txt_low = p.get_text(strip=True).lower()
                if "españa, valencia" in txt_low:
                    ubicacion = txt_low
                elif "dormitorio" in txt_low:
                    habitaciones_txt = txt_low
                elif "comercialización" in txt_low or "próximamente" in txt_low:
                    status = p.get_text(strip=True)

            precio_tag = card.select_one("div.precio p.paragraph-size--2:last-child")
            precio_txt = precio_tag.get_text(strip=True) if precio_tag else None

            # ── Línea de depuración —––––––––––––––––––––––––––––––––––––––
            print(f"  · [{idx}] N='{nombre}' U='{ubicacion}' S='{status}' "
                  f"H='{habitaciones_txt}' P='{precio_txt}'", flush=True)

            # ── Filtrado por criterios del usuario ───────────────────────
            if ubicacion and any(loc in ubicacion for loc in LOCALIZACIONES_DESEADAS):
                if status and "próximamente" in status.lower():
                    resultados.append(
                        f"\n*{nombre} (Vía Célere - Próximamente)*"
                        f"\n📍 {ubicacion.title()}"
                        f"\n🔗 [Ver promoción]({url_promo})"
                    )
                elif status and "comercialización" in status.lower():
                    precio       = limpiar_y_convertir_a_numero(precio_txt)
                    habitaciones = limpiar_y_convertir_a_numero(habitaciones_txt)

                    if (precio is not None and habitaciones is not None
                            and precio <= PRECIO_MAXIMO
                            and habitaciones >= HABITACIONES_MINIMAS):
                        resultados.append(
                            f"\n*{nombre} (Vía Célere)*"
                            f"\n📍 {ubicacion.title()}"
                            f"\n💶 Desde: {precio:,}€"
                            f"\n🛏️ Dorms: {habitaciones}"
                            f"\n🔗 [Ver promoción]({url_promo})".replace(",", ".")
                        )

    except Exception as exc:
        print(f"❌ ERROR en el scraper de VÍA CÉLERE: {exc}", flush=True)

    return resultados


# ────────────────────────────────────────────────────────────────
# MAIN
# ────────────────────────────────────────────────────────────────
def main() -> None:
    resultados = scrape_aedas() + scrape_viacelere()

    if resultados:
        msg = f"📢 ¡{len(resultados)} promociones cumplen tus filtros! 🚀\n"
        msg += "".join(resultados)
    else:
        msg = (
            "✅ Scrapers finalizados.\n\n"
            "No se encontró ninguna promoción nueva que cumpla tus filtros "
            "en AEDAS o Vía Célere."
        )

    enviar_mensaje_telegram(msg)


if __name__ == "__main__":
    main()