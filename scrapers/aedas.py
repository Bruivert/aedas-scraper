import requests
import os
import sys
import re
from bs4 import BeautifulSoup

# --- TUS FILTROS (Se aplicarán a las promociones "En Comercialización") ---
LOCALIZACIONES_DESEADAS = ["mislata", "valencia", "quart de poblet", "paterna", "manises"]
PRECIO_MAXIMO = 270000
HABITACIONES_MINIMAS = 2

# --- Funciones auxiliares (no necesitas tocarlas) ---

def enviar_mensaje_telegram(texto):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Error: Secrets de Telegram no encontrados.", flush=True)
        return
    if len(texto) > 4096:
        texto = texto[:4000] + "\n\n[Mensaje truncado...]"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": texto, "parse_mode": "Markdown", "disable_web_page_preview": True}
    try:
        response = requests.post(url, data=payload, timeout=20)
        response.raise_for_status()
        print("Mensaje enviado a Telegram.", flush=True)
    except requests.exceptions.RequestException as e:
        print(f"Error CRÍTICO al enviar a Telegram: {e}", flush=True)

def limpiar_y_convertir_a_numero(texto):
    if not texto: return None
    try:
        numeros = re.findall(r'[\d.]+', texto)
        if not numeros: return None
        return int(numeros[0].replace('.', ''))
    except (ValueError, TypeError):
        return None

# --- SCRAPER PARA AEDAS (Sin cambios) ---

def scrape_aedas(headers):
    print("\n--- Iniciando scraper de AEDAS ---", flush=True)
    resultados_aedas = []
    try:
        url_aedas = "https://www.aedashomes.com/viviendas-obra-nueva?province=2509951"
        response = requests.get(url_aedas, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        tarjetas = soup.select('a.card-promo.card')
        print(f"AEDAS: Se encontraron {len(tarjetas)} promociones.", flush=True)

        for tarjeta in tarjetas:
            nombre_tag = tarjeta.find('span', class_='promo-title')
            nombre = nombre_tag.get_text(strip=True) if nombre_tag else "N/A"
            precio_tag = tarjeta.find('span', class_='promo-price')
            precio_texto = precio_tag.get_text(strip=True) if precio_tag else None
            detalles_lista = tarjeta.select('ul.promo-description li')
            ubicacion = detalles_lista[0].get_text(strip=True).lower() if len(detalles_lista) > 0 else "N/A"
            habitaciones_texto = detalles_lista[1].get_text(strip=True) if len(detalles_lista) > 1 else None
            precio = limpiar_y_convertir_a_numero(precio_texto)
            habitaciones = limpiar_y_convertir_a_numero(habitaciones_texto)

            if all([nombre, ubicacion, precio, habitaciones]):
                if any(loc in ubicacion for loc in LOCALIZACIONES_DESEADAS) and precio <= PRECIO_MAXIMO and habitaciones >= HABITACIONES_MINIMAS:
                    print(f"  -> MATCH en AEDAS: {nombre}", flush=True)
                    url_promo = "https://www.aedashomes.com" + tarjeta.get('href', '')
                    resultados_aedas.append(f"\n*{nombre} (AEDAS)*\n📍 {ubicacion.title()}\n💶 Desde: {precio:,}€\n🛏️ Dorms: {habitaciones}\n🔗 [Ver promoción]({url_promo})".replace(",","."))
    except Exception as e:
        print(f"  -> ERROR en el scraper de AEDAS: {e}", flush=True)
    return resultados_aedas