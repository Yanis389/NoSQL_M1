# Rapport de Failover et Bascule de Nœud

Ce document regroupe les mesures de temps de bascule et d'élection au sein du Replica Set rs0.

## Tableau synthétique des pannes (Q22)

| Scénario | Commande | Délai mesuré | Nœud élu | Écritures perdues ? |
| :--- | :--- | :--- | :--- | :--- |
| **Arrêt propre** | `docker stop mongo1` | 2,1 s | `mongo2:27017` | Non (transfert propre du rôle) |
| **Panne brutale** | `docker kill mongo1` | 11,8 s | `mongo3:27017` | Non sur les données confirmées |
| **Retour du nœud** | `docker start mongo1` | ~12,4 s (reprise P1) | `mongo1:27017` | Aucune (rattrapage via l'oplog) |

## Analyse pour la DSI

Pour respecter un SLA de **99,9 %** (soit un maximum de **43 minutes d'indisponibilité par mois**) :
1. Une panne brutale isole l'écriture pendant **~12 secondes**, ce qui consomme moins de **0,5 %** de notre quota d'indisponibilité mensuel par incident.
2. Le cluster tolère parfaitement la perte d'un membre sur un ensemble de 3 nœuds sans interruption de service pour les lectures correctement configurées.
3. La ré-élection automatique via `priority: 2` provoque une seconde bascule brève lors du retour du nœud principal.