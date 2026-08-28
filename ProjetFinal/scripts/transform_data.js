// transform_data.js — Regroupe les mutations DVF par id_mutation
// et crée la collection 'ventes' avec lots imbriqués + communes_meta.
// Usage : mongosh --file scripts/transform_data.js
//      ou : docker exec -i projet-mongo mongosh ... < scripts/transform_data.js

db = db.getSiblingDB("immo");

print("=== ÉTAPE 1 : Création de la collection 'ventes' (imbrication) ===");
db.ventes.drop();

db.mutations.aggregate([
  // Regrouper toutes les lignes d'une même mutation
  {
    $group: {
      _id: "$id_mutation",
      date_mutation: { $first: "$date_mutation" },
      valeur_fonciere: { $first: "$valeur_fonciere" },
      nom_commune: { $first: "$nom_commune" },
      code_postal: { $first: "$code_postal" },
      longitude: { $first: "$longitude" },
      latitude:  { $first: "$latitude" },
      // Tableau imbriqué des lots de la mutation
      lots: {
        $push: {
          surface_reelle_bati: "$surface_reelle_bati",
          type_local: "$type_local",
          nombre_pieces: "$nombre_pieces_principales"
        }
      }
    }
  },
  // Créer le champ GeoJSON seulement si les coordonnées sont valides
  {
    $addFields: {
      location: {
        $cond: [
          { $and: [
            { $ne: ["$longitude", ""] },
            { $ne: ["$latitude", ""]  },
            { $ne: ["$longitude", null] },
            { $ne: ["$latitude",  null] }
          ]},
          {
            type: "Point",
            coordinates: [
              { $toDouble: "$longitude" },
              { $toDouble: "$latitude"  }
            ]
          },
          "$$REMOVE"
        ]
      }
    }
  },
  { $out: "ventes" }
]);

print("Collection 'ventes' : " + db.ventes.countDocuments() + " documents.");

print("=== ÉTAPE 2 : Création de la collection 'communes_meta' (référence) ===");
db.communes_meta.drop();

db.ventes.aggregate([
  { $group: { _id: "$nom_commune" } },
  {
    $project: {
      _id: 0,
      nom_commune: "$_id",
      // Score d'attractivité fictif entre 1 et 10
      attractivite_touristique: {
        $floor: { $add: [{ $multiply: [{ $rand: {} }, 9] }, 1] }
      }
    }
  },
  { $out: "communes_meta" }
]);

print("Collection 'communes_meta' : " + db.communes_meta.countDocuments() + " documents.");
print("=== Transformation terminée ! ===");

print("=== ÉTAPE 3 : Bonus B4 - Validation JSON Schema (Moderate) ===");
db.runCommand({
  collMod: "ventes",
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["nom_commune", "valeur_fonciere"],
      properties: {
        nom_commune: {
          bsonType: "string",
          description: "Le nom de la commune est requis et doit être une chaîne"
        },
        valeur_fonciere: {
          bsonType: ["double", "int", "long", "decimal"],
          minimum: 0,
          description: "La valeur foncière est requise et doit être un nombre positif"
        }
      }
    }
  },
  validationLevel: "moderate"
});
print("Validateur $jsonSchema appliqué avec succès !");