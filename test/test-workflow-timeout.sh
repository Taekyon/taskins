#!/bin/bash
set -e

BASE_URL="http://localhost:80"
COOKIE_JAR=$(mktemp)
ENV_FILE="./.env.dev"
CURL_OPTS="--noproxy *"

if [ ! -f "$ENV_FILE" ]; then
  echo "Fichier $ENV_FILE introuvable — ajuste ENV_FILE ou lance ce script depuis le bon répertoire." >&2
  exit 1
fi

ADMIN_USER=$(grep -E '^TASKINS_BOOTSTRAP_ADMIN_USERNAME=' "$ENV_FILE" | cut -d '=' -f2- | sed "s/^['\"]//;s/['\"]$//")
ADMIN_PASS=$(grep -E '^TASKINS_BOOTSTRAP_ADMIN_PASSWORD=' "$ENV_FILE" | cut -d '=' -f2- | sed "s/^['\"]//;s/['\"]$//")

echo "--- Login ---"
curl -s $CURL_OPTS -c "$COOKIE_JAR" -o /dev/null -w "status: %{http_code}\n" \
  -X POST "$BASE_URL/login" -d "username=$ADMIN_USER&password=$ADMIN_PASS"

echo "--- Création du workflow (sleep 30s avec timeout 5s) ---"
RESPONSE=$(curl -s $CURL_OPTS -b "$COOKIE_JAR" -w "\n%{http_code}" \
  -X POST "$BASE_URL/api/v1/workflows" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-timeout",
    "description": "La tâche dort 30s mais le timeout est à 5s : doit échouer en ~5s",
    "tasks": [
      {
        "name": "dormir_longtemps",
        "command": "sleep 30",
        "target": "worker-1",
        "timeout_seconds": 5
      }
    ]
  }')
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')
echo "status: $HTTP_CODE"
echo "$BODY"
WF_ID=$(echo "$BODY" | grep -o '"id":[0-9]*' | head -n1 | grep -o '[0-9]*')

echo "--- Soumission ---"
curl -s $CURL_OPTS -b "$COOKIE_JAR" -o /dev/null -w "status: %{http_code}\n" \
  -X POST "$BASE_URL/api/v1/workflows/$WF_ID/submit"

echo "--- Exécution ---"
curl -s $CURL_OPTS -b "$COOKIE_JAR" -o /dev/null -w "status: %{http_code}\n" \
  -X POST "$BASE_URL/api/v1/workflows/$WF_ID/execute"

echo ""
echo "Attends ~15s (intervalle du moteur 10s + timeout 5s), puis :"
echo "  curl $CURL_OPTS -b $COOKIE_JAR $BASE_URL/api/v1/workflows/$WF_ID/executions"
echo ""
echo "Résultat attendu : status=FAILED"
echo "Sur la page web : /workflows/$WF_ID -> exécution FAILED, stderr contient 'Timeout'"

rm -f "$COOKIE_JAR"