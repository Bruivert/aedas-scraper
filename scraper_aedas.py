import requests
import os
import sys
import re
from bs4 import BeautifulSoup

# --- TUS FILTROS (Puedes cambiarlos aquí) ---
LOCALIZACIONES_DESEADAS = ["mislata", "valencia", "quart de poblet", "paterna", "manises"]
PRECIO_MAXIMO = 270000
HABITACIONES_MINIMAS = 2

# --- Funciones auxiliares (no necesitas tocarlas) ---

def enviar_mensaje_telegram(texto):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Error: Secrets de Telegram no encontrados.", flush=True)
        sys.exit(1)
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
        sys.exit(1)

def limpiar_y_convertir_a_numero(texto):
    """Extrae el primer grupo de dígitos de un texto y lo convierte a número."""
    if not texto: return None
    try:
        # Busca cualquier número, incluyendo los que tienen puntos como separadores de miles
        numeros = re.findall(r'[\d.]+', texto)
        if not numeros: return None
        # Limpia los puntos de los miles y convierte a entero
        return int(numeros[0].replace('.', ''))
    except (ValueError, TypeError):
        return None

# --- Función principal (NUEVA LÓGICA) ---

def main():
    URL_BASE = "https://www.aedashomes.com"
    URL_PROMOCIONES = f"{URL_BASE}/viviendas-obra-nueva?province=2509951"
    HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    try:
        print(f"PASO 1: Obteniendo promociones desde la página de Valencia: {URL_PROMOCIONES}", flush=True)
        response = requests.get(URL_PROMOCIONES, headers=HEADERS, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Seleccionamos cada "tarjeta" de promoción basándonos en tu foto
        tarjetas_promociones = soup.select('a.card-promo.card')
        if not tarjetas_promociones:
            enviar_mensaje_telegram("❌ No se encontraron tarjetas de promociones en la página. El selector 'a.card-promo.card' podría haber cambiado.")
            return

        print(f"Se encontraron {len(tarjetas_promociones)} promociones. Extrayendo datos y filtrando...", flush=True)
        promociones_filtradas = []

        for tarjeta in tarjetas_promociones:
            # --- EXTRACCIÓN DIRECTA BASADA EN TU FOTO ---
            nombre_tag = tarjeta.find('span', class_='promo-title')
            nombre = nombre_tag.get_text(strip=True) if nombre_tag else None

            precio_tag = tarjeta.find('span', class_='promo-price')
            precio_texto = precio_tag.get_text(strip=True) if precio_tag else None
            
            # Los detalles están en una lista 'ul'
            detalles_lista = tarjeta.select('ul.promo-description li')
            ubicacion_texto = detalles_lista[0].get_text(strip=True
