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
