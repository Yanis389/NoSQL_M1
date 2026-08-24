# Compte-rendu TP Jour 1 : NYC Restaurants

**Nom :** Yanis HELALI  
**Formation :** Master 1 Data IA - IPSSI  
**Module :** Conception et intégration de bases de données NoSQL  

---

## Partie 1 — Lecture & opérateurs

### Q1. Nombre total de restaurants
* **Commande :** `db.restaurants.countDocuments({})`
* **Résultat :** `25359`

### Q2. Nombre de types de cuisine distincts
* **Commande :** `db.restaurants.distinct("cuisine").length`
* **Résultat :** `85`

### Q3. Restaurants dans l'arrondissement Brooklyn
* **Commande :** `db.restaurants.countDocuments({ borough: "Brooklyn" })`
* **Résultat :** `6086`

### Q4. Restaurants de cuisine French (exactement)
* **Commande :** `db.restaurants.countDocuments({ cuisine: "French" })`
* **Résultat :** `344`

### Q5. Restaurants à Manhattan ET de cuisine Italian
* **Commande :** `db.restaurants.countDocuments({ borough: "Manhattan", cuisine: "Italian" })`
* **Résultat :** `621`

### Q6. Restaurants dans le Bronx ET cuisine Chinese
* **Commande :** `db.restaurants.countDocuments({ borough: "Bronx", cuisine: "Chinese" })`
* **Résultat :** `323`

### Q7. Restaurants avec le nom exact "Subway" et 3 premiers éléments
* **Commande :** `db.restaurants.countDocuments({ name: "Subway" })` -> `421`
* **Affichage des 3 premiers :** `db.restaurants.find({ name: "Subway" }, { name: 1, borough: 1, _id: 0 }).limit(3)`
* **Résultat :**json
[
  { "borough": "Manhattan", "name": "Subway" },
  { "borough": "Queens", "name": "Subway" },
  { "borough": "Manhattan", "name": "Subway" }
]


### Q8. Cuisine parmi Japanese, Korean, Thai, Indian ($in)
* **Commande :** `db.restaurants.countDocuments({ cuisine: { $in: ["Japanese", "Korean", "Thai", "Indian"] } })`
* **Résultat :** `1623`

### Q9. Recherche par regex sur "BBQ" et "House"
* **(a) Sensible à la casse :** `db.restaurants.countDocuments({ name: /BBQ/ })` -> `0`
* **(b) Insensible à la casse :** `db.restaurants.countDocuments({ name: /BBQ/i })` -> `73`
* **(c) Explication de l'écart :** La différence de 73 documents vient du fait que les restaurants sont écrits avec une casse mixte (ex: `"Dallas Bbq"`, `"Virgil'S Bbq"`). 
* **(d) Cas de "House" :** 
  * `db.restaurants.countDocuments({ name: /House/ })` -> `503`
  * `db.restaurants.countDocuments({ name: /House/i })` -> `503`
  * *Raison :* Dans ce jeu de données, tous les mots "House" sont uniformément écrits avec un H majuscule et le reste en minuscules, d'où l'absence d'écart.
* **(e) Recommandation de production :** L'utilisation de regex avec l'option `i` empêche l'utilisation des index classiques (B-Tree) et force un balayage complet (COLLSCAN). Pour optimiser, il faut créer un index de type texte (`Text Index`) ou stocker un champ normalisé en minuscules lors de l'insertion.

### Q10. Code postal "10462"
* **Commande :** `db.restaurants.countDocuments({ "address.zipcode": "10462" })`
* **Résultat :** `150`

### Q11. Restaurant avec l'ID "30075445"
* **Commande :** `db.restaurants.find({ restaurant_id: "30075445" }, { name: 1, _id: 0 })`
* **Résultat :** `Morris Park Bake Shop`

---

## Partie 2 — Tableaux & sous-documents

