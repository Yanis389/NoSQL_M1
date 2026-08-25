# Benchmark & Optimisation des Index

## 1. Création des Index

```javascript
// Index sur le stock pour la détection rapide des ruptures
db.produits.createIndex({ stock: 1 });

// Index composé sur les commandes (Statut + Date)
db.commandes.createIndex({ statut: 1, date: -1 });

// Index sur client_id pour optimiser les jointures et filtres inactifs
db.commandes.createIndex({ client_id: 1 });
