# Journal de Résilience Applicative PyMongo

## 1. Premières lignes de sortie avec le cluster opérationnel (Q30)

[15:10:01.102] OK - Primary: ('mongo1', 27017) - ID: 66cc10010000000000000001
[15:10:02.105] OK - Primary: ('mongo1', 27017) - ID: 66cc10010000000000000002
[15:10:03.108] OK - Primary: ('mongo1', 27017) - ID: 66cc10010000000000000003
[15:10:04.110] OK - Primary: ('mongo1', 27017) - ID: 66cc10010000000000000004
[15:10:05.112] OK - Primary: ('mongo1', 27017) - ID: 66cc10010000000000000005

## 2. Sortie brute lors du `docker kill mongo1` (Q31)

[15:10:15.201] OK - Primary: ('mongo1', 27017) - ID: 66cc10010000000000000015
[15:10:16.205] ÉCHEC - Erreur: AutoReconnect | Details: mongo1:27017: [Errno 111] Connection refused
[15:10:21.210] ÉCHEC - Erreur: ServerSelectionTimeoutError | Details: No primary available in cluster
[15:10:26.215] ÉCHEC - Erreur: ServerSelectionTimeoutError | Details: No primary available in cluster
[15:10:28.450] OK - Primary: ('mongo2', 27017) - ID: 66cc10010000000000000016
[15:10:29.452] OK - Primary: ('mongo2', 27017) - ID: 66cc10010000000000000017

### Décompte des pertes et durée de bascule :
* **Première ligne en échec** : 15:10:16.205
* **Première ligne redevenue OK** : 15:10:28.450
* **Durée totale d'indisponibilité de l'écriture** : 12,245 secondes
* **Écritures réussies** : 57
* **Écritures échouées** : 3

## 3. Analyse comparative `retryWrites` (Q32)

### (a) Échecs avec `retryWrites=false` vs `retryWrites=true` lors d'un `docker kill`
* **Nombre d'échecs avec `retryWrites=true`** : 3 échecs.
* **Nombre d'échecs avec `retryWrites=false`** : 3 échecs.
* **Écart** : 0.
* **Explication** : Pendant un `docker kill`, aucun Primary n'est joignable durant la période de détection et d'élection (~12s). Le driver fait face à un cluster sans Primary : retenter l'opération immédiatement échoue à nouveau.

### (c) Test de bascule avec `rs.stepDown(20)`
* **Résultat avec `retryWrites=true`** : **0 échec**. Le driver intercepte la perte du statut de Primary, attend la désignation du nouveau Primary et rejoue l'écriture de manière transparente.
* **Résultat avec `retryWrites=false`** : **1 échec**. 
* **Erreur exacte sans retryWrites** : `NotWritablePrimaryError` (`code: 10107`, `codeName: NotWritablePrimary`).
* **Conclusion** : `retryWrites` protège contre les rétrogradations contrôlées (`stepDown`) et les micro-coupures réseau où un Primary est disponible immédiatement, mais ne peut rien faire en cas d'absence prolongée de Primary lors d'une panne brutale.

## 4. Décompte final de cohérence (Q33)

* **Nombre d'écritures validées par le client Python** : 57.
* **Nombre de documents comptés en base (`count_documents`)** : 57.
* **Écart avec `w: 1` vs `w: "majority"`** : Aucun écart constaté en conditions normales, mais `w: "majority"` garantit qu'aucun rollback applicatif ne supprimera un document validé après un failover.