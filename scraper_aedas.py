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
    """Extrae todos los dígitos de un texto y los convierte en un número entero."""
    if not texto: return None
    try:
        numeros = re.findall(r'\d+', texto)
        return int("".join(numeros)) if numeros else None
    except (ValueError, TypeError):
        return None

def extraer_detalles_promocion(url_promocion, headers):
    """Visita la página de una promoción y extrae sus detalles con los selectores ACTUALIZADOS."""
    try:
        print(f"  -> Analizando: {url_promocion}", flush=True)
        response = requests.get(url_promocion, headers=headers, timeout=20)
        if not response.ok: return None

        soup_promo = BeautifulSoup(response.text, 'html.parser')

        # --- SELECTORES ACTUALIZADOS (AQUÍ ESTÁ LA MAGIA) ---
        nombre_tag = soup_promo.find('h1')
        nombre = nombre_tag.get_text(strip=True) if nombre_tag else 'Nombre no encontrado'

        # La ubicación ahora está en un div con esta clase específica
        ubicacion_tag = soup_promo.find('div', class_='promotion-location-text')
        ubicacion = ubicacion_tag.get_text(strip=True).lower() if ubicacion_tag else ''

        # El precio tiene una clase 'promotion-price' y contiene el texto
        precio_tag = soup_promo.find('p', class_='promotion-price')
        precio_texto = precio_tag.get_text(strip=True) if precio_tag else None
        
        # Las habitaciones están en varios 'feature-item', buscamos el que contiene "dormitorio"
        habitaciones_texto = None
        feature_items = soup_promo.find_all('div', class_='feature-item__text')
        for item in feature_items:
            if 'dormitorio' in item.get_text(strip=True).lower():
                habitaciones_texto = item.get_text(strip=True)
                break
        
        return {
            'nombre': nombre,
            'ubicacion': ubicacion,
            'precio': limpiar_y_convertir_a_numero(precio_texto),
            'habitaciones': limpiar_y_convertir_a_numero(habitaciones_texto), # Usamos el primer número que encuentre (ej: "2 a 3" -> 2)
            'url': url_promocion
        }
    except Exception as e:
        print(f"    Error extrayendo detalles de {url_promocion}: {e}", flush=True)
        return None

# --- Función principal (lógica general) ---

def main():
    URL_PRINCIPAL = "https://www.aedashomes.com/viviendas-obra-nueva"
    HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    try:
        print("PASO 1: Obteniendo enlaces...", flush=True)
        response = requests.get(URL_PRINCIPAL, headers=HEADERS, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # El selector para las tarjetas de promoción es correcto
        enlaces_promociones = soup.select('a.card-promo')
        if not enlaces_promociones:
            enviar_mensaje_telegram("❌ No se encontraron promociones en la página principal. El selector 'a.card-promo' podría haber cambiado.")
            return

        urls_a_visitar = list(set([enlace['href'] for enlace in enlaces_promociones if enlace.has_attr('href')]))
        print(f"Se encontraron {len(urls_a_visitar)} promociones. Analizando una por una...", flush=True)
        
        promociones_filtradas = []
        for url in urls_a_visitar:
            detalles = extraer_detalles_promocion(url, HEADERS)
            if not detalles: continue

            # --- APLICACIÓN DE FILTROS ---
            if detalles['ubicacion'] and detalles['precio'] and detalles['habitaciones']:
                ubicacion_ok = any(loc in detalles['ubicacion'] for loc in LOCALIZACIONES_DESEADAS)
                precio_ok = detalles['precio'] <= PRECIO_MAXIMO
                habitaciones_ok = detalles['habitaciones'] >= HABITACIONES_MINIMAS

                if ubicacion_ok and precio_ok and habitaciones_ok:
                    print(f"    ¡MATCH! {detalles['nombre']} cumple los criterios.", flush=True)
                    promociones_filtradas.append(detalles)

        print("\nPASO FINAL: Generando reporte.", flush=True)
        if not promociones_filtradas:
            mensaje_final = f"✅ Scraper de AEDAS finalizado.\n\nNo se ha encontrado ninguna promoción que cumpla tus filtros:\n- Ubicación: `{', '.join(LOCALIZACIONES_DESEADAS)}`\n- Precio Máx: `{PRECIO_MAXIMO}€`\n- Hab. Mín: `{HABITACIONES_MINIMAS}`"
        else:
            mensaje_final = f"📢 ¡Se han encontrado {len(promociones_filtradas)} promociones que cumplen tus filtros!\n"
            for promo in promociones_filtradas:
                mensaje_final += f"\n*{promo['nombre']}*\n"
                mensaje_final += f"📍 {promo['ubicacion'].title()}\n"
                mensaje_final += f"💶 Desde: {promo['precio']}€\n"
                mensaje_final += f"🛏️ Dorms: {promo['habitaciones']}\n"
                mensaje_final += f"🔗 [Ver promoción]({promo['url']})\n"
        
        enviar_mensaje_telegram(mensaje_final)

    except Exception as e:
        error_msg = f"❌ Ha ocurrido un error inesperado en el scraper: {e}"
        print(error_msg, flush=True)
        enviar_mensaje_telegram(error_msg)

# --- Punto de entrada del script ---
if __name__ == "__main__":
    main()
