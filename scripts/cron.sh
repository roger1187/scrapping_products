#!/usr/bin/env bash
# Corrida diaria en un servidor Linux propio. Instalar con `crontab -e`:
#   CRON_TZ=America/Lima
#   0 7 * * * /ruta/a/scrapping_products/scripts/cron.sh
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p logs
LOG="logs/$(date +%F).log"
PY=python3
[ -x .venv/bin/python ] && PY=.venv/bin/python
{
  echo "=== $(date) ==="
  "$PY" main.py
  "$PY" build_site.py
} >>"$LOG" 2>&1
