# Taskins — Livrables de conception (Phase 2)

Ce document et les fichiers associés (01 à 09) constituent l'ensemble des livrables de conception du projet Taskins. Ils sont destinés à servir de base directe à l'implémentation (Phase 3). Le contexte fonctionnel complet (acteurs, fonctionnalités F1-F13, entités métier, environnement Proxmox/Debian) se trouve dans `phase1_ordonnanceur-synthese.md`, à lire en complément.

## Sommaire des fichiers

| Fichier | Contenu | Point du plan Phase 2 |
|---|---|---|
| `01-stack-technologique.md` | Langage, framework, base de données, client SSH | Point 1 |
| `02-modele-donnees.md` + `02-schema.sql` | Entités, schéma SQL complet, machines à états | Point 2 |
| `03-architecture-applicative.md` | Découpage en composants, structure des dossiers, cycle de vie du moteur | Point 3 |
| `04-protocole-ssh.md` | Mécanisme de communication serveur ↔ machine cible | Point 4 |
| `05-moteur-ordonnancement.md` | Logique d'enchaînement, mécanisme de conditions, boucle du moteur | Point 5 |
| `06-controle-acces.md` | Visibilité, flux d'approbation — périmètre V1 | Point 6 |
| `07-nommage.md` | Convention de nommage (services, endpoints, Docker, variables) | Point 7 |
| `08-format-yaml.md` | Spécification du format YAML de définition d'un workflow | Phase 1, "ce qui reste à décider", point 5 |
| `09-environnement-docker.md` | Stratégie `.env`, gestion multi-environnement, pratiques DevOps | Environnement de travail |

## Périmètre V1 — statut de chaque fonctionnalité

| # | Fonctionnalité | Statut en V1 |
|---|---|---|
| F1 | Créer un workflow (web ou YAML) | Implémenté — format YAML figé (08) |
| F2 | Soumettre pour approbation | Implémenté — transition DRAFT → PENDING_APPROVAL |
| F3 | Approuver/rejeter un workflow | Non opérant — transition automatique sans intervention admin (05, 06) |
| F4 | Exécuter un workflow (plusieurs fois) | Implémenté — un Workflow peut produire plusieurs Executions |
| F5 | Enchaîner des tâches en série | Implémenté |
| F6 | Exécuter des tâches en parallèle | Différé V2 — moteur écrit en async, prêt pour l'activation (05) |
| F7 | Conditions entre tâches (code de retour) | Implémenté (05) |
| F8 | Distribuer sur plusieurs machines via agent | Implémenté — mode SSH ad hoc, sans agent permanent (04) |
| F9 | Remonter le code de retour de chaque tâche | Implémenté |
| F10 | Consulter l'état des workflows | Données prêtes en base — aucune maquette d'interface produite en Phase 2 |
| F11 | Consulter l'historique des exécutions | Idem F10 |
| F12 | Gérer les utilisateurs et les groupes | Modèle de données prêt — visibilité non appliquée, groupe unique `all` par défaut (06) |
| F13 | Attribuer/retirer les droits admin | Colonne `is_admin` présente — mécanisme d'attribution non conçu (gap) |

## Points non tranchés (gaps de la Phase 2)

Ces points n'ont pas été abordés durant la Phase 2 et devront être tranchés avant ou pendant l'implémentation des modules concernés.

**Mécanisme d'authentification** — aucune décision sur le hachage des mots de passe, la gestion de session (cookie signé, JWT, session serveur), ni sur la procédure de connexion elle-même.

**Bootstrap du premier compte administrateur** — la base de données ne contient initialement aucun utilisateur ; le mécanisme de création du tout premier compte admin n'est pas défini.

**Attribution concrète du rôle admin (F13)** — la colonne `users.is_admin` existe, mais l'écran ou l'action permettant de la modifier n'a pas été défini.

**Interface de supervision (F10, F11)** — aucune maquette n'a été produite. Les données nécessaires (`executions`, `task_results`) sont prêtes, mais la présentation reste à concevoir.

## Correction apportée lors de la compilation

En consolidant le schéma de données et la logique du moteur, une incohérence a été identifiée entre deux décisions prises séparément : le modèle d'entités de la Phase 1 prévoit qu'un Workflow produise plusieurs Executions (exécutions multiples, F4), mais la description initiale du moteur (première synthèse Phase 2) faisait porter les états `RUNNING`/`DONE`/`FAILED` directement sur le Workflow. Un Workflow ne peut pas être à la fois "exécutable plusieurs fois" et "verrouillé sur un état d'exécution unique" — ces deux idées sont incompatibles telles qu'elles étaient écrites.

Correction retenue : `workflows.status` ne porte que le cycle de conception/approbation (`DRAFT`, `PENDING_APPROVAL`, `PENDING`). Les états `RUNNING`, `DONE`, `FAILED` appartiennent exclusivement à `executions.status`. Le moteur scanne donc la table `executions`, pas la table `workflows`. Détail complet dans `02-modele-donnees.md` et `05-moteur-ordonnancement.md`.
