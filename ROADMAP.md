# Évolutions prévues

> **Mis à jour le [DATE].** Document de prospective : sa validité se dégrade
> avec le temps. Les éléments de la section « À implémenter » ont vocation à
> devenir des issues GitHub puis à disparaître d'ici.

État actuel : PoC fonctionnel et testé, jugé prêt pour un usage restreint. Deux
manques le rendent impropre à une mise en service élargie — ils constituent le
cœur de la V2.

---

## Cœur de la V2

Ces deux points sont bloquants. Tant qu'ils ne sont pas traités, l'application
ne doit tourner que sur un périmètre où **tous les comptes sont de confiance**.

### 1. Contrôle d'accès aux workflows

**Problème.** Aucune règle de visibilité n'est appliquée. Tout utilisateur
authentifié peut consulter, **exécuter** et **planifier** n'importe quel
workflow, y compris ceux d'un autre utilisateur, et rediriger son exécution vers
n'importe quelle machine enregistrée. Comme un workflow contient des commandes
shell arbitraires, tout compte permet en pratique d'exécuter du code sur
l'ensemble du parc.

L'archivage et la suppression, eux, sont bien restreints au propriétaire ou à un
administrateur : l'incohérence montre qu'il s'agit d'un oubli, pas d'un choix.

**Ce qui existe déjà.** Les tables `groups`, `user_groups` et la clé étrangère
`workflows.group_id` sont en place et alimentées. Un groupe unique `all` reçoit
tous les workflows en V1.

**Ce qu'il reste à faire.**

- Filtrer les requêtes de lecture selon l'appartenance aux groupes du
  demandeur — modification localisée dans `workflow_service`.
- Appliquer la même règle à l'exécution et à la planification, aujourd'hui
  ouvertes à tout compte authentifié. C'est le point le plus urgent.
- Permettre le choix du groupe à la création d'un workflow, plutôt que le
  rattachement automatique à `all`.
- Gérer l'appartenance des utilisateurs aux groupes depuis l'interface
  d'administration : la table de liaison existe mais aucun écran ne la remplit.

**Impact.** Aucune migration de schéma. Modification des requêtes de lecture et
ajout de vérifications d'autorisation dans les services concernés.

### 2. Chaîne de validation des workflows

**Problème.** Soumettre un workflow le rend immédiatement exécutable. La
transition `DRAFT → PENDING_APPROVAL → PENDING` existe dans le modèle mais la
seconde étape est franchie automatiquement, sans intervention humaine. Un
utilisateur standard peut donc mettre en service un workflow contenant
n'importe quelle commande, sans revue.

**Ce qui existe déjà.** L'état `PENDING_APPROVAL` est accepté par le schéma. La
distinction des rôles administrateur / standard est en place.

**Ce qu'il reste à faire.**

- Supprimer la transition automatique dans `workflow_service.submit_workflow`.
- Ajouter les actions d'approbation et de rejet, réservées aux administrateurs.
- Prévoir le motif de rejet et le retour en `DRAFT` pour correction.
- Ajouter la file d'attente de validation sur la page d'accueil des
  administrateurs — l'emplacement est déjà prévu.

**Impact.** Aucune migration. Change le parcours utilisateur : un workflow n'est
plus exécutable immédiatement après soumission.

---

## À implémenter

Liste destinée à être transférée en issues GitHub, puis retirée de ce document.
Classée par priorité décroissante.

### Sécurité et exploitation

- [ ] **Restreindre l'exécution et la planification** au propriétaire, à son
      groupe ou à un administrateur *(cœur V2, point 1 — à traiter en premier)*
- [ ] **Filtrer la lecture des workflows** par appartenance de groupe
      *(cœur V2, point 1)*
- [ ] **Gérer l'appartenance aux groupes** depuis l'interface d'administration
- [ ] **Choisir le groupe** à la création d'un workflow
- [ ] **Chaîne de validation administrateur** *(cœur V2, point 2)*
- [ ] **Automatiser la sauvegarde** de la base — procédure documentée dans le
      README mais aucune tâche planifiée n'existe
