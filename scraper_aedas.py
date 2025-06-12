import requests
import os
import sys
from bs4 import BeautifulSoup

def depurar_secrets():
    """Imprime el estado de los secrets para depuración en GitHub Actions."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    print("--- INICIO DEPURACIÓN DE SECRETS ---", flush=True)
    if token and "..." not in token: # Comprueba si el token existe y parece real
        print("✅ TELEGRAM_BOT_TOKEN: Leído correctamente.", flush=True)
    else:
        print("❌ TELEGRAM_BOT_TOKEN: NO ENCONTRADO O VACÍO.", flush=True)

    if chat_id:
        print(f"✅ TELEGRAM_CHAT_ID: Leído correctamente (valor: {chat_id[:2]}...)", flush=True)
    else:
        print("❌ TELEGRAM_CHAT_ID: NO ENCONTRADO O VACÍO.", flush=True)
    print("--- FIN DEPURACIÓN ---", flush=True)

    # Si falta alguno, el script no puede continuar.
    if not token or not chat_id:
        print("Error crítico: Faltan los secrets. El script no puede continuar.", flush=True)
        sys.exit(1) # Salir con error para que la Action falle y te des cuenta.

def enviar_mensaje_telegram(texto):
    """Envía 'texto' a tu chat/canal de Telegram."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": texto, "parse_mode": "Markdown"}

    try:
        response = requests.post(url, data=payload, timeout=15)
        response.raise_for_status()
        print("Mensaje enviado a Telegram con éxito.", flush=True)
    except requests.exceptions.RequestException as e:
        print(f"Error al enviar el mensaje a Telegram: {e}", flush=True)
        # No salimos con sys.exit aquí para que el script pueda continuar si solo falla el envío
        
def main():
    """Función principal que ejecuta el scraper."""
    URL_AEDAS = "https://www.aedashomes.com/viviendas-obra-nueva"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        print(f"Iniciando scraping de: {URL_AEDAS}", flush=True)
        response = requests.get(URL_AEDAS, headers=headers, timeout=30)
        response.raise_for_status()

        print("Página descargada con éxito. Analizando HTML...", flush=True)
        soup = BeautifulSoup(response.text, 'html.parser')

        # AJUSTA ESTE SELECTOR SI ES NECESARIO
        promociones_encontradas = soup.find_all('article', class_='promotion-card')

        if not promociones_encontradas:
            mensaje = "✅ El scraper de AEDAS ha funcionado, pero no se han encontrado promociones con los selectores actuales."
            enviar_mensaje_telegram(mensaje)
        else:
            lista_titulos = [promo.find('h2').get_text(strip=True) for promo in promociones_encontradas if promo.find('h2')]
            if lista_titulos:
                mensaje = "📢 ¡Promociones encontradas en AEDAS!\n\n- " + "\n- ".join(lista_titulos)
            else:
                mensaje = "⚠️ Se encontraron tarjetas de promoción, pero no se pudo extraer el título. Revisa los selectores."
            enviar_mensaje_telegram(mensaje)

    except requests.exceptions.RequestException as e:
        error_msg = f"❌ Error al acceder a la web de AEDAS: {e}"
        print(error_msg, flush=True)
        enviar_mensaje_telegram(error_msg)
    except Exception as e:
        error_msg = f"❌ Error inesperado en el scraper: {e}"
        print(error_msg, flush=True)
        enviar_mensaje_telegram(error_msg)

# --- Punto de entrada para ejecutar el script ---
if __name__ == "__main__":
    depurar_secrets() # Primero, depuramos los secrets
    main()            # Si todo está bien, ejecutamos el scraper
