# scrapping_products

Comparador diario de precios de productos de bebé: mejor precio entre tiendas de EE.UU. contra Lima, con margen estimado.

## Cómo empezar

1. Descomprime esta carpeta en `C:\Users\RACACERE\scrapping_products`.
2. Abre una terminal en esa carpeta y ejecuta `claude` (Claude Code).
3. Escribe: `Lee CLAUDE.md y ejecuta las tareas 1 a 8 en orden.`

## Probar a mano

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python main.py --dry-run
```

`CLAUDE.md` es la especificación completa: tiendas, fórmula de margen, web y automatización diaria.
