# Benchmarks Sharding - Partie A

## Q2. Distribution initiale de la Shard Key `{ state: 1 }`
```text
Shard shardA at shardA/shardA:27017
 data : 1.35MiB docs : 13348
Shard shardB at shardB/shardB:27017
 data : 1.63MiB docs : 16122

Totals
 data : 2.98MiB docs : 29470
```
- Nombre de chunks : 2 chunks.
- Pourcentages : ~45.2% sur shardA, ~54.8% sur shardB.
- Équilibrage : Correct en volume, mais imparfait en nombre de documents.

## Q3. Frontières de chunks
```text
shardA [MinKey -> "NY"]
shardB ["NY" -> MaxKey]
```

## Q4. Après split manuel (4 coupures supplémentaires)
```text
Shard shardA at shardA/shardA:27017
 data : 1.48MiB docs : 14590
Shard shardB at shardB/shardB:27017
 data : 1.5MiB docs : 14880

Totals
 data : 2.98MiB docs : 29470
```
- Nombre de chunks : 6 chunks répartis entre A et B.
- Nouveaux pourcentages : ~49.5% sur shardA et ~50.5% sur shardB.
- Évolution : L'écart s'est resserré d'environ 4 points. La distribution s'approche des 50/50, mais la racine du problème des gros États n'est pas réglée.
