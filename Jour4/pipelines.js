// B1 — Aggregation Pipeline : les fondamentaux

// Q12. Top 5 des stations de départ
var q12 = [
  { $group: { _id: "$start station name", count: { $sum: 1 } } },
  { $sort: { count: -1 } },
  { $limit: 5 }
];

// Q13. Répartition par type d'abonnement
var q13 = [
  { $group: { _id: "$usertype", count: { $sum: 1 }, avgDuration: { $avg: "$tripduration" } } }
];

// Q14. Trajets par jour
var q14 = [
  { $group: { _id: { $dateTrunc: { date: "$start time", unit: "day" } }, count: { $sum: 1 } } },
  { $sort: { "_id": 1 } }
];

// Q15. Heure de pointe
var q15 = [
  { $group: { _id: { $hour: "$start time" }, count: { $sum: 1 } } },
  { $sort: { count: -1 } },
  { $limit: 5 }
];

// Q16. Distribution des durées
var q16 = [
  { $bucket: {
      groupBy: "$tripduration",
      boundaries: [0, 300, 600, 1800, 3600, 1000000],
      default: "Other",
      output: { effectif: { $sum: 1 } }
  } }
];

// Q17. Boucles
var q17 = [
  { $match: { $expr: { $eq: ["$start station id", "$end station id"] } } },
  { $count: "trajets_boucle" }
];

// B2 — Qualité de données

// Q19. Âge moyen
var q19 = [
  { $match: { "birth year": { $type: "number" } } },
  { $group: { 
      _id: null, 
      avgBirthYear: { $avg: "$birth year" }, 
      minBirthYear: { $min: "$birth year" }, 
      effectif: { $sum: 1 } 
  } },
  { $project: {
      avgAge: { $subtract: [2016, "$avgBirthYear"] },
      maxAge: { $subtract: [2016, "$minBirthYear"] },
      effectif: 1
  } }
];

// Q21. Recalcul de l'écart sans les valeurs aberrantes
var q21 = [
  { $match: { tripduration: { $lte: 10800 } } },
  { $group: { _id: "$usertype", count: { $sum: 1 }, avgDuration: { $avg: "$tripduration" } } }
];
