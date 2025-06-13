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
    # ... (código de aedas se mantiene igual, es funcional)
    resultados_aedas = []
    try:
        url_aedas = "https://www.aedashomes.com/viviendas-obra-nueva?province=2509951"
        response = requests.get(url_aedas, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        tarjetas = soup.select('a.card-promo.card')
        print(f"AEDAS: Se encontraron {len(tarjetas)} promociones.", flush=True)
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
                    url_promo = "https://www.aedashomes.com" + tarjeta.get('href', '')
                    resultados_aedas.append(f"\n*{nombre} (AEDAS)*\n📍 {ubicacion.title()}\n💶 Desde: {precio:,}€\n🛏️ Dorms: {habitaciones}\n🔗 [Ver promoción]({url_promo})".replace(",","."))
    except Exception as e:
        print(f"  -> ERROR en el scraper de AEDAS: {e}", flush=True)
    return resultados_aedas

# --- SCRAPER PARA VÍA CÉLERE (LÓGICA RECONSTRUIDA Y CORRECTA) ---

def scrape_viacelere(headers):
    print("\n--- Iniciando scraper de VÍA CÉLERE ---", flush=True)
    resultados_celere = []
    try:
        url_celere = "https://www.viacelere.com/promociones?provincia_id=46"
        response = requests.get(url_celere, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # El contenedor principal de cada promoción es un 'article'
        tarjetas = soup.select('article.card-promotion')
        print(f"VÍA CÉLERE: Se encontraron {len(tarjetas)} promociones.", flush=True)

        for tarjeta in tarjetas:
            # --- Extracción con los selectores correctos ---
            nombre_tag = tarjeta.select_one('h2.card-promotion__title')
            nombre = nombre_tag.get_text(strip=True) if nombre_tag else "SIN NOMBRE"

            url_tag = tarjeta.find('a', class_='card-promotion__link')
            url_promo = url_tag['href'] if url_tag and url_tag.has_attr('href') else "SIN URL"
            
            # El estado ('Próximamente', 'En comercialización') está en un tag específico
            status_tag = tarjeta.select_one('span.card-promotion__tag')
            status = status_tag.get_text(strip=True) if status_tag else "SIN ESTADO"
            
            ubicacion_tag = tarjeta.select_one('p.card-promotion__location')
            ubicacion = ubicacion_tag.get_text(strip=True).lower() if ubicacion_tag else "SIN UBICACIÓN"
            
            precio_tag = tarjeta.select_one('p.card-promotion__price')
            precio_texto = precio_tag.get_text(strip=True) if precio_tag else None

            habitaciones_tag = tarjeta.select_one('p.card-promotion__typology')
            habitaciones_texto = habitaciones_tag.get_text(strip=True) if habitaciones_tag else None
            
            print(f"  -> Crudo: N='{nombre}', U='{ubicacion}', S='{status}', H='{habitaciones_texto}', P='{precio_texto}'", flush=True)

            # --- Lógica de filtrado ---
            if any(loc in ubicacion for loc in LOCALIZACIONES_DESEADAS):
                if 'Próximamente' in status:
                    print(f"    -> MATCH 'Próximamente': {nombre}", flush=True)
                    resultados_celere.append(f"\n*{nombre} (Vía Célere - Próximamente)*\n📍 {ubicacion.title()}\n🔗 [Ver promoción]({url_promo})")
                
                elif 'En comercialización' in status:
                    precio = limpiar_y_convertir_a_numero(precio_texto)
                    habitaciones = limpiar_y_convertir_a_numero(habitaciones_texto)
                    
                    if all([precio, habitaciones]) and precio <= PRECIO_MAXIMO and habitaciones >= HABITACIONES_MINIMAS:
                        print(f"    -> MATCH 'En Venta': {nombre}", flush=True)
                        resultados_celere.append(f"\n*{nombre} (Vía Célere)*\n📍 {ubicacion.title()}\n💶 Desde: {precio:,}€\n🛏️ Dorms: {habitaciones}\n🔗 [Ver promoción]({url_promo})".replace(",","."))

    except Exception as e:
        print(f"  -> ERROR en el scraper de VÍA CÉLERE: {e}", flush=True)
    return resultados_celere

# --- Función Principal (Sin cambios) ---

def main():
    HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    todos_los_resultados = []
    todos_los_resultados.extend(scrape_aedas(HEADERS))
    todos_los_resultados.extend(scrape_viacelere(HEADERS))
    if not todos_los_resultados:
        mensaje_final = f"✅ Scrapers finalizados.\n\nNo se ha encontrado ninguna promoción nueva que cumpla tus filtros en AEDAS o Vía Célere."
    else:
        mensaje_final = f"📢 ¡Se han encontrado {len(todos_los_resultados)} promociones que cumplen tus filtros!\n"
        mensaje_final += "".join(todos_los_resultados)
    enviar_mensaje_telegram(mensaje_final)

if __name__ == "__main__":
    main()
