-- Étape 9 — retargeting, instantané d'historique, timeout par tâche.
--
-- À exécuter UNIQUEMENT si tu veux conserver une base existante. Sinon,
-- supprimer le volume Docker est plus simple (create_all() recrée tout).
--
-- Usage :
--   docker compose -f docker-compose.dev.yml exec taskins \
--     sqlite3 /app/data/taskins.db < migrations/001-retargeting-snapshot-timeout.sql
--
-- Les lignes task_results antérieures garderont command/machine_alias/machine_host
-- à NULL : leur historique n'est pas reconstituable a posteriori.

ALTER TABLE tasks        ADD COLUMN timeout_seconds INTEGER;
ALTER TABLE executions   ADD COLUMN machine_id      INTEGER REFERENCES machines(id);
ALTER TABLE task_results ADD COLUMN command         TEXT;
ALTER TABLE task_results ADD COLUMN machine_alias   TEXT;
ALTER TABLE task_results ADD COLUMN machine_host    TEXT;
