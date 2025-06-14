#!/usr/bin/env python3
"""
Orquestador: ejecuta todos los scrapers y envía un único mensaje
"""

from scrapers import (
    aedas,
    viacelere,
    metrovacesa,
    atica,        
    urbania,# ← nuevo scraper
)
from utils import enviar_mensaje_telegram


def main() -> None:
    # ─── Lanza cada scraper ─────────────────────────────────────────────
    res_aedas       = aedas.scrape()
    res_viacelere   = viacelere.scrape()
    res_metrovacesa = metrovacesa.scrape()
    res_atica       = atica.scrape()
    res_urbania     = urbania.scrape()

    # ─── Traza de control en el log ─────────────────────────────────────
    print(f"[DEBUG] AEDAS        → {len(res_aedas)} promociones filtradas", flush=True)
    print(f"[DEBUG] VÍA CÉLERE   → {len(res_viacelere)} promociones filtradas", flush=True)
    print(f"[DEBUG] METROVACESA  → {len(res_metrovacesa)} promociones filtradas", flush=True)
    print(f"[DEBUG] ÁTICA        → {len(res_atica)} promociones filtradas", flush=True)
    print(f"[DEBUG] URBANIA        → {len(res_urbania)} promociones filtradas", flush=True)

    # ─── Une todos los resultados ───────────────────────────────────────
    resultados = res_aedas + res_viacelere + res_metrovacesa + res_atica + res_urbania

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
