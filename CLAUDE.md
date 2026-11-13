# baby-price-scraper

## Objetivo
Cada mañana, para cada producto de bebé de `products.yaml`, encontrar el PRECIO MÁS BAJO entre TODAS las tiendas
de EE.UU. configuradas (no solo Amazon), compararlo contra el precio en Lima (Perú), calcular costo puesto en Lima
y margen, y publicar el resultado en una web estática que el dueño abre desde el celular. Avisar por Telegram
cuando un producto entra en VERDE o cuando cambia la tienda ganadora.

## Principio: ninguna tienda es la favorita
Para cada producto se consultan todas las fuentes USA disponibles y se guarda la oferta más barata con su tienda y URL.
Si hoy Walmart está más barato que Amazon, el ganador es Walmart y la web muestra "Comprar en Walmart" con el link.
Se guarda también el ranking completo (todas las tiendas con precio) para auditar.

## Estado actual del código (punto de partida)
Ya existe y funciona como base:
- `main.py` recorre `USA_SOURCES` y `LIMA_SOURCES`, elige la oferta USA más barata y escribe `data/latest.json`
  y `data/history/YYYY-MM-DD.json`.
- `scraper/sources/usa/amazon.py` (scraping HTML básico) y `scraper/sources/lima/mercadolibre.py` (API pública).
- `scraper/compare.py`, `scraper/fx.py`, `scraper/notify.py`, `scraper/models.py`.
Falta todo lo demás de este documento. Este CLAUDE.md manda sobre el código base: si algo no coincide, se corrige el código.

## Fuentes USA (módulos en scraper/sources/usa/, cada uno expone get_offers(query, marca) -> list[Offer])
1. google_shopping.py  AGREGADOR PRINCIPAL. SerpAPI (engine=google_shopping, gl=us, hl=en) si existe SERPAPI_KEY
   (plan gratis 100 búsquedas/mes; alternativas: ScraperAPI, Oxylabs). Devuelve precios de decenas de tiendas de golpe
   (Amazon, Walmart, Target, Kohl's, Macy's, Nordstrom, Zappos, sitio de la marca...). Normalizar nombre de tienda.
2. amazon.py  scraping HTML directo (ya existe versión base); con KEEPA_API_KEY usar Keepa para precio actual + histórico.
3. walmart.py  scraping de https://www.walmart.com/search?q= (JSON embebido en __NEXT_DATA__).
4. target.py  API Redsky que usa el sitio (key en el HTML) o Playwright.
5. brand_site.py  si el producto tiene brand_url en el YAML, abrir esa URL con Playwright y leer el precio
   (Kyte Baby, Little Sleepies, Posh Peanut, Skip Hop, Ergobaby, Hatch, Solly Baby, Freshly Picked). Las marcas suelen
   tener el mejor precio en sus propias ventas. Respetar robots.txt y 1 request/seg.
6. slickdeals.py (opcional)  buscar la marca para detectar cupones activos y anotarlos como nota.

Cada módulo nuevo se registra en la lista `USA_SOURCES` de `main.py`; no hay que tocar nada más.

Relevancia: descartar ofertas cuyo título no contenga la marca (case-insensitive, sin apóstrofes) y las "used"/"renewed".
Si el producto tiene size o pack en el YAML, exigir que el título lo contenga.
Empate de precio: gana la que tenga envío gratis; luego orden de confianza marca > Amazon > Walmart > Target > resto.

## Fuentes Lima (módulos en scraper/sources/lima/)
- mercadolibre.py  API pública https://api.mercadolibre.com/sites/MPE/search?q=  (ya existe; si la API pide token,
  usar OAuth de aplicación con ML_CLIENT_ID / ML_CLIENT_SECRET o caer a scraping de listado.mercadolibre.com.pe)
- falabella.py, ripley.py, oechsle.py  Playwright headless; 5 primeros resultados; screenshot en debug/ si falla el selector.
- precio_lima_manual del YAML se usa como piso si no hay resultados.

