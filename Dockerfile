FROM python:3.12-slim

ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY

# Le conteneur tourne en root (pas de USER dédié). Décision volontaire :
# le bind mount ./secrets:/app/secrets:ro préserve les UID de l'hôte, et un
# désalignement d'UID entre svc-taskins côté VM et un utilisateur svc-taskins
# créé dans l'image casserait la lecture de la clé SSH. À revoir en phase 4
# (déploiement) si un durcissement est nécessaire.

WORKDIR /app

RUN mkdir -p /app/data /app/secrets

# Les dépendances de test ne sont installées que dans l'image de développement
# (docker-compose.dev.yml passe INSTALL_DEV=true).
ARG INSTALL_DEV=false

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt && \
    if [ "$INSTALL_DEV" = "true" ]; then pip install --no-cache-dir -r requirements-dev.txt; fi

COPY . .

EXPOSE 8000

CMD ["uvicorn", "taskins.main:app", "--host", "0.0.0.0", "--port", "8000"]
