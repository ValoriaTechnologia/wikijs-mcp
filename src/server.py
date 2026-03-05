"""Serveur MCP principal pour WikiJS utilisant FastMCP."""

import json
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Optional

from fastmcp import FastMCP, Context
from fastmcp.prompts import Message

from src.graphql_client import GraphQLClient
from src.auth import get_auth_provider
from src.config import get_config


@dataclass
class AppContext:
    """Contexte d'application avec dépendances typées."""

    graphql_client: GraphQLClient


# Variable globale pour stocker le contexte (sera initialisé dans lifespan)
_app_context: Optional[AppContext] = None


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Gère le cycle de vie de l'application avec contexte typé."""
    global _app_context
    
    # Récupérer la configuration
    config = get_config()
    
    # Initialisation au démarrage
    # Créer le client GraphQL avec authentification par clé API
    graphql_client = GraphQLClient(
        graphql_endpoint=config.wikijs_graphql_endpoint,
        api_key=config.wikijs_api_key
    )
    
    # Créer le contexte
    app_ctx = AppContext(
        graphql_client=graphql_client
    )
    _app_context = app_ctx
    
    try:
        yield app_ctx
    finally:
        # Nettoyage à l'arrêt (si nécessaire)
        _app_context = None


# Créer le provider d'authentification si configuré
_auth_provider = get_auth_provider()

# Créer l'instance FastMCP
# Si un provider d'authentification est configuré, l'utiliser
mcp = FastMCP("wikijs-mcp", lifespan=app_lifespan, auth=_auth_provider)


# Tools MCP
@mcp.tool()
async def search_wiki(
    ctx: Context,
    query: str
) -> str:
    """
    Recherche des pages dans WikiJS.
    
    Args:
        query: Terme de recherche
    
    Returns:
        Résultats de la recherche formatés en JSON
    """
    global _app_context
    if _app_context is None:
        return json.dumps({"error": "Contexte non initialisé"}, indent=2)
    
    try:
        result = await _app_context.graphql_client.search_pages(query)
        return json.dumps(result, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Erreur lors de la recherche: {str(e)}"}, indent=2)


@mcp.tool()
async def read_page(
    ctx: Context,
    page_id: int
) -> str:
    """
    Récupère le contenu d'une page WikiJS par son ID.
    
    Args:
        page_id: ID de la page à récupérer
    
    Returns:
        Contenu de la page (Markdown brut et HTML rendu) formaté en JSON
    """
    global _app_context
    if _app_context is None:
        return json.dumps({"error": "Contexte non initialisé"}, indent=2)
    
    try:
        result = await _app_context.graphql_client.get_page(page_id)
        return json.dumps(result, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Erreur lors de la récupération de la page: {str(e)}"}, indent=2)


@mcp.tool()
async def list_pages(
    ctx: Context,
    limit: int = 20
) -> str:
    """
    Liste les pages disponibles dans WikiJS.
    
    Args:
        limit: Nombre maximum de résultats (défaut: 20)
    
    Returns:
        Liste des pages formatée en JSON
    """
    global _app_context
    if _app_context is None:
        return json.dumps({"error": "Contexte non initialisé"}, indent=2)
    
    try:
        result = await _app_context.graphql_client.list_pages(limit)
        return json.dumps(result, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Erreur lors de la récupération de la liste: {str(e)}"}, indent=2)


@mcp.tool()
async def get_page_by_path(
    ctx: Context,
    path: str,
    language: str = 'fr'
) -> str:
    """
    Récupère une page WikiJS par son chemin.
    
    Args:
        path: Chemin de la page (ex: /home, /documentation/intro)
        language: Langue de la page (défaut: 'fr')
    
    Returns:
        Contenu de la page (Markdown brut et HTML rendu) formaté en JSON
    """
    global _app_context
    if _app_context is None:
        return json.dumps({"error": "Contexte non initialisé"}, indent=2)
    
    try:
        result = await _app_context.graphql_client.get_page_by_path(path, language)
        return json.dumps(result, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Erreur lors de la récupération de la page: {str(e)}"}, indent=2)


# Resources avec FastMCP
@mcp.resource("wikijs://pages")
def get_pages_resource(ctx: Context) -> str:
    """Liste toutes les pages disponibles dans WikiJS."""
    global _app_context
    if _app_context is None:
        return json.dumps({"error": "Contexte non initialisé"}, indent=2)
    
    # Note: Cette resource est synchrone, donc on ne peut pas faire d'appel async
    # On retourne juste une description
    return json.dumps({
        "description": "Liste des pages WikiJS",
        "note": "Utilisez le tool list_pages pour récupérer la liste complète"
    }, indent=2, ensure_ascii=False)


# Prompts avec FastMCP
@mcp.prompt()
def wiki_help_prompt() -> Message:
    """Documentation générale de l'API WikiJS et exemples d'utilisation."""
    help_text = """# Documentation API WikiJS

Le serveur MCP expose 4 outils pour interagir avec WikiJS via l'API GraphQL.

## Outils disponibles

### 1. search_wiki
Recherche des pages dans WikiJS.

**Paramètres:**
- `query` (string, requis): Terme de recherche

**Exemple:**
```python
search_wiki(query="documentation")
```

### 2. read_page
Récupère le contenu d'une page par son ID.

**Paramètres:**
- `page_id` (int, requis): ID de la page

**Exemple:**
```python
read_page(page_id=1)
```

### 3. list_pages
Liste les pages disponibles avec pagination.

**Paramètres:**
- `limit` (int, optionnel, défaut: 20): Nombre maximum de résultats

**Exemple:**
```python
list_pages(limit=50)
```

### 4. get_page_by_path
Récupère une page par son chemin.

**Paramètres:**
- `path` (string, requis): Chemin de la page (ex: /home, /documentation/intro)
- `language` (string, optionnel, défaut: 'fr'): Langue de la page

**Exemple:**
```python
get_page_by_path(path="/home", language="fr")
```

## Authentification

- **Utilisateurs MCP** : OAuth Keycloak (si configuré)
- **Appels WikiJS** : Clé API dans le header Authorization

## Workflow typique

1. Utiliser `search_wiki` ou `list_pages` pour trouver des pages
2. Utiliser `read_page` ou `get_page_by_path` pour récupérer le contenu complet
"""
    return Message(help_text)


def main():
    """Point d'entrée principal."""
    # Rediriger les logs vers stderr pour ne pas polluer stdout
    import logging
    logging.basicConfig(
        level=logging.WARNING,
        stream=sys.stderr,
        format='%(levelname)s: %(message)s'
    )
    
    # Récupérer la configuration
    config = get_config()
    
    # Lancer le serveur avec le transport approprié
    # FastMCP.run() est une fonction synchrone qui gère sa propre boucle d'événements
    host = config.mcp_host
    port = config.mcp_port
    # Utiliser run avec transport HTTP (FastMCP utilise HTTP avec SSE fallback)
    mcp.run(transport="http", host=host, port=port, path="/mcp")


if __name__ == "__main__":
    main()
