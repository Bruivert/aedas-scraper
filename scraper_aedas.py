import requests
import os
import sys
import re
from bs4 import BeautifulSoup

# --- TUS FILTROS (Se aplicarán a TODAS las búsquedas) ---
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

# --- SCRAPER PARA AEDAS ---

def scrape_aedas(headers):
    print("\n--- Iniciando scraper de AEDAS ---", flush=True)
    resultados_aedas = []
    try:
        url_aedas = "https://www.aedashomes.com/viviendas-obra-nueva?province=2509951"
        response = requests.get(url_aedas, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        tarjetas = soup.select('a.card-promo.card')
        print(f"AEDAS: Se encontraron {len(tarjetas)} promociones en la página de Valencia.", flush=True)

        for tarjeta in tarjetas:
            nombre = tarjeta.find('span', class_='promo-title').get_text(strip=True)
            precio_texto = tarjeta.find('span', class_='promo-price').get_text(strip=True)
            detalles_lista = tarjeta.select('ul.promo-description li')
            ubicacion = detalles_lista[0].get_text(strip=True).lower()
            habitaciones_texto = detalles_lista[1].get_text(strip=True)
            
            precio = limpiar_y_convertir_a_numero(precio_texto)
            habitaciones = limpiar_y_convertir_a_numero(habitaciones_texto)

            if all([nombre, ubicacion, precio, habitaciones]):
                if any(loc in ubicacion for loc in LOCALIZACIONES_DESEADAS) and precio <= PRECIO_MAXIMO and habitaciones >= HABITACIONES_MINIMAS:
                    print(f"  -> MATCH en AEDAS: {nombre}", flush=True)
                    url_promo = "https://www.aedashomes.com" + tarjeta.get('href', '')
                    resultados_aedas.append(f"\n*{nombre} (AEDAS)*\n📍 {ubicacion.title()}\n💶 Desde: {precio:,}€\n🛏️ Dorms: {habitaciones}\n🔗 [Ver promoción]({url_promo})".replace(",","."))
    except Exception as e:
        print(f"  -> ERROR en el scraper de AEDAS: {e}", flush=True)
        resultados_aedas.append("\n❌ No se pudo completar la búsqueda en AEDAS por un error.")
    
    return resultados_aedas

# --- SCRAPER PARA VÍA CÉLERE ---

def scrape_viacelere(headers):
    print("\n--- Iniciando scraper de VÍA CÉLERE ---", flush=True)
    resultados_celere = []
    try:
        url_celere = "https://www.viacelere.com/promociones?provincia_id=46"
        response = requests.get(url_celere, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        tarjetas = soup.select('article.card-promotion')
        print(f"VÍA CÉLERE: Se encontraron {len(tarjetas)} promociones en la página de Valencia.", flush=True)

        for tarjeta in tarjetas:
            nombre = tarjeta.find('h2', class_='card-promotion__title').get_text(strip=True)
            ubicacion = tarjeta.find('p', class_='card-promotion__location').get_text(strip=True).lower()
            precio_texto = tarjeta.find('p', class_='card-promotion__price').get_text(strip=True)
            
            # Las habitaciones no están en la tarjeta, hay que visitar el enlace
            url_promo = tarjeta.find('a')['href']
            
            precio = limpiar_y_convertir_a_numero(precio_texto)

            if any(loc in ubicacion for loc in LOCALIZACIONES_DESEADAS) and precio and precio <= PRECIO_MAXIMO:
                # Solo visitamos la página si cumple el filtro de ubicación y precio
                print(f"  -> VÍA CÉLERE: Visitando '{nombre}' para buscar habitaciones...", flush=True)
                promo_response = requests.get(url_promo, headers=headers, timeout=20)
                promo_soup = BeautifulSoup(promo_response.text, 'html.parser')
                
                habitaciones = None
                features = promo_soup.select('ul.features li')
                for feature in features:
                    if 'dormitorio' in feature.get_text(strip=True).lower():
                        habitaciones = limpiar_y_convertir_a_numero(feature.get_text(strip=True))
                        break

                if habitaciones and habitaciones >= HABITACIONES_MINIMAS:
                    print(f"    -> MATCH en VÍA CÉLERE: {nombre}", flush=True)
                    resultados_celere.append(f"\n*{nombre} (Vía Célere)*\n📍 {ubicacion.title()}\n💶 Desde: {precio:,}€\n🛏️ Dorms: {habitaciones}\n🔗 [Ver promoción]({url_promo})".replace(",","."))

    except Exception as e:
        print(f"  -> ERROR en el scraper de VÍA CÉLERE: {e}", flush=True)
        resultados_celere.append("\n❌ No se pudo completar la búsqueda en Vía Célere por un error.")
        
    return resultados_celere

# --- Función Principal ---

def main():
    HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    todos_los_resultados = []
    
    # Ejecutamos cada scraper y recogemos sus resultados
    todos_los_resultados.extend(scrape_aedas(HEADERS))
    todos_los_resultados.extend(scrape_viacelere(HEADERS))
    
    # Generamos el reporte final
    if not todos_los_resultados:
        mensaje_final = f"✅ Scrapers finalizados.\n\nNo se ha encontrado ninguna promoción nueva que cumpla tus filtros en AEDAS o Vía Célere."
    else:
        mensaje_final = f"📢 ¡Se han encontrado {len(todos_los_resultados)} promociones que cumplen tus filtros!\n"
        mensaje_final += "".join(todos_los_resultados)
        
    enviar_mensaje_telegram(mensaje_final)

if __name__ == "__main__":
    main()
