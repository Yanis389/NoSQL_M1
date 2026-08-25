use ecommerce;

// ==========================================
// 1. Top 10 clients par chiffre d'affaires
// ==========================================
db.commandes.aggregate([
  { $match: { statut: { $ne: "annulee" } } },
  { $group: { _id: "$client_id", ca_total: { $sum: "$montant_total" } } },
  { $sort: { ca_total: -1 } },
  { $limit: 10 }
]);

// ==========================================
// 2. Panier moyen des commandes livrées
// ==========================================
db.commandes.aggregate([
  { $match: { statut: "livree" } },
  { $group: { _id: null, panier_moyen: { $avg: "$montant_total" } } }
]);

// ==========================================
// 3. Produits en rupture de stock
// ==========================================
db.produits.find({ stock: 0 });

// ==========================================
// 4. Chiffre d'affaires mensuel
// ==========================================
db.commandes.aggregate([
  { $match: { statut: { $ne: "annulee" } } },
  {
    $group: {
      _id: { annee: { $year: "$date" }, mois: { $month: "$date" } },
      ca_mensuel: { $sum: "$montant_total" },
      nb_commandes: { $sum: 1 }
    }
  },
  { $sort: { "_id.annee": -1, "_id.mois": -1 } }
]);

// ==========================================
// 5. Clients inactifs depuis plus de 6 mois
// ==========================================
const d = new Date();
d.setMonth(d.getMonth() - 6);

const clientsActifs = db.commandes.distinct("client_id", { date: { $gte: d } });
db.clients.find({ _id: { $nin: clientsActifs } });

// ==========================================
// BONUS : Index texte et recherche full-text
// ==========================================
db.produits.createIndex({ description: "text", nom: "text" });

db.produits.find(
  { $text: { $search: "tech ergonomique" } },
  { score: { $meta: "textScore" } }
).sort({ score: { $meta: "textScore" } });