- [ ] **Exécuter le conteneur sous un compte dédié** plutôt qu'en `root` —
      aligner l'UID sur celui du compte propriétaire de `secrets/`
- [ ] **HTTPS** — placer derrière un reverse proxy TLS et activer
      `https_only=True` sur le `SessionMiddleware`
- [ ] **Journaliser les actions sensibles** — qui a exécuté quoi, sur quelle
      machine, à quel moment. Aucune traçabilité par utilisateur aujourd'hui

### Fonctionnalités

- [ ] **Bouton « tester la connexion »** sur chaque machine cible — un `echo`
      dont le résultat brut est affiché. Aurait détecté immédiatement le
      problème de shell documenté dans MAINTENANCE.md. Coût faible, valeur
      élevée au diagnostic
- [ ] **Exécution parallèle des tâches** — le moteur est écrit en `async` pour
      permettre cette évolution sans réécriture complète
- [ ] **Notification en cas d'échec** — courriel ou webhook sur exécution en
      échec ; aujourd'hui il faut consulter l'interface pour le savoir
- [ ] **Purge de l'historique** — les tables `executions` et `task_results`
      grossissent indéfiniment. Prévoir une rétention configurable
- [ ] **Export YAML d'un workflow** — le format est spécifié et les règles de
      validation sont déjà implémentées ; seul l'export reste à écrire
- [ ] **Duplication d'un workflow** — contourne l'immuabilité des définitions
      sans la remettre en cause : dupliquer puis adapter
- [ ] **Pages d'erreur HTML** — les 404 renvoient le format JSON par défaut de
      FastAPI, y compris depuis l'interface web

### Chantiers lourds

- [ ] **Délais et temporisations entre tâches** — impose de rendre le moteur
      *reprenable* : traiter une exécution jusqu'au prochain point d'attente,
      persister « ne pas reprendre avant T », rendre la main. Une attente
      bloquante gèlerait le fil du moteur et donc toutes les autres exécutions.
      À traiter comme un chantier isolé, pas au milieu d'autres changements
- [ ] **Traitement concurrent des exécutions** — le moteur en traite une à la
      fois. Acceptable au volume actuel ; deux workflows planifiés à la même
      heure s'attendent
- [ ] **Exécution conditionnelle inter-workflows** — déclencher un workflow
      après la réussite d'un autre
- [ ] **Mapping de machines par rôle** — le retargeting actuel est
      tout-ou-rien : rediriger un workflow multi-machines envoie tout sur une
      seule cible. Un mapping fin (`web` → machine A, `db` → machine B) suppose
      que les tâches déclarent un rôle plutôt qu'une machine

### Dette technique

- [ ] **Uniformiser la langue** — commits en français et en anglais ; choisir
      l'anglais et s'y tenir. La documentation suivra
- [ ] **Traduire la documentation en anglais** une fois la V2 stabilisée
- [ ] **Tests de bout en bout** — la suite actuelle ne couvre ni le
      comportement navigateur, ni une connexion SSH réelle. Le seul défaut ayant
      atteint la production appartenait précisément à cette catégorie

---

## Hors périmètre

Écarté volontairement, à ne pas rouvrir sans raison nouvelle.

**Modification d'un workflow validé.** La définition est immuable par
construction : ce qui change entre deux exécutions — machine cible,
planification — n'en fait pas partie. Voir
[ARCHITECTURE.md](ARCHITECTURE.md#immuabilité-des-définitions).

**Rattrapage des exécutions manquées.** Après un arrêt du service, rejouer
plusieurs occurrences en rafale ferait plus de dégâts que d'en ignorer.

**Framework JavaScript.** Les pages sont des tableaux, pas une application
interactive.

**SGBD réseau.** SQLite suffit au volume visé. À reconsidérer seulement si le
traitement concurrent des exécutions est implémenté.
