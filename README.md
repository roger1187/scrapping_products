# scrapping_products

Comparador diario de precios de productos de bebé: el precio más bajo entre tiendas de EE.UU. contra el de Lima,
con costo puesto en Lima, margen y semáforo. El resultado se publica como web para el celular y llegan avisos por Telegram.

## Setup en 10 líneas

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt && playwright install chromium
cp .env.example .env                                  # Windows: copy .env.example .env  → completa SERPAPI_KEY, TELEGRAM_*
python main.py --dry-run                              # tabla en consola, no escribe nada
python main.py && python build_site.py                # escribe data/ y genera site/
python -m http.server -d site 8000                    # abrir http://localhost:8000
pytest                                                # tests de la lógica
```

En GitHub: **Settings → Secrets and variables → Actions**, crea los secrets `SERPAPI_KEY`, `TELEGRAM_TOKEN` y `TELEGRAM_CHAT_ID`
(opcionales: `ML_CLIENT_ID`, `ML_CLIENT_SECRET`, `KEEPA_API_KEY`) y las variables `SITE_BASE_URL`, `SERPAPI_MAX_DIARIO` y `FACTOR_IMPORTACION`.
Después ejecuta el workflow **daily-prices** una vez a mano y activa **Settings → Pages → Deploy from branch → `gh-pages`**.
Desde ahí corre solo todos los días a las 07:00 (hora de Lima).

## Cómo funciona

- `products.yaml`: los productos. `precio_lima_manual` se usa **solo** si no hay ningún resultado en Lima, y en la web se marca como «referencia estimada».
- SerpAPI (Google Shopping) da 100 búsquedas al mes gratis. `SERPAPI_MAX_DIARIO` (por defecto 3, unas 90 al mes) limita cuántos productos se consultan cada día.
  Los productos rotan; para los demás se reutiliza el último precio conocido, que la web marca como «del dd-mm» (hasta 14 días de antigüedad).
- Fórmula: `costo = USD × TC × 1.25`, `venta = mínimo Lima × 0.92`, `margen % = (venta − costo) / venta`. VERDE ≥ 35 %, AMARILLO 20–35 %, ROJO < 20 %.
- Telegram avisa solo cuando un producto pasa a VERDE, cambia la tienda más barata o el precio en EE.UU. baja más de 15 % respecto de ayer.
- Sin GitHub Actions: `scripts/cron.sh` (Linux) o `scripts/run_daily.ps1` (Windows, con la instrucción del Programador de tareas en su encabezado).

`CLAUDE.md` es la especificación completa.
