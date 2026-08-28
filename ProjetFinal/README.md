# Observatoire Immobilier — Hérault (34)

Projet NoSQL M1 · Données **DVF** (Demandes de Valeurs Foncières) 2023-2024, département 34.  
Stack : **MongoDB 7** · **FastAPI** · **Nginx** · **Docker Compose**

---

## Démarrage rapide

```bash
# 1. Copier les variables d'environnement
cp .env.example .env          # puis éditez les mots de passe

# 2. Lancer les conteneurs
docker compose up -d

# 3. Importer les données brutes (DVF 34, ~70 000 lignes)
bash scripts/import_data.sh

# 4. Transformer : regrouper par mutation + créer communes_meta
docker exec -i projet-mongo mongosh \
  -u app_immo -p immo_password34 \
  --authenticationDatabase immo immo \
  < scripts/transform_data.js

# 5. Accéder à l'application
open http://localhost:3000        # Frontend
open http://localhost:8000/docs   # Swagger / OpenAPI
```

---

## Architecture

```
.
├── docker-compose.yml          # Orchestration (mongo, api, web/nginx)
├── .env.example                # Variables d'environnement (template)
├── api/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── main.py                 # API FastAPI — CRUD + 3 agrégations
├── web/
│   └── index.html              # Frontend HTML/JS (fetch API)
├── db/
│   └── 01-init-app-user.js     # Init MongoDB : utilisateur applicatif
├── scripts/
│   ├── import_data.sh          # Télécharge et importe le CSV DVF
│   └── transform_data.js       # Crée les collections ventes + communes_meta
└── rapport/
    └── captures/
        ├── 01_avant_index_nom_commune.json   # explain() COLLSCAN
        └── 02_apres_index_nom_commune.json   # explain() IXSCAN
```

---

## Modélisation des données

### Collection `mutations` — données brutes

Collection importée directement depuis le CSV DVF.  
**Problème** : une même mutation (vente) peut apparaître sur **plusieurs lignes** (une par lot cadastral). Ex : une maison avec garage génère 2 lignes avec le même `id_mutation`.

### Collection `ventes` — **imbrication**

Créée par `scripts/transform_data.js` via `$group` sur `id_mutation`.  
Un document = une mutation, avec un tableau **`lots` imbriqué** :

```json
{
  "_id": "2024-123456",
  "date_mutation": "2024-03-15",
  "valeur_fonciere": 250000,
  "nom_commune": "Montpellier",
  "code_postal": "34000",
  "location": { "type": "Point", "coordinates": [3.877, 43.611] },
  "lots": [
    { "surface_reelle_bati": 72, "type_local": "Maison", "nombre_pieces": 4 },
    { "surface_reelle_bati": 12, "type_local": "Garage", "nombre_pieces": null }
  ]
}
```

**Justification** : les lots n'ont pas d'existence indépendante, ils sont toujours consultés avec la mutation parente → **imbrication** appropriée (pas de référence séparée).

### Collection `communes_meta` — **référence**

340 documents, un par commune unique de l'Hérault.  
Contient des métadonnées complémentaires (`attractivite_touristique`).  
Liée à `ventes` via `nom_commune` (relation par **référence**).

```json
{ "nom_commune": "Montpellier", "attractivite_touristique": 9 }
```

**Justification** : les métadonnées de commune sont partagées entre des milliers de ventes et peuvent évoluer indépendamment → **référence** appropriée (évite la duplication).

---

## Index et performances

| Collection     | Index                                     | Type       | Justification                            |
|----------------|-------------------------------------------|------------|------------------------------------------|
| `ventes`       | `{ nom_commune: 1 }`                      | Simple     | Filtre et regroupement par commune       |
| `ventes`       | `{ nom_commune: 1, valeur_fonciere: -1 }` | Composé    | Tri par prix dans une commune            |
| `ventes`       | `{ location: "2dsphere" }` (sparse)       | Géospatial | Requêtes `$geoNear` sur coordonnées GPS  |
| `ventes`       | `{ "lots.type_local": 1 }`                | Sur tableau | Filtre sur le type de bien imbriqué     |
| `communes_meta`| `{ nom_commune: 1 }` (unique)             | Unique     | Accélère le `$lookup` entre collections  |

### Protocole de capture explain()

```bash
# 1. Démarrer SANS index
AUTO_INDEX=false docker compose up -d api
curl http://localhost:8000/agg/explain?commune=Montpellier
# → stages: ["COLLSCAN"], totalDocsExamined: 29565, ratio: 5.3x

# 2. Créer les index
curl -X POST http://localhost:8000/admin/index

# 3. Recapturer AVEC index
curl http://localhost:8000/agg/explain?commune=Montpellier
# → stages: ["FETCH", "IXSCAN"], totalDocsExamined: 5588, ratio: 1.0x
```

Voir les captures JSON dans `rapport/captures/`.

---

## Agrégations métier

### 1. `GET /agg/top-communes` — Top 10 communes les plus chères
- Calcule le prix au m² par vente (`valeur_fonciere / Σ surfaces lots`)
- Groupe par commune, filtre ≥ 10 ventes pour la fiabilité statistique
- **`$lookup`** vers `communes_meta` pour enrichir avec `attractivite_touristique`

### 2. `GET /agg/repartition-biens` — Répartition Maisons / Appartements
- **`$unwind`** sur le tableau imbriqué `lots`
- Filtre `type_local ∈ {Maison, Appartement}`
- Calcule count, valeur moyenne et pourcentage du marché

### 3. `GET /agg/geospatial` — Ventes géospatiales
- Opérateur **`$geoNear`** (requiert l'index `2dsphere`)
- Retourne les communes dans un rayon paramétrable autour d'un point GPS
- Paramètres : `lat`, `lng`, `distance_km`

---

## Accès aux services

| Service       | URL                         |
|---------------|-----------------------------|
| Frontend      | http://localhost:3000        |
| API REST      | http://localhost:8000        |
| Swagger/Docs  | http://localhost:8000/docs   |
| MongoDB       | mongodb://localhost:27017    |

---

## Réponses aux questions du sujet

**Q1 : Imbrication vs Référence — justifiez votre choix.**

- **Imbrication** (`lots` dans `ventes`) : les lots cadastraux n'ont aucun sens sans leur mutation parente. Ils sont toujours lus ensemble. L'imbrication évite une jointure et reflète la structure naturelle des données DVF.
- **Référence** (`communes_meta` séparée) : les métadonnées d'une commune sont partagées par des milliers de ventes. Les dupliquer en imbrication provoquerait une mise à jour coûteuse. La référence + `$lookup` est ici plus adaptée.

**Q2 : Comment avez-vous géré les anomalies du jeu de données ?**

1. **Mutations multi-lignes** : regroupement via `$group` sur `id_mutation` dans `transform_data.js`. Les 69 651 lignes brutes donnent 29 565 mutations uniques.
2. **Coordonnées GPS manquantes** : opérateur `$cond` dans l'agrégation pour ne créer le champ `location` que si `longitude` et `latitude` sont non-vides et convertibles en double. L'index `2dsphere` est créé avec `sparse: true` pour ignorer les documents sans `location`.
