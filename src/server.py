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

import logging
from fastmcp.utilities.logging import get_logger

to_client_logger = get_logger(name="fastmcp.server.auth.providers.jwt")
to_client_logger.setLevel(level=logging.DEBUG)


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


@mcp.tool()
async def list_wiki_pages(
    ctx: Context,
) -> str:
    """
    Liste déterministe de toutes les pages WikiJS.
    
    Utiliser ce tool pour obtenir la carte complète de l'arborescence
    (liste de tous les chemins de pages disponibles avec leur titre).
    """
    del ctx  # non utilisé pour le moment
    global _app_context
    if _app_context is None:
        return json.dumps({"error": "Contexte non initialisé"}, indent=2)
    
    try:
        pages = await _app_context.graphql_client.list_wiki_pages()
        return json.dumps(pages, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps(
            {"error": f"Erreur lors de la récupération de la liste des pages: {str(e)}"},
            indent=2,
            ensure_ascii=False,
        )


@mcp.tool()
async def read_wiki_page(
    ctx: Context,
    path: str,
) -> str:
    """
    Lit le contenu brut (Markdown) d'une page WikiJS par son chemin.
    
    C'est l'outil prioritaire pour récupérer le contenu d'une ressource
    connue sans faire de recherche floue.
    """
    del ctx  # non utilisé pour le moment
    global _app_context
    if _app_context is None:
        return json.dumps({"error": "Contexte non initialisé"}, indent=2)
    
    try:
        page = await _app_context.graphql_client.read_wiki_page(path)
        return json.dumps(page, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps(
            {"error": f"Erreur lors de la lecture de la page '{path}': {str(e)}"},
            indent=2,
            ensure_ascii=False,
        )


@mcp.prompt()
def wiki_help_prompt() -> Message:
    """
    Documentation des outils MCP disponibles pour interagir avec WikiJS.
    
    Note importante : aucune recherche textuelle floue n'est exposée.
    L'interaction se fait exclusivement via des ressources déterministes.
    """
    help_text = """# Documentation API WikiJS (MCP)

Le serveur MCP expose **2 outils déterministes** pour interagir avec WikiJS
via l'API GraphQL. Il n'expose **aucune recherche textuelle floue**.

## Outils disponibles

### 1. list_wiki_pages
Récupère la **carte complète** des pages du wiki.

**But :**
- Donner à l'IA une vision déterministe de toutes les ressources existantes.

**Retour :**
- Une liste d'objets avec au minimum :
  - `path` : chemin unique de la page (ex: `/home`, `/docs/intro`)
  - `title` : titre humainement lisible

**Exemple d'appel :**
```python
list_wiki_pages()
```

### 2. read_wiki_page
Lit le **contenu brut (Markdown)** d'une page spécifique.

**Paramètres :**
- `path` (string, requis) : chemin exact de la page, tel que renvoyé par `list_wiki_pages`.

**But :**
- Obtenir le contenu d'une ressource connue sans faire de recherche sur Internet.

**Retour :**
- Un objet contenant au minimum :
  - `content` : contenu Markdown brut de la page
  - `contentType` : type de contenu renvoyé par WikiJS

**Exemple d'appel :**
```python
read_wiki_page(path="/docs/intro")
```

## Stratégie d'utilisation recommandée

1. Utiliser `list_wiki_pages` pour découvrir toutes les ressources disponibles
   et choisir précisément la page à lire.
2. Utiliser `read_wiki_page(path)` comme **source de vérité prioritaire**
   pour toute connaissance interne documentée dans le wiki.
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
    
    # Lancer le serveur avec le transport configuré (MCP_TRANSPORT)
    if config.mcp_transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(
            transport=config.mcp_transport,
            host=config.mcp_host,
            port=config.mcp_port,
            path="/mcp",
        )


if __name__ == "__main__":
    main()
