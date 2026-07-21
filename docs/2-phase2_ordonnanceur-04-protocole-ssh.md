# Taskins — Protocole de communication serveur ↔ machine cible

## Mode retenu : ad hoc, sans agent permanent

Aucun daemon ni service persistant n'est déployé sur les machines exécutantes. Le serveur central ouvre une connexion SSH à la demande, pour chaque tâche, et la ferme immédiatement après.

## Séquence d'exécution d'une tâche

1. Résoudre la machine cible : lire `host`, `ssh_user`, `ssh_port` depuis la table `machines`, via l'alias indiqué dans la tâche (`machine_id`).
2. Ouvrir une session SSH avec paramiko, authentification par clé (chemin défini par `TASKINS_SSH_KEY_PATH`).
3. Pousser et exécuter la commande shell définie dans `tasks.command`.
4. Attendre la fin complète de l'exécution de la commande.
5. Capturer le code de retour (exit code), le flux stdout et le flux stderr.
6. Fermer immédiatement la session SSH.

Cette séquence correspond au module `core/ssh_client.py` (voir `03-architecture-applicative.md`).

## Distinction importante

Un échec à l'étape 2 (connexion impossible, timeout, machine injoignable) est un échec d'infrastructure : `task_results.status = FAILED`. Un code de retour non nul après une exécution réussie de la commande n'est pas un échec d'infrastructure : `task_results.status = DONE`, avec `return_code` non nul. Cette distinction conditionne directement le mécanisme de conditions — voir `05-moteur-ordonnancement.md`.

## Dépendances déjà en place (Phase 1)

L'utilisateur système `adm-taskins` et l'utilisateur applicatif `svc-taskins` existe sur les deux VMs. Une clé ed25519 a été générée sur `scheduler-server` et copiée vers `scheduler-worker`. `PermitRootLogin no` et `PasswordAuthentication no` sont déjà configurés. Aucune configuration SSH supplémentaire n'est requise pour le PoC — seul l'ajout de nouvelles machines cibles (au-delà de `scheduler-worker`) nécessitera de répéter cet échange de clés.
