# Taskins — Moteur d'ordonnancement

## Les trois machines à états

Voir `02-modele-donnees.md` pour le détail complet. Résumé : `workflows.status` (conception/approbation : `DRAFT`, `PENDING_APPROVAL`, `PENDING`) est indépendant de `executions.status` (une exécution : `PENDING`, `RUNNING`, `DONE`, `FAILED`), lui-même indépendant de `task_results.status` (une tâche au sein d'une exécution : `PENDING`, `RUNNING`, `DONE`, `FAILED`).

## Transition automatique V1

À la soumission d'un workflow, l'application le fait passer de `DRAFT` à `PENDING_APPROVAL`, puis immédiatement et automatiquement à `PENDING`, sans intervention humaine. En V2, il suffira de bloquer cette transition automatique et de la lier à une action de l'administrateur dans l'interface (voir `06-controle-acces.md`).

## Boucle du moteur

Fonction asynchrone périodique, intervalle défini par `TASKINS_SCHEDULER_INTERVAL` :

```
toutes les N secondes :
    pour chaque ligne de `executions` au statut PENDING :
        verrouiller : execution.status = RUNNING, execution.started_at = maintenant
        pour chaque task du workflow, dans l'ordre de order_index :
            créer task_result (status = RUNNING, started_at = maintenant)

            si task.condition_task_id n'est pas NULL :
                lire task_result où execution_id = execution.id ET task_id = task.condition_task_id
                si task_result.return_code != task.condition_expected_code :
                    execution.status = FAILED, execution.finished_at = maintenant
                    arrêter le traitement de cette exécution

            exécuter la commande via core/ssh_client.py

            si échec d'infrastructure (connexion, timeout) :
                task_result.status = FAILED
                execution.status = FAILED, execution.finished_at = maintenant
                arrêter le traitement de cette exécution
            sinon :
                task_result.status = DONE
                task_result.return_code, stdout, stderr = résultat de la commande
                task_result.finished_at = maintenant

        si toutes les tâches ont été traitées sans interruption :
            execution.status = DONE, execution.finished_at = maintenant
```

Chaque cycle de la boucle externe est protégé par un `try/except` — voir `03-architecture-applicative.md`.

## Mécanisme de conditions entre tâches

Décisions retenues :

| Question | Décision |
|---|---|
| Ce qu'on évalue | Le code de retour uniquement (pas stdout/stderr) |
| Opérateur | Égalité sur une valeur spécifique attendue |
| Condition non satisfaite | L'exécution s'arrête, passe en `FAILED` |

Le code de retour attendu pour comparaison est lu dans `task_results`, filtré par `execution_id` (l'exécution en cours) et `task_id` (la tâche référencée) — jamais une recherche globale, puisqu'une même tâche produit un `return_code` différent à chaque exécution.

Une tâche sans condition (`condition_task_id` et `condition_expected_code` à `NULL`) s'exécute toujours.

## Ce qui n'est pas couvert en V1 (différé V2)

Le comportement en cas de condition non satisfaite n'est pas configurable par tâche : pas de statut `SKIPPED`, pas de champ `on_condition_failure`. L'exécution en parallèle des tâches n'est pas implémentée, bien que le moteur soit écrit en `async`/`await` dès la V1 pour permettre son activation ultérieure sans réécriture complète. Aucune condition basée sur le contenu de stdout/stderr.
