# Projet Ordonnanceur — Synthèse Phase 1

## Contexte

Atelier de développement d'un ordonnanceur de tâches destiné à une PME. L'IA assiste tout au long du cycle de développement. Le projet est un PoC fonctionnel, avec environ 2-3 semaines de mise en place.

---

## Cahier des charges — Fonctionnalités requises

### Gestion des workflows
- Création et exécution de workflows simples
- Enchaînement de tâches en série ou en parallèle
- Application de conditions d'exécution entre tâches (basées sur le code de retour)
- Définition des workflows via interface web **ou fichier YAML** (portabilité)
- Un workflow peut être exécuté plusieurs fois

### Exécution distribuée
- Exécution des tâches sur plusieurs machines de l'entreprise
- Mécanisme d'agent distant déployé sur chaque machine exécutante
- Communication via SSH entre le serveur central et les agents

### Interface de supervision
- Consultation de l'état des workflows (en cours, terminés)
- Visualisation des codes de retour de chaque tâche exécutée
- Accès à l'historique des exécutions

### Gestion des utilisateurs
- Utilisateurs standards : peuvent créer et soumettre des workflows
- Administrateurs : approuvent les workflows soumis, gèrent les droits
- Gestion manuelle des utilisateurs depuis l'interface web (pas de LDAP)
- Chaque utilisateur appartient à un ou plusieurs groupes

### Règles de visibilité
- Un utilisateur voit ses propres workflows
- Un utilisateur voit les workflows des groupes auxquels il appartient

### Interface
- Toutes les fonctionnalités accessibles depuis une interface web

---

## Acteurs

| Acteur | Rôle |
|---|---|
| Utilisateur standard | Crée, soumet et consulte ses workflows et ceux de son groupe |
| Administrateur | Approuve les workflows, gère les utilisateurs et les droits |
| Agent distant | Processus technique sur les machines exécutantes, reçoit et exécute les tâches, remonte les codes de retour |
| Serveur central | Orchestre les workflows, communique avec les agents, expose l'API et l'interface web |

---

## Fonctionnalités

| # | Fonctionnalité | Acteur |
|---|---|---|
| F1 | Créer un workflow (interface web ou fichier YAML) | Utilisateur standard |
| F2 | Soumettre un workflow pour approbation | Utilisateur standard |
| F3 | Approuver ou rejeter un workflow soumis | Administrateur |
| F4 | Exécuter un workflow approuvé (plusieurs fois possible) | Serveur central |
| F5 | Enchaîner des tâches en série | Moteur d'ordonnancement |
| F6 | Exécuter des tâches en parallèle | Moteur d'ordonnancement |
| F7 | Appliquer des conditions entre tâches (code de retour) | Moteur d'ordonnancement |
| F8 | Distribuer l'exécution sur plusieurs machines via agent | Serveur central + Agent |
| F9 | Remonter le code de retour de chaque tâche | Agent distant |
| F10 | Consulter l'état des workflows | Utilisateur standard / Admin |
| F11 | Consulter l'historique des exécutions | Utilisateur standard / Admin |
| F12 | Gérer les utilisateurs et les groupes | Administrateur |
| F13 | Attribuer / retirer les droits admin | Administrateur |

---

## Entités métier

```
User
  - id, username, password_hash, is_admin
  - appartient à 1 ou plusieurs Groups

Group
  - id, name
  - contient 1 ou plusieurs Users

Workflow
  - id, name, owner (User), group (Group), status
  - statuts : draft | pending_approval | approved | running | done | failed
  - définissable via interface web ou fichier YAML

Task
  - id, appartient à 1 Workflow
  - command (commande shell à exécuter)
  - target_machine
  - type : serial | parallel
  - condition (optionnelle) : dépend du code de retour d'une Task précédente

Execution
  - id, liée à 1 Workflow
  - started_at, finished_at, status
  - contient 1 ou plusieurs TaskResults
  - relation 1 Workflow → N Executions (exécutions multiples)

TaskResult
  - id, liée à 1 Task et 1 Execution
  - return_code, stdout, stderr, started_at, finished_at

Agent
  - entité technique, pas en base de données
  - identifié par hostname + IP dans la configuration du serveur
```

---

## Environnement de travail

### Infrastructure
- 2 machines virtuelles sur Proxmox (infrastructure de formation)
- OS : Debian (installation NetInstall, sans interface graphique)
- Paquets installés : SSH server + standard system utilities uniquement

### Rôles des machines

| Machine | Hostname | Rôle |
|---|---|---|
| VM 1 | `scheduler-server` | Serveur central : API, interface web, base de données, moteur d'ordonnancement |
| VM 2 | `scheduler-worker` | Machine exécutante : héberge l'agent distant |

### Configuration SSH
- Utilisateur système : `adm-taskins` sur les deux machines
- Utilisateur applicatif : `svc-taskins` sur les deux machines
- Clé SSH générée sur `scheduler-server` (ed25519), copiée vers `scheduler-worker`
- Connexion sans mot de passe de `scheduler-server` → `scheduler-worker` : opérationnelle
- `PermitRootLogin no` et `PasswordAuthentication no` configurés sur les deux machines
- IPs fixes configurées dans `/etc/network/interfaces`

---

## Décisions techniques arrêtées en phase 1

| Décision | Choix | Justification |
|---|---|---|
| Format de définition des workflows | YAML | Lisible par des non-développeurs, standard DevOps |
| Architecture agent | Agent simple (PoC) | Objectif PoC, pas de surenchère |
| Communication serveur ↔ agent | SSH | Recommandé dans la consigne, déjà configuré |
| Gestion des utilisateurs | Manuelle via interface web | Pas de LDAP, simplicité |
| Exécutions multiples | Oui | Un workflow peut être relancé plusieurs fois |

---

## Ce qui reste à décider — Phase 2

Les points suivants seront tranchés en phase de conception :

1. **Stack technologique** — langage(s), framework web, base de données (plusieurs options à présenter)
2. **Architecture applicative** — découpage en composants et frontières entre eux
3. **Protocole serveur ↔ agent** — mécanisme SSH détaillé (connexion ad hoc vs daemon)
4. **Moteur d'ordonnancement** — logique série/parallèle, machine à états, gestion des conditions
5. **Format YAML** — structure exacte du fichier de définition d'un workflow
6. **Modèle de contrôle d'accès** — implémentation des règles de visibilité et du flux d'approbation
7. **Convention de nommage des services** — à figer avant l'implémentation

---

## Points de risque identifiés

- **Moteur d'ordonnancement** : partie la plus complexe, toute ambiguïté sur son modèle coûte du refactoring. Priorité absolue en conception.
- **Communication SSH** : timeouts, reconnexions et gestion des clés sont souvent sous-estimés.
- **Nommage des services** : doit être figé avant le début de l'implémentation.
