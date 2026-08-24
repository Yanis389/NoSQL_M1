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
* **Résultat :**
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