# Rapport complet TP3 — Réplication & Haute Disponibilité

    **Nom :** Yanis HELALI  
    **Formation :** Master 1 Data IA - IPSSI  
    **Module :** Conception et intégration de bases de données NoSQL  
## Partie 0 — Monter le Replica Set

### Q1. État avant initialisation
Commandes exécutées :
docker exec mongo1 mongosh --quiet --eval 'printjson(db.hello())'
docker exec mongo1 mongosh --quiet --eval 'db.test.insertOne({a: 1})'

Sortie et analyse :
* isWritablePrimary : false
* primary : Champ absent
* info : "Configuring replica set"
* Code d'erreur d'écriture : NotWritablePrimaryNoReplicaSetMember
* Conclusion : Un nœud lancé avec --replSet mais non initialisé n'est ni Primary ni Secondary. Il refuse les écritures et les lectures tant que la configuration n'est pas appliquée.

### Q2. Membres après initialisation
Commande exécutée :
docker exec mongo1 mongosh --quiet --eval 'rs.status().members.map(m => m.name+" "+m.stateStr).join("\n")'

Sortie observée :
mongo1:27017 PRIMARY
mongo2:27017 SECONDARY
mongo3:27017 SECONDARY

Le nœud mongo1:27017 est PRIMARY car dans init-rs.js, sa propriété priority est définie à 2 (contre 1 pour mongo2 et mongo3).

### Q3. Vérification des données importées
Commande exécutée :
docker exec mongo1 mongosh --quiet census --eval 'print("Total:", db.zips.countDocuments()); print("States:", db.zips.distinct("state").length); printjson(db.zips.aggregate([{$group: {_id: null, totalPop: {$sum: "$pop"}}}]))'

Résultats :
* Nombre de documents : 29 470
* États distincts : 51 (les 50 États américains + le district de Columbia, DC)
* Population totale : 298 584 315 habitants

### Q4. Analyse de la clé naturelle zip
Commande exécutée :
docker exec mongo1 mongosh --quiet census --eval 'print("Zips distincts:", db.zips.distinct("zip").length); printjson(db.zips.aggregate([{$group: {_id: "$zip", count: {$sum: 1}}}, {$match: {count: {$gt: 1}}}]))'

Résultats :
* Codes postaux distincts : 29 470 (égal au nombre total de documents).
* Agrégation des doublons : Renvoie une liste vide [ ].
* Tentative de création d'index unique :
docker exec mongo1 mongosh --quiet census --eval 'db.zips.createIndex({zip: 1}, {unique: true})'
Sortie : { "numIndexesBefore": 1, "numIndexesAfter": 2, "ok": 1 }. La création réussit car zip est bien une clé unique dans ce jeu de données.

### Q5. Codes postaux à population nulle
Commande exécutée :
docker exec mongo1 mongosh --quiet census --eval 'db.zips.countDocuments({pop: 0})'

Résultats :
* Documents avec pop: 0 : 77.
* Explication métier : Il s'agit d'une réalité métier correspondant à des zones d'entreprises, des installations militaires ou des bâtiments gouvernementaux disposant de leur propre code postal sans résident permanent.

---

## Partie 1 — Anatomie du Replica Set et de l'oplog

### Q6. Paramètres de configuration temporelle
Commande exécutée :
docker exec mongo1 mongosh --quiet --eval 'printjson(rs.conf().settings)'

Résultats :
* electionTimeoutMillis : 10000
* heartbeatIntervalMillis : 2000
* Traduction : Un secondary déclare le primary mort au bout de 10 000 ms (10 s) alors qu'il l'interroge toutes les 2 000 ms (2 s).

### Q7. Surveillance de la santé des membres dans rs.status()
* Champs clés : stateStr (statut du membre), health (1 si en vie, 0 si HS).
* Le champ indiquant qu'un nœud est injoignable est health: 0 (associé au lastHeartbeatMessage décrivant l'échec réseau).

### Q8. Taille maximale de l'oplog
Commande exécutée :
docker exec mongo1 mongosh --quiet --eval 'const l = db.getSiblingDB("local"); print("maxSize:", l.oplog.rs.stats().maxSize)'

Résultats :
* maxSize : 134217728 octets (128 Mo).
* Cette valeur provient du drapeau --oplogSize 128 défini dans docker-compose.rs.yml. Without option, MongoDB alloue par défaut 5 % de l'espace disque libre.

### Q9. Granularité des opérations d'oplog
Commande exécutée :
docker exec mongo1 mongosh --quiet --eval 'db.getSiblingDB("local").oplog.rs.countDocuments({op: "i", ns: "census.zips"})'

Résultats :
* Nombre d'entrées : 29470.
* Démonstration : L'égalité parfaite avec le nombre de documents prouve que l'oplog décompose les opérations par lots (mongoimport) en opérations unitaires individuelles.

### Q10. Idempotence des opérations d'insertion
Dans l'entrée d'oplog (findOne({op: "i", ns: "census.zips"})), le champ o contient le document complet avec son identifiant fixe _id. Si l'opération est rejouée, MongoDB effectue un remplacement basé sur l'identifiant unique sans générer de doublons, garantissant l'idempotence.

### Q11. Idempotence des mises à jour (updateMany)
Commandes exécutées :
docker exec mongo1 mongosh --quiet census --eval 'db.zips.updateMany({state: "TX"}, {$inc: {pop: 1}})'
docker exec mongo1 mongosh --quiet local --eval 'db.oplog.rs.findOne({op: "u", ns: "census.zips"})'

Résultats :
* Dans l'oplog, le champ o ne contient pas $inc, mais un opérateur $set: { pop: <nouvelle_valeur> }.
* Raison : Rejouer $inc: 1 deux fois incrémenterait la valeur de 2. Remplacer par la valeur absolue finale $set garantit que rejouer l'oplog donne toujours le même résultat.

### Q12. Dimensionnement de l'oplog
Commande exécutée :
docker exec mongo1 mongosh --quiet local --eval 'const s = db.oplog.rs.stats(); print("Size:", s.size, "Count:", s.count)'

Calculs :
* (a) Taille moyenne d'une opération : ~320 octets.
* (b) Nombre d'opérations mémorisables : 134 217 728 / 320 ≈ 419 430 opérations.
* (c) Fenêtre de réplication à 300 éc/s : 419 430 / 300 = 1398 s ≈ 23,3 minutes.
* Conclusion : Un secondary tombé le vendredi à 18 h ne pourra pas rattraper son retard le lundi à 9 h. L'oplog aura tourné en boucle et écrasé les anciennes entrées, exigeant une resynchronisation totale (resync).

---