# Vue d'ensemble — 4 phases du projet


## Phase 1 — Initialisation

L'objectif est de poser les bases avant d'écrire la moindre ligne de code.

1. Lire et analyser le cahier des charges — identifier tous les acteurs (utilisateur standard, administrateur, agent distant), toutes les fonctionnalités, et toutes les contraintes (SSH, Proxmox, Debian).
2. Cartographier les entités métier — lister les objets centraux du domaine : Workflow, Tâche, Exécution, Utilisateur, Groupe, Agent. C'est la base du vocabulaire partagé et des noms de services.
3. Clarifier les points ambigus (voir questions ci-dessus) — avant toute conception, trancher les questions ouvertes pour éviter de retravailler l'architecture.
4. Définir l'environnement de travail — accéder aux deux VMs Proxmox, vérifier la connectivité réseau entre elles, planifier les rôles (quelle VM = serveur central, quelle VM = machine exécutante).
5. Installer Debian sur les deux VMs (NetInstall) — configurer le réseau, SSH, et les accès de base.


## Phase 2 — Conception

L'objectif est de produire des décisions techniques documentées avant d'implémenter.

1. Choisir la stack technologique — langage(s), framework web, base de données, bibliothèques de gestion de processus. (Décision bloquée par Q1)
2. Concevoir le modèle de données — schéma des entités : Workflow, Tâche (série/parallèle, conditions), Exécution, Code de retour, Utilisateur, Groupe, Rôle (standard/admin). (Décision partiellement bloquée par Q3)
3. Définir l'architecture applicative — découper en composants : serveur central, agent distant, interface web, API interne. Décider de la frontière entre eux.
4. Concevoir le protocole serveur ↔ agent — mécanisme exact de communication SSH : connexion persistante vs. connexion à la demande, format des messages, gestion des erreurs et timeouts. (Décision bloquée par Q2)
5. Concevoir le moteur d'ordonnancement — logique d'enchaînement série/parallèle, évaluation des conditions entre tâches, gestion des états (en attente, en cours, terminé, en erreur). (Impacté par Q4)
6. Concevoir le modèle de contrôle d'accès — règles de visibilité (propres workflows, workflows du groupe), flux d'approbation admin, gestion des droits.
7. Nommer les services et composants de manière cohérente — arrêter une convention de nommage (ex. : scheduler-server, task-agent, workflow-api) avant l'implémentation.


## Phase 3 — Réalisation

L'objectif est d'implémenter par couches, du cœur vers la périphérie.

1. Mettre en place la structure du projet — organisation des dossiers, dépôt de code, gestion des dépendances, environnements (dev / prod).
2. Implémenter le modèle de données et la persistence — créer le schéma de base de données, les migrations, les modèles/ORM.
3. Implémenter le moteur d'ordonnancement — logique série/parallèle, gestion des conditions, machine à états des exécutions.
4. Implémenter l'agent distant — daemon ou script déployable via SSH, capable de recevoir une tâche, l'exécuter, et renvoyer le code de retour.
5. Implémenter la communication serveur ↔ agent — couche SSH, gestion des connexions, protocole de message.
6. Implémenter la gestion des utilisateurs et des droits — authentification, rôles, groupes, flux d'approbation des workflows.
7. Implémenter l'interface web — formulaires de création de workflow, tableau de bord de supervision (état des workflows, codes de retour, historique).
8. Tests fonctionnels — tester chaque fonctionnalité en isolation : création de workflow, exécution série, exécution parallèle, conditions, visibilité par groupe, approbation admin.


## Phase 4 — Déploiement

L'objectif est de faire tourner la solution sur les VMs Proxmox dans des conditions proches du réel.

1. Déployer le serveur central sur la VM principale — installer les dépendances, configurer le service, sécuriser l'accès.
2. Déployer l'agent distant sur la VM secondaire — installer l'agent, configurer les clés SSH, vérifier la communication avec le serveur central.
3. Configurer la communication SSH inter-VMs — échange de clés, règles de pare-feu, test de connectivité.
4. Test d'intégration end-to-end — créer un workflow de test couvrant les deux machines, vérifier l'exécution distribuée, les codes de retour, et la supervision via l'interface web.
5. Validation du cahier des charges — passer en revue chaque exigence de la consigne et confirmer qu'elle est satisfaite.

## Réponse aux questions

Q1: il n'y aucune contrainte. Tu devras me présenter différentes options pour chaque décision importante
Q2: L'idée de ce projet est surtout de faire une sorte de PoC qui fonctionne, il faut donc développer l'agent le plus simple. La consigne "SSH" est une piste, car SSH va être utiliser pour la configuration
Q3: Dans un premier temps, les utilisateurs ne sont pas lié à un LDAP. Chaque utilisateur appartient à 1 groupe ou +. J'aimerai pouvoir gérer ses utilisateurs manuellement depuis l'interface web.
Q4: Choix libre. Dans l'hypothèse ou ce projet serait vraiment utiliser par une petite entreprise, il faudrait que les workflows puissent être définis via un fichier, pour une meilleur portabilité.
Q5: Il me reste environ deux à trois semaine de mise en place. Dis-moi si c'est faisable en moins.