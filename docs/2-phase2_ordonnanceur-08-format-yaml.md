# Taskins — Format YAML de définition d'un workflow

## Spécification des champs

**Workflow (racine)**

| Champ | Obligatoire | Type | Description |
|---|---|---|---|
| `name` | Oui | texte | Identifiant lisible du workflow |
| `description` | Non | texte | Documentation libre |
| `tasks` | Oui | liste | Tâches dans l'ordre d'exécution |

**Tâche**

| Champ | Obligatoire | Type | Description |
|---|---|---|---|
| `name` | Oui | texte | Identifiant unique au sein du workflow |
| `command` | Oui | texte | Commande shell à exécuter |
| `target` | Oui | texte | Alias de la machine cible (correspond à `machines.alias`) |
| `condition` | Non | bloc | Condition d'exécution |

**Bloc `condition`**

| Champ | Obligatoire | Type | Description |
|---|---|---|---|
| `task` | Oui | texte | Nom de la tâche précédente à observer |
| `return_code` | Oui | entier | Code de retour attendu |

## Règles de validation

Chaque `name` de tâche doit être unique dans le workflow. Un `target` doit correspondre à un alias déclaré dans la table `machines`. Le `task` d'une condition doit référencer une tâche qui apparaît avant la tâche courante dans la liste. Une condition ne peut référencer qu'une seule tâche.

## Exemple 1 — Workflow sans condition

```yaml
name: deploiement-applicatif
description: "Arrêt, mise à jour et redémarrage du service applicatif"

tasks:
  - name: arreter_service
    command: "systemctl stop monapp"
    target: worker-1

  - name: mettre_a_jour
    command: "apt-get install -y monapp"
    target: worker-1

  - name: demarrer_service
    command: "systemctl start monapp"
    target: worker-1
```

## Exemple 2 — Workflow avec condition

```yaml
name: maintenance-disque
description: "Vérifie l'espace disponible avant de lancer le nettoyage"

tasks:
  - name: verifier_espace
    command: "df /var | awk 'NR==2 {exit ($5+0 > 80)}'"
    target: worker-1

  - name: nettoyer_logs
    command: "find /var/log -name '*.gz' -mtime +30 -delete"
    target: worker-1
    condition:
      task: verifier_espace
      return_code: 0
```

## Exemple 3 — Conditions en chaîne, multi-étapes

```yaml
name: sauvegarde-distante
description: "Sauvegarde de la base de données vers le serveur de stockage"

tasks:
  - name: verifier_connectivite
    command: "ping -c 1 storage-server"
    target: worker-1

  - name: dumper_base
    command: "pg_dump mabase > /tmp/dump.sql"
    target: worker-1
    condition:
      task: verifier_connectivite
      return_code: 0

  - name: transferer_dump
    command: "scp /tmp/dump.sql storage:/backups/"
    target: worker-1
    condition:
      task: dumper_base
      return_code: 0

  - name: nettoyer_tmp
    command: "rm /tmp/dump.sql"
    target: worker-1
    condition:
      task: transferer_dump
      return_code: 0
```

## Hors périmètre V1

Tâches parallèles (`type: parallel`), comportement configurable en cas de condition non satisfaite (`on_condition_failure`), timeout par tâche, variables et paramètres dynamiques dans les commandes.
