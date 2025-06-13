import requests
import os
import sys
import re

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

# --- SCRAPER PARA AEDAS (Volvemos al método simple con Requests) ---
def scrape_aedas(headers):
    print("\n--- Iniciando scraper de AEDAS (Método Directo) ---", flush=True)
    resultados = []
    try:
        from bs4 import BeautifulSoup
        url = "https://www.aedashomes.com/viviendas-obra-nueva?province=2509951"
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        tarjetas = soup.select('div.card-promo-list')
        print(f"AEDAS: Se encontraron {len(tarjetas)} promociones.", flush=True)

        for tarjeta in tarjetas:
            nombre = tarjeta.find('h2', class_='card-promo-list__title').get_text(strip=True) if tarjeta.find('h2') else "N/A"
            ubicacion = tarjeta.find('p', class_='card-promo-list__location').get_text(strip=True).lower() if tarjeta.find('p') else "N/A"
            precio_texto = tarjeta.find('p', class_='card-promo-list__price').get_text(strip=True) if tarjeta.find('p', class_='card-promo-list__price') else None
            habitaciones_texto = next((feat.get_text(strip=True) for feat in tarjeta.select('li.card-promo-list__feature') if 'dormitorio' in feat.get_text(strip=True).lower()), None)
            url_promo = "https://www.aedashomes.com" + tarjeta.find_parent('a')['href'] if tarjeta.find_parent('a') else "SIN URL"
            precio = limpiar_y_convertir_a_numero(precio_texto)
            habitaciones = limpiar_y_convertir_a_numero(habitaciones_texto)

            if all([nombre, ubicacion, precio, habitaciones]) and any(loc in ubicacion for loc in LOCALIZACIONES_DESEADAS) and precio <= PRECIO_MAXIMO and habitaciones >= HABITACIONES_MINIMAS:
                print(f"  -> MATCH en AEDAS: {nombre}", flush=True)
                resultados.append(f"\n*{nombre} (AEDAS)*\n📍 {ubicacion.title()}\n💶 Desde: {precio:,}€\n🛏️ Dorms: {habitaciones}\n🔗 [Ver promoción]({url_promo})".replace(",", "."))
    except Exception as e:
        print(f"  -> ERROR en el scraper de AEDAS: {e}", flush=True)
    return resultados

# --- SCRAPER PARA VÍA CÉLERE (NUEVO MÉTODO DE API DIRECTA) ---
def scrape_viacelere(headers):
    print("\n--- Iniciando scraper de VÍA CÉLERE (Método API) ---", flush=True)
    resultados = []
    try:
        # Esta es la URL de la "llamada secreta"
        api_url = "https://www.viacelere.com/graphql"
        # Este es el "mensaje" que le enviamos, pidiendo las promociones de Valencia (province_id: 46)
        api_payload = {
            "query": """
                query Promotions($filters: PromotionFilters) {
                  promotions(filters: $filters) {
                    items {
                      name
                      url
                      status { name }
                      location { name }
                      price_from
                      typologies { name }
                    }
                  }
                }
            """,
            "variables": { "filters": { "province_id": 46 } }
        }
        
        response = requests.post(api_url, headers=headers, json=api_payload, timeout=20)
        response.raise_for_status()
        data = response.json()
        
        promociones = data.get('data', {}).get('promotions', {}).get('items', [])
        print(f"VÍA CÉLERE: Se encontraron {len(promociones)} promociones vía API.", flush=True)

        for promo in promociones:
            nombre = promo.get('name')
            ubicacion = promo.get('location', {}).get('name', '').lower()
            status = promo.get('status', {}).get('name', '')
            url_promo = promo.get('url')
            
            if any(loc in ubicacion for loc in LOCALIZACIONES_DESEADAS):
                if 'Próximamente' in status:
                    print(f"    -> MATCH 'Próximamente': {nombre}", flush=True)
                    resultados.append(f"\n*{nombre} (Vía Célere - Próximamente)*\n📍 {ubicacion.title()}\n🔗 [Ver promoción]({url_promo})")
                elif 'En comercialización' in status:
                    precio = int(promo.get('price_from', 0))
                    # Buscamos el número mínimo de habitaciones en las tipologías
                    habitaciones = 99 # Un número alto por defecto
                    for tipo in promo.get('typologies', []):
                        num_hab = limpiar_y_convertir_a_numero(tipo.get('name', ''))
                        if num_hab and num_hab < habitaciones:
                            habitaciones = num_hab
                    
                    if all([precio > 0, habitaciones != 99]) and precio <= PRECIO_MAXIMO and habitaciones >= HABITACIONES_MINIMAS:
                        print(f"    -> MATCH 'En Venta': {nombre}", flush=True)
                        resultados.append(f"\n*{nombre} (Vía Célere)*\n📍 {ubicacion.title()}\n💶 Desde: {precio:,}€\n🛏️ Dorms: {habitaciones}\n🔗 [Ver promoción]({url_promo})".replace(",","."))
    except Exception as e:
        print(f"  -> ERROR en el scraper de VÍA CÉLERE (API): {e}", flush=True)
    return resultados

# --- Función Principal ---
def main():
    HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    todos_los_resultados = []
    
    # Probamos ambos métodos
    todos_los_resultados.extend(scrape_aedas(HEADERS))
    todos_los_resultados.extend(scrape_viacelere(HEADERS))

    if not todos_los_resultados:
        mensaje_final = f"✅ Scrapers finalizados.\n\nNo se ha encontrado ninguna promoción nueva que cumpla tus filtros."
    else:
        mensaje_final = f"📢 ¡Se han encontrado {len(todos_los_resultados)} promociones que cumplen tus filtros!\n"
        mensaje_final += "".join(todos_los_resultados)
        
    enviar_mensaje_telegram(mensaje_final)

if __name__ == "__main__":
    main()