### Q12. Au moins une note > 50
* **Commande :** `db.restaurants.countDocuments({ "grades.score": { $gt: 50 } })`
* **Résultat :** `349`

### Q13. Restaurants mal notés
* **(a) Grade "C" dans l'historique :** `db.restaurants.countDocuments({ "grades.grade": "C" })` -> `2708`
* **(b) Première entrée égale à "C" :** `db.restaurants.countDocuments({ "grades.0.grade": "C" })` -> `220`
* **(c) Analyse :** Le tableau `grades` classe les inspections de la plus récente (indice 0) à la plus ancienne. L'écart de 2488 documents s'explique par le fait que beaucoup d'établissements ont eu un "C" dans le passé mais se sont améliorés. La requête (b) est donc la seule qui reflète l'état actuel.

### Q14. Tableau d'inspections vide
* **Commande :** `db.restaurants.countDocuments({ grades: { $size: 0 } })`
* **Résultat :** `738`
* **Explication métier :** Ce sont probablement des établissements nouvellement immatriculés qui n'ont pas encore reçu la visite des services sanitaires.

### Q15. Au moins 6 notes
* **Commande :** `db.restaurants.countDocuments({ "grades.5": { $exists: true } })`
* **Résultat :** `3864`

### Q16. Dernière note égale à "A"
* **Commande :** `db.restaurants.countDocuments({ "grades.0.grade": "A" })`
* **Résultat :** `20687`

### Q17. L'importance de $elemMatch
* **(a) Sans $elemMatch :** `db.restaurants.countDocuments({ "grades.grade": "B", "grades.score": { $gt: 20 } })` -> `4908`
* **(b) Avec $elemMatch :** `db.restaurants.countDocuments({ grades: { $elemMatch: { grade: "B", score: { $gt: 20 } } } })` -> `4280`
* **(c) Pourquoi l'utiliser :** La première requête valide le document si une inspection "x" a eu un B et une inspection "y" a eu >20. `$elemMatch` force la condition : le grade B ET le score >20 doivent obligatoirement provenir du même objet d'inspection.

### Q18. Anomalies de notes
* **(a) Scores négatifs :** `db.restaurants.countDocuments({ "grades.score": { $lt: 0 } })` -> `13`
* **(b) Impact sur la moyenne :**
  * Moyenne globale : `11.4348`
  * Moyenne sans les anomalies : `11.4365`
* **(c) Décision :** L'écart mathématique est infime (~0.015%), mais d'un point de vue métier et gouvernance, un score négatif est une aberration. Il faudrait purger ou corriger ces 13 entrées.

### Q19. Score le plus élevé
* **Commande :** `db.restaurants.find({}, { name: 1, "grades.score": 1, _id: 0 }).sort({ "grades.score": -1 }).limit(1)`
* **Résultat :** `Murals On 54/Randolphs'S` (Score : 131)

---

## Partie 3 — Création & mise à jour

### Q20. Insertion (CREATE)
* **Commande exécutée :**
db.restaurants.insertOne({
  name: "YH Bistro",
  borough: "Montpellier",
  cuisine: "French",
  address: { coord: [3.8767, 43.6108] },
  grades: [{ grade: "A", score: 7, date: new Date() }]
})

### Q21. Ajout d'une note (Push)
* **Cible :** `restaurant_id: "30075445"`
* **Commande :** `db.restaurants.updateOne({ restaurant_id: "30075445" }, { $push: { grades: { grade: "A", score: 3, date: new Date() } } })`
* **Résultat :** Le nombre de notes passe de 5 à 6.

### Q22. Marquer le risque
* **Commande :** `db.restaurants.updateMany({ "grades.score": { $gt: 50 } }, { $set: { risque: "eleve" } })`
* **Impact :** 349 documents modifiés.

### Q23. Label qualité
* **Commande :** `db.restaurants.updateMany({ cuisine: "French" }, { $set: { label_qualite: true } })`
* **Impact :** 345 documents modifiés (incluant YH Bistro créé en Q20).

---