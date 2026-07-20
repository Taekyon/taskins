#!/bin/bash
set -e


BASE_URL="http://localhost:80"
COOKIE_JAR=$(mktemp)
ENV_FILE="./.env.dev"

if [ ! -f "$ENV_FILE" ]; then
  echo "Fichier $ENV_FILE introuvable — ajuste ENV_FILE ou lance ce script depuis le bon répertoire." >&2
  exit 1
fi

# Récupération des identifiants d'admin depuis le fichier .env.dev
ADMIN_USER=$(grep -E '^TASKINS_BOOTSTRAP_ADMIN_USERNAME=' "$ENV_FILE" | cut -d '=' -f2-)
ADMIN_PASS=$(grep -E '^TASKINS_BOOTSTRAP_ADMIN_PASSWORD=' "$ENV_FILE" | cut -d '=' -f2- | sed "s/^['\"]//;s/['\"]$//")

if [ -z "$ADMIN_USER" ] || [ -z "$ADMIN_PASS" ]; then
  echo "TASKINS_BOOTSTRAP_ADMIN_USERNAME/PASSWORD introuvables dans $ENV_FILE" >&2
  exit 1
fi

 
echo "--- 1. Login ($ADMIN_USER) ---"
curl -s -c "$COOKIE_JAR" -o /dev/null -w "status: %{http_code}\n" \
  -X POST "$BASE_URL/login" \
  -d "username=$ADMIN_USER&password=$ADMIN_PASS"

echo "--- 2. Création du workflow (3 tâches, conditions en chaîne) ---"
RESPONSE=$(curl -s -b "$COOKIE_JAR" -w "\n%{http_code}" \
  -X POST "$BASE_URL/api/v1/workflows" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "selfping",
    "description": "test manuel",
    "tasks": [
      {"name": "verifier_connectivite", "command": "ping -c 3 127.0.0.1", "target": "worker-1"}
    ]
  }')
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')
echo "status: $HTTP_CODE"
echo "$BODY"

WF_ID=$(echo "$BODY" | grep -o '"id":[0-9]*' | head -n1 | grep -o '[0-9]*')
echo "workflow_id extrait : $WF_ID"

echo "--- 3. Soumission (DRAFT -> PENDING) ---"
curl -s -b "$COOKIE_JAR" -w "\nstatus: %{http_code}\n" \
  -X POST "$BASE_URL/api/v1/workflows/$WF_ID/submit"

echo "--- 4. Exécution (crée une ligne executions) ---"
curl -s -b "$COOKIE_JAR" -w "\nstatus: %{http_code}\n" \
  -X POST "$BASE_URL/api/v1/workflows/$WF_ID/execute"

echo "--- 5. Historique des exécutions ---"
curl -s -b "$COOKIE_JAR" -w "\nstatus: %{http_code}\n" \
  "$BASE_URL/api/v1/workflows/$WF_ID/executions"

rm -f "$COOKIE_JAR"
