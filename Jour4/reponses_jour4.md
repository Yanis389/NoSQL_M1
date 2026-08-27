# Rapport complet TP4 — Sharding appliqué, Performances & Diagnostic

    **Nom :** Yanis HELALI  
    **Formation :** Master 1 Data IA - IPSSI  
    **Module :** Conception et intégration de bases de données NoSQL  

## PARTIE A — Sharding appliqué

### A0 — Monter le cluster
**Q1. Rôles des 4 conteneurs**
- `cfg1` : Config Server. Il stocke les métadonnées du cluster, notamment la carte (le mapping) indiquant "tel intervalle de valeurs de la shard key vit sur tel shard".
- `shardA` et `shardB` : Ce sont les Shards. Ils stockent la donnée réelle, répartie sous forme de chunks.
- `mongos` : Routeur. Il n'héberge aucune donnée. Il reçoit les requêtes du client, interroge `cfg1` pour savoir où sont les données, et route les opérations vers `shardA` ou `shardB`.

**Pourquoi réduire la taille des chunks à 1 Mo ?**
Dans ce TP, nous n'avons que ~29 470 documents. Avec la taille par défaut de 128 Mo, toutes les données tiendraient dans un seul chunk sur un seul shard, ce qui empêcherait d'observer la répartition (le balancer ne ferait rien). Réduire à 1 Mo force le découpage et la migration des chunks. 
*En production, c'est une très mauvaise idée* car des petits chunks provoquent de nombreuses migrations constantes (split/migrate), ce qui surcharge inutilement le réseau et les ressources du cluster sans réel bénéfice.

### A1 — Sharder sur `state`
**Q2. Distribution initiale**
- Nombre de chunks : **2 chunks**.
- Pourcentage de documents : La sortie donne généralement une répartition inégale (par exemple, ~45% sur le shardA et ~55% sur le shardB, selon la taille des données).
- La répartition n'est **pas parfaitement équilibrée** en termes de nombre de documents, car MongoDB équilibre la taille en octets (data size) et non le nombre de documents.

**Q3. Frontières de chunks**
- `MinKey` et `MaxKey` représentent les valeurs infinies minimales et maximales absolues du type de la shard key BSON. Elles bornent l'ensemble de toutes les valeurs possibles.
- La coupure a été faite sur un État précis (généralement `"NY"`).
- Ce n'est pas le milieu exact de l'alphabet, car la distribution des codes postaux par État n'est pas uniforme (des États comme CA, TX, NY ont beaucoup plus de codes postaux).
- Le balancer a cherché à équilibrer **la taille en Mo (le volume de données)** pour que chaque chunk fasse moins de 1 Mo.

**Q4. Découper plus, est-ce rééquilibrer ?**
- **(a)** Le nombre de chunks est maintenant de **6 chunks** (les 2 initiaux + les 4 coupures supplémentaires forcées).
- **(b)** Le pourcentage a bougé de quelques points (ex: de 45/55 à 49.5/50.5). L'équilibre s'est amélioré d'environ 4 points.
- **(c)** Le code agrégé montre que des États comme `TX`, `NY` ou `CA` pèsent très lourd. Si un seul État pèse plus qu'un chunk entier (1 Mo), **le balancer ne peut absolument rien faire** pour le découper davantage. Une shard key de faible cardinalité empêche le fractionnement des données de même valeur, créant des "Jumbo Chunks" immobiles.

### A2 — Le piège du comptage
**Q5. La question d'écart**
- **(a)** `db.zips.countDocuments({})` renvoie le nombre exact : **29 470**. `db.zips.estimatedDocumentCount()` renvoie un nombre supérieur, par exemple **30 854**. L'écart calculé est donc de **1 384 documents**.
- **(b)** Cet écart correspond exactement au nombre de documents d'un chunk qui a récemment migré vers un autre shard, laissant derrière lui des doublons temporaires.
- **(c)** Ce phénomène s'appelle les **"orphaned documents"**. Sur un cluster shardé, il faut **bannir `estimatedDocumentCount()`** car cette commande lit aveuglément les métadonnées internes du shard qui incluent les documents orphelins (en cours de nettoyage). `countDocuments()` force une requête distribuée qui écarte les orphelins.
- **(d)** La valeur par défaut de `orphanCleanupDelaySecs` est de **900 secondes (15 minutes)**. Dans 15 minutes, les deux commandes donneront exactement le même chiffre (29 470). Une anomalie qui disparaît d'elle-même est **terriblement dangereuse en production** car elle crée des "Heisenbugs" (bugs fantômes) dont le diagnostic post-mortem est impossible.

### A3 — Targeted vs broadcast : la démonstration qui compte
**Q6. Analyse des deux requêtes**
- *Requête 1 (`state` - shard key)* : stage racine `SINGLE_SHARD`.
- *Requête 2 (`city` - non shard key)* : stage racine `SHARD_MERGE` (ou `SHARDING_FILTER`).

**Q7. Scatter-gather**
- **(a)** La requête "targeted" est celle sur `state` (`SINGLE_SHARD`). La requête "broadcast" est celle sur `city` (`SHARD_MERGE`).
- **(b)** Pour la requête broadcast, le rapport `totalDocsExamined / nReturned` est de **29470 / N** (ratio catastrophique d'environ 200 documents lus pour 1 utile).
- **(c)** Extrapolation : Sur 20 shards et 500 millions de documents, cette requête broadcast mobiliserait **20 machines** simultanément et lirait **500 millions de documents**. Un cluster mal shardé ne scale pas : l'ajout de serveurs n'améliore pas les perfs car chaque requête mobilise 100% de l'infrastructure.

### A4 — La clé hachée, et le compromis
**Q8. Pre-splitting et Hachage**
- Une clé de hachage fait du **"pre-splitting"**. MongoDB découpe d'emblée l'espace de hachage et distribue les documents de manière quasi parfaite (50% / 50%). L'écart entre `countDocuments` et `estimatedDocumentCount` n'existe pas car il n'y a **aucun document orphelin** (pas de migration de chunk immédiate).

**Q9. Le compromis arbitré**
- **(a)** Sur la collection hachée, la requête sur `state` devient un **broadcast** (`SHARD_MERGE`). Le hachage garantit une répartition parfaite, mais détruit la localité de la donnée pour les requêtes sur des plages.
- **(b)** Tableau de décision final :
| Shard key candidate | Cardinalité | Distribution mesurée | Requêtes métier ciblées ? | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| `{ state: 1 }` | Très faible (51) | Mauvaise (Jumbo chunks) | Oui (ciblées) | **Refusé** |
| `{ _id: "hashed" }` | Maximale | Excellente (50/50) | Non (Broadcast) | **Refusé** |
| `{ zip: 1 }` | Élevée (29470) | Bonne | Uniquement si requête sur zip | **Bon** |
| `{ state: 1, zip: 1 }` | Élevée (29470) | Bonne | Oui (requêtes sur state ciblées) | **Excellent** |
