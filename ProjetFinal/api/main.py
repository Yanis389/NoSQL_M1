"""Projet final NoSQL — Observatoire Immobilier Hérault (34)
Données DVF (Demandes de Valeurs Foncières) 2023-2024.

Collections :
  • mutations  : données brutes importées (1 ligne CSV = 1 document)
  • ventes     : données agrégées par id_mutation, avec tableau 'lots' imbriqué
  • communes_meta : métadonnées par commune (référence, $lookup)

Documentation interactive : http://localhost:8000/docs
"""

import os
from contextlib import asynccontextmanager
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pymongo import ASCENDING, DESCENDING, GEOSPHERE, MongoClient

# ── Configuration ──────────────────────────────────────────────────────────
MONGO_URI   = os.environ["MONGO_URI"]
MONGO_DB    = os.environ.get("MONGO_DB", "immo")
COLLECTION  = os.environ.get("COLLECTION", "ventes")
CORS_ORIGIN = os.environ.get("CORS_ORIGIN", "http://localhost:3000")
AUTO_INDEX  = os.environ.get("AUTO_INDEX", "true").lower() != "false"

# ── Client MongoDB ──────────────────────────────────────────────────────────
client = MongoClient(MONGO_URI)
db     = client[MONGO_DB]
col    = db["ventes"]           # collection principale
col_meta = db["communes_meta"]  # collection secondaire (référence)

# ── Index ───────────────────────────────────────────────────────────────────
def creer_index() -> list[str]:
    """Crée tous les index du projet."""
    noms = []
    noms.append(col.create_index([("nom_commune", ASCENDING)]))
    noms.append(col.create_index([("nom_commune", ASCENDING), ("valeur_fonciere", DESCENDING)]))
    noms.append(col.create_index([("location", GEOSPHERE)], sparse=True))
    noms.append(col.create_index([("lots.type_local", ASCENDING)]))
    noms.append(col_meta.create_index([("nom_commune", ASCENDING)], unique=True))
    return noms

# ── Lifespan ────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(_: "FastAPI"):
    if AUTO_INDEX:
        creer_index()
    yield
    client.close()

