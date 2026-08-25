# Modélisation de la base E-commerce

## 1. Choix d'architecture (Embed vs Reference)

### Collection `clients` (Référencé)
* **Structure :** Document autonome contenant `nom`, `email`, `ville`, `date_inscription`.
* **Justification :** Un client existe indépendamment des commandes. L'entité a une cardinalité qui évolue et possède son propre cycle de vie.

### Collection `produits` (Référencé)
* **Structure :** Document autonome contenant `nom`, `description`, `prix`, `stock`, `categorie`.
* **Justification :** Les produits sont consultés et modifiés indépendamment. Les imbriquer dans chaque commande dupliquerait inutilement la donnée sans garantie de cohérence lors des mises à jour du catalogue.

### Collection `commandes` (Modèle Hybride / Extended Reference Pattern)
* **Structure :**
  * `client_id` : Référence (`ObjectId`) vers la collection `clients`.
  * `lignes` : Tableau de sous-documents **embarqués** (`produit_id`, `nom`, `prix_unitaire`, `quantite`).
* **Justification :** 
  * **Embed pour les lignes :** Suivra la règle *"Data accessed together should be stored together"*. On lit toujours le détail des articles avec la commande.
  * **Immuabilité du prix :** Le prix unitaire est figé dans la commande au moment de l'achat, évitant ainsi l'impact des variations de prix futures du catalogue.

---

## 2. Structure des Documents BSON

```json
// clients
{
  "_id": ObjectId("..."),
  "nom": "Jean Dupont",
  "email": "jean.dupont@example.com",
  "ville": "Paris",
  "date_inscription": ISODate("2025-01-15T10:00:00Z")
}

// produits
{
  "_id": ObjectId("..."),
  "nom": "Clavier Mécanique",
  "description": "Clavier RGB switch red ergonomique",
  "prix": 89.99,
  "stock": 15,
  "categorie": "Tech"
}

// commandes
{
  "_id": ObjectId("..."),
  "client_id": ObjectId("..."),
  "date": ISODate("2026-02-10T14:30:00Z"),
  "statut": "livree",
  "montant_total": 109.89,
  "lignes": [
    {
      "produit_id": ObjectId("..."),
      "nom": "Clavier Mécanique",
      "prix_unitaire": 89.99,
      "quantite": 1
    }
  ]
}
