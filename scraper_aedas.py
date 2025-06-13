import requests
import os
import sys
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

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

def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    return webdriver.Chrome(options=options)

# --- SCRAPERS ACTUALIZADOS Y CORREGIDOS ---

def scrape_aedas(driver):
    print("\n--- Iniciando scraper de AEDAS con Selenium ---", flush=True)
    resultados = []
    try:
        url = "https://www.aedashomes.com/viviendas-obra-nueva?province=2509951"
        driver.get(url)
        
        # --- ¡AQUÍ ESTÁ LA CORRECCIÓN PARA AEDAS! ---
        # Esperamos al banner de cookies y lo aceptamos si aparece.
        try:
            cookie_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler")))
            cookie_button.click()
            print("  -> Banner de cookies de AEDAS aceptado.", flush=True)
        except TimeoutException:
            print("  -> Banner de cookies de AEDAS no encontrado, continuamos.", flush=True)

        # Ahora esperamos a que las promociones carguen
        WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "div.card-promo-list")))
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
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

def scrape_viacelere(driver):
    print("\n--- Iniciando scraper de VÍA CÉLERE con Selenium ---", flush=True)
    resultados = []
    try:
        url = "https://www.viacelere.com/promociones?provincia_id=46"
        driver.get(url)
        
        # --- ¡AQUÍ ESTÁ LA CORRECCIÓN PARA VÍA CÉLERE! ---
        # También intentamos aceptar las cookies por si acaso.
        try:
            cookie_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler")))
            cookie_button.click()
            print("  -> Banner de cookies de VÍA CÉLERE aceptado.", flush=True)
        except TimeoutException:
            print("  -> Banner de cookies de VÍA CÉLERE no encontrado, continuamos.", flush=True)

        WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "article.card-promotion")))
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        tarjetas = soup.select('article.card-promotion')
        print(f"VÍA CÉLERE: Se encontraron {len(tarjetas)} promociones.", flush=True)

        for tarjeta in tarjetas:
            nombre = tarjeta.select_one('h2.card-promotion__title').get_text(strip=True) if tarjeta.select_one('h2') else "SIN NOMBRE"
            url_promo = tarjeta.find('a', class_='card-promotion__link')['href'] if tarjeta.find('a', class_='card-promotion__link') else "SIN URL"
            status = tarjeta.select_one('span.card-promotion__tag').get_text(strip=True) if tarjeta.select_one('span.card-promotion__tag') else "SIN ESTADO"
            ubicacion = tarjeta.select_one('p.card-promotion__location').get_text(strip=True).lower() if tarjeta.select_one('p.card-promotion__location') else "SIN UBICACIÓN"
            precio_texto = tarjeta.select_one('p.card-promotion__price').get_text(strip=True) if tarjeta.select_one('p.card-promotion__price') else None
            habitaciones_texto = tarjeta.select_one('p.card-promotion__typology').get_text(strip=True) if tarjeta.select_one('p.card-promotion__typology') else None
            
            # Línea de depuración mejorada para ver todos los datos
            print(f"  -> Crudo Vía Célere: N='{nombre}', U='{ubicacion}', S='{status}', H='{habitaciones_texto}', P='{precio_texto}'", flush=True)
            
            if any(loc in ubicacion for loc in LOCALIZACIONES_DESEADAS):
                if 'Próximamente' in status:
                    resultados.append(f"\n*{nombre} (Vía Célere - Próximamente)*\n📍 {ubicacion.title()}\n🔗 [Ver promoción]({url_promo})")
                elif 'En comercialización' in status:
                    precio = limpiar_y_convertir_a_numero(precio_texto)
                    habitaciones = limpiar_y_convertir_a_numero(habitaciones_texto)
                    if all([precio, habitaciones]) and precio <= PRECIO_MAXIMO and habitaciones >= HABITACIONES_MINIMAS:
                        resultados.append(f"\n*{nombre} (Vía Célere)*\n📍 {ubicacion.title()}\n💶 Desde: {precio:,}€\n🛏️ Dorms: {habitaciones}\n🔗 [Ver promoción]({url_promo})".replace(",","."))
    except Exception as e:
        print(f"  -> ERROR en el scraper de VÍA CÉLERE: {e}", flush=True)
    return resultados

# --- Función Principal ---
def main():
    driver = setup_driver()
    todos_los_resultados = []
    try:
        todos_los_resultados.extend(scrape_aedas(driver))
        todos_los_resultados.extend(scrape_viacelere(driver))
    finally:
        driver.quit() # Aseguramos que el navegador se cierre siempre, incluso si hay errores

    if not todos_los_resultados:
        mensaje_final = f"✅ Scrapers finalizados.\n\nNo se ha encontrado ninguna promoción nueva que cumpla tus filtros en AEDAS o Vía Célere."
    else:
        mensaje_final = f"📢 ¡Se han encontrado {len(todos_los_resultados)} promociones que cumplen tus filtros!\n"
        mensaje_final += "".join(todos_los_resultados)
        
    enviar_mensaje_telegram(mensaje_final)

if __name__ == "__main__":
    main()
