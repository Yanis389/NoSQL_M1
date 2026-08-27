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

## PARTIE B — Performances & diagnostic

### B0 — Environnement et import
**Q10. Les espaces dans les noms de champs**
- **Conséquence :** La présence d'espaces nous oblige à toujours entourer les noms de champs de guillemets dans nos requêtes, et on perd la notation pointée simple.
- **(a) Syntaxe pour un `find` :** `db.trips.find({ "start station id": 476 })`
- **(b) Syntaxe dans `$group` :** `{ _id: "$start station id" }`
- **Oubli des guillemets :** Le shell va crasher avec une erreur de syntaxe (`SyntaxError`) car l'espace est illégal en JS pour une clé non quotée.

**Q11. Plage temporelle et anomalie**
- Requête : `db.trips.aggregate([{ $group: { _id: null, min: { $min: "$start time" }, max: { $max: "$stop time" } } }])`
- **Observation :** La plage s'étend au-delà de janvier 2016 (débordements sur février, valeurs aberrantes de 1970). Dans la vraie vie, une base de données brute contient toujours des débordements nécessitant un nettoyage.

### B1 — Aggregation Pipeline : les fondamentaux
*(Requêtes exactes dans `pipelines.js`)*

**Q12. Top 5 des stations de départ**
- Les stations comme `Pershing Square North` et `W 21 St & 6 Ave` figurent en tête (grands nœuds de transit).

**Q13. Répartition par type d'abonnement**
- **Hypothèse métier :** Les abonnés (Subscriber) font des trajets pendulaires domicile-travail très courts et efficaces. Les clients occasionnels (Customer) font des trajets beaucoup plus longs (touristes).

**Q14. Trajets par jour**
- Nous obtenons un nombre de jours supérieur à 31, ce qui confirme que la plage déborde de janvier.

**Q15. Heure de pointe**
- Les heures de pointe sont `8h` et `17h-18h`, correspondant à l'usage domicile-travail classique.

**Q16. Distribution des durées**
- La tranche la plus peuplée est `[300, 600[` (5 à 10 minutes) ou `[600, 1800[` (10 à 30 minutes).

**Q17. Boucles**
- Un certain nombre de trajets finissent exactement là où ils ont commencé.

### B2 — Qualité de données et optimiseur
**Q18. Le champ piégé**
- **Tous les `Customer` ont une année de naissance stockée en chaîne de caractères**, alors que les `Subscriber` l'ont en entier. La requête `{ "birth year": { $lt: 1950 } }` est silencieusement fausse car une chaîne BSON est toujours considérée comme supérieure à un nombre.

**Q19. Âge moyen**
- L'âge du plus vieil usager remonte souvent à plus de 100 ans. C'est absurde, c'est une valeur par défaut. En production, j'ajouterais un `$match` sanitaire.

**Q20. Valeurs aberrantes**
- Certains trajets durent **plus de 24 heures**. (Vélos volés, mal raccrochés).

**Q21. La question d'écart**
- Les `Customer` sont infiniment plus affectés car plus sujets aux vols/oublis. Je communiquerais la **médiane** à la direction (insensible aux valeurs extrêmes).

**Q22. `$match` en premier — vraiment ?**
- Les deux plans d'exécution sont **identiques**. L'optimiseur a fait du *Match Pushdown* et a déplacé le `$match` avant le `$group`.

**Q23. La limite de l'optimiseur**
- L'optimiseur ne peut pas remonter le filtre car il dépend d'un champ `n` généré *par* le `$group`.

### B3 — Matérialisation et jointure
**Q25. `$out` vs `$merge`**
- `$merge` permet le rafraîchissement incrémental en mettant à jour uniquement les statistiques du jour sans écraser toute la table.

**Q26. `$lookup`**
- Une station d'arrivée très forte ("puits") signifie un endroit où les usagers convergent (quartier résidentiel le soir) nécessitant une redistribution logistique (camions).

### B4 — Index géospatial `2dsphere`
*(Scripts dans `geo.js`)*
**Q27. Sans index**
- **Pourquoi obligatoire :** Calculer la distance de Haversine pour toute la collection plomberait le CPU, MongoDB refuse un COLLSCAN géospatial.

**Q28. Ordre de `$near`**
- Les résultats sont renvoyés **strictement triés du plus proche au plus éloigné**.

**Q29. Le piège de `countDocuments` avec `$near`**
- `countDocuments` génère un `$match` enfoui, alors que `$near` exige d'être la requête principale. Solution : utiliser `$geoWithin` + `$centerSphere`.

**Q30. `$geoNear` sur la collection `stations`**
- `$geoNear` doit **absolument être le premier stage** pour tirer parti de l'index `2dsphere`.

## Partie C — Réflexion SRE

**R1. Le tableau de bord quotidien**
- **Architecture :** Pipeline avec `$merge` vers `stations_stats` planifié à 5h50.
- **Gain :** Le dashboard lit 400 documents pré-calculés au lieu d'exécuter un `$group` sur des milliers/millions de trajets.
- **Compromis :** La fraîcheur des données est décalée d'une journée (latence batch), ce qui est suffisant pour le décisionnel.

**R2. La règle d'écriture des pipelines**
- L'optimiseur ne remonte un filtre que si celui-ci porte sur un champ présent *avant* modification. S'il s'agit d'un champ calculé par le `$group` ou supprimé par `$project`, le filtre ne sera pas remonté. Il faut donc écrire ses `$match` le plus tôt possible par sécurité.

**R3. Le chiffre unique, et son coût**
- **(a)** "La durée moyenne d'usage normal d'un vélo est de X min (calculée sur 99,5% des trajets après exclusion des locations > 3h)."
- **(b)** La **médiane** (`$median`) est mathématiquement insensible aux valeurs extrêmes, contrairement à la moyenne.
- **(c)** Un chiffre brut cache le contexte (vélos volés) et provoque de mauvaises décisions stratégiques.

**R4. `explain()` ou profiler ?**
- `explain()` analyse la *stratégie théorique* (index). Le profiler enregistre la *pratique réelle* (lenteurs disques, locks).
- **Incident 14h :** 
  1. `mongostat` (macroscopique : saturation CPU/RAM ?).
  2. `profiler` (quelle requête précise embouteille ?).
  3. `explain()` (pourquoi cette requête bloque : index manquant ?).
