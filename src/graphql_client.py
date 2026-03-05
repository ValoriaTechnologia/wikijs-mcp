"""Client GraphQL pour l'API WikiJS."""

from typing import Any, Dict, Optional
import httpx

from src.config import get_config


class GraphQLClient:
    """Client GraphQL asynchrone pour interagir avec l'API WikiJS."""
    
    def __init__(
        self,
        graphql_endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 30.0
    ):
        """
        Initialise le client GraphQL.
        
        Args:
            graphql_endpoint: URL de l'endpoint GraphQL (défaut: depuis WIKIJS_GRAPHQL_ENDPOINT)
            api_key: Clé API pour l'authentification (défaut: depuis WIKIJS_API_KEY)
            timeout: Timeout des requêtes en secondes
        """
        config = get_config()
        self.graphql_endpoint = graphql_endpoint or config.wikijs_graphql_endpoint
        self.api_key = api_key or config.wikijs_api_key
        self.timeout = timeout
        
        # Nettoyer l'URL (enlever le slash final)
        self.graphql_endpoint = self.graphql_endpoint.rstrip('/')
        
        # Headers par défaut avec authentification
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        if self.api_key:
            self.headers['Authorization'] = f'Bearer {self.api_key}'
    
    async def execute_query(
        self,
        query: str,
        variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Exécute une requête GraphQL.
        
        Args:
            query: Requête GraphQL (string)
            variables: Variables pour la requête (dict optionnel)
        
        Returns:
            Réponse JSON de l'API GraphQL
        
        Raises:
            httpx.HTTPError: En cas d'erreur HTTP
            ValueError: Si la réponse contient des erreurs GraphQL
        """
        if not self.api_key:
            raise ValueError(
                "Clé API WikiJS manquante. Fournissez WIKIJS_API_KEY "
                "dans les variables d'environnement ou au constructeur."
            )
        
        payload = {
            'query': query
        }
        
        if variables:
            payload['variables'] = variables
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    self.graphql_endpoint,
                    json=payload,
                    headers=self.headers
                )
                response.raise_for_status()
                
                result = response.json()
                
                # Vérifier les erreurs GraphQL
                if 'errors' in result and result['errors']:
                    error_messages = [err.get('message', str(err)) for err in result['errors']]
                    raise ValueError(f"Erreurs GraphQL: {'; '.join(error_messages)}")
                
                return result.get('data', {})
            
            except httpx.HTTPStatusError as e:
                error_detail = {
                    'status_code': e.response.status_code,
                    'message': str(e),
                    'response': None
                }
                try:
                    error_detail['response'] = e.response.json()
                except Exception:
                    error_detail['response'] = e.response.text
                
                raise httpx.HTTPError(
                    f"Erreur HTTP {e.response.status_code}: {error_detail.get('response', 'Unknown error')}"
                ) from e
            
            except httpx.RequestError as e:
                raise httpx.RequestError(f"Erreur de requête GraphQL: {str(e)}") from e
    
    async def search_pages(self, query: str) -> Dict[str, Any]:
        """
        Recherche des pages dans WikiJS.
        
        Args:
            query: Terme de recherche
        
        Returns:
            Résultats de la recherche
        """
        graphql_query = """
        query SearchPages($query: String!) {
          pages {
            search(query: $query) {
              results {
                id
                title
                description
                path
                locale
              }
            }
          }
        }
        """
        
        variables = {
            'query': query,
        }
        
        result = await self.execute_query(graphql_query, variables)
        return result.get('pages', {}).get('search', {})
    
    async def get_page(self, page_id: int) -> Dict[str, Any]:
        """
        Récupère une page par son ID.
        
        Args:
            page_id: ID de la page
        
        Returns:
            Données de la page (id, title, description, path, content, render)
        """
        graphql_query = """
        query GetPage($id: Int!) {
          pages {
            single(id: $id) {
              id
              title
              description
              path
              content
              render
            }
          }
        }
        """
        
        variables = {
            'id': page_id
        }
        
        result = await self.execute_query(graphql_query, variables)
        return result.get('pages', {}).get('single', {})
    
    async def list_pages(self, limit: int = 20) -> Dict[str, Any]:
        """
        Liste les pages disponibles.
        
        Args:
            limit: Nombre maximum de résultats (défaut: 20)
        
        Returns:
            Liste des pages
        """
        graphql_query = """
        query ListPages($limit: Int) {
          pages {
            list(limit: $limit) {
              id
              title
              description
              path
            }
          }
        }
        """
        
        variables = {
            'limit': limit,
        }
        
        result = await self.execute_query(graphql_query, variables)
        return result.get('pages', {}).get('list', [])
    
    async def get_page_by_path(self, path: str, language: str = 'fr') -> Dict[str, Any]:
        """
        Récupère une page par son chemin.
        
        Args:
            path: Chemin de la page (ex: /home, /documentation/intro)
            language: Langue de la page (défaut: 'fr')
        
        Returns:
            Données de la page (id, title, description, path, content, render)
        """
        graphql_query = """
        query GetPageByPath($path: String!, $locale: String!) {
          pages {
            singleByPath(path: $path, locale: $locale) {
              id
              title
              description
              path
              content
              render
            }
          }
        }
        """
        
        variables = {
            'path': path,
            'locale': language
        }
        
        result = await self.execute_query(graphql_query, variables)
        return result.get('pages', {}).get('singleByPath', {})
