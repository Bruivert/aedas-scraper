import requests
import os
import sys
import re
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# --- TUS FILTROS ---
LOCALIZACIONES_DESEADAS = ["mislata", "valencia", "quart de poblet", "paterna", "manises"]
PRECIO_MAXIMO = 270000
HABITACIONES_MINIMAS = 2

# --- Funciones auxiliares ---
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

def setup_driver():
    options = uc.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument('--disable-blink-features=AutomationControlled')
    return uc.Chrome(options=options, use_subprocess=True)

# --- SCRAPERS ---
def scrape_aedas(driver):
    print("\n--- Iniciando scraper de AEDAS (Modo Final) ---", flush=True)
    resultados = []
    try:
        url = "https://www.aedashomes.com/viviendas-obra-nueva?province=2509951"
        driver.get(url)
        try:
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))).click()
            print("  -> Banner de cookies de AEDAS aceptado.", flush=True)
        except TimeoutException:
            print("  -> Banner de cookies de AEDAS no encontrado.", flush=True)

        WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "div.card-promo-list")))
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        tarjetas = soup.select('div.card-promo-list')
        print(f"AEDAS: Se encontraron {len(tarjetas)} promociones.", flush=True)

        for tarjeta in tarjetas:
            # ... Lógica de extracción robusta ...
            nombre = tarjeta.find('h2', class_='card-promo-list__title').get_text(strip=True) if tarjeta.find('h2') else None
            ubicacion = tarjeta.find('p', class_='card-promo-list__location').get_text(strip=True).lower() if tarjeta.find('p', class_='card-promo-list__location') else None
            if nombre and ubicacion and any(loc in ubicacion for loc in LOCALIZACIONES_DESEADAS):
                 # ... (resto de filtros) ...
                 pass # Aquí iría el resto de tu lógica de filtros
    except Exception as e:
        print(f"  -> ERROR en el scraper de AEDAS: {e}", flush=True)
    return resultados

def scrape_viacelere(driver):
    print("\n--- Iniciando scraper de VÍA CÉLERE (Modo Final) ---", flush=True)
    # ... (código similar, pero simplificado para la explicación)
    return []

def main():
    driver = None
    todos_los_resultados = []
    try:
        driver = setup_driver()
        todos_los_resultados.extend(scrape_aedas(driver))
        # todos_los_resultados.extend(scrape_viacelere(driver)) # Desactivado temporalmente para aislar el problema
    except Exception as e:
        print(f"ERROR GENERAL: El navegador falló. Causa probable: Detección anti-bot. Error: {e}", flush=True)
    finally:
        if driver:
            driver.quit()
    
    if not todos_los_resultados:
        mensaje_final = f"✅ Scrapers finalizados.\n\nNo se ha encontrado ninguna promoción nueva que cumpla tus filtros."
    else:
        mensaje_final = f"📢 ¡Se han encontrado {len(todos_los_resultados)} promociones!\n" + "".join(todos_los_resultados)
    enviar_mensaje_telegram(mensaje_final)

if __name__ == "__main__":
    main()

