import requests
import os
import sys
import re
from bs4 import BeautifulSoup

# --- FILTROS (Puedes cambiar esto cuando quieras) ---
LOCALIZACIONES_DESEADAS = ["mislata", "valencia", "quart de poblet", "paterna", "manises"]
PRECIO_MAXIMO = 270000
HABITACIONES_MINIMAS = 2

# --- Funciones auxiliares (no necesitas tocarlas) ---

def enviar_mensaje_telegram(texto):
    """Envía un mensaje a Telegram."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Error: Secrets de Telegram no encontrados.", flush=True)
        sys.exit(1)

    # Telegram tiene un límite de 4096 caracteres por mensaje
    if len(texto) > 4096:
        texto = texto[:4000] + "\n\n[Mensaje truncado por exceder el límite de Telegram]"

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": texto, "parse_mode": "Markdown", "disable_web_page_preview": True}
    
    try:
        response = requests.post(url, data=payload, timeout=20)
        response.raise_for_status()
        print(f"Mensaje enviado a Telegram.", flush=True)
    except requests.exceptions.RequestException as e:
        print(f"Error CRÍTICO al enviar a Telegram: {e}", flush=True)
        sys.exit(1)

def limpiar_y_convertir_precio(texto_precio):
    """Convierte texto como 'Desde 250.000 €' a un número entero 250000."""
    if not texto_precio:
        return None
    try:
        # Extrae solo los dígitos del texto
        numeros = re.findall(r'\d+', texto_precio)
        return int("".join(numeros))
    except (ValueError, TypeError):
        return None

def limpiar_y_convertir_habitaciones(texto_habitaciones):
    """Convierte texto como 'Hasta 4 dormitorios' al número 4."""
    if not texto_habitaciones:
        return None
    try:
        numeros = re.findall(r'\d+', texto_habitaciones)
        return int(numeros[0]) if numeros else None
    except (ValueError, TypeError):
        return None

def extraer_detalles_promocion(url_promocion, headers):
    """Visita la página de una promoción y extrae sus detalles."""
    try:
        print(f"  -> Analizando promoción: {url_promocion}", flush=True)
        response = requests.get(url_promocion, headers=headers, timeout=20)
        if not response.ok:
            return None # Si la página da error, la saltamos

        soup_promo = BeautifulSoup(response.text, 'html.parser')

        # --- Selectores para la página de detalle (pueden cambiar si la web se actualiza) ---
        nombre = soup_promo.find('h1').get_text(strip=True) if soup_promo.find('h1') else 'Nombre no encontrado'
        ubicacion_tag = soup_promo.find('div', class_='promotion-location-text')
        ubicacion = ubicacion_tag.get_text(strip=True).lower() if ubicacion_tag else ''

        precio_tag = soup_promo.find('p', class_='promotion-price')
        precio_texto = precio_tag.get_text(strip=True) if precio_tag else None
        
        habitaciones_tag = soup_promo.find('p', text=re.compile(r'dormitorio'))
        habitaciones_texto = habitaciones_tag.get_text(strip=True) if habitaciones_tag else None
        
        return {
            'nombre': nombre,
            'ubicacion': ubicacion,
            'precio': limpiar_y_convertir_precio(precio_texto),
            'habitaciones': limpiar_y_convertir_habitaciones(habitaciones_texto),
            'url': url_promocion
        }
    except Exception as e:
        print(f"    Error extrayendo detalles de {url_promocion}: {e}", flush=True)
        return None

# --- Función principal ---

def main():
    """Lógica principal del scraper: obtiene enlaces, visita cada uno y filtra."""
    URL_PRINCIPAL = "https://www.aedashomes.com/viviendas-obra-nueva"
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        print("PASO 1: Obteniendo todos los enlaces de las promociones...", flush=True)
        response = requests.get(URL_PRINCIPAL, headers=HEADERS, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Basado en tu captura, el selector correcto es 'a' con clase 'card-promo'
        enlaces_promociones = soup.select('a.card-promo')
        if not enlaces_promociones:
            enviar_mensaje_telegram("❌ No se encontraron enlaces de promociones en la página principal. Puede que la estructura de la web haya cambiado.")
            return

        urls_a_visitar = list(set([enlace['href'] for enlace in enlaces_promociones if enlace.has_attr('href')]))
        print(f"Se encontraron {len(urls_a_visitar)} promociones únicas.", flush=True)
        
        print("\nPASO 2: Extrayendo detalles y aplicando filtros...", flush=True)
        promociones_filtradas = []
        for url in urls_a_visitar:
            detalles = extraer_detalles_promocion(url, HEADERS)
            if not detalles:
                continue

            # --- APLICACIÓN DE FILTROS ---
            ubicacion_ok = any(loc in detalles['ubicacion'] for loc in LOCALIZACIONES_DESEADAS)
            precio_ok = detalles['precio'] is not None and detalles['precio'] <= PRECIO_MAXIMO
            habitaciones_ok = detalles['habitaciones'] is not None and detalles['habitaciones'] >= HABITACIONES_MINIMAS

            if ubicacion_ok and precio_ok and habitaciones_ok:
                print(f"    ¡MATCH! {detalles['nombre']} cumple los criterios.", flush=True)
                promociones_filtradas.append(detalles)

        print("\nPASO 3: Generando y enviando reporte final.", flush=True)
        if not promociones_filtradas:
            mensaje_final = f"✅ Scraper de AEDAS finalizado.\n\nNo se ha encontrado ninguna promoción que cumpla con tus filtros:\n- Ubicación: `{', '.join(LOCALIZACIONES_DESEADAS)}`\n- Precio Máx: `{PRECIO_MAXIMO}€`\n- Hab. Mín: `{HABITACIONES_MINIMAS}`"
        else:
            mensaje_final = f"📢 ¡Se han encontrado {len(promociones_filtradas)} promociones que cumplen tus filtros!\n"
            for promo in promociones_filtradas:
                mensaje_final += f"\n*{promo['nombre']}*\n"
                mensaje_final += f"📍 {promo['ubicacion'].title()}\n"
                mensaje_final += f"💶 Precio: {promo['precio']}€\n"
                mensaje_final += f"🛏️ Dorms: {promo['habitaciones']}\n"
                mensaje_final += f"🔗 [Ver más]({promo['url']})\n"
        
        enviar_mensaje_telegram(mensaje_final)

    except Exception as e:
        error_msg = f"❌ Ha ocurrido un error inesperado en el scraper: {e}"
        print(error_msg, flush=True)
        enviar_mensaje_telegram(error_msg)

# --- Punto de entrada del script ---
if __name__ == "__main__":
    main()

