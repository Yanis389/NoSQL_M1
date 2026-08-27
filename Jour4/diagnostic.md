# B5 — Diagnostic et Optimisation

## Q31. Analyse d'Index (Explain)

**Requête :** `db.trips.find({ "start station id": 476 })`

### (a) Avant indexation
- **Stage racine :** `COLLSCAN`
- **totalDocsExamined :** 10000
- **Ratio (docs/returned) :** Très élevé.

### (b) Après création de l'index `{ "start station id": 1 }`
- **Stage racine :** `FETCH` (sous-stage `IXSCAN`)
- **Ratio :** Égal à 1.

### (c) Ratio et Objectif
- Le ratio idéal est **1**. On ne l'atteint presque jamais sans projection car il faut exécuter un `FETCH` en RAM.

## Q32 & Q33. Le Profiler
- **Niveaux :** 0 (Off), 1 (Slow), 2 (All).
- **Production :** Niveau 1 (`slowms: 100`).
- **Risques du Niveau 2 :** Overhead CPU massif et perte d'historique (effacement des requêtes lentes intéressantes par des micro-requêtes anodines car c'est une capped collection).

## Q34. Dashboard de production
```javascript
db.system.profile.find({ 
  planSummary: /COLLSCAN/, 
  millis: { $gt: 100 } 
}).sort({ millis: -1 })
```