## Regla de negocio
- tipo_cambio: GET https://api.apis.net.pe/v1/tipo-cambio-sunat (campo venta); fallback 3.80
- costo_lima_pen = mejor_precio_usa_usd * tipo_cambio * FACTOR_IMPORTACION (default 1.25)
- venta_objetivo_pen = min(precios_lima) * 0.92
- margen_pen = venta_objetivo_pen - costo_lima_pen ; margen_pct = margen_pen / venta_objetivo_pen
- estado: VERDE >= 35 %, AMARILLO 20-35 %, ROJO < 20 %, SIN DATOS si falta un lado
- Guardar por producto: tienda_ganadora, url_ganadora, ranking_tiendas, precio_usa_ayer, delta_pct_vs_ayer

## Salida: WEB, no Google Sheets
- data/latest.json  resultado de hoy; data/history/YYYY-MM-DD.json  un archivo por día
- site/  web estática generada con Jinja2 desde data/:
  - index.html: tabla ordenada por margen desc, semáforo por color, columnas Producto, Marca, Mejor precio USA, Tienda,
    botón Comprar (link), Costo Lima, Ref. Lima, Venta objetivo, Margen S/, Margen %, Cambio vs ayer.
    Mobile-first (se lee en el celular), filtro por estado, buscador, fecha y tipo de cambio en el header.
  - producto/<id>.html: ranking de tiendas de hoy + línea del mejor precio USA últimos 30 días (Chart.js por CDN).
- Publicación: GitHub Pages desde site/ (rama gh-pages, gratis). Alternativa Vercel/Netlify. SITE_BASE_URL configurable.
- Telegram: mensaje diario corto con los VERDES, cambios de tienda ganadora y link a la web.

## Automatización diaria (obligatoria)
- .github/workflows/daily.yml: cron "0 12 * * *" (07:00 Lima) + workflow_dispatch. Pasos: checkout, python 3.12,
  pip install, playwright install chromium, python main.py, python build_site.py, deploy de site/ a gh-pages
  (peaceiris/actions-gh-pages), commit de data/ para conservar historial. El workflow base ya existe; completarlo.
- Si el dueño prefiere servidor propio o su PC con Windows: incluir scripts/cron.sh (Linux) y scripts/run_daily.ps1
  + instrucción de Programador de tareas de Windows para las 07:00.
- Timeout del job 25 min. Si una fuente falla, loguear y seguir; nunca abortar la corrida completa.

## Estructura
    products.yaml
    main.py            orquesta: fx -> fuentes USA -> fuentes Lima -> compare -> data/
    build_site.py      genera site/ desde data/            (por crear)
    scraper/fx.py  scraper/models.py  scraper/compare.py  scraper/notify.py
    scraper/sources/usa/{google_shopping,amazon,walmart,target,brand_site,slickdeals}.py
    scraper/sources/lima/{mercadolibre,falabella,ripley,oechsle}.py
    templates/{index.html,producto.html}                   (por crear)
    data/  site/  tests/  debug/
    .github/workflows/daily.yml

## Tareas para Claude Code (en orden)
1. Correr `python main.py --dry-run`, arreglar lo que falle en las fuentes base (Amazon, Mercado Libre).
2. Implementar google_shopping.py (SerpAPI), walmart.py, target.py, brand_site.py y registrarlos en USA_SOURCES.
3. Implementar fuentes Lima con Playwright (falabella, ripley, oechsle) y registrarlas en LIMA_SOURCES.
4. build_site.py + templates mobile-first; verificar en viewport 390 px.
5. Completar el workflow diario con deploy a GitHub Pages y commit de data/.
6. Tests pytest con fixtures guardados; test de que Carter's sale ROJO y Skip Hop/Kyte VERDE.
7. Telegram solo cuando un producto pasa a VERDE, cambia la tienda ganadora o el mejor precio USA baja más de 15 % vs ayer.
8. README con setup en 10 líneas.

## Comandos
- pip install -r requirements.txt && playwright install chromium
- python main.py --dry-run            tabla en consola, no escribe
- python main.py && python build_site.py && python -m http.server -d site 8000   ver la web local
- pytest

## Variables de entorno (.env local / GitHub Secrets) — nunca commitear .env
SERPAPI_KEY (recomendado), KEEPA_API_KEY (opcional), TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, FACTOR_IMPORTACION (opcional), SITE_BASE_URL
