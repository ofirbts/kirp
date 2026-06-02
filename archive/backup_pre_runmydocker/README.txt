Backup created before RunMyDocker / cloud deployment changes.
Contains: .env (if present), Dockerfile.api, requirements.txt, docker-compose.yml,
src/main.py, src/core/*.py, src/api/*.py, all Dockerfiles (root + deploy/Dockerfile.qdrant).
Restore by copying files back to project root.
