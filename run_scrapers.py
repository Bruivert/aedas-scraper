#!/usr/bin/env python3
"""
Orquestador: llama a cada scraper, suma resultados y envía Telegram
"""

from scrapers import aedas, viacelere, metrovacesa
from utils import enviar_mensaje_telegram


def main() -> None:
    # ─── Lanza ambos scrapers ──────────────────────────────────────────────
    res_aedas     = aedas.scrape()
    res_viacelere = viacelere.scrape()
    res_metrovacesa = metrovacesa.scrape()

    # ─── Trazas para verlos en el log de GitHub Actions ───────────────────
    print(f"[DEBUG] AEDAS     → {len(res_aedas)} promociones filtradas", flush=True)
    print(f"[DEBUG] VÍA CÉLERE → {len(res_viacelere)} promociones filtradas", flush=True)
    print(f"[DEBUG] METROVACESA → {len(res_metrovacesa)} promociones filtradas", flush=True)
    # ─── Construye el mensaje a Telegram ──────────────────────────────────
    resultados = res_aedas + res_viacelere
    if resultados:
        mensaje = (
            f"📢 ¡{len(resultados)} promociones cumplen tus filtros! 🚀\n"
            + "".join(resultados)
        )
    else:
        mensaje = (
            "✅ Scrapers finalizados.\n\n"
            "No se encontró ninguna promoción nueva que cumpla tus filtros."
        )

    enviar_mensaje_telegram(mensaje)


if __name__ == "__main__":
    main()