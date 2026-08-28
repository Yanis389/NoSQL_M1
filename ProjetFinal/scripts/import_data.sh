#!/usr/bin/env bash
# import_data.sh — Télécharge les DVF 34 et les importe dans MongoDB
# Usage : bash scripts/import_data.sh
set -euo pipefail

DATA_URL="https://files.data.gouv.fr/geo-dvf/latest/csv/2024/departements/34.csv.gz"
CSV_GZ="/tmp/dvf_34_2024.csv.gz"
CONTAINER="projet-mongo"
DB="immo"
COL="mutations"

echo "📥 Téléchargement des données DVF 34..."
curl -L -o "$CSV_GZ" "$DATA_URL"

echo "📦 Décompression..."
gunzip -f "$CSV_GZ"

CSV="/tmp/dvf_34_2024.csv"
echo "🍃 Import dans MongoDB (collection ${DB}.${COL})..."
docker exec -i "$CONTAINER" mongoimport \
  --uri "mongodb://app_immo:immo_password34@localhost:27017/${DB}?authSource=${DB}" \
  --collection "$COL" \
  --type csv \
  --headerline \
  --ignoreBlanks \
  --file /dev/stdin < "$CSV"

echo "✅ Import terminé."
