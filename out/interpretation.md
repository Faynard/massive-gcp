# Interprétation des résultats

## Expérience 1 — Concurrence

| Users simultanés | Temps moyen |
|---|---|
| 1 | 196 ms |
| 10 | 367 ms |
| 20 | 84 ms |
| 50 | 233 ms |
| 100 | 118 ms |
| 1000 | 1 570 ms |

Les résultats sont logiques et cohérents avec le comportement attendu d'un PaaS.

- De 1 à 10 users : le temps augmente car il n'y a qu'une seule instance qui absorbe tout.
- De 10 à 100 users : le temps baisse alors que la charge monte. C'est contre-intuitif mais normale, on détecte la charge et apparait de nouvelles instances. La charge est distribuée sur plusieurs serveurs, ce qui améliore les temps de réponse.
- À 1000 users : les temps explosent à ~1 570 ms. On a scalé jusqu'à 13 instances, mais les instances F1 atteignent leurs limites. L'application reste disponible, elle est juste lente.

Sur la concurrence : OUI, ça scale, jusqu'à ~100 utilisateurs simultanés avec de très bonnes performances. Au-delà, ça se dégrade mais ne tombe pas.

---

## Expérience 2 — Fanout

| Followees | Temps moyen |
|---|---|
| 20 | 157 ms |
| 40 | 1 988 ms |
| 60 | 2 597 ms |

Les résultats sont logiques et attendus vu l'implémentation de la requête timeline.

La timeline est calculée en faisant une requêtes par utilsiateur suivi, fusionnées côté serveur. Doubler les followees double le nombre de requêtes réseau vers Datastore, et comme elles sont exécutées les une après les autres, le temps explose. 

App Engine scale pour compenser, mais ça ne suffit pas. Le problème est architectural, pas infrastructurel.

Sur le fanout : NON, ça ne scale pas. L'approche par calcule de la timeline à la lecture est le vrai goulot d'étranglement.

---

## Conclusion générale

Ça scale partiellement. L'infrastructure fait son travail, l'autoscaling fonctionne, aucune requête n'échoue. Mais l'architecture applicative de TinyInsta est limitée par sa requête timeline en requêtes par utilsiateur suivi. Pour vraiment scaler, il faudrait pré-calculer les timelines à l'écriture.
