#!/usr/bin/env python3
from scrapers import aedas, viacelere
from utils import enviar_mensaje_telegram

def main():
    resultados = aedas.scrape() + viacelere.scrape()
    if resultados:
        msg = f"📢 {len(resultados)} promociones cumplen tus filtros:\n" + "".join(resultados)
    else:
        msg = (
            "✅ Scrapers finalizados.\n\n"
            "No se encontró ninguna promoción nueva que cumpla tus filtros."
        )
    enviar_mensaje_telegram(msg)

if __name__ == "__main__":
    main()