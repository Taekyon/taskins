-- Étape 10 — archivage des workflows (suppression douce).
-- À exécuter uniquement pour conserver une base existante ; sinon, supprimer
-- le volume Docker suffit (create_all() recrée tout).
ALTER TABLE workflows ADD COLUMN archived_at TEXT;
