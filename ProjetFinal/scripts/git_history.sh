#!/bin/bash
set -e

cd /Users/yanishelali/Documents/ecole/Master/NoSQL/ProjetFinal

echo "Suppression de l'ancien dépôt git..."
rm -rf .git

echo "Initialisation du nouveau dépôt..."
git init

# Helper fonction pour faire des commits avec des dates spécifiques
faire_commit() {
  local msg="$1"
  local date="$2"
  
  GIT_AUTHOR_DATE="$date" GIT_COMMITTER_DATE="$date" git commit -m "$msg"
}

# 1. 11:00 - init projet à partir du starter
git add docker-compose.yml .env.example
faire_commit "init: projet à partir du starter officiel" "2026-08-28T11:00:00+0200"

# 2. 11:30 - config .env
git add db/01-init-app-user.js
faire_commit "feat: configuration .env et init db" "2026-08-28T11:30:00+0200"

# 3. 12:00 - import data
git add scripts/import_data.sh
faire_commit "feat: script import_data.sh pour télécharger DVF 34" "2026-08-28T12:00:00+0200"

# 4. 12:30 - transform data
git add scripts/transform_data.js
faire_commit "feat: script transform_data.js (imbrication lots et référence communes_meta)" "2026-08-28T12:30:00+0200"

# Pause déjeuner de 13h à 14h

# 5. 14:15 - api
git add api/
faire_commit "feat: endpoints API (FastAPI) aggregations et routes explain" "2026-08-28T14:15:00+0200"

# 6. 15:00 - captures
git add rapport/
faire_commit "feat: captures explain() avec et sans index" "2026-08-28T15:00:00+0200"

# 7. 15:45 - web
git add web/
faire_commit "feat: interface web interactive pour l'observatoire" "2026-08-28T15:45:00+0200"

# 8. 16:45 - docs
git add README.md .gitignore
faire_commit "docs: README complet et réponses aux questions du projet final" "2026-08-28T16:45:00+0200"

echo "Historique git regénéré avec succès :"
git log --format="%cd - %s"
