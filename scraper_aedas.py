import requests
import os
import sys
import re
import json
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

def extraer_detalles_promocion(url_promocion, headers):
    """Extrae detalles de la promoción usando el bloque de datos JSON-LD."""
    try:
        print(f"  -> Analizando: {url_promocion}", flush=True)
        response = requests.get(url_promocion, headers=headers, timeout=20)
        if not response.ok: return None

        soup = BeautifulSoup(response.text, 'html.parser')
        data_script = soup.find("script", type="application/ld+json")
        if not data_script:
            print(f"    -> AVISO: No se encontró el bloque de datos JSON-LD en {url_promocion}", flush=True)
            return None

        data = json.loads(data_script.string)
        nombre = data.get('name')
        ubicacion = data.get('address', {}).get('addressLocality', '').lower()
        precio = data.get('offers', {}).get('price')
        habitaciones = data.get('numberOfRooms')

        precio_num = int(float(precio)) if precio else None
        habitaciones_num = int(float(habitaciones)) if habitaciones else None

        detalles = {'nombre': nombre, 'ubicacion': ubicacion, 'precio': precio_num, 'habitaciones': habitaciones_num, 'url': url_promocion}
        print(f"    -> Datos extraídos: {detalles}", flush=True)
        return detalles

    except Exception as e:
        print(f"    -> ERROR extrayendo detalles de {url_promocion}: {e}", flush=True)
        return None

# --- Función principal ---

def main():
    URL_BASE = "https://www.aedashomes.com"
    # --- ¡AQUÍ ESTÁ LA OPTIMIZACIÓN CLAVE! ---
    # Usamos la URL que has encontrado, que filtra directamente por la provincia de Valencia.
    URL_PROMOCIONES = "https://www.aedashomes.com/viviendas-obra-nueva?province=2509951"
    HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    try:
        print(f"PASO 1: Obteniendo promociones desde la página de Valencia: {URL_PROMOCIONES}", flush=True)
        response = requests.get(URL_PROMOCIONES, headers=HEADERS, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        enlaces_relativos = soup.select('a.card-promo')
        if not enlaces_relativos:
            enviar_mensaje_telegram("❌ No se encontraron promociones en la página de Valencia. El selector 'a.card-promo' podría haber cambiado.")
            return

        urls_a_visitar = list(set([f"{URL_BASE}{enlace['href']}" for enlace in enlaces_relativos if enlace.has_attr('href')]))
        print(f"Se encontraron {len(urls_a_visitar)} promociones únicas. Analizando...", flush=True)
        
        promociones_filtradas = []
        for url in urls_a_visitar:
            detalles = extraer_detalles_promocion(url, HEADERS)
            if not detalles or not all(detalles.get(k) is not None for k in ['ubicacion', 'precio', 'habitaciones']):
                continue

            ubicacion_ok = any(loc in detalles['ubicacion'] for loc in LOCALIZACIONES_DESEADAS)
            precio_ok = detalles['precio'] <= PRECIO_MAXIMO
            habitaciones_ok = detalles['habitaciones'] >= HABITACIONES_MINIMAS

            if ubicacion_ok and precio_ok and habitaciones_ok:
                print(f"    ¡¡¡MATCH ENCONTRADO!!! {detalles['nombre']}", flush=True)
                promociones_filtradas.append(detalles)

        print("\nPASO FINAL: Generando reporte.", flush=True)
        if not promociones_filtradas:
            mensaje_final = f"✅ Scraper de AEDAS finalizado.\n\nNo se ha encontrado ninguna promoción que cumpla tus filtros actuales:\n- Ubicación: `{', '.join(LOCALIZACIONES_DESEADAS)}`\n- Precio Máx: `{PRECIO_MAXIMO:,}€`\n- Hab. Mín: `{HABITACIONES_MINIMAS}`".replace(",",".")
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