app = FastAPI(
    title="Observatoire Immobilier Hérault (34)",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# ── Helpers ─────────────────────────────────────────────────────────────────
def _oid(v: str) -> ObjectId:
    try:
        return ObjectId(v)
    except InvalidId:
        raise HTTPException(422, "Identifiant invalide")

# ── Health ───────────────────────────────────────────────────────────────────
@app.get("/health")
def health() -> dict[str, Any]:
    client.admin.command("ping")
    return {
        "status": "ok",
        "base": MONGO_DB,
        "collection": COLLECTION,
        "ventes": col.count_documents({}),
        "communes_meta": col_meta.count_documents({}),
    }

# ── CRUD ventes (Création, Lecture, Mise à jour, Suppression) ────────────────

@app.get("/ventes")
def lister_ventes(
    commune: str | None = None,
    type_bien: str | None = None,
    limite: int = Query(20, ge=1, le=100),
    page: int = Query(1, ge=1),
) -> dict[str, Any]:
    """Liste paginée des ventes avec filtres optionnels (Read)."""
    filtre: dict[str, Any] = {}
    if commune:
        filtre["nom_commune"] = {"$regex": commune, "$options": "i"}
    if type_bien:
        filtre["lots.type_local"] = type_bien

    curseur = col.find(filtre, {"_id": 0}).skip((page - 1) * limite).limit(limite)
    return {
        "page": page,
        "limite": limite,
        "total": col.count_documents(filtre),
        "resultats": list(curseur),
    }

@app.post("/ventes", status_code=201)
def creer_vente(vente: dict[str, Any]) -> dict[str, str]:
    """Création d'une nouvelle vente (Create)."""
    resultat = col.insert_one(vente)
    return {"_id": str(resultat.inserted_id)}

@app.put("/ventes/{id_vente}")
def modifier_vente(id_vente: str, mise_a_jour: dict[str, Any]) -> dict[str, int]:
    """Modification d'une vente existante (Update)."""
    resultat = col.update_one({"_id": _oid(id_vente)}, {"$set": mise_a_jour})
    if resultat.matched_count == 0:
        raise HTTPException(status_code=404, detail="Vente introuvable")
    return {"documents_modifies": resultat.modified_count}

@app.delete("/ventes/{id_vente}")
def supprimer_vente(id_vente: str) -> dict[str, int]:
    """Suppression d'une vente (Delete)."""
    resultat = col.delete_one({"_id": _oid(id_vente)})
    if resultat.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Vente introuvable")
    return {"documents_supprimes": resultat.deleted_count}

# ── BONUS B2 : REQUÊTE COUVERTE ─────────────────────────────────────────────
@app.get("/ventes/couverte")
def requete_couverte(commune: str = "Montpellier") -> list[dict[str, Any]]:
    """Bonus B2: Requête couverte par l'index (totalDocsExamined = 0)."""
    curseur = col.find(
        {"nom_commune": commune},
        {"_id": 0, "nom_commune": 1, "valeur_fonciere": 1}
    ).limit(5)
    return list(curseur)

# ── AGG 1 : Top 10 communes les plus chères au m² ────────────────────────────
@app.get("/agg/top-communes")
def top_communes(limite: int = Query(10, ge=1, le=50)) -> list[dict[str, Any]]:
    """Top communes les plus chères au m² (Corrigé avec filtres)."""
    pipeline = [
        {"$match": {
            "valeur_fonciere": {"$type": "number", "$gt": 0},
            "lots.type_local": {"$in": ["Maison", "Appartement"]}
        }},
        {"$addFields": {"surface_totale": {"$sum": "$lots.surface_reelle_bati"}}},
        {"$match": {"surface_totale": {"$gte": 9}}},
        {"$addFields": {"prix_m2": {"$divide": ["$valeur_fonciere", "$surface_totale"]}}},
        {"$group": {
            "_id": "$nom_commune",
            "prix_m2_moyen": {"$avg": "$prix_m2"},
            "nb_ventes": {"$sum": 1},
            "valeur_totale": {"$sum": "$valeur_fonciere"},
        }},
        {"$match": {"nb_ventes": {"$gte": 10}}},
        {"$lookup": {
            "from": "communes_meta",
            "localField": "_id",
            "foreignField": "nom_commune",
            "as": "meta",
        }},
        {"$unwind": {"path": "$meta", "preserveNullAndEmptyArrays": True}},
        {"$sort": {"prix_m2_moyen": -1}},
        {"$limit": limite},
        {"$project": {
            "_id": 0,
            "commune": "$_id",
            "prix_m2_moyen": {"$round": ["$prix_m2_moyen", 0]},
            "nb_ventes": 1,
            "valeur_totale": {"$round": ["$valeur_totale", 0]},
            "attractivite": "$meta.attractivite_touristique",
        }},
    ]
    return list(col.aggregate(pipeline))

# ── AGG 2 : Répartition Maisons vs Appartements ───────────────────────────────
@app.get("/agg/repartition-biens")
def repartition_biens() -> list[dict[str, Any]]:
    pipeline = [
        {"$unwind": "$lots"},
        {"$match": {"lots.type_local": {"$in": ["Maison", "Appartement"]}}},
        {"$group": {
            "_id": "$lots.type_local",
            "count": {"$sum": 1},
            "valeur_moyenne": {"$avg": "$valeur_fonciere"},
        }},
        {"$sort": {"count": -1}},
        {"$project": {
            "_id": 0,
            "type": "$_id",
            "count": 1,
            "valeur_moyenne": {"$round": ["$valeur_moyenne", 0]},
        }},
    ]
    result = list(col.aggregate(pipeline))
    total = sum(r["count"] for r in result)
    for r in result:
        r["pourcentage"] = round(r["count"] / total * 100, 1) if total else 0
    return result

# ── AGG 3 : Géospatial — ventes dans un rayon autour d'un point ───────────────
@app.get("/agg/geospatial")
def geospatial(
    lat: float = Query(43.6107, description="Latitude"),
    lng: float = Query(3.8767, description="Longitude"),
    distance_km: float = Query(5.0, description="Rayon en km"),
) -> list[dict[str, Any]]:
    pipeline = [
        {"$geoNear": {
            "near": {"type": "Point", "coordinates": [lng, lat]},
            "distanceField": "distance_m",
            "maxDistance": distance_km * 1000,
            "spherical": True,
        }},
        {"$group": {
            "_id": "$nom_commune",
            "nb_ventes": {"$sum": 1},
            "prix_moyen": {"$avg": "$valeur_fonciere"},
            "distance_min_m": {"$min": "$distance_m"},
        }},
        {"$sort": {"nb_ventes": -1}},
        {"$project": {
            "_id": 0,
            "commune": "$_id",
            "nb_ventes": 1,
            "prix_moyen": {"$round": ["$prix_moyen", 0]},
            "distance_min_km": {"$round": [{"$divide": ["$distance_min_m", 1000]}, 2]},
        }},
    ]
    return list(col.aggregate(pipeline))

# ── AGG 4 : Évolution mensuelle par commune ──────────────────────────────────
@app.get("/agg/evolution")
def evolution_prix_par_commune(limite: int = Query(50, ge=1, le=200)) -> list[dict[str, Any]]:
    """Évolution mensuelle du prix au m² classée par commune et par mois."""
    pipeline = [
        {"$match": {
            "valeur_fonciere": {"$type": "number", "$gt": 0},
            "lots.type_local": {"$in": ["Maison", "Appartement"]}
        }},
        {"$addFields": {"surface_totale": {"$sum": "$lots.surface_reelle_bati"}}},
        {"$match": {"surface_totale": {"$gte": 9}}},
        {"$addFields": {
            "prix_m2": {"$divide": ["$valeur_fonciere", "$surface_totale"]},
            "mois": {"$substr": ["$date_mutation", 0, 7]} # Extrait AAAA-MM
        }},
        {"$group": {
            "_id": {
                "commune": "$nom_commune",
                "mois": "$mois"
            },
            "prix_m2_moyen": {"$avg": "$prix_m2"},
            "nb_ventes": {"$sum": 1}
        }},
        {"$sort": {"_id.commune": 1, "_id.mois": 1}},
        {"$limit": limite},
        {"$project": {
            "_id": 0,
            "commune": "$_id.commune",
            "mois": "$_id.mois",
            "prix_m2_moyen": {"$round": ["$prix_m2_moyen", 0]},
            "nb_ventes": 1
        }}
    ]
    return list(col.aggregate(pipeline))

# ── Admin : index & explain ───────────────────────────────────────────────────
@app.post("/admin/index", status_code=201)
def creer_les_index() -> dict[str, Any]:
    return {"index_crees": creer_index()}

@app.delete("/admin/index")
def supprimer_les_index() -> dict[str, Any]:
    avant = [i for i in col.index_information() if i != "_id_"]
    col.drop_indexes()
    return {"index_supprimes": avant}

def _chaine_stages(stage: dict[str, Any]) -> list[str]:
    chaine = []
    while stage:
        chaine.append(stage["stage"])
        stage = stage.get("inputStage") or (stage.get("inputStages") or [None])[0]
    return chaine

@app.get("/agg/explain")
def expliquer(commune: str = "Montpellier") -> dict[str, Any]:
    plan = db.command(
        "explain",
        {"find": "ventes", "filter": {"nom_commune": commune}},
        verbosity="executionStats",
    )
    stats  = plan["executionStats"]
    stages = _chaine_stages(stats["executionStages"])
    nb     = stats["nReturned"]
    return {
        "stages": stages,
        "stage_racine": stages[0],
        "index_utilise": "IXSCAN" in stages,
        "totalDocsExamined": stats["totalDocsExamined"],
        "totalKeysExamined": stats["totalKeysExamined"],
        "nReturned": nb,
        "ratio_examines_sur_rendus": (
            round(stats["totalDocsExamined"] / nb, 1) if nb else None
        ),
        "executionTimeMillis": stats["executionTimeMillis"],
    }