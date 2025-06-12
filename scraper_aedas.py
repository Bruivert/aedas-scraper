def main():
    """Función principal que ejecuta el scraper."""
    # --- ¡AQUÍ ESTÁ EL CAMBIO! ---
    # Hemos actualizado a la nueva URL de promociones de AEDAS.
    URL_AEDAS = "https://www.aedashomes.com/viviendas-obra-nueva"
    
    # IMPORTANTE: Simulamos ser un navegador para evitar bloqueos básicos.
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        print(f"Iniciando scraping de: {URL_AEDAS}")
        # Hacemos la petición a la web de AEDAS
        response = requests.get(URL_AEDAS, headers=headers, timeout=30)
        response.raise_for_status() # Lanza un error si la página devuelve un código como 404, 500, etc.

        print("Página descargada con éxito. Analizando HTML...")
        soup = BeautifulSoup(response.text, 'html.parser')

        # --- ¡ATENCIÓN! ESTA ES LA PARTE QUE DEBES ADAPTAR ---
        # Debes inspeccionar la web de AEDAS para encontrar la etiqueta y clase correctas
        # que contienen cada promoción. Este es solo un EJEMPLO.
        # Haz clic derecho en una promoción en la web -> "Inspeccionar" para encontrarlo.
        # Por ejemplo, podría ser algo como: <article class="promotion-card">...</article>
        
        promociones_encontradas = soup.find_all('article', class_='promotion-card') # EJEMPLO, ¡ajústalo!

        if not promociones_encontradas:
            # Si no se encuentran promociones, envía un mensaje para saber que el script funcionó.
            mensaje = "✅ El scraper de AEDAS ha funcionado, pero no se han encontrado promociones con los selectores actuales. Revisa la clase del 'article' en la web."
            enviar_mensaje_telegram(mensaje)
        else:
            # Si encontramos promociones, creamos un mensaje con sus nombres
            lista_promociones = []
            for promo in promociones_encontradas:
                # DE NUEVO, EJEMPLO: busca la etiqueta del título dentro de la tarjeta de promoción
                titulo_tag = promo.find('h2', class_='promotion-card__title') 
                if titulo_tag:
                    lista_promociones.append(f"- {titulo_tag.get_text(strip=True)}")
            
            if lista_promociones:
                mensaje = "📢 ¡Nuevas promociones encontradas en AEDAS!\n\n" + "\n".join(lista_promociones)
            else:
                mensaje = "⚠️ Se encontraron tarjetas de promoción, pero no se pudo extraer el título. Revisa los selectores internos (como el 'h2')."

            enviar_mensaje_telegram(mensaje)

    except requests.exceptions.RequestException as e:
        # Si hay un error al descargar la web, notifícalo.
        error_msg = f"❌ Error al intentar acceder a la web de AEDAS: {e}"
        print(error_msg)
        enviar_mensaje_telegram(error_msg)
    except Exception as e:
        # Para cualquier otro error inesperado.
        error_msg = f"❌ Ha ocurrido un error inesperado en el scraper: {e}"
        print(error_msg)
        enviar_mensaje_telegram(error_msg)
