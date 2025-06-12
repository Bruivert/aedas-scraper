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
    if not texto: return None
    try:
        numeros = re.findall(r'[\d.]+', texto)
        if not numeros: return None
        return int(numeros[0].replace('.', ''))
    except (ValueError, TypeError):
        return None

# --- Función principal (LÓGICA CORREGIDA) ---

def main():
    URL_BASE = "https://www.aedashomes.com"
    URL_PROMOCIONES = f"{URL_BASE}/viviendas-obra-nueva?province=2509951"
    HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    try:
        print(f"PASO 1: Obteniendo promociones desde la página de Valencia: {URL_PROMOCIONES}", flush=True)
        response = requests.get(URL_PROMOCIONES, headers=HEADERS, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        tarjetas_promociones = soup.select('a.card-promo.card')
        if not tarjetas_promociones:
            enviar_mensaje_telegram("❌ No se encontraron tarjetas de promociones en la página. El selector 'a.card-promo.card' podría haber cambiado.")
            return

        print(f"Se encontraron {len(tarjetas_promociones)} promociones. Extrayendo datos y filtrando...", flush=True)
        promociones_filtradas = []

        for tarjeta in tarjetas_promociones:
            nombre_tag = tarjeta.find('span', class_='promo-title')
            nombre = nombre_tag.get_text(strip=True) if nombre_tag else None

            precio_tag = tarjeta.find('span', class_='promo-price')
            precio_texto = precio_tag.get_text(strip=True) if precio_tag else None
            
            detalles_lista = tarjeta.select('ul.promo-description li')
            
            # --- ¡AQUÍ ESTABA EL ERROR! AÑADIMOS EL PARÉNTESIS DE CIERRE ---
            ubicacion_texto = detalles_lista[0].get_text(strip=True) if len(detalles_lista) > 0 else None
            habitaciones_texto = detalles_lista[1].get_text(strip=True) if len(detalles_lista) > 1 else None
            
            url = URL_BASE + tarjeta.get('href', '')

            precio = limpiar_y_convertir_a_numero(precio_texto)
            habitaciones = limpiar_y_convertir_a_numero(habitaciones_texto)
            ubicacion = ubicacion_texto.lower() if ubicacion_texto else ''

            print(f"  -> Analizando: {nombre} | {ubicacion} | {habitaciones} hab. | {precio}€", flush=True)

            if all([nombre, ubicacion, precio, habitaciones]):
                ubicacion_ok = any(loc in ubicacion for loc in LOCALIZACIONES_DESEADAS)
                precio_ok = precio <= PRECIO_MAXIMO
                habitaciones_ok = habitaciones >= HABITACIONES_MINIMAS

                if ubicacion_ok and precio_ok and habitaciones_ok:
                    print(f"    ¡¡¡MATCH ENCONTRADO!!! {nombre}", flush=True)
                    promociones_filtradas.append({'nombre': nombre, 'ubicacion': ubicacion, 'precio': precio, 'habitaciones': habitaciones, 'url': url})
        
        print("\nPASO FINAL: Generando reporte.", flush=True)
        if not promociones_filtradas:
            mensaje_final = f"✅ Scraper de AEDAS finalizado.\n\nNo se ha encontrado ninguna promoción que cumpla tus filtros actuales en la página de Valencia:\n- Ubicación: `{', '.join(LOCALIZACIONES_DESEADAS)}`\n- Precio Máx: `{PRECIO_MAXIMO:,}€`\n- Hab. Mín: `{HABITACIONES_MINIMAS}`".replace(",",".")
        else:
            mensaje_final = f"📢 ¡Se han encontrado {len(promociones_filtradas)} promociones que cumplen tus filtros!\n"
            for promo in promociones_filtradas:
                mensaje_final += f"\n*{promo['nombre']}*\n"
                mensaje_final += f"📍 {promo['ubicacion'].title()}\n"
                mensaje_final += f"💶 Desde: {promo['precio']:,}€\n".replace(",",".")
                mensaje_final += f"🛏️ Dorms: {promo['habitaciones']}\n"
                mensaje_final += f"🔗 [Ver promoción]({promo['url']})\n"
        
        enviar_mensaje_telegram(mensaje_final)

    except Exception as e:
        error_msg = f"❌ Error inesperado en el scraper: {e}"
        print(error_msg, flush=True)
        enviar_mensaje_telegram(error_msg)

if __name__ == "__main__":
    main()
