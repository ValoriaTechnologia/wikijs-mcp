# Dockerfile pour le serveur MCP Oversecur
FROM python:3.11-slim

# Définir le répertoire de travail
WORKDIR /app

# Installer les dépendances système si nécessaire
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Copier le fichier requirements.txt
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code source
COPY src/ ./src/
COPY run_server.py .

# Créer un utilisateur non-root pour la sécurité
RUN useradd -m -u 1000 mcpuser && chown -R mcpuser:mcpuser /app
USER mcpuser

# Exposer le port pour l'accès réseau (SSE)
EXPOSE 8000

# Variables d'environnement par défaut
ENV MCP_TRANSPORT=sse
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8000

# Commande par défaut (mode réseau SSE)
CMD ["python", "run_server.py"]
