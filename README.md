# Serveur MCP pour WikiJS

Serveur MCP (Model Context Protocol) qui expose l'API GraphQL de WikiJS pour rechercher et lire des pages de documentation.

## Architecture

Le serveur MCP utilise **FastMCP v3** pour interagir avec WikiJS via son API GraphQL. Il expose 4 outils simples pour rechercher et lire des pages.

## Fonctionnalités

- **4 Tools MCP** : Recherche et lecture de pages WikiJS
- **Resources** : Accès aux pages WikiJS
- **Prompts** : Aide interactive pour utiliser l'API
- **Authentification OAuth** : Protection du serveur MCP via Keycloak (optionnel)
- **Authentification API** : Clé API WikiJS pour les requêtes GraphQL

## Outils disponibles

1. **search_wiki** - Recherche des pages dans WikiJS
2. **read_page** - Récupère le contenu d'une page par son ID
3. **list_pages** - Liste les pages disponibles avec pagination
4. **get_page_by_path** - Récupère une page par son chemin

## Installation

1. Clonez ce repository ou copiez les fichiers dans votre projet

2. Installez les dépendances :
```bash
pip install -r requirements.txt
```

3. Configurez les variables d'environnement :
```bash
cp env.example .env
```

Éditez `.env` et configurez :
- `WIKIJS_URL` : URL de base de WikiJS (ex: `https://wiki.example.com`)
- `WIKIJS_GRAPHQL_ENDPOINT` : Endpoint GraphQL (optionnel, défaut: `{WIKIJS_URL}/graphql`)
- `WIKIJS_API_KEY` : Clé API WikiJS avec droits de lecture
- `MCP_TRANSPORT` : Mode de transport (`stdio` pour local, `sse` pour réseau, défaut: `sse`)
- `MCP_HOST` : Adresse d'écoute pour le mode réseau (défaut: `0.0.0.0`)
- `MCP_PORT` : Port pour le mode réseau (défaut: `8000`)
- `FASTMCP_SHOW_SERVER_BANNER` : Afficher la bannière au démarrage (optionnel, voir [FastMCP](https://gofastmcp.com))

## Configuration WikiJS

### Générer une clé API

1. Connectez-vous à votre instance WikiJS en tant qu'administrateur
2. Allez dans **Administration** > **API Keys**
3. Cliquez sur **Create New Key**
4. Configurez :
   - **Name** : Nom descriptif (ex: "MCP Server")
   - **Permissions** : Sélectionnez au minimum les permissions de **lecture** (Read)
   - **Expiration** : Optionnel
5. Copiez la clé API générée et ajoutez-la dans votre fichier `.env` :
   ```bash
   WIKIJS_API_KEY=votre_cle_api_ici
   ```

### Configuration de l'endpoint GraphQL

Par défaut, l'endpoint GraphQL est `{WIKIJS_URL}/graphql`. Si votre instance WikiJS utilise un endpoint différent, vous pouvez le spécifier :

```bash
WIKIJS_GRAPHQL_ENDPOINT=https://wiki.example.com/graphql
```

## Authentification

Le serveur utilise **deux niveaux d'authentification distincts** :

### 1. Authentification avec WikiJS (clé API)

Le serveur MCP s'authentifie auprès de WikiJS en utilisant une clé API.

**Configuration :**
- Définissez `WIKIJS_API_KEY` dans votre fichier `.env`
- La clé API doit avoir au minimum les permissions de lecture
- Toutes les requêtes GraphQL incluent automatiquement le header `Authorization: Bearer {WIKIJS_API_KEY}`

**Exemple de configuration :**
```bash
WIKIJS_URL=https://wiki.example.com
WIKIJS_API_KEY=votre_cle_api_ici
```

### 2. Authentification du serveur MCP avec OAuth Keycloak (optionnel)

Le serveur MCP peut être protégé par OAuth 2.0 avec Keycloak pour authentifier les clients MCP. Cette authentification est **indépendante** de l'authentification avec WikiJS.

Le serveur utilise `OAuthProxy` de FastMCP qui gère automatiquement :
- Les endpoints OAuth discovery (`.well-known/oauth-authorization-server`, etc.)
- Le flux OAuth complet avec Dynamic Client Registration (DCR)
- La vérification des tokens JWT via JWKS
- Le support PKCE pour la sécurité
- La protection contre les attaques "confused deputy" via consent screen

**Configuration Keycloak requise :**

Avant d'utiliser le serveur MCP, vous devez configurer un client dans Keycloak :

1. **Créer un client** dans votre realm Keycloak :
   - Client ID : choisissez un nom (ex: `wikijs-mcp-client`)
   - Client Protocol : `openid-connect`
   - Access Type : `confidential` (recommandé) ou `public`
   - Valid Redirect URIs : `{MCP_BASE_URL}/auth/callback` (ex: `http://localhost:8000/auth/callback`)

2. **Obtenir le Client Secret** si le client est confidentiel (onglet "Credentials" dans Keycloak)

3. **Configurer les scopes** si nécessaire (par défaut: `openid profile email`)

**Note (FastMCP v3)** : Le stockage OAuth par défaut utilise désormais FileTreeStore. Lors d'une mise à jour depuis FastMCP v2, les clients MCP devront se ré-enregistrer une fois à la première connexion (comportement automatique).

**Activation :**

1. Définissez les variables d'environnement dans votre fichier `.env` :
   ```bash
   KEYCLOAK_URL=https://keycloak.example.com
   KEYCLOAK_REALM=wikijs-mcp
   KEYCLOAK_CLIENT_ID=wikijs-mcp-client
   KEYCLOAK_CLIENT_SECRET=your-client-secret-here
   KEYCLOAK_SCOPES=openid profile email
   MCP_BASE_URL=http://localhost:8000
   ```

2. Si `KEYCLOAK_REALM` n'est **pas défini**, l'authentification est désactivée et le serveur est accessible à tous (mode développement uniquement).

**Mode avancé (URLs séparées) :**

Pour un déploiement avec des URLs différentes pour PUBLIC et INTERNAL (ex: Docker) :

```bash
KEYCLOAK_PUBLIC_URL=https://keycloak.example.com
KEYCLOAK_INTERNAL_URL=http://keycloak:8080
KEYCLOAK_REALM=wikijs-mcp
KEYCLOAK_CLIENT_ID=wikijs-mcp-client
KEYCLOAK_CLIENT_SECRET=your-client-secret-here
MCP_BASE_URL=http://localhost:8000
```

**Résumé des deux authentifications :**

| Type | Variable d'environnement | Usage | Obligatoire |
|------|-------------------------|-------|-------------|
| WikiJS | `WIKIJS_API_KEY` | Authentification du serveur MCP auprès de WikiJS | ✅ Oui |
| Serveur MCP | `KEYCLOAK_URL`<br>`KEYCLOAK_REALM`<br>`KEYCLOAK_CLIENT_ID` | Protection du serveur MCP via OAuth Keycloak | ⚠️ Optionnel (recommandé en production) |

## Utilisation

### Lancer le serveur MCP

#### Méthode 1 : Exécution directe

**Mode réseau HTTP/SSE (accessible depuis le réseau) :**
```bash
python run_server.py
# Le serveur sera accessible sur http://0.0.0.0:8000 par défaut
# Configurez MCP_HOST et MCP_PORT dans .env pour personnaliser
```

#### Méthode 2 : Avec Docker

Construire et lancer avec Docker :

```bash
# Construire l'image
docker build -t wikijs-mcp .

# Lancer le conteneur
docker run -p 8000:8000 --env-file .env wikijs-mcp
```

Ou avec Docker Compose (si vous avez un fichier `docker-compose.yml`) :

```bash
docker-compose up
```

Le serveur MCP utilise la bibliothèque **FastMCP v3** et supporte le transport HTTP avec SSE automatique.

### Configuration dans Cursor/Claude Desktop

#### Avec Python directement (mode stdio)

Pour utiliser le serveur en mode stdio, modifiez `run_server.py` ou créez un script séparé qui utilise le transport stdio.

**Configuration de base (sans authentification du serveur MCP) :**
```json
{
  "mcpServers": {
    "wikijs": {
      "command": "python",
      "args": ["run_server.py"],
      "cwd": "/chemin/vers/WikiJSMCP",
      "env": {
        "WIKIJS_URL": "https://wiki.example.com",
        "WIKIJS_API_KEY": "votre_cle_api",
        "MCP_TRANSPORT": "stdio"
      }
    }
  }
}
```

**Configuration avec authentification du serveur MCP (recommandé en production) :**
```json
{
  "mcpServers": {
    "wikijs": {
      "command": "python",
      "args": ["run_server.py"],
      "cwd": "/chemin/vers/WikiJSMCP",
      "env": {
        "WIKIJS_URL": "https://wiki.example.com",
        "WIKIJS_API_KEY": "votre_cle_api",
        "MCP_TRANSPORT": "stdio",
        "KEYCLOAK_URL": "https://keycloak.example.com",
        "KEYCLOAK_REALM": "wikijs-mcp",
        "KEYCLOAK_CLIENT_ID": "wikijs-mcp-client",
        "KEYCLOAK_CLIENT_SECRET": "your-client-secret",
        "MCP_BASE_URL": "http://localhost:8000"
      }
    }
  }
}
```

## Structure du projet

```
WikiJSMCP/
├── src/
│   ├── __init__.py
│   ├── server.py             # Serveur MCP principal
│   ├── graphql_client.py     # Client GraphQL pour WikiJS
│   ├── config.py             # Configuration
│   └── auth.py               # Authentification OAuth Keycloak
├── requirements.txt          # Dépendances Python
├── Dockerfile                # Image Docker
├── env.example               # Exemple de configuration
├── run_server.py             # Script d'entrée
└── README.md                 # Cette documentation
```

## Fonctionnalités MCP

### Tools

#### search_wiki
Recherche des pages dans WikiJS.

**Paramètres:**
- `query` (string, requis): Terme de recherche
- `limit` (int, optionnel, défaut: 10): Nombre maximum de résultats

**Exemple:**
```python
search_wiki(query="documentation", limit=5)
```

**Retourne:**
```json
{
  "results": [
    {
      "id": 1,
      "title": "Documentation",
      "description": "Guide d'utilisation",
      "path": "/documentation"
    }
  ]
}
```

#### read_page
Récupère le contenu d'une page par son ID.

**Paramètres:**
- `page_id` (int, requis): ID de la page

**Exemple:**
```python
read_page(page_id=1)
```

**Retourne:**
```json
{
  "id": 1,
  "title": "Documentation",
  "description": "Guide d'utilisation",
  "path": "/documentation",
  "content": "# Documentation\n\nContenu Markdown...",
  "render": "<h1>Documentation</h1><p>Contenu HTML...</p>"
}
```

#### list_pages
Liste les pages disponibles avec pagination.

**Paramètres:**
- `limit` (int, optionnel, défaut: 20): Nombre maximum de résultats
- `offset` (int, optionnel, défaut: 0): Décalage pour la pagination

**Exemple:**
```python
list_pages(limit=50, offset=0)
```

**Retourne:**
```json
[
  {
    "id": 1,
    "title": "Page 1",
    "description": "Description",
    "path": "/page1"
  },
  {
    "id": 2,
    "title": "Page 2",
    "description": "Description",
    "path": "/page2"
  }
]
```

#### get_page_by_path
Récupère une page par son chemin.

**Paramètres:**
- `path` (string, requis): Chemin de la page (ex: /home, /documentation/intro)

**Exemple:**
```python
get_page_by_path(path="/home")
```

**Retourne:**
```json
{
  "id": 1,
  "title": "Accueil",
  "description": "Page d'accueil",
  "path": "/home",
  "content": "# Accueil\n\nBienvenue...",
  "render": "<h1>Accueil</h1><p>Bienvenue...</p>"
}
```

### Resources

- `wikijs://pages` - Description des pages WikiJS disponibles

### Prompts

- `wiki-help` - Documentation générale de l'API WikiJS et exemples d'utilisation

## Exemples d'utilisation

### Rechercher des pages

```python
# Via un client MCP
result = await mcp_client.call_tool(
    "search_wiki",
    {
        "query": "documentation",
        "limit": 5
    }
)
```

### Lire une page par ID

```python
result = await mcp_client.call_tool(
    "read_page",
    {
        "page_id": 1
    }
)
```

### Lire une page par chemin

```python
result = await mcp_client.call_tool(
    "get_page_by_path",
    {
        "path": "/documentation/intro"
    }
)
```

### Lister les pages

```python
result = await mcp_client.call_tool(
    "list_pages",
    {
        "limit": 20,
        "offset": 0
    }
)
```

## Workflow typique

1. Utiliser `search_wiki` ou `list_pages` pour trouver des pages
2. Utiliser `read_page` ou `get_page_by_path` pour récupérer le contenu complet
3. Le contenu Markdown brut est disponible dans le champ `content`
4. Le contenu HTML rendu est disponible dans le champ `render`

## Développement

### Structure du code

- **`graphql_client.py`** : Client GraphQL asynchrone avec authentification par clé API
- **`server.py`** : Serveur MCP principal utilisant FastMCP
- **`config.py`** : Configuration centralisée avec Pydantic Settings
- **`auth.py`** : Authentification OAuth Keycloak (optionnel)

### Requêtes GraphQL

Le client GraphQL utilise les requêtes suivantes :

- **SearchPages** : Recherche de pages
- **GetPage** : Récupération d'une page par ID
- **ListPages** : Liste des pages avec pagination
- **GetPageByPath** : Récupération d'une page par chemin

Consultez `src/graphql_client.py` pour voir les requêtes GraphQL complètes.

## Docker

### Construction de l'image

```bash
docker build -t wikijs-mcp .
```

### Utilisation avec docker-compose

1. Créez un fichier `.env` avec vos credentials
2. Lancez le conteneur :
```bash
docker-compose up
```

## Dépannage

### Erreur : "Clé API WikiJS manquante"

**Cause :** La variable `WIKIJS_API_KEY` n'est pas définie.

**Solution :** Définissez `WIKIJS_API_KEY` dans votre fichier `.env` avec une clé API valide générée dans WikiJS.

### Erreur : "Erreurs GraphQL"

**Causes possibles :**
- Clé API invalide ou expirée
- Permissions insuffisantes sur la clé API
- Endpoint GraphQL incorrect
- Structure de la requête GraphQL incompatible avec votre version de WikiJS

**Solutions :**
1. Vérifiez que la clé API est valide et a les permissions de lecture
2. Vérifiez que `WIKIJS_GRAPHQL_ENDPOINT` pointe vers le bon endpoint
3. Consultez les logs du serveur pour voir les erreurs GraphQL détaillées
4. Vérifiez la documentation de l'API GraphQL de votre version de WikiJS

### Erreur : "Contexte non initialisé"

**Cause :** Le serveur MCP n'a pas été correctement initialisé.

**Solution :** Vérifiez les logs du serveur et assurez-vous que toutes les variables d'environnement requises sont définies.

### Erreurs d'authentification OAuth

Consultez la section "Authentification du serveur MCP avec OAuth Keycloak" pour la configuration détaillée.

## Licence

Ce projet est fourni tel quel pour l'utilisation avec WikiJS.

## Support

Pour toute question ou problème :
- Consultez la documentation de l'API GraphQL de WikiJS
- Vérifiez les logs du serveur pour les erreurs détaillées
- Contactez le support WikiJS si nécessaire
