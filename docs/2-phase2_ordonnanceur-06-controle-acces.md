# Taskins — Contrôle d'accès (périmètre V1)

## Ce qui est en place

Le schéma de données intègre dès la V1 les tables nécessaires à la gestion des groupes et de la visibilité : `groups`, `user_groups` (relation many-to-many), et la clé étrangère `workflows.group_id`. Un groupe unique nommé `all` est injecté par défaut (voir `02-schema.sql`). Tous les workflows créés en V1 sont rattachés à ce groupe.

## Ce qui n'est pas appliqué en V1

Aucune règle de visibilité n'est appliquée dans la logique métier ni dans l'interface : tout utilisateur authentifié voit l'ensemble des workflows. Le passage en V2 consistera à filtrer les requêtes selon l'appartenance aux groupes (`user_groups`), sans migration de schéma — uniquement une modification des requêtes dans `services/workflow_service.py`.

Le flux d'approbation administrateur (F3) existe dans la machine à états (`PENDING_APPROVAL`) mais ne déclenche aucune action réelle : la transition vers `PENDING` est automatique (voir `05-moteur-ordonnancement.md`). Aucune action d'approbation/rejet n'est exposée dans l'interface en V1.

## Ce qui n'a pas été conçu (gap)

L'attribution et le retrait du rôle administrateur (F13) ne sont pas conçus dans le détail : la colonne `users.is_admin` existe, mais l'écran ou l'action permettant de la modifier n'a pas été défini. Le mécanisme d'authentification lui-même (connexion, gestion de session, hachage des mots de passe) n'a pas été abordé en Phase 2 — voir `00-index.md`.
