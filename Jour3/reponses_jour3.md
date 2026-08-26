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

## Partie 2 — Lire et écrire dans un Replica Set

### Q13. Lecture sur un Secondary
Commande :
docker exec mongo2 mongosh --quiet census --eval 'db.zips.countDocuments({})'
La lecture fonctionne directement car mongosh (v2.0+) gère automatiquement la préférence de lecture implicite lors d'une connexion directe à un nœud secondaire.

### Q14. Écriture sur un Secondary
Commande :
docker exec mongo2 mongosh --quiet census --eval 'db.zips.insertOne({test: 1})'
* Code d'erreur : NotWritablePrimary (code: 10107).
* Raison : Seul le Primary est autorisé à traiter les écritures pour garantir la cohérence et l'ordonnancement dans l'oplog.

### Q15. Retard de réplication et nature asynchrone
Commande :
docker exec mongo1 mongosh --quiet --eval 'rs.printSecondaryReplicationInfo()'
Lors de l'écriture en lot de 1 000 documents, un léger décalage temporaire (quelques millisecondes) apparaît sur le secondary avant d'atteindre 0, ce qui démontre le caractère asynchrone de la réplication par défaut (w: 1).

### Q16. Read Preference
* primary : Lit strictly sur le Primary (garantit la fraîcheur absolue des données).
* secondary : Décharge les lectures sur un Secondary (risque de lire des données périmées / stale data).
* Cas métier acceptable : Génération de rapports statistiques analytiques.
* Cas métier dangereux : Solde de compte bancaire immédiatement après un virement.

---

## Partie 3 — Failover & Quorum

### Q17 à Q22. Synthèse des pannes
(Les mesures détaillées figurent dans le fichier failover.md).

### Q21. Analyse du délai de panne brutale (docker kill)
* Délai d'élection mesuré : ~11,8 secondes.
* Le délai est légèrement supérieur à electionTimeoutMillis (10 000 ms) car il inclut l'intervalle de heartbeat (heartbeatIntervalMillis = 2000 ms) avant le déclenchement officiel de l'élection.

### Q23. Rupture de Quorum
Commandes :
docker stop mongo2 mongo3
docker exec mongo1 mongosh --quiet --eval 'print("Writable:", db.hello().isWritablePrimary); print("State:", rs.status().myState)'

Résultats :
* (a) Immédiatement après la coupure, mongo1 bascule de isWritablePrimary: true (état 1) à isWritablePrimary: false (état 2 / SECONDARY).
* (b) Écriture : Refusée avec NotWritablePrimaryError. Lecture avec readPreference: primary : Refusée.
* (c) Règle de majorité : La majorité d'un cluster à 3 nœuds est 2. Avec 2 pannes, il ne reste qu'un membre sur 3 (pas de majorité possible), le nœud se destitue donc lui-même. Un cluster de 4 nœuds a une majorité de 3 : il ne tolère toujours qu'une seule panne (4 - 3 = 1), tout comme un cluster à 3 nœuds.

---

## Partie 4 — Write Concern & Read Concern

### Q24. Différence de garantie entre w: 1 et w: "majority"
* w: 1 confirme l'écriture dès que le Primary l'a écrite dans son journal local.
* w: "majority" attend la confirmation par au moins 2 nœuds sur 3.
* En cas de docker kill brutal du Primary avant la réplication, une écriture validée en w: 1 peut être définitivement perdue (rollback).

### Q25. Write Concern invalide (w: 4)
Commande :
docker exec mongo1 mongosh --quiet census --eval 'db.demo.insertOne({a: 1}, {writeConcern: {w: 4, wtimeout: 3000}})'
* Code d'erreur : CannotSatisfyWriteConcern.
* MongoDB rejette immédiatement la requête sans attendre les 3 secondes du wtimeout car le nombre de nœuds demandés (4) dépasse le nombre total de membres configurés dans le Replica Set (3).

### Q26. Panne d'un membre et Write Concern
Après docker stop mongo3 :
* w: "majority" (2 nœuds nécessaires) : Passe avec succès.
* w: 3 (3 nœuds nécessaires) : Échoue avec WriteConcernFailed au bout de 3000 ms.
* countDocuments({}) : Les deux documents sont présents en base.
* Explication : L'échec d'un Write Concern signifie que le délai d'attente de confirmation a expiré, et non que l'écriture a été annulée. L'écriture est bien appliquée sur le Primary. Si l'application rejoue la requête après l'erreur, elle risque de créer un doublon en l'absence d'identifiant unique.

### Q27. Impact du paramètre j: true
j: true force le changement à être écrit sur le journal disque avant de confirmer. Cela protège contre une perte totale d'alimentation simultanée sur l'ensemble des 3 machines.

### Q28. Propriétés de readConcern: "majority"
Il garantit que la donnée lue a été confirmée par la majorité du cluster et ne pourra jamais être annulée par un rollback suite à la panne du Primary.

---