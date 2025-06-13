import requests
import os
import sys
import re
from bs4 import BeautifulSoup

# --- TUS FILTROS ---
LOCALIZACIONES_DESEADAS = ["mislata", "valencia", "quart de poblet", "paterna", "manises"]
PRECIO_MAXIMO = 270000
HABITACIONES_MINIMAS = 2

# --- Funciones auxiliares (no necesitas tocarlas) ---
def enviar_mensaje_telegram(texto):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id: return
    if len(texto) > 4096: texto = texto[:4000] + "\n\n[...]"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": texto, "parse_mode": "Markdown", "disable_web_page_preview": True}
    try:
        requests.post(url, data=payload, timeout=20).raise_for_status()
        print("Mensaje enviado a Telegram.", flush=True)
    except Exception as e:
        print(f"Error CRÍTICO al enviar a Telegram: {e}", flush=True)

def limpiar_y_convertir_a_numero(texto):
    if not texto: return None
    try:
        numeros = re.findall(r'[\d.]+', texto)
        return int(numeros[0].replace('.', '')) if numeros else None
    except (ValueError, TypeError):
        return None

def get_google_cache(url, headers):
    """Obtiene el contenido de una URL a través del caché de Google."""
    # Construimos la URL del caché de Google
    cache_url = f"http://webcache.googleusercontent.com/search?q=cache:{url}"
    print(f"  -> Pidiendo a Google la 'foto' de: {url}", flush=True)
    response = requests.get(cache_url, headers=headers, timeout=30)
    response.raise_for_status()
    return BeautifulSoup(response.text, 'html.parser')

# --- SCRAPERS CON LA TÉCNICA DEL CACHÉ ---

def scrape_aedas(headers):
    print("\n--- Iniciando scraper de AEDAS (vía Google Cache) ---", flush=True)
    resultados = []
    try:
        url_aedas = "https://www.aedashomes.com/viviendas-obra-nueva?province=2509951"
        soup = get_google_cache(url_aedas, headers)
        
        # En la versión de caché, los selectores pueden ser más simples
        tarjetas = soup.select('div.card-promo-list')
        print(f"AEDAS: Se encontraron {len(tarjetas)} promociones en el caché de Google.", flush=True)

        for tarjeta in tarjetas:
            nombre = tarjeta.find('h2', class_='card-promo-list__title').get_text(strip=True) if tarjeta.find('h2') else None
            ubicacion = tarjeta.find('p', class_='card-promo-list__location').get_text(strip=True).lower() if tarjeta.find('p', class_='card-promo-list__location') else None
            precio_texto = tarjeta.find('p', class_='card-promo-list__price').get_text(strip=True) if tarjeta.find('p', class_='card-promo-list__price') else None
            habitaciones_texto = next((feat.get_text(strip=True) for feat in tarjeta.select('li.card-promo-list__feature') if 'dormitorio' in feat.get_text(strip=True).lower()), None)
            
            if all([nombre, ubicacion]):
                precio = limpiar_y_convertir_a_numero(precio_texto)
                habitaciones = limpiar_y_convertir_a_numero(habitaciones_texto)
                if all([precio, habitaciones]) and any(loc in ubicacion for loc in LOCALIZACIONES_DESEADAS) and precio <= PRECIO_MAXIMO and habitaciones >= HABITACIONES_MINIMAS:
                    url_promo = "https://www.aedashomes.com" + tarjeta.find_parent('a')['href'] if tarjeta.find_parent('a') else url_aedas
                    resultados.append(f"\n*{nombre} (AEDAS)*\n📍 {ubicacion.title()}\n💶 Desde: {precio:,}€\n🛏️ Dorms: {habitaciones}\n🔗 [Ver promoción]({url_promo})".replace(",", "."))
    except Exception as e:
        print(f"  -> ERROR en el scraper de AEDAS (Google Cache): {e}", flush=True)
    return resultados

def scrape_viacelere(headers):
    print("\n--- Iniciando scraper de VÍA CÉLERE (vía Google Cache) ---", flush=True)
    resultados = []
    try:
        url_celere = "https://www.viacelere.com/promociones?provincia_id=46"
        soup = get_google_cache(url_celere, headers)
        
        # Usamos los selectores que funcionaban en la versión simple de la web
        tarjetas = soup.select('article.card-promotion')
        print(f"VÍA CÉLERE: Se encontraron {len(tarjetas)} promociones en el caché de Google.", flush=True)

        for tarjeta in tarjetas:
            nombre = tarjeta.select_one('h2.card-promotion__title').get_text(strip=True) if tarjeta.select_one('h2') else None
            ubicacion = tarjeta.select_one('p.card-promotion__location').get_text(strip=True).lower() if tarjeta.select_one('p.card-promotion__location') else None
            status_tag = tarjeta.select_one('span.card-promotion__tag')
            status = status_tag.get_text(strip=True) if status_tag else "En comercialización"
            
            if nombre and ubicacion and any(loc in ubicacion for loc in LOCALIZACIONES_DESEADAS):
                if 'Próximamente' in status:
                    url_promo = tarjeta.find('a', class_='card-promotion__link')['href'] if tarjeta.find('a', class_='card-promotion__link') else url_celere
                    resultados.append(f"\n*{nombre} (Vía Célere - Próximamente)*\n📍 {ubicacion.title()}\n🔗 [Ver promoción]({url_promo})")
                else:
                    precio_texto = tarjeta.select_one('p.card-promotion__price').get_text(strip=True) if tarjeta.select_one('p.card-promotion__price') else None
                    habitaciones_texto = tarjeta.select_one('p.card-promotion__typology').get_text(strip=True) if tarjeta.select_one('p.card-promotion__typology') else None
                    precio = limpiar_y_convertir_a_numero(precio_texto)
                    habitaciones = limpiar_y_convertir_a_numero(habitaciones_texto)
                    if all([precio, habitaciones]) and precio <= PRECIO_MAXIMO and habitaciones >= HABITACIONES_MINIMAS:
                        url_promo = tarjeta.find('a', class_='card-promotion__link')['href'] if tarjeta.find('a', class_='card-promotion__link') else url_celere
                        resultados.append(f"\n*{nombre} (Vía Célere)*\n📍 {ubicacion.title()}\n💶 Desde: {precio:,}€\n🛏️ Dorms: {habitaciones}\n🔗 [Ver promoción]({url_promo})".replace(",","."))
    except Exception as e:
        print(f"  -> ERROR en el scraper de VÍA CÉLERE (Google Cache): {e}", flush=True)
    return resultados

# --- Función Principal ---
def main():
    HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    todos_los_resultados = []
    
    todos_los_resultados.extend(scrape_aedas(HEADERS))
    todos_los_resultados.extend(scrape_viacelere(HEADERS))

    if not todos_los_resultados:
        mensaje_final = f"✅ Scrapers finalizados.\n\nNo se ha encontrado ninguna promoción que cumpla tus filtros."
    else:
        mensaje_final = f"📢 ¡Se han encontrado {len(todos_los_resultados)} promociones!\n" + "".join(todos_los_resultados)
        
    enviar_mensaje_telegram(mensaje_final)

if __name__ == "__main__":
    main()